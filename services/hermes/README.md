# hermes

**Protocol adapter** — Telegram bot agent. Long-polls Telegram for commands, maps them to `wiki-agent` orchestrator calls, and sends responses back to the chat.

> **Status:** skeleton. Implementation lives on its own feature branch (`feat/hermes`) off `main`, branched once the `wiki-agent` platform is shipped. See [.claude/designs/wiki-system.md](../../.claude/designs/wiki-system.md) → "Implementation Progress" for the plan.

## What lives here

This service is a **thin adapter**. All wiki logic — orchestrators, models, parsers, storage abstraction — lives in [`services/wiki-agent/`](../wiki-agent/) (the shared platform). `hermes` imports `wiki-agent` and forwards Telegram commands to the platform's orchestrator functions.

Planned contents (added on `feat/hermes`):

```
hermes/
  src/hermes/
    bot.py             # long-poll loop, command router
    handlers.py        # /ingest, /query, /lint command handlers
    formatting.py      # response chunking for TELEGRAM_MESSAGE_LIMIT
  tests/
    test_bot.py
    test_handlers.py
  pyproject.toml       # declares wiki-agent as a workspace/path dep
  Dockerfile
```

`TELEGRAM_USER_ID` (from `.env`) gates access — only the configured user can interact with the bot. See [.claude/designs/wiki-system.md](../../.claude/designs/wiki-system.md) → "Deployment" for the env-var contract.

## Why a separate service

See [ADR 0005 — Shared platform + protocol-adapter services](../../.claude/decisions/0005-shared-platform-plus-protocol-adapters.md). Short version: `hermes` is a long-running daemon (Telegram long-polling) with a different lifecycle from `wiki-mcp` (which runs as a child of Claude Desktop). Independent deploy and restart, but both share the same domain via the `wiki-agent` package.

## Why "hermes"

Greek messenger of the gods — the name fits a Telegram bot that ferries commands between user and wiki.
