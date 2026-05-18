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


class StubUrlFetcher:
    """Stub `UrlFetcher` that returns pre-seeded text for a fixed URL→text map.

    Returns canned data with no expectation checking; records every fetched
    URL on `.calls` so tests can later assert on call count (e.g. for
    idempotency: "the orchestrator should not have fetched a second time").

    Parameters
    ----------
    responses : dict[str, str]
        Map from URL → text that should be returned when that URL is fetched.
        Calling `fetch(url)` with a URL not in this map raises `KeyError`.
    """

    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses
        self.calls: list[str] = []

    def fetch(self, url: str) -> str:
        """Record the call and return the seeded text for `url`.

        Parameters
        ----------
        url : str
            URL to look up in the seeded responses.

        Returns
        -------
        str
            The text mapped to `url` in `responses`.

        Raises
        ------
        KeyError
            If `url` is not present in the seeded responses dict.
        """
        self.calls.append(url)
        return self._responses[url]

    def last_call(self) -> str | None:
        """Return the most recently fetched URL, or None if `fetch` has not run.

        Returns
        -------
        str | None
            The last URL fetched, or `None` if the stub has not been called yet.
        """
        return self.calls[-1] if self.calls else None
