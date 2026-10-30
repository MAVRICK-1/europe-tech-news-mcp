"""Fetch, cache, filter and rank articles across feeds."""

from __future__ import annotations

import asyncio
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

import httpx

from .feeds import FEEDS, Feed, feeds_for
from .parser import Article, parse_feed

USER_AGENT = "europe-tech-news-mcp/0.1 (+https://github.com/MAVRICK-1/europe-tech-news-mcp)"
CACHE_TTL_SECONDS = 600
MAX_FEED_BYTES = 3_000_000

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ai": ("ai", "artificial intelligence", "llm", "machine learning", "mistral", "genai", "openai", "model"),
    "funding": ("raises", "raised", "funding", "series a", "series b", "series c", "seed", "round", "investment", "€", "$m"),
    "regulation": ("regulation", "eu ai act", "dma", "dsa", "gdpr", "data act", "commission", "parliament", "antitrust", "fine", "law"),
    "security": ("security", "breach", "ransomware", "vulnerability", "cve", "cyber", "hack"),
    "cloud": ("cloud", "kubernetes", "open source", "sovereign", "data centre", "data center", "hyperscaler", "devops", "aws", "azure", "google cloud", "ovh", "scaleway", "hetzner", "gaia-x"),
    "opensource": ("open source", "opensource", "cncf", "cloud native", "kubernetes", "cilium", "prometheus", "grafana", "helm", "argocd", "argo cd", "flux"),
    "sovereignty": ("sovereign", "sovereignty", "gaia-x", "european cloud", "data localisation", "data localization"),
    "bugs": ("bug", "bugs", "crash", "crashes", "crashed", "outage", "down", "glitch", "flaw", "vulnerability", "zero-day", "patch", "exploit", "failure", "disruption", "incident"),
    "outages": ("outage", "outages", "down", "downtime", "disruption", "incident", "failure"),
    "projects": ("project", "release", "roadmap", "open source", "opensource", "cncf", "cloud native", "kubernetes", "cilium", "prometheus", "grafana", "helm", "argocd", "argo cd", "flux"),
    "opportunities": ("tender", "procurement", "rfp", "request for proposals", "grant", "funding opportunity", "contract notice"),
    "tenders": ("tender", "procurement", "rfp", "request for proposals", "contract notice"),
    "all": (),
    "tech": (),
    "semiconductors": ("chip", "semiconductor", "asml", "infineon", "stmicro", "foundry", "nexperia"),
    "fintech": ("fintech", "payments", "bank", "neobank", "revolut", "klarna", "wise"),
    "climate": ("climate", "energy", "cleantech", "battery", "carbon", "solar", "hydrogen"),
    "startups": ("startup", "founder", "scaleup", "unicorn", "accelerator"),
}

OPERATIONAL_PLATFORM_KEYWORDS = (
    "kubernetes",
    "k8s",
    "container",
    "docker",
    "helm",
    "argo cd",
    "argocd",
    "gitlab",
    "github",
    "linux",
    "ubuntu",
    "debian",
    "red hat",
    "cilium",
    "prometheus",
    "grafana",
    "cloud",
    "aws",
    "azure",
    "google cloud",
    "gcp",
    "hetzner",
    "ovh",
    "scaleway",
    "data centre",
    "data center",
)

OPERATIONAL_RISK_KEYWORDS = (
    "critical",
    "cve",
    "vulnerability",
    "zero-day",
    "zero day",
    "exploit",
    "attack",
    "attacked",
    "ransomware",
    "breach",
    "outage",
    "incident",
    "downtime",
    "disruption",
    "failure",
)

OPERATIONAL_CHANGE_KEYWORDS = (
    "release",
    "upgrade",
    "update",
    "patch",
    "deprecat",
    "end of life",
    "support",
    "migration",
)

OPERATIONAL_SECURITY_TARGET_KEYWORDS = (
    "php",
    "ruby",
    "openssl",
    "nginx",
    "apache",
    "ssh",
    "vpn",
    "database",
    "postgres",
    "mysql",
)

