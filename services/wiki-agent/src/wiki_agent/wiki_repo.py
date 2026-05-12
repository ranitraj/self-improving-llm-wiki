"""WikiRepo storage Protocol and a filesystem-backed implementation."""

import logging
from pathlib import Path
from typing import Protocol

from wiki_agent.index_md import parse_index, serialize_index
from wiki_agent.log_md import append_entry, parse_log
from wiki_agent.models import LogEntry, WikiIndex, WikiLog, WikiPage
from wiki_agent.wiki_page_md import parse_page

logger = logging.getLogger(__name__)


class WikiRepo(Protocol):
    """Storage contract for the wiki content repository."""

    def read_index(self) -> WikiIndex:
        """Return the wiki catalog parsed from `index.md`."""

    def write_index(self, index: WikiIndex) -> None:
        """Persist `index` as the new contents of `index.md`."""

    def read_page(self, path: str) -> WikiPage:
        """Return the wiki page stored at the given repo-relative `path`."""

    def write_page(self, page: WikiPage) -> None:
        """Persist `page` at `page.path`, creating parent directories as needed."""

    def list_page_paths(self) -> list[str]:
        """Return all repo-relative paths of pages currently in the wiki."""

    def read_log(self) -> WikiLog:
        """Return the chronological log parsed from `log.md`."""

    def append_log_entry(self, entry: LogEntry) -> None:
        """Append `entry` to `log.md` without rewriting prior history."""


class FilesystemWikiRepo:
    """WikiRepo backed by a working copy on the local filesystem.

    Parameters
    ----------
    root : Path
        Directory containing `index.md`, `log.md`, and the `wiki/` subtree.
        Created lazily on first write — callers do not need to pre-create it.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def read_index(self) -> WikiIndex:
        """Parse `<root>/index.md` into a WikiIndex.

        Returns
        -------
        WikiIndex
            The catalog parsed from disk.

        Raises
        ------
        FileNotFoundError
            If `index.md` does not exist. Callers should rebuild from
            `list_page_paths()` before retrying.
        """
        return parse_index((self.root / "index.md").read_text(encoding="utf-8"))

    def write_index(self, index: WikiIndex) -> None:
        """Serialize `index` and overwrite `<root>/index.md`.

        Parameters
        ----------
        index : WikiIndex
            Catalog to persist. The root directory is created if missing.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "index.md").write_text(serialize_index(index), encoding="utf-8")

    def read_page(self, path: str) -> WikiPage:
        """Read a wiki page from disk into a WikiPage.

        Parameters
        ----------
        path : str
            Repo-relative path, e.g. `wiki/characters/tanjiro.md`.

        Returns
        -------
        WikiPage
            The parsed page with `entry_type` inferred from the path.

        Raises
        ------
        FileNotFoundError
            If the file does not exist at `<root>/<path>`.
        """
        return parse_page(path, (self.root / path).read_text(encoding="utf-8"))

    def write_page(self, page: WikiPage) -> None:
        """Write `page.to_markdown()` to `<root>/<page.path>`, creating parents as needed.

        Parameters
        ----------
        page : WikiPage
            Page to persist. Parent directories are created silently.
        """
        full = self.root / page.path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(page.to_markdown(), encoding="utf-8")

    def list_page_paths(self) -> list[str]:
        """Return every `.md` file under `<root>/wiki/`, sorted, with POSIX separators.

        Returns
        -------
        list[str]
            Repo-relative paths. Empty list when the `wiki/` subdirectory
            does not yet exist (fresh repo).
        """
        wiki_dir = self.root / "wiki"
        if not wiki_dir.is_dir():
            return []
        return sorted(p.relative_to(self.root).as_posix() for p in wiki_dir.rglob("*.md"))

    def read_log(self) -> WikiLog:
        """Parse `<root>/log.md` into a WikiLog, never raising.

        Returns
        -------
        WikiLog
            Parsed log, or an empty `WikiLog` when the file is missing or
            corrupted. Corruption is logged at ERROR; missing-file at INFO.
            On-disk content is never destroyed — `append_log_entry` will
            preserve a corrupted file by appending after it.
        """
        log_path = self.root / "log.md"
        try:
            content = log_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.info("log.md not found at %s; treating as empty log", log_path)
            return WikiLog(entries=[])
        try:
            return parse_log(content)
        except ValueError as exc:
            logger.error("failed to parse log.md at %s, returning empty log: %s", log_path, exc)
            return WikiLog(entries=[])

    def append_log_entry(self, entry: LogEntry) -> None:
        """Append `entry` to `<root>/log.md` without re-parsing existing content.

        Parameters
        ----------
        entry : LogEntry
            New event to record at the end of the log. The root directory
            and `log.md` are created if missing. A corrupted existing log
            is preserved verbatim — the new entry is added after it.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        log_path = self.root / "log.md"
        try:
            existing = log_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            existing = ""
        log_path.write_text(append_entry(existing, entry) + "\n", encoding="utf-8")
