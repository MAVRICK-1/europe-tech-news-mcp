"""Minimal, dependency-free RSS 2.0 / Atom parser with safe XML handling."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass
class Article:
    title: str
    url: str
    source: str
    published: datetime | None
    summary: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published": self.published.isoformat() if self.published else None,
            "summary": self.summary,
            "tags": self.tags,
        }


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _clean(text: str | None, limit: int = 280) -> str:
    if not text:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", text))
    text = _WS_RE.sub(" ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _child_text(el: ET.Element, *names: str) -> str | None:
    for child in el:
        if _local(child.tag) in names and child.text:
            return child.text
    return None


def parse_feed(xml_bytes: bytes, source: str) -> list[Article]:
    """Parse RSS or Atom bytes into Articles. Returns [] on malformed input."""
    # Reject DTDs/entities outright to avoid entity-expansion attacks.
    head = xml_bytes[:4096].lower()
    if b"<!doctype" in head and b"<!entity" in xml_bytes[:65536].lower():
        return []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    articles: list[Article] = []
    for el in root.iter():
        kind = _local(el.tag)
        if kind not in ("item", "entry"):
            continue
        title = _clean(_child_text(el, "title"), limit=300)
        url = ""
        if kind == "item":
            url = (_child_text(el, "link") or "").strip()
        else:
            for child in el:
                if _local(child.tag) == "link":
                    rel = child.attrib.get("rel", "alternate")
                    if rel == "alternate" and child.attrib.get("href"):
                        url = child.attrib["href"]
                        break
        if not title or not url.startswith(("http://", "https://")):
            continue
        published = _parse_date(
            _child_text(el, "pubDate", "published", "updated", "date")
        )
        summary = _clean(_child_text(el, "description", "summary", "encoded", "content"))
        tags = [
            _clean(c.text, 40) if kind == "item" else c.attrib.get("term", "")
            for c in el
            if _local(c.tag) in ("category",)
        ]
        tags = [t for t in tags if t][:6]
        articles.append(Article(title, url, source, published, summary, tags))
    return articles
