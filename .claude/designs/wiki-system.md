---
type: service
name: wiki-system
step: 1
status: draft
depends_on: []
---

# Wiki System — Demon Slayer Self-Improving LLM Wiki

## Purpose
A self-improving, spoiler-aware personal wiki for Demon Slayer (Kimetsu no Yaiba) that ingests episode summaries and URLs via Telegram or CLI, synthesizes them into structured markdown pages using Claude, and serves them publicly via GitHub Pages — extensible to any media series via config.

## Problem
Fandom wikis spoil future episodes. Personal notes go stale and aren't cross-referenced. There is no tool that builds a rich, compounding knowledge base gated strictly to what you have already watched.

## Architecture

```
[Telegram]                    [Claude Desktop]
     │ long-polling                 │
     ▼                             │
[Telegram Bot (Python)]           │
     │ maps commands to MCP        │
     ▼                             ▼
[MCP Server — FastMCP]   ←────────┘
     │  wiki_ingest / wiki_query / wiki_lint
     ▼
[Claude API]
  Sonnet → ingest, lint (reasoning-heavy)
  Haiku  → query (fast, cheap)
     │
     ▼
[GitHub API]  →  commits to demon-slayer-wiki repo
                        │
                        ▼
               [GitHub Pages]  ←  public read-only site
```

## Wiki Repository Structure

```
demon-slayer-wiki/
  raw/                         # immutable source documents
  wiki/
    characters/
    episodes/
    arcs/
    breathing-styles/
    blood-demon-arts/
    locations/
    organizations/
  schema/
    AGENTS.md                  # LLM maintenance rules
    templates/                 # 7 entry type templates
  index.md                     # page catalog (summaries only, loaded every ingest)
  log.md                       # append-only chronological record
```

## Entry Types & Templates (7)

Each template has YAML frontmatter + fixed markdown sections. LLM fills them consistently.

| Type | Key frontmatter fields |
|---|---|
| `character` | name, status, affiliation, rank, breathing_style, blood_demon_art, first_appearance |
| `episode` | number, title, arc, key_characters |
| `arc` | name, episodes, location, key_characters |
| `breathing_style` | name, derived_from, users |
| `blood_demon_art` | name, user, moon_rank |
| `location` | name, region, arcs_featured |
| `organization` | name, leader, members |

## Core Operations

### Ingest
1. Receive source (URL or free text) from Telegram bot or CLI.
2. If URL: fetch and extract text. If page > token threshold, split at H2 headings and process chunks sequentially.
3. Load `index.md` (summaries only) to identify existing pages.
4. Call Claude Sonnet: synthesize source into page updates. Create new pages or update existing ones using the appropriate template.
5. Commit all changed pages to GitHub via API.
6. Append entry to `log.md`. Update `index.md`.
7. `log.md` is the source of truth — `index.md` is considered stale if its last-updated timestamp predates the latest log entry.
8. Check episode count from `log.md`. If Season 1 boundary (episode 26) is reached, auto-trigger Lint silently.

### Query
1. Receive question from Telegram or CLI.
2. Load `index.md` to find relevant page candidates.
3. Fetch those pages from GitHub.
4. Call Claude Haiku: synthesize answer from page content.
5. If answer surfaces new knowledge worth keeping, ingest it as a new page.
6. Return answer to Telegram (split across messages if > 4096 chars).

### Lint
1. Triggered automatically after episode 26 (Season 1 boundary), or manually.
2. Load all wiki pages.
3. Call Claude Sonnet: find contradictions, orphan pages, missing cross-references, pages that mention a character with no dedicated page.
4. Apply fixes: update pages, create missing pages, update `index.md`.
5. Append lint summary to `log.md`.
6. Send quiet notification to Telegram: "Season 1 lint complete — N issues fixed."

## Public API

```python
# services/wiki-agent/src/wiki_agent/mcp_server.py

async def wiki_ingest(source: str) -> IngestResult: ...
# source: URL or free text. Chunks large pages, updates wiki, updates index + log.

async def wiki_query(question: str) -> QueryResult: ...
# Returns synthesized answer. Files new page if answer is worth keeping.

async def wiki_lint() -> LintResult: ...
# Audits full wiki. Fixes contradictions, orphans, missing pages.
```

```python
# services/wiki-agent/src/wiki_agent/models.py

class IngestResult(BaseModel):
    pages_created: list[str]
    pages_updated: list[str]
    log_entry: str

class QueryResult(BaseModel):
    answer: str
    source_pages: list[str]
    new_page_filed: bool

class LintResult(BaseModel):
    issues_found: int
    issues_fixed: int
    pages_created: list[str]
    summary: str
```

## Data Models

