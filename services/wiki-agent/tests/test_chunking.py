"""Tests for chunk_text_by_h2."""

import logging

import pytest
from wiki_agent.chunking import chunk_text_by_h2


def test_small_text_returns_a_single_chunk_unchanged() -> None:
    """Verify text below the token threshold is returned as one chunk with original content intact."""
    text = "## Tanjiro\nHe is the protagonist.\n\n## Nezuko\nShe is his sister."

    chunks = chunk_text_by_h2(text, max_tokens=1000)

    assert chunks == [text]


def test_large_text_with_h2_headings_is_split_into_per_section_chunks() -> None:
    """Verify text above the threshold splits at `## ` boundaries, with each H2 section in its own chunk."""
    section_a = "## Tanjiro\n" + "He is the protagonist.\n" * 50
    section_b = "## Nezuko\n" + "She is his sister.\n" * 50
    section_c = "## Zenitsu\n" + "He uses Thunder Breathing.\n" * 50
    text = section_a + section_b + section_c

    chunks = chunk_text_by_h2(text, max_tokens=100)

    assert len(chunks) >= 2
    rejoined = "".join(chunks)
    assert "## Tanjiro" in rejoined
    assert "## Nezuko" in rejoined
    assert "## Zenitsu" in rejoined
    for chunk in chunks:
        assert chunk.startswith("## "), f"chunk does not start at an H2 boundary: {chunk[:40]!r}"


def test_large_text_without_h2_returns_single_chunk_and_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Verify oversized text with no H2 boundaries is passed through as one chunk and a warning is logged."""
    text = "This is a single very long paragraph. " * 500

    with caplog.at_level(logging.WARNING, logger="wiki_agent.chunking"):
        chunks = chunk_text_by_h2(text, max_tokens=100)

    assert chunks == [text]
    assert any(
        "no H2" in record.message.lower() or "could not split" in record.message.lower() for record in caplog.records
    )


def test_chunks_preserve_content_when_rejoined() -> None:
    """Verify rejoining chunks reproduces the original H2-prefixed text exactly (no content lost or duplicated)."""
    text = "## Section A\nContent A.\n\n## Section B\nContent B.\n\n## Section C\nContent C.\n"

    chunks = chunk_text_by_h2(text, max_tokens=10)

    assert "".join(chunks) == text
