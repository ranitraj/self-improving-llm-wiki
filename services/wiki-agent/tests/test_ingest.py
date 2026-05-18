"""Tests for the wiki_ingest orchestrator (Chunk 3.1 — text-only ingest)."""

from datetime import UTC, datetime
from pathlib import Path

from wiki_agent.ingest import wiki_ingest
from wiki_agent.models import WikiIndex, WikiPage
from wiki_agent.wiki_repo import FilesystemWikiRepo

from tests.stubs import StubClaudeClient


def test_wiki_ingest_writes_new_pages_when_source_yields_unknown_paths(tmp_path: Path) -> None:
    """Verify a fresh repo with one new synthesized page records it in pages_created and on disk."""
    repo = FilesystemWikiRepo(tmp_path)
    new_page = WikiPage(
        entry_type="character",
        path="wiki/characters/tanjiro.md",
        frontmatter={"name": "Tanjiro Kamado", "summary": "Protagonist demon slayer"},
        body="## Summary\nProtagonist of Demon Slayer.",
    )
    claude = StubClaudeClient(pages_to_return=[new_page])

    result = wiki_ingest(
        source="https://example.com/tanjiro",
        repo=repo,
        claude=claude,
        now=lambda: datetime(2026, 5, 18, 14, 30, tzinfo=UTC),
    )

    assert result.pages_created == ["wiki/characters/tanjiro.md"]
    assert not result.pages_updated
    assert repo.read_page("wiki/characters/tanjiro.md") == new_page


def test_wiki_ingest_updates_existing_page_rather_than_duplicating(
    tmp_path: Path, wiki_index_with_tanjiro: WikiIndex
) -> None:
    """Verify an ingest that returns a page whose path is already in the index counts as an update."""
    repo = FilesystemWikiRepo(tmp_path)
    original = WikiPage(
        entry_type="character",
        path="wiki/characters/tanjiro.md",
        frontmatter={"name": "Tanjiro Kamado", "summary": "Protagonist demon slayer"},
        body="Old body.",
    )
    repo.write_page(original)
    repo.write_index(wiki_index_with_tanjiro)
    refreshed = original.model_copy(update={"body": "## Summary\nProtagonist — now with Hinokami Kagura."})
    claude = StubClaudeClient(pages_to_return=[refreshed])

    result = wiki_ingest(
        source="https://example.com/tanjiro-v2",
        repo=repo,
        claude=claude,
        now=lambda: datetime(2026, 5, 18, 14, 30, tzinfo=UTC),
    )

    assert result.pages_updated == ["wiki/characters/tanjiro.md"]
    assert not result.pages_created
    assert repo.read_page("wiki/characters/tanjiro.md").body == "## Summary\nProtagonist — now with Hinokami Kagura."


def test_wiki_ingest_appends_log_entry_with_source_and_classification(tmp_path: Path) -> None:
    """Verify the log gains an ingest entry capturing the source URL and the created/updated split."""
    repo = FilesystemWikiRepo(tmp_path)
    new_page = WikiPage(
        entry_type="episode",
        path="wiki/episodes/01.md",
        frontmatter={"title": "Cruelty", "summary": "Tanjiro's family is killed"},
        body="ep1",
    )
    claude = StubClaudeClient(pages_to_return=[new_page])

    wiki_ingest(
        source="https://demonslayer.fandom.com/wiki/Episode_1",
        repo=repo,
        claude=claude,
        now=lambda: datetime(2026, 5, 18, 14, 30, tzinfo=UTC),
    )

    log = repo.read_log()
    assert len(log.entries) == 1
    entry = log.entries[0]
    assert entry.operation == "ingest"
    assert entry.source == "https://demonslayer.fandom.com/wiki/Episode_1"
    assert entry.created == ["wiki/episodes/01.md"]
    assert entry.updated == []
    assert entry.timestamp == datetime(2026, 5, 18, 14, 30, tzinfo=UTC)


def test_wiki_ingest_updates_index_with_new_entries(tmp_path: Path) -> None:
    """Verify the index gains an IndexEntry for each newly created page after ingest."""
    repo = FilesystemWikiRepo(tmp_path)
    new_page = WikiPage(
        entry_type="character",
        path="wiki/characters/zenitsu.md",
        frontmatter={"name": "Zenitsu Agatsuma", "summary": "Thunder Breathing user"},
        body="body",
    )
    claude = StubClaudeClient(pages_to_return=[new_page])

    wiki_ingest(
        source="https://example.com/zenitsu",
        repo=repo,
        claude=claude,
        now=lambda: datetime(2026, 5, 18, 14, 30, tzinfo=UTC),
    )

    index = repo.read_index()
    zenitsu = index.find_by_path("wiki/characters/zenitsu.md")
    assert zenitsu is not None
    assert zenitsu.title == "Zenitsu Agatsuma"
    assert zenitsu.entry_type == "character"
    assert zenitsu.summary == "Thunder Breathing user"
    assert index.last_updated == datetime(2026, 5, 18, 14, 30, tzinfo=UTC)


def test_wiki_ingest_handles_repo_without_prior_index_or_log(tmp_path: Path) -> None:
    """Verify ingest works on a brand-new repo where index.md and log.md do not yet exist."""
    repo = FilesystemWikiRepo(tmp_path)
    new_page = WikiPage(
        entry_type="arc",
        path="wiki/arcs/final-selection.md",
        frontmatter={"name": "Final Selection", "summary": "Demon Slayer Corps entrance exam"},
        body="body",
    )
    claude = StubClaudeClient(pages_to_return=[new_page])

    result = wiki_ingest(
        source="initial seed",
        repo=repo,
        claude=claude,
        now=lambda: datetime(2026, 5, 18, 14, 30, tzinfo=UTC),
    )

    assert result.pages_created == ["wiki/arcs/final-selection.md"]
    assert repo.read_index().find_by_path("wiki/arcs/final-selection.md") is not None
    assert len(repo.read_log().entries) == 1
