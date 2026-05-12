---
id: 0004
title: read-log-degrades-gracefully-never-overwrites-corrupted-content
status: accepted
date: 2026-05-12
scope: wiki-system
superseded_by:
---

# 0004 — `read_log` degrades gracefully; `append_log_entry` never overwrites corrupted content

## Context
When designing `FilesystemWikiRepo`, the question came up: what should `read_log()` do if `log.md` is missing or corrupted (malformed timestamp, partial write, hand-edit)? The default in most file APIs is to raise. The user explicitly steered the behaviour: *"For read_log, I dont want the process to stop (user to see an error if logging fails but it should be logged for me to verify)."*

Availability over strict consistency: the ingest pipeline should not halt because the log file is in a weird state, but the operator must be able to find out *that* it was in a weird state.

## Decision
- `FilesystemWikiRepo.read_log()` returns an empty `WikiLog(entries=[])` on both **missing** and **corrupted** files. It does *not* raise. It emits a stdlib `logging` message: `INFO` for missing (first-run case), `ERROR` for corruption with the exception detail.
- `FilesystemWikiRepo.append_log_entry()` preserves the existing on-disk content **verbatim** when reading it back fails — it appends after the existing bytes rather than rewriting from a parsed (and possibly empty) `WikiLog`. A corrupted log is therefore never silently destroyed; the operator can repair it by hand without losing the recovery entry.
- The asymmetry with `read_index()` (which *does* raise `FileNotFoundError`) is intentional: a missing log means "no events yet" (valid initial state); a missing index means "you need to rebuild from `list_page_paths()`" (an error the caller must handle explicitly).

## Consequences
- **Positive:** Ingest pipeline keeps running across log corruption. Operator gets actionable telemetry via `logging`. Repair is non-destructive — fix the file by hand, future appends keep working.
- **Negative / tradeoffs:** Callers reading the log can't tell from the return value whether the log was missing vs corrupted vs genuinely empty — they have to inspect the log stream. For now, the only consumer that cares (`WikiLog.count_episodes()`) treats all three the same way (count is 0), so this is fine.
- **Followups:** If a consumer later needs to distinguish empty-vs-corrupt (e.g. a `wiki_repair` command), expose the failure mode via a separate method, not by changing `read_log()`'s contract.

## Alternatives considered
- **Raise on corruption, return empty on missing.** Rejected: the user explicitly prioritised availability over loud failure for log corruption.
- **Raise on both.** Cleaner contract but forces every caller to handle "first run" explicitly. Wrong for an append-only log that legitimately starts empty.
- **Return empty on both, silently.** Rejected: silent corruption is the worst failure mode — operator never knows.
