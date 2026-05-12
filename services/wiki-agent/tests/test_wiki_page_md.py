"""Tests for the wiki page parser."""

import pytest
from wiki_agent.wiki_page_md import parse_page


def test_parse_page_extracts_frontmatter_and_body() -> None:
    """Verify parse_page splits the YAML frontmatter into a dict and keeps the body verbatim."""
    content = "---\nname: Tanjiro Kamado\nstatus: alive\n---\n## Summary\nProtagonist of Demon Slayer.\n"

    page = parse_page("wiki/characters/tanjiro.md", content)

    assert page.frontmatter == {"name": "Tanjiro Kamado", "status": "alive"}
    assert page.body == "## Summary\nProtagonist of Demon Slayer.\n"
    assert page.path == "wiki/characters/tanjiro.md"


def test_parse_page_infers_entry_type_from_category_segment() -> None:
    """Verify the second path segment maps to the right EntryType for hyphenated and simple names."""
    content = "---\nname: x\n---\nbody"
    cases = [
        ("wiki/characters/tanjiro.md", "character"),
        ("wiki/episodes/01.md", "episode"),
        ("wiki/breathing-styles/water.md", "breathing_style"),
        ("wiki/blood-demon-arts/temari.md", "blood_demon_art"),
        ("wiki/organizations/demon-slayer-corps.md", "organization"),
    ]
    for path, expected_type in cases:
        page = parse_page(path, content)
        assert page.entry_type == expected_type, f"path {path} expected {expected_type}"


def test_parse_page_round_trips_through_to_markdown() -> None:
    """Verify parse_page → to_markdown reproduces the original content for string-valued frontmatter."""
    original = "---\nname: Tanjiro Kamado\nstatus: alive\n---\n## Summary\nProtagonist."

    reparsed = parse_page("wiki/characters/tanjiro.md", original)

    assert reparsed.to_markdown() == original


def test_parse_page_raises_when_frontmatter_missing() -> None:
    """Verify parse_page raises ValueError when a page lacks the leading `---` block."""
    with pytest.raises(ValueError, match="frontmatter"):
        parse_page("wiki/characters/tanjiro.md", "# Tanjiro\nNo frontmatter here.")


def test_parse_page_raises_on_unknown_category_segment() -> None:
    """Verify parse_page rejects paths whose category segment is not one of the seven entry types."""
    content = "---\nname: x\n---\nbody"
    with pytest.raises(ValueError, match="entry type"):
        parse_page("wiki/legends/foo.md", content)
