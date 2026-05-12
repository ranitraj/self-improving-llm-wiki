"""Parser and serializer for the on-disk index.md catalog."""

from datetime import datetime

from wiki_agent.models import EntryType, IndexEntry, WikiIndex

_FRONTMATTER_DELIMITER = "---"

_SECTION_TO_ENTRY_TYPE: dict[str, EntryType] = {
    "Characters": "character",
    "Episodes": "episode",
    "Arcs": "arc",
    "Breathing Styles": "breathing_style",
    "Blood Demon Arts": "blood_demon_art",
    "Locations": "location",
    "Organizations": "organization",
}


def parse_index(content: str) -> WikiIndex:
    """Parse the textual content of index.md into a WikiIndex.

    Parameters
    ----------
    content : str
        Full text of an index.md file, including the YAML frontmatter block.

    Returns
    -------
    WikiIndex
        The parsed catalog with last_updated and all entries.

    Raises
    ------
    ValueError
        If the frontmatter block or its `last_updated` field is missing.
    """
    frontmatter_block, body = _split_frontmatter(content)
    last_updated = datetime.fromisoformat(_read_field(frontmatter_block, "last_updated"))
    entries = list(_parse_entries(body))
    return WikiIndex(entries=entries, last_updated=last_updated)


def serialize_index(index: WikiIndex) -> str:
    """Render a WikiIndex as the canonical index.md text.

    Parameters
    ----------
    index : WikiIndex
        Catalog to serialize.

    Returns
    -------
    str
        Markdown content suitable for writing back to index.md. Sections with
        no entries are omitted; section order is fixed by `_SECTION_TO_ENTRY_TYPE`.
    """
    lines: list[str] = [
        _FRONTMATTER_DELIMITER,
        f"last_updated: {index.last_updated.isoformat()}",
        _FRONTMATTER_DELIMITER,
        "",
        "# Wiki Index",
        "",
    ]
    for section, entry_type in _SECTION_TO_ENTRY_TYPE.items():
        entries_for_type = index.find_by_type(entry_type)
        if not entries_for_type:
            continue
        lines.append(f"## {section}")
        lines.extend(entry.to_markdown_link() for entry in entries_for_type)
        lines.append("")
    return "\n".join(lines)


def _split_frontmatter(content: str) -> tuple[str, str]:
    """Split index.md content into its frontmatter block and the markdown body.

    Parameters
    ----------
    content : str
        Full file text. The first line must be a `---` delimiter.

    Returns
    -------
    tuple[str, str]
        (frontmatter_block, body) — both without the surrounding delimiters.

    Raises
    ------
    ValueError
        If the opening or closing `---` delimiter is missing.
    """
    opening, sep, rest = content.partition(f"{_FRONTMATTER_DELIMITER}\n")
    if sep == "" or opening != "":
        raise ValueError("index.md is missing its opening frontmatter delimiter")
    frontmatter_block, sep, body = rest.partition(f"\n{_FRONTMATTER_DELIMITER}\n")
    if sep == "":
        raise ValueError("index.md is missing its closing frontmatter delimiter")
    return frontmatter_block, body


def _read_field(frontmatter_block: str, field: str) -> str:
    """Read a single `key: value` field out of the frontmatter block.

    Parameters
    ----------
    frontmatter_block : str
        Text between the two `---` delimiters.
    field : str
        Field name to look up.

    Returns
    -------
    str
        The trimmed value for `field`.

    Raises
    ------
    ValueError
        If `field` is not present in the block.
    """
    for line in frontmatter_block.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == field:
            return value.strip()
    raise ValueError(f"index.md frontmatter is missing required `{field}` field")


def _parse_entries(body: str) -> list[IndexEntry]:
    """Walk the body line by line, tracking the current section, and collect bullets.

    Parameters
    ----------
    body : str
        Markdown body of index.md with the frontmatter already stripped.

    Returns
    -------
    list[IndexEntry]
        Entries discovered under recognised `## <Section>` headings. Bullets
        under unknown sections are silently skipped.
    """
    entries: list[IndexEntry] = []
    current_type: EntryType | None = None
    for line in body.splitlines():
        if line.startswith("## "):
            current_type = _SECTION_TO_ENTRY_TYPE.get(line[3:].strip())
            continue
        entry = _parse_bullet(line, current_type)
        if entry is not None:
            entries.append(entry)
    return entries


def _parse_bullet(line: str, current_type: EntryType | None) -> IndexEntry | None:
    """Parse a single `- [title](path) — summary` bullet, or return None if the line is not one.

    Parameters
    ----------
    line : str
        A single line from the body of index.md.
    current_type : EntryType | None
        The entry type of the section the line falls under; None for bullets
        outside any recognised section (those are skipped).

    Returns
    -------
    IndexEntry | None
        The parsed entry, or None if `line` is not a well-formed bullet or
        `current_type` is None.
    """
    if current_type is None or not line.startswith("- ["):
        return None
    title, sep, rest = line[3:].partition("](")
    if not sep:
        return None
    path, sep, rest = rest.partition(") — ")
    if not sep:
        return None
    return IndexEntry(title=title, path=path, entry_type=current_type, summary=rest)
