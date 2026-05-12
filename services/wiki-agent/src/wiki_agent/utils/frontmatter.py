"""Shared helpers for the `---` YAML frontmatter block used by index.md and wiki pages."""

_DELIMITER = "---"


def split_frontmatter(content: str) -> tuple[str, str]:
    """Split markdown content into its frontmatter block and the trailing body.

    Parameters
    ----------
    content : str
        Full file text. The first line must be a `---` delimiter, and a
        matching closing `---` line must follow.

    Returns
    -------
    tuple[str, str]
        (frontmatter_block, body) — both without the surrounding delimiters.

    Raises
    ------
    ValueError
        If the opening or closing `---` delimiter is missing.
    """
    opening, sep, rest = content.partition(f"{_DELIMITER}\n")
    if not sep or opening != "":
        raise ValueError("content is missing its opening frontmatter delimiter")
    block, sep, body = rest.partition(f"\n{_DELIMITER}\n")
    if not sep:
        raise ValueError("content is missing its closing frontmatter delimiter")
    return block, body


def parse_fields(block: str) -> dict[str, str]:
    """Parse a frontmatter block into a `{key: value}` dict of stripped strings.

    Values are returned as-is (strings). Type coercion (datetime, int, etc.)
    is the caller's responsibility — we don't have a YAML dependency.

    Parameters
    ----------
    block : str
        Text between the two `---` delimiters.

    Returns
    -------
    dict[str, str]
        One entry per `key: value` line. Lines without a `:` are skipped.
    """
    fields: dict[str, str] = {}
    for line in block.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields
