"""Claude API client Protocol used by Layer 3 orchestrators."""

from typing import Protocol

from wiki_agent.models import WikiIndex, WikiPage


# pylint: disable=too-few-public-methods
# ^ Remove when `synthesize_query` (chunk 3.6) and `synthesize_lint` (chunk 3.6)
#   are added. R0903 is a false positive for a Protocol with a single contract
#   method, but becomes redundant once the Protocol carries multiple methods.
class ClaudeClient(Protocol):
    """Contract for the Claude API client used by Layer 3 orchestrators."""

    def synthesize_ingest(
        self,
        source: str,
        index: WikiIndex,
        existing_pages: list[WikiPage],
    ) -> list[WikiPage]:
        """Return the pages to create or update for `source`, given current wiki state."""
