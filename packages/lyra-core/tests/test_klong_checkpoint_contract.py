"""Wave-F Task 14 — KLong checkpoint & resume contract."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_core.klong import (
    KLongCheckpoint,
    KLongError,
    KLongStore,
    resume,
    snapshot,
)
from lyra_core.klong.checkpoint import CURRENT_SCHEMA_VERSION


# ---- envelope round-trip -------------------------------------------


def test_snapshot_then_resume_returns_same_payload(tmp_path: Path) -> None:
    store = KLongStore(root=tmp_path)
    payload = {"turns": ["hello", "world"], "tdd_phase": "green"}
    snapshot(
        store=store,
        session_id="sess-1",
        payload=payload,
        model_generation="gpt-5",
    )
    restored = resume(store=store, session_id="sess-1")
    assert restored is not None
    assert restored.payload == payload
    assert restored.model_generation == "gpt-5"
    assert restored.schema_version == CURRENT_SCHEMA_VERSION


def test_resume_returns_latest_of_multiple(tmp_path: Path) -> None:
    store = KLongStore(root=tmp_path)
    snapshot(
        store=store,
        session_id="sess",
        payload={"t": 1},
        model_generation="gpt-5",
    )
    snapshot(
        store=store,
        session_id="sess",
        payload={"t": 2},
        model_generation="gpt-5",
    )
    snapshot(
        store=store,
        session_id="sess",
        payload={"t": 3},
        model_generation="gpt-6",
    )
    latest = resume(store=store, session_id="sess")
    assert latest is not None
    assert latest.payload == {"t": 3}
    assert latest.model_generation == "gpt-6"


def test_resume_missing_session_returns_none(tmp_path: Path) -> None:
    store = KLongStore(root=tmp_path)
    assert resume(store=store, session_id="ghost") is None


def test_list_returns_empty_for_unknown(tmp_path: Path) -> None:
    store = KLongStore(root=tmp_path)
    assert store.list("ghost") == []


# ---- malformed envelopes ------------------------------------------


def test_malformed_json_rejected(tmp_path: Path) -> None:
    with pytest.raises(KLongError):
        KLongCheckpoint.from_json("not json")


def test_missing_field_rejected() -> None:
    with pytest.raises(KLongError):
        KLongCheckpoint.from_json(
            json.dumps(
                {
                    "schema_version": 1,
                    "model_generation": "gpt-5",
                    "created_at": "2026-01-01T00:00:00Z",
                    "session_id": "x",
                }
            )
        )


def test_non_object_payload_rejected() -> None:
    with pytest.raises(KLongError):
        KLongCheckpoint.from_json(
            json.dumps(
                {
                    "schema_version": 1,
                    "model_generation": "gpt-5",
                    "created_at": "2026-01-01T00:00:00Z",
                    "session_id": "x",
                    "payload": ["not", "an", "object"],
                }
            )
        )


# ---- forward + backward compatibility ------------------------------


def test_newer_version_rejected_with_helpful_message(tmp_path: Path) -> None:
    store = KLongStore(root=tmp_path)
    (tmp_path / "sess").mkdir()
    (tmp_path / "sess" / "future.klong.json").write_text(
        json.dumps(
            {
                "schema_version": CURRENT_SCHEMA_VERSION + 1,
                "model_generation": "gpt-99",
                "created_at": "2030-01-01T00:00:00Z",
                "session_id": "sess",
                "payload": {"fancy_new_field": True},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(KLongError) as excinfo:
        store.latest("sess")
    assert "newer" in str(excinfo.value).lower()


def test_older_version_migrates_transparently(tmp_path: Path) -> None:
    def v0_to_v1(payload, old_version):
        # Migration: rename "turns_old" → "turns"
        new = dict(payload)
        if "turns_old" in new:
            new["turns"] = new.pop("turns_old")
        return new

    store = KLongStore(root=tmp_path, migrators={0: v0_to_v1})
    (tmp_path / "sess").mkdir()
    (tmp_path / "sess" / "old.klong.json").write_text(
        json.dumps(
            {
                "schema_version": 0,
                "model_generation": "gpt-4",
                "created_at": "2025-01-01T00:00:00Z",
                "session_id": "sess",
                "payload": {"turns_old": ["a", "b"]},
            }
        ),
        encoding="utf-8",
    )
    checkpoint = store.latest("sess")
    assert checkpoint is not None
    assert checkpoint.schema_version == CURRENT_SCHEMA_VERSION
    assert checkpoint.payload == {"turns": ["a", "b"]}


def test_missing_migrator_raises(tmp_path: Path) -> None:
    store = KLongStore(root=tmp_path)  # no migrators registered
    (tmp_path / "sess").mkdir()
    (tmp_path / "sess" / "old.klong.json").write_text(
        json.dumps(
            {
                "schema_version": 0,
                "model_generation": "gpt-3",
                "created_at": "2024-01-01T00:00:00Z",
                "session_id": "sess",
                "payload": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(KLongError) as excinfo:
        store.latest("sess")
    assert "migrator" in str(excinfo.value).lower()


def test_checkpoint_to_json_roundtrips() -> None:
    cp = KLongCheckpoint(
        schema_version=1,
        model_generation="gpt-5",
        created_at="2026-01-01T00:00:00Z",
        session_id="sess",
        payload={"a": 1},
    )
    restored = KLongCheckpoint.from_json(cp.to_json())
    assert restored.payload == cp.payload
