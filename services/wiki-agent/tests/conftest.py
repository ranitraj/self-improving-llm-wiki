"""Shared fixtures for the wiki-agent test suite."""

from datetime import UTC, datetime

import pytest
from wiki_agent.models import IndexEntry, LogEntry, WikiIndex

from tests.stubs import StubUrlFetcher


@pytest.fixture
def tanjiro_index_entry() -> IndexEntry:
    """Return a canonical IndexEntry for Tanjiro used across catalog tests.

    Returns
    -------
    IndexEntry
        Character entry for Tanjiro Kamado.
    """
    return IndexEntry(
        title="Tanjiro Kamado",
        path="wiki/characters/tanjiro.md",
        entry_type="character",
        summary="Protagonist demon slayer",
    )


@pytest.fixture
def wiki_index_with_tanjiro(tanjiro_index_entry: IndexEntry) -> WikiIndex:
    """Return a WikiIndex containing just the Tanjiro character entry.

    Parameters
    ----------
    tanjiro_index_entry : IndexEntry
        Injected by pytest from the sibling fixture.

    Returns
    -------
    WikiIndex
        Index with one character entry and a fixed last_updated timestamp.
    """
    return WikiIndex(
        entries=[tanjiro_index_entry],
        last_updated=datetime(2026, 5, 12, 14, 30, tzinfo=UTC),
    )


@pytest.fixture
def ingest_log_entry() -> LogEntry:
    """Return a canonical ingest LogEntry dated 2026-05-01.

    Returns
    -------
    LogEntry
        Ingest event with a source URL and a single-word summary.
    """
    return LogEntry(
        timestamp=datetime(2026, 5, 1, tzinfo=UTC),
        operation="ingest",
        source="https://example.com/a",
        summary="first",
    )


@pytest.fixture
def lint_log_entry() -> LogEntry:
    """Return a canonical lint LogEntry dated 2026-05-07.

    Returns
    -------
    LogEntry
        Lint event with no source and a single-word summary.
    """
    return LogEntry(
        timestamp=datetime(2026, 5, 7, tzinfo=UTC),
        operation="lint",
        summary="second",
    )


@pytest.fixture
def text_only_fetcher() -> StubUrlFetcher:
    """Return an empty `StubUrlFetcher` for tests that ingest text sources.

    Useful when a test passes a non-URL source through `wiki_ingest` and the
    fetcher should never be called. Any accidental fetch will raise `KeyError`,
    making the misuse obvious.

    Returns
    -------
    StubUrlFetcher
        A fetcher with no seeded URL responses.
    """
    return StubUrlFetcher(responses={})
