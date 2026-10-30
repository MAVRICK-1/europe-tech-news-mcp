"""MCP server exposing European tech news tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import aggregator
from .aggregator import TOPIC_KEYWORDS
from .feeds import FEEDS, REGION_ALIASES

mcp = FastMCP(
    "europe-tech-news",
    instructions=(
        "Fetches recent European tech news from public RSS feeds. Summaries are short "
        "snippets; paraphrase them and always link the original article. Check `errors` "
        "in results, since some feeds may be unreachable. Present stories to the user as a "
        "markdown table with columns Heading | Context | Link; each result includes a "
        "ready-made `table` field you can show as is. Use topic 'bugs' for bugs/crashes/outages "
        "and topic 'cloud' for cloud news. Use get_obmondo_operations_news for actionable "
        "managed-platform security, availability, infrastructure, and EU compliance news."
    ),
)


@mcp.tool()
async def get_top_eu_tech_news(region: str = "europe", topic: str | None = None, days: int = 3, limit: int = 10) -> dict:
    """Biggest European tech stories right now, ranked by recency, outlet weight and how many
    outlets cover them. Best for daily briefings. topic examples: bugs (bugs/crashes/outages),
    cloud, ai, funding, regulation. days: 1-30 (default 3)."""
    return await aggregator.get_top_news(region=region, topic=topic, days=days, limit=limit)


@mcp.tool()
async def get_europe_tech_news(
    region: str = "europe",
    topic: str | None = None,
    days: int = 7,
    limit: int = 10,
) -> dict:
    """Top recent tech stories from European outlets.

    region: europe, eu, uk, ireland, germany/dach, france, benelux/netherlands,
            nordics/scandinavia, spain/iberia.
    topic: ai, funding, regulation, security, cloud, bugs (bugs/crashes/outages),
           semiconductors, fintech, climate, startups (or any free keyword).
    days: lookback window, 1-60 (default 7). limit: max stories, 1-50 (default 10).
    """
    return await aggregator.get_news(region=region, topic=topic, days=days, limit=limit)


@mcp.tool()
async def get_obmondo_operations_news(days: int = 14, limit: int = 10) -> dict:
    """European news prioritized for managed-platform operations: critical vulnerabilities,
    outages, Kubernetes/GitOps/Linux/cloud changes, and EU compliance. Each result includes
    a priority and a short explanation of operational relevance. days: 1-30; limit: 1-50."""
    return await aggregator.get_operational_news(days=days, limit=limit)


@mcp.tool()
async def search_europe_tech_news(query: str, days: int = 14, limit: int = 10, region: str = "europe") -> dict:
    """Keyword search across European tech feeds (e.g. 'Mistral', 'Digital Markets Act', 'ASML')."""
    return await aggregator.get_news(region=region, query=query, days=days, limit=limit)


@mcp.tool()
async def get_source_news(source: str, days: int = 7, limit: int = 10) -> dict:
    """Latest stories from one outlet by name, e.g. 'Sifted', 'Tech.eu', 'Heise'."""
    return await aggregator.get_news(region="europe", source=source, days=days, limit=limit)


@mcp.tool()
def list_sources() -> dict:
    """List configured feeds, supported regions and topics."""
    return {
        "sources": [{"name": f.name, "region": f.region, "topics": list(f.topics)} for f in FEEDS],
        "regions": sorted(REGION_ALIASES),
        "topics": sorted(TOPIC_KEYWORDS),
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
