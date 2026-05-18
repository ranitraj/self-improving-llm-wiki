"""Test stubs for Protocols defined in `wiki_agent`. Test-only — not shipped."""

from dataclasses import dataclass

from wiki_agent.models import WikiIndex, WikiPage


@dataclass(frozen=True)
class SynthesizeIngestCall:
    """One recorded invocation of `StubClaudeClient.synthesize_ingest`.

    Stored so tests can assert on how the orchestrator called the stub —
    e.g. that the existing index was passed, or that no second call was
    made when a duplicate source should have been skipped.

    Parameters
    ----------
    source : str
        The source value the orchestrator passed.
    index : WikiIndex
        The index value the orchestrator passed.
    existing_pages : list[WikiPage]
        The page list the orchestrator passed.
    """

    source: str
    index: WikiIndex
    existing_pages: list[WikiPage]


class StubClaudeClient:
    """Stub `ClaudeClient` that returns pre-seeded pages and records every call.

    Returns canned data with no expectation checking — a textbook stub per
    Fowler's *Mocks Aren't Stubs* — but also captures each invocation so
    tests can later assert on call count and arguments (e.g. for idempotency
    checks: "the orchestrator should not have called Claude a second time").

    Parameters
    ----------
    pages_to_return : list[WikiPage]
        Pages returned verbatim from every `synthesize_ingest` call.
    """

    def __init__(self, pages_to_return: list[WikiPage]) -> None:
        self._pages_to_return = pages_to_return
        self.calls: list[SynthesizeIngestCall] = []

    def synthesize_ingest(
        self,
        source: str,
        index: WikiIndex,
        existing_pages: list[WikiPage],
    ) -> list[WikiPage]:
        """Record the call and return the pre-seeded page list.

        Parameters
        ----------
        source : str
            Ingest source — recorded, not used to choose a response.
        index : WikiIndex
            Current wiki index — recorded, not used to choose a response.
        existing_pages : list[WikiPage]
            Pages referenced by the index — recorded.

        Returns
        -------
        list[WikiPage]
            The exact list passed to `__init__`.
        """
        self.calls.append(SynthesizeIngestCall(source=source, index=index, existing_pages=existing_pages))
        return self._pages_to_return

    def last_call(self) -> SynthesizeIngestCall | None:
        """Return the most recent recorded call, or None if `synthesize_ingest` has not run.

        Returns
        -------
        SynthesizeIngestCall | None
            The last invocation, or `None` if the stub has not been called yet.
        """
        return self.calls[-1] if self.calls else None
