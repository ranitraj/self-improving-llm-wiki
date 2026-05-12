---
id: 0002
title: handroll-frontmatter-parser-no-python-frontmatter-dep
status: accepted
date: 2026-05-12
scope: wiki-system
superseded_by:
---

# 0002 — Hand-roll the frontmatter parser instead of adding `python-frontmatter`

## Context
The wiki-system design originally listed `python-frontmatter` as a dependency for parsing/writing YAML frontmatter in wiki pages and `index.md`. When implementing `index_md.py`, neither `python-frontmatter` nor `PyYAML` was installed yet, and the existing `WikiPage.to_markdown()` already hand-rolled the serialization side. Adding a transitive dependency for ~30 lines of code we control didn't feel justified.

## Decision
Hand-roll a small `services/wiki-agent/src/wiki_agent/utils/frontmatter.py` module that exposes `split_frontmatter(content) -> (block, body)` and `parse_fields(block) -> dict[str, str]`. Both use plain `str.partition` / `str.splitlines` — no YAML parsing, just flat `key: value` lines. Values stay strings; type coercion is the caller's responsibility (e.g. `datetime.fromisoformat` in `parse_index`).

## Consequences
- **Positive:** Zero added third-party deps. Frontmatter parsing is fully testable in isolation (`tests/test_frontmatter.py`) and shared by `index_md.py`, `wiki_page_md.py`. The serializer side (`WikiPage.to_markdown()` and `serialize_index`) stays trivially compatible.
- **Negative / tradeoffs:** We don't parse nested YAML, lists, anchors, or quoted strings. The format is restricted to flat scalars — if the wiki ever needs richer frontmatter (lists in `arc.episodes`, for example), this decision needs revisiting.
- **Followups:** If a future entry-type template demands nested frontmatter, supersede this ADR with one that adopts `python-frontmatter` (or `tomllib`-style alternatives).

## Alternatives considered
- **Add `python-frontmatter`.** Rejected for v1: too much surface for what we need. Easy to add later if requirements grow.
