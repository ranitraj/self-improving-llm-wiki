"""Wiki ingest orchestrator — synthesizes a source into wiki page updates."""

from collections.abc import Callable
from datetime import UTC, datetime

from wiki_agent.claude_client import ClaudeClient
from wiki_agent.models import IndexEntry, IngestResult, LogEntry, WikiIndex, WikiPage
from wiki_agent.wiki_repo import WikiRepo


def wiki_ingest(
    source: str,
    repo: WikiRepo,
    claude: ClaudeClient,
    *,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> IngestResult:
    """Synthesize `source` into wiki page updates via Claude, persisting via `repo`.

    Reads the current index, asks Claude to produce a set of new or updated
    pages, classifies each by whether its path is already in the index,
    writes them through `repo`, appends a single log entry capturing the
    source and the create/update split, and rebuilds the index.

    Parameters
    ----------
    source : str
        Free text or URL identifying the input. Used as the log entry's
        `source` field for duplicate-detection by later chunks.
    repo : WikiRepo
        Storage backend for the wiki content repo.
    claude : ClaudeClient
        Claude client used to synthesize the new page set.
    now : Callable[[], datetime]
        Injected clock for testability. Defaults to `datetime.now(UTC)`.

    Returns
    -------
    IngestResult
        Repo-relative paths of created and updated pages, plus a
        human-readable summary of the event.
    """
    timestamp = now()
    index = _load_index(repo, timestamp)
    existing_pages = [repo.read_page(entry.path) for entry in index.entries]

    synthesized = claude.synthesize_ingest(source, index, existing_pages)

    created, updated = _persist_pages(repo, index, synthesized)
    summary = _build_log_summary(created, updated)
    repo.append_log_entry(
        LogEntry(
            timestamp=timestamp,
            operation="ingest",
            source=source,
            created=created,
            updated=updated,
            summary=summary,
        )
    )
    repo.write_index(_merged_index(index, synthesized, timestamp))

    return IngestResult(pages_created=created, pages_updated=updated, log_entry=summary)


def _load_index(repo: WikiRepo, fallback_timestamp: datetime) -> WikiIndex:
    """Return the current index, or an empty one if `index.md` does not exist yet.

    Parameters
    ----------
    repo : WikiRepo
        Storage backend.
    fallback_timestamp : datetime
        `last_updated` value for the empty index returned on a fresh repo.

    Returns
    -------
    WikiIndex
        The loaded or freshly-constructed empty index.
    """
    try:
        return repo.read_index()
    except FileNotFoundError:
        return WikiIndex(entries=[], last_updated=fallback_timestamp)


def _persist_pages(
    repo: WikiRepo,
    index: WikiIndex,
    synthesized: list[WikiPage],
) -> tuple[list[str], list[str]]:
    """Write each synthesized page and return the create/update path split.

    Parameters
    ----------
    repo : WikiRepo
        Storage backend.
    index : WikiIndex
        Pre-ingest index, used to classify each path as new or pre-existing.
    synthesized : list[WikiPage]
        Pages Claude returned for this ingest.

    Returns
    -------
    tuple[list[str], list[str]]
        (created_paths, updated_paths) preserving the order Claude returned.
    """
    created: list[str] = []
    updated: list[str] = []
    for page in synthesized:
        if index.find_by_path(page.path) is None:
            created.append(page.path)
        else:
            updated.append(page.path)
        repo.write_page(page)
    return created, updated


def _merged_index(
    current: WikiIndex,
    synthesized: list[WikiPage],
    timestamp: datetime,
) -> WikiIndex:
    """Return a new index with `synthesized` pages merged into `current.entries`.

    Existing paths have their IndexEntry refreshed in place (preserves order);
    new paths are appended at the end.

    Parameters
    ----------
    current : WikiIndex
        Index before this ingest.
    synthesized : list[WikiPage]
        Pages produced by Claude.
    timestamp : datetime
        New `last_updated` value.

    Returns
    -------
    WikiIndex
        Updated index ready to persist.
    """
    by_path: dict[str, IndexEntry] = {entry.path: entry for entry in current.entries}
    for page in synthesized:
        by_path[page.path] = _index_entry_from_page(page)
    return WikiIndex(entries=list(by_path.values()), last_updated=timestamp)


def _index_entry_from_page(page: WikiPage) -> IndexEntry:
    """Derive an `IndexEntry` from a `WikiPage`'s frontmatter.

    Falls back to the filename (without `.md`) for `title` and an empty
    string for `summary` if the expected frontmatter fields are absent.

    Parameters
    ----------
    page : WikiPage
        The page whose frontmatter to read.

    Returns
    -------
    IndexEntry
        Title sourced from `name` (preferred for character/arc/etc.) or
        `title` (preferred for episode); summary sourced from `summary`.
    """
    title = str(page.frontmatter.get("name") or page.frontmatter.get("title") or page.file_name().removesuffix(".md"))
    summary = str(page.frontmatter.get("summary") or "")
    return IndexEntry(title=title, path=page.path, entry_type=page.entry_type, summary=summary)


def _build_log_summary(created: list[str], updated: list[str]) -> str:
    """Build the human-readable summary string recorded on the log entry.

    Parameters
    ----------
    created : list[str]
        Paths of pages created during this ingest.
    updated : list[str]
        Paths of pages updated during this ingest.

    Returns
    -------
    str
        One-line summary, e.g. "Ingest: 1 created, 2 updated" or
        "Ingest: no pages touched" when both lists are empty.
    """
    parts: list[str] = []
    if created:
        parts.append(f"{len(created)} created")
    if updated:
        parts.append(f"{len(updated)} updated")
    return f"Ingest: {', '.join(parts) if parts else 'no pages touched'}"
