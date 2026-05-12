"""Tests for the log.md parser and serializer."""

from datetime import UTC, datetime

from wiki_agent.log_md import parse_log, serialize_log
from wiki_agent.models import LogEntry, WikiLog


def test_parse_log_returns_empty_log_for_empty_content() -> None:
    """Verify parse_log treats an empty file as a zero-entry log rather than failing."""
    assert parse_log("") == WikiLog(entries=[])


def test_parse_log_extracts_ingest_and_lint_entries_in_order() -> None:
    """Verify parse_log reads multiple chronological entries with the right fields populated."""
    content = (
        "## 2026-05-01T10:00:00+00:00 — ingest\n"
        "- source: https://demonslayer.fandom.com/wiki/Tanjiro\n"
        "- created: wiki/characters/tanjiro.md\n"
        "- updated: wiki/episodes/01.md, wiki/arcs/mugen-train.md\n"
        "- summary: Mugen Train arc introduction\n"
        "\n"
        "## 2026-05-12T15:00:00+00:00 — lint\n"
        "- summary: Season 1 lint complete — 3 issues fixed\n"
    )

    log = parse_log(content)

    assert len(log.entries) == 2

    ingest = log.entries[0]
    assert ingest.operation == "ingest"
    assert ingest.timestamp == datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
    assert ingest.source == "https://demonslayer.fandom.com/wiki/Tanjiro"
    assert ingest.created == ["wiki/characters/tanjiro.md"]
    assert ingest.updated == ["wiki/episodes/01.md", "wiki/arcs/mugen-train.md"]
    assert ingest.summary == "Mugen Train arc introduction"

    lint = log.entries[1]
    assert lint.operation == "lint"
    assert lint.source is None
    assert lint.created == []
    assert lint.updated == []
    assert lint.summary == "Season 1 lint complete — 3 issues fixed"


def test_serialize_log_omits_empty_lists_and_missing_source() -> None:
    """Verify serialize_log skips bullet lines for empty page lists and absent source (lint entries)."""
    log = WikiLog(
        entries=[
            LogEntry(
                timestamp=datetime(2026, 5, 12, 15, 0, tzinfo=UTC),
                operation="lint",
                summary="Season 1 lint complete — 3 issues fixed",
            ),
        ]
    )

    output = serialize_log(log)

    assert output.startswith("## 2026-05-12T15:00:00+00:00 — lint\n")
    assert "- source:" not in output
    assert "- created:" not in output
    assert "- updated:" not in output
    assert "- summary: Season 1 lint complete — 3 issues fixed" in output


def test_round_trip_preserves_entries() -> None:
    """Verify a multi-entry log round-trips through serialize and parse with all fields intact."""
    original = WikiLog(
        entries=[
            LogEntry(
                timestamp=datetime(2026, 5, 1, 10, 0, tzinfo=UTC),
                operation="ingest",
                source="https://demonslayer.fandom.com/wiki/Tanjiro",
                created=["wiki/characters/tanjiro.md"],
                updated=["wiki/episodes/01.md"],
                summary="Tanjiro debut",
            ),
            LogEntry(
                timestamp=datetime(2026, 5, 7, 9, 0, tzinfo=UTC),
                operation="ingest",
                source="https://demonslayer.fandom.com/wiki/Rengoku",
                created=["wiki/characters/rengoku.md"],
                summary="Flame Hashira introduction",
            ),
            LogEntry(
                timestamp=datetime(2026, 5, 12, 15, 0, tzinfo=UTC),
                operation="lint",
                summary="Season 1 lint complete — 3 issues fixed",
            ),
        ]
    )

    assert parse_log(serialize_log(original)) == original
