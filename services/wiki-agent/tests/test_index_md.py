"""Tests for the index.md parser and serializer."""

from datetime import UTC, datetime

import pytest
from wiki_agent.index_md import parse_index, serialize_index
from wiki_agent.models import IndexEntry, WikiIndex


def test_parse_index_extracts_entries_under_each_section() -> None:
    """Verify parse_index reads bullets from each section and maps them to the right entry_type."""
    content = (
        "---\n"
        "last_updated: 2026-05-11T14:30:00+00:00\n"
        "---\n"
        "\n"
        "# Wiki Index\n"
        "\n"
        "## Characters\n"
        "- [Tanjiro Kamado](wiki/characters/tanjiro.md) — Protagonist demon slayer\n"
        "- [Nezuko Kamado](wiki/characters/nezuko.md) — Demon sister of Tanjiro\n"
        "\n"
        "## Episodes\n"
        "- [Episode 1](wiki/episodes/01.md) — Cruelty\n"
        "\n"
        "## Breathing Styles\n"
        "- [Water Breathing](wiki/breathing-styles/water.md) — First breathing form taught to Tanjiro\n"
    )

    index = parse_index(content)

    assert index.last_updated == datetime(2026, 5, 11, 14, 30, tzinfo=UTC)
    assert len(index.entries) == 4
    tanjiro = index.find_by_path("wiki/characters/tanjiro.md")
    assert tanjiro is not None
    assert tanjiro.entry_type == "character"
    assert tanjiro.title == "Tanjiro Kamado"
    assert tanjiro.summary == "Protagonist demon slayer"
    ep1 = index.find_by_path("wiki/episodes/01.md")
    assert ep1 is not None
    assert ep1.entry_type == "episode"
    water = index.find_by_path("wiki/breathing-styles/water.md")
    assert water is not None
    assert water.entry_type == "breathing_style"


def test_parse_index_handles_absent_sections_as_empty() -> None:
    """Verify a wiki with only one section parses cleanly and does not invent entries for missing ones."""
    content = (
        "---\n"
        "last_updated: 2026-05-11T14:30:00+00:00\n"
        "---\n"
        "\n"
        "# Wiki Index\n"
        "\n"
        "## Characters\n"
        "- [Tanjiro Kamado](wiki/characters/tanjiro.md) — Protagonist demon slayer\n"
    )

    index = parse_index(content)

    assert len(index.entries) == 1
    assert index.find_by_type("episode") == []
    assert index.find_by_type("organization") == []


def test_parse_index_raises_when_frontmatter_missing() -> None:
    """Verify parse_index raises ValueError when the frontmatter block is missing — last_updated is required."""
    content = "# Wiki Index\n\n## Characters\n- [Tanjiro](wiki/characters/tanjiro.md) — Protagonist\n"

    with pytest.raises(ValueError, match="frontmatter"):
        parse_index(content)


def test_serialize_index_omits_sections_with_no_entries() -> None:
    """Verify serialize_index does not emit headings for entry types that have no entries."""
    index = WikiIndex(
        entries=[
            IndexEntry(
                title="Tanjiro Kamado",
                path="wiki/characters/tanjiro.md",
                entry_type="character",
                summary="Protagonist demon slayer",
            ),
        ],
        last_updated=datetime(2026, 5, 11, 14, 30, tzinfo=UTC),
    )

    output = serialize_index(index)

    assert "## Characters" in output
    assert "## Episodes" not in output
    assert "## Organizations" not in output
    assert "last_updated: 2026-05-11T14:30:00+00:00" in output


def test_round_trip_preserves_all_entries_across_types() -> None:
    """Verify a full index with entries in multiple sections round-trips through serialize and parse unchanged."""
    original = WikiIndex(
        entries=[
            IndexEntry(
                title="Tanjiro Kamado",
                path="wiki/characters/tanjiro.md",
                entry_type="character",
                summary="Protagonist demon slayer",
            ),
            IndexEntry(
                title="Kyojuro Rengoku",
                path="wiki/characters/rengoku.md",
                entry_type="character",
                summary="Flame Hashira",
            ),
            IndexEntry(
                title="Mugen Train",
                path="wiki/arcs/mugen-train.md",
                entry_type="arc",
                summary="Confrontation with Lower Moon One",
            ),
            IndexEntry(
                title="Flame Breathing",
                path="wiki/breathing-styles/flame.md",
                entry_type="breathing_style",
                summary="Rengoku's breathing style",
            ),
        ],
        last_updated=datetime(2026, 5, 11, 14, 30, tzinfo=UTC),
    )

    reparsed = parse_index(serialize_index(original))

    assert reparsed.last_updated == original.last_updated
    assert len(reparsed.entries) == len(original.entries)
    for entry in original.entries:
        match = reparsed.find_by_path(entry.path)
        assert match is not None
        assert match.title == entry.title
        assert match.entry_type == entry.entry_type
        assert match.summary == entry.summary
