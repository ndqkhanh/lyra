"""Terminal-facing driver: prompt_toolkit (fancy) and ``input()`` (plain).

The driver is the ONLY place in the interactive stack that touches stdio,
so every subtle behaviour (history, bottom toolbar, Ctrl-D handling,
non-TTY fallback) lives here and is kept small.

UX model — patterned on Claude Code, sst/opencode, and Hermes Agent,
translated into our colour vocabulary and toolchain:

- ``plan ›`` prompt glyph in the mode's brand colour. Modes cycle
  ``plan → build → run → explore → retro`` via Tab, reverse via
  Shift-Tab.
- Rich rendering of every structured command result; strings-only for
  the non-TTY path and for tests.
- Bottom status bar shows repo · mode · model · turn · tokens · cost
  (+ deep-think / budget badges when active) and a compact
  key-binding strip.
- ``!cmd`` prefix runs ``cmd`` in a subshell and displays the output
  inside a result panel (Claude-Code bash mode).
- ``@path`` triggers the repo path completer (Claude-Code @file mention).
- ``Ctrl-L`` clears + reprints banner, buffer intact.
- ``Ctrl-G`` opens ``$EDITOR`` for a long prompt (opencode/Hermes).
- ``Ctrl-T`` / ``Ctrl-O`` toggle task-panel / verbose echo.
- ``Alt-T`` toggles deep-think (Claude-Code extended thinking).
- ``Alt-P`` prints the model catalog so users can pick (``/model`` then
  applies the switch).
- ``Esc Esc`` rewinds the last turn (alias for ``/rewind``).
- Multi-line: ``Alt-Enter`` or ``Ctrl-J`` inserts a newline; a line
  ending with ``\\`` keeps the editor open on the next Enter.
- ``Ctrl-C`` cancels the in-progress line; ``Ctrl-D`` / ``/exit`` leaves
  the REPL with a session-summary goodbye panel.

Two render paths: prompt_toolkit for real TTYs, plain ``input()`` for
piped / CI stdin. Every affordance above gracefully degrades on the
plain path so headless invocations stay deterministic.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def _terminal_columns_safe() -> int:
    """Best-effort terminal width for layout decisions. Floors at 60."""
    try:
        return max(60, shutil.get_terminal_size(fallback=(80, 24)).columns)
    except (OSError, ValueError):
        return 80

from prompt_toolkit import PromptSession
from prompt_toolkit.application.current import get_app
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from .suggest import CommandAutoSuggest
from rich.console import Console
from rich.text import Text

from .keybindings_help import show_keybindings_help

from . import output as _out
from . import keybinds as _keybinds
from .banner import render_banner, render_sparse_banner
from .banner_claude import (
    render_claude_style_banner,
    render_input_frame,
    render_using_line,
)
from .completer import SlashCompleter
from .hir import HIRLogger, default_event_path
from .session import (
    CommandResult,
    InteractiveSession,
    _MODE_CYCLE,
    display_mode,
)
from .spinner import Spinner
from . import store as _store
from . import themes as _themes


def _history_path(repo_root: Path) -> Path:
    state_dir = repo_root / ".lyra"
    state_dir.mkdir(exist_ok=True)
    return state_dir / "interactive_history"


def _render_result(console: Console, result: CommandResult) -> None:
    """Prefer a Rich renderable when one is supplied; fall back to text."""
    if result.clear_screen:
        console.clear()
    if result.renderable is not None:
        console.print(result.renderable)
        return
    if not result.output:
        return
    # markup=False keeps ``[plan]``-style labels from being parsed as
    # Rich markup tags and silently dropped.
    console.print(result.output, markup=False, highlight=False)


def _resolve_banner_model(model: str) -> str:
    """Return the string the banner should show for ``Model …``.

    For concrete model slugs (``mock``, ``deepseek``, ``gpt-5``,
    ``claude-opus-4.5``) we pass through unchanged — that's what
    the user typed and what the session persists.

    For the implicit default ``auto`` we *resolve* via
    :func:`describe_selection` so the banner reads
    "Model deepseek · deepseek-chat" instead of the bare flag value
    "Model auto", which is technically correct but unhelpful — the
    user wants to see *which* backend the cascade landed on.

    :func:`describe_selection` is idempotent and stdlib-only (no
    network), so calling it on every banner refresh stays cheap.
    """
    if model.strip().lower() != "auto":
        return model
    try:
        from ..llm_factory import describe_selection

        return describe_selection("auto")
    except Exception:  # pragma: no cover — defensive
        # Banner rendering must never crash the REPL; on any error
        # fall back to the raw flag value.
        return model


def _apply_budget_settings(
    session: InteractiveSession,
    *,
    override: float | None = None,
) -> None:
    """Seed the session's budget cap + meter from CLI flag or store.

    Resolution order:

    1. ``override`` — non-None means the user passed ``--budget`` and
       wants this exact cap for this session. Persisted defaults are
       ignored.
    2. The cap already on the session — preserved when ``--resume``
       loaded a snapshot with a saved cap.
    3. ``lyra_core.auth.store.load_budget()`` — the user's persisted
       default (set via ``/budget save`` or ``lyra connect``).

    Always materialises a :class:`BudgetMeter` on the session so
    :func:`_chat_with_llm` can preflight every turn against
    ``meter.gate()`` without checking for ``None`` first.
    """
    from .budget import BudgetCap, BudgetMeter

    persisted: dict[str, Any] = {}
    try:
        from lyra_core.auth.store import load_budget

        persisted = load_budget()
    except Exception:  # pragma: no cover — store IO failures are non-fatal
        persisted = {"cap_usd": None, "alert_pct": 80.0, "auto_stop": True}

    if override is not None:
        cap = float(override)
    elif session.budget_cap_usd is not None:
        cap = float(session.budget_cap_usd)
    else:
        cap = persisted.get("cap_usd")

    session.budget_cap_usd = cap
    session.budget_auto_stop = bool(persisted.get("auto_stop", True))

    cap_obj = (
        BudgetCap(
            limit_usd=float(cap),
            alert_pct=float(persisted.get("alert_pct", 80.0)),
        )
        if cap is not None
        else None
    )
    if getattr(session, "budget_meter", None) is None:
        session.budget_meter = BudgetMeter(cap=cap_obj)
    else:
        session.budget_meter.cap = cap_obj


def _wire_observability_to_lifecycle(
    session: InteractiveSession, hir: HIRLogger
) -> None:
    """Bridge :class:`LifecycleBus` to HIR JSONL + optional OTel (Phase E.3).

    The REPL already writes ``user.prompt``, ``slash.dispatch``,
    ``bash.run``, ``mode.change``, ``session.start``, ``session.end``
    through the per-session :class:`HIRLogger` from inside the driver
    loop. v2.7 adds the missing fan-in for the events emitted by
    :func:`session._chat_with_llm` (Phase D.3): every ``turn_start`` /
    ``turn_complete`` / ``turn_rejected`` / ``tool_call`` is now also
    journaled to ``.lyra/sessions/events.jsonl`` under the
    corresponding kernel-canonical kind name.

    OTel fan-out is opt-in via ``LYRA_OTEL_COLLECTOR``:

    * unset / ``""`` / ``off`` — only the HIR JSONL path runs.
    * ``in-memory`` — install
      :class:`lyra_core.observability.InMemoryCollector` so tests can
      assert the events without touching the network.
    * ``otel`` — install
      :class:`lyra_core.observability.OpenTelemetryCollector`, which
      tries to use the global ``opentelemetry.trace`` provider; missing
      SDK raises :class:`FeatureUnavailable` which we swallow with a
      warning so the REPL stays functional offline.

    All failures are best-effort: a broken collector or a write error
    must never break a chat turn.
    """
    try:
        from .session import _ensure_lifecycle_bus
        from lyra_core.hooks.lifecycle import LifecycleEvent
    except Exception:
        return

    bus = _ensure_lifecycle_bus(session)
    if bus is None:
        return

    collector_kind = (
        os.environ.get("LYRA_OTEL_COLLECTOR", "").strip().lower()
    )
    collector: Any = None
    if collector_kind == "in-memory":
        try:
            from lyra_core.observability import InMemoryCollector

            collector = InMemoryCollector()
            session._otel_collector = collector  # type: ignore[attr-defined]
        except Exception:
            collector = None
    elif collector_kind in ("otel", "opentelemetry"):
        try:
            from lyra_core.observability import OpenTelemetryCollector

            collector = OpenTelemetryCollector()
            session._otel_collector = collector  # type: ignore[attr-defined]
        except Exception:
            collector = None

    def _journal(event_name: str, payload: dict[str, Any]) -> None:
        # 1. HIR JSONL via the existing CLI-local logger.
        try:
            hir.log(
                f"chat.{event_name}",
                dict(payload),
                session_turn=session.turn,
            )
        except Exception:
            pass
        # 2. Optional OTel fan-out.
        if collector is None:
            return
        try:
            collector.submit(
                {
                    "session_id": getattr(session, "session_id", "lyra"),
                    "ts": payload.get("ts") or "",
                    "kind": f"chat.{event_name}",
                    "attributes": dict(payload),
                }
            )
        except Exception:
            pass

    bus.subscribe(
        LifecycleEvent.SESSION_START,
        lambda payload: _journal("session_start", payload),
    )
    bus.subscribe(
        LifecycleEvent.TURN_START,
        lambda payload: _journal("turn_start", payload),
    )
    # v3.5.0 (Phase O.2): journal which progressive skills fired for
    # the upcoming turn so observers (HIR JSONL / OTel) can correlate
    # skill activation with eventual ``turn_complete`` /
    # ``turn_rejected`` and the skill ledger's utility stats.
    if hasattr(LifecycleEvent, "SKILLS_ACTIVATED"):
        bus.subscribe(
            LifecycleEvent.SKILLS_ACTIVATED,
            lambda payload: _journal("skills.activated", payload),
        )
    bus.subscribe(
        LifecycleEvent.TURN_COMPLETE,
        lambda payload: _journal("turn_complete", payload),
    )
    bus.subscribe(
        LifecycleEvent.TURN_REJECTED,
        lambda payload: _journal("turn_rejected", payload),
    )
    bus.subscribe(
        LifecycleEvent.TOOL_CALL,
        lambda payload: _journal("tool_call", payload),
    )
    bus.subscribe(
        LifecycleEvent.SESSION_END,
        lambda payload: _journal("session_end", payload),
    )


def _wire_skill_telemetry_to_lifecycle(session: InteractiveSession) -> None:
    """Bridge ``turn_complete`` / ``turn_rejected`` to the skill ledger.

    Phase O.2 records per-skill outcomes so future Read–Write
    Reflective Learning passes (``lyra skill stats`` / ``lyra skill
    reflect`` / ``lyra skill consolidate``) can rank skills by
    utility instead of guessing.

    The recorder is installed on ``session._skill_activation_recorder``
    so the chat handler (in :func:`session._augment_system_prompt_with_skills`)
    can stash per-turn activations on it; the lifecycle hooks here
    settle each turn's activations into the ledger.

    All failures are best-effort — a missing ``lyra_skills`` package,
    a read-only home directory, etc. must never break a chat turn.
    """
    try:
        from .session import _ensure_lifecycle_bus
        from lyra_core.hooks.lifecycle import LifecycleEvent
        from .skills_telemetry import SkillActivationRecorder
    except Exception:
        return

    bus = _ensure_lifecycle_bus(session)
    if bus is None:
        return

    recorder = getattr(session, "_skill_activation_recorder", None)
    if recorder is None:
        try:
            recorder = SkillActivationRecorder()
        except Exception:
            return
        session._skill_activation_recorder = recorder

    def _on_complete(payload: dict[str, Any]) -> None:
        try:
            sid = str(getattr(session, "session_id", None) or "lyra")
            recorder.on_turn_complete(session_id=sid, turn=int(session.turn))
        except Exception:
            pass

    def _on_rejected(payload: dict[str, Any]) -> None:
        try:
            reason = str(payload.get("reason") or "rejected")
            sid = str(getattr(session, "session_id", None) or "lyra")
            recorder.on_turn_rejected(
                session_id=sid, turn=int(session.turn), reason=reason
            )
        except Exception:
            pass

    bus.subscribe(LifecycleEvent.TURN_COMPLETE, _on_complete)
    bus.subscribe(LifecycleEvent.TURN_REJECTED, _on_rejected)


def _wire_plugins_to_lifecycle(session: InteractiveSession) -> None:
    """Discover ``lyra.plugins`` entry points and bridge them to the bus.

    Plugins can opt into lifecycle notifications by exposing any of:

    * ``on_session_start(payload)`` / ``on_turn_start`` /
      ``on_turn_complete`` / ``on_turn_rejected`` / ``on_tool_call``
      / ``on_session_end`` — single-event hooks; or
    * ``on_lifecycle_event(event_name, payload)`` — universal sink
      receiving the lowercase event name (``"turn_start"`` etc.) and
      the same payload dict the bus emits.

    Plugin discovery is *additive*: an in-process plugin already
    on ``session.plugins`` is preserved, with the entry-point set
    appended. Each plugin is wrapped in a try/except so a buggy
    third-party plugin can't trip telemetry for the user.
    """
    try:
        from lyra_core.plugins import discover_plugins
        from lyra_core.hooks.lifecycle import LifecycleEvent
    except Exception:
        return

    extra = list(getattr(session, "plugins", []) or [])
    discovered = discover_plugins(extra=extra) or []
    session.plugins = list(discovered)
    if not discovered:
        return

    from .session import _ensure_lifecycle_bus

    bus = _ensure_lifecycle_bus(session)
    if bus is None:
        return

    def _bind(event: LifecycleEvent, hook_name: str) -> None:
        for plugin in discovered:
            target = getattr(plugin, hook_name, None)
            universal = getattr(plugin, "on_lifecycle_event", None)
            if not callable(target) and not callable(universal):
                continue

            def _make_subscriber(p: Any, t: Any, u: Any, ev: LifecycleEvent):
                def _sub(payload: dict[str, Any]) -> None:
                    if callable(t):
                        try:
                            t(payload)
                        except Exception:
                            pass
                    if callable(u):
                        try:
                            u(ev.value, payload)
                        except Exception:
                            pass

                return _sub

            bus.subscribe(event, _make_subscriber(plugin, target, universal, event))

    _bind(LifecycleEvent.SESSION_START, "on_session_start")
    _bind(LifecycleEvent.TURN_START, "on_turn_start")
    if hasattr(LifecycleEvent, "SKILLS_ACTIVATED"):
        _bind(LifecycleEvent.SKILLS_ACTIVATED, "on_skills_activated")
    _bind(LifecycleEvent.TURN_COMPLETE, "on_turn_complete")
    _bind(LifecycleEvent.TURN_REJECTED, "on_turn_rejected")
    _bind(LifecycleEvent.TOOL_CALL, "on_tool_call")
    _bind(LifecycleEvent.SESSION_END, "on_session_end")


def _read_ui_settings() -> dict:
    """Return the ``ui`` block from ``$LYRA_HOME/settings.json`` (or {})."""
    try:
        from lyra_core.auth.store import lyra_home
        from ..config_io import load_settings

        settings = load_settings(lyra_home() / "settings.json")
    except Exception:
        return {}
    ui = settings.get("ui")
    return ui if isinstance(ui, dict) else {}


def _print_banner(
    *, repo_root: Path, model: str, mode: str, plain: bool
) -> None:
    ui = _read_ui_settings()
    # Phase 1 (May 2026 redesign): the new default is the sparse,
    # one-line banner — see ``render_sparse_banner``. Users who liked
    # the old gradient logo or the multi-line Claude-style frame can
    # still opt in via ``ui.banner_style = "fancy" | "claude"``.
    style = ui.get("banner_style", "sparse")

    if style == "claude" and not plain:
        resolved_model = _resolve_banner_model(model)
        banner = render_claude_style_banner(
            user_name=ui.get("user_name") or os.environ.get("USER", "there"),
            model=resolved_model,
            plan=ui.get("plan", "Lyra Pro"),
            organization=ui.get("organization", ""),
            cwd=repo_root,
            tips=ui.get("tips", [
                "Run /init to create a LYRA.md",
                f"Note: You have launched in {mode}",
            ]),
            whats_new=ui.get("whats_new", [
                "/release-notes for more",
            ]),
        )
        using = render_using_line(
            model=resolved_model,
            settings_source=ui.get("settings_source", ".lyra/settings.json"),
        )
        frame = render_input_frame(
            mode=mode,
            effort=ui.get("effort", "high"),
        )
        sys.stdout.write(banner)
        sys.stdout.write("\n")
        sys.stdout.write(using)
        sys.stdout.write("\n")
        sys.stdout.write(frame)
        sys.stdout.flush()
        return

    if style == "fancy":
        banner = render_banner(
            repo_root=repo_root,
            model=_resolve_banner_model(model),
            mode=mode,
            plain=plain,
        )
    else:
        # Default: the new sparse one-liner.
        banner = render_sparse_banner(
            repo_root=repo_root,
            model=_resolve_banner_model(model),
            mode=mode,
            plain=plain,
        )
    sys.stdout.write(banner)
    sys.stdout.flush()


def run(
    *,
    repo_root: Path,
    model: str,
    mode: str = "agent",
    resume: bool = False,
    resume_id: str | None = None,
    pin_session_id: str | None = None,
    budget_cap_usd: float | None = None,
    bare: bool = False,
) -> int:
    """Start the REPL. Returns the process exit code.

    ``budget_cap_usd`` is an explicit one-shot override (typically
    plumbed from ``lyra --budget 5``). When ``None`` the driver falls
    back to the persisted ``~/.lyra/auth.json`` ``budget`` block — see
    :func:`_apply_budget_settings`.

    ``resume_id`` (v3.2.0, Phase L) names a specific session under
    ``<repo>/.lyra/sessions/<id>/turns.jsonl`` to attach to before
    the first prompt. It can be:

    * a full session id (``sess-20260427-1234``)
    * the literal ``"latest"`` / ``"last"`` / ``"recent"`` — most
      recently modified session
    * a unique prefix of an id

    When ``resume_id`` is set the REPL boots with the restored
    ``_chat_history``, ``_turns_log``, mode, model, and cost so the
    user picks up exactly where they left off — no slash command
    needed. ``resume`` (the legacy boolean) still loads a JSON
    snapshot from ``interactive/store.py`` for back-compat.
    """
    # v3.2.0 (Phase L): every fresh REPL writes ``turns.jsonl`` by
    # default so ``lyra session list`` and ``--resume`` work without
    # opt-in. Pre-v3.2 the driver constructed ``InteractiveSession``
    # without a ``sessions_root``, which made ``_persist_turn`` a
    # no-op — meaning the user's first run always vanished on exit.
    sessions_root_default = repo_root / ".lyra" / "sessions"
    try:
        sessions_root_default.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Read-only filesystem (rare). Persistence will degrade to
        # in-memory only; the REPL stays alive.
        pass

    # New: ``--resume <id>`` / ``--continue`` / ``--session <id>``
    # plumbing. Tries to rebuild the live session from disk; falls
    # through to a fresh session when the id can't be resolved. When
    # ``pin_session_id`` is set (from ``--session ID``) we pin the
    # fresh session to that exact id so subsequent ``--resume ID``
    # attaches back to this run.
    session: InteractiveSession | None = None
    if resume_id:
        from .session import _resolve_session_reference

        target = _resolve_session_reference(
            resume_id, sessions_root_default, fallback=resume_id
        )
        restored = InteractiveSession.resume_session(
            session_id=target,
            sessions_root=sessions_root_default,
            repo_root=repo_root,
        )
        if restored is None:
            # Pinned id (``--session ID``) suppresses the warning and
            # creates a fresh session with that exact id below — that's
            # the documented "create-or-resume" semantic.
            if pin_session_id is None:
                sys.stderr.write(
                    f"lyra: --resume {resume_id!r} could not be resolved "
                    f"under {sessions_root_default}. starting a fresh session.\n"
                )
        else:
            session = restored
            # Honour an explicit ``--model`` override (CLI flag wins
            # over the persisted slug); leave ``session.model`` alone
            # when the user just typed ``--model auto``.
            if model != "auto":
                session.model = model

    if session is None:
        if resume:
            try:
                session = _store.load(repo_root)
                session.repo_root = repo_root
                # The CLI default for ``--model`` / ``--llm`` is ``"auto"``
                # in v2.1; only override the persisted snapshot's model when
                # the user explicitly named one (anthropic, deepseek, etc.).
                if model != "auto":
                    session.model = model
                session.mode = session.mode or mode
                # Pre-v3.2 snapshots didn't carry a JSONL
                # ``sessions_root`` — wire one in so subsequent turns
                # land in the new layout.
                if session.sessions_root is None:
                    session.sessions_root = sessions_root_default
            except FileNotFoundError:
                fresh_kwargs: dict[str, Any] = dict(
                    repo_root=repo_root,
                    model=model,
                    mode=mode,
                    sessions_root=sessions_root_default,
                )
                if pin_session_id:
                    fresh_kwargs["session_id"] = pin_session_id
                session = InteractiveSession(**fresh_kwargs)
        else:
            fresh_kwargs = dict(
                repo_root=repo_root,
                model=model,
                mode=mode,
                sessions_root=sessions_root_default,
            )
            if pin_session_id:
                fresh_kwargs["session_id"] = pin_session_id
            session = InteractiveSession(**fresh_kwargs)

    # v3.10 ``--bare`` mode: disable every auto-discovery surface so
    # headless / CI / debugging runs are deterministic. Setting these
    # *before* the budget / MCP / cron blocks below means a single
    # flag flips the whole posture rather than threading a flag into
    # each subsystem. The fields below are pre-existing session
    # toggles; ``--bare`` just flips them all off in one move.
    if bare:
        session.skills_inject_enabled = False
        session.memory_inject_enabled = False
        # Pre-cache an empty policy + hooks tuple so the agent loop's
        # lazy loader skips the disk read entirely. None as the policy
        # means "no user rules" → falls back to the LOW_RISK + ASK
        # legacy path, which is exactly the deterministic posture
        # ``--bare`` is supposed to produce.
        session._policy_hooks_cache = (None, [], False)

    # Auto-budget: explicit CLI flag wins, otherwise use the persisted
    # default. Only seeds *fresh* sessions — when ``--resume`` carries a
    # cap from disk we leave it alone unless the user supplied a flag.
    _apply_budget_settings(session, override=budget_cap_usd)

    console = Console()
    plain = not sys.stdout.isatty()

    # Streaming chat (v2.2.4). Only enable when:
    #   * stdout is a TTY (non-plain),
    #   * the user hasn't disabled it via ``LYRA_NO_STREAM``.
    # The session field stays False for non-TTY / plain runs and
    # ``_chat_with_llm`` will use the existing non-streaming path.
    streaming_off = os.environ.get("LYRA_NO_STREAM", "").strip().lower() in (
        "1", "true", "yes", "on"
    )
    session._console = console
    session._streaming_enabled = (not plain) and (not streaming_off)

    # Phase-8 onboarding wizard: fires only on a true first-run TTY
    # session with no saved key and no env-var override. The wizard is
    # purely additive — Ctrl-C dismisses it without persisting state.
    try:
        from .onboarding import run_wizard, should_run_wizard

        if should_run_wizard():
            run_wizard(console=console)
    except Exception:  # pragma: no cover — never block REPL boot on UX flow
        # If the wizard fails for any reason (terminal cap missing,
        # transient network, anything) we still want to drop the user
        # into the REPL with a working banner.
        pass

    # v2.5.0 (Phase C.2): autoload MCP servers from ~/.lyra/mcp.json and
    # <repo>/.lyra/mcp.json so chat tool calls in this session can route
    # through them. Cheap (no child spawned yet); each server only spins
    # up on first actual ``/mcp connect`` or first chat tool dispatch.
    # ``--bare`` skips the autoload entirely so a CI run never makes a
    # network call against a config left on disk by a prior dev session.
    if not bare:
        try:
            from .mcp_autoload import autoload_mcp_servers

            autoload_mcp_servers(session)
        except Exception:
            # Never block REPL boot on MCP problems — chat still works.
            pass

    # v2.6.0 (Phase D.2): start the cron daemon so scheduled jobs fire
    # while the REPL is alive. Best-effort — missing lyra-core or
    # ``LYRA_DISABLE_CRON_DAEMON=1`` keeps the REPL fully functional
    # without it. ``--bare`` skips the daemon — scheduled jobs are an
    # auto-discovery surface and bare mode is precisely "no surprises".
    if not bare:
        try:
            from .cron_daemon import start_cron_daemon

            start_cron_daemon(session)
        except Exception:
            pass

    # v2.6.0 (Phase D.4): discover plugins and wire them onto the
    # session-scoped LifecycleBus so they receive the events emitted
    # in :func:`session._chat_with_llm`. Best-effort — discovery may
    # surface third-party packages that fail to import, and that
    # must never block REPL boot.
    try:
        _wire_plugins_to_lifecycle(session)
    except Exception:
        pass

    # v3.5.0 (Phase O.2): install the skill activation recorder and
    # bridge ``turn_complete`` / ``turn_rejected`` to the skill ledger
    # at ``~/.lyra/skill_ledger.json``. Skill outcomes drive the
    # Memento-style Read-Write Reflective Learning loop (utility-aware
    # activation, ``lyra skill stats`` / ``reflect`` / ``consolidate``).
    # Best-effort — a missing ``lyra_skills`` package or read-only
    # home directory must never block REPL boot.
    try:
        _wire_skill_telemetry_to_lifecycle(session)
    except Exception:
        pass

    # v2.6.0 (Phase D.6): wire the SQLite + FTS5 session store so
    # ``/search`` works out of the box. Pre-warming at boot keeps the
    # first /search snappy even on large histories. Best-effort: if
    # SQLite/FTS5 is unavailable the helper returns ``None`` and
    # /search degrades to a friendly diagnostic.
    try:
        from .session import _ensure_default_search_fn

        _ensure_default_search_fn(session)
    except Exception:
        pass

    _print_banner(
        repo_root=repo_root, model=session.model, mode=session.mode, plain=plain
    )

    hir = HIRLogger(default_event_path(repo_root))
    hir.on_session_start(
        repo_root=repo_root, model=session.model, mode=session.mode
    )

    # v2.7.0 (Phase E.3): bridge the chat-handler LifecycleBus events
    # added in Phase D.3 to the HIR JSONL log (and optionally an OTel
    # collector via ``LYRA_OTEL_COLLECTOR=in-memory|otel``). Best-effort
    # — if lyra-core is missing the bus type, the bridge is a no-op.
    try:
        _wire_observability_to_lifecycle(session, hir)
    except Exception:
        pass

    try:
        if sys.stdin.isatty() and sys.stdout.isatty():
            return _run_prompt_toolkit(session, console, hir)
        return _run_plain(session, console, hir)
    finally:
        hir.on_session_end(
            turns=session.turn,
            cost_usd=session.cost_usd,
            tokens=session.tokens_used,
        )
        hir.close()
        try:
            from .session import _emit_lifecycle

            _emit_lifecycle(
                session,
                "session_end",
                {
                    "turns": session.turn,
                    "cost_usd": session.cost_usd,
                    "tokens": session.tokens_used,
                },
            )
        except Exception:
            pass
        try:
            from .mcp_autoload import shutdown_all_mcp_clients

            shutdown_all_mcp_clients(session)
        except Exception:
            pass
        try:
            from .cron_daemon import stop_cron_daemon

            stop_cron_daemon(session)
        except Exception:
            pass
        store = getattr(session, "_session_store", None)
        if store is not None:
            try:
                store.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# prompt_toolkit path
# ---------------------------------------------------------------------------


def _run_prompt_toolkit(
    session: InteractiveSession, console: Console, hir: HIRLogger
) -> int:  # pragma: no cover — requires a real TTY
    history = (
        FileHistory(str(_history_path(session.repo_root)))
        if os.access(session.repo_root, os.W_OK)
        else InMemoryHistory()
    )
    kb = _build_key_bindings(session, console, hir)

    pt_session: PromptSession = PromptSession(
        history=history,
        completer=SlashCompleter(repo_root=session.repo_root),
        complete_while_typing=True,
        # Reserve vertical space for the completion menu so the slash
        # palette actually renders — without this, prompt_toolkit will
        # silently squash the menu to zero rows whenever the bottom
        # toolbar + short terminals leave no room. 8 rows matches
        # Claude-Code's palette height and scrolls the rest.
        reserve_space_for_menu=8,
        # Ghost-text suggestions: the fish/Claude-Code/hermes trick where
        # the next likely command appears in dim grey under your cursor
        # and ``→`` / ``Ctrl-E`` accepts it. Built on prompt_toolkit's
        # history suggester with extra priorities for the slash registry.
        auto_suggest=CommandAutoSuggest(),
        bottom_toolbar=lambda: _bottom_toolbar(session),
        key_bindings=kb,
        mouse_support=False,
        # Intentionally NOT setting ``enable_history_search=True``: prompt_toolkit
        # silently disables the buffer-level ``complete_while_typing`` filter when
        # history search is on (see prompt_toolkit/shortcuts/prompt.py — the Buffer
        # is wired with ``Condition(complete_while_typing AND NOT enable_history_search)``).
        # That nukes the dropdown after the first keystroke (e.g. ``/`` opens the
        # palette via our explicit ``start_completion``, but typing ``m`` clears
        # ``complete_state`` and never re-fires). Up/Down history walk still works;
        # Ctrl-R reverse-search remains available via the ``c-r`` keybinding below.
        multiline=False,
        prompt_continuation=_prompt_continuation,
        # Ghost text colour follows the skin's ``dim`` token so it
        # visually matches the rest of the chrome (otherwise the default
        # is a fixed grey that looks wrong on light/custom palettes).
        style=_prompt_style(),
    )

    while True:
        try:
            if session.vim_mode:
                pt_session.editing_mode = EditingMode.VI
            else:
                pt_session.editing_mode = EditingMode.EMACS
            line = pt_session.prompt(lambda: _prompt_fragments(session))
        except EOFError:
            _save_on_exit(session)
            _print_goodbye(console, session)
            return 0
        except KeyboardInterrupt:
            # Ctrl-C should cancel the current buffer, not kill the REPL.
            # prompt_toolkit raises KeyboardInterrupt on an empty buffer
            # when the user hits Ctrl-C twice in a row — treat that as
            # a soft message, not a crash.
            console.print(
                Text(" (interrupted — press Ctrl-D to exit)", style="#6B7280")
            )
            continue

        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("!"):
            _run_bash(console, stripped[1:].strip(), session=session, hir=hir)
            continue

        hir.on_prompt(turn=session.turn, mode=session.mode, line=stripped)

        if stripped.startswith("/"):
            # Slash commands are pure dispatch — no spinner. They're
            # always instant in v1 (no I/O), and even when /evals or
            # /ultrareview do real work later, those handlers will own
            # their own progress UI rather than this loop's.
            result = session.dispatch(line)
        else:
            # Plain text → mode handler. This is the seam Phase 14's
            # CodeAct LLM call hooks into; today the handlers are stubs,
            # but wrapping them in the agent-turn helper means the day
            # we plug in a real LLM, every turn already gets the live
            # "thinking…" spinner + duration tag for free.
            result = _run_agent_turn(console, session, line)
        _render_result(console, result)

        if stripped.startswith("/"):
            parts = stripped[1:].split(maxsplit=1)
            name = parts[0].lower() if parts else ""
            args = parts[1] if len(parts) > 1 else ""
            hir.on_slash(turn=session.turn, name=name, args=args)
            _post_slash_actions(name, args, session, console)

        if result.should_exit:
            _save_on_exit(session)
            _print_goodbye(console, session)
            return 0


def _post_slash_actions(
    name: str, args: str, session: InteractiveSession, console: Console
) -> None:  # pragma: no cover — driver glue
    """Side effects that must run after the pure dispatch layer returns.

    Keeping them here (not in :mod:`.session`) lets the session stay
    pure / unit-testable while still getting Claude-Code-style effects
    like "actually write the export file" or "actually load a snapshot".
    """
    if name == "export":
        path = (
            session.repo_root / ".lyra" / "exports"
            / f"turn-{session.turn}.md"
        )
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_transcript_markdown(session), encoding="utf-8")
            console.print(
                Text(f" → wrote {path}", style="#7CFFB2")
            )
        except OSError as exc:
            console.print(
                Text(f" (export failed: {exc})", style="#FF5370")
            )
    elif name == "handoff":
        path = session.repo_root / ".lyra" / "handoff.md"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_handoff_markdown(session), encoding="utf-8")
            console.print(
                Text(f" → staged {path}", style="#7CFFB2")
            )
        except OSError as exc:
            console.print(
                Text(f" (handoff failed: {exc})", style="#FF5370")
            )
    elif name == "fork":
        fork_name = args.strip() or f"fork-{session.turn}"
        try:
            path = _store.fork(session, name=fork_name)
            console.print(
                Text(f" → snapshot at {path}", style="#7CFFB2")
            )
        except OSError as exc:
            console.print(
                Text(f" (fork failed: {exc})", style="#FF5370")
            )
    elif name == "resume":
        # v3.2.0 (Phase L): the slash handler ``_cmd_resume`` is now
        # the *only* code path that restores a session. Pre-v3.2 the
        # driver also fired the JSON-snapshot loader here as a second
        # pass, which produced two well-known bugs:
        #
        # 1. When the user resumed a JSONL session id (the common
        #    case), ``store.load`` couldn't find a matching JSON
        #    snapshot file and printed ``(unknown session …)`` *after*
        #    the slash handler had already succeeded — making it look
        #    like resume failed when it actually didn't.
        # 2. When the JSON snapshot did exist (e.g. the user named a
        #    timestamp id), the driver overwrote the JSONL state the
        #    slash handler had just installed, blowing away the
        #    just-restored ``_chat_history`` and model slots.
        #
        # We keep the branch as a no-op marker so future maintainers
        # see the intentional gap before reintroducing a snapshot
        # loader (which would belong behind a different slash, e.g.
        # ``/snapshot load <ts>``, not on top of ``/resume``).
        return
    elif name == "sessions":
        entries = _store.list_sessions(session.repo_root)
        if not entries:
            console.print(Text(" (no saved sessions yet)", style="#6B7280 italic"))
            return
        for e in entries:
            console.print(
                Text.assemble(
                    ("  • ", "#6B7280"),
                    (e["id"], "bold #00E5FF"),
                    ("  ", ""),
                    (e["name"], "bright_white"),
                    ("   turn=", "#6B7280"),
                    (str(e["turn"]), "#00E5FF"),
                    ("   ", ""),
                    (e["saved_at"], "#6B7280"),
                )
            )


def _save_on_exit(session: InteractiveSession) -> None:  # pragma: no cover
    """Persist the session so ``/resume`` on next run picks up where we left off."""
    try:
        _store.save(session)
    except OSError:
        # Exit is not a good time to crash; silent-drop is fine.
        pass


def _transcript_markdown(session: InteractiveSession) -> str:
    lines = [
        f"# Lyra session transcript",
        "",
        f"- repo: `{session.repo_root}`",
        f"- model: `{session.model}`",
        f"- mode: `{session.mode}`",
        f"- turns: {session.turn}",
        f"- cost: ${session.cost_usd:.4f}",
        f"- tokens: {session.tokens_used:,}",
        "",
        "## Input history",
        "",
    ]
    for i, entry in enumerate(session.history, 1):
        lines.append(f"{i}. `{entry}`")
    return "\n".join(lines) + "\n"


def _handoff_markdown(session: InteractiveSession) -> str:
    pending = session.pending_task or "(none)"
    return (
        "# Handoff summary\n\n"
        f"- **Repo**: `{session.repo_root}`\n"
        f"- **Model**: `{session.model}`\n"
        f"- **Mode**: `{session.mode}`\n"
        f"- **Turns**: {session.turn}\n"
        f"- **Pending task**: {pending}\n\n"
        "## What happened\n\n"
        "- (fill in once v1 Phase 5 verifier writes the post-turn summary)\n\n"
        "## Test plan\n\n"
        "- [ ] Run `lyra evals --corpus golden --drift-gate 0.0`\n"
        "- [ ] Verify `lyra retro` has no P0 safety flags\n"
    )


def _prompt_fragments(
    session: InteractiveSession,
) -> FormattedText:
    """Two-column prompt: coloured mode badge + skin's prompt glyph.

    Deep-think adds a 🧠-less ``●`` dot so the user sees when Alt-T is on.
    The trailing glyph follows the active skin's ``branding.prompt_symbol``
    so /theme aurora/claude/hermes... actually shows up at the prompt.
    """
    skin = _themes.get_active_skin()
    accent = skin.color("accent", "#00E5FF")
    warning = skin.color("warning", "#FFC857")
    danger = skin.color("danger", "#FF2D95")
    secondary = skin.color("secondary", "#7C4DFF")
    dim = skin.color("dim", "#6B7280")
    from . import glyphs as _glyphs

    glyph = skin.brand("prompt_symbol", _glyphs.PROMPT)
    colour = {
        "plan": accent,
        "build": warning,
        "run": danger,
        "explore": accent,
        "retro": secondary,
    }.get(session.mode, warning)
    fragments = [
        ("", "\n"),
        (f"bold fg:{colour}", f" {display_mode(session.mode)}"),
    ]
    if session.deep_think:
        fragments.append((f"bold fg:{danger}", " ●"))
    fragments.append((f"fg:{dim}", f"  {glyph}  "))
    return FormattedText(fragments)


def _prompt_continuation(
    width: int, line_number: int, is_soft_wrap: bool
) -> FormattedText:
    """Visual continuation marker for multiline input.

    Uses the active skin's ``dim`` token so multiline prompts blend with
    the rest of the chrome (white-on-aurora vs muted-on-mono, etc).
    """
    glyph = "· "
    dim = _themes.get_active_skin().color("dim", "#6B7280")
    return FormattedText([(f"fg:{dim}", glyph.rjust(width))])


def _prompt_style() -> Style:
    """prompt_toolkit Style dict — ghost text, completion menu, search.

    Centralised here so every visual token used by prompt_toolkit itself
    (as opposed to Rich renderables) can be re-skinned in one place.
    The ghost-text class (``auto-suggestion``) is the new big one — it
    previously rendered as default-grey which looked wrong on every
    non-aurora skin; pulling from the skin's ``dim`` token matches the
    continuation marker and status-bar separators.
    """
    skin = _themes.get_active_skin()
    dim = skin.color("dim", "#6B7280")
    accent = skin.color("accent", "#00E5FF")
    secondary = skin.color("secondary", "#7C4DFF")
    menu_bg = skin.color("completion_menu_bg", "#0D0D14")
    menu_current_bg = skin.color("completion_menu_current_bg", "#1F1F2E")
    return Style.from_dict(
        {
            # Ghost-text suggestion (the "auto-suggest" in fish / Claude Code).
            "auto-suggestion": f"{dim} italic",
            # Completion menu — aligns the dropdown with the status bar.
            "completion-menu": f"bg:{menu_bg} {dim}",
            "completion-menu.completion.current": (
                f"bg:{menu_current_bg} bold {accent}"
            ),
            "completion-menu.completion": f"bg:{menu_bg} {dim}",
            "completion-menu.meta.completion": f"bg:{menu_bg} {dim} italic",
            "completion-menu.meta.completion.current": (
                f"bg:{menu_current_bg} {dim} italic"
            ),
            # Reverse / incremental history search prompt.
            "search": f"bg:{menu_bg} {accent}",
            "search.current": f"bg:{menu_current_bg} bold {accent}",
            # Scrollbar — keeps the dropdown navigable on narrow panels.
            "scrollbar.background": f"bg:{menu_bg}",
            "scrollbar.button": f"bg:{secondary}",
        }
    )


def _bottom_toolbar(session: InteractiveSession) -> HTML:
    """Compact, segmented status bar rendered via prompt_toolkit HTML.

    Shows the running-session facts on the left and the key-binding
    hint strip on the right. prompt_toolkit auto-truncates if the
    terminal is narrower than the line; we still try to keep it short
    on purpose so it doesn't steal focus from the prompt.

    Colours follow the **active skin** (``themes.get_active_skin()``)
    so ``/theme hermes`` actually re-skins the bar in real time —
    previously the hex codes were hard-coded against the ``aurora``
    palette, which made every other skin feel half-applied.
    """
    skin = _themes.get_active_skin()
    accent = skin.color("accent", "#00E5FF")
    secondary = skin.color("secondary", "#7C4DFF")
    success = skin.color("success", "#7CFFB2")
    danger = skin.color("danger", "#FF2D95")
    warning = skin.color("warning", "#FFC857")
    error = skin.color("error", "#FF5370")
    text = skin.color("status_bar_text", "#A1A7B3")
    sep = skin.color("status_bar_dim", "#3E4048")

    repo_label = session.repo_root.name or str(session.repo_root)
    # Mode colour keyed off the *short display label* so the v3.6
    # canonical IDs (``edit_automatically`` etc.) actually resolve
    # rather than always falling through to ``warning``.
    mode_short = display_mode(session.mode)
    mode_colour = {
        "agent": warning,
        "plan":  accent,
        "ask":   secondary,
        "auto":  success,
        # Pre-v3.6 names — preserved for legacy snapshots / themes.
        "build":   warning,
        "run":     danger,
        "explore": accent,
        "retro":   secondary,
    }.get(mode_short, warning)

    # Tighter separator — 7 chars (`   │   `) per gap × 6 gaps wasted
    # ~24 cols on every render and pushed the keybind hint strip off
    # narrow terminals (the user's screenshot showed ``skin au`` cut
    # off mid-word). 3 chars (` │ `) is enough visual separation.
    bar = f"<style fg='{sep}'> │ </style>"

    deep_badge = (
        f"{bar}<style fg='{text}'>deep </style>"
        f"<style fg='{danger}'><b>on</b></style>"
        if session.deep_think
        else ""
    )
    budget_badge = (
        f"{bar}<style fg='{text}'>cap </style>"
        f"<style fg='{warning}'><b>${session.budget_cap_usd:.2f}</b></style>"
        if session.budget_cap_usd is not None
        else ""
    )
    # Skin badge only when the user has switched off the default. Saves
    # a segment on every line in the common case while still surfacing
    # the active theme when the user is exploring skins.
    skin_badge = (
        f"{bar}<style fg='{text}'>skin </style>"
        f"<style fg='{accent}'>{_xml_escape(skin.name)}</style>"
        if skin.name not in ("aurora", "")
        else ""
    )

    # Permission mode badge — shown only when non-default (yolo/strict).
    perm_badge = {
        "yolo": (
            f"{bar}<style fg='{danger}'><b>⏵⏵</b></style>"
            f"<style fg='{danger}'> bypass permissions on</style>"
        ),
        "strict": (
            f"{bar}<style fg='{warning}'><b>🔒</b></style>"
            f"<style fg='{warning}'> strict</style>"
        ),
    }.get(session.permission_mode, "")

    # Background task count + "esc to interrupt" from shared StatusSource.
    _ss = getattr(session, "status_source", None)
    _bg = _ss.bg_task_count if _ss is not None else 0
    bg_badge = ""
    interrupt_badge = ""
    if _bg > 0:
        _label = "task" if _bg == 1 else "tasks"
        bg_badge = (
            f"{bar}<style fg='{accent}'><b>⏵⏵</b></style>"
            f"<style fg='{text}'> {_bg} background {_label}</style>"
        )
        interrupt_badge = f"{bar}<style fg='{text}'>esc to interrupt</style>"

    left = (
        f"<style fg='{accent}'> ◆ </style>"
        f"<style fg='{text}'>repo </style>"
        f"<style fg='ansiwhite'>{_xml_escape(repo_label)}</style>"
        f"{bar}<style fg='{text}'>mode </style>"
        f"<style fg='{mode_colour}'><b>{_xml_escape(mode_short)}</b></style>"
        f"{bar}<style fg='{text}'>model </style>"
        f"<style fg='{success}'><b>{_xml_escape(_resolve_banner_model(session.model))}</b></style>"
        f"{bar}<style fg='{text}'>turn </style>"
        f"<style fg='{accent}'>{session.turn}</style>"
        f"{bar}<style fg='{text}'>tok </style>"
        f"<style fg='ansiwhite'>{session.tokens_used:,}</style>"
        f"{bar}<style fg='{text}'>cost </style>"
        f"<style fg='ansiwhite'>${session.cost_usd:.4f}</style>"
        + deep_badge
        + budget_badge
        + skin_badge
        + perm_badge
        + bg_badge
        + interrupt_badge
    )
    # Compact keybind strip — same glyphs, single-space separator so the
    # full hint row fits beside the status segments on an 80-col panel.
    # Terminal-width-adaptive: on narrow terminals drop the right strip
    # entirely so the left status line ("turn N · tok N · cost $") isn't
    # truncated mid-word. Users can /help for the full keybind list.
    cols = _terminal_columns_safe()
    if cols >= 140:
        right = (
            f"<style fg='{accent}'><b>/</b></style><style fg='{text}'>cmd</style>"
            f" <style fg='{danger}'><b>!</b></style><style fg='{text}'>sh</style>"
            f" <style fg='{success}'><b>@</b></style><style fg='{text}'>file</style>"
            f" <style fg='{success}'><b>⇥</b></style><style fg='{text}'>mode</style>"
            f" <style fg='{accent}'><b>⌥P</b></style><style fg='{text}'>plan</style>"
            f" <style fg='{secondary}'><b>⌥R</b></style><style fg='{text}'>review</style>"
            f" <style fg='{danger}'><b>⌥T</b></style><style fg='{text}'>deep</style>"
            f" <style fg='{secondary}'><b>^G</b></style><style fg='{text}'>edit</style>"
            f" <style fg='{warning}'><b>^L</b></style><style fg='{text}'>clr</style>"
            f" <style fg='{error}'><b>^D</b></style><style fg='{text}'>exit</style>"
        )
        return HTML(f"{left}{bar}{right}")
    if cols >= 100:
        # Mid-width: the four most-used hints only.
        right = (
            f"<style fg='{accent}'><b>/</b></style><style fg='{text}'>cmd</style>"
            f" <style fg='{success}'><b>⇥</b></style><style fg='{text}'>mode</style>"
            f" <style fg='{warning}'><b>^L</b></style><style fg='{text}'>clr</style>"
            f" <style fg='{error}'><b>^D</b></style><style fg='{text}'>exit</style>"
        )
        return HTML(f"{left}{bar}{right}")
    # Narrow terminal: status segments only. /help has the keybinds.
    return HTML(left)


def _build_key_bindings(
    session: InteractiveSession, console: Console, hir: HIRLogger
) -> KeyBindings:  # pragma: no cover — keybindings only fire in a real TTY
    """Key bindings that mirror Claude Code / opencode / Hermes muscle memory."""
    kb = KeyBindings()

    @kb.add("/")
    def _(event: Any) -> None:
        """Typing `/` opens the slash-command palette *immediately*.

        Claude-Code and opencode open their command palette on the very
        first keystroke, not on the next ``complete_while_typing`` tick.
        We replicate that by intercepting ``/``, inserting the character
        ourselves, then calling ``start_completion`` to pop the dropdown
        on this frame. When the buffer already has content (e.g. the
        user is typing a URL or a path like ``foo/bar``) we fall through
        to the default handler so ``/`` behaves like a normal character.
        """
        buf = event.app.current_buffer
        if buf.text:
            buf.insert_text("/")
            return
        buf.insert_text("/")
        buf.start_completion(select_first=False)

    @kb.add("@")
    def _(event: Any) -> None:
        """Typing ``@`` opens the in-repo file picker on a word boundary.

        Trigger when ``@`` would start a new word — buffer empty, or
        the previous char (immediately before the cursor) is whitespace
        — so ``hello @packages/`` mid-prompt pops the picker. Skip when
        the previous char is part of a word (``user@host``, ``a@b.com``)
        so legitimate email/path tokens keep working without ambushing
        the user with a dropdown over their own text.
        """
        buf = event.app.current_buffer
        text_before = buf.document.text_before_cursor
        prev = text_before[-1] if text_before else ""
        if prev and not prev.isspace():
            buf.insert_text("@")
            return
        buf.insert_text("@")
        buf.start_completion(select_first=False)

    @kb.add("#")
    def _(event: Any) -> None:
        """Typing ``#`` opens the skill-pack picker on a word boundary.

        Mirrors ``/`` and ``@``: trigger when ``#`` would start a new
        token (buffer empty, or previous char is whitespace) so
        ``find me #python-testing`` mid-prompt pops the picker. Skip
        when the previous char is part of a word so issue refs like
        ``GH#123`` and CSS-style ``id#name`` selectors stay literal.
        """
        buf = event.app.current_buffer
        text_before = buf.document.text_before_cursor
        prev = text_before[-1] if text_before else ""
        if prev and not prev.isspace():
            buf.insert_text("#")
            return
        buf.insert_text("#")
        buf.start_completion(select_first=False)

    @kb.add("backspace")
    def _(event: Any) -> None:
        """Keep the /, @, # palette open after backspace.

        prompt_toolkit closes the completion menu by default when a
        character is deleted. For our prefix-driven palettes that's
        wrong — the user is still browsing /mode ↔ /model ↔ /models
        and needs the dropdown to stay live as the stem shrinks.
        """
        buf = event.app.current_buffer
        buf.delete_before_cursor(1)
        if buf.text and buf.text[0] in ("/", "@", "#"):
            buf.start_completion(select_first=False)

    @kb.add("c-l")
    def _(event: Any) -> None:
        """Clear screen + reprint banner, keep the buffer intact."""
        app = get_app()
        app.renderer.clear()
        _print_banner(
            repo_root=session.repo_root,
            model=session.model,
            mode=session.mode,
            plain=False,
        )
        app.invalidate()

    def _cycle_mode(step: int) -> None:
        before = session.mode
        if step == +1:
            # Delegate the canonical Wave-C order to the tested helper so
            # the TTY can never drift away from the parity-matrix docs.
            _keybinds.cycle_mode(session)
        else:
            try:
                i = _MODE_CYCLE.index(session.mode)
            except ValueError:
                i = 0
            session.mode = _MODE_CYCLE[(i + step) % len(_MODE_CYCLE)]
        hir.on_mode_change(
            turn=session.turn, from_mode=before, to_mode=session.mode
        )
        get_app().invalidate()

    @kb.add("s-tab")
    def _(event: Any) -> None:
        """Cycle modes in reverse."""
        _cycle_mode(-1)

    @kb.add("tab")
    def _(event: Any) -> None:
        """Cycle modes forward — only when the buffer is empty.

        With a non-empty buffer Tab should complete, not switch modes.
        """
        buf = event.app.current_buffer
        if buf.text.strip():
            buf.complete_next()
            return
        _cycle_mode(+1)

    @kb.add("c-r")
    def _(event: Any) -> None:
        """Reverse history search (prompt_toolkit built-in)."""
        event.app.current_buffer.start_history_lines_completion()

    def _editor_handler(event: Any) -> None:
        """Open $EDITOR for the current buffer, replace it with the edit."""
        buf = event.app.current_buffer
        text = _open_in_editor(buf.text)
        if text is not None:
            buf.text = text
            buf.cursor_position = len(text)

    @kb.add("c-g")
    def _(event: Any) -> None:
        """Ctrl-G — open $EDITOR for the current buffer."""
        _editor_handler(event)

    @kb.add("c-x", "c-e")
    def _(event: Any) -> None:
        """Ctrl-X Ctrl-E — bash/zsh/aider canonical editor binding.

        Same behaviour as Ctrl-G but uses the muscle memory most shell
        users already have. Both are kept so neither group has to relearn.
        """
        _editor_handler(event)

    @kb.add("c-e")
    def _(event: Any) -> None:
        """Ctrl-E — accept the ghost-text auto-suggestion in full.

        Mirrors Claude Code and fish shell: the most-likely continuation
        is rendered in dim grey at the end of your buffer; Ctrl-E snaps
        it into place. Falls through to end-of-line when there's no
        suggestion so the classic Emacs binding still works when you're
        not in suggest-land.
        """
        buf = event.app.current_buffer
        suggestion = buf.suggestion
        if suggestion and suggestion.text:
            buf.insert_text(suggestion.text)
            return
        buf.cursor_position = len(buf.text)

    @kb.add("right")
    def _(event: Any) -> None:
        """→ at end-of-line — accept the suggestion; otherwise move right.

        Feels like fish: if the cursor is at the end of the buffer and
        there's a ghost-text preview, the arrow swallows the suggestion
        into the real text. Otherwise it's the plain cursor-right you'd
        expect from Emacs mode.
        """
        buf = event.app.current_buffer
        suggestion = buf.suggestion
        if (
            suggestion
            and suggestion.text
            and buf.cursor_position == len(buf.text)
        ):
            buf.insert_text(suggestion.text)
            return
        buf.cursor_right()

    @kb.add("escape", "f")
    def _(event: Any) -> None:
        """Alt-F — accept only the next word of the suggestion (fish-style).

        Useful when the suggestion is long (``/mode plan → /approve``-ish)
        and you only want the first token. Inserts up to — but not
        including — the first whitespace in the suggestion.
        """
        buf = event.app.current_buffer
        suggestion = buf.suggestion
        if not (suggestion and suggestion.text):
            return
        text = suggestion.text
        # Find the first whitespace run; if none, accept the full text.
        cut = len(text)
        for i, ch in enumerate(text):
            if ch.isspace():
                cut = i + 1  # include the space so a second Alt-F advances
                break
        buf.insert_text(text[:cut])

    @kb.add("c-t")
    def _(event: Any) -> None:
        """Toggle the in-session task panel flag."""
        # Delegate to the tested keybind helper so CI behaviour and TTY
        # behaviour can never diverge.
        _keybinds.toggle_task_panel(session)
        get_app().invalidate()

    @kb.add("escape", "v")
    def _(event: Any) -> None:
        """Alt-V → toggle verbose tool-call output (was Ctrl-O before
        Ctrl-O was repurposed to expand the last tool output)."""
        _keybinds.toggle_verbose_tool_output(session)
        get_app().invalidate()

    @kb.add("c-j")
    def _(event: Any) -> None:
        """Ctrl-J inserts a newline (multi-line input)."""
        event.app.current_buffer.insert_text("\n")
        event.app.current_buffer.multiline = True  # type: ignore[attr-defined]

    @kb.add("escape", "enter")
    def _(event: Any) -> None:
        """Alt-Enter / Esc-Enter inserts a newline."""
        event.app.current_buffer.insert_text("\n")

    @kb.add("escape", "t")
    def _(event: Any) -> None:
        """Alt-T toggles deep-think."""
        _keybinds.toggle_deep_think(session)
        console.print(
            Text(
                f" → deep-think {'on' if session.deep_think else 'off'}",
                style="#FF2D95" if session.deep_think else "#6B7280",
            )
        )
        get_app().invalidate()

    @kb.add("escape", "m")
    def _(event: Any) -> None:
        """Alt-M cycles the permission mode (normal → strict → yolo)."""
        toast = _keybinds.toggle_permission_mode(session)
        console.print(
            Text(
                f" → {toast}",
                style="#FF2D95" if session.permission_mode == "yolo" else "#6B7280",
            )
        )
        get_app().invalidate()

    def _jump_mode(target: str) -> None:
        """Snap directly to ``target`` mode (Hermes / Claude-Code style)."""
        toast = _keybinds.set_mode(session, target)
        console.print(Text(f" → {toast}", style="#7C4DFF"))
        get_app().invalidate()

    @kb.add("escape", "p")
    def _(event: Any) -> None:
        """Alt-P → jump straight to plan_mode (read-only design pass)."""
        _jump_mode("plan_mode")

    @kb.add("escape", "e")
    def _(event: Any) -> None:
        """Alt-E → jump straight to edit_automatically (default)."""
        _jump_mode("edit_automatically")

    @kb.add("escape", "a")
    def _(event: Any) -> None:
        """Alt-A → jump straight to ask_before_edits."""
        _jump_mode("ask_before_edits")

    @kb.add("escape", "u")
    def _(event: Any) -> None:
        """Alt-U → jump straight to auto_mode (per-turn router)."""
        _jump_mode("auto_mode")

    @kb.add("escape", "l")
    def _(event: Any) -> None:
        """Alt-L → list configured model providers (former Alt-P)."""
        result = session.dispatch("/models")
        _render_result(console, result)

    @kb.add("escape", "r")
    def _(event: Any) -> None:
        """Alt-R → run /review on the most recent code-touching turn."""
        result = session.dispatch("/review")
        _render_result(console, result)

    @kb.add("escape", "s")
    def _(event: Any) -> None:
        """Alt-S → open the /spawn subagent picker."""
        result = session.dispatch("/spawn")
        _render_result(console, result)

    @kb.add("escape", "c")
    def _(event: Any) -> None:
        """Alt-C → /compact the conversation context."""
        result = session.dispatch("/compact")
        _render_result(console, result)

    @kb.add("escape", "i")
    def _(event: Any) -> None:
        """Alt-I → open the /skills picker (Claude-Code style)."""
        result = session.dispatch("/skills")
        _render_result(console, result)

    @kb.add("escape", "g")
    def _(event: Any) -> None:
        """Alt-G → open the /agents picker (Claude-Code style)."""
        result = session.dispatch("/agents")
        _render_result(console, result)

    @kb.add("c-o")
    def _(event: Any) -> None:
        """Ctrl-O → expand the last collapsed tool output.

        The chat-tool render stashes the full output on
        ``session._last_tool_output`` whenever a tool finishes. This
        dumps it to scrollback so the user can read past the truncated
        ``… +N lines`` footer.
        """
        full = getattr(session, "_last_tool_output", None)
        if not full:
            console.print(Text(" → no captured tool output to expand", style="#6B7280"))
            return
        console.rule("[dim]expanded tool output (Ctrl+O)[/]", style="#3E4048")
        console.print(full)
        console.rule(style="#3E4048")

    @kb.add("escape", "escape")
    def _(event: Any) -> None:
        """Esc Esc = persistent rewind (truncates the on-disk JSONL)."""
        # Use the tested helper so a single rewind always pops one turn
        # AND shrinks the persisted log when ``sessions_root`` is set —
        # the previous ``/rewind`` slash could no-op silently when the
        # session was opened from disk.
        toast = _keybinds.rewind_one_persisted(session)
        console.print(Text(f" → {toast}", style="#6B7280"))
        get_app().invalidate()

    @kb.add("c-f")
    def _(event: Any) -> None:
        """Ctrl-F = re-focus the foreground subagent (Wave-D Task 2)."""
        toast = _keybinds.focus_foreground_subagent(session)
        console.print(Text(f" → {toast}", style="#6B7280"))

    @kb.add("escape", "k")
    def _(event: Any) -> None:
        """Esc-K — wipe the input buffer.

        Distinct from Ctrl-L (which redraws the screen) and Esc Esc
        (which rewinds a turn). Esc-K just empties what you've typed
        so you can start a message over without losing chat history.
        """
        buf = event.app.current_buffer
        buf.text = ""
        buf.cursor_position = 0

    @kb.add("escape", "?")
    def _(event: Any) -> None:
        """Alt-? — pop the keybindings cheatsheet overlay.

        Mirrors Claude Code's discoverability story: new users hit a
        single key and see every chord that's wired up, with one-line
        descriptions. Rendered as a Rich table over the Console (the
        prompt is still active behind it).
        """
        show_keybindings_help(console)
        get_app().invalidate()

    @kb.add("c-n")
    def _(event: Any) -> None:
        """Ctrl-N — start a new chat (clear messages, keep mode/model).

        Wipes the in-memory message log, input history, turn counter,
        and per-turn snapshots. Preserves: mode, model, repo_root,
        MCP servers, permission settings, deep-think flag. The on-disk
        JSONL session file (if any) is left intact — use `/fork` if
        you want to branch instead of starting fresh.
        """
        toast = _keybinds.new_chat(session)
        console.print(Text(f" → {toast}", style="#7C4DFF"))
        get_app().invalidate()
        get_app().invalidate()

    return kb


def _open_in_editor(initial: str) -> str | None:
    """Open $EDITOR on a tempfile. Returns the stripped-trailing-newline text, or None on failure."""
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".oc.md", delete=False, encoding="utf-8"
        ) as fh:
            if initial:
                fh.write(initial)
            tmp_path = Path(fh.name)
    except OSError:
        return None
    try:
        subprocess.call([editor, str(tmp_path)])  # noqa: S603 — user editor
        text = tmp_path.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return None
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass
    return text.rstrip("\n")


_AGENT_VERB_BY_MODE: dict[str, str] = {
    # v3.2.0 Claude-Code 4-mode taxonomy.
    "agent": "implementing",
    "plan": "planning",
    "debug": "investigating",
    "ask": "tracing",
    # Legacy v1.x / v2.x fall-throughs — kept so a third-party skin
    # or saved transcript that hard-codes the old mode names still
    # gets a sensible verb instead of "thinking".
    "build": "implementing",
    "run": "executing",
    "explore": "tracing",
    "retro": "reflecting",
}

# Anything below this elapsed time stays silent — slash command stubs
# return in <1 ms today and a "agent thought for 0.0s" line would be
# pure noise. Once a real LLM is wired in, turns will trivially exceed
# the threshold and the completion line will start showing up.
_AGENT_COMPLETION_THRESHOLD_SEC: float = 3.0


def agent_verb_for_mode(mode: str, skin: _themes.Skin | None = None) -> str:
    """Pick the verb the spinner shows while the agent is thinking.

    Strategy: mode → "planning"/"implementing"/etc. If the active skin
    declares a custom ``verbs`` list we honour the mode-mapped verb
    only when it's actually in that list (so a kawaii skin saying
    ``["pondering", "musing"]`` doesn't get overridden by ``planning``).
    Otherwise we fall back to the first declared verb, then to
    ``"thinking"`` as the universal default.
    """
    desired = _AGENT_VERB_BY_MODE.get(mode, "thinking")
    if skin is None:
        skin = _themes.get_active_skin()
    declared = [v for v in (skin.spinner.get("verbs") or []) if isinstance(v, str)]
    if declared and desired not in declared:
        return declared[0]
    return desired


def _run_agent_turn(
    console: Console,
    session: InteractiveSession,
    line: str,
) -> CommandResult:
    """Wrap a plain-text turn with the skin-aware agent spinner.

    Today the underlying handler is a one-line stub (handlers in
    :mod:`.session` ship the ``[plan] recorded ...`` placeholders); the
    spinner blinks for ~1 ms in that case and we suppress the trailing
    completion line via :data:`_AGENT_COMPLETION_THRESHOLD_SEC`. Once
    Phase 14's CodeAct plugin lands, the same wrapper will render the
    "thinking…" animation + final duration for every real LLM turn
    without the call sites changing.

    Failure path: if the handler raises, we still emit a red ✗
    completion line so the user sees the dispatch *attempted* — then
    re-raise so the outer loop's existing exception handling kicks in.
    """
    skin = _themes.get_active_skin()
    verb = agent_verb_for_mode(session.mode, skin)
    started = time.monotonic()
    # Skip the outer ``Spinner`` for plain (non-slash) turns — the chat
    # handler downstream paints its own visible output (a streaming
    # ``rich.live.Live`` panel, tool-call cards via ``console.print``,
    # or a final Markdown panel). Running both at once meant the
    # spinner's ``\r``-rewinds raced with Rich's cursor positioning,
    # leaving truncated panel borders ("╭─ agent ───") stranded above
    # the real panel and overwriting tool-call lines with spinner
    # frames. Slash commands keep the spinner because most return
    # silently in <1ms and the user wants *some* feedback that the
    # keystroke registered.
    use_spinner = line.lstrip().startswith("/")
    try:
        if use_spinner:
            with Spinner(verb):
                result = session.dispatch(line)
        else:
            result = session.dispatch(line)
    except Exception:
        duration = time.monotonic() - started
        console.print(
            _out.tool_completion_renderable(
                "agent",
                verb,
                duration_sec=duration,
                success=False,
                suffix="[error]",
            )
        )
        raise
    duration = time.monotonic() - started
    if duration >= _AGENT_COMPLETION_THRESHOLD_SEC:
        console.print(
            _out.tool_completion_renderable(
                "agent",
                verb,
                duration_sec=duration,
                success=True,
            )
        )
    return result


def _run_bash(
    console: Console,
    command: str,
    *,
    session: InteractiveSession,
    hir: HIRLogger,
) -> None:  # pragma: no cover — subprocess
    """Execute ``!cmd`` via the user's shell and render the result panel."""
    if not command:
        console.print(
            Text(" (empty bash command)", style="#6B7280 italic")
        )
        return
    try:
        # shell=False + shlex.split keeps it tool-friendly; users who
        # want pipelines can pass them through $SHELL explicitly.
        tokens = shlex.split(command)
    except ValueError as exc:
        console.print(
            Text(f" (bad shell syntax: {exc})", style="#FF5370")
        )
        return

    # Pull skin config so /theme actually re-skins the wait animation,
    # tool prefix and emoji. Falling back to defaults keeps the flow
    # alive if the skin's blocks are empty.
    skin = _themes.get_active_skin()
    prefix = skin.tool_prefix or "┊"
    bash_emoji = skin.tool_emojis.get("bash", "⚡")

    short_args = command if len(command) <= 70 else command[:67] + "…"

    # Tool preview line — same shape hermes uses (``┊ ⚡ <command>``).
    console.print(
        _out.tool_preview_renderable(
            "bash",
            short_args,
            prefix=prefix,
            accent=skin.color("accent", "#00E5FF"),
            emoji=bash_emoji,
        )
    )

    spinner_message = short_args
    started = time.monotonic()
    try:
        with Spinner(spinner_message):
            completed = subprocess.run(  # noqa: S603 — user-supplied by design
                tokens,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
    except FileNotFoundError:
        console.print(
            Text(
                f" (command not found: {tokens[0]})",
                style="#FF5370",
            )
        )
        return
    except subprocess.TimeoutExpired:
        console.print(
            Text(
                " (bash command timed out after 60s)", style="#FFC857"
            )
        )
        return
    duration = time.monotonic() - started

    failed, suffix = _out.detect_tool_failure(
        "bash",
        exit_code=completed.returncode,
        output=(completed.stderr or "") + "\n" + (completed.stdout or ""),
    )
    console.print(
        _out.tool_completion_renderable(
            "bash",
            short_args,
            duration_sec=duration,
            success=not failed,
            suffix=suffix,
        )
    )

    console.print(
        _out.bash_output_renderable(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_sec=duration,
        )
    )
    hir.on_bash(
        turn=session.turn,
        command=command,
        exit_code=completed.returncode,
        stdout_bytes=len(completed.stdout.encode("utf-8")),
        stderr_bytes=len(completed.stderr.encode("utf-8")),
    )


def _print_goodbye(
    console: Console, session: InteractiveSession
) -> None:  # pragma: no cover — only called on real TTY exit
    console.print()
    console.print(
        _out.goodbye_renderable(
            turns=session.turn,
            tokens=session.tokens_used,
            cost_usd=session.cost_usd,
        )
    )


def _xml_escape(s: str) -> str:
    """Minimal escaping for prompt_toolkit HTML."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
# Plain path (non-TTY / prompt_toolkit missing)
# ---------------------------------------------------------------------------


def _run_plain(
    session: InteractiveSession, console: Console, hir: HIRLogger
) -> int:
    while True:
        prompt_text = Text.assemble(
            ("\n" + display_mode(session.mode), "cyan bold"),
            (" ", ""),
            ("\u203a", "magenta"),
            (" ", ""),
        )
        console.print(prompt_text, end="")
        try:
            line = input()
        except EOFError:
            _save_on_exit(session)
            # Skin-aware farewell — falls back to the historical "bye."
            # for aurora since its branding["goodbye"] is the legacy
            # string. Non-TTY callers (CI smoke tests) still see a
            # short, single-line exit so log diffs stay tiny.
            farewell = _themes.get_active_skin().brand("goodbye", "bye.")
            console.print(f"\n{farewell}")
            return 0
        except KeyboardInterrupt:
            console.print("\naborted.")
            return 0

        stripped = line.strip()
        if stripped.startswith("!"):
            # Non-TTY bash still useful for piped smoke tests; no logger
            # panel, just raw stdout so CI output stays predictable.
            cmd = stripped[1:].strip()
            if cmd:
                try:
                    completed = subprocess.run(  # noqa: S603
                        shlex.split(cmd),
                        capture_output=True,
                        text=True,
                        timeout=60,
                        check=False,
                    )
                except (FileNotFoundError, ValueError) as exc:
                    console.print(f"(bash failed: {exc})")
                    continue
                if completed.stdout:
                    console.print(completed.stdout.rstrip("\n"))
                if completed.stderr:
                    console.print(completed.stderr.rstrip("\n"))
            continue

        hir.on_prompt(turn=session.turn, mode=session.mode, line=stripped)
        if stripped.startswith("/"):
            result = session.dispatch(line)
        else:
            # Same agent-turn wrapper as the prompt_toolkit path — the
            # spinner is auto-disabled in non-TTY mode, so this is a
            # no-op visually but preserves the timing/error-handling
            # contract for headless runs and CI smoke tests.
            result = _run_agent_turn(console, session, line)
        _render_result(console, result)

        if stripped.startswith("/"):
            parts = stripped[1:].split(maxsplit=1)
            name = parts[0].lower() if parts else ""
            args = parts[1] if len(parts) > 1 else ""
            hir.on_slash(turn=session.turn, name=name, args=args)

        if result.should_exit:
            _save_on_exit(session)
            return 0
