"""Page document surface — immutable snapshots + versioned timeline.

Design notes:
    - Snapshots are *content-addressable* by version; diff summaries are
      computed at edit time so the timeline can be displayed without re-diffing.
    - Authors are typed strings ``"agent:<name>"`` / ``"user:<id>"`` so the
      page can render the timeline with role-aware iconography.
    - Conflicts surface when two edits share the same parent version; this is
      the substrate for branching (the consumer surfaces them as Lobe-style
      branches, or auto-merges).
    - Production wires diff/merge to a real diff library (e.g., ``difflib`` or
      ``diff-match-patch``); the in-process default uses a line-set heuristic.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Iterable, Optional


@dataclass(frozen=True)
class PageSnapshot:
    """One immutable snapshot of a page.

    >>> s = PageSnapshot(page_id="p1", content="hello", author="user:alice",
    ...                   version=1, parent_version=None)
    >>> s.version
    1
    """

    page_id: str
    content: str
    author: str  # "user:<id>" | "agent:<name>"
    version: int
    parent_version: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    diff_summary: str = ""
    note: str = ""  # optional human-readable note about the edit

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError(f"version must be >= 1, got {self.version}")
        if self.version == 1 and self.parent_version is not None:
            raise ValueError("version-1 snapshot cannot have a parent_version")
        if self.version > 1 and self.parent_version is None:
            raise ValueError(f"version > 1 must have a parent_version (got {self.version})")
        if not self.author:
            raise ValueError("author must be non-empty")

    @property
    def is_user_edit(self) -> bool:
        return self.author.startswith("user:")

    @property
    def is_agent_edit(self) -> bool:
        return self.author.startswith("agent:")


def line_diff_summary(old: str, new: str) -> str:
    """Compact line-set summary of two strings.

    Returns ``+N -M`` (lines added, lines removed) — useful for compact
    timeline display without computing a full diff. Production wires
    ``difflib`` or similar for richer diffs.
    """
    old_lines = set(old.splitlines())
    new_lines = set(new.splitlines())
    added = len(new_lines - old_lines)
    removed = len(old_lines - new_lines)
    return f"+{added} -{removed}"


@dataclass(frozen=True)
class EditConflict:
    """Two snapshots with the same parent_version — concurrent edit conflict.

    A consumer (host harness) decides what to do: surface as Lobe-style
    branches, auto-merge, or raise to the user.
    """

    page_id: str
    parent_version: int
    versions_in_conflict: tuple[int, ...]


@dataclass
class PageHistory:
    """Timeline of immutable snapshots for one page.

    >>> h = PageHistory(page_id="p1")
    >>> s1 = h.append_snapshot(PageSnapshot(
    ...     page_id="p1", content="hello", author="user:alice", version=1))
    >>> h.current.content
    'hello'
    """

    page_id: str
    snapshots: list[PageSnapshot] = field(default_factory=list)

    def append_snapshot(self, snapshot: PageSnapshot) -> PageSnapshot:
        if snapshot.page_id != self.page_id:
            raise ValueError(
                f"snapshot.page_id={snapshot.page_id!r} != history.page_id={self.page_id!r}"
            )
        # Prevent duplicate versions.
        if any(s.version == snapshot.version for s in self.snapshots):
            raise ValueError(f"version {snapshot.version} already in history")
        self.snapshots.append(snapshot)
        return snapshot

    @property
    def current(self) -> Optional[PageSnapshot]:
        """The latest snapshot by version. None if history is empty."""
        if not self.snapshots:
            return None
        return max(self.snapshots, key=lambda s: s.version)

    def at_version(self, version: int) -> Optional[PageSnapshot]:
        for s in self.snapshots:
            if s.version == version:
                return s
        return None

    def linear_chain(self) -> list[PageSnapshot]:
        """Return snapshots that form the canonical linear chain.

        The chain follows ``parent_version`` from the current head back to
        version 1. Branches (snapshots not on this chain) are excluded.
        """
        if not self.snapshots:
            return []
        chain: list[PageSnapshot] = []
        head = self.current
        while head is not None:
            chain.append(head)
            if head.parent_version is None:
                break
            head = self.at_version(head.parent_version)
        chain.reverse()
        return chain

    def conflicts(self) -> list[EditConflict]:
        """Detect concurrent edits — multiple snapshots with the same parent."""
        by_parent: dict[Optional[int], list[int]] = {}
        for s in self.snapshots:
            by_parent.setdefault(s.parent_version, []).append(s.version)
        conflicts: list[EditConflict] = []
        for parent_v, versions in by_parent.items():
            if parent_v is None:
                # Multiple version-1s would also conflict; collect them.
                if len(versions) > 1:
                    conflicts.append(EditConflict(
                        page_id=self.page_id,
                        parent_version=0,  # sentinel for "root"
                        versions_in_conflict=tuple(sorted(versions)),
                    ))
                continue
            if len(versions) > 1:
                conflicts.append(EditConflict(
                    page_id=self.page_id,
                    parent_version=parent_v,
                    versions_in_conflict=tuple(sorted(versions)),
                ))
        return conflicts

    def authors(self) -> list[str]:
        """Distinct authors in chronological order."""
        seen: set[str] = set()
        ordered: list[str] = []
        for s in sorted(self.snapshots, key=lambda x: x.created_at):
            if s.author not in seen:
                seen.add(s.author)
                ordered.append(s.author)
        return ordered

    def stats(self) -> dict[str, int]:
        return {
            "snapshots": len(self.snapshots),
            "user_edits": sum(1 for s in self.snapshots if s.is_user_edit),
            "agent_edits": sum(1 for s in self.snapshots if s.is_agent_edit),
            "conflicts": len(self.conflicts()),
            "authors": len(self.authors()),
        }


@dataclass
class Page:
    """A page — wrapper that pairs ``page_id`` with its :class:`PageHistory`."""

    page_id: str
    history: PageHistory = field(init=False)

    def __post_init__(self) -> None:
        self.history = PageHistory(page_id=self.page_id)


@dataclass
class PageEditor:
    """Controller that produces new snapshots from edits.

    >>> editor = PageEditor(history=PageHistory(page_id="p1"))
    >>> s1 = editor.create(content="hello world", author="user:alice")
    >>> s2 = editor.edit(content="hello world!", author="agent:bot")
    >>> s2.parent_version
    1
    >>> s2.version
    2
    """

    history: PageHistory

    def create(
        self,
        *,
        content: str,
        author: str,
        note: str = "",
    ) -> PageSnapshot:
        """Create the first version of a page."""
        if self.history.current is not None:
            raise RuntimeError(
                "history is non-empty; use edit(...) instead of create(...)"
            )
        snap = PageSnapshot(
            page_id=self.history.page_id,
            content=content,
            author=author,
            version=1,
            parent_version=None,
            diff_summary=line_diff_summary("", content),
            note=note,
        )
        self.history.append_snapshot(snap)
        return snap

    def edit(
        self,
        *,
        content: str,
        author: str,
        parent_version: Optional[int] = None,
        note: str = "",
    ) -> PageSnapshot:
        """Append a new snapshot.

        ``parent_version`` defaults to the current head; supply explicitly to
        produce a concurrent edit (creates an :class:`EditConflict`).
        """
        current = self.history.current
        if current is None:
            raise RuntimeError("history is empty; use create(...) first")

        parent_v = parent_version if parent_version is not None else current.version
        parent_snap = self.history.at_version(parent_v)
        if parent_snap is None:
            raise ValueError(f"parent_version {parent_v} not in history")

        new_version = max(s.version for s in self.history.snapshots) + 1
        snap = PageSnapshot(
            page_id=self.history.page_id,
            content=content,
            author=author,
            version=new_version,
            parent_version=parent_v,
            diff_summary=line_diff_summary(parent_snap.content, content),
            note=note,
        )
        self.history.append_snapshot(snap)
        return snap

    def revert_to(self, *, version: int, author: str, note: str = "") -> PageSnapshot:
        """Revert to a past version by appending a new snapshot with that content."""
        target = self.history.at_version(version)
        if target is None:
            raise ValueError(f"version {version} not in history")
        return self.edit(
            content=target.content,
            author=author,
            note=note or f"reverted to version {version}",
        )

    def diff(self, *, from_version: int, to_version: int) -> str:
        """Compact diff summary between two versions."""
        a = self.history.at_version(from_version)
        b = self.history.at_version(to_version)
        if a is None or b is None:
            raise ValueError(
                f"missing version: from={from_version} to={to_version}"
            )
        return line_diff_summary(a.content, b.content)


__all__ = [
    "EditConflict",
    "Page",
    "PageEditor",
    "PageHistory",
    "PageSnapshot",
    "line_diff_summary",
]
