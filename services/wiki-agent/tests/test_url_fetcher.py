"""Tests for the StubUrlFetcher test double."""

import pytest

from tests.stubs import StubUrlFetcher


def test_stub_url_fetcher_returns_seeded_text_for_known_url() -> None:
    """Verify fetch(url) returns the text the stub was configured with for that URL."""
    fetcher = StubUrlFetcher(responses={"https://example.com/tanjiro": "Tanjiro is the protagonist."})

    assert fetcher.fetch("https://example.com/tanjiro") == "Tanjiro is the protagonist."


def test_stub_url_fetcher_raises_key_error_for_unmapped_url() -> None:
    """Verify fetch(url) raises KeyError when the URL has no seeded response."""
    fetcher = StubUrlFetcher(responses={})

    with pytest.raises(KeyError):
        fetcher.fetch("https://example.com/unknown")


def test_stub_url_fetcher_records_every_invocation() -> None:
    """Verify each fetch call is captured on `.calls`, exposed via `last_call()`."""
    fetcher = StubUrlFetcher(
        responses={
            "https://example.com/a": "page A",
            "https://example.com/b": "page B",
        }
    )

    assert fetcher.last_call() is None

    fetcher.fetch("https://example.com/a")
    fetcher.fetch("https://example.com/b")

    assert fetcher.calls == ["https://example.com/a", "https://example.com/b"]
    assert fetcher.last_call() == "https://example.com/b"
