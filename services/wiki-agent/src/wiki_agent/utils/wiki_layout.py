"""Single source of truth for the wiki's category taxonomy.

Every entry in the wiki belongs to one of seven categories. Each category has:
- an `EntryType` literal — used in code and Pydantic models,
- a display section heading — used in index.md (e.g. "Characters"),
- a filesystem path segment — used in repo paths (e.g. "characters").

Other modules import the lookup helpers below rather than redefining the mapping.
"""

from dataclasses import dataclass
from typing import Literal

EntryType = Literal[
    "character",
    "episode",
    "arc",
    "breathing_style",
    "blood_demon_art",
    "location",
    "organization",
]


@dataclass(frozen=True)
class WikiCategory:
    """Display and filesystem identifiers for a single wiki category.

    Parameters
    ----------
    entry_type : EntryType
        The canonical type literal used throughout the codebase.
    section : str
        The display heading used under `## ` in index.md.
    path_segment : str
        The second segment of repo-relative paths (e.g. `wiki/<segment>/<file>.md`).
    """

    entry_type: EntryType
    section: str
    path_segment: str


WIKI_CATEGORIES: tuple[WikiCategory, ...] = (
    WikiCategory("character", "Characters", "characters"),
    WikiCategory("episode", "Episodes", "episodes"),
    WikiCategory("arc", "Arcs", "arcs"),
    WikiCategory("breathing_style", "Breathing Styles", "breathing-styles"),
    WikiCategory("blood_demon_art", "Blood Demon Arts", "blood-demon-arts"),
    WikiCategory("location", "Locations", "locations"),
    WikiCategory("organization", "Organizations", "organizations"),
)


def entry_type_for_section(section: str) -> EntryType | None:
    """Return the EntryType for an index.md section heading, or None if unknown.

    Parameters
    ----------
    section : str
        Section heading text (e.g. "Characters").

    Returns
    -------
    EntryType | None
        Matching entry type, or None when the heading is not a known category.
    """
    return _BY_SECTION.get(section)


def entry_type_for_path_segment(segment: str) -> EntryType | None:
    """Return the EntryType for a path's category segment, or None if unknown.

    Parameters
    ----------
    segment : str
        Second segment of a `wiki/<segment>/<file>.md` path.

    Returns
    -------
    EntryType | None
        Matching entry type, or None when the segment is not a known category.
    """
    return _BY_PATH_SEGMENT.get(segment)


def section_for(entry_type: EntryType) -> str:
    """Return the index.md section heading for an entry type.

    Parameters
    ----------
    entry_type : EntryType
        Canonical category type.

    Returns
    -------
    str
        The display heading used in index.md (e.g. "Characters").
    """
    return _BY_ENTRY_TYPE[entry_type].section


def path_prefix_for(entry_type: EntryType) -> str:
    """Return the `wiki/<segment>/` path prefix for an entry type.

    Parameters
    ----------
    entry_type : EntryType
        Canonical category type.

    Returns
    -------
    str
        Path prefix ending in a slash, e.g. `wiki/episodes/`.
    """
    return f"wiki/{_BY_ENTRY_TYPE[entry_type].path_segment}/"


_BY_ENTRY_TYPE: dict[EntryType, WikiCategory] = {c.entry_type: c for c in WIKI_CATEGORIES}
_BY_SECTION: dict[str, EntryType] = {c.section: c.entry_type for c in WIKI_CATEGORIES}
_BY_PATH_SEGMENT: dict[str, EntryType] = {c.path_segment: c.entry_type for c in WIKI_CATEGORIES}
