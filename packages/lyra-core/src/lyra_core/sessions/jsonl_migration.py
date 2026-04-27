"""One-shot migration of legacy JSONL session logs into SQLite+FTS5.

Historic ``.opencoding/sessions/*.jsonl`` files (one session per file,
one message per line) are folded into the new
``.lyra/state.db`` store. The migration is idempotent: a
``jsonl_migrated`` marker stores the list of files already ingested so
re-running the CLI does not duplicate content.

This module is intentionally legacy-aware: it references the old
``.opencoding/sessions/`` path by name so existing user data can be
ingested. Do not strip the token — it would break migration.

lyra-legacy-aware
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .store import SessionStore


_MARKER_NAME = "JSONL_MIGRATED"


def _read_jsonl(path: Path) -> Iterable[dict]:
    try:
        with path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except OSError:
        return


def migrate_jsonl_sessions(
    *,
    source_dir: Path,
    store: SessionStore,
    marker_path: Path | None = None,
) -> int:
    """Fold every ``*.jsonl`` file under ``source_dir`` into ``store``.

    Returns the number of messages appended. Writes a marker under
    ``marker_path`` (defaults to ``<source_dir>.parent/JSONL_MIGRATED``)
    so subsequent runs short-circuit.
    """
    if not source_dir.is_dir():
        return 0

    marker = marker_path or (source_dir.parent / _MARKER_NAME)
    already: set[str] = set()
    if marker.exists():
        try:
            already = {
                line.strip()
                for line in marker.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
        except OSError:
            already = set()

    appended = 0
    migrated_files: list[str] = list(already)
    for jsonl in sorted(source_dir.glob("*.jsonl")):
        key = str(jsonl.relative_to(source_dir))
        if key in already:
            continue
        session_id = jsonl.stem or "legacy"
        store.start_session(session_id, model="legacy-jsonl", mode="import")
        for row in _read_jsonl(jsonl):
            role = str(row.get("role") or "user")
            content = str(row.get("content") or "")
            if not content:
                continue
            tool_calls = row.get("tool_calls") or None
            store.append_message(
                session_id,
                role=role,
                content=content,
                tool_calls=tool_calls if isinstance(tool_calls, list) else None,
            )
            appended += 1
        migrated_files.append(key)

    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("\n".join(sorted(set(migrated_files))), encoding="utf-8")
    except OSError:
        pass
    return appended


__all__ = ["migrate_jsonl_sessions"]
