"""Parser and serializer for the on-disk log.md chronological record."""

from datetime import datetime
from typing import cast

from wiki_agent.models import LogEntry, LogOperation, WikiLog


def parse_log(content: str) -> WikiLog:
    """Parse log.md content into a WikiLog.

    Parameters
    ----------
    content : str
        Full text of a log.md file. An empty string is treated as a zero-entry log.

    Returns
    -------
    WikiLog
        All entries discovered in the file, in the order they appear (oldest first).
    """
    entries = [_parse_entry_block(block) for block in _split_into_blocks(content)]
    return WikiLog(entries=entries)


def serialize_log(log: WikiLog) -> str:
    """Render a WikiLog as canonical log.md content.

    Parameters
    ----------
    log : WikiLog
        Log to serialize. Entries are written in stored order; the newest
        entry ends up at the bottom of the file.

    Returns
    -------
    str
        Markdown text suitable for writing back to log.md. Empty page lists
        and an absent source produce no bullet line.
    """
    return "\n\n".join(_serialize_entry(entry) for entry in log.entries)


def append_entry(content: str, entry: LogEntry) -> str:
    """Return new log.md content with `entry` appended to the end.

    Designed for append-only writers that want to avoid re-parsing the whole
    file on every event. Preserves whatever is already in `content` (even
    if it doesn't parse cleanly) and joins the new entry with the canonical
    `\\n\\n` separator.

    Parameters
    ----------
    content : str
        Existing log.md text, possibly empty.
    entry : LogEntry
        Entry to append.

    Returns
    -------
    str
        Updated log.md text. No trailing newline — callers control file-level
        newline conventions.
    """
    new_block = _serialize_entry(entry)
    if not content.strip():
        return new_block
    return content.rstrip() + "\n\n" + new_block


def _split_into_blocks(content: str) -> list[list[str]]:
    """Group lines into one block per `## ` header.

    Parameters
    ----------
    content : str
        Full file text.

    Returns
    -------
    list[list[str]]
        Each inner list is the lines of one entry, starting with its `## ` header.
        Any preamble before the first header is dropped.
    """
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in content.splitlines():
        if line.startswith("## "):
            current = [line]
            blocks.append(current)
        elif current is not None:
            current.append(line)
    return blocks


def _parse_entry_block(block: list[str]) -> LogEntry:
    """Parse a `## ` header plus its bullet lines into a LogEntry.

    Parameters
    ----------
    block : list[str]
        Lines belonging to one entry; `block[0]` is the `## ...` header line.

    Returns
    -------
    LogEntry
        The parsed entry. Pydantic validates `operation` against `LogOperation`.

    Raises
    ------
    ValueError
        If the header line does not contain the ` — ` operation separator.
    """
    timestamp_str, sep, operation_str = block[0][3:].partition(" — ")
    if not sep:
        raise ValueError(f"log.md entry header missing operation separator: {block[0]!r}")

    fields: dict[str, str] = {}
    for line in block[1:]:
        if not line.startswith("- "):
            continue
        key, key_sep, value = line[2:].partition(":")
        if key_sep:
            fields[key.strip()] = value.strip()

    return LogEntry(
        timestamp=datetime.fromisoformat(timestamp_str.strip()),
        operation=cast(LogOperation, operation_str.strip()),
        source=fields.get("source"),
        created=_split_paths(fields.get("created", "")),
        updated=_split_paths(fields.get("updated", "")),
        summary=fields.get("summary", ""),
    )


def _split_paths(value: str) -> list[str]:
    """Split a comma-separated path list, dropping empty pieces.

    Parameters
    ----------
    value : str
        Raw bullet value, possibly empty.

    Returns
    -------
    list[str]
        Non-empty path strings with surrounding whitespace removed.
    """
    return [piece.strip() for piece in value.split(",") if piece.strip()]


def _serialize_entry(entry: LogEntry) -> str:
    """Render a single LogEntry as its on-disk markdown block.

    Parameters
    ----------
    entry : LogEntry
        Entry to render.

    Returns
    -------
    str
        Multi-line string starting with `## <iso> — <operation>` followed by
        one bullet per populated field.
    """
    lines: list[str] = [f"## {entry.timestamp.isoformat()} — {entry.operation}"]
    if entry.source is not None:
        lines.append(f"- source: {entry.source}")
    if entry.created:
        lines.append(f"- created: {', '.join(entry.created)}")
    if entry.updated:
        lines.append(f"- updated: {', '.join(entry.updated)}")
    lines.append(f"- summary: {entry.summary}")
    return "\n".join(lines)
