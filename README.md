# europe-tech-news-mcp

An MCP server that gives Claude (or any MCP client) current tech news from across Europe, pulled live from public RSS/Atom feeds. No API keys needed.

## Tools

| Tool | What it does |
|---|---|
| `get_europe_tech_news` | Top recent stories. Filter by `region`, `topic`, `days`, `limit`. |
| `search_europe_tech_news` | Keyword search (e.g. `Mistral`, `Digital Markets Act`, `ASML`). |
| `get_source_news` | Latest from one outlet (Sifted, Tech.eu, Heise, ...). |
| `list_sources` | Configured feeds, regions and topics. |

Regions: `europe`, `eu`, `uk`, `ireland`, `germany`/`dach`, `france`, `benelux`/`netherlands`, `nordics`/`scandinavia`, `spain`/`iberia`.
Topics: `ai`, `funding`, `regulation`, `security`, `cloud`, `semiconductors`, `fintech`, `climate`, `startups`, or any free keyword.

Sources include Tech.eu, EU-Startups, Sifted, The Next Web, Euractiv, Politico Europe, The Register, Computer Weekly, Silicon Republic, Heise, Maddyness, Silicon Canals and Nordic9. Edit `src/europe_tech_news/feeds.py` to add more.

## Install

```bash
pip install git+https://github.com/MAVRICK-1/europe-tech-news-mcp
```

### Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "europe-tech-news": {
      "command": "europe-tech-news-mcp"
    }
  }
}
```

Claude Code one-liner:

```bash
claude mcp add europe-tech-news -- europe-tech-news-mcp
```

### Docker

```bash
docker build -t europe-tech-news-mcp .
claude mcp add europe-tech-news -- docker run -i --rm europe-tech-news-mcp
```

## Behaviour

- Feeds are fetched concurrently with a 10s timeout and cached for 10 minutes.
- A failing feed never breaks a request. It is reported under `errors` in the result.
- Results are deduplicated by canonical URL and normalized title, sorted newest first.
- Only `http(s)` links are returned. XML with DTD entity declarations is rejected.
- Summaries are short snippets. Link back to the original article when you use them.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
