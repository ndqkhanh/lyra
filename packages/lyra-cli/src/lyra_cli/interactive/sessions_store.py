"""On-disk session management for the REPL.

Owns the ``~/.lyra/sessions/<id>/`` layout — every session lives in
its own directory with a ``turns.jsonl`` (one JSON event per dispatch,
written by :class:`InteractiveSession`) and an optional ``meta.json``
(display name, created-at, derived-from). The directory *slug* is the
session id and is immutable; the display name lives in ``meta.json``
so renames don't break stable references.

Why a separate module from :mod:`.session`?

The REPL session is a runtime object; the store is a tiny CRUD layer.
Splitting them keeps :class:`InteractiveSession` free of disk-walking
code and lets us test fork/rename/list/export without spinning up a
session at all.
"""

from __future__ import annotations

import datetime as _dt
import json as _json
import os as _os
import re as _re
import shutil as _shutil
import tempfile as _tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal


ExportFormat = Literal["md", "json", "jsonl"]


class UnsupportedExportFormat(ValueError):
    """Raised when ``export_to`` is asked for a format it doesn't ship."""


class InvalidSessionId(ValueError):
    """Raised when a session id would escape the sessions root.

    Session ids end up as directory names; we reject anything that
    contains path separators, ``..``, NULs, or non-printable bytes so a
    rogue ``/fork ../../../../etc/passwd`` can never reach disk.
    """


# Conservative slug: letters/digits + ``-_.``. Rejecting ``..`` and any
# slash variant (``/``, ``\``, ``:``) is the load-bearing part — the
# allow-list just prevents future bugs from a forgiving regex.
_SAFE_ID_RE = _re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_session_id(session_id: str) -> str:
    """Reject ids that could escape the sessions root.

    Why so strict? Session ids show up as directory names under
    ``~/.lyra/sessions/``. Allowing ``..`` or ``/`` would let
    ``/fork ../foo`` write outside the user's session tree (and could
    overwrite arbitrary files on a shared host). The whole REPL is the
    privilege boundary — this is the choke point.
    """
    if not isinstance(session_id, str) or not session_id:
        raise InvalidSessionId("session id must be a non-empty string")
    if session_id in (".", ".."):
        raise InvalidSessionId(f"reserved id {session_id!r}")
    if not _SAFE_ID_RE.match(session_id):
        raise InvalidSessionId(
            f"session id {session_id!r} must match [A-Za-z0-9._-]+ "
            "(no separators, no ``..``)"
        )
    return session_id


