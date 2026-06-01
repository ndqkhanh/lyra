"""Snapshot engine — capture, diff, replay, serialize, save/load pane content."""

from __future__ import annotations

import json
import os
from typing import Sequence

from lyra_rmux.models import Snapshot


class SnapshotEngine:
    """Captures pane content as frozen snapshots and provides diff/replay."""

    def __init__(self, archive_dir: str | None = None) -> None:
        self._archive: dict[str, list[Snapshot]] = {}
        self._archive_dir = archive_dir or os.path.join(os.path.expanduser("~"), ".lyra-rmux", "snapshots")

    # ------------------------------------------------------------------
    # capture
    # ------------------------------------------------------------------

    def capture(self, pane_id: str, lines: Sequence[str]) -> Snapshot:
        """Create a new snapshot for *pane_id* and archive it."""
        snap = Snapshot(
            pane_id=pane_id,
            lines=tuple(lines),
            cursor_row=len(lines) - 1 if lines else 0,
            cursor_col=len(lines[-1]) if lines else 0,
            scrollback_rows=0,
        )
        self._archive.setdefault(pane_id, []).append(snap)
        return snap

    # ------------------------------------------------------------------
    # diff
    # ------------------------------------------------------------------

    def diff(self, pane_id: str) -> str | None:
        """Return a unified-diff-style string between the last two snapshots.

        Returns None if fewer than 2 snapshots exist for *pane_id*.
        """
        history = self._archive.get(pane_id)
        if not history or len(history) < 2:
            return None
        old = history[-2]
        new = history[-1]
        return self._compute_diff(old.lines, new.lines)

    @staticmethod
    def _compute_diff(old_lines: tuple[str, ...], new_lines: tuple[str, ...]) -> str:
        """Simple line-by-line diff (no external dep)."""
        result: list[str] = []
        i = j = 0
        while i < len(old_lines) or j < len(new_lines):
            if i < len(old_lines) and j < len(new_lines) and old_lines[i] == new_lines[j]:
                result.append(f" {old_lines[i]}")
                i += 1
                j += 1
            elif j < len(new_lines) and (i >= len(old_lines) or new_lines[j] != old_lines[i]):
                result.append(f"+{new_lines[j]}")
                j += 1
            else:
                result.append(f"-{old_lines[i]}")
                i += 1
        return "\n".join(result)

    def diff_between(self, pane_id: str, snap_a: Snapshot, snap_b: Snapshot) -> str:
        """Diff two arbitrary snapshots."""
        return self._compute_diff(snap_a.lines, snap_b.lines)

    # ------------------------------------------------------------------
    # replay
    # ------------------------------------------------------------------

    def replay(self, pane_id: str) -> list[str] | None:
        """Return the accumulated lines for *pane_id* as a replay timeline.

        Each entry is a timestamped snapshot summary of the form::

            "[N lines] first line ..."
        """
        history = self._archive.get(pane_id)
        if not history:
            return None
        timeline: list[str] = []
        for i, snap in enumerate(history):
            preview = snap.lines[0][:60] if snap.lines else "(empty)"
            timeline.append(f"[{i}] ({len(snap.lines)} lines) {preview}")
        return timeline

    # ------------------------------------------------------------------
    # serialize / deserialize
    # ------------------------------------------------------------------

    def serialize_snapshot(self, snap: Snapshot) -> str:
        """Serialize a snapshot to JSON."""
        return json.dumps({
            "pane_id": snap.pane_id,
            "lines": list(snap.lines),
            "cursor_row": snap.cursor_row,
            "cursor_col": snap.cursor_col,
            "scrollback_rows": snap.scrollback_rows,
        })

    def deserialize_snapshot(self, raw: str) -> Snapshot:
        """Deserialize a snapshot from JSON."""
        d = json.loads(raw)
        return Snapshot(
            pane_id=d["pane_id"],
            lines=tuple(d["lines"]),
            cursor_row=d["cursor_row"],
            cursor_col=d["cursor_col"],
            scrollback_rows=d["scrollback_rows"],
        )

    # ------------------------------------------------------------------
    # save / load (whole archive)
    # ------------------------------------------------------------------

    def save(self, path: str | None = None) -> str:
        """Save the entire snapshot archive to a JSON file.

        Returns the path written.
        """
        dest = path or os.path.join(self._archive_dir, "archive.json")
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        payload: dict[str, list] = {}
        for pane_id, snaps in self._archive.items():
            payload[pane_id] = [json.loads(self.serialize_snapshot(s)) for s in snaps]

        with open(dest, "w") as f:
            json.dump(payload, f, indent=2)
        return dest

    def load(self, path: str | None = None) -> int:
        """Load snapshot archive from a JSON file.

        Returns the number of snapshots loaded.
        """
        src = path or os.path.join(self._archive_dir, "archive.json")
        if not os.path.isfile(src):
            return 0

        with open(src) as f:
            payload: dict[str, list] = json.load(f)

        count = 0
        for pane_id, snaps in payload.items():
            for entry in snaps:
                snap = Snapshot(
                    pane_id=entry["pane_id"],
                    lines=tuple(entry["lines"]),
                    cursor_row=entry["cursor_row"],
                    cursor_col=entry["cursor_col"],
                    scrollback_rows=entry["scrollback_rows"],
                )
                self._archive.setdefault(pane_id, []).append(snap)
                count += 1
        return count

    # ------------------------------------------------------------------
    # utilities
    # ------------------------------------------------------------------

    def history(self, pane_id: str, limit: int = 0) -> Sequence[Snapshot]:
        """Return the snapshot history for a pane (most recent first)."""
        snaps = self._archive.get(pane_id, [])
        if limit > 0:
            snaps = snaps[-limit:]
        return list(snaps)

    def clear(self, pane_id: str | None = None) -> None:
        """Clear snapshot history for a pane, or all panes."""
        if pane_id:
            self._archive.pop(pane_id, None)
        else:
            self._archive.clear()

    def snapshot_count(self, pane_id: str | None = None) -> int:
        """Count archived snapshots."""
        if pane_id:
            return len(self._archive.get(pane_id, []))
        return sum(len(v) for v in self._archive.values())
