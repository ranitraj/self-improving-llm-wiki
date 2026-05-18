"""Tests for the wiki_ingest orchestrator."""

from datetime import UTC, datetime
from pathlib import Path

from wiki_agent.deps import WikiAgentDeps
from wiki_agent.ingest import wiki_ingest
from wiki_agent.models import WikiIndex, WikiPage
from wiki_agent.wiki_repo import FilesystemWikiRepo

from tests.stubs import StubClaudeClient, StubUrlFetcher


def _fixed_now() -> datetime:
    """Return a fixed timestamp so log entries and index timestamps are deterministic."""
    return datetime(2026, 5, 18, 14, 30, tzinfo=UTC)


def _deps(
    repo: FilesystemWikiRepo,
    claude: StubClaudeClient,
    fetcher: StubUrlFetcher,
) -> WikiAgentDeps:
    """Construct a WikiAgentDeps bundle with a fixed clock for deterministic tests."""
    return WikiAgentDeps(repo=repo, claude=claude, fetcher=fetcher, now=_fixed_now)


def test_wiki_ingest_writes_new_pages_when_source_yields_unknown_paths(
    tmp_path: Path, text_only_fetcher: StubUrlFetcher
) -> None:
    """Verify a fresh repo with one new synthesized page records it in pages_created and on disk."""
    repo = FilesystemWikiRepo(tmp_path)
    new_page = WikiPage(
        entry_type="character",
        path="wiki/characters/tanjiro.md",
        frontmatter={"name": "Tanjiro Kamado", "summary": "Protagonist demon slayer"},
        body="## Summary\nProtagonist of Demon Slayer.",
    )
    claude = StubClaudeClient(pages_to_return=[new_page])

    result = wiki_ingest(source="Tanjiro Kamado wiki notes", deps=_deps(repo, claude, text_only_fetcher))

    assert result.pages_created == ["wiki/characters/tanjiro.md"]
    assert not result.pages_updated
    assert repo.read_page("wiki/characters/tanjiro.md") == new_page


