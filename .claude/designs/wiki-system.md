---
type: service
name: wiki-system
step: 1
status: in-progress
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

EntryType = Literal[
    "character", "episode", "arc", "breathing_style",
    "blood_demon_art", "location", "organization",
]

class WikiPage(BaseModel):
    entry_type: EntryType
    path: str                # repo-relative path; validator rejects absolute paths
    frontmatter: dict[str, Any]
    body: str
    # helpers: to_markdown(), file_name()

class IndexEntry(BaseModel):
    title: str
    path: str
    entry_type: EntryType
    summary: str             # one-line only — token budget constraint
    # helpers: to_markdown_link(), matches_path(path)

class WikiIndex(BaseModel):
    entries: list[IndexEntry]
    last_updated: datetime
    # helpers: is_stale(log_updated_at), find_by_type(t), find_by_path(p)

LogOperation = Literal["ingest", "lint"]

class LogEntry(BaseModel):
    timestamp: datetime
    operation: LogOperation
    source: str | None       # URL/identifier; None for lint entries
    created: list[str]       # repo-relative paths created during this event
    updated: list[str]       # repo-relative paths updated during this event
    summary: str

class WikiLog(BaseModel):
    entries: list[LogEntry]
    # helpers: latest_timestamp(), count_episodes(), has_source(s), append(entry)
```

Result models (`IngestResult`, `QueryResult`, `LintResult`) carry small convenience helpers:
- `IngestResult.total_pages_touched()`, `is_empty()`
- `QueryResult.split_for_telegram()` (uses `TELEGRAM_MESSAGE_LIMIT` from `wiki_agent.constants`), `has_sources()`; `new_page_filed` defaults to `False`
- `LintResult.has_issues()`, `fix_rate()`

Shared constants (e.g. `TELEGRAM_MESSAGE_LIMIT`) live in `services/wiki-agent/src/wiki_agent/constants.py`.

### Category taxonomy (single source of truth)

The seven entry types appear in three different shapes across the wiki: as a type
literal, as a display section heading in `index.md`, and as a filesystem path
segment under `wiki/`. To avoid duplicating that taxonomy, all three views are
defined once in `services/wiki-agent/src/wiki_agent/utils/wiki_layout.py`:

```python
EntryType = Literal["character", "episode", "arc", "breathing_style",
                    "blood_demon_art", "location", "organization"]

@dataclass(frozen=True)
class WikiCategory:
    entry_type: EntryType
    section: str        # heading in index.md (e.g. "Characters")
    path_segment: str   # repo path piece (e.g. "characters")

WIKI_CATEGORIES: tuple[WikiCategory, ...] = (...)  # one per EntryType

def entry_type_for_section(section: str) -> EntryType | None: ...
def entry_type_for_path_segment(segment: str) -> EntryType | None: ...
def section_for(entry_type: EntryType) -> str: ...
def path_prefix_for(entry_type: EntryType) -> str: ...  # "wiki/<segment>/"
```

`models.py`, `index_md.py`, `wiki_page_md.py`, and `WikiLog.count_episodes()`
all read from these helpers — adding a new entry type touches exactly one place.

### `index.md` on-disk format

```markdown
---
last_updated: 2026-05-11T14:30:00
---

# Wiki Index

## Characters
- [Tanjiro Kamado](wiki/characters/tanjiro.md) — Protagonist demon slayer

## Episodes
- [Episode 1](wiki/episodes/01.md) — Cruelty
```

- Frontmatter holds `last_updated` (ISO-8601). Required — parser raises if missing.
- `## <Section>` heading maps to `entry_type`:
  Characters→character, Episodes→episode, Arcs→arc, Breathing Styles→breathing_style,
  Blood Demon Arts→blood_demon_art, Locations→location, Organizations→organization.
- Each bullet uses `IndexEntry.to_markdown_link()` format.
- Empty sections are omitted on serialize; absent sections parse as zero entries.
- Parser/serializer: `services/wiki-agent/src/wiki_agent/index_md.py`
  - `parse_index(content: str) -> WikiIndex`
  - `serialize_index(index: WikiIndex) -> str`

### `log.md` on-disk format

```markdown
## 2026-05-12T14:30:00+00:00 — ingest
- source: https://demonslayer.fandom.com/wiki/Tanjiro
- created: wiki/characters/tanjiro.md
- updated: wiki/episodes/01.md, wiki/arcs/mugen-train.md
- summary: Mugen Train arc introduction

## 2026-05-12T15:00:00+00:00 — lint
- summary: Season 1 lint complete — 3 issues fixed
```

- Each entry starts with `## <ISO-8601 timestamp> — <operation>`. `<operation>` is one of `ingest` | `lint`.
- Body is `- key: value` bullets. Fields: `source` (omitted for lint), `created`, `updated` (both comma-separated path lists; omitted when empty), `summary` (required).
- Entries are separated by a single blank line. Append-only — oldest first, newest at the bottom.
- A corrupted/unparsable file is read as an empty `WikiLog` (error logged) but **never overwritten** — the next append preserves the original bytes and adds the new entry after them.
- Parser/serializer: `services/wiki-agent/src/wiki_agent/log_md.py`
  - `parse_log(content: str) -> WikiLog`
  - `serialize_log(log: WikiLog) -> str`
  - `append_entry(content: str, entry: LogEntry) -> str` — append-only writer that avoids re-parsing the whole file on every event.

### Wiki page on-disk format

