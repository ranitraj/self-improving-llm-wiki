"""Pydantic data models for wiki pages, index, and operation results."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator

from wiki_agent.constants import TELEGRAM_MESSAGE_LIMIT

EntryType = Literal[
    "character",
    "episode",
    "arc",
    "breathing_style",
    "blood_demon_art",
    "location",
    "organization",
]


class WikiPage(BaseModel):
    """A single LLM-generated wiki page with frontmatter and markdown body.

    Parameters
    ----------
    entry_type : EntryType
        Category of the wiki entry — must be one of the seven known types.
    path : str
        Repo-relative path to the markdown file (must not start with '/').
    frontmatter : dict
        Parsed YAML frontmatter fields for this entry type.
    body : str
        Markdown body content below the frontmatter.
    """

    entry_type: EntryType
    path: str
    frontmatter: dict[str, Any]
    body: str

    @field_validator("path")
    @classmethod
    def _path_must_be_relative(cls, path: str) -> str:
        """Reject absolute paths to enforce repo-relative convention.

        Parameters
        ----------
        path : str
            The path value to validate.

        Returns
        -------
        str
            The validated path.

        Raises
        ------
        ValueError
            If the path starts with '/'.
        """
        if path.startswith("/"):
            raise ValueError("path must be repo-relative, not absolute")
        return path

    def to_markdown(self) -> str:
        """Render the page as a full markdown string with YAML frontmatter block.

        Returns
        -------
        str
            The complete markdown content ready to be written to a .md file.
        """
        frontmatter_lines = "\n".join(f"{k}: {v}" for k, v in self.frontmatter.items())
        return f"---\n{frontmatter_lines}\n---\n{self.body}"

    def file_name(self) -> str:
        """Return the bare filename from the repo-relative path.

        Returns
        -------
        str
            The filename component, e.g. 'tanjiro.md'.
        """
        return self.path.split("/")[-1]


class IndexEntry(BaseModel):
    """A single line in index.md representing one wiki page.

    Parameters
    ----------
    title : str
        Display title of the page.
    path : str
        Repo-relative path to the markdown file.
    entry_type : EntryType
        Category of the wiki entry.
    summary : str
        One-line summary — kept short for token efficiency.
    """

    title: str
    path: str
    entry_type: EntryType
    summary: str

    def to_markdown_link(self) -> str:
        """Render this entry as a markdown list item with an inline link.

        Returns
        -------
        str
            Formatted string, e.g. '- [Tanjiro](wiki/characters/tanjiro.md) — Protagonist'.
        """
        return f"- [{self.title}]({self.path}) — {self.summary}"

    def matches_path(self, path: str) -> bool:
        """Return True if this entry's path matches the given repo-relative path.

        Parameters
        ----------
        path : str
            Repo-relative path to compare against.

        Returns
        -------
        bool
            True if the paths are equal.
        """
        return self.path == path


class WikiIndex(BaseModel):
    """Catalog of all wiki pages loaded from index.md.

    Parameters
    ----------
    entries : list[IndexEntry]
        All known wiki pages.
    last_updated : datetime
        Timestamp of the last index rebuild.
    """

    entries: list[IndexEntry]
    last_updated: datetime

    def is_stale(self, log_updated_at: datetime) -> bool:
        """Return True if the log has entries newer than this index.

        Parameters
        ----------
        log_updated_at : datetime
            Timestamp of the most recent entry in log.md.

        Returns
        -------
        bool
            True if the index predates the latest log entry.
        """
        return self.last_updated < log_updated_at

    def find_by_type(self, entry_type: EntryType) -> list[IndexEntry]:
        """Return all index entries matching the given entry type.

        Parameters
        ----------
        entry_type : EntryType
            The entry type to filter by.

        Returns
        -------
        list[IndexEntry]
            All entries whose entry_type matches.
        """
        return [e for e in self.entries if e.entry_type == entry_type]

    def find_by_path(self, path: str) -> IndexEntry | None:
        """Return the index entry for a given repo-relative path, or None.

        Parameters
        ----------
        path : str
            Repo-relative path to look up.

        Returns
        -------
        IndexEntry | None
            The matching entry, or None if not found.
        """
        return next((e for e in self.entries if e.matches_path(path)), None)


class IngestResult(BaseModel):
    """Result of a wiki_ingest operation.

    Parameters
    ----------
    pages_created : list[str]
        Repo-relative paths of newly created wiki pages.
    pages_updated : list[str]
        Repo-relative paths of existing pages that were updated.
    log_entry : str
        The formatted string appended to log.md.
    """

    pages_created: list[str]
    pages_updated: list[str]
    log_entry: str

    def total_pages_touched(self) -> int:
        """Return the total number of pages created or updated during this ingest.

        Returns
        -------
        int
            Sum of created and updated page counts.
        """
        return len(self.pages_created) + len(self.pages_updated)

    def is_empty(self) -> bool:
        """Return True if the ingest produced no changes to the wiki.

        Returns
        -------
        bool
            True when no pages were created or updated.
        """
        return self.total_pages_touched() == 0


class QueryResult(BaseModel):
    """Result of a wiki_query operation.

    Parameters
    ----------
    answer : str
        Synthesized answer from wiki page content.
    source_pages : list[str]
        Repo-relative paths of pages used to generate the answer.
    new_page_filed : bool
        Whether the answer was filed as a new wiki page, by default False.
    """

    answer: str
    source_pages: list[str]
    new_page_filed: bool = False

    def split_for_telegram(self) -> list[str]:
        """Split the answer into chunks that fit within Telegram's message limit.

        Returns
        -------
        list[str]
            One or more message strings, each at most 4096 characters.
        """
        return [
            self.answer[i : i + TELEGRAM_MESSAGE_LIMIT] for i in range(0, len(self.answer), TELEGRAM_MESSAGE_LIMIT)
        ]

    def has_sources(self) -> bool:
        """Return True if the answer was synthesized from at least one wiki page.

        Returns
        -------
        bool
            True when source_pages is non-empty.
        """
        return len(self.source_pages) > 0


class LintResult(BaseModel):
    """Result of a wiki_lint operation.

    Parameters
    ----------
    issues_found : int
        Total number of issues detected.
    issues_fixed : int
        Number of issues resolved by the lint pass.
    pages_created : list[str]
        Repo-relative paths of pages created to fill gaps found during lint.
    summary : str
        Human-readable summary sent as a Telegram notification.
    """

    issues_found: int
    issues_fixed: int
    pages_created: list[str]
    summary: str

    def has_issues(self) -> bool:
        """Return True if the lint pass found at least one issue.

        Returns
        -------
        bool
            True when issues_found is greater than zero.
        """
        return self.issues_found > 0

    def fix_rate(self) -> float:
        """Return the fraction of detected issues that were resolved.

        Returns
        -------
        float
            Value between 0.0 and 1.0, or 0.0 if no issues were found.
        """
        if self.issues_found == 0:
            return 0.0
        return self.issues_fixed / self.issues_found
