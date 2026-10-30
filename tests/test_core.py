from datetime import datetime, timedelta, timezone

import httpx

from europe_tech_news import aggregator
from europe_tech_news.feeds import feeds_for
from europe_tech_news.parser import parse_feed

NOW = datetime.now(timezone.utc)


def rfc(dt: datetime) -> str:
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def rss(items: list[tuple[str, str, datetime, str]]) -> bytes:
    body = "".join(
        f"<item><title>{t}</title><link>{u}</link><pubDate>{rfc(d)}</pubDate>"
        f"<description>&lt;p&gt;{s}&lt;/p&gt;</description></item>"
        for t, u, d, s in items
    )
    return f"<?xml version='1.0'?><rss version='2.0'><channel>{body}</channel></rss>".encode()


ATOM = b"""<?xml version='1.0'?>
<feed xmlns='http://www.w3.org/2005/Atom'>
  <entry><title>Atom story</title><link rel='alternate' href='https://x.eu/a'/>
  <updated>2099-01-01T00:00:00Z</updated><summary>hello</summary></entry>
</feed>"""


def test_parse_rss_strips_html():
    arts = parse_feed(rss([("Mistral raises", "https://a.eu/1", NOW, "Big round")]), "T")
    assert arts[0].title == "Mistral raises"
    assert arts[0].summary == "Big round"


def test_parse_atom():
    arts = parse_feed(ATOM, "T")
    assert arts[0].url == "https://x.eu/a"


def test_malformed_and_entity_bombs_return_empty():
    assert parse_feed(b"<rss><oops", "T") == []
    bomb = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><rss>&a;</rss>'
    assert parse_feed(bomb, "T") == []


def test_rejects_non_http_links():
    xml = rss([("Bad", "javascript:alert(1)", NOW, "x")])
    assert parse_feed(xml, "T") == []


def test_filter_window_topic_dedupe():
    arts = parse_feed(
        rss(
            [
                ("Startup raises €10M Series A", "https://a.eu/1", NOW - timedelta(days=1), "funding"),
                ("Startup raises €10M Series A", "https://www.b.eu/1/", NOW - timedelta(days=1), "dup title"),
                ("Old news about AI", "https://a.eu/2", NOW - timedelta(days=30), "ai"),
                ("EU AI Act delay", "https://a.eu/3", NOW - timedelta(hours=3), "regulation"),
            ]
        ),
        "T",
    )
    out = aggregator.filter_articles(arts, days=7)
    assert [a.url for a in out] == ["https://a.eu/3", "https://a.eu/1"]
    assert len(aggregator.filter_articles(arts, days=7, topic="funding")) == 1
    assert aggregator.filter_articles(arts, days=7, topic="ai")[0].title == "EU AI Act delay"


def test_region_selection_includes_pan_european():
    names = {f.name for f in feeds_for("germany")}
    assert "Heise Online" in names and "Tech.eu" in names
    assert "Maddyness" not in names
    assert {f.name for f in feeds_for("europe", source="sifted")} == {"Sifted"}


async def test_get_news_survives_failing_feed():
    aggregator._cache.clear()
    good = rss([("Chip news ASML", "https://a.eu/9", NOW, "semiconductor")])

    def handler(request: httpx.Request) -> httpx.Response:
        if "sifted" in str(request.url):
            return httpx.Response(500)
        return httpx.Response(200, content=good)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await aggregator.get_news(region="europe", topic="semiconductors", client=client)
    assert res["count"] == 1
    assert "Sifted" in res["errors"]
