"""Tests for wiki data models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from wiki_agent.models import (
    IngestResult,
    LogEntry,
    QueryResult,
    WikiIndex,
    WikiLog,
    WikiPage,
)


def test_wiki_page_accepts_valid_entry_type() -> None:
    """Verify WikiPage accepts all seven known entry types without error."""
    page = WikiPage(
        entry_type="character",
        path="wiki/characters/tanjiro.md",
        frontmatter={"name": "Tanjiro Kamado"},
        body="## Summary\nProtagonist of Demon Slayer.",
    )
    assert page.entry_type == "character"


def test_wiki_page_rejects_invalid_entry_type() -> None:
    """Verify WikiPage raises ValidationError for an unrecognised entry type."""
    with pytest.raises(ValidationError):
        WikiPage(
            entry_type="villain",
            path="wiki/characters/muzan.md",
            frontmatter={},
            body="",
        )


def test_wiki_page_rejects_absolute_path() -> None:
    """Verify WikiPage raises ValidationError when path is absolute instead of repo-relative."""
    with pytest.raises(ValidationError):
        WikiPage(
            entry_type="character",
            path="/absolute/path/tanjiro.md",
            frontmatter={},
            body="",
        )


def test_wiki_index_is_stale_when_log_is_newer() -> None:
    """Verify is_stale returns True when the log has entries newer than the index."""
    index = WikiIndex(
        entries=[],
        last_updated=datetime(2026, 5, 1, tzinfo=UTC),
    )
    log_updated_at = datetime(2026, 5, 7, tzinfo=UTC)
    assert index.is_stale(log_updated_at) is True


def test_wiki_index_is_not_stale_when_up_to_date() -> None:
    """Verify is_stale returns False when the index is as recent as the log."""
    index = WikiIndex(
        entries=[],
        last_updated=datetime(2026, 5, 7, tzinfo=UTC),
    )
    log_updated_at = datetime(2026, 5, 1, tzinfo=UTC)
    assert index.is_stale(log_updated_at) is False


def test_ingest_result_separates_created_and_updated_pages() -> None:
    """Verify IngestResult stores created and updated page lists independently."""
    result = IngestResult(
        pages_created=["wiki/characters/rengoku.md"],
        pages_updated=["wiki/episodes/ep-001.md", "wiki/arcs/mugen-train.md"],
        log_entry="## [2026-05-07] ingest | Mugen Train arc",
    )
    assert len(result.pages_created) == 1
    assert len(result.pages_updated) == 2


def test_query_result_new_page_filed_defaults_to_false() -> None:
    """Verify QueryResult defaults new_page_filed to False when not provided."""
    result = QueryResult(
        answer="Rengoku is the Flame Hashira.",
        source_pages=["wiki/characters/rengoku.md"],
    )
    assert result.new_page_filed is False


def test_log_entry_rejects_unknown_operation() -> None:
    """Verify LogEntry only allows the two known operations."""
    with pytest.raises(ValidationError):
        LogEntry(
            timestamp=datetime(2026, 5, 12, 14, 30, tzinfo=UTC),
            operation="query",
            summary="not a valid log operation",
        )


def test_wiki_log_latest_timestamp_returns_none_when_empty() -> None:
    """Verify latest_timestamp returns None for a freshly initialised log."""
    assert WikiLog(entries=[]).latest_timestamp() is None


def test_wiki_log_latest_timestamp_returns_last_entry_timestamp() -> None:
    """Verify latest_timestamp returns the timestamp of the most recent entry (last in order)."""
    log = WikiLog(
        entries=[
            LogEntry(
                timestamp=datetime(2026, 5, 1, tzinfo=UTC),
                operation="ingest",
                source="https://example.com/a",
                created=["wiki/episodes/01.md"],
                summary="ep 1",
            ),
            LogEntry(
                timestamp=datetime(2026, 5, 7, tzinfo=UTC),
                operation="ingest",
                source="https://example.com/b",
                created=["wiki/episodes/02.md"],
                summary="ep 2",
            ),
        ]
    )
    assert log.latest_timestamp() == datetime(2026, 5, 7, tzinfo=UTC)


def test_wiki_log_count_episodes_dedupes_across_entries() -> None:
    """Verify count_episodes counts distinct episode paths across created and updated lists."""
    log = WikiLog(
        entries=[
            LogEntry(
                timestamp=datetime(2026, 5, 1, tzinfo=UTC),
                operation="ingest",
                source="https://example.com/a",
                created=["wiki/episodes/01.md", "wiki/characters/tanjiro.md"],
                summary="ep 1 + Tanjiro",
            ),
            LogEntry(
                timestamp=datetime(2026, 5, 2, tzinfo=UTC),
                operation="ingest",
                source="https://example.com/b",
                created=["wiki/episodes/02.md"],
                updated=["wiki/episodes/01.md"],
                summary="ep 2 + ep 1 update",
            ),
        ]
    )
    assert log.count_episodes() == 2


def test_wiki_log_has_source_detects_existing_ingest() -> None:
    """Verify has_source returns True for a URL already recorded and False otherwise."""
    log = WikiLog(
        entries=[
            LogEntry(
                timestamp=datetime(2026, 5, 1, tzinfo=UTC),
                operation="ingest",
                source="https://example.com/tanjiro",
                summary="t",
            ),
        ]
    )
    assert log.has_source("https://example.com/tanjiro") is True
    assert log.has_source("https://example.com/zenitsu") is False


def test_wiki_log_append_returns_new_log_without_mutating_original() -> None:
    """Verify append produces a new WikiLog and leaves the original entries list unchanged."""
    original = WikiLog(entries=[])
    entry = LogEntry(
        timestamp=datetime(2026, 5, 12, tzinfo=UTC),
        operation="lint",
        summary="Season 1 lint complete",
    )
    appended = original.append(entry)
    assert not original.entries
    assert appended.entries == [entry]
