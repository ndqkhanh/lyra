"""HIR (Harness IR) event emitter.

Phase 1 responsibilities:
    - Stable JSONL emission to ``.lyra/<session>/events.jsonl``.
    - Monotonic ``ts`` per emitter instance.
    - Secrets masking at emit time via the shared regex pack.
    - Parent dir auto-creation.

Non-goals (future blocks):
    - OTLP exporter (block 13)
    - Artifact hashing sidecar (block 13)
    - Trace viewer UI (stretch)
"""
from __future__ import annotations

import enum
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any


class HIREventKind(str, enum.Enum):
    # agent lifecycle
    AGENT_LOOP_START = "AgentLoop.start"
    AGENT_LOOP_STEP = "AgentLoop.step"
    AGENT_LOOP_END = "AgentLoop.end"

    # tool lifecycle
    TOOL_CALL = "Tool.call"
    TOOL_RESULT = "Tool.result"

    # permission + hook
    PERMISSION_DECISION = "PermissionBridge.decision"
    HOOK_START = "Hook.start"
    HOOK_END = "Hook.end"

    # tdd
    TDD_STATE_CHANGE = "TDD.state_change"


# Redaction patterns — keep in sync with hooks/secrets_scan.py
_REDACT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:AKIA|ASIA|AIDA)[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bxox[bpaor]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |DSA |EC )?PRIVATE KEY-----"),
    re.compile(r"\bsk_(?:live|test)_[0-9A-Za-z]{16,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    re.compile(r"[Bb]earer\s+[A-Za-z0-9_\-\.=]{20,}"),
)


def _redact(value: str) -> str:
    out = value
    for pat in _REDACT_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def _redact_deep(obj: Any) -> Any:
    if isinstance(obj, str):
        return _redact(obj)
    if isinstance(obj, dict):
        return {k: _redact_deep(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_deep(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_redact_deep(v) for v in obj)
    return obj


@dataclass
class HIREvent:
    kind: HIREventKind | str | None
    session_id: str
    trace_id: str
    span_id: str
    actor: str = "generator"
    parent_span_id: str | None = None
    ts: float | None = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.kind, HIREventKind):
            # allow passing string values from HIREventKind; reject others
            raise ValueError(f"invalid HIREventKind: {self.kind!r}")
        for required, name in [
            (self.session_id, "session_id"),
            (self.trace_id, "trace_id"),
            (self.span_id, "span_id"),
            (self.actor, "actor"),
        ]:
            if not isinstance(required, str) or not required:
                raise ValueError(f"HIREvent.{name} must be a non-empty string")

    def to_json(self) -> dict[str, Any]:
        assert isinstance(self.kind, HIREventKind)
        payload: dict[str, Any] = {
            "kind": self.kind.value,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "actor": self.actor,
            "ts": self.ts,
            "attrs": _redact_deep(self.attrs),
        }
        if self.parent_span_id:
            payload["parent_span_id"] = self.parent_span_id
        return payload


class HIREmitter:
    """JSONL appender with monotonic timestamp and secrets masking."""

    def __init__(self, events_path: str | Path) -> None:
        self.events_path = Path(events_path)
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.events_path.open("a", encoding="utf-8")
        self._lock = Lock()
        self._last_ts: float = 0.0

    def emit(self, event: HIREvent) -> None:
        event.validate()
        with self._lock:
            now = time.time()
            # enforce monotonicity at ns-level to stabilise ordering under high
            # throughput; we never rewind.
            if now <= self._last_ts:
                now = self._last_ts + 1e-6
            self._last_ts = now
            if event.ts is None:
                event.ts = now
            line = json.dumps(event.to_json(), ensure_ascii=False)
            self._fh.write(line + "\n")
            self._fh.flush()

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass

    def __enter__(self) -> HIREmitter:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


# ===========================================================================
# Phase 9 flat HIR schema
# ===========================================================================

class HIRValidationError(Exception):
    pass


_VALID_KINDS = frozenset(
    {
        "session.start",
        "session.end",
        "tool.call",
        "tool.result",
        "permission.decision",
        "hook.decision",
        "tdd.transition",
        "safety.flag",
        "plan.generated",
        "plan.approved",
    }
)

_REQUIRED_TOP = ("schema_version", "session_id", "ts", "kind")


@dataclass
class HirEvent:
    schema_version: str
    session_id: str
    ts: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, obj: dict[str, Any]) -> HirEvent:
        for key in _REQUIRED_TOP:
            if key not in obj:
                raise HIRValidationError(f"HirEvent missing required field {key!r}")
        return cls(
            schema_version=str(obj["schema_version"]),
            session_id=str(obj["session_id"]),
            ts=str(obj["ts"]),
            kind=str(obj["kind"]),
            payload=dict(obj.get("payload", {}) or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "ts": self.ts,
            "kind": self.kind,
            "payload": self.payload,
        }


def validate_event(ev: HirEvent) -> None:
    if ev.kind not in _VALID_KINDS:
        raise HIRValidationError(f"unknown HIR kind: {ev.kind!r}")


def mask_secrets(obj: Any) -> Any:
    """Recursive secrets masker — public alias for _redact_deep with an
    explicit ``<redacted>`` tag so callers know the value was rewritten.
    """
    if isinstance(obj, str):
        masked = _redact(obj)
        if masked != obj:
            return "<redacted>"
        return obj
    if isinstance(obj, dict):
        return {k: mask_secrets(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask_secrets(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(mask_secrets(v) for v in obj)
    return obj