```python
# services/wiki-agent/src/wiki_agent/models.py

class WikiPage(BaseModel):
    entry_type: str          # character | episode | arc | ...
    path: str                # repo-relative path e.g. wiki/characters/tanjiro.md
    frontmatter: dict        # parsed YAML frontmatter
    body: str                # markdown body content

class WikiIndex(BaseModel):
    entries: list[IndexEntry]
    last_updated: datetime

class IndexEntry(BaseModel):
    title: str
    path: str
    entry_type: str
    summary: str             # one-line only — token budget constraint
```

## Data Flow

**Ingest:** source → fetch/chunk → load index.md → Claude Sonnet → page diffs → GitHub commits → log.md + index.md update → season check → (optional) auto-lint

**Query:** question → load index.md → fetch relevant pages → Claude Haiku → answer → Telegram reply (chunked if needed) → (optional) ingest answer as new page

**Lint:** all pages → Claude Sonnet → fixes → GitHub commits → log.md entry → Telegram notification

## Dependencies

- **Internal**: none (this is the root service)
- **External**:
  - `anthropic` — Claude API (Sonnet + Haiku)
  - `fastmcp` — MCP server framework
  - `python-telegram-bot` — Telegram long-polling bot
  - `httpx` — URL fetching
  - `pydantic` — data models
  - `PyGithub` or raw `httpx` — GitHub API commits
  - `python-frontmatter` — parse/write YAML frontmatter in wiki pages

## Deployment

```yaml
# docker-compose.yml (repo root)
services:
  mcp-server:
    build: services/wiki-agent
    env_file: .env           # ANTHROPIC_API_KEY, GITHUB_TOKEN, WIKI_REPO
    ports:
      - "8000:8000"

  telegram-bot:
    build: services/wiki-agent
    command: python -m wiki_agent.telegram_bot
    env_file: .env           # TELEGRAM_BOT_TOKEN + above
    depends_on:
      - mcp-server
```

`.env` variables (never committed):
- `ANTHROPIC_API_KEY`
- `GITHUB_TOKEN` — fine-grained, scoped to wiki content repo only
- `WIKI_REPO` — e.g. `your-username/demon-slayer-wiki`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_USER_ID` — only this user ID can interact with the bot

## Test Scenarios

- **T1** — Given a valid fandom URL, when `wiki_ingest` is called, then at least one wiki page is created or updated and `log.md` gains a new entry.
- **T2** — Given a URL whose page is > token threshold, when `wiki_ingest` is called, then the page is chunked at H2 headings and all chunks are processed without error.
- **T3** — Given an existing page for Tanjiro, when `wiki_ingest` is called with a source mentioning Tanjiro, then the existing page is updated (not duplicated).
- **T4** — Given the same URL is ingested twice, when `wiki_ingest` is called the second time, then it is skipped silently and `log.md` is not modified.
- **T5** — Given a question about Rengoku, when `wiki_query` is called, then the answer references the correct source pages and is returned in under 4096 chars or split correctly.
- **T6** — Given 26 episode ingests have been logged, when the 26th ingest completes, then `wiki_lint` is triggered automatically with no user prompt.
- **T7** — Given `wiki_lint` runs, when orphan pages exist (mentioned in log but no dedicated page), then those pages are created and `index.md` is updated.
- **T8** — Given `index.md` last-updated timestamp is older than the latest `log.md` entry, when any operation loads the index, then it is rebuilt before use.

## Error Cases

| Error | Trigger | Handling |
|---|---|---|
| URL fetch fails (404, timeout) | Bad or unavailable URL | Return error to Telegram, do not modify wiki |
| Paywalled / empty page | Fetch succeeds but content is empty | Return error to Telegram, do not modify wiki |
| GitHub API commit fails | Rate limit or auth error | Retry once; if still failing, return error and leave wiki unchanged |
| Claude API error | Timeout or overload | Retry once with backoff; surface error to Telegram |
| Telegram message > 4096 chars | Long query answer | Split into sequential messages automatically |
| `index.md` stale | Log entry newer than index timestamp | Rebuild index from wiki directory before proceeding |

## Out of Scope

- Multi-user access (single owner only, enforced by `TELEGRAM_USER_ID`)
- File upload ingestion (v1 — URL and free text only)
- Automatic episode schedule tracking (season boundary is episode count only)
- Obsidian or any local editor integration
- Any series other than Demon Slayer in v1 (config extension is v2)
- Cloud deployment (Docker Compose locally only in v1)

## Open Questions

- [ ] Which GitHub library: `PyGithub` (higher-level) or raw `httpx` to GitHub REST API (fewer deps)?
- [ ] Should `AGENTS.md` in the wiki repo be committed manually once, or auto-generated by the MCP server on bootstrap?
- [ ] Token threshold for chunking: 6K tokens per chunk (leaves room for index + system prompt in 64K context) — confirm?
