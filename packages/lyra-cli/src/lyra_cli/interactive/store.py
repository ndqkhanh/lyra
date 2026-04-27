"""Session persistence — JSON snapshots under ``.lyra/sessions/``.

Claude-Code-style ``/resume`` and ``/fork`` both live here. The on-disk
format is pure JSON so external tooling can diff / display / migrate
snapshots without depending on Lyra's Python types.

File layout::

    <repo>/.lyra/sessions/
        index.json                       # [{id, name, turn, saved_at}, ...]
        2026-04-22T12-30-04-123456.json  # one snapshot per file, sorted lexically

A snapshot captures everything :class:`~.session.InteractiveSession`
holds, minus the private ``_turns_log`` (which we serialise explicitly
because ``dataclasses.asdict`` recurses through it correctly only if
the nested ``_TurnSnapshot`` stays a ``dataclass``).

Design choices:

- **One JSON file per snapshot**. Easy to ``cat``, ``git diff``, and
  deletes don't require rewriting everything.
- **ISO-8601 basename**. Chronological sort = insertion order without
  an extra index field.
- **Index for O(1) list**. The driver calls ``list_sessions()`` on every
  ``/sessions`` render and we don't want to rescan the directory.
- **No schema migration today** — format version ``1``; bumps land with
  persistence features (Phase 9 HIR, v1.7 skill-creator, …).
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .session import InteractiveSession, _TurnSnapshot


_FORMAT_VERSION = 1


def sessions_dir(repo_root: Path) -> Path:
    return repo_root / ".lyra" / "sessions"


def save(session: InteractiveSession, *, name: str | None = None) -> Path:
    """Persist ``session`` to a new JSON snapshot. Returns the file path."""
    folder = sessions_dir(session.repo_root)
    folder.mkdir(parents=True, exist_ok=True)

    saved_at = datetime.now(timezone.utc)
    # Microsecond precision so back-to-back saves (e.g. /fork right after a
    # turn) get unique filenames — a second-precision id collided in tests
    # and would have collided in real use the first time a user fired two
    # snapshots in the same second.
    snapshot_id = saved_at.strftime("%Y-%m-%dT%H-%M-%S-%f")
    path = folder / f"{snapshot_id}.json"

    # Avoid ``asdict(session)`` because the ``_turns_log`` field wouldn't
    # round-trip cleanly on load (``_TurnSnapshot`` isn't exposed). We
    # serialise by hand so the JSON shape is explicit + documented.
    payload: dict[str, Any] = {
        "format": _FORMAT_VERSION,
        "id": snapshot_id,
        "name": name or f"session-{session.turn}",
        "saved_at": saved_at.isoformat(),
        "repo_root": str(session.repo_root),
        "state": {
            "model": session.model,
            "mode": session.mode,
            "turn": session.turn,
            "cost_usd": session.cost_usd,
            "tokens_used": session.tokens_used,
            "history": list(session.history),
            "pending_task": session.pending_task,
            "deep_think": session.deep_think,
            "verbose": session.verbose,
            "vim_mode": session.vim_mode,
            "theme": session.theme,
            "budget_cap_usd": session.budget_cap_usd,
            "task_panel": session.task_panel,
            "turns_log": [asdict(t) for t in session._turns_log],
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    _update_index(folder, snapshot_id, payload["name"], session.turn, saved_at)
    return path


def load(
    repo_root: Path, snapshot_id: str | None = None
) -> InteractiveSession:
    """Load a snapshot. ``None`` means "the most recent one"."""
    folder = sessions_dir(repo_root)
    target = _resolve_snapshot(folder, snapshot_id)
    raw = json.loads(target.read_text(encoding="utf-8"))
    state = raw["state"]
    session = InteractiveSession(
        repo_root=Path(raw.get("repo_root", repo_root)),
        model=state.get("model", "auto"),
        mode=state.get("mode", "plan"),
        turn=int(state.get("turn", 0)),
        cost_usd=float(state.get("cost_usd", 0.0)),
        tokens_used=int(state.get("tokens_used", 0)),
        history=list(state.get("history", [])),
        pending_task=state.get("pending_task"),
        deep_think=bool(state.get("deep_think", False)),
        verbose=bool(state.get("verbose", False)),
        vim_mode=bool(state.get("vim_mode", False)),
        theme=str(state.get("theme", "aurora")),
        budget_cap_usd=state.get("budget_cap_usd"),
        task_panel=bool(state.get("task_panel", False)),
    )
    for entry in state.get("turns_log", []):
        session._turns_log.append(
            _TurnSnapshot(
                line=entry.get("line", ""),
                mode=entry.get("mode", session.mode),
                turn=int(entry.get("turn", session.turn)),
                pending_task=entry.get("pending_task"),
                cost_usd=float(entry.get("cost_usd", 0.0)),
                tokens_used=int(entry.get("tokens_used", 0)),
            )
        )
    return session


def list_sessions(repo_root: Path) -> list[dict[str, Any]]:
    """Return ``[{id, name, turn, saved_at, path}, ...]`` newest-first."""
    folder = sessions_dir(repo_root)
    index = folder / "index.json"
    if not index.exists():
        return []
    try:
        payload = json.loads(index.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    entries = payload.get("entries", [])
    out: list[dict[str, Any]] = []
    for entry in entries:
        out.append(
            {
                "id": entry["id"],
                "name": entry.get("name", entry["id"]),
                "turn": int(entry.get("turn", 0)),
                "saved_at": entry.get("saved_at", ""),
                "path": str(folder / f"{entry['id']}.json"),
            }
        )
    out.sort(key=lambda e: e["saved_at"], reverse=True)
    return out


def fork(
    session: InteractiveSession, *, name: str
) -> Path:
    """Save a forked snapshot under ``name`` — alias for :func:`save`.

    Kept as a named helper so the ``/fork`` audit trail is explicit: a
    fork is always a *new* snapshot of the current session, never a
    copy of the parent file.
    """
    return save(session, name=name)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _resolve_snapshot(folder: Path, snapshot_id: str | None) -> Path:
    if snapshot_id is None:
        candidates = sorted(folder.glob("*.json"))
        # Skip the index file itself.
        candidates = [c for c in candidates if c.name != "index.json"]
        if not candidates:
            raise FileNotFoundError(
                f"no saved sessions under {folder}. "
                f"save one first with /fork or on exit."
            )
        return candidates[-1]

    direct = folder / f"{snapshot_id}.json"
    if direct.exists():
        return direct

    # Allow matching by name too (e.g. ``/resume fork-3``).
    for entry in list_sessions(folder.parent.parent):
        if entry["name"] == snapshot_id:
            return Path(entry["path"])

    raise FileNotFoundError(
        f"snapshot {snapshot_id!r} not found under {folder}. "
        f"run /sessions to list available ids + names."
    )


def _update_index(
    folder: Path,
    snapshot_id: str,
    name: str,
    turn: int,
    saved_at: datetime,
) -> None:
    index = folder / "index.json"
    if index.exists():
        try:
            payload = json.loads(index.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"entries": []}
    else:
        payload = {"entries": []}

    entries = [e for e in payload.get("entries", []) if e.get("id") != snapshot_id]
    entries.append(
        {
            "id": snapshot_id,
            "name": name,
            "turn": turn,
            "saved_at": saved_at.isoformat(),
        }
    )
    payload["entries"] = entries
    payload["format"] = _FORMAT_VERSION
    index.write_text(json.dumps(payload, indent=2), encoding="utf-8")