def _atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Write *content* to *path* via tempfile + ``os.replace``.

    ``os.replace`` is atomic on POSIX and Windows (within the same
    filesystem), so a crash mid-write leaves the previous file intact
    instead of a half-truncated one. Falls back to a direct write only
    when the parent directory cannot host a tempfile (extremely rare —
    e.g. a read-only mount).
    """
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    try:
        fd, tmp = _tempfile.mkstemp(prefix=path.name + ".", dir=str(parent))
    except OSError:
        path.write_text(content, encoding=encoding)
        return
    try:
        with _os.fdopen(fd, "w", encoding=encoding) as fh:
            fh.write(content)
        _os.replace(tmp, path)
    except Exception:
        try:
            _os.unlink(tmp)
        except OSError:
            pass
        raise


@dataclass(frozen=True)
class SessionMeta:
    """A summary row shown by ``/sessions`` (and consumable by tests)."""

    session_id: str
    name: str | None
    turn_count: int
    created_at: str | None  # ISO 8601, ``None`` when unknown


class SessionsStore:
    """CRUD facade for ``<sessions_root>/<session_id>/`` directories.

    All methods are best-effort: missing files / malformed JSON are
    treated as "not present" rather than fatal so a corrupt session
    can never block the user from listing or forking the rest.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    # ---- public ---------------------------------------------------

    def list(self) -> list[SessionMeta]:
        """Return one :class:`SessionMeta` per discoverable session.

        Sessions without a ``turns.jsonl`` are skipped (an empty
        directory shouldn't pollute ``/sessions``). Order is
        ``session_id`` ascending so the listing is stable for tests
        and the time-ordered ids sort chronologically.
        """
        if not self.root.is_dir():
            return []
        out: list[SessionMeta] = []
        for entry in sorted(self.root.iterdir(), key=lambda p: p.name):
            if not entry.is_dir():
                continue
            turns = entry / "turns.jsonl"
            if not turns.is_file():
                continue
            out.append(
                SessionMeta(
                    session_id=entry.name,
                    name=self._read_name(entry),
                    turn_count=self._count_turns(turns),
                    created_at=self._read_created_at(entry),
                )
            )
        return out

    def fork(self, source_id: str, *, new_id: str) -> str:
        """Copy *source_id*'s ``turns.jsonl`` under *new_id* and return *new_id*.

        Raises :class:`FileNotFoundError` when the source directory or
        its log is missing — surfacing the error keeps "fork into
        thin air" out of the slash command and forces the caller to
        either pick a different source or seed one first. Both ids are
        validated against :func:`_validate_session_id` so a path like
        ``../../etc`` can't reach disk.
        """
        _validate_session_id(source_id)
        _validate_session_id(new_id)
        src_dir = self.root / source_id
        src_log = src_dir / "turns.jsonl"
        if not src_log.is_file():
            raise FileNotFoundError(
                f"cannot fork: source session {source_id!r} has no turns.jsonl"
            )
        dst_dir = self.root / new_id
        dst_dir.mkdir(parents=True, exist_ok=True)
        _shutil.copy2(src_log, dst_dir / "turns.jsonl")
        # Carry meta forward so the user keeps display name + provenance.
        src_meta = src_dir / "meta.json"
        meta: dict[str, object] = {}
        if src_meta.is_file():
            try:
                meta = _json.loads(src_meta.read_text(encoding="utf-8"))
            except _json.JSONDecodeError:
                meta = {}
        meta["forked_from"] = source_id
        meta["created_at"] = _dt.datetime.now().isoformat(timespec="seconds")
        _atomic_write_text(dst_dir / "meta.json", _json.dumps(meta, indent=2))
        return new_id

    def rename(self, session_id: str, *, new_name: str) -> None:
        """Update the display *name* in ``meta.json`` (slug stays put)."""
        _validate_session_id(session_id)
        sd = self.root / session_id
        if not sd.is_dir():
            raise FileNotFoundError(f"no such session: {session_id!r}")
        meta_path = sd / "meta.json"
        meta: dict[str, object] = {}
        if meta_path.is_file():
            try:
                meta = _json.loads(meta_path.read_text(encoding="utf-8"))
            except _json.JSONDecodeError:
                meta = {}
        meta["name"] = new_name
        _atomic_write_text(meta_path, _json.dumps(meta, indent=2))

    def export_to(
        self,
        session_id: str,
        *,
        path: Path,
        fmt: ExportFormat,
    ) -> Path:
        """Write the transcript to *path* in *fmt* and return *path*.

        Supported formats:
          * ``md``    — human-readable markdown with a ``# Session …``
                         heading and one fenced block per turn.
          * ``json``  — single JSON array of turn dicts.
          * ``jsonl`` — verbatim copy of the live ``turns.jsonl``.
        """
        _validate_session_id(session_id)
        rows = list(self._read_rows(session_id))
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "md":
            _atomic_write_text(path, self._render_markdown(session_id, rows))
        elif fmt == "json":
            _atomic_write_text(path, _json.dumps(rows, indent=2))
        elif fmt == "jsonl":
            src = self.root / session_id / "turns.jsonl"
            if src.is_file():
                _shutil.copy2(src, path)
            else:
                _atomic_write_text(path, "")
        else:
            raise UnsupportedExportFormat(
                f"unknown export format {fmt!r}; expected one of: md, json, jsonl"
            )
        return path

    # ---- internals ------------------------------------------------

    def _read_rows(self, session_id: str) -> Iterable[dict]:
        _validate_session_id(session_id)
        log = self.root / session_id / "turns.jsonl"
        if not log.is_file():
            return []
        out: list[dict] = []
        for raw in log.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                out.append(_json.loads(raw))
            except _json.JSONDecodeError:
                continue
        return out

    @staticmethod
    def _count_turns(log_path: Path) -> int:
        try:
            return sum(1 for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip())
        except OSError:
            return 0

    @staticmethod
    def _read_name(entry: Path) -> str | None:
        meta = entry / "meta.json"
        if not meta.is_file():
            return None
        try:
            return _json.loads(meta.read_text(encoding="utf-8")).get("name")
        except (_json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _read_created_at(entry: Path) -> str | None:
        meta = entry / "meta.json"
        if not meta.is_file():
            return None
        try:
            return _json.loads(meta.read_text(encoding="utf-8")).get("created_at")
        except (_json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _render_markdown(session_id: str, rows: list[dict]) -> str:
        lines = [f"# Session {session_id}", ""]
        for i, row in enumerate(rows, start=1):
            mode = row.get("mode", "?")
            line = row.get("line", "")
            lines.append(f"## Turn {i} (mode: {mode})")
            lines.append("")
            lines.append("```")
            lines.append(line)
            lines.append("```")
            lines.append("")
        return "\n".join(lines)


__all__ = [
    "ExportFormat",
    "InvalidSessionId",
    "SessionMeta",
    "SessionsStore",
    "UnsupportedExportFormat",
]
