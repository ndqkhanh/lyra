"""KLong checkpoint + resume.

Envelope shape (JSON):

    {
      "schema_version": int,
      "model_generation": str,    # e.g. "gpt-5", "gpt-6"
      "created_at": str,           # ISO-8601 UTC
      "session_id": str,
      "payload": { ... }           # opaque to the store; caller-owned
    }

The store keeps checkpoints on disk under ``<root>/<session_id>/``
with timestamped filenames. ``KLongStore.latest(session_id)``
returns the newest checkpoint (by ``created_at``). ``snapshot``
and ``resume`` are thin wrappers so simple callers don't
instantiate the store.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping


__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "KLongCheckpoint",
    "KLongError",
    "KLongStore",
    "Migrator",
    "resume",
    "snapshot",
]


CURRENT_SCHEMA_VERSION = 1


class KLongError(RuntimeError):
    pass


Migrator = Callable[[Mapping[str, object], int], Mapping[str, object]]


@dataclass(frozen=True)
class KLongCheckpoint:
    schema_version: int
    model_generation: str
    created_at: str
    session_id: str
    payload: Mapping[str, object]

    def to_json(self) -> str:
        return json.dumps(
            {
                "schema_version": self.schema_version,
                "model_generation": self.model_generation,
                "created_at": self.created_at,
                "session_id": self.session_id,
                "payload": self.payload,
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, raw: str) -> "KLongCheckpoint":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise KLongError(f"checkpoint JSON invalid: {exc}") from exc
        if not isinstance(data, Mapping):
            raise KLongError("checkpoint root must be an object")
        for field_name in (
            "schema_version",
            "model_generation",
            "created_at",
            "session_id",
            "payload",
        ):
            if field_name not in data:
                raise KLongError(f"checkpoint missing required field {field_name!r}")
        if not isinstance(data["payload"], Mapping):
            raise KLongError("checkpoint payload must be an object")
        return cls(
            schema_version=int(data["schema_version"]),
            model_generation=str(data["model_generation"]),
            created_at=str(data["created_at"]),
            session_id=str(data["session_id"]),
            payload=dict(data["payload"]),
        )


# ---- store --------------------------------------------------------


@dataclass
class KLongStore:
    root: Path
    migrators: dict[int, Migrator] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.root = Path(self.root)

    def _dir_for(self, session_id: str) -> Path:
        return self.root / session_id

    def save(
        self,
        *,
        session_id: str,
        payload: Mapping[str, object],
        model_generation: str,
    ) -> KLongCheckpoint:
        now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        created_at = datetime.now(timezone.utc).isoformat()
        target_dir = self._dir_for(session_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        checkpoint = KLongCheckpoint(
            schema_version=CURRENT_SCHEMA_VERSION,
            model_generation=model_generation,
            created_at=created_at,
            session_id=session_id,
            payload=dict(payload),
        )
        path = target_dir / f"{now}.klong.json"
        path.write_text(checkpoint.to_json(), encoding="utf-8")
        return checkpoint

    def list(self, session_id: str) -> list[Path]:
        d = self._dir_for(session_id)
        if not d.exists():
            return []
        return sorted(d.glob("*.klong.json"))

    def latest(self, session_id: str) -> KLongCheckpoint | None:
        paths = self.list(session_id)
        if not paths:
            return None
        return self._load_with_migrate(paths[-1])

    def load(self, path: Path) -> KLongCheckpoint:
        return self._load_with_migrate(path)

    def _load_with_migrate(self, path: Path) -> KLongCheckpoint:
        raw = Path(path).read_text(encoding="utf-8")
        cp = KLongCheckpoint.from_json(raw)
        if cp.schema_version > CURRENT_SCHEMA_VERSION:
            raise KLongError(
                f"checkpoint schema_version={cp.schema_version} is newer than "
                f"this binary understands (max={CURRENT_SCHEMA_VERSION}); "
                "upgrade Lyra before resuming."
            )
        current = cp
        while current.schema_version < CURRENT_SCHEMA_VERSION:
            migrator = self.migrators.get(current.schema_version)
            if migrator is None:
                raise KLongError(
                    f"no migrator registered for schema_version "
                    f"{current.schema_version} → {current.schema_version + 1}"
                )
            new_payload = migrator(current.payload, current.schema_version)
            current = KLongCheckpoint(
                schema_version=current.schema_version + 1,
                model_generation=current.model_generation,
                created_at=current.created_at,
                session_id=current.session_id,
                payload=new_payload,
            )
        return current


# ---- convenience wrappers -----------------------------------------


def snapshot(
    *,
    store: KLongStore,
    session_id: str,
    payload: Mapping[str, object],
    model_generation: str,
) -> KLongCheckpoint:
    return store.save(
        session_id=session_id,
        payload=payload,
        model_generation=model_generation,
    )


def resume(
    *,
    store: KLongStore,
    session_id: str,
) -> KLongCheckpoint | None:
    return store.latest(session_id)