OPERATIONAL_COMPLIANCE_KEYWORDS = (
    "nis2",
    "dora",
    "gdpr",
    "cyber resilience act",
    "data act",
    "sovereignty",
)

EUROPE_RE = re.compile(
    r"(?<!\w)(europe|european|eu|brussels|ai act|dma|dsa|gdpr|uk|britain|british|london|germany|german|"
    r"berlin|france|french|paris|dutch|netherlands|amsterdam|nordic|sweden|swedish|finland|finnish|norway|"
    r"denmark|danish|spain|spanish|italy|italian|ireland|irish|dublin|poland|polish|swiss|switzerland|"
    r"ofcom|mistral|asml|spotify|klarna|revolut|sap|nokia|ericsson|siemens|infineon|ovh|scaleway|hetzner|deepl)(?!\w)",
    re.IGNORECASE,
)

TECH_RE = re.compile(
    r"(?<!\w)(ai|artificial intelligence|algorithm|software|hardware|cloud|cybersecurity|cybercrime|"
    r"ransomware|vulnerability|cve|data cent(?:er|re)|datacent(?:er|re)|internet|"
    r"telecom|network|5g|6g|mobile|semiconductor|chip|quantum|kubernetes|linux|open source|"
    r"space|satellite|gps|platform|technology|technologies|tech|open source|opensource|cncf|cloud native|"
    r"kubernetes|cilium|prometheus|grafana|helm|argocd|argo cd|flux|sovereign|sovereignty|gaia-x|"
    r"nis2|dora|gdpr|cyber resilience act|data act|digital markets act|digital services act|dma|dsa|"
    r"mistral|asml|sap|nokia|ericsson|infineon|ovh|scaleway|hetzner|cryptocurrency|crypto|blockchain)(?!\w)",
    re.IGNORECASE,
)

_STOP = {"the", "a", "an", "to", "of", "in", "for", "and", "on", "with", "is", "as", "at", "by", "from", "its", "new"}

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
        if feed.broad:
            articles = [a for a in articles if EUROPE_RE.search(f"{a.title} {a.summary}")]
        articles = [a for a in articles if TECH_RE.search(f"{a.title} {a.summary} {' '.join(a.tags)}")]
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
    topic_key = (topic or "").lower()
    keywords = TOPIC_KEYWORDS.get(topic_key, ()) if topic else ()
    if topic and not keywords and topic_key not in {"all", "tech"}:
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


def _tokens(title: str) -> set[str]:
    return {w for w in _norm_title(title).split() if len(w) > 2 and w not in _STOP}


def rank_top(articles: list[Article], now: datetime | None = None) -> list[tuple[float, int, Article]]:
    """Rank by recency, outlet weight, Europe relevance and multi-outlet coverage."""
    now = now or datetime.now(timezone.utc)
    weights = {f.name: f.weight for f in FEEDS}
    toks = [_tokens(a.title) for a in articles]
    scored: list[tuple[float, int, Article]] = []
    for i, a in enumerate(articles):
        sources = {a.source}
        for j, b in enumerate(articles):
            if i != j and toks[i] and toks[j] and len(toks[i] & toks[j]) / len(toks[i] | toks[j]) >= 0.4:
                sources.add(b.source)
        age_h = max(0.0, (now - a.published).total_seconds() / 3600)  # type: ignore[operator]
        score = 3.0 / (1.0 + age_h / 24) + weights.get(a.source, 1.0) + 1.5 * (len(sources) - 1)
        if EUROPE_RE.search(a.title):
            score += 0.5
        scored.append((score, len(sources), a))
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored


def _cell(text: str, limit: int | None = None) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def to_table(articles: list[Article]) -> str:
    """Markdown table: heading, short context, link."""
    if not articles:
        return "No matching stories found."
    rows = ["| # | Heading | Context | Source | Date | Link |", "|---|---|---|---|---|---|"]
    for i, a in enumerate(articles, 1):
        date = a.published.strftime("%Y-%m-%d") if a.published else ""
        rows.append(
            f"| {i} | {_cell(a.title)} | {_cell(a.summary, 200)} | {_cell(a.source)} | {date} | [Read]({a.url}) |"
        )
    return "\n".join(rows)