Each entry under `wiki/<category>/<file>.md` is YAML frontmatter (key-value pairs only, no nesting) followed by markdown body. Parser/serializer: `services/wiki-agent/src/wiki_agent/wiki_page_md.py` — `parse_page(path, content)` infers `entry_type` from the path's category segment via `wiki_layout`. `WikiPage.to_markdown()` is the writer.

## Storage Abstraction

`WikiRepo` is a `typing.Protocol` that decouples the orchestrator from any specific
backend. Defined in `services/wiki-agent/src/wiki_agent/wiki_repo.py`:

```python
class WikiRepo(Protocol):
    def read_index(self) -> WikiIndex: ...
    def write_index(self, index: WikiIndex) -> None: ...
    def read_page(self, path: str) -> WikiPage: ...
    def write_page(self, page: WikiPage) -> None: ...
    def list_page_paths(self) -> list[str]: ...
    def read_log(self) -> WikiLog: ...                  # graceful: empty on missing/corrupt
    def append_log_entry(self, entry: LogEntry) -> None: ...
```

- `FilesystemWikiRepo(root: Path)` — local filesystem backend, used for tests and local-only operation. Composition root (CLI / MCP bootstrap) supplies the root path via dependency injection; no env reads inside the class.
- `GithubWikiRepo` — to be added when wiring the public-facing service. Same Protocol, different I/O. (Closes the original "PyGithub vs raw httpx" open question — the choice is now isolated behind this Protocol and either library can implement it without touching callers.)

## Internal Package Layout

```
services/wiki-agent/src/wiki_agent/
  constants.py        # cross-cutting constants (TELEGRAM_MESSAGE_LIMIT, ...)
  models.py           # Pydantic models: WikiPage, IndexEntry, WikiIndex,
                      #                  LogEntry, WikiLog, IngestResult, ...
  index_md.py         # parse_index / serialize_index
  log_md.py           # parse_log / serialize_log / append_entry
  wiki_page_md.py     # parse_page
  wiki_repo.py        # WikiRepo Protocol + FilesystemWikiRepo
  utils/
    frontmatter.py    # split_frontmatter / parse_fields (shared by index + page)
    wiki_layout.py    # EntryType + WIKI_CATEGORIES taxonomy + lookups
```

Tests sit under `services/wiki-agent/tests/`, one `test_<module>.py` per source module (TDD enforcement hook). `tests/conftest.py` holds shared fixtures.

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
  - GitHub API client — `PyGithub` or raw `httpx`; deferred decision, isolated behind `WikiRepo` Protocol (see Storage Abstraction).
  - ~~`python-frontmatter`~~ — not used. Frontmatter is hand-rolled in `utils/frontmatter.py` because index.md and wiki pages only need flat `key: value` parsing; pulling a dependency for ~30 lines of code wasn't worth it.

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

## Implementation Progress

Built in chunked TDD order; each chunk landed with full pytest / mypy / ruff / pylint coverage.

- [x] **Layer 0 — Data models** (`models.py`): `WikiPage`, `IndexEntry`, `WikiIndex`, `LogEntry`, `WikiLog`, `IngestResult`, `QueryResult`, `LintResult`.
- [x] **Layer 0 — Taxonomy** (`utils/wiki_layout.py`): `EntryType`, `WIKI_CATEGORIES`, section/path-segment lookups.
- [x] **Layer 1 — Parsers / serializers**: `utils/frontmatter.py`, `index_md.py`, `log_md.py` (incl. `append_entry`), `wiki_page_md.py`.
- [x] **Layer 2 — Storage abstraction** (`wiki_repo.py`): `WikiRepo` Protocol + `FilesystemWikiRepo`. Graceful `read_log`. `GithubWikiRepo` pending.
- [ ] **Layer 3 — Orchestrators**: `wiki_ingest`, `wiki_query`, `wiki_lint`. Needs a Claude client + a URL fetcher.
- [ ] **Layer 4 — Service edges**: MCP server (FastMCP), Telegram long-polling bot, Docker Compose deployment.
- [ ] **Content repo bootstrap**: 7 entry-type templates + `AGENTS.md` in the `demon-slayer-wiki` content repo.

The integration test scenarios below (T1–T8) exercise Layer 3 + 4 and will be written when those layers land. Layers 0–2 are covered by unit tests in `services/wiki-agent/tests/`.

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
| `log.md` missing or corrupted | Fresh repo, or hand-edited / partially-written file | `WikiRepo.read_log()` returns an empty `WikiLog` and emits a `logging` line (INFO for missing, ERROR for corrupted). On-disk content is never overwritten — the next `append_log_entry` preserves the existing bytes and adds the new entry after them, so a corrupted log can be fixed by hand without losing the recovery entry. |

## Out of Scope

- Multi-user access (single owner only, enforced by `TELEGRAM_USER_ID`)
- File upload ingestion (v1 — URL and free text only)
- Automatic episode schedule tracking (season boundary is episode count only)
- Obsidian or any local editor integration
- Any series other than Demon Slayer in v1 (config extension is v2)
- Cloud deployment (Docker Compose locally only in v1)

## Open Questions

- [x] ~~Which GitHub library: `PyGithub` (higher-level) or raw `httpx` to GitHub REST API (fewer deps)?~~ **Deferred:** the choice is now isolated behind the `WikiRepo` Protocol. Pick when implementing `GithubWikiRepo`; callers are unaffected.
- [ ] Should `AGENTS.md` in the wiki repo be committed manually once, or auto-generated by the MCP server on bootstrap?
- [ ] Token threshold for chunking: 6K tokens per chunk (leaves room for index + system prompt in 64K context) — confirm?
