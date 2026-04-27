"""HIR (Harness Intermediate Representation) event log.

HIR is the single, framework-agnostic event schema Lyra emits so
every downstream consumer (replay, eval, OTLP export, retro) can read
the same log without re-deriving state. The kernel implementation
(v1 Phase 9, block 13) will produce a validated schema with OpenTelemetry
spans; this module ships the *scaffold* so the CLI can already log
turns, slash dispatches, and bash invocations to
``.lyra/sessions/events.jsonl``.

Design:

- One JSONL line per event. Trivially tailable (``!tail -f``),
  appendable, diffable.
- One common envelope:

      {"ts": ISO-8601, "kind": "...", "session_turn": int, "data": {...}}

  The ``kind`` tag is the only field the kernel schema bolts extra
  invariants onto; everything else is free-form until v1 Phase 9.
- Open a single ``HIRLogger`` per session, reuse the handle across
  events, close it on REPL exit so ``tail -f`` sees the final line.
- No dependency on Rich / prompt_toolkit; this module is safe to import
  from tests and the non-TTY path.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


class HIRLogger:
    """Append-only JSONL writer keyed on one session.

    ``HIRLogger`` deliberately swallows ``OSError`` on write: the REPL
    must never crash because logging failed. Failures surface through
    ``self.last_error`` so ``/doctor`` can report them, and the logger
    flips to ``self.enabled = False`` until reopened.
    """

    def __init__(self, path: Path, *, enabled: bool = True) -> None:
        self.path = path
        self.enabled = enabled
        self.last_error: str | None = None
        self._handle: TextIO | None = None
        if enabled:
            self._open()

    # ---- lifecycle --------------------------------------------------------

    def _open(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = self.path.open("a", encoding="utf-8")
        except OSError as exc:
            self.enabled = False
            self.last_error = str(exc)
            self._handle = None

    def close(self) -> None:
        h, self._handle = self._handle, None
        if h is not None:
            try:
                h.close()
            except OSError:
                # Ignore — we're closing.
                pass

    def __enter__(self) -> "HIRLogger":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ---- writes -----------------------------------------------------------

    def log(
        self,
        kind: str,
        data: dict[str, Any] | None = None,
        *,
        session_turn: int | None = None,
    ) -> None:
        """Append a single event line. Silently no-ops when disabled."""
        if not self.enabled or self._handle is None:
            return
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "session_turn": session_turn,
            "data": data or {},
        }
        try:
            self._handle.write(json.dumps(record, default=str) + "\n")
            self._handle.flush()
        except OSError as exc:
            self.enabled = False
            self.last_error = str(exc)
            self.close()

    # ---- convenience wrappers -------------------------------------------

    def on_prompt(self, *, turn: int, mode: str, line: str) -> None:
        self.log(
            "user.prompt",
            {"mode": mode, "line": line},
            session_turn=turn,
        )

    def on_slash(
        self,
        *,
        turn: int,
        name: str,
        args: str,
        exit_code: int = 0,
    ) -> None:
        self.log(
            "slash.dispatch",
            {"name": name, "args": args, "exit_code": exit_code},
            session_turn=turn,
        )

    def on_bash(
        self,
        *,
        turn: int,
        command: str,
        exit_code: int,
        stdout_bytes: int,
        stderr_bytes: int,
    ) -> None:
        self.log(
            "bash.run",
            {
                "command": command,
                "exit_code": exit_code,
                "stdout_bytes": stdout_bytes,
                "stderr_bytes": stderr_bytes,
            },
            session_turn=turn,
        )

    def on_mode_change(
        self, *, turn: int, from_mode: str, to_mode: str
    ) -> None:
        self.log(
            "mode.change",
            {"from": from_mode, "to": to_mode},
            session_turn=turn,
        )

    def on_session_start(
        self, *, repo_root: Path, model: str, mode: str
    ) -> None:
        self.log(
            "session.start",
            {"repo_root": str(repo_root), "model": model, "mode": mode},
            session_turn=0,
        )

    def on_session_end(
        self,
        *,
        turns: int,
        cost_usd: float,
        tokens: int,
    ) -> None:
        self.log(
            "session.end",
            {"turns": turns, "cost_usd": cost_usd, "tokens": tokens},
            session_turn=turns,
        )


def default_event_path(repo_root: Path) -> Path:
    return repo_root / ".lyra" / "sessions" / "events.jsonl"
