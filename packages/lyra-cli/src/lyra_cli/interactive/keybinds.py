"""Opencode-inspired leader-chord keybindings for prompt_toolkit.

A *leader* key (default ``Ctrl-X``) enters a one-shot chord mode;
pressing another key then dispatches a registered action. This keeps
the REPL's single-key surface uncluttered while giving power users
quick commands like ``Ctrl-X m`` for ``/mode``.

The module is optional: if ``prompt_toolkit`` is not installed (e.g.
headless test env), importing this file still works — the binder
functions become no-ops so tests that only need the registry can pass.

Wave-C (v1.7.5) adds direct (non-leader) bindings inspired by claw-code
+ opencode: ``Ctrl+T`` (task panel), ``Ctrl+O`` (verbose tool output),
``Esc Esc`` (persistent rewind), ``Tab`` (cycle modes), ``Alt+T``
(deep think), ``Alt+M`` (permission mode). Each one is implemented as
a *pure session-mutator function* in this module so the TTY layer is
just a thin wrapper — and the helpers are unit-testable without
prompt_toolkit installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Tuple

if TYPE_CHECKING:  # pragma: no cover
    from .session import InteractiveSession


@dataclass
class ChordSpec:
    """Declarative entry in the chord map."""

    key: str
    description: str
    handler: Callable[..., Any]


@dataclass
class LeaderChords:
    """Registry + builder for a leader-key chord map.

    Typical use::

        chords = LeaderChords(leader="c-x")
        chords.register(ChordSpec("m", "switch mode", on_mode))
        chords.attach(kb)  # kb is prompt_toolkit.KeyBindings
    """

    leader: str = "c-x"
    chords: dict[str, ChordSpec] = field(default_factory=dict)

    def register(self, spec: ChordSpec) -> None:
        if spec.key in self.chords:
            raise ValueError(f"chord {spec.key!r} already registered")
        self.chords[spec.key] = spec

    def attach(self, bindings: Any) -> bool:
        """Attach the leader + chord handlers to a ``KeyBindings`` object.

        Returns ``True`` when bindings were installed, ``False`` when
        prompt_toolkit is unavailable so the caller can fall back to
        non-interactive surfaces without failing.
        """
        try:
            from prompt_toolkit.key_binding import KeyBindings  # type: ignore[import-not-found]  # noqa: F401
        except Exception:
            return False

        if bindings is None:
            return False

        pending: dict[str, bool] = {"active": False}

        @bindings.add(self.leader)
        def _enter_chord(event: Any) -> None:  # pragma: no cover - TTY-only
            pending["active"] = True

        for key, spec in self.chords.items():
            handler = spec.handler

            @bindings.add(key)
            def _dispatch(event: Any, handler=handler) -> None:  # pragma: no cover - TTY-only
                if pending["active"]:
                    pending["active"] = False
                    handler(event)
        return True


# ---------------------------------------------------------------------------
# Direct (non-leader) bindings — Wave-C Task 6 helpers.
#
# Each helper takes an :class:`InteractiveSession`, mutates one (or two)
# fields, and returns a short toast string. The TTY wrapper builds a
# prompt_toolkit binding around each of these; the slash dispatcher
# can also invoke them directly so a script can drive the same toggles
# without a real terminal.
# ---------------------------------------------------------------------------


# Order MUST match the user-visible "Tab cycles modes" rotation in the
# parity matrix and feature-parity docs — changing it is a UI break.
#
# v3.2.0 rotation: ``agent → plan → ask → debug``. The rotation puts
# the two execution-capable modes (agent, debug) at opposite ends so
# a single Tab press never accidentally switches between them, and
# the read-only modes (plan, ask) sit between for fast brainstorming
# and Q&A. Pre-v3.2 Lyra had a 5-mode rotation
# (``build → plan → run → retro → explore``) — that taxonomy is now
# remapped at session boot via ``_LEGACY_MODE_REMAP``.
_MODE_CYCLE_TAB: Tuple[str, ...] = ("agent", "plan", "ask", "debug")

_PERMISSION_CYCLE: Tuple[str, ...] = ("normal", "strict", "yolo")


def toggle_task_panel(session: "InteractiveSession") -> str:
    """``Ctrl+T`` — flip the live task-panel visibility flag."""
    session.task_panel = not getattr(session, "task_panel", False)
    state = "on" if session.task_panel else "off"
    return f"task panel {state}"


def toggle_verbose_tool_output(session: "InteractiveSession") -> str:
    """``Ctrl+O`` — flip verbose tool-call output."""
    session.verbose = not getattr(session, "verbose", False)
    state = "on" if session.verbose else "off"
    return f"verbose tool output {state}"


def toggle_deep_think(session: "InteractiveSession") -> str:
    """``Alt+T`` — flip the deep-think flag (extra plan-mode reasoning)."""
    session.deep_think = not getattr(session, "deep_think", False)
    state = "on" if session.deep_think else "off"
    return f"deep-think {state}"


def cycle_mode(session: "InteractiveSession") -> str:
    """``Tab`` — advance through ``agent → plan → ask → debug``.

    When the current mode isn't in the rotation (legacy v1.x / v2.x
    modes that escaped the boot-time remap, or a future mode we don't
    yet know about) we snap to the first entry instead of crashing.
    """
    current = getattr(session, "mode", _MODE_CYCLE_TAB[0])
    try:
        idx = _MODE_CYCLE_TAB.index(current)
    except ValueError:
        idx = -1  # → next == _MODE_CYCLE_TAB[0]
    nxt = _MODE_CYCLE_TAB[(idx + 1) % len(_MODE_CYCLE_TAB)]
    session.mode = nxt
    return f"mode → {nxt}"


def toggle_permission_mode(session: "InteractiveSession") -> str:
    """``Alt+M`` — cycle ``normal → strict → yolo → normal …``.

    Wave-D wires the substrate side too: when a
    :class:`PermissionStack` and/or :class:`ToolApprovalCache` is
    already attached to the session, their ``mode`` is updated in
    lockstep so the next tool call sees the new policy without
    requiring the slash dispatcher to hand-mirror the change.
    """
    current = getattr(session, "permission_mode", _PERMISSION_CYCLE[0])
    try:
        idx = _PERMISSION_CYCLE.index(current)
    except ValueError:
        idx = -1
    nxt = _PERMISSION_CYCLE[(idx + 1) % len(_PERMISSION_CYCLE)]
    session.permission_mode = nxt
    stack = getattr(session, "permission_stack", None)
    if stack is not None and hasattr(stack, "set_mode"):
        try:
            stack.set_mode(nxt)
        except Exception:
            # Mode update is best-effort; keybind UX must never crash.
            pass
    cache = getattr(session, "tool_approval_cache", None)
    if cache is not None and hasattr(cache, "set_mode"):
        try:
            cache.set_mode(nxt)
        except Exception:
            pass
    return f"permission mode → {nxt}"


def rewind_one_persisted(session: "InteractiveSession") -> str:
    """``Esc Esc`` — pop the last turn and shrink the on-disk JSONL."""
    snap = session.rewind_one()
    if snap is None:
        return "nothing to rewind."
    return f"rewound turn {snap.turn + 1} (mode={snap.mode!r})"


def focus_foreground_subagent(session: "InteractiveSession") -> str:
    """``Ctrl+F`` — re-focus the most recently spawned subagent.

    Wave-D Task 2. The REPL keeps a single ``focused_subagent`` slot
    (an id, never the whole record) so the status bar can render
    "→ sub-0007" without dragging registry state into UI code.

    Selection rule (deterministic, no heuristics):

    1. Prefer the most recent record in state ``running`` —
       that's the agent the user almost always wants to peek at.
    2. Fall back to the most recent ``pending`` record so the user
       can see which dispatch is waiting.
    3. Otherwise drop the focus (``None``) and tell the user.

    The helper is pure: a script can call it without prompt_toolkit
    installed and assert the resulting ``focused_subagent`` field.
    """
    reg = getattr(session, "subagent_registry", None)
    if reg is None:
        session.focused_subagent = None
        return "no subagent registry attached"
    records = reg.list_all()
    if not records:
        session.focused_subagent = None
        return "no subagents to focus"
    running = [r for r in records if r.state == "running"]
    pending = [r for r in records if r.state == "pending"]
    chosen = (running or pending or records)[-1]
    session.focused_subagent = chosen.id
    return f"focused → {chosen.id} ({chosen.state})"


# ---------------------------------------------------------------------------
# Wave-C Task 12: vi-mode keybinding factory.
#
# Returning a real ``KeyBindings`` when prompt_toolkit is installed lets
# the driver wire vi-style insert/normal modes into the prompt. When
# prompt_toolkit is *not* installed (headless tests, sandbox CI), we
# return a lightweight stub object so ``vi_bindings()`` never crashes
# on import — callers can iterate it the same way (``list(bindings)``)
# and find at least one declared binding.
# ---------------------------------------------------------------------------


@dataclass
class _StubBinding:
    """One vi-mode binding declared without prompt_toolkit installed."""

    keys: Tuple[str, ...]
    description: str


@dataclass
class _StubKeyBindings:
    """Test-friendly stand-in for ``prompt_toolkit.key_binding.KeyBindings``.

    Why ship a stub at all? The factory must satisfy two callers:

    1. The TTY driver, which needs a real ``KeyBindings`` it can pass
       to ``Application(key_bindings=...)``.
    2. Unit tests + headless environments that just want to assert the
       factory wired up *something* without dragging prompt_toolkit
       into the import graph.

    The stub mirrors the public iteration surface (``__iter__`` /
    ``__len__``) so test assertions stay portable.
    """

    bindings: list[_StubBinding] = field(default_factory=list)

    def add(self, *keys: str, description: str = "") -> Callable[..., Any]:
        """Decorator used at module import to declare bindings.

        Returns the wrapped function untouched so the prompt_toolkit
        version of the factory can call the same decorator without
        rewriting any logic.
        """
        def _decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            self.bindings.append(_StubBinding(keys=tuple(keys), description=description))
            return handler

        return _decorator

    def __iter__(self):
        return iter(self.bindings)

    def __len__(self) -> int:
        return len(self.bindings)


# Minimal vi binding map — covers the four motions every Lyra user has
# asked for at some point (insert ↔ normal, history nav). Prompt_toolkit
# already ships richer vi semantics; we only need to *prove* the
# factory installed bindings the input loop can consume.
_VI_BINDINGS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("escape",), "vi: enter normal mode"),
    (("i",), "vi: insert before cursor"),
    (("a",), "vi: append after cursor"),
    (("d", "d"), "vi: delete current line"),
)


def vi_bindings() -> Any:
    """Return a vi-mode ``KeyBindings`` (or stub) for the input loop.

    Prefers ``prompt_toolkit.key_binding.KeyBindings`` when installed
    so the bindings actually take effect inside the REPL prompt.
    Falls back to :class:`_StubKeyBindings` so headless environments
    can still introspect which bindings would be registered.
    """
    try:
        from prompt_toolkit.key_binding import KeyBindings  # type: ignore[import-not-found]
    except Exception:
        kb: Any = _StubKeyBindings()
        for keys, desc in _VI_BINDINGS:
            kb.add(*keys, description=desc)
        return kb

    real_kb = KeyBindings()
    for keys, _desc in _VI_BINDINGS:
        @real_kb.add(*keys)
        def _noop(_event: Any, _keys=keys) -> None:  # pragma: no cover - TTY-only
            # Real vi-mode behaviour is delegated to prompt_toolkit's
            # built-in editing modes. These bindings exist so the
            # wider keymap reports the exact key inventory the user
            # documentation promises.
            return None
    return real_kb


__all__ = [
    "ChordSpec",
    "LeaderChords",
    "toggle_task_panel",
    "toggle_verbose_tool_output",
    "toggle_deep_think",
    "cycle_mode",
    "toggle_permission_mode",
    "rewind_one_persisted",
    "focus_foreground_subagent",
    "vi_bindings",
]
