"""Session view manifests (v3.7 L37-3).

Anthropic's UI refresh ships a sidebar (filter / group / open-in-window),
a split view (drag-drop), and three view modes (Plan / Diff / Files).
Lyra's CLI cannot render those visually, but it can ship the *typed
manifest* both the CLI and any web client consume to render
identically — the contract.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Iterable


class ViewKind(str, enum.Enum):
    PLAN = "plan"
    DIFF = "diff"
    FILES = "files"


class GroupBy(str, enum.Enum):
    PROJECT = "project"
    BRANCH = "branch"
    STATUS = "status"
    AGENT = "agent"
    NONE = "none"


@dataclass(frozen=True)
class SessionEntry:
    """One session in the directory."""

    session_id: str
    title: str
    project: str
    branch: str = ""
    status: str = "idle"            # idle / running / waiting / done / error
    agent: str = ""
    started_ts: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class SessionFilter:
    """Sidebar filter spec."""

    project: str = ""               # exact match (empty → any)
    branch: str = ""
    status: str = ""
    text: str = ""                  # substring match against title / project

    def matches(self, entry: SessionEntry) -> bool:
        if self.project and entry.project != self.project:
            return False
        if self.branch and entry.branch != self.branch:
            return False
        if self.status and entry.status != self.status:
            return False
        if self.text:
            t = self.text.lower()
            if t not in entry.title.lower() and t not in entry.project.lower():
                return False
        return True


@dataclass(frozen=True)
class SessionGroup:
    """One group in the sidebar (e.g. by project / branch)."""

    label: str
    entries: tuple[SessionEntry, ...]


@dataclass(frozen=True)
class SplitLayout:
    """Split-view layout spec.

    ``panes`` is an ordered tuple of session_ids. ``orientation`` is
    "horizontal" (side-by-side) or "vertical" (stacked).
    """

    panes: tuple[str, ...]
    orientation: str = "horizontal"

    def __post_init__(self) -> None:
        if self.orientation not in ("horizontal", "vertical"):
            raise ValueError(f"orientation must be horizontal/vertical, got {self.orientation!r}")
        if len(self.panes) != len(set(self.panes)):
            raise ValueError("SplitLayout panes must be unique")


@dataclass(frozen=True)
class ViewManifest:
    """The view a single session is currently surfacing."""

    session_id: str
    kind: ViewKind
    payload: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)


@dataclass
class SessionDirectory:
    """The set of known sessions, with sidebar grouping + filter helpers."""

    entries: list[SessionEntry] = field(default_factory=list)
    views: dict[str, ViewManifest] = field(default_factory=dict)
    layout: SplitLayout = field(
        default_factory=lambda: SplitLayout(panes=(), orientation="horizontal")
    )

    def add(self, entry: SessionEntry) -> None:
        if any(e.session_id == entry.session_id for e in self.entries):
            raise ValueError(f"session {entry.session_id!r} already in directory")
        self.entries.append(entry)

    def remove(self, session_id: str) -> None:
        self.entries = [e for e in self.entries if e.session_id != session_id]
        self.views.pop(session_id, None)

    def filter(self, spec: SessionFilter) -> tuple[SessionEntry, ...]:
        return tuple(e for e in self.entries if spec.matches(e))

    def group_by(self, key: GroupBy,
                 *, filter_spec: SessionFilter | None = None) -> tuple[SessionGroup, ...]:
        items = self.filter(filter_spec) if filter_spec else tuple(self.entries)
        if key is GroupBy.NONE:
            return (SessionGroup(label="all", entries=items),)
        bucket: dict[str, list[SessionEntry]] = {}
        for e in items:
            label = _label_for(e, key) or "(unset)"
            bucket.setdefault(label, []).append(e)
        return tuple(
            SessionGroup(label=label, entries=tuple(entries))
            for label, entries in sorted(bucket.items())
        )

    def set_view(self, session_id: str, kind: ViewKind,
                 *, payload: dict[str, Any] | None = None) -> ViewManifest:
        if not any(e.session_id == session_id for e in self.entries):
            raise KeyError(f"unknown session_id {session_id!r}")
        manifest = ViewManifest(
            session_id=session_id, kind=kind,
            payload=dict(payload or {}),
        )
        self.views[session_id] = manifest
        return manifest

    def get_view(self, session_id: str) -> ViewManifest | None:
        return self.views.get(session_id)

    def set_split_layout(self, layout: SplitLayout) -> None:
        for pane in layout.panes:
            if not any(e.session_id == pane for e in self.entries):
                raise KeyError(f"split pane references unknown session_id {pane!r}")
        self.layout = layout


def _label_for(entry: SessionEntry, key: GroupBy) -> str:
    return {
        GroupBy.PROJECT: entry.project,
        GroupBy.BRANCH: entry.branch,
        GroupBy.STATUS: entry.status,
        GroupBy.AGENT: entry.agent,
    }.get(key, "")


__all__ = [
    "GroupBy",
    "SessionDirectory",
    "SessionEntry",
    "SessionFilter",
    "SessionGroup",
    "SplitLayout",
    "ViewKind",
    "ViewManifest",
]
