"""Parser and serializer for the on-disk index.md catalog."""

from datetime import datetime

from wiki_agent.models import EntryType, IndexEntry, WikiIndex
from wiki_agent.utils.frontmatter import parse_fields, split_frontmatter
from wiki_agent.utils.wiki_layout import WIKI_CATEGORIES, entry_type_for_section


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
    block, body = split_frontmatter(content)
    fields = parse_fields(block)
    if "last_updated" not in fields:
        raise ValueError("index.md frontmatter is missing required `last_updated` field")
    last_updated = datetime.fromisoformat(fields["last_updated"])
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
        no entries are omitted; section order is fixed by `WIKI_CATEGORIES`.
    """
    lines: list[str] = [
        "---",
        f"last_updated: {index.last_updated.isoformat()}",
        "---",
        "",
        "# Wiki Index",
        "",
    ]
    for category in WIKI_CATEGORIES:
        entries_for_type = index.find_by_type(category.entry_type)
        if not entries_for_type:
            continue
        lines.append(f"## {category.section}")
        lines.extend(entry.to_markdown_link() for entry in entries_for_type)
        lines.append("")
    return "\n".join(lines)


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
            current_type = entry_type_for_section(line[3:].strip())
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
