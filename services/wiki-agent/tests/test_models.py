"""Tests for wiki data models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from wiki_agent.models import (
    IngestResult,
    QueryResult,
    WikiIndex,
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
