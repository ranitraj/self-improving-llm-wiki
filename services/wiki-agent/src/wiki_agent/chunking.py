"""Split large markdown text into chunks at H2 boundaries for Claude's context window."""

import logging

logger = logging.getLogger(__name__)


def chunk_text_by_h2(text: str, max_tokens: int) -> list[str]:
    """Return `text` split into chunks no larger than `max_tokens` approximate tokens.

    Chunks are cut at `## ` (H2) line boundaries. If the input already fits
    within `max_tokens`, it is returned as a single-element list. If the input
    exceeds the threshold but contains no H2 headings to split on, the input
    is returned as a single chunk and a `logging.WARNING` is emitted so the
    operator can investigate (Claude's own context window is the final guard).

    Token counts are approximate — derived from a `len(text) // 4` heuristic
    rather than a real tokenizer. Good enough for chunk-routing decisions
    and avoids pulling in `tiktoken`.

    Parameters
    ----------
    text : str
        Markdown text to chunk.
    max_tokens : int
        Soft upper bound on each chunk's approximate token count. A single
        H2 section that is itself larger than the threshold becomes one
        oversized chunk — H2 boundaries are the only split points.

    Returns
    -------
    list[str]
        One or more chunks whose concatenation equals `text` exactly. Each
        chunk begins at an H2 boundary when splitting was possible.
    """
    if _approx_tokens(text) <= max_tokens:
        return [text]

    sections = _split_into_h2_sections(text)
    if len(sections) <= 1:
        logger.warning(
            "could not split text — no H2 boundaries found and text exceeds %d-token threshold (%d approx tokens)",
            max_tokens,
            _approx_tokens(text),
        )
        return [text]

    return _pack_sections_into_chunks(sections, max_tokens)


def _split_into_h2_sections(text: str) -> list[str]:
    """Group lines into H2 sections, where each section starts at a `## ` line.

    Parameters
    ----------
    text : str
        Markdown text.

    Returns
    -------
    list[str]
        Sections in order, joined with `\\n` line endings preserved. Any
        preamble before the first `## ` line is its own first section
        (without an H2 prefix).
    """
    sections: list[list[str]] = []
    current: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("## ") and current:
            sections.append(current)
            current = []
        current.append(line)
    if current:
        sections.append(current)
    return ["".join(section) for section in sections]


def _pack_sections_into_chunks(sections: list[str], max_tokens: int) -> list[str]:
    """Greedily concatenate sections into chunks, flushing whenever adding the next section would exceed `max_tokens`.

    Parameters
    ----------
    sections : list[str]
        H2 sections in order.
    max_tokens : int
        Soft upper bound per chunk.

    Returns
    -------
    list[str]
        Packed chunks. A single section larger than `max_tokens` becomes a
        chunk on its own — better than discarding it.
    """
    chunks: list[str] = []
    current = ""
    for section in sections:
        if current and _approx_tokens(current + section) > max_tokens:
            chunks.append(current)
            current = section
        else:
            current += section
    if current:
        chunks.append(current)
    return chunks


def _approx_tokens(text: str) -> int:
    """Return an approximate token count using the `len // 4` industry heuristic.

    Parameters
    ----------
    text : str
        Text to measure.

    Returns
    -------
    int
        Estimated token count.
    """
    return len(text) // 4
