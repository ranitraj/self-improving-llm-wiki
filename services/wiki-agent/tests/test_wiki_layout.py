"""Tests for the wiki category taxonomy helpers."""

from typing import get_args

from wiki_agent.utils.wiki_layout import (
    WIKI_CATEGORIES,
    EntryType,
    entry_type_for_path_segment,
    entry_type_for_section,
    path_prefix_for,
    section_for,
)


def test_wiki_categories_covers_every_entry_type_exactly_once() -> None:
    """Verify the taxonomy table includes every member of the EntryType literal with no duplicates."""
    entry_types = {category.entry_type for category in WIKI_CATEGORIES}
    assert entry_types == set(get_args(EntryType))
    assert len(WIKI_CATEGORIES) == len(entry_types)


def test_entry_type_for_section_maps_display_headings() -> None:
    """Verify display section headings map back to the right entry types, including hyphenated ones."""
    assert entry_type_for_section("Characters") == "character"
    assert entry_type_for_section("Breathing Styles") == "breathing_style"
    assert entry_type_for_section("Blood Demon Arts") == "blood_demon_art"


def test_entry_type_for_section_returns_none_for_unknown_heading() -> None:
    """Verify unknown section headings return None rather than raising."""
    assert entry_type_for_section("Villains") is None


def test_entry_type_for_path_segment_maps_filesystem_segments() -> None:
    """Verify filesystem path segments (lowercase, hyphenated) map back to the right entry types."""
    assert entry_type_for_path_segment("characters") == "character"
    assert entry_type_for_path_segment("breathing-styles") == "breathing_style"
    assert entry_type_for_path_segment("blood-demon-arts") == "blood_demon_art"


def test_entry_type_for_path_segment_returns_none_for_unknown_segment() -> None:
    """Verify unknown path segments return None rather than raising."""
    assert entry_type_for_path_segment("villains") is None


def test_path_prefix_for_returns_wiki_relative_directory() -> None:
    """Verify path_prefix_for returns the canonical `wiki/<segment>/` form used in repo paths."""
    assert path_prefix_for("episode") == "wiki/episodes/"
    assert path_prefix_for("breathing_style") == "wiki/breathing-styles/"


def test_section_for_round_trips_with_entry_type_for_section() -> None:
    """Verify section_for and entry_type_for_section are exact inverses across all categories."""
    for category in WIKI_CATEGORIES:
        assert entry_type_for_section(section_for(category.entry_type)) == category.entry_type
