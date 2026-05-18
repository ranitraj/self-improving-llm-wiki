"""URL fetcher Protocol used by `wiki_ingest` to read source pages from the web."""

from typing import Protocol


# pylint: disable=too-few-public-methods
# ^ Remove if/when the Protocol grows a second method. For now the contract is
#   intentionally a single method; R0903 is a false positive for one-method
#   Protocols (see the same pattern on ClaudeClient).
class UrlFetcher(Protocol):
    """Contract for the URL-fetcher used by the ingest orchestrator."""

    def fetch(self, url: str) -> str:
        """Return the plain-text content of the page at `url` (HTML stripped)."""
