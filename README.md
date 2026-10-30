# europe-tech-news-mcp

An MCP server that gives Claude (or any MCP client) current tech news from across Europe, pulled live from public RSS/Atom feeds. No API keys needed.

## Tools

| Tool | What it does |
|---|---|
| `get_top_eu_tech_news` | Ranked top stories (recency, outlet weight, multi-outlet coverage). Returns a ready-made markdown `table` (Heading, Context, Link). |
| `get_europe_tech_news` | Top recent stories. Filter by `region`, `topic`, `days`, `limit`. |
| `search_europe_tech_news` | Keyword search (e.g. `Mistral`, `Digital Markets Act`, `ASML`). |
| `get_source_news` | Latest from one outlet (Sifted, Tech.eu, Heise, ...). |
| `list_sources` | Configured feeds, regions and topics. |

Regions: `europe`, `eu`, `uk`, `ireland`, `germany`/`dach`, `france`, `benelux`/`netherlands`, `nordics`/`scandinavia`, `spain`/`iberia`, `italy`.
Topics: `ai`, `funding`, `regulation`, `security`, `cloud`, `bugs` (bugs, crashes, outages), `semiconductors`, `fintech`, `climate`, `startups`, or any free keyword.

Sources include Tech.eu, EU-Startups, Sifted, The Next Web, Euractiv, Politico Europe, European Commission Digital Strategy, The Register, Computer Weekly, ITPro, BBC, The Guardian, Silicon Republic, Heise, Golem, t3n, Netzpolitik, Maddyness, Silicon.fr, Le Monde Informatique, Computable, Il Sole 24 Ore, Silicon Canals and Nordic9. General outlets are filtered to Europe-related stories. Edit `src/europe_tech_news/feeds.py` to add more.

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

## Test with different clients

The server speaks MCP over stdio, so any MCP client works. In every config below, `command` can be an absolute path (for example `/path/to/venv/bin/europe-tech-news-mcp`) if the command is not on your `PATH`.

Good first prompts: "Top EU tech news today", "Latest cloud outages and bugs in Europe", "EU AI regulation news this week". Answers should come back as a table (Heading, Context, Link).

### Claude Code

```bash
claude mcp add europe-tech-news -- europe-tech-news-mcp
claude mcp list          # should show europe-tech-news as connected
```

### GitHub Copilot CLI

Run `/mcp add` in the CLI, or add to `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "europe-tech-news": { "type": "local", "command": "europe-tech-news-mcp", "args": [], "tools": ["*"] }
  }
}
```

Restart, then check `/mcp`.

### Gemini CLI

```bash
gemini mcp add europe-tech-news europe-tech-news-mcp
```

Or add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "europe-tech-news": { "command": "europe-tech-news-mcp" }
  }
}
```

Run `/mcp` inside Gemini CLI to confirm the tools are listed.

### Local models

Use a model with tool-calling support, such as Qwen 2.5/3, Llama 3.1+ or Mistral.

- **LM Studio** (0.3.17+): open *Program → Edit mcp.json* and add the same `mcpServers` block as above, then chat with a tool-capable model.
- **Ollama**: Ollama has no built-in MCP client, so use a bridge such as [mcphost](https://github.com/mark3labs/mcphost). Put the `mcpServers` block above in `~/.mcphost.json`, then run `ollama pull qwen2.5` and `mcphost -m ollama:qwen2.5`.

Small local models may ignore the table instruction. Ask for it explicitly: "show the results as a table with heading, context and link".

### Without any LLM (MCP Inspector)

```bash
npx @modelcontextprotocol/inspector europe-tech-news-mcp
```

Open the printed URL, then *Tools → List tools* and call `get_top_eu_tech_news` with `topic` set to `bugs` or `cloud`.

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
