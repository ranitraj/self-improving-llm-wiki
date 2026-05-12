"""Tests for the shared frontmatter parsing helpers."""

import pytest
from wiki_agent.utils.frontmatter import parse_fields, split_frontmatter


def test_split_frontmatter_extracts_block_and_body() -> None:
    """Verify split_frontmatter returns the block and the body without the surrounding delimiters."""
    content = "---\nname: Tanjiro\nstatus: alive\n---\n## Summary\nProtagonist.\n"

    block, body = split_frontmatter(content)

    assert block == "name: Tanjiro\nstatus: alive"
    assert body == "## Summary\nProtagonist.\n"


def test_split_frontmatter_raises_when_opening_delimiter_missing() -> None:
    """Verify split_frontmatter raises ValueError when the content does not begin with `---`."""
    with pytest.raises(ValueError, match="opening frontmatter delimiter"):
        split_frontmatter("name: Tanjiro\n---\nbody")


def test_split_frontmatter_raises_when_closing_delimiter_missing() -> None:
    """Verify split_frontmatter raises ValueError when no closing `---` line follows the opener."""
    with pytest.raises(ValueError, match="closing frontmatter delimiter"):
        split_frontmatter("---\nname: Tanjiro\nstatus: alive\n")


def test_parse_fields_extracts_stripped_key_value_pairs() -> None:
    """Verify parse_fields strips whitespace around both keys and values."""
    block = "  name :  Tanjiro Kamado  \nstatus:alive"

    fields = parse_fields(block)

    assert fields == {"name": "Tanjiro Kamado", "status": "alive"}


def test_parse_fields_skips_lines_without_a_colon() -> None:
    """Verify parse_fields ignores blank and non-`key: value` lines rather than raising."""
    block = "\nname: Tanjiro\nthis line has no colon\nstatus: alive\n"

    assert parse_fields(block) == {"name": "Tanjiro", "status": "alive"}


def test_parse_fields_keeps_colons_inside_values() -> None:
    """Verify parse_fields treats only the first colon as the separator so URL values survive intact."""
    block = "source: https://demonslayer.fandom.com/wiki/Tanjiro\nlast_updated: 2026-05-11T14:30:00+00:00"

    fields = parse_fields(block)

    assert fields["source"] == "https://demonslayer.fandom.com/wiki/Tanjiro"
    assert fields["last_updated"] == "2026-05-11T14:30:00+00:00"
