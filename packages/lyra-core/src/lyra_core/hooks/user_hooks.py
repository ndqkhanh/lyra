"""User-defined shell hooks (Claude-Code-style).

Complements :class:`lyra_core.hooks.lifecycle.LifecycleBus` (in-process
pub/sub for plugin code) by adding a **subprocess** dispatch path
configured from ``settings.json``:

.. code-block:: json

    {
      "enable_hooks": true,
      "hooks": {
        "PreToolUse": [
          { "matcher": "Bash(rm *)", "command": "~/.lyra/hooks/block-rm.sh" }
        ],
        "PostToolUse": [
          { "matcher": "Edit(./src/**)", "command": "ruff format $LYRA_HOOK_PATH" }
        ]
      }
    }

Why a separate dispatch surface from ``LifecycleBus``:

* Plugin code subscribes to LifecycleBus *in the same process* — best
  for telemetry, structured state, zero-overhead reactive logic.
* User hooks are **shell commands** the operator drops into a config
  file; they need an isolated subprocess + JSON I/O contract so a
  broken hook can't bring down the REPL and a malicious one can't
  read the agent's memory.

**Security:** disabled by default. The session must explicitly set
``enable_hooks: true`` in settings before any subprocess is spawned;
configs without that flag silently no-op. This stops a typoed git
clone of a hostile repo from running arbitrary shell commands the
moment Lyra opens it.

The handler protocol:

* **stdin** (utf-8 JSON): ``{"event", "tool", "args", "session_id"}``.
* **stdout** (utf-8 JSON): ``{"continue": bool, "reason": str?,
  "args": dict?}``. ``continue=false`` blocks the tool call;
  ``continue=true`` with ``args`` mutates the invocation; bare
  ``continue=true`` allows. Non-JSON output ⇒ allow with a warning
  logged (broken hook ≠ blocking outcome).

A 5-second timeout caps wall time per hook so a stuck handler can't
freeze the REPL. Timeouts fail open (allow) and log; timing-out is a
hook bug, not a deny signal.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

from lyra_core.permissions.grammar import (
    Rule,
    _matches_specifier,
    parse_rule,
)


def compile_matcher(rule_text: str):
    """Wrap a permission-grammar rule literal as a (tool, args) -> bool predicate.

    Reuses the permissions grammar so users only learn one rule
    dialect — ``Bash(git push *)`` matches the same way whether it's
    in ``permissions.allow`` or ``hooks.PreToolUse[].matcher``.
    """
    rule: Rule = parse_rule(rule_text)

    def _match(tool_name: str, args) -> bool:
        if rule.tool != tool_name:
            return False
        return _matches_specifier(rule, tool_name, args or {})

    return _match


_LOG = logging.getLogger(__name__)
_DEFAULT_TIMEOUT_SEC: float = 5.0


# Events the runner accepts. Mirrors the CC subset Lyra cares about
# today; can grow without breaking the handler protocol since the
# event name is just a string.
SUPPORTED_EVENTS: frozenset[str] = frozenset(
    {
        "SessionStart",
        "SessionEnd",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "PostToolUseFailure",
        "PermissionRequest",
        "SubagentStart",
        "SubagentStop",
        "Stop",
        "PreCompact",
        "PostCompact",
        "Notification",
    }
)


@dataclass(frozen=True)
class HookSpec:
    """One configured user hook."""

    event: str
    matcher: str  # rule literal e.g. ``Bash(rm *)``; "*" matches any
    command: str  # shell command line


@dataclass
class HookOutcome:
    """The runner's verdict for one event-dispatch cycle.

    ``block`` is set when *any* matching hook returned
    ``continue=false``; ``mutated_args`` carries the most-recent
    args-rewrite a hook produced (later hooks override earlier ones,
    matching CC semantics).
    """

    block: bool = False
    reason: Optional[str] = None
    mutated_args: Optional[dict[str, Any]] = None
    fired: list[str] = field(default_factory=list)  # source rules that ran


def parse_hooks_config(payload: Mapping[str, Any]) -> tuple[list[HookSpec], bool]:
    """Read the ``hooks`` block from a settings mapping.

    Returns ``(specs, enabled)``. Specs are returned even when
    ``enable_hooks`` is false — gives the doctor / status renderer a
    way to show "you have N hooks configured but they're disabled".
    """
    enabled = bool(payload.get("enable_hooks", False))
    raw = payload.get("hooks") or {}
    if not isinstance(raw, Mapping):
        raise ValueError(
            f"hooks block must be a mapping, got {type(raw).__name__}"
        )
    specs: list[HookSpec] = []
    for event, entries in raw.items():
        if event not in SUPPORTED_EVENTS:
            _LOG.warning("unknown hook event %r — skipping", event)
            continue
        if not isinstance(entries, list):
            raise ValueError(
                f"hooks.{event} must be a list, got {type(entries).__name__}"
            )
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ValueError(
                    f"hooks.{event}[…] entries must be mappings"
                )
            command = entry.get("command")
            if not isinstance(command, str) or not command.strip():
                raise ValueError(
                    f"hooks.{event}[…].command must be a non-empty string"
                )
            matcher = str(entry.get("matcher", "*")) or "*"
            specs.append(HookSpec(event=event, matcher=matcher, command=command))
    return specs, enabled


def _spec_matches(spec: HookSpec, tool_name: str, args: Mapping[str, Any]) -> bool:
    """Decide whether ``spec`` applies to a given tool invocation.

    ``"*"`` is the bare wildcard (matches any tool, any args). Any
    other matcher reuses the permission-grammar matcher so users only
    learn one rule dialect — ``Bash(git push *)`` works the same
    here as it does in ``permissions.allow``.
    """
    if spec.matcher.strip() == "*":
        return True
    return compile_matcher(spec.matcher)(tool_name, args)


def _dispatch_one(
    spec: HookSpec,
    *,
    event: str,
    tool_name: str,
    args: Mapping[str, Any],
    session_id: str,
    timeout: float,
) -> Optional[dict[str, Any]]:
    """Run a single hook command; return its parsed JSON response.

    Returns ``None`` when the hook fails (non-zero exit, timeout,
    invalid JSON) — failures are *not* a deny signal. Logging captures
    the diagnostic so users notice broken hooks without their tool
    calls getting blocked.
    """
    payload = json.dumps(
        {
            "event": event,
            "tool": tool_name,
            "args": dict(args or {}),
            "session_id": session_id,
        }
    )
    try:
        proc = subprocess.run(
            spec.command,
            shell=True,
            input=payload.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _LOG.warning("hook %r timed out after %.1fs", spec.command, timeout)
        return None
    except OSError as exc:
        _LOG.warning("hook %r failed to launch: %s", spec.command, exc)
        return None
    if proc.returncode != 0:
        _LOG.warning(
            "hook %r exit=%d stderr=%s",
            spec.command,
            proc.returncode,
            (proc.stderr or b"").decode("utf-8", errors="replace").strip()[:200],
        )
        return None
    body = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    if not body:
        return {"continue": True}
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        _LOG.warning("hook %r emitted non-JSON output: %s", spec.command, exc)
        return None
    if not isinstance(parsed, Mapping):
        _LOG.warning("hook %r returned non-object JSON: %r", spec.command, parsed)
        return None
    return dict(parsed)


def run_hooks(
    specs: Iterable[HookSpec],
    *,
    event: str,
    tool_name: str = "",
    args: Mapping[str, Any] | None = None,
    session_id: str = "",
    timeout: float = _DEFAULT_TIMEOUT_SEC,
    enabled: bool = True,
    env: Optional[Mapping[str, str]] = None,
) -> HookOutcome:
    """Fire all matching hooks for ``event``; return aggregate :class:`HookOutcome`.

    When ``enabled`` is false (master switch off) returns an empty
    :class:`HookOutcome` immediately — the master switch wins over
    individual matchers so a user who toggled hooks off in settings
    never sees a stale rule fire.

    Iterates hooks in declared order. The first ``continue=false``
    short-circuits with ``block=True``; ``args`` rewrites compose
    across hooks (each subsequent hook sees the previous rewrite).
    """
    if not enabled:
        return HookOutcome()

    args_dict: dict[str, Any] = dict(args or {})
    outcome = HookOutcome()
    if env:
        # Merge into os.environ for the subprocess shell so users can
        # reference $VAR in their hook command without exporting
        # globally — scoped to the dispatch loop.
        merged_env = dict(os.environ)
        merged_env.update(env)
        os.environ.update(env)  # noqa: S105 — env is operator-supplied
    for spec in specs:
        if spec.event != event:
            continue
        if not _spec_matches(spec, tool_name, args_dict):
            continue
        response = _dispatch_one(
            spec,
            event=event,
            tool_name=tool_name,
            args=args_dict,
            session_id=session_id,
            timeout=timeout,
        )
        outcome.fired.append(spec.matcher)
        if response is None:
            # Broken hook — fail open, log already emitted.
            continue
        if response.get("continue") is False:
            outcome.block = True
            reason = response.get("reason")
            outcome.reason = (
                str(reason) if isinstance(reason, str) else
                f"blocked by hook {spec.matcher!r}"
            )
            return outcome
        new_args = response.get("args")
        if isinstance(new_args, Mapping):
            args_dict = dict(new_args)
            outcome.mutated_args = args_dict

    return outcome


__all__ = [
    "HookOutcome",
    "HookSpec",
    "SUPPORTED_EVENTS",
    "parse_hooks_config",
    "run_hooks",
]
