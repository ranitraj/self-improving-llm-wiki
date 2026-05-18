"""Tests for the WikiAgentDeps bundle."""

from datetime import UTC, datetime
from pathlib import Path

from wiki_agent.deps import WikiAgentDeps
from wiki_agent.wiki_repo import FilesystemWikiRepo

from tests.stubs import StubClaudeClient, StubUrlFetcher


def test_wiki_agent_deps_default_now_returns_utc_datetime(tmp_path: Path) -> None:
    """Verify the default `now` callable returns a tz-aware datetime in UTC.

    Guards against accidentally swapping to a naive `datetime.now()` — log
    timestamps and `WikiIndex.last_updated` MUST be tz-aware so the stale-
    index check is comparable across hosts.
    """
    deps = WikiAgentDeps(
        repo=FilesystemWikiRepo(tmp_path),
        claude=StubClaudeClient(pages_to_return=[]),
        fetcher=StubUrlFetcher(responses={}),
    )

    now = deps.now()

    assert isinstance(now, datetime)
    assert now.tzinfo == UTC


def test_wiki_agent_deps_is_frozen_against_field_mutation(tmp_path: Path) -> None:
    """Verify the dataclass is frozen so callers cannot reassign deps mid-orchestration."""
    deps = WikiAgentDeps(
        repo=FilesystemWikiRepo(tmp_path),
        claude=StubClaudeClient(pages_to_return=[]),
        fetcher=StubUrlFetcher(responses={}),
    )

    try:
        deps.repo = FilesystemWikiRepo(tmp_path)  # type: ignore[misc]
    except (AttributeError, TypeError):
        return
    raise AssertionError("expected dataclass(frozen=True) to reject attribute reassignment")
