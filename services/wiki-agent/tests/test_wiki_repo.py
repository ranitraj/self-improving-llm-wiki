"""Tests for the WikiRepo Protocol and the filesystem-backed implementation."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from wiki_agent.models import LogEntry, WikiIndex, WikiPage
from wiki_agent.wiki_repo import FilesystemWikiRepo, WikiRepo


def test_filesystem_repo_is_assignable_to_wiki_repo_protocol(tmp_path: Path) -> None:
    """Verify FilesystemWikiRepo structurally satisfies the WikiRepo Protocol (checked by mypy)."""
    repo: WikiRepo = FilesystemWikiRepo(tmp_path)
    assert isinstance(repo, FilesystemWikiRepo)


def test_write_page_then_read_page_round_trips(tmp_path: Path) -> None:
    """Verify writing a page then reading it back returns the same WikiPage."""
    repo = FilesystemWikiRepo(tmp_path)
    page = WikiPage(
        entry_type="character",
        path="wiki/characters/tanjiro.md",
        frontmatter={"name": "Tanjiro Kamado", "status": "alive"},
        body="## Summary\nProtagonist.",
    )

    repo.write_page(page)
    loaded = repo.read_page("wiki/characters/tanjiro.md")

    assert loaded == page


def test_write_page_creates_missing_parent_directories(tmp_path: Path) -> None:
    """Verify write_page silently creates wiki/<category>/ when it does not yet exist."""
    repo = FilesystemWikiRepo(tmp_path)
    page = WikiPage(
        entry_type="episode",
        path="wiki/episodes/01.md",
        frontmatter={"number": "1"},
        body="ep1",
    )

    repo.write_page(page)

    assert (tmp_path / "wiki" / "episodes" / "01.md").exists()


def test_read_page_raises_file_not_found_for_missing_page(tmp_path: Path) -> None:
    """Verify read_page raises FileNotFoundError when the page file does not exist."""
    repo = FilesystemWikiRepo(tmp_path)
    with pytest.raises(FileNotFoundError):
        repo.read_page("wiki/characters/missing.md")


def test_list_page_paths_returns_all_wiki_pages_sorted_with_posix_separators(tmp_path: Path) -> None:
    """Verify list_page_paths walks wiki/ recursively and returns sorted repo-relative POSIX paths."""
    repo = FilesystemWikiRepo(tmp_path)
    repo.write_page(
        WikiPage(entry_type="character", path="wiki/characters/zenitsu.md", frontmatter={"name": "Z"}, body="")
    )
    repo.write_page(
        WikiPage(entry_type="character", path="wiki/characters/tanjiro.md", frontmatter={"name": "T"}, body="")
    )
    repo.write_page(WikiPage(entry_type="episode", path="wiki/episodes/01.md", frontmatter={"number": "1"}, body=""))

    assert repo.list_page_paths() == [
        "wiki/characters/tanjiro.md",
        "wiki/characters/zenitsu.md",
        "wiki/episodes/01.md",
    ]


def test_list_page_paths_returns_empty_when_wiki_dir_missing(tmp_path: Path) -> None:
    """Verify list_page_paths handles a brand-new repo with no wiki/ subdirectory yet."""
    repo = FilesystemWikiRepo(tmp_path)
    assert repo.list_page_paths() == []


def test_write_index_then_read_index_round_trips(tmp_path: Path, wiki_index_with_tanjiro: WikiIndex) -> None:
    """Verify writing an index then reading it back preserves entries and last_updated timestamp."""
    repo = FilesystemWikiRepo(tmp_path)

    repo.write_index(wiki_index_with_tanjiro)
    loaded = repo.read_index()

    assert loaded == wiki_index_with_tanjiro


def test_read_index_raises_file_not_found_when_index_md_missing(tmp_path: Path) -> None:
    """Verify read_index surfaces FileNotFoundError so callers can decide to rebuild from disk."""
    repo = FilesystemWikiRepo(tmp_path)
    with pytest.raises(FileNotFoundError):
        repo.read_index()


def test_append_log_entry_then_read_log_returns_that_entry(tmp_path: Path, ingest_log_entry: LogEntry) -> None:
    """Verify appending a single entry to a fresh repo makes it visible via read_log."""
    repo = FilesystemWikiRepo(tmp_path)

    repo.append_log_entry(ingest_log_entry)

    assert repo.read_log().entries == [ingest_log_entry]


def test_append_log_entry_preserves_prior_entries_in_chronological_order(
    tmp_path: Path, ingest_log_entry: LogEntry, lint_log_entry: LogEntry
) -> None:
    """Verify successive appends keep older entries first and never rewrite history."""
    repo = FilesystemWikiRepo(tmp_path)

    repo.append_log_entry(ingest_log_entry)
    repo.append_log_entry(lint_log_entry)

    assert repo.read_log().entries == [ingest_log_entry, lint_log_entry]


def test_read_log_returns_empty_when_log_md_missing(tmp_path: Path) -> None:
    """Verify read_log gracefully returns an empty WikiLog on a fresh repo (no log.md yet)."""
    repo = FilesystemWikiRepo(tmp_path)
    assert not repo.read_log().entries


def test_read_log_returns_empty_and_logs_error_when_log_md_is_corrupted(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify read_log does not raise on a corrupted log; it logs an error and returns empty."""
    (tmp_path / "log.md").write_text("## not-a-valid-iso-timestamp — ingest\n- summary: broken", encoding="utf-8")
    repo = FilesystemWikiRepo(tmp_path)

    with caplog.at_level(logging.ERROR, logger="wiki_agent.wiki_repo"):
        log = repo.read_log()

    assert not log.entries
    assert any("log.md" in record.message for record in caplog.records)


def test_append_log_entry_preserves_corrupted_existing_content(tmp_path: Path) -> None:
    """Verify a corrupted log.md is not destroyed by append — the new entry is added at the end."""
    corrupted_text = "## not-a-valid-iso-timestamp — ingest\n- summary: broken"
    (tmp_path / "log.md").write_text(corrupted_text, encoding="utf-8")
    repo = FilesystemWikiRepo(tmp_path)
    new_entry = LogEntry(
        timestamp=datetime(2026, 5, 12, tzinfo=UTC),
        operation="lint",
        summary="recovery lint",
    )

    repo.append_log_entry(new_entry)

    on_disk = (tmp_path / "log.md").read_text(encoding="utf-8")
    assert corrupted_text in on_disk
    assert "## 2026-05-12T00:00:00+00:00 — lint" in on_disk
