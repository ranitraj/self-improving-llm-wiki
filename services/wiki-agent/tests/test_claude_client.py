"""Tests for the StubClaudeClient test double."""

from datetime import UTC, datetime

from wiki_agent.models import WikiIndex, WikiPage

from tests.stubs import StubClaudeClient


def test_stub_claude_client_returns_pre_seeded_pages_for_ingest() -> None:
    """Verify StubClaudeClient.synthesize_ingest hands back exactly the pages it was constructed with."""
    seeded = [
        WikiPage(
            entry_type="character",
            path="wiki/characters/tanjiro.md",
            frontmatter={"name": "Tanjiro Kamado"},
            body="## Summary\nProtagonist.",
        ),
    ]
    client = StubClaudeClient(pages_to_return=seeded)

    result = client.synthesize_ingest(
        source="https://example.com/tanjiro",
        index=WikiIndex(entries=[], last_updated=datetime(2026, 5, 18, tzinfo=UTC)),
        existing_pages=[],
    )

    assert result == seeded


def test_stub_claude_client_records_every_invocation_with_call_args() -> None:
    """Verify each synthesize_ingest call is captured on `.calls`, exposed via `last_call()`."""
    client = StubClaudeClient(pages_to_return=[])
    index = WikiIndex(entries=[], last_updated=datetime(2026, 5, 18, tzinfo=UTC))

    assert client.last_call() is None

    client.synthesize_ingest(source="first", index=index, existing_pages=[])
    client.synthesize_ingest(source="second", index=index, existing_pages=[])

    assert len(client.calls) == 2
    assert client.calls[0].source == "first"
    assert client.calls[1].source == "second"
    last = client.last_call()
    assert last is not None
    assert last.source == "second"
