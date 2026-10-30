"""Fetch, cache, filter and rank articles across feeds."""

from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

import httpx

from .feeds import Feed, feeds_for
from .parser import Article, parse_feed

USER_AGENT = "europe-tech-news-mcp/0.1 (+https://github.com/MAVRICK-1/europe-tech-news-mcp)"
CACHE_TTL_SECONDS = 600
MAX_FEED_BYTES = 3_000_000

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ai": ("ai", "artificial intelligence", "llm", "machine learning", "mistral", "genai", "openai", "model"),
    "funding": ("raises", "raised", "funding", "series a", "series b", "series c", "seed", "round", "investment", "€", "$m"),
    "regulation": ("regulation", "eu ai act", "dma", "dsa", "gdpr", "data act", "commission", "parliament", "antitrust", "fine", "law"),
    "security": ("security", "breach", "ransomware", "vulnerability", "cve", "cyber", "hack"),
    "cloud": ("cloud", "kubernetes", "open source", "sovereign", "data centre", "data center", "hyperscaler", "devops"),
    "semiconductors": ("chip", "semiconductor", "asml", "infineon", "stmicro", "foundry", "nexperia"),
    "fintech": ("fintech", "payments", "bank", "neobank", "revolut", "klarna", "wise"),
    "climate": ("climate", "energy", "cleantech", "battery", "carbon", "solar", "hydrogen"),
    "startups": ("startup", "founder", "scaleup", "unicorn", "accelerator"),
}

_cache: dict[str, tuple[float, list[Article]]] = {}


def _canonical(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc.lower().removeprefix("www."), parts.path.rstrip("/"), "", ""))


def _norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


async def _fetch_one(client: httpx.AsyncClient, feed: Feed) -> tuple[Feed, list[Article], str | None]:
    now = time.monotonic()
    hit = _cache.get(feed.url)
    if hit and now - hit[0] < CACHE_TTL_SECONDS:
        return feed, hit[1], None
    try:
        resp = await client.get(feed.url)
        resp.raise_for_status()
        body = resp.content[:MAX_FEED_BYTES]
        articles = parse_feed(body, feed.name)
        _cache[feed.url] = (now, articles)
        return feed, articles, None
    except Exception as exc:  # noqa: BLE001 - one bad feed must not break the digest
        return feed, [], f"{type(exc).__name__}: {exc}"[:200]


async def fetch_articles(
    feeds: list[Feed], client: httpx.AsyncClient | None = None
) -> tuple[list[Article], dict[str, str]]:
    owns = client is None
    client = client or httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
        timeout=httpx.Timeout(10.0),
        follow_redirects=True,
    )
    try:
        results = await asyncio.gather(*(_fetch_one(client, f) for f in feeds))
    finally:
        if owns:
            await client.aclose()
    articles: list[Article] = []
    errors: dict[str, str] = {}
    for feed, items, err in results:
        articles.extend(items)
        if err:
            errors[feed.name] = err
    return articles, errors


def filter_articles(
    articles: list[Article],
    *,
    days: int = 7,
    topic: str | None = None,
    query: str | None = None,
    now: datetime | None = None,
) -> list[Article]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    keywords = TOPIC_KEYWORDS.get((topic or "").lower(), ()) if topic else ()
    if topic and not keywords:
        keywords = (topic.lower(),)
    q = (query or "").lower().strip()

    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    out: list[Article] = []
    for a in articles:
        if a.published is None or a.published < cutoff or a.published > now + timedelta(hours=2):
            continue
        hay = f"{a.title} {a.summary} {' '.join(a.tags)}".lower()
        if keywords and not any(re.search(rf"(?<!\w){re.escape(k)}", hay) for k in keywords):
            continue
        if q and q not in hay:
            continue
        cu, nt = _canonical(a.url), _norm_title(a.title)
        if cu in seen_urls or nt in seen_titles:
            continue
        seen_urls.add(cu)
        seen_titles.add(nt)
        out.append(a)
    out.sort(key=lambda a: a.published, reverse=True)  # type: ignore[arg-type,return-value]
    return out


async def get_news(
    *,
    region: str | None = None,
    topic: str | None = None,
    query: str | None = None,
    source: str | None = None,
    days: int = 7,
    limit: int = 10,
    client: httpx.AsyncClient | None = None,
) -> dict:
    days = max(1, min(days, 60))
    limit = max(1, min(limit, 50))
    feeds = feeds_for(region, source)
    if not feeds:
        return {"articles": [], "errors": {}, "note": f"No feeds match region={region!r} source={source!r}."}
    articles, errors = await fetch_articles(feeds, client)
    picked = filter_articles(articles, days=days, topic=topic, query=query)[:limit]
    return {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_days": days,
        "feeds_queried": [f.name for f in feeds],
        "count": len(picked),
        "articles": [a.to_dict() for a in picked],
        "errors": errors,
    }
