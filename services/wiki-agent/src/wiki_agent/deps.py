"""Dependency bundle passed to Layer 3 orchestrators."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from wiki_agent.claude_client import ClaudeClient
from wiki_agent.url_fetcher import UrlFetcher
from wiki_agent.wiki_repo import WikiRepo


def _utc_now() -> datetime:
    """Return the current time in UTC. Default clock for WikiAgentDeps.

    Returns
    -------
    datetime
        Current UTC time.
    """
    return datetime.now(UTC)


@dataclass(frozen=True)
class WikiAgentDeps:
    """Bundle of dependencies passed to every Layer 3 orchestrator.

    Constructed once at the composition root (CLI / MCP server bootstrap /
    Telegram bot startup) and threaded through `wiki_ingest`, `wiki_query`,
    and `wiki_lint` so they share a single source of truth for storage,
    Claude, URL fetching, and the clock.

    Parameters
    ----------
    repo : WikiRepo
        Storage backend for the wiki content repo.
    claude : ClaudeClient
        Claude client used to synthesize ingest/query/lint operations.
    fetcher : UrlFetcher
        URL fetcher invoked when an orchestrator receives an http(s) source.
    now : Callable[[], datetime]
        Injected clock for testability. Defaults to `datetime.now(UTC)`.
    """

    repo: WikiRepo
    claude: ClaudeClient
    fetcher: UrlFetcher
    now: Callable[[], datetime] = _utc_now
