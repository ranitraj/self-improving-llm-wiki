---
id: 0001
title: consolidate-entry-type-taxonomy-in-wiki-layout
status: accepted
date: 2026-05-12
scope: wiki-system
superseded_by:
---

# 0001 — Consolidate entry-type taxonomy in `utils/wiki_layout.py`

## Context
The seven wiki entry types appear in three different shapes across the codebase:
- as a `Literal` type used in models and validators,
- as a display section heading in `index.md` (e.g. `"Characters"`),
- as a filesystem path segment under `wiki/` (e.g. `"characters"`).

The first cut had a `_SECTION_TO_ENTRY_TYPE` dict in `index_md.py` and was about to add a parallel `_PATH_SEGMENT_TO_ENTRY_TYPE` dict in `wiki_page_md.py`, plus an `EPISODE_PATH_PREFIX` constant in `constants.py`. The user pushed back: *"I see we are using it everywhere in all files."* These were three views of the same taxonomy, keyed differently — invisible to grep but visible to a careful reader.

## Decision
Create `services/wiki-agent/src/wiki_agent/utils/wiki_layout.py` as the single source of truth. Export `EntryType` (Literal), a `WIKI_CATEGORIES: tuple[WikiCategory, ...]` table where each `WikiCategory` carries `(entry_type, section, path_segment)`, and four lookup helpers (`entry_type_for_section`, `entry_type_for_path_segment`, `section_for`, `path_prefix_for`). All consumers — `models.py`, `index_md.py`, `wiki_page_md.py`, `WikiLog.count_episodes()` — read from these helpers instead of carrying their own mapping.

## Consequences
- **Positive:** Adding a new entry type touches exactly one file. The taxonomy is testable independently (`tests/test_wiki_layout.py`). Display/filesystem/code views can never drift apart.
- **Negative / tradeoffs:** A `utils/` subpackage was introduced specifically for this, plus the related frontmatter helper. Mild import-graph complexity (models depends on utils.wiki_layout).
- **Followups:** None.

## Alternatives considered
- **Keep per-module dicts.** Rejected: pylint would not catch the duplication (different keys), and the next entry-type addition would require three edits without any safety net.
- **Put the mapping in `models.py` alongside `EntryType`.** Rejected: mixes display/filesystem concerns into the model layer.
