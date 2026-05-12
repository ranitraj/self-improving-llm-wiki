---
id: 0003
title: introduce-wiki-repo-protocol-with-filesystem-backend-first
status: accepted
date: 2026-05-12
scope: wiki-system
superseded_by:
---

# 0003 — Introduce a `WikiRepo` Protocol with a filesystem backend first

## Context
The original architecture diagram in `designs/wiki-system.md` showed the MCP server calling the GitHub API directly to commit pages. That coupling made it hard to:
- Test ingest/query/lint without a real GitHub token,
- Defer the still-open question of `PyGithub` vs raw `httpx`,
- Develop end-to-end locally before the public wiki repo is bootstrapped.

The user agreed to abstracting storage when offered the choice.

## Decision
Define `WikiRepo` as a `typing.Protocol` in `services/wiki-agent/src/wiki_agent/wiki_repo.py`, with seven methods: `read_index` / `write_index`, `read_page` / `write_page`, `list_page_paths`, `read_log`, `append_log_entry`. Ship one concrete impl now — `FilesystemWikiRepo(root: Path)` — backed by the local filesystem and constructed via dependency injection from the composition root (CLI / MCP bootstrap reads `WIKI_REPO`-style env vars; the class itself reads nothing from env).

`GithubWikiRepo` will land later as a drop-in implementation when the public service is wired.

## Consequences
- **Positive:** Orchestrators (ingest/query/lint) program against the Protocol; tests use the filesystem backend with `tmp_path` fixtures — no network, no auth. The `PyGithub` vs `httpx` choice is now isolated behind one interface and can be decided when GithubWikiRepo is implemented.
- **Negative / tradeoffs:** A small layer of indirection. One Protocol + one impl is overhead compared to "just call httpx directly." Justified by the testability win.
- **Followups:** Implement `GithubWikiRepo`. Once it exists, decide `PyGithub` vs raw `httpx` (and write a follow-up ADR if the choice was non-obvious). Closes Open Question #1 in the design doc.

## Alternatives considered
- **Direct GitHub calls in the orchestrator.** Rejected: forces every test to mock the GitHub client and blocks local development without auth.
- **`abc.ABC` instead of `typing.Protocol`.** Rejected: structural typing fits better — backends don't share implementation, they share a shape. No reason to force inheritance.