def _matches_keywords(haystack: str, keywords: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", haystack) for keyword in keywords)


def _operational_priority(article: Article) -> tuple[int, str] | None:
    haystack = f"{article.title} {article.summary} {' '.join(article.tags)}".lower()
    platform_match = _matches_keywords(haystack, OPERATIONAL_PLATFORM_KEYWORDS)
    risk_match = _matches_keywords(haystack, OPERATIONAL_RISK_KEYWORDS)
    security_target_match = _matches_keywords(haystack, OPERATIONAL_SECURITY_TARGET_KEYWORDS)
    change_match = _matches_keywords(haystack, OPERATIONAL_CHANGE_KEYWORDS)
    compliance_match = _matches_keywords(haystack, OPERATIONAL_COMPLIANCE_KEYWORDS)

    if not (compliance_match or (risk_match and (platform_match or security_target_match)) or (platform_match and change_match)):
        return None
    if risk_match and (platform_match or security_target_match):
        return 3, "Potential impact to managed platform availability or security; assess exposure and patch status."
    if compliance_match:
        return 1, "European compliance or infrastructure change that may affect customer platform planning."
    return 1, "Relevant platform, cloud, or infrastructure development to monitor for managed environments."


def to_operations_table(items: list[tuple[int, str, Article]]) -> str:
    """Markdown table for operational news, including priority and relevance."""
    if not items:
        return "No operationally relevant stories found."
    labels = {3: "Critical", 2: "Watch", 1: "Monitor"}
    rows = [
        "| # | Priority | Heading | Why it matters | Source | Date | Link |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, (priority, reason, article) in enumerate(items, 1):
        date = article.published.strftime("%Y-%m-%d") if article.published else ""
        rows.append(
            f"| {i} | {labels[priority]} | {_cell(article.title)} | {_cell(reason, 140)} | "
            f"{_cell(article.source)} | {date} | [Read]({article.url}) |"
        )
    return "\n".join(rows)


async def get_operational_news(
    *,
    days: int = 14,
    limit: int = 10,
    client: httpx.AsyncClient | None = None,
) -> dict:
    """Return European news prioritized for managed-platform operations."""
    days = max(1, min(days, 30))
    limit = max(1, min(limit, 50))
    articles, errors = await fetch_articles(feeds_for("europe"), client)
    candidates: list[tuple[int, str, Article]] = []
    for article in filter_articles(articles, days=days):
        priority = _operational_priority(article)
        if priority is not None:
            candidates.append((*priority, article))
    candidates.sort(
        key=lambda item: (item[0], item[2].published or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )
    selected = candidates[:limit]
    return {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_days": days,
        "count": len(selected),
        "table": to_operations_table(selected),
        "articles": [
            {
                **article.to_dict(),
                "priority": {3: "critical", 2: "watch", 1: "monitor"}[priority],
                "why_it_matters": reason,
            }
            for priority, reason, article in selected
        ],
        "errors": errors,
    }


async def get_top_news(
    *,
    region: str | None = None,
    topic: str | None = None,
    days: int = 3,
    limit: int = 10,
    client: httpx.AsyncClient | None = None,
) -> dict:
    days = max(1, min(days, 30))
    limit = max(1, min(limit, 50))
    articles, errors = await fetch_articles(feeds_for(region), client)
    pool = filter_articles(articles, days=days, topic=topic)
    ranked = rank_top(pool)[:limit]
    return {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_days": days,
        "count": len(ranked),
        "table": to_table([a for _, _, a in ranked]),
        "articles": [{**a.to_dict(), "covered_by_sources": n} for _, n, a in ranked],
        "errors": errors,
    }


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
        "table": to_table(picked),
        "articles": [a.to_dict() for a in picked],
        "errors": errors,
    }
