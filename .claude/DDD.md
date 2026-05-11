# Document Driven Design (DDD)

Before implementing any non-trivial feature or module, a design doc must be created and approved.
Template lives at `.claude/designs/_template.md` — copy it, fill it, get sign-off, then code.

## Workflow

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

## Frontmatter rules

- `type`: `feature` | `model` | `service` | `tool` | `refactor`
- `step`: integer ordering (1, 2, 3…) — for human reading only
- `depends_on`: list of other design doc **names** (not step numbers) — e.g. `[wiki-entry-model]`
- `status`: `draft` → `in-progress` → `done` (or `abandoned` with a reason note)

## Stable IDs

Test scenarios in design docs use T-IDs (T1, T2…) that never renumber — gaps from deletion are fine.
T-IDs live only in the design doc as scenario references. Test function names use plain descriptive snake_case:
`test_fetch_entry_returns_entry`, not `test_T1_fetch_entry_returns_entry`.

## Hard rules

- Before starting any implementation task, automatically scan `.claude/designs/` for a doc whose
  name matches the feature. If one exists, read it in full before writing a single line of code.
  The user should never have to say "read the design doc" — Claude does it proactively.
- All file paths in design docs are **repo-relative only** — never absolute paths.
- No implementation code in design docs — signatures and intent only.
- `depends_on` is enforced: do not start a step if its dependency is not `done`.
