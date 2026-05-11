# Project Memory

Living document of best practices, decisions, and conventions for this project.
Updated as we discover and agree on new standards. Auto-read by Claude Code every session.

---

## Python Packaging

### `__init__.py` conventions
- **`tests/__init__.py`** — always empty. Marker file only; pytest uses it for test discovery.
- **`src/<package>/__init__.py`** — always empty for application services.
  - Do NOT add re-exports until there is a clear public API need.
  - If this becomes a library, curate the public API here with explicit re-exports + `__all__`.
  - `__version__` is acceptable here if needed.
  - Consumers import from submodules directly: `from wiki_agent.agent import WikiAgent`

---

## Docstring & Comment Conventions

### Module docstrings
Every `.py` file we create (e.g. `agent.py`, `wiki.py`) gets a single-line docstring at the top.
`__init__.py` files are exempt — they stay empty.

```python
"""Short description of what this module does."""
```

### Function / method docstrings — NumPy style
Every public function and method must have a NumPy-style docstring with all applicable sections:

```python
def fetch_entry(title: str, max_tokens: int = 512) -> WikiEntry:
    """Fetch a wiki entry by title from the store.

    Parameters
    ----------
    title : str
        The exact title of the wiki entry to retrieve.
    max_tokens : int, optional
        Maximum tokens to include in the returned entry body, by default 512.

    Returns
    -------
    WikiEntry
        The retrieved wiki entry with title, body, and metadata.

    Raises
    ------
    EntryNotFoundError
        If no entry with the given title exists in the store.
    ValueError
        If `max_tokens` is less than or equal to zero.
    """
```

Rules:
- One-line summary on the first line (imperative mood: "Fetch", "Update", "Run").
- Include `Parameters`, `Returns`, and `Raises` sections whenever they apply.
- Omit a section entirely if it does not apply (e.g. no `Returns` for `None`-returning functions).
- Private helpers (`_prefixed`) follow the same NumPy docstring rules as public functions.

---

## Code Organisation

### Function ordering within a file
Public functions and methods first, private helpers (`_prefixed`) at the bottom.
Readers see the interface before implementation details.

### Private functions
- Defined at the bottom of the file / class.
- Never imported from another module. Private means private to the module.

### Design principles
- **SOLID** — single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion.
- **DRY** — no duplicated logic; extract shared behaviour into a named function.
- **Python best practices** — type hints everywhere, prefer dataclasses/Pydantic models over raw dicts, use `pathlib` over `os.path`.

---

## Development Workflow — TDD (RED / GREEN)

All implementation follows strict RED → GREEN TDD:

1. **RED** — write a failing test that describes the real-world behaviour first. No implementation yet.
2. **GREEN** — write the minimal code that makes the test pass. No extra logic.
3. **REFACTOR** — clean up while keeping tests green.

### Test quality rules
- Tests must cover **real-world scenarios** — actual inputs, edge cases, and failure modes that will occur in production.
- No contrived tests (e.g. `assert 1 + 1 == 2`, trivial round-trips that test nothing meaningful).
- Each test should have a single, clear reason to fail.
- Use descriptive test names: `test_fetch_entry_raises_when_title_missing` not `test_error`.

### Code review pace
- Claude writes code in **small, reviewable chunks** — one logical unit at a time.
- No skeletons / signature-only stubs. Each chunk is real, tested, working code.
- Wait for explicit approval before moving to the next chunk.

---

## Document Driven Design (DDD)

Before implementing any non-trivial feature or module, a design doc must be created and approved.
Template lives at `.claude/designs/_template.md` — copy it, fill it, get sign-off, then code.

### Workflow
1. **Two-phase questioning** before writing anything:
   - **Phase 1 — Exploration**: Ask open questions to help the user discover what they want. Continue as long as the user is still pivoting or undecided. Do not ask implementation-detail questions yet.
   - **Phase 2 — Finalisation** (once direction is clear): Ask exactly 3 targeted rounds:
     - Round 1: gaps and ambiguities surfaced by exploration
     - Round 2: edge cases and failure modes
     - Round 3: constraints (scale, security, ops, cost)
   - After Round 3: ask *"Want to dig deeper, or shall we proceed to the design doc?"*
   - If dig deeper → continue targeted rounds, repeat the question after each.
   - If proceed → move to step 2.
2. Copy `_template.md` → `.claude/designs/<name>.md` and fill every section.
3. Get explicit sign-off before writing any implementation code.
4. Implement against the doc. Update the doc if design changes — doc stays the source of truth.
5. Set `status: done` when the feature is complete.

The same two-phase flow applies to `STRATEGY.md`.

### Frontmatter rules
- `type`: `feature` | `model` | `service` | `tool` | `refactor`
- `step`: integer ordering (1, 2, 3…) — for human reading only
- `depends_on`: list of other design doc **names** (not step numbers) — e.g. `[wiki-entry-model]`
- `status`: `draft` → `in-progress` → `done` (or `abandoned` with a reason note)

### Stable IDs
Test scenarios in design docs use T-IDs (T1, T2…) that never renumber — gaps from deletion are fine.
T-IDs live only in the design doc as scenario references. Test function names use plain descriptive snake_case:
`test_fetch_entry_returns_entry`, not `test_T1_fetch_entry_returns_entry`.

### Hard rules
- Before starting any implementation task, automatically scan `.claude/designs/` for a doc whose
  name matches the feature. If one exists, read it in full before writing a single line of code.
  The user should never have to say "read the design doc" — Claude does it proactively.
- All file paths in design docs are **repo-relative only** — never absolute paths.
- No implementation code in design docs — signatures and intent only.
- `depends_on` is enforced: do not start a step if its dependency is not `done`.

---

## Solution Docs (.claude/solutions/)

Solution docs are created automatically by Claude — the user never has to ask.

**Trigger:** The moment a design doc is marked `status: done`, immediately:
1. Read the completed `.claude/designs/<name>.md` for what was intended
2. Read the files touched during implementation for what was actually built
3. Copy `.claude/solutions/_template.md` → `.claude/solutions/<topic>.md`
4. Fill every section — purpose, root cause (if a bug), solution, validation, prevention
5. Present to the user for a quick review, then save

The user's only job is to provide the requirement. Claude handles the rest.

Status values:
- `status: current` — actively relevant, follow the patterns in it
- `status: archived` — superseded but kept for history
- `status: deprecated` — pattern actively discouraged now

These compound over time. Each doc makes the next feature faster to build.

---

## Architecture Decisions

_To be added._
