"""Red tests for the HIR (Harness Intermediate Representation) event schema.

Every HIR event must round-trip through JSON and validate against its kind.
"""
from __future__ import annotations

import json

import pytest

from lyra_core.observability.hir import (
    HirEvent,
    HIRValidationError,
    validate_event,
)


def _base(kind: str, **extra):
    base = {
        "schema_version": "1.0",
        "session_id": "01HSID00000000000000000000",
        "ts": "2025-01-01T00:00:00Z",
        "kind": kind,
    }
    base.update(extra)
    return base


def test_known_kinds_validate() -> None:
    for k in (
        "session.start",
        "tool.call",
        "tool.result",
        "permission.decision",
        "hook.decision",
        "tdd.transition",
        "safety.flag",
        "session.end",
    ):
        ev = HirEvent.from_dict(_base(k, payload={}))
        validate_event(ev)


def test_unknown_kind_rejected() -> None:
    with pytest.raises(HIRValidationError):
        validate_event(HirEvent.from_dict(_base("bogus.kind", payload={})))


def test_round_trip_json() -> None:
    ev = HirEvent.from_dict(_base("tool.call", payload={"name": "Read", "args": {"path": "x"}}))
    raw = json.dumps(ev.to_dict())
    back = HirEvent.from_dict(json.loads(raw))
    assert back.kind == ev.kind
    assert back.payload == ev.payload


def test_missing_required_field_rejected() -> None:
    with pytest.raises(HIRValidationError):
        HirEvent.from_dict({"kind": "tool.call"})  # missing schema_version etc.


def test_secrets_masked_at_emit() -> None:
    from lyra_core.observability.hir import mask_secrets

    data = {"auth": "AKIAABCDEFGHIJKLMNOP", "other": "ok"}
    masked = mask_secrets(data)
    assert masked["auth"] != "AKIAABCDEFGHIJKLMNOP"
    assert "redacted" in masked["auth"].lower()
    assert masked["other"] == "ok"
