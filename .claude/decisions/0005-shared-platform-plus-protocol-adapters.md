---
id: 0005
title: split-into-shared-platform-plus-protocol-adapter-services
status: accepted
date: 2026-05-18
scope: wiki-system
superseded_by:
---

# 0005 — Split into a shared platform (`wiki-agent`) + protocol-adapter services (`wiki-mcp`, `hermes`)

## Context

Layer 4 of the design needs two entry points to the same wiki logic:
- An **MCP server** (FastMCP) exposing `wiki_ingest` / `wiki_query` / `wiki_lint` for Claude Desktop.
- A **Telegram bot** (`hermes`) wrapping the same operations behind long-polling Telegram commands.

Naïve options:
1. **Modular monolith** — everything in one Python process, `wiki-agent` contains both the MCP server and the Telegram bot as submodules. Simplest, but the user explicitly wants independent deploy/restart cycles as deployment-learning.
2. **Pure microservices** — duplicate models, parsers, and orchestrator logic into each service. Communication via HTTP/gRPC contracts only. Standard counsel against this in shared-domain cases is strong (see Alternatives below).
3. **Shared platform + protocol adapters** — one shared library (`wiki-agent`) owns the domain (orchestrators, models, parsers, repo abstraction); each adapter service (`wiki-mcp`, `hermes`) is a thin process that imports the platform and exposes one protocol.

Option 3 fits this project because both planned services interact with **the same domain** through **different protocols**. That is exactly the case where shared-library concerns (tight coupling, version skew, "shared lib makes services hard to change independently") *do not apply* — both services legitimately need the same `WikiPage`, `IngestResult`, etc. Diverging copies would be a bug, not a feature.

## Decision

Adopt the **shared-platform + protocol-adapter** layout:

```
services/
  wiki-agent/         # the shared PLATFORM: orchestrators, models, parsers,
                      # repo abstraction, ClaudeClient + UrlFetcher Protocols.
                      # No HTTP, no long-polling, no protocol-specific code.
  wiki-mcp/           # FastMCP adapter. Imports wiki-agent. Exposes
                      # wiki_ingest/wiki_query/wiki_lint via MCP.
  hermes/             # Telegram bot adapter. Imports wiki-agent.
                      # Long-polls Telegram and maps commands → wiki-agent calls.
```

Each adapter is independently deployable (own Docker image, own restart cycle). They share the domain via the `wiki-agent` package — *one source of truth for `WikiPage`, `IngestResult`, etc.*

Naming clarifications:
- `wiki-agent` is the **platform / shared library**, despite the historical name carrying "agent". The actual "agents" (in the user-facing sense) are the adapter services.
- Each adapter's package name matches its domain: `wiki_mcp` (FastMCP adapter), `hermes` (Telegram agent).

The dep mechanism (uv workspaces vs path-based deps) is **deferred** — it will be decided when the first adapter gets real code in Layer 4. This ADR commits to the *architecture*, not the build-tooling.

## Consequences

- **Positive**:
  - Independent deploy: `wiki-mcp` and `hermes` can restart on their own cadence.
  - One source of truth for the domain: changing `WikiPage` updates everywhere atomically.
  - The platform stays protocol-agnostic; it's testable without booting a server.
  - User gets real multi-service deployment learning (Dockerfiles, compose, per-service logs) without paying the "duplicate everything" cost of pure microservices.
- **Negative / tradeoffs**:
  - Tighter coupling between adapters than pure microservices — a breaking change to `wiki-agent` requires re-deploying both adapters. Mitigated by versioning the platform.
  - More moving parts than a monolith (three services to wire up, run, monitor).
  - The "platform vs adapter" boundary needs discipline: protocol-specific code must not leak into `wiki-agent`. Code review enforces this.
- **Followups**:
  - When the first adapter (`wiki-mcp` or `hermes`) gets real code in Layer 4, write a follow-up ADR for the dep mechanism choice (uv workspaces vs path deps).
  - Add Dockerfiles per service and a `docker-compose.yml` alongside that work.

## Alternatives considered

- **Modular monolith** — Rejected: the user explicitly wants to learn independent deployment, and Layer 4 already calls for two distinct edge components with different lifecycles (an MCP server tied to Claude Desktop's process model; a long-polling Telegram bot). Forcing them into one process trades real learning for marginal simplicity.
- **Pure microservices (no shared lib)** — Rejected: this is the variant the "don't create shared libraries" school argues against ([Ryan Krull, *Microservices — Don't Create Shared Libraries*](https://medium.com/standard-bank/microservices-dont-create-shared-libraries-2e803b033552)). Those arguments apply when services have **different domains** that accidentally share code (a `User` model copy-pasted across teams). They do *not* apply here, where both services target the **same domain** through different protocols — diverging `WikiPage` copies would be a bug. [Duda's *Shared Libraries — Design and Best Practices*](https://medium.com/duda/shared-libraries-design-and-best-practices-710774ae0bdc) and the broader community consensus both endorse shared libraries for cross-cutting concerns and shared-domain cases.
- **uv workspaces vs path deps right now** — Deferred. The architectural commitment is independent of the dep mechanism. Either approach satisfies this ADR; the choice gets its own ADR when an adapter has consumers.

## References

- [Building a Python Monorepo with uv (2026)](https://medium.com/@naorcho/building-a-python-monorepo-with-uv-the-modern-way-to-manage-multi-package-projects-4cbcc56df1b4) — current best practice for shared-platform Python monorepos.
- [FOSDEM 2026 — Modern Python monorepo with uv, workspaces, and shared libraries](https://fosdem.org/2026/schedule/event/WE7NHM-modern-python-monorepo-apache-airflow/) — Apache Airflow ships 120+ Python distributions from one repo, real-world scale precedent.
- [Anthropic claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python) — a public example of the shared-core + thin adapter pattern (the `claude-agent-sdk` wraps the core `anthropic-sdk-python` client).
