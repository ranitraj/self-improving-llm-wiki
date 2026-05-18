"""Wiki ingest orchestrator — synthesizes a source into wiki page updates."""

from datetime import datetime

from wiki_agent.chunking import chunk_text_by_h2
from wiki_agent.claude_client import ClaudeClient
from wiki_agent.constants import TOKEN_CHUNK_THRESHOLD
from wiki_agent.deps import WikiAgentDeps
from wiki_agent.models import IndexEntry, IngestResult, LogEntry, WikiIndex, WikiPage
from wiki_agent.wiki_repo import WikiRepo


def wiki_ingest(
    source: str,
    deps: WikiAgentDeps,
    *,
    max_tokens_per_chunk: int = TOKEN_CHUNK_THRESHOLD,
) -> IngestResult:
    """Synthesize `source` into wiki page updates via Claude, persisting via `deps.repo`.

    If `source` is an http(s) URL it is first fetched through `deps.fetcher`;
    any other string is treated as the raw text. The resulting text is split
    at `## ` H2 boundaries when it exceeds `max_tokens_per_chunk`, and each
    chunk is sent to Claude separately. Pages returned across chunks are
    merged by path — later chunks overwrite earlier ones. Then: reads the
    current index, classifies each synthesized page as new or updated,
    writes them through `deps.repo`, appends a single log entry capturing
    the original `source` and the create/update split, and rebuilds the index.

    Parameters
    ----------
    source : str
        URL (http/https) or free text identifying the input. Stored on the
        log entry verbatim for duplicate-detection by later chunks.
    deps : WikiAgentDeps
        Bundle of orchestrator dependencies — `repo`, `claude`, `fetcher`,
        `now`. Constructed once at the composition root and threaded through
        every Layer 3 orchestrator.
    max_tokens_per_chunk : int
        Soft upper bound on tokens passed to Claude in a single call.
        Triggers H2-boundary chunking when the source exceeds this size.
        Defaults to `TOKEN_CHUNK_THRESHOLD` from `wiki_agent.constants`.

    Returns
    -------
    IngestResult
        Repo-relative paths of created and updated pages, plus a
        human-readable summary of the event.
    """
    timestamp = deps.now()
    index = _load_index(deps.repo, timestamp)
    existing_pages = [deps.repo.read_page(entry.path) for entry in index.entries]

    text = deps.fetcher.fetch(source) if _is_url(source) else source
    chunks = chunk_text_by_h2(text, max_tokens=max_tokens_per_chunk)
    synthesized = _synthesize_across_chunks(deps.claude, chunks, index, existing_pages)

    created, updated = _persist_pages(deps.repo, index, synthesized)
    summary = _build_log_summary(created, updated)
    deps.repo.append_log_entry(
        LogEntry(
            timestamp=timestamp,
            operation="ingest",
            source=source,
            created=created,
            updated=updated,
            summary=summary,
        )
    )
    deps.repo.write_index(_merged_index(index, synthesized, timestamp))

    return IngestResult(pages_created=created, pages_updated=updated, log_entry=summary)


def _synthesize_across_chunks(
    claude: ClaudeClient,
    chunks: list[str],
    index: WikiIndex,
    existing_pages: list[WikiPage],
) -> list[WikiPage]:
    """Call `claude.synthesize_ingest` once per chunk and merge the returned pages.

    Pages are merged by path with later chunks overwriting earlier ones —
    so if Claude returns conflicting versions of the same page across
    chunks, the latest synthesis wins. Page order in the returned list
    matches first-seen order across the chunked walk.

    Parameters
    ----------
    claude : ClaudeClient
        Claude client invoked once per chunk.
    chunks : list[str]
        Source text split into per-chunk strings (see `chunk_text_by_h2`).
    index : WikiIndex
        Current wiki index, passed unchanged to every chunk's Claude call.
    existing_pages : list[WikiPage]
        Pages referenced by the index, passed unchanged to every chunk's call.

    Returns
    -------
    list[WikiPage]
        Merged pages across all chunk responses; one entry per unique path.
    """
    by_path: dict[str, WikiPage] = {}
    for chunk in chunks:
        for page in claude.synthesize_ingest(chunk, index, existing_pages):
            by_path[page.path] = page
    return list(by_path.values())


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


def _is_url(source: str) -> bool:
    """Return True if `source` looks like an http(s) URL.

    Used to decide whether to route the source through the `UrlFetcher` or
    pass it directly to Claude as raw text.

    Parameters
    ----------
    source : str
        Raw source string supplied by the caller.

    Returns
    -------
    bool
        True for strings starting with `http://` or `https://`; False otherwise.
    """
    return source.startswith(("http://", "https://"))


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
