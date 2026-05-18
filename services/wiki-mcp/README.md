# wiki-mcp

**Protocol adapter** — FastMCP server exposing `wiki_ingest` / `wiki_query` / `wiki_lint` to Claude Desktop over the MCP protocol.

> **Status:** skeleton. Implementation lives on its own feature branch (`feat/wiki-mcp`) off `main`, branched once the `wiki-agent` platform is shipped. See [.claude/designs/wiki-system.md](../../.claude/designs/wiki-system.md) → "Implementation Progress" for the plan.

## What lives here

This service is a **thin adapter**. All wiki logic — orchestrators, models, parsers, storage abstraction — lives in [`services/wiki-agent/`](../wiki-agent/) (the shared platform). `wiki-mcp` imports `wiki-agent` and exposes three MCP tools that map 1:1 to the platform's orchestrator functions.

Planned contents (added on `feat/wiki-mcp`):

```
wiki-mcp/
  src/wiki_mcp/
    server.py          # FastMCP server entry point
    tools.py           # wiki_ingest_tool / wiki_query_tool / wiki_lint_tool
  tests/
    test_server.py
    test_tools.py
  pyproject.toml       # declares wiki-agent as a workspace/path dep
  Dockerfile
```

## Why a separate service

See [ADR 0005 — Shared platform + protocol-adapter services](../../.claude/decisions/0005-shared-platform-plus-protocol-adapters.md). Short version: this service has a different lifecycle from the Telegram bot (`hermes`) — Claude Desktop manages MCP servers as child processes; the bot is a long-polling daemon. Independent deploy, independent restart, but both share the same domain via the `wiki-agent` package.