def test_wiki_ingest_updates_existing_page_rather_than_duplicating(
    tmp_path: Path, wiki_index_with_tanjiro: WikiIndex, text_only_fetcher: StubUrlFetcher
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

    result = wiki_ingest(source="Tanjiro Kamado update notes", deps=_deps(repo, claude, text_only_fetcher))

    assert result.pages_updated == ["wiki/characters/tanjiro.md"]
    assert not result.pages_created
    assert repo.read_page("wiki/characters/tanjiro.md").body == "## Summary\nProtagonist — now with Hinokami Kagura."


def test_wiki_ingest_appends_log_entry_with_source_and_classification(
    tmp_path: Path, text_only_fetcher: StubUrlFetcher
) -> None:
    """Verify the log gains an ingest entry capturing the source identifier and the created/updated split."""
    repo = FilesystemWikiRepo(tmp_path)
    new_page = WikiPage(
        entry_type="episode",
        path="wiki/episodes/01.md",
        frontmatter={"title": "Cruelty", "summary": "Tanjiro's family is killed"},
        body="ep1",
    )
    claude = StubClaudeClient(pages_to_return=[new_page])

    wiki_ingest(source="Episode 1: Cruelty — plot summary", deps=_deps(repo, claude, text_only_fetcher))

    log = repo.read_log()
    assert len(log.entries) == 1
    entry = log.entries[0]
    assert entry.operation == "ingest"
    assert entry.source == "Episode 1: Cruelty — plot summary"
    assert entry.created == ["wiki/episodes/01.md"]
    assert entry.updated == []
    assert entry.timestamp == datetime(2026, 5, 18, 14, 30, tzinfo=UTC)


def test_wiki_ingest_updates_index_with_new_entries(tmp_path: Path, text_only_fetcher: StubUrlFetcher) -> None:
    """Verify the index gains an IndexEntry for each newly created page after ingest."""
    repo = FilesystemWikiRepo(tmp_path)
    new_page = WikiPage(
        entry_type="character",
        path="wiki/characters/zenitsu.md",
        frontmatter={"name": "Zenitsu Agatsuma", "summary": "Thunder Breathing user"},
        body="body",
    )
    claude = StubClaudeClient(pages_to_return=[new_page])

    wiki_ingest(source="Zenitsu Agatsuma character notes", deps=_deps(repo, claude, text_only_fetcher))

    index = repo.read_index()
    zenitsu = index.find_by_path("wiki/characters/zenitsu.md")
    assert zenitsu is not None
    assert zenitsu.title == "Zenitsu Agatsuma"
    assert zenitsu.entry_type == "character"
    assert zenitsu.summary == "Thunder Breathing user"
    assert index.last_updated == datetime(2026, 5, 18, 14, 30, tzinfo=UTC)


def test_wiki_ingest_handles_repo_without_prior_index_or_log(
    tmp_path: Path, text_only_fetcher: StubUrlFetcher
) -> None:
    """Verify ingest works on a brand-new repo where index.md and log.md do not yet exist."""
    repo = FilesystemWikiRepo(tmp_path)
    new_page = WikiPage(
        entry_type="arc",
        path="wiki/arcs/final-selection.md",
        frontmatter={"name": "Final Selection", "summary": "Demon Slayer Corps entrance exam"},
        body="body",
    )
    claude = StubClaudeClient(pages_to_return=[new_page])

    result = wiki_ingest(source="initial seed", deps=_deps(repo, claude, text_only_fetcher))

    assert result.pages_created == ["wiki/arcs/final-selection.md"]
    assert repo.read_index().find_by_path("wiki/arcs/final-selection.md") is not None
    assert len(repo.read_log().entries) == 1


def test_wiki_ingest_fetches_url_source_through_fetcher_before_calling_claude(tmp_path: Path) -> None:
    """Verify a URL source is fetched, and Claude receives the fetched text (not the URL itself)."""
    repo = FilesystemWikiRepo(tmp_path)
    url = "https://demonslayer.fandom.com/wiki/Tanjiro_Kamado"
    fetched_text = "Tanjiro Kamado is the protagonist of Demon Slayer."
    fetcher = StubUrlFetcher(responses={url: fetched_text})
    page = WikiPage(
        entry_type="character",
        path="wiki/characters/tanjiro.md",
        frontmatter={"name": "Tanjiro Kamado", "summary": "Protagonist"},
        body="body",
    )
    claude = StubClaudeClient(pages_to_return=[page])

    wiki_ingest(source=url, deps=_deps(repo, claude, fetcher))

    assert fetcher.calls == [url]
    last_claude_call = claude.last_call()
    assert last_claude_call is not None
    assert last_claude_call.source == fetched_text


def test_wiki_ingest_calls_claude_once_for_small_text_source(
    tmp_path: Path, text_only_fetcher: StubUrlFetcher
) -> None:
    """Verify a small text source triggers exactly one synthesize_ingest call (no chunking)."""
    repo = FilesystemWikiRepo(tmp_path)
    page = WikiPage(
        entry_type="character",
        path="wiki/characters/tanjiro.md",
        frontmatter={"name": "Tanjiro", "summary": "Protagonist"},
        body="body",
    )
    claude = StubClaudeClient(pages_to_return=[page])

    wiki_ingest(source="Short text about Tanjiro.", deps=_deps(repo, claude, text_only_fetcher))

    assert len(claude.calls) == 1


def test_wiki_ingest_chunks_large_text_into_multiple_claude_calls_at_h2_boundaries(
    tmp_path: Path, text_only_fetcher: StubUrlFetcher
) -> None:
    """Verify a large multi-H2 text triggers more than one synthesize_ingest call, each receiving an H2 chunk."""
    repo = FilesystemWikiRepo(tmp_path)
    page = WikiPage(
        entry_type="character",
        path="wiki/characters/tanjiro.md",
        frontmatter={"name": "Tanjiro", "summary": "Protagonist"},
        body="body",
    )
    claude = StubClaudeClient(pages_to_return=[page])
    large_source = (
        "## Tanjiro\n"
        + ("Tanjiro is the protagonist.\n" * 100)
        + "## Nezuko\n"
        + ("Nezuko is his sister.\n" * 100)
        + "## Zenitsu\n"
        + ("Zenitsu uses Thunder Breathing.\n" * 100)
    )

    wiki_ingest(
        source=large_source,
        deps=_deps(repo, claude, text_only_fetcher),
        max_tokens_per_chunk=200,
    )

    assert len(claude.calls) >= 2
    for call in claude.calls:
        assert call.source.startswith("## "), f"chunk does not begin at an H2 boundary: {call.source[:40]!r}"


def test_wiki_ingest_passes_text_source_to_claude_without_calling_fetcher(
    tmp_path: Path, text_only_fetcher: StubUrlFetcher
) -> None:
    """Verify a non-URL source bypasses the fetcher entirely and reaches Claude unchanged."""
    repo = FilesystemWikiRepo(tmp_path)
    page = WikiPage(
        entry_type="character",
        path="wiki/characters/inosuke.md",
        frontmatter={"name": "Inosuke Hashibira", "summary": "Beast Breathing user"},
        body="body",
    )
    claude = StubClaudeClient(pages_to_return=[page])
    plain_text = "Inosuke is a Demon Slayer who wears a boar's head."

    wiki_ingest(source=plain_text, deps=_deps(repo, claude, text_only_fetcher))

    assert text_only_fetcher.calls == []
    last_claude_call = claude.last_call()
    assert last_claude_call is not None
    assert last_claude_call.source == plain_text
