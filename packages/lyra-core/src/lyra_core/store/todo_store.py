"""Persistent JSON-backed store for the ``TodoWrite`` tool.

Design contract:

- Atomic writes — the file never appears in a half-written state. We
  write to ``<path>.tmp`` and then ``Path.replace`` onto the live
  path. If the rename raises (e.g. disk full, process killed) the
  live file is unchanged and the tmp file is cleaned up.
- Small and self-healing — the store lazily creates its parent
  directory and treats a missing or malformed file as empty.
- Schema-less — the store stores a JSON list of opaque todo dicts;
  validation is the tool's concern.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


_STATUS_VALUES: frozenset[str] = frozenset(
    {"pending", "in_progress", "completed", "cancelled"}
)


class TodoStore:
    """Atomic JSON store for the ``TodoWrite`` tool.

    Args:
        path: File path where todos live. Parent directories are
            created lazily on first write.
    """

    def __init__(self, *, path: Path) -> None:
        self._path = Path(path)

    # ---- read side ------------------------------------------------- #

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> list[dict]:
        """Return the persisted list; ``[]`` when the file is missing
        or malformed (self-healing).
        """
        if not self._path.exists():
            return []
        try:
            payload = json.loads(self._path.read_text())
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        return [dict(item) for item in payload if isinstance(item, dict)]

    # ---- write side ----------------------------------------------- #

    def save(self, todos: list[dict]) -> None:
        """Atomic write of ``todos`` to the live path.

        Uses a same-directory ``<name>.tmp.<pid>`` file and
        :meth:`Path.replace` for crash-safe semantics on both POSIX and
        Windows. On any exception the tmp file is cleaned up and the
        live file is left untouched.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(list(todos), indent=2, sort_keys=False)

        tmp_path = self._path.with_name(f"{self._path.name}.tmp.{os.getpid()}")
        try:
            tmp_path.write_text(payload)
            tmp_path.replace(self._path)
        except Exception:
            # Clean up the tmp file so callers don't leak stale
            # ``<path>.tmp.<pid>`` artefacts after a crash.
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
            raise


__all__ = ["TodoStore"]
