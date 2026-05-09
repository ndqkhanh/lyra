"""L311-1 / L311-3 — Shell-script hook gates for team events.

Matches Claude Code's hook semantics ([`docs/05-hooks.md`](../../../../../../docs/05-hooks.md))
for the Agent Teams runtime: users register external scripts that run
*synchronously* on lifecycle events (`team.task_created`,
`team.task_completed`, `team.teammate_idle`). The script's **exit
code** decides whether the action is allowed:

* **0** — allow (default).
* **1** — non-blocking warning; logged but the action proceeds.
* **2** — **block**. The action is rejected; for `task_created` this
  means the task isn't added; for `task_completed` it forces a
  revision.

Hooks are configured in YAML. Each hook is a pair of
``(event_name, script_path_or_command)``, optionally with a timeout
and a stdin payload template.

Example ``~/.lyra/hooks.yaml``::

    hooks:
      - event: team.task_completed
        script: ~/.lyra/hooks/lint-completion.sh
        timeout_s: 30
        # stdin gets the JSON event payload; exit-code 2 blocks completion.
      - event: team.task_created
        script: |
          #!/bin/bash
          [ -n "$LYRA_TEAM" ] || exit 2
          exit 0
        timeout_s: 5

The :class:`TeamHookRegistry` is process-wide; the
:class:`LeadSession` consults it before emitting blockable events.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal


HookableEvent = Literal[
    "team.task_created",
    "team.task_completed",
    "team.teammate_idle",
]
"""Events that hooks can gate. Other team events (`team.create`,
`team.spawn`, `team.shutdown`) are observation-only and not blockable
because their gate semantics are unclear."""


HOOKABLE_EVENTS: frozenset[str] = frozenset(
    ("team.task_created", "team.task_completed", "team.teammate_idle")
)


# ---- decision types --------------------------------------------------


@dataclass(frozen=True)
class HookDecision:
    """Outcome of running one hook."""

    event: str
    script: str
    exit_code: int
    stdout: str
    stderr: str
    elapsed_s: float

    @property
    def blocked(self) -> bool:
        return self.exit_code == 2

    @property
    def warning(self) -> bool:
        return self.exit_code == 1

    @property
    def allowed(self) -> bool:
        return self.exit_code == 0


@dataclass(frozen=True)
class GateResult:
    """Aggregated outcome of every hook for one event."""

    event: str
    decisions: tuple[HookDecision, ...]

    @property
    def blocked(self) -> bool:
        return any(d.blocked for d in self.decisions)

    @property
    def warnings(self) -> tuple[HookDecision, ...]:
        return tuple(d for d in self.decisions if d.warning)

    @property
    def block_reason(self) -> str | None:
        for d in self.decisions:
            if d.blocked:
                msg = (d.stderr or d.stdout or "").strip().splitlines()
                return msg[-1] if msg else f"hook {d.script!r} blocked with exit 2"
        return None


# ---- hook spec -------------------------------------------------------


@dataclass(frozen=True)
class HookSpec:
    """One configured hook."""

    event: HookableEvent
    script: str
    timeout_s: float = 30.0

    def __post_init__(self) -> None:
        if self.event not in HOOKABLE_EVENTS:
            raise ValueError(
                f"event {self.event!r} is not blockable; one of {sorted(HOOKABLE_EVENTS)}"
            )
        if self.timeout_s <= 0:
            raise ValueError(f"timeout_s must be > 0, got {self.timeout_s}")


# ---- registry --------------------------------------------------------


class TeamHookRegistry:
    """Process-wide registry of team-event hooks."""

    def __init__(self) -> None:
        self._by_event: dict[str, list[HookSpec]] = {e: [] for e in HOOKABLE_EVENTS}

    def register(self, hook: HookSpec) -> None:
        self._by_event[hook.event].append(hook)

    def unregister_all(self) -> None:
        self._by_event = {e: [] for e in HOOKABLE_EVENTS}

    def hooks_for(self, event: str) -> tuple[HookSpec, ...]:
        return tuple(self._by_event.get(event, ()))

    def __len__(self) -> int:
        return sum(len(v) for v in self._by_event.values())

    # ---- gate dispatch ------------------------------------------

    def gate(
        self,
        event: HookableEvent,
        payload: dict[str, Any],
        *,
        env_extra: dict[str, str] | None = None,
    ) -> GateResult:
        """Run every registered hook for ``event``. Returns a
        :class:`GateResult` carrying every decision.

        The first hook to exit 2 blocks the gate; subsequent hooks
        still run so trace observability is preserved (matches Claude
        Code's behavior — every hook fires, the *aggregate* decides).
        """
        decisions: list[HookDecision] = []
        for spec in self.hooks_for(event):
            decisions.append(self._run_one(spec, payload, env_extra=env_extra or {}))
        return GateResult(event=event, decisions=tuple(decisions))

    def _run_one(
        self,
        spec: HookSpec,
        payload: dict[str, Any],
        *,
        env_extra: dict[str, str],
    ) -> HookDecision:
        import time

        start = time.time()
        env = dict(os.environ)
        env["LYRA_HOOK_EVENT"] = spec.event
        env["LYRA_HOOK_TEAM"] = str(payload.get("team", ""))
        env["LYRA_HOOK_TASK_ID"] = str(payload.get("task_id", ""))
        env["LYRA_HOOK_TEAMMATE"] = str(payload.get("teammate", ""))
        env.update(env_extra)
        stdin_payload = json.dumps(payload, default=str)

        # Dispatch: if `script` looks like a path, run it as a
        # subprocess; if it looks like inline shell, pipe through
        # `sh -c`. Heuristic: starts with `/`, `~`, `./`, or is a
        # single token that exists on PATH → treated as a path.
        cmd = self._resolve_command(spec.script)
        try:
            cp = subprocess.run(
                cmd,
                input=stdin_payload,
                capture_output=True,
                text=True,
                timeout=spec.timeout_s,
                env=env,
                check=False,
            )
            exit_code = cp.returncode
            stdout = cp.stdout
            stderr = cp.stderr
        except subprocess.TimeoutExpired as e:
            exit_code = 2  # treat timeout as block
            stdout = ""
            stderr = f"hook timed out after {spec.timeout_s}s: {e}"
        except FileNotFoundError as e:
            exit_code = 1  # warning — script missing
            stdout = ""
            stderr = f"hook script not found: {e}"
        except Exception as e:  # noqa: BLE001
            exit_code = 1  # warning — caller decides whether to escalate
            stdout = ""
            stderr = f"hook crashed: {type(e).__name__}: {e}"
        elapsed = time.time() - start
        return HookDecision(
            event=spec.event,
            script=spec.script,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            elapsed_s=elapsed,
        )

    @staticmethod
    def _resolve_command(script: str) -> list[str]:
        """Return the argv to subprocess.

        - Absolute / home / relative paths → treat as executable path.
        - Anything else → run via ``sh -c`` so inline shell works.
        """
        s = script.strip()
        # Path-shaped → run as an executable on disk.
        looks_like_path = (
            s.startswith("/")
            or s.startswith("~")
            or s.startswith("./")
            or s.startswith("../")
        )
        if looks_like_path:
            return [os.path.expanduser(s)]
        # Anything else → route through `sh -c` so shell builtins
        # (`exit`, `true`, `false`), pipes, redirections, and inline
        # multi-line scripts all work uniformly. We deliberately do
        # NOT shlex-split bare argv into a direct exec because shell
        # builtins won't resolve that way.
        return ["sh", "-c", s]


# ---- YAML loader -----------------------------------------------------


def load_hooks_yaml(path: Path | str, *, registry: TeamHookRegistry | None = None) -> TeamHookRegistry:
    """Load a hooks YAML file and register every hook into ``registry``.

    Stdlib-only minimal parser (we already have one in
    :mod:`lyra_core.bundle.source_bundle`); accepts both the current
    Lyra hooks shape::

        hooks:
          - event: team.task_completed
            script: /path/to/script.sh
            timeout_s: 30

    and tolerates extra keys that future hooks might use.
    """
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"hooks file not found: {path}")
    text = path.read_text(encoding="utf-8")

    # Parse via the existing minimal YAML parser.
    from ..bundle.source_bundle import _parse_minimal_yaml  # type: ignore

    parsed = _parse_minimal_yaml(text)
    raw_hooks = parsed.get("hooks") or []
    if not isinstance(raw_hooks, list):
        raise ValueError("hooks: top-level 'hooks' key must be a list")

    reg = registry if registry is not None else TeamHookRegistry()
    for entry in raw_hooks:
        if not isinstance(entry, dict):
            continue
        event = str(entry.get("event") or "").strip()
        script = str(entry.get("script") or "").strip()
        timeout = entry.get("timeout_s") or entry.get("timeout") or 30
        if not event or not script:
            continue
        reg.register(HookSpec(event=event, script=script, timeout_s=float(timeout)))  # type: ignore[arg-type]
    return reg


# ---- process-wide singleton -----------------------------------------


_GLOBAL_REGISTRY: TeamHookRegistry | None = None


def global_registry() -> TeamHookRegistry:
    """Return the process-wide :class:`TeamHookRegistry` singleton.

    The :class:`LeadSession` consults this on every blockable event.
    Tests reset between cases via :func:`reset_global_registry`.
    """
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = TeamHookRegistry()
    return _GLOBAL_REGISTRY


def reset_global_registry() -> None:
    global _GLOBAL_REGISTRY
    _GLOBAL_REGISTRY = None


__all__ = [
    "GateResult",
    "HOOKABLE_EVENTS",
    "HookDecision",
    "HookSpec",
    "HookableEvent",
    "TeamHookRegistry",
    "global_registry",
    "load_hooks_yaml",
    "reset_global_registry",
]
