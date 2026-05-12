"""Parser for individual wiki page markdown files."""

from wiki_agent.models import EntryType, WikiPage
from wiki_agent.utils.frontmatter import parse_fields, split_frontmatter
from wiki_agent.utils.wiki_layout import entry_type_for_path_segment


def parse_page(path: str, content: str) -> WikiPage:
    """Parse a wiki page's markdown text into a WikiPage.

    Parameters
    ----------
    path : str
        Repo-relative path of the page (e.g. `wiki/characters/tanjiro.md`).
        The second segment determines `entry_type` via `wiki_layout`.
    content : str
        Full markdown content of the page, starting with a `---` frontmatter block.

    Returns
    -------
    WikiPage
        The parsed page. `frontmatter` values are strings — type coercion is
        the caller's responsibility.

    Raises
    ------
    ValueError
        If the path's category segment is not one of the seven known entry
        types, or the frontmatter delimiters are missing.
    """
    entry_type = _entry_type_for_path(path)
    block, body = split_frontmatter(content)
    return WikiPage(
        entry_type=entry_type,
        path=path,
        frontmatter=dict(parse_fields(block)),
        body=body,
    )


def _entry_type_for_path(path: str) -> EntryType:
    """Infer EntryType from the second segment of a repo-relative wiki path.

    Parameters
    ----------
    path : str
        Repo-relative path; expected shape is `wiki/<category>/<file>.md`.

    Returns
    -------
    EntryType
        The matching entry type.

    Raises
    ------
    ValueError
        If the path has fewer than two segments or the category segment is unknown.
    """
    segments = path.split("/")
    if len(segments) < 2:
        raise ValueError(f"wiki page path must include a category segment: {path!r}")
    entry_type = entry_type_for_path_segment(segments[1])
    if entry_type is None:
        raise ValueError(f"unknown entry type for category segment {segments[1]!r} in path {path!r}")
    return entry_type
