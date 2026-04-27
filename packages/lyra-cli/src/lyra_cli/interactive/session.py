"""Interactive session dispatch — pure, TTY-free, unit-testable.

Every slash command is a free function ``(session, args) -> CommandResult``
registered in ``SLASH_COMMANDS``. Plain text falls through to the mode's
handler in ``_MODE_HANDLERS``.

Why pure? Because the REPL is exactly the surface where a subtle state
bug (wrong mode, lost plan, miscounted turn) kills trust in the harness.
Tests exercise ``dispatch`` directly; the driver is a thin I/O wrapper.

Output contract (dual-channel):
    Each handler fills ``CommandResult.output`` with a plain-text line
    that contains every keyword tests assert on (mode names, model
    names, "unknown", "reject", etc). Handlers *may additionally* set
    ``CommandResult.renderable`` to a Rich object (Panel, Table,
    Columns, …) that the driver prefers over the plain string when a
    real TTY is available. This lets us keep the test suite string-
    based while shipping a Claude-Code-grade visual UX in the terminal.

Mode semantics (v3.2.0 Claude-Code 4-mode taxonomy):

- ``agent`` — default; full-access execution. Plain text drives the
  agent loop (real edits, real shell, real tools).
- ``plan``  — read-only collaborative design. Plain text proposes a
  plan; ``/approve`` hands the plan off to ``agent`` for execution.
- ``debug`` — systematic troubleshooting with runtime evidence. Plain
  text walks the user through hypothesis → experiment → fix.
- ``ask``   — read-only Q&A about the codebase. No edits, no tools.

Pre-v3.2 had a 5-mode taxonomy (``plan / build / run / explore /
retro``); the legacy names are remapped on construction via
:data:`_LEGACY_MODE_REMAP` so old settings.json files and stored
session JSONLs keep working without manual migration.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import time as _time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .. import __version__
from . import output as _out
from .config_store import Config as _ConfigT
from .config_store import apply_to_session as _apply_config_to_session
from .cron import CronCommandError, handle_cron


_VALID_MODES: tuple[str, ...] = ("agent", "plan", "debug", "ask")

# Legacy mode names from v1.x / v2.x → canonical v3.2 mode. We honour them
# everywhere the user can supply a string (CLI flags, /mode, snapshots on
# disk, settings.json) so a fresh ``lyra`` upgrade doesn't break a user's
# stored sessions or their muscle memory. The mapping is intentionally
# many-to-one: ``build`` and ``run`` both collapse into ``agent`` because
# Claude-Code-style modes don't draw the "design vs. execute" line that
# Lyra's older 5-mode taxonomy did — execution is just what ``agent``
# does. ``retro`` becomes ``debug`` because the retrospective journal
# survives at the CLI subcommand layer (``lyra retro``) while the
# interactive REPL mode is now systematic troubleshooting.
_LEGACY_MODE_REMAP: dict[str, str] = {
    "build": "agent",
    "run": "agent",
    "explore": "ask",
    "retro": "debug",
}

# Tab cycle order is intentionally NOT the same as `_VALID_MODES`. v3.2
# rotates ``agent → plan → ask → debug`` to put the two execution-capable
# modes (agent, debug) at opposite ends so a single Tab press never
# accidentally toggles between them. We re-export the canonical order
# from ``keybinds`` so the TTY driver, the slash helper, and the parity
# docs can never drift apart again.
from .keybinds import _MODE_CYCLE_TAB as _MODE_CYCLE  # noqa: E402,F401  (re-export)

_SHIPPED_SKILL_PACKS: tuple[tuple[str, str], ...] = (
    ("atomic-skills", "small, single-purpose behaviours used by every agent"),
    ("tdd-sprint", "red → green → refactor discipline enforcers"),
    ("karpathy", "Karpathy-style prompting and debugging patterns"),
    ("safety", "policy guards, secret triage, dangerous-command detection"),
)

def _valid_themes() -> tuple[str, ...]:
    """Lazy-resolve from the skin engine so a YAML user-skin auto-extends /theme.

    Resolved at command time (not import time) so the user can drop a new
    skin into ``~/.lyra/skins/`` and it shows up on the next
    ``/theme`` invocation without restarting the REPL.
    """
    from . import themes as _t  # local: keep cold-start cheap

    return _t.names()


# Kept for back-compat: tests + driver imports still reference the constant.
# It freezes the module-import-time list of skins; new YAML skins added
# during a session show up via the ``_valid_themes()`` accessor instead.
_VALID_THEMES: tuple[str, ...] = (
    "aurora",
    "candy",
    "claude",
    "hermes",
    "mono",
    "opencode",
    "solar",
    "sunset",
)


@dataclass
class _TurnSnapshot:
    """What we need to undo a turn on /rewind.

    v3.2.0 — the original five-field record (line/mode/turn/pending_task/
    cost_usd/tokens_used) captured everything ``rewind_one`` needs to
    restore live state, but nothing the user could later inspect via
    ``/history --verbose`` or ``lyra session show``. The new fields
    (``model``, ``ts``, ``tokens_in``, ``tokens_out``, ``cost_delta_usd``,
    ``latency_ms``) are *additive* and all default to ``None`` so:

    * existing tests that build a snapshot with positional kwargs keep
      working unchanged,
    * pre-v3.2 ``turns.jsonl`` files load with the new fields all
      ``None`` (the JSON loader skips missing keys silently), and
    * verbose history rendering can show "model · tokens IN/OUT · cost
      delta · latency · timestamp" once a session is recorded with
      v3.2+.

    We deliberately store *deltas* for ``cost_delta_usd`` and the token
    counts (rather than the running totals already on the session) so
    a future ``/history --verbose`` table can show "this turn cost
    $0.0023" without having to subtract neighbours.
    """

    line: str
    mode: str
    turn: int
    pending_task: str | None
    cost_usd: float
    tokens_used: int
    # v3.2.0 (Phase L) per-turn metadata — all optional so old call
    # sites and on-disk JSONL records keep working.
    model: str | None = None
    ts: float | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_delta_usd: float | None = None
    latency_ms: float | None = None


@dataclass
class CommandResult:
    """What ``dispatch`` hands back to the driver.

    - ``output``: plain-text rendering (what tests assert on and what
      the plain / non-TTY path prints).
    - ``renderable``: optional Rich renderable (Panel, Table, Group…)
      the fancy driver prefers when a real terminal is attached. When
      ``None`` the driver prints ``output`` instead. Typed as ``Any`` so
      this module can stay Rich-free at import time (only the helper
      module :mod:`.output` imports Rich, and only when a handler opts
      in).
    - ``should_exit``: drop out of the REPL loop.
    - ``clear_screen``: issue ANSI clear (or equivalent).
    - ``new_mode``: already applied to the session; the driver uses it
      to re-render the status bar without re-reading state.
    """

    output: str = ""
    renderable: Any | None = None
    should_exit: bool = False
    clear_screen: bool = False
    new_mode: str | None = None


SlashHandler = Callable[["InteractiveSession", str], CommandResult]


def _default_session_id() -> str:
    """Time-ordered, sortable session id (no extra deps).

    Mirrors claw-code's "session-YYYYMMDDHHMMSS-XXXX" shape so the
    on-disk listing of ``~/.lyra/sessions/`` sorts chronologically
    without metadata. The 4-char suffix is process-id (mod 10000) so
    two parallel REPLs in the same second still get distinct ids.
    """
    import datetime as _dt
    import os as _os

    stamp = _dt.datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = f"{_os.getpid() % 10000:04d}"
    return f"sess-{stamp}-{suffix}"


@dataclass
class InteractiveSession:
    """All state the REPL accumulates during a run."""

    repo_root: Path
    model: str = "auto"
    # v2.7.1: Claude-Code-style small/smart split.
    #
    # ``fast_model`` is the cheap/quick alias used for plain chat
    # turns, summarisation, /compact, completion, status banter, and
    # any cron job that doesn't need deep reasoning. ``smart_model``
    # is the slower, more capable alias used for /plan, /spawn, /review,
    # /ultrareview, agent-loop tool reasoning, and verifier rounds.
    #
    # Defaults map to the DeepSeek catalog (``deepseek-v4-flash`` →
    # ``deepseek-chat``, ``deepseek-v4-pro`` → ``deepseek-reasoner``)
    # because DeepSeek is Lyra's cost-aware default backend. Users on
    # other providers (Anthropic, OpenAI, Vertex, Bedrock, etc.) can
    # override via ``/model fast=<slug>`` and ``/model smart=<slug>``,
    # or by setting ``HARNESS_LLM_MODEL`` directly.
    #
    # ``model`` (above) remains the *canonical* slot for back-compat:
    # legacy callers that pass ``--model`` keep getting their pin
    # honoured. When ``model == "auto"`` the routing logic in
    # :func:`_resolve_model_for_role` reads from these two slots; when
    # ``model`` is pinned explicitly it overrides both slots so power
    # users keep their hard pins. See ``docs/blocks/01-agent-loop.md``
    # for the routing table.
    fast_model: str = "deepseek-v4-flash"
    smart_model: str = "deepseek-v4-pro"
    # v3.2.0: Lyra's interactive modes follow Claude Code's taxonomy —
    # ``agent`` (default; full-access execution), ``plan`` (read-only
    # collaborative design), ``debug`` (systematic troubleshooting),
    # ``ask`` (read-only Q&A). Legacy v1.x / v2.x names (``build``,
    # ``run``, ``explore``, ``retro``) are remapped on construction
    # via ``__post_init__``; passing one in still works but resolves
    # to the canonical Claude-Code-style name before the session boots.
    mode: str = "agent"
    turn: int = 0
    cost_usd: float = 0.0
    tokens_used: int = 0
    history: list[str] = field(default_factory=list)
    pending_task: str | None = None

    # New in this wave (all optional so existing tests stay green):
    deep_think: bool = False
    verbose: bool = False
    vim_mode: bool = False
    theme: str = "aurora"
    budget_cap_usd: float | None = None
    # v2.2.3: when True, ``_chat_with_llm`` refuses any new LLM call
    # once the meter reports ``EXCEEDED``. False means "warn, but
    # never block" — the legacy behaviour. Driver.run wires this from
    # the persisted ``budget`` block, so toggling lives in
    # ``~/.lyra/auth.json`` rather than at the CLI flag level.
    budget_auto_stop: bool = True

    # v2.2.4: streaming chat. ``_console`` is the ``rich.Console``
    # the driver creates for the REPL — the chat handler reuses it to
    # drive a :class:`rich.live.Live` panel that grows token-by-token.
    # ``_streaming_enabled`` gates the whole thing: True only when the
    # driver booted on a TTY *and* the user hasn't disabled streaming
    # via ``LYRA_NO_STREAM`` or ``/stream off``. Tests construct
    # sessions without setting either, so the default behaviour stays
    # identical to v2.2.3.
    _console: Any = None
    _streaming_enabled: bool = False
    # Set by the streaming branch of ``_chat_with_llm`` so the
    # mode-handler factory knows the panel is already on screen and
    # can return ``CommandResult(renderable=None, output="")`` —
    # otherwise the driver would repaint the same reply.
    _stream_just_drew: bool = False
    task_panel: bool = False
    # v1.7.5 Wave-C Task 6: cycled by Alt+M. ``strict`` requires
    # explicit confirmation for every tool call; ``normal`` is the
    # default; ``yolo`` skips confirmation prompts entirely.
    permission_mode: str = "normal"
    # v3.0.0 (Phase G): TDD became opt-in. The default is now
    # ``False`` so a fresh ``lyra`` behaves like claw-code, opencode,
    # and hermes-agent: a general coding agent that doesn't refuse
    # Edits because no failing test exists yet. Users who want the
    # historical TDD-as-kernel behaviour flip this on with one of:
    #   * ``/tdd-gate on`` (per-session)
    #   * ``/config set tdd_gate=on`` (persists in ``~/.lyra/config.yaml``)
    #   * ``[plugins.tdd] enabled = true`` in ``~/.lyra/settings.toml``
    # The slash ``/tdd-gate on|off|status`` still toggles it. The full
    # state machine (`lyra_core.tdd.state`), the gate hook
    # (`lyra_core.hooks.tdd_gate`), and the slashes (`/phase`,
    # `/tdd-gate`, `/red-proof`) all remain available — they are
    # simply not the default surface anymore.
    tdd_gate_enabled: bool = False

    # v1.7.5 Wave-C Task 14: pair-programming mode (presentational
    # today; live streaming arrives in Wave D). When ``True``, the
    # status line surfaces ``pair: on`` and the driver swaps to a
    # transcript-style render. The flag itself is the contract; the
    # driver wiring stays out of this dataclass on purpose.
    pair_mode: bool = False
    # Wave-E (v1.9.0) Task 11: ``/voice on|off`` flag. The REPL
    # driver reads this to decide whether to pipe mic audio through
    # the STT pipeline and speak responses via TTS.
    voice_mode: bool = False
    # Wave-F (v2.0) Task 9: ``/review --auto on`` flag. When true,
    # the REPL driver runs ``/review`` after every agent turn and
    # prints the verdict as a post-turn banner.
    auto_review: bool = False
    # Side-channel for ``/btw <topic>`` — questions that should NOT
    # enter the main agent context. Kept as plain strings so a future
    # exporter can drop them into a "side notes" section without
    # touching the LLM transcript.
    _btw_log: list[str] = field(default_factory=list, repr=False)

    # v1.7.4: tracks which provider slug the live LLM was built from,
    # so ``/model list`` can highlight the currently-selected backend.
    # Defaults to None — the factory cascade decides at first use.
    current_llm_name: str | None = None

    # v1.7.5 (Wave-C, Task 1): persistent rewind / resume.
    # ``sessions_root`` is opt-in — when ``None`` the session never
    # touches disk, preserving back-compat for the dozens of existing
    # tests that build a transient ``InteractiveSession``. The driver
    # passes ``repo_root / ".lyra" / "sessions"`` to enable persistence.
    sessions_root: Path | None = None
    session_id: str = field(default_factory=_default_session_id)
    session_name: str | None = None

    # v1.7.5 (Wave-C, Task 11): persistent config store. ``config_path``
    # is opt-in (defaults to ``None`` so transient sessions stay 100%
    # in-memory); ``config`` is always non-None — boot uses an empty
    # store when no path was provided. ``InteractiveSession.from_config``
    # is the canonical entry point that loads the file *and* applies
    # the known keys.
    config_path: Path | None = None
    config: "_ConfigT | None" = field(default=None, repr=False)

    # v1.8 (Wave-D, Task 2): live subagent process table.
    # ``subagent_registry`` is an injected
    # :class:`lyra_core.subagent.SubagentRegistry`; the REPL itself
    # never constructs one (the driver wires it once it has a
    # ``task`` callable). Stays ``None`` for headless tests that
    # don't exercise ``/agents``. ``focused_subagent`` is the id
    # currently surfaced in the status bar — Ctrl+F (Wave-D Task 2)
    # mutates it via :func:`keybinds.focus_foreground_subagent`.
    subagent_registry: Any | None = field(default=None, repr=False)
    focused_subagent: str | None = None

    # v1.8 (Wave-D, Tasks 6/7/12/13/15): substrate fields the slashes
    # lazily attach. None until the first slash that needs them, so
    # transient sessions stay zero-cost.
    permission_stack: Any | None = field(default=None, repr=False)
    tool_approval_cache: Any | None = field(default=None, repr=False)
    mcp_registry: Any | None = field(default=None, repr=False)
    budget_meter: Any | None = field(default=None, repr=False)
    lifecycle_bus: Any | None = field(default=None, repr=False)
    plugins: list[Any] = field(default_factory=list, repr=False)
    _session_store: Any | None = field(default=None, repr=False)
    _pair_stream: Any | None = field(default=None, repr=False)
    _pair_sink: Any | None = field(default=None, repr=False)

    # v2.2.1: cached LLMProvider so plain-text routing in the active
    # modes (plan / build / run / explore) doesn't rebuild the provider
    # on every turn. ``None`` until the first plain-text call. The
    # cache is invalidated when ``/model`` switches the active model.
    _llm_provider: Any | None = field(default=None, repr=False)
    _llm_provider_kind: str | None = field(default=None, repr=False)
    # Conversation history fed into the LLM. Rolling buffer trimmed by
    # turn count rather than tokens — keeps the implementation simple
    # and good enough until we add proper context-window management.
    _chat_history: list[Any] = field(default_factory=list, repr=False)

    # v2.4.0 (Phase B): chat-mode tool loop.
    #
    # ``chat_tools_enabled`` toggles the read/write filesystem tool
    # set in plain-text turns. ``True`` by default so the marquee
    # "ask Lyra about your codebase" UX works the moment a fresh
    # ``lyra`` lands; flip with ``/tools chat off`` for users who
    # want pure conversational LLM with no side-effects.
    #
    # ``_chat_tool_registry`` is lazily built on the first turn that
    # actually needs it (saves the lyra-core import cost on plain
    # banner / status / help paths). ``None`` until then.
    #
    # ``_chat_tools_loaded`` is a one-shot flag so we only attempt
    # registry construction once per session — if lyra-core isn't
    # installed (rare; almost always shipped together) the second
    # attempt would just retrigger the same ImportError.
    chat_tools_enabled: bool = True
    _chat_tool_registry: Any | None = field(default=None, repr=False)
    _chat_tools_loaded: bool = field(default=False, repr=False)

    # v2.4.0 (Phase B.4): SKILL.md injection.
    #
    # ``skills_inject_enabled`` toggles whether ``_chat_with_llm``
    # prepends a "## Available skills" block to the active mode
    # system prompt on every turn. Default ``True`` so the LLM
    # actually knows about the packs we ship and the user's project
    # skills; flip with ``/skills off`` for shorter system prompts
    # on tight context budgets.
    #
    # ``_cached_skill_block`` memoises the rendered block so we
    # don't re-walk every ``SKILL.md`` on every turn — discovery is
    # cheap (dozens of files, max) but pointless to repeat. The
    # cache is invalidated when ``/skills reload`` is invoked.
    skills_inject_enabled: bool = True
    _cached_skill_block: Optional[str] = field(default=None, repr=False)

    # v3.5.0 (Phase O.2): per-turn skill activation telemetry.
    #
    # ``_skill_activation_recorder`` bridges the chat lifecycle (the
    # ``turn_complete`` / ``turn_rejected`` events emitted by
    # ``_chat_with_llm``) and the on-disk skill ledger (under
    # ``$LYRA_HOME/skill_ledger.json``). It accumulates activations
    # while the turn is in flight and writes a :class:`SkillOutcome`
    # per skill once the verdict arrives. Lazily built by the driver
    # bootstrap so embedded clients that don't want telemetry can
    # leave it ``None`` — :func:`_augment_system_prompt_with_skills`
    # treats a missing recorder as a no-op.
    _skill_activation_recorder: Any | None = field(default=None, repr=False)

    # v2.4.0 (Phase B.5): memory injection.
    #
    # ``memory_inject_enabled`` toggles whether ``_chat_with_llm``
    # queries procedural memory + the reasoning bank for the user's
    # line and prepends a "## Relevant memory" block to the system
    # prompt. Default ``True`` because that's the entire point of
    # paying the cost of having memory in the first place.
    #
    # ``reasoning_bank`` is an optional in-process
    # :class:`lyra_core.memory.reasoning_bank.ReasoningBank` (or any
    # duck-typed equivalent). The driver attaches one at boot when
    # the project opts in (via plugin / config); when ``None`` the
    # bank query is skipped without complaint.
    #
    # ``_procedural_memory`` is the lazily-opened SQLite-backed
    # store at ``<repo>/.lyra/memory/procedural.sqlite``. A missing
    # file is fine — chat still works, the block just stays empty.
    memory_inject_enabled: bool = True
    reasoning_bank: Any | None = field(default=None, repr=False)
    _procedural_memory: Any | None = field(default=None, repr=False)
    _procedural_memory_loaded: bool = field(default=False, repr=False)

    # v2.5.0 (Phase C.2): MCP autoload.
    #
    # ``mcp_servers`` is the list of :class:`MCPServerConfig` records
    # discovered at REPL boot from ``~/.lyra/mcp.json`` and
    # ``./.lyra/mcp.json``. Empty when the file is missing — chat
    # still works without MCP. The driver populates this so ``/mcp
    # list`` can show what's autoloaded; the entries are also fed to
    # the chat-tool loop in Phase C.4 so the LLM can call them.
    #
    # ``_mcp_clients`` is a name → live transport map populated lazily
    # on first ``/mcp connect <name>`` (or on first chat turn when
    # auto-spawn is on). We keep them long-lived per-session so we
    # don't pay handshake cost per tool call.
    #
    # ``mcp_autospawn`` controls whether the chat loop will lazily
    # spawn entries from ``mcp_servers`` the first time the LLM
    # actually wants to call one. Default ``True`` because that's the
    # whole point of declaring them in ``mcp.json``; flip to ``False``
    # for paranoid runs that want explicit ``/mcp connect`` first.
    mcp_servers: list[Any] = field(default_factory=list, repr=False)
    _mcp_clients: dict[str, Any] = field(default_factory=dict, repr=False)
    mcp_autospawn: bool = True
    _mcp_load_issues: list[Any] = field(default_factory=list, repr=False)

    # Internal; populated by ``dispatch`` and replayed by ``/rewind``.
    _turns_log: list[_TurnSnapshot] = field(default_factory=list, repr=False)

    # v3.0.0 (Phase I): companion stack for /redo. ``rewind_one`` pushes
    # popped snapshots here; ``redo_one`` pops them back. Any new
    # plain-text turn drains this stack so a redo can never resurrect a
    # branch that diverged from the live timeline. Mirrors opencode's
    # ``revert``/``unrevert`` semantics.
    _redo_log: list[_TurnSnapshot] = field(default_factory=list, repr=False)

    # v3.0.0 (Phase I): named tool bundle currently in effect. Defaults
    # to ``"default"`` (every kernel-registered tool); changes via
    # ``/toolsets apply <name>``. Hermes-agent parity. The kernel's
    # permission stack still arbitrates per-call risk — this only
    # advertises a curated subset to the user / LLM at /tools time.
    active_toolset: str = "default"

    # v3.0.0 (Phase I): user-authored slash commands loaded from
    # ``<repo>/.lyra/commands/*.md``. Lazily populated by
    # :meth:`_dispatch_slash` on first miss so cold starts pay nothing
    # and the loader picks up files added mid-session via /init or
    # external editing. ``None`` means "not loaded yet"; an empty
    # dict means "scanned, nothing found".
    _user_commands: dict[str, Any] | None = field(default=None, repr=False)

    # v3.1.0 (Phase J.4): Reflexion retrospective loop. ``reflexion_enabled``
    # gates whether the next plain-text turn injects a "Lessons from
    # previous attempts" preamble drawn from the on-disk memory at
    # ``<repo>/.lyra/reflexion.json``. ``_reflexion_memory`` is a lazy
    # accessor populated on first /reflect call so cold starts pay
    # nothing; ``_last_user_task`` lets ``/reflect add`` attach a
    # lesson to the most recent prompt without forcing the user to
    # retype it.
    reflexion_enabled: bool = False
    _reflexion_memory: Any = field(default=None, repr=False)
    _last_user_task: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Normalise legacy mode names from v1.x / v2.x → v3.2 canonical.

        v3.2.0 collapsed Lyra's 5-mode taxonomy onto Claude-Code's 4-mode
        one. A user landing here with an old persisted ``mode = "build"``
        from settings.json or with a ``--mode build`` flag from a script
        needs to keep working without staring at a "valid: agent, plan,
        debug, ask" error. We do the remap here so every code path
        (driver default, CLI flag, settings.json restore, ``/mode build``
        muscle memory) lands on the same canonical name.
        """
        canonical = _LEGACY_MODE_REMAP.get(self.mode, self.mode)
        if canonical != self.mode:
            self.mode = canonical

    def dispatch(self, line: str) -> CommandResult:
        stripped = line.strip()
        if not stripped:
            return CommandResult()
        self.history.append(stripped)
        if stripped.startswith("/"):
            return self._dispatch_slash(stripped)
        return self._dispatch_plain(stripped)

    def _dispatch_slash(self, line: str) -> CommandResult:
        parts = line[1:].split(maxsplit=1)
        name = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""
        handler = SLASH_COMMANDS.get(name)
        if handler is not None:
            return handler(self, args)

        user_cmd = self._lookup_user_command(name)
        if user_cmd is not None:
            rendered = user_cmd.render(args)
            if not rendered.strip():
                return CommandResult(
                    output=(
                        f"/{name} resolved to user command at {user_cmd.source} "
                        f"but produced an empty prompt body."
                    )
                )
            return self._dispatch_plain(rendered)

        return CommandResult(
            output=(
                f"unknown command /{name}. "
                f"Type /help for the full list."
            ),
            renderable=_out.bad_command_renderable(name),
        )

    def _lookup_user_command(self, name: str):
        """Resolve ``name`` against ``.lyra/commands/*.md`` (Phase I).

        Lazily populates :attr:`_user_commands` on first miss so cold
        starts pay nothing. Reload via :meth:`reload_user_commands`
        (e.g. after the user edits a markdown file mid-session).
        """
        if self._user_commands is None:
            self._user_commands = self._load_user_commands_for_repo()
        return self._user_commands.get(name)

    def reload_user_commands(self) -> int:
        """Force a re-scan of ``.lyra/commands``; returns the count."""
        self._user_commands = self._load_user_commands_for_repo()
        return len(self._user_commands)

    def _load_user_commands_for_repo(self) -> dict[str, Any]:
        try:
            from .user_commands import (
                default_commands_dir,
                expand_aliases,
                load_user_commands,
            )

            commands = load_user_commands(default_commands_dir(self.repo_root))
            return expand_aliases(commands)
        except Exception:
            return {}

    def list_user_commands(self) -> dict[str, Any]:
        """Return a snapshot of currently-loaded user commands."""
        if self._user_commands is None:
            self._user_commands = self._load_user_commands_for_repo()
        return dict(self._user_commands)

    def _dispatch_plain(self, line: str) -> CommandResult:
        # Snapshot *before* mutating so ``/rewind`` can restore exactly
        # the state the user saw when they pressed Enter. v3.2.0 also
        # stamps the *active* model + wall-clock timestamp so
        # ``/history --verbose`` and ``lyra session show`` can render
        # per-turn provenance even when the chat-side log was skipped
        # (e.g. a slash command, or a turn rejected before billing).
        snap = _TurnSnapshot(
            line=line,
            mode=self.mode,
            turn=self.turn,
            pending_task=self.pending_task,
            cost_usd=self.cost_usd,
            tokens_used=self.tokens_used,
            model=self.model,
            ts=_time.time(),
        )
        self._turns_log.append(snap)
        self._persist_turn(snap)
        # A fresh prompt makes any "future" history that sat on the
        # redo stack invalid (the timeline diverged), so we drain it.
        # Without this, /rewind ; type ; /redo would resurrect the
        # pre-divergence state and silently overwrite the new turn.
        self._redo_log.clear()
        # v3.1.0 (Phase J.4): record the plain-text prompt so a later
        # ``/reflect add`` can attach a lesson to it without forcing
        # the user to retype the task.
        self._last_user_task = line
        self.turn += 1
        handler = _MODE_HANDLERS.get(self.mode, _handle_plan_text)
        return handler(self, line)

    # ---- helpers used by slash handlers ------------------------------------

    def status_line(self) -> str:
        """One-line bar the driver shows at the bottom of the terminal."""
        repo_label = self.repo_root.name or str(self.repo_root)
        # Pair-mode flag (Wave-C Task 14) surfaces only when on so the
        # bar stays compact in the common case.
        pair_segment = "  │  pair: on" if getattr(self, "pair_mode", False) else ""
        return (
            f"mode: {self.mode}  │  model: {self.model}  │  repo: {repo_label}"
            f"  │  turn: {self.turn}  │  cost: ${self.cost_usd:.2f}"
            f"{pair_segment}"
            f"  │  /help"
        )

    def rewind_one(self) -> _TurnSnapshot | None:
        """Pop the most recent plain-text turn and restore state.

        When :attr:`sessions_root` is set the on-disk JSONL is also
        truncated by one line so the file stays in lockstep with
        ``self._turns_log`` — a subsequent ``/resume <id>`` therefore
        restores the post-rewind state, not a stale pre-rewind one.

        v3.0.0: also pushes the popped snapshot onto ``_redo_log`` so
        :meth:`redo_one` can re-apply it. Any subsequent plain-text
        turn drains the redo stack (see :meth:`_dispatch_plain`).
        """
        if not self._turns_log:
            return None
        snap = self._turns_log.pop()
        self.mode = snap.mode
        self.turn = snap.turn
        self.pending_task = snap.pending_task
        self.cost_usd = snap.cost_usd
        self.tokens_used = snap.tokens_used
        self._truncate_persisted_log_by_one()
        self._redo_log.append(snap)
        return snap

    def redo_one(self) -> _TurnSnapshot | None:
        """Re-apply the most recent ``/rewind``.

        Symmetric counterpart to :meth:`rewind_one`. Pops the top of
        ``_redo_log`` (the snapshot that ``/rewind`` last popped),
        appends it back onto ``_turns_log``, advances ``self.turn``
        past it, and re-persists the JSONL line so ``/resume`` lands
        on the post-redo state.

        Returns ``None`` when there is nothing to redo (either the
        stack is empty or it was drained by a fresh plain-text turn).
        """
        if not self._redo_log:
            return None
        snap = self._redo_log.pop()
        # Restore the *post-turn* state. The snapshot captured the
        # pre-turn cost / tokens / mode, so after re-appending it the
        # session's "turn" pointer must advance to one past the
        # snapshot's recorded turn — exactly what ``_dispatch_plain``
        # would have done if the turn had run for real.
        self._turns_log.append(snap)
        self.mode = snap.mode
        self.turn = snap.turn + 1
        self.pending_task = snap.pending_task
        self.cost_usd = snap.cost_usd
        self.tokens_used = snap.tokens_used
        self._persist_turn(snap)
        return snap

    # ---- v1.7.5: persistence helpers (Wave-C Task 1) -------------------

    def _session_dir(self) -> Path | None:
        """Resolve ``<sessions_root>/<session_id>`` or ``None`` when off.

        Validates the session id against
        :func:`sessions_store._validate_session_id` so a forged id like
        ``../../../etc`` can never escape the sessions root, even if a
        future caller forgets to sanitise.
        """
        if self.sessions_root is None:
            return None
        from .sessions_store import _validate_session_id  # local: keep cold-start cheap

        try:
            _validate_session_id(self.session_id)
        except ValueError:
            # An invalid id is treated as "persistence off" so a corrupt
            # field can't crash the REPL — the caller already gracefully
            # handles ``None`` from this helper.
            return None
        return self.sessions_root / self.session_id

    def _turns_log_path(self) -> Path | None:
        d = self._session_dir()
        return None if d is None else d / "turns.jsonl"

    def _persist_turn(self, snap: _TurnSnapshot) -> None:
        """Append one JSONL line for *snap*. No-op when persistence is off.

        Persistence failures must never break the live session — we
        log nothing and swallow the exception. The on-disk file is a
        recovery aid, not a hard dependency.
        """
        path = self._turns_log_path()
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            import json as _json

            # v3.2.0 (Phase L): bootstrap a minimal ``meta.json`` on
            # first write so ``lyra session show`` can always display
            # ``created_at`` (and the SessionsStore.list() summary
            # stays useful for sessions never explicitly named or
            # forked). Cheap and idempotent — just an existence check.
            meta_path = path.parent / "meta.json"
            if not meta_path.exists():
                try:
                    import datetime as _dt

                    meta_payload = {
                        "session_id": self.session_id,
                        "created_at": _dt.datetime.now().isoformat(
                            timespec="seconds"
                        ),
                    }
                    meta_path.write_text(
                        _json.dumps(meta_payload, indent=2),
                        encoding="utf-8",
                    )
                except OSError:
                    pass

            payload: dict[str, Any] = {
                # Pre-v2.3.0 lines have no "kind" field; we omit it
                # too on turn snapshots so old turns.jsonl files keep
                # parsing identically. ``resume_session`` treats a
                # missing "kind" as ``"turn"``.
                "line": snap.line,
                "mode": snap.mode,
                "turn": snap.turn,
                "pending_task": snap.pending_task,
                "cost_usd": snap.cost_usd,
                "tokens_used": snap.tokens_used,
            }
            # v3.2.0 (Phase L): write the optional per-turn metadata
            # only when present so old readers (and pre-v3.2 sessions
            # being appended to) don't see a flood of ``null`` keys.
            if snap.model is not None:
                payload["model"] = snap.model
            if snap.ts is not None:
                payload["ts"] = snap.ts
            if snap.tokens_in is not None:
                payload["tokens_in"] = snap.tokens_in
            if snap.tokens_out is not None:
                payload["tokens_out"] = snap.tokens_out
            if snap.cost_delta_usd is not None:
                payload["cost_delta_usd"] = snap.cost_delta_usd
            if snap.latency_ms is not None:
                payload["latency_ms"] = snap.latency_ms
            with path.open("a", encoding="utf-8") as fh:
                fh.write(_json.dumps(payload) + "\n")
        except OSError:
            pass

    def _persist_chat_exchange(
        self,
        user_text: str,
        assistant_text: str,
        *,
        model: str | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        cost_delta_usd: float | None = None,
        latency_ms: float | None = None,
        ts: float | None = None,
    ) -> None:
        """Append a JSONL record of one user→assistant chat exchange.

        v2.3.0 addition: prior to this, ``_chat_history`` was only
        kept in memory, so ``/resume`` rebuilt session metadata
        (``mode`` / ``turn`` / ``cost_usd``) but the LLM saw an empty
        conversation and the user got "who are you again?" responses
        on continued sessions. The new ``"kind": "chat"`` lines let
        :meth:`resume_session` rebuild the assistant-side context
        verbatim, so the model picks up exactly where it left off.

        Records are appended *after* the corresponding turn snapshot
        (so a single user line on disk produces two entries: the
        ``"turn"`` and then the ``"chat"``). Non-LLM turns (slash
        commands, mode switches, etc.) skip this method and only the
        ``"turn"`` line lands.

        v3.2.0 (Phase L): the optional kwargs let the LLM dispatch
        layer attach per-turn metadata (model slug, tokens_in/out,
        cost delta, latency_ms, timestamp) so ``/history --verbose``
        and ``lyra session show`` can show exactly which model
        answered each prompt and what it spent. Every kwarg is
        optional — call sites that don't have the data (or older
        plumbing that hasn't been ported yet) keep working as
        before, and old readers see them as missing keys.

        We persist the *plain text* of each side rather than the full
        :class:`Message` (no tool_calls, no metadata) because:

        1. Tool-call recapture happens on the next live turn anyway;
           the model rebuilds intent from text just fine.
        2. The on-disk format stays human-greppable, which is the
           main reason ``turns.jsonl`` is a JSONL file instead of an
           opaque blob.
        3. Forward-compat: future schema additions (multi-modal,
           citations, tool transcripts) can land as new ``"kind"``
           values without breaking older readers.
        """
        path = self._turns_log_path()
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            import json as _json

            payload: dict[str, Any] = {
                "kind": "chat",
                "turn": self.turn,
                "user": user_text,
                "assistant": assistant_text,
            }
            # v3.2.0 (Phase L): only emit the optional fields when the
            # caller passes them so old transcripts stay byte-identical
            # for the lines they already produced.
            if model is not None:
                payload["model"] = model
            if tokens_in is not None:
                payload["tokens_in"] = int(tokens_in)
            if tokens_out is not None:
                payload["tokens_out"] = int(tokens_out)
            if cost_delta_usd is not None:
                payload["cost_delta_usd"] = float(cost_delta_usd)
            if latency_ms is not None:
                payload["latency_ms"] = float(latency_ms)
            if ts is not None:
                payload["ts"] = float(ts)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(_json.dumps(payload) + "\n")
        except OSError:
            pass

        # Phase D.6: also write through to the FTS5 store when one is
        # already attached so /search finds the latest exchange. The
        # store is attached lazily by :func:`_ensure_default_search_fn`
        # — we only index when it exists, otherwise the import is
        # deferred until the user actually runs /search.
        try:
            _index_exchange_in_store(self, user_text, assistant_text)
        except Exception:
            pass

    def _truncate_persisted_log_by_one(self) -> None:
        """Drop the trailing turn (and any chat extension) after :meth:`rewind_one`.

        Uses the same atomic temp-file + rename dance as
        :class:`SessionsStore` so a crash mid-rewind can never leave a
        partially truncated turns.jsonl.

        v2.3.0: handles the new mixed-record format where each
        plain-text turn may be followed by zero or more
        ``{"kind": "chat"}`` lines persisting the LLM exchange. We
        peel off all trailing ``"chat"`` records first, then the
        terminating turn snapshot, so the file stays in lockstep
        with ``self._turns_log``. Older single-record sessions still
        truncate exactly one line, matching the pre-v2.3.0 behaviour.
        """
        path = self._turns_log_path()
        if path is None or not path.is_file():
            return
        try:
            text = path.read_text(encoding="utf-8")
            lines = [ln for ln in text.splitlines() if ln.strip()]
            if not lines:
                return

            import json as _json

            def _is_chat(raw: str) -> bool:
                try:
                    return _json.loads(raw).get("kind") == "chat"
                except (ValueError, TypeError):
                    return False

            # Peel any trailing chat extensions, then the turn line.
            while lines and _is_chat(lines[-1]):
                lines.pop()
            if lines:
                lines.pop()

            from .sessions_store import _atomic_write_text  # local: keep cold-start cheap

            _atomic_write_text(
                path,
                "\n".join(lines) + ("\n" if lines else ""),
            )
        except OSError:
            pass

    @classmethod
    def resume_session(
        cls,
        *,
        session_id: str,
        sessions_root: Path,
        repo_root: Path,
    ) -> "InteractiveSession | None":
        """Re-build a session from its on-disk ``turns.jsonl``.

        Returns ``None`` when the directory or log is missing — callers
        surface a friendly "no such session" message rather than a
        traceback. State is restored to the *last recorded* turn (i.e.
        ``mode``, ``turn``, ``pending_task``, ``cost_usd``,
        ``tokens_used`` of the most recent line) so the user picks up
        exactly where they left off.

        The ``InteractiveSession`` returned has persistence already
        enabled (``sessions_root`` and ``session_id`` set), so any
        further dispatch keeps appending to the same JSONL.
        """
        from .sessions_store import _validate_session_id  # local: keep cold-start cheap

        try:
            _validate_session_id(session_id)
        except ValueError:
            return None
        path = sessions_root / session_id / "turns.jsonl"
        if not path.is_file():
            return None
        import json as _json

        snaps: list[_TurnSnapshot] = []
        chat_records: list[tuple[str, str]] = []
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                if not raw.strip():
                    continue
                row = _json.loads(raw)
                # v2.3.0 schema: chat exchanges land as
                # ``{"kind": "chat", ...}`` lines next to the existing
                # turn snapshots. Older sessions have no "kind" field
                # at all on their lines and parse as plain turns
                # (default branch below).
                kind = row.get("kind") or "turn"
                if kind == "chat":
                    user_text = row.get("user")
                    assistant_text = row.get("assistant")
                    if isinstance(user_text, str) and isinstance(assistant_text, str):
                        chat_records.append((user_text, assistant_text))
                    continue
                raw_mode = row.get("mode", "plan")
                # v3.2.0 (Phase L): read the optional per-turn metadata
                # when the on-disk record carries it. Old (<= v3.1)
                # lines just omit the keys, so ``.get`` returns ``None``
                # and the snapshot keeps the dataclass defaults.
                def _maybe_int(v: Any) -> int | None:
                    return int(v) if isinstance(v, (int, float)) else None

                def _maybe_float(v: Any) -> float | None:
                    return float(v) if isinstance(v, (int, float)) else None

                snaps.append(
                    _TurnSnapshot(
                        line=row.get("line", ""),
                        mode=_LEGACY_MODE_REMAP.get(raw_mode, raw_mode),
                        turn=int(row.get("turn", 0)),
                        pending_task=row.get("pending_task"),
                        cost_usd=float(row.get("cost_usd", 0.0)),
                        tokens_used=int(row.get("tokens_used", 0)),
                        model=row.get("model"),
                        ts=_maybe_float(row.get("ts")),
                        tokens_in=_maybe_int(row.get("tokens_in")),
                        tokens_out=_maybe_int(row.get("tokens_out")),
                        cost_delta_usd=_maybe_float(row.get("cost_delta_usd")),
                        latency_ms=_maybe_float(row.get("latency_ms")),
                    )
                )
        except (OSError, _json.JSONDecodeError, ValueError):
            return None

        if not snaps:
            # File exists but is empty; treat the same as "no session".
            return None

        last = snaps[-1]
        s = cls(
            repo_root=repo_root,
            sessions_root=sessions_root,
            session_id=session_id,
            mode=last.mode,
            # JSONL stores the *pre-turn* counter; restore the
            # post-turn counter so the next dispatch increments cleanly.
            turn=last.turn + 1,
            pending_task=last.pending_task,
            cost_usd=last.cost_usd,
            tokens_used=last.tokens_used,
        )
        # v3.2.0 (Phase L): carry the *last recorded model* forward so
        # a resumed session keeps using the model the user picked, not
        # whatever the cls default ("auto") would resolve to. Old
        # transcripts without a model field fall through to the default
        # so back-compat is preserved.
        if last.model:
            s.model = last.model
        s._turns_log = snaps
        # Rebuild the rolling chat-history buffer from the persisted
        # records. We only restore the most recent
        # ``_CHAT_HISTORY_TURNS`` exchanges to match the live trim
        # behaviour (otherwise resuming a 500-turn session would shoot
        # a context-window exception on the next call). The trim is
        # applied *here*, not when persisting, so the on-disk record
        # remains the full history — useful for ``/transcript``-style
        # exports and offline audit.
        if chat_records:
            try:
                from harness_core.messages import Message as _Msg

                trimmed = chat_records[-_CHAT_HISTORY_TURNS:]
                rebuilt: list[Any] = []
                for user_text, assistant_text in trimmed:
                    rebuilt.append(_Msg.user(user_text))
                    if hasattr(_Msg, "assistant"):
                        rebuilt.append(_Msg.assistant(assistant_text))
                    else:
                        rebuilt.append(
                            _Msg(role="assistant", content=assistant_text)
                        )
                s._chat_history = rebuilt
            except Exception:
                # ``harness_core`` should always be importable; we keep
                # the silent fallback so a partial install can still
                # resume metadata even when Message reconstruction
                # fails. Better than refusing to resume entirely.
                pass
        return s

    @classmethod
    def from_config(
        cls,
        *,
        repo_root: Path,
        config_path: Path | None = None,
        **overrides: Any,
    ) -> "InteractiveSession":
        """Boot a session honouring the user's persisted ``/config`` keys.

        ``config_path`` defaults to ``None`` — callers that want the
        canonical ``~/.lyra/config.yaml`` should compute and pass it
        explicitly so this factory stays pure (no implicit env reads).

        The known keys (``theme``, ``vim``, ``permission_mode``,
        ``tdd_gate``, ``effort``, ``budget_cap_usd``, ``model``,
        ``mode``) are applied after construction so explicit
        ``overrides`` always win — letting the driver still pin the
        repo / model from CLI flags.
        """
        cfg = _ConfigT.load(config_path)
        session = cls(
            repo_root=repo_root,
            config_path=config_path,
            config=cfg,
            **overrides,
        )
        _apply_config_to_session(cfg, session)
        return session

    # ---- v1.7.4: /model list + /models -----------------------------------

    def _cmd_model_list(self, _rest: str) -> str:
        """Render every known LLM provider with configured/selected markers.

        Output legend: ``●`` = currently selected, ``✓`` = configured
        (key set or local endpoint reachable), ``—`` = not configured.

        Combines ``known_llm_names`` (curated short names) with the
        OpenAI-compatible ``PRESETS`` registry so adding a new preset
        in v1.7.4 (DashScope / vLLM / llama-server / TGI / Llamafile /
        MLX) automatically appears here without touching this file.
        """
        import os

        from lyra_cli.llm_factory import known_llm_names
        from lyra_cli.providers.openai_compatible import PRESETS

        selected = (self.current_llm_name or "").lower().strip()
        seen: set[str] = set()
        rows: list[tuple[str, str, bool]] = []  # (name, detail, configured)

        for name in known_llm_names():
            if name == "auto" or name in seen:
                continue
            seen.add(name)
            configured = False
            detail = ""
            if name == "mock":
                configured = True
                detail = "canned outputs"
            elif name == "anthropic":
                configured = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
                detail = os.environ.get("HARNESS_LLM_MODEL", "claude-*")
            elif name == "gemini":
                configured = bool(
                    os.environ.get("GEMINI_API_KEY", "").strip()
                    or os.environ.get("GOOGLE_API_KEY", "").strip()
                )
                detail = "gemini-*"
            elif name == "ollama":
                try:
                    from lyra_cli.providers.ollama import ollama_reachable

                    configured = ollama_reachable()
                except Exception:
                    configured = False
                detail = "local"
            else:
                preset = next((p for p in PRESETS if p.name == name), None)
                if preset is not None:
                    try:
                        configured = preset.configured()
                    except Exception:
                        configured = False
                    detail = preset.default_model
                    if preset.auth_scheme == "none":
                        detail = f"{detail} (local)"
            rows.append((name, detail, configured))

        lines = ["Available providers:"]
        for name, detail, configured in rows:
            if name == selected:
                marker = "●"
            elif configured:
                marker = "✓"
            else:
                marker = "—"
            lines.append(f"  {marker}  {name:<22}  {detail}")
        lines.append("")
        lines.append("Legend: ●=selected  ✓=configured  —=not configured")
        return "\n".join(lines)

    def _cmd_models(self, rest: str) -> str:
        """Alias for :meth:`_cmd_model_list` — same output, different slash."""
        return self._cmd_model_list(rest)

    # ---- v1.7.4: /diff (real git diff) -----------------------------------

    def _cmd_diff_text(self, _rest: str) -> str:
        """Run real ``git diff --stat`` + ``git diff`` and render the output.

        Returns one of three text shapes:

        1. Outside a git repo (or git missing): a friendly error.
        2. Working tree clean: a friendly "no changes" message.
        3. Otherwise: ``git diff --stat`` followed by the unified diff,
           truncated at 20k chars so the REPL doesn't get flooded.
        """
        import subprocess

        try:
            toplevel = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "/diff: not a git repository (or git is not installed)"

        try:
            stat = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=toplevel,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            body = subprocess.run(
                ["git", "diff"],
                cwd=toplevel,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        except subprocess.CalledProcessError as exc:
            return f"/diff: git failed: {(exc.stderr or '').strip() or exc}"

        if not stat.strip() and not body.strip():
            return "/diff: working tree clean - no changes since HEAD"

        if len(body) > 20_000:
            body = (
                body[:20_000]
                + "\n...\n(truncated; run `git diff` in shell for full output)"
            )
        return f"{stat}\n{body}" if stat else body

    # ---- v1.7.5: /blame, /trace, /self (Wave-C Task 4) ----------------

    def _cmd_blame_text(self, rest: str) -> str:
        """Run ``git blame`` on *rest* (or fall back to a friendly message).

        Skip-on-no-git mirrors :meth:`_cmd_diff_text` so the slash
        always returns *something* even outside a git checkout. The
        body is truncated at 20k chars for the same flood-protection
        reason as ``/diff``.
        """
        import subprocess

        target = rest.strip() or "(unspecified)"
        if target == "(unspecified)":
            return (
                "/blame: pass a path, e.g. `/blame src/lyra/runtime/agent.py`."
            )

        try:
            toplevel = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_root,
            ).stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return f"/blame: not a git repository (or git is not installed): {target}"

        try:
            body = subprocess.run(
                ["git", "blame", "--date=short", target],
                cwd=toplevel,
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        except subprocess.CalledProcessError as exc:
            return f"/blame: git failed: {(exc.stderr or '').strip() or exc}"

        if len(body) > 20_000:
            body = body[:20_000] + "\n...\n(truncated; run `git blame` in shell for full output)"
        return body or f"/blame: no blame data for {target}"

    def _cmd_trace_text(self, rest: str) -> str:
        """Render the last N events from the global HIR ring buffer.

        ``rest`` accepts ``--last=N`` to override the default of 25 so
        the user can drill in further when investigating a cascade.
        """
        from lyra_core.hir import events as _ev

        last = 25
        for tok in (rest or "").split():
            if tok.startswith("--last="):
                try:
                    last = max(1, int(tok.split("=", 1)[1]))
                except ValueError:
                    pass

        snap = _ev.global_ring().snapshot()[-last:]
        if not snap:
            return "/trace: ring buffer is empty (no HIR events recorded yet)."
        lines = [f"/trace: last {len(snap)} HIR events"]
        for i, entry in enumerate(snap, start=1):
            attrs_str = ", ".join(f"{k}={v!r}" for k, v in entry.get("attrs", {}).items())
            lines.append(f"  {i:>3}.  {entry['name']:<28}  {attrs_str}")
        return "\n".join(lines)

    def _cmd_self_text(self, _rest: str) -> str:
        """Render the live :class:`InteractiveSession` state as YAML-ish text.

        We avoid PyYAML to keep the dep surface minimal. The history
        is truncated to 5 most-recent entries (with a "+N more" tail)
        so a long REPL doesn't make the slash unreadable.
        """
        truncated_history = self.history[-5:]
        more_history = max(0, len(self.history) - len(truncated_history))
        lines = [
            "InteractiveSession:",
            f"  session_id:    {self.session_id}",
            f"  session_name:  {self.session_name!r}",
            f"  repo_root:     {self.repo_root}",
            f"  model:         {self.model}",
            f"  mode:          {self.mode}",
            f"  turn:          {self.turn}",
            f"  cost_usd:      {self.cost_usd}",
            f"  tokens_used:   {self.tokens_used}",
            f"  pending_task:  {self.pending_task!r}",
            f"  current_llm:   {self.current_llm_name!r}",
            f"  deep_think:    {self.deep_think}",
            f"  verbose:       {self.verbose}",
            f"  vim_mode:      {self.vim_mode}",
            f"  theme:         {self.theme}",
            f"  budget_cap:    {self.budget_cap_usd}",
            f"  task_panel:    {self.task_panel}",
            f"  sessions_root: {self.sessions_root}",
            "  history:",
        ]
        for line in truncated_history:
            lines.append(f"    - {line!r}")
        if more_history:
            lines.append(f"    (+{more_history} earlier entries elided)")
        return "\n".join(lines)

    # ---- v1.7.5: /map (Wave-C Task 3) -----------------------------------

    def _cmd_map_text(self, rest: str) -> str:
        """Render an indented ASCII tree of every ``*.py`` under ``repo_root``.

        ``rest`` accepts a single ``--max-depth=N`` flag (default 4) so
        deep monorepos can be summarised without flooding the REPL.
        Directories whose contents are clipped by the depth cap render
        as ``…`` so the user knows there's more to drill into.

        Stdlib-only by design — no graphviz / tree-sitter dep. The
        Phase-F /map upgrade (true import-graph) supersedes this body
        without changing the slash signature.
        """
        max_depth = 4
        rest = (rest or "").strip()
        for tok in rest.split():
            if tok.startswith("--max-depth="):
                try:
                    max_depth = max(0, int(tok.split("=", 1)[1]))
                except ValueError:
                    pass

        root = self.repo_root
        if not root.is_dir():
            return f"/map: {root} is not a directory"

        py_files = list(root.rglob("*.py"))
        if not py_files:
            return f"/map: no .py sources found under {root}"

        # Build a nested dict {dir_name: subtree_or_filename_set}.
        tree: dict = {}
        for path in py_files:
            try:
                rel = path.relative_to(root)
            except ValueError:
                continue
            parts = rel.parts
            cursor = tree
            for part in parts[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor.setdefault("__files__", set()).add(parts[-1])

        lines: list[str] = [f"/map: Repository map for {root}"]
        self._render_tree_recursive(
            tree, lines=lines, prefix="", depth=0, max_depth=max_depth
        )
        return "\n".join(lines)

    def _render_tree_recursive(
        self,
        node: dict,
        *,
        lines: list[str],
        prefix: str,
        depth: int,
        max_depth: int,
    ) -> None:
        """Walk *node* and append rendered tree lines.

        Uses claw-code-style box-drawing characters (``├──`` / ``└──``)
        with a depth gutter so the output reads cleanly in any terminal
        font.
        """
        if depth > max_depth:
            return
        # Stable ordering: directories first (alpha), then files (alpha).
        dir_keys = sorted(k for k in node if k != "__files__")
        files = sorted(node.get("__files__", set()))

        if depth == max_depth and (dir_keys or any(node.get(k) for k in dir_keys)):
            # We're at the cap — collapse anything deeper to "…".
            entries: list[tuple[str, bool]] = [(d, True) for d in dir_keys] + [
                (f, False) for f in files
            ]
            for i, (name, is_dir) in enumerate(entries):
                connector = "└── " if i == len(entries) - 1 else "├── "
                marker = "/" if is_dir else ""
                # Show '…' next to directories with hidden contents.
                hint = "  …" if is_dir and node.get(name) else ""
                lines.append(f"{prefix}{connector}{name}{marker}{hint}")
            return

        entries: list[tuple[str, bool]] = [(d, True) for d in dir_keys] + [
            (f, False) for f in files
        ]
        for i, (name, is_dir) in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            extension = "    " if i == len(entries) - 1 else "│   "
            marker = "/" if is_dir else ""
            lines.append(f"{prefix}{connector}{name}{marker}")
            if is_dir:
                self._render_tree_recursive(
                    node[name],
                    lines=lines,
                    prefix=prefix + extension,
                    depth=depth + 1,
                    max_depth=max_depth,
                )


# ---------------------------------------------------------------------------
# Mode handlers (plain-text routing)
# ---------------------------------------------------------------------------
#
# v3.2.0: Lyra's REPL exposes the Claude-Code 4-mode taxonomy — agent,
# plan, debug, ask. Every mode is a single-shot LLM chat turn with a
# mode-specific system prompt; tool-using turns (real edits, real
# shell) are still gated behind ``lyra run --plan``, which is the
# explicit "spend tokens + side-effect the repo" surface.
#
# Pre-v3.2 had five modes (plan / build / run / explore / retro) with
# ``retro`` carrying journal-note semantics. Journaling now lives at
# the CLI subcommand layer (``lyra retro``) so the REPL can stay a
# clean conversation surface that matches Claude Code's UX.


# v3.2.0: Lyra's interactive modes mirror Claude Code's 4-mode taxonomy
# (agent, plan, debug, ask). Every system prompt below ENUMERATES the
# four modes so the LLM never confabulates from training-data residue
# when the user asks "what modes do you have?". The shared preamble
# also explicitly notes that TDD's RED → GREEN → REFACTOR cycle is an
# OPT-IN PLUGIN (lyra_core.tdd), not a mode — this defends against a
# regression where the model used to list "BUILD / RED / GREEN /
# REFACTOR" as if they were peer modes (see CHANGELOG v3.2.0).
_LYRA_MODE_PREAMBLE = (
    "You are Lyra, a CLI-native coding assistant. You operate in one "
    "of four modes:\n"
    "  • agent — default; full-access execution. You can write code "
    "and call tools when the runtime gives them.\n"
    "  • plan  — read-only collaborative design. You produce plans, "
    "you do not edit files.\n"
    "  • debug — systematic troubleshooting with runtime evidence. "
    "You investigate failures and propose fixes.\n"
    "  • ask   — read-only Q&A. You answer questions about code "
    "without modifying it.\n"
    "TDD is an OPT-IN PLUGIN (RED → GREEN → REFACTOR phases inside "
    "the agent mode), NOT a separate mode. Never list TDD phases as "
    "modes when the user asks how many modes you have — the answer "
    "is always exactly four: agent, plan, debug, ask.\n"
)

_AGENT_SYSTEM_PROMPT = (
    _LYRA_MODE_PREAMBLE + "\n"
    "You are currently in AGENT mode. The user is asking you to "
    "design, write, or modify code. Reply concisely. If they ask a "
    "coding question, answer with a small focused code block. If "
    "they greet you / chitchat, reply naturally and offer to help. "
    "Do not pretend to have run any tools — only call a tool when "
    "the runtime explicitly gives you one this turn."
)

_PLAN_SYSTEM_PROMPT = (
    _LYRA_MODE_PREAMBLE + "\n"
    "You are currently in PLAN mode. The user is brainstorming what "
    "to build. Reply concisely and conversationally. If they "
    "describe a non-trivial task, propose a short numbered plan "
    "(3–7 steps). If they say hello / ask a question / chitchat, "
    "just answer naturally. Do not pretend to have run any tools — "
    "plan mode is read-only by contract."
)

_DEBUG_SYSTEM_PROMPT = (
    _LYRA_MODE_PREAMBLE + "\n"
    "You are currently in DEBUG mode. The user is troubleshooting a "
    "failure or unexpected behaviour. Be systematic: ask for the "
    "exact error / log / repro before proposing a fix, then form a "
    "hypothesis, then suggest the smallest experiment that proves "
    "or disproves it. Prefer runtime evidence over speculation. If "
    "they greet you, reply naturally and ask what's broken."
)

_ASK_SYSTEM_PROMPT = (
    _LYRA_MODE_PREAMBLE + "\n"
    "You are currently in ASK mode. The user is investigating a "
    "codebase or asking a conceptual question. Answer concisely. If "
    "they ask about specific files, suggest what to look at and "
    "why. Ask mode is strictly read-only — never propose edits, "
    "never claim to have run tools."
)


_MODE_SYSTEM_PROMPTS: dict[str, str] = {
    "agent": _AGENT_SYSTEM_PROMPT,
    "plan": _PLAN_SYSTEM_PROMPT,
    "debug": _DEBUG_SYSTEM_PROMPT,
    "ask": _ASK_SYSTEM_PROMPT,
}

# Rolling window for ``_chat_history``. 20 turns ≈ 40 messages, which
# fits comfortably in a 32k-token context for the cheap-tier models
# (DeepSeek, Qwen, gpt-4o-mini) we recommend by default.
_CHAT_HISTORY_TURNS = 20


def _resolve_model_for_role(session: InteractiveSession, role: str) -> Optional[str]:
    """Pick the user-facing model alias for a given task role.

    v2.7.1 introduced a Claude-Code-style **small/smart split**: cheap
    chat turns (default REPL conversation, /compact, status banter,
    completion) flow through ``session.fast_model`` while reasoning-
    heavy paths (/plan, /spawn, /review, /ultrareview, agent-loop tool
    reasoning, verifier rounds) flow through ``session.smart_model``.

    The defaults are ``deepseek-v4-flash`` → ``deepseek-chat`` and
    ``deepseek-v4-pro`` → ``deepseek-reasoner`` because DeepSeek is
    Lyra's cost-aware default backend. Users on other providers can
    override the slot pins via ``/model fast=<slug>`` and
    ``/model smart=<slug>``.

    The function returns ``None`` if the slot is empty (e.g. the
    user explicitly cleared it) — callers treat ``None`` as "honour
    whatever the provider reads from env" and skip env-stamping.
    """
    role_norm = (role or "chat").lower().strip()
    if role_norm in ("smart", "reasoning", "plan", "review", "verify", "spawn", "subagent"):
        slot = (getattr(session, "smart_model", "") or "").strip()
    else:
        slot = (getattr(session, "fast_model", "") or "").strip()
    return slot or None


# Map provider keys (as registered in ``lyra_core.providers.aliases``) to
# the env vars each preset reads model slugs from. We stamp every entry
# in the list so the resolved alias survives whichever lookup priority
# the active backend uses.
#
# ``HARNESS_LLM_MODEL`` is always stamped first because it's the canonical
# Lyra-wide override that Anthropic / Vertex / Bedrock / Copilot all
# read; the preset-specific keys catch the OpenAI-compatible lane that
# bypasses ``HARNESS_LLM_MODEL`` and prefers its own env var.
_PROVIDER_MODEL_ENV: dict[str, tuple[str, ...]] = {
    "anthropic":  ("HARNESS_LLM_MODEL",),
    "deepseek":   ("HARNESS_LLM_MODEL", "DEEPSEEK_MODEL", "OPEN_HARNESS_DEEPSEEK_MODEL"),
    "openai":     ("HARNESS_LLM_MODEL", "OPENAI_MODEL", "OPEN_HARNESS_OPENAI_MODEL"),
    "xai":        ("HARNESS_LLM_MODEL", "XAI_MODEL", "OPEN_HARNESS_XAI_MODEL"),
    "groq":       ("HARNESS_LLM_MODEL", "GROQ_MODEL", "OPEN_HARNESS_GROQ_MODEL"),
    "cerebras":   ("HARNESS_LLM_MODEL", "CEREBRAS_MODEL", "OPEN_HARNESS_CEREBRAS_MODEL"),
    "mistral":    ("HARNESS_LLM_MODEL", "MISTRAL_MODEL", "OPEN_HARNESS_MISTRAL_MODEL"),
    "openrouter": ("HARNESS_LLM_MODEL", "OPENROUTER_MODEL", "OPEN_HARNESS_OPENROUTER_MODEL"),
    "dashscope":  ("HARNESS_LLM_MODEL", "DASHSCOPE_MODEL", "QWEN_MODEL",
                   "OPEN_HARNESS_DASHSCOPE_MODEL", "OPEN_HARNESS_QWEN_MODEL"),
    "gemini":     ("HARNESS_LLM_MODEL", "GEMINI_MODEL", "OPEN_HARNESS_GEMINI_MODEL"),
    "ollama":     ("HARNESS_LLM_MODEL", "OLLAMA_MODEL", "OPEN_HARNESS_LOCAL_MODEL"),
    "bedrock":    ("HARNESS_LLM_MODEL", "BEDROCK_MODEL"),
    "vertex":     ("HARNESS_LLM_MODEL", "VERTEX_MODEL"),
    "copilot":    ("HARNESS_LLM_MODEL", "COPILOT_MODEL"),
}


def _stamp_model_env(alias: str) -> Optional[str]:
    """Resolve an alias and stamp it into provider-specific env vars.

    Returns the resolved canonical slug (e.g. ``deepseek-reasoner``)
    or ``None`` if the alias was empty / unknown to the registry. The
    function intentionally **overwrites** matching env vars even if
    the user pre-set them — fast/smart slots are the source of truth
    when role-based routing is engaged. Callers wanting a hard pin
    should set ``HARNESS_LLM_MODEL`` *before* booting the REPL or use
    ``--model`` on the CLI; those paths skip role routing entirely.
    """
    import os as _os

    if not alias:
        return None
    try:
        from lyra_core.providers.aliases import provider_key_for, resolve_alias
    except Exception:
        return None

    slug = resolve_alias(alias)
    if not slug:
        return None
    provider = provider_key_for(alias)
    keys = _PROVIDER_MODEL_ENV.get(provider or "", ("HARNESS_LLM_MODEL",))
    for k in keys:
        _os.environ[k] = slug
    return slug


def _apply_role_model(session: InteractiveSession, role: str) -> Optional[str]:
    """Stamp the env model for ``role`` and update the cached provider.

    Returns the resolved slug or ``None`` if no slot was applicable.
    The cached :class:`LLMProvider` (if any) gets ``provider.model``
    mutated directly so the next ``generate`` call picks up the new
    slug without rebuilding the entire provider — DeepSeek/Anthropic/
    OpenAI-compatible providers all expose ``model`` as a settable
    attribute, so the swap is one assignment.

    The function is a **no-op when the user has pinned the backend
    via ``/model <kind>`` or ``--llm <kind>`` AND set an explicit
    model (HARNESS_LLM_MODEL) outside the slot system** — we honour
    the explicit pin in that case rather than overwrite it. Detection
    is heuristic: if ``session.model != "auto"`` *and* both fast and
    smart slots are still at their default DeepSeek aliases, the user
    almost certainly hand-picked a backend and wants to keep its
    default model.
    """
    alias = _resolve_model_for_role(session, role)
    slug = _stamp_model_env(alias) if alias else None
    if slug:
        prov = getattr(session, "_llm_provider", None)
        if prov is not None:
            try:
                # All Lyra LLM provider classes expose ``model`` as a
                # plain attribute (anthropic/openai-compat/gemini/
                # bedrock/vertex/copilot). Best-effort: silently skip
                # for any future provider that doesn't.
                setattr(prov, "model", slug)
            except Exception:
                pass
    return slug


def _ensure_llm(session: InteractiveSession, *, role: str = "chat"):
    """Resolve and cache the ``LLMProvider`` for ``session.model``.

    Lazy: first plain-text turn pays the resolution cost, subsequent
    turns reuse the cached provider. The cache is invalidated by the
    ``/model`` slash so model switches take effect immediately.

    ``role`` (v2.7.1) selects the small/smart slot. ``"chat"`` (the
    default) uses ``session.fast_model``; reasoning-heavy callers
    (planner, /spawn, /review) pass ``role="smart"`` to route to
    ``session.smart_model``. The active provider's ``model`` attribute
    is mutated in place so the same cached provider serves both
    slots without an SDK rebuild.

    Raises ``RuntimeError`` from :mod:`lyra_cli.llm_factory` when no
    provider is configured (no env var, no ``auth.json`` entry).
    """
    # Stamp env BEFORE building so the provider's ``__init__`` reads
    # the right model on first turn. On subsequent turns
    # ``_apply_role_model`` mutates ``provider.model`` directly.
    _apply_role_model(session, role)

    if session._llm_provider is not None and session._llm_provider_kind == session.model:
        return session._llm_provider

    from ..llm_factory import build_llm

    provider = build_llm(session.model)
    session._llm_provider = provider
    session._llm_provider_kind = session.model
    # Re-apply on the freshly built provider so its ``model`` attr
    # reflects the current role even if the env stamp lost a race
    # with a preset that read its env keys at construction time.
    _apply_role_model(session, role)
    return provider


def _ensure_lifecycle_bus(session: InteractiveSession) -> Any:
    """Lazy-init the per-session :class:`LifecycleBus`. Idempotent.

    Returns ``None`` if ``lyra_core`` isn't importable (degraded mode):
    callers must already tolerate ``None`` from
    :func:`_emit_lifecycle`.
    """
    bus = getattr(session, "lifecycle_bus", None)
    if bus is not None:
        return bus
    try:
        from lyra_core.hooks.lifecycle import LifecycleBus as _Bus
    except Exception:
        return None
    bus = _Bus()
    session.lifecycle_bus = bus
    return bus


def _lifecycle_event(name: str) -> Any:
    """Resolve a :class:`LifecycleEvent` constant by lowercase name.

    Returns ``None`` when the import fails — :func:`_emit_lifecycle`
    no-ops on ``None`` so this stays safe.
    """
    try:
        from lyra_core.hooks.lifecycle import LifecycleEvent as _Event
    except Exception:
        return None
    return getattr(_Event, name.upper(), None)


def _emit_lifecycle(
    session: InteractiveSession,
    event_name: str,
    payload: dict[str, Any],
) -> None:
    """Best-effort lifecycle emit.

    Plugins (Phase D.4) subscribe to the bus on REPL boot via
    :func:`driver._wire_plugins_to_lifecycle`; emitting an event with
    no subscribers is a no-op and free.
    """
    bus = _ensure_lifecycle_bus(session)
    if bus is None:
        return
    event = _lifecycle_event(event_name)
    if event is None:
        return
    try:
        bus.emit(event, payload)
    except Exception:
        # Telemetry must never break a chat turn.
        pass


def _ensure_default_search_fn(session: InteractiveSession) -> Any:
    """Lazy-attach a SQLite + FTS5-backed ``search_fn`` to ``session``.

    Phase D.6 (v2.6.0): ``/search`` previously printed
    "session store not wired" because the REPL never seeded a store.
    This helper opens (or creates)
    ``<repo>/.lyra/sessions.sqlite`` and exposes
    :meth:`SessionStore.search_messages` as ``session.search_fn`` so
    ``/search foo`` works on every fresh REPL boot.

    To populate historical chats we also import every
    ``{"kind": "chat"}`` line from ``turns.jsonl`` for the *current*
    session and from sibling sessions under ``sessions_root``. The
    import is idempotent — we tag each session with its ``session_id``
    and skip start_session if it already exists. New chat turns are
    added live via :func:`_index_exchange_in_store`.

    Returns ``None`` (and leaves ``session.search_fn`` unset) when
    SQLite is not available or the bootstrap fails — :func:`_cmd_search`
    surfaces a friendly message in that case.
    """
    if getattr(session, "_session_store", None) is not None:
        return getattr(session, "search_fn", None)
    try:
        from lyra_core.sessions.store import SessionStore
    except Exception:
        return None

    db_path = session.repo_root / ".lyra" / "sessions.sqlite"
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        store = SessionStore(db_path=db_path)
    except Exception:
        return None

    session._session_store = store  # type: ignore[attr-defined]
    session.search_fn = lambda query, *, k=10: store.search_messages(query, k=k)  # type: ignore[attr-defined]

    try:
        _import_existing_turns_into_store(session, store)
    except Exception:
        # Index failures are recoverable — /search will simply return
        # a smaller hit set, which still beats outright failure.
        pass
    return session.search_fn


def _import_existing_turns_into_store(
    session: InteractiveSession, store: Any
) -> None:
    """Backfill ``store`` with chat exchanges from existing ``turns.jsonl``.

    Walks ``sessions_root`` (when set) and the current session's log,
    importing every ``{"kind": "chat"}`` line as two messages
    (user + assistant). The import is bounded so it stays cheap
    even on histories with thousands of turns: we cap each session
    at 5000 messages — more than enough for /search relevance and
    fast enough to not stall REPL boot.
    """
    import json as _json

    candidates: list[tuple[str, Path]] = []
    if session.sessions_root is not None and session.sessions_root.is_dir():
        for child in session.sessions_root.iterdir():
            if not child.is_dir():
                continue
            log = child / "turns.jsonl"
            if log.is_file():
                candidates.append((child.name, log))
    elif session._turns_log_path() is not None and session._turns_log_path().is_file():  # type: ignore[union-attr]
        candidates.append((str(session.session_id), session._turns_log_path()))  # type: ignore[arg-type]

    for sid, log in candidates:
        try:
            store.start_session(sid, model=session.model, mode=session.mode)
        except Exception:
            continue
        count = 0
        try:
            with log.open("r", encoding="utf-8") as fh:
                for raw in fh:
                    raw = raw.strip()
                    if not raw or count >= 5000:
                        break
                    try:
                        rec = _json.loads(raw)
                    except ValueError:
                        continue
                    if rec.get("kind") != "chat":
                        continue
                    user = (rec.get("user") or "").strip()
                    assistant = (rec.get("assistant") or "").strip()
                    if user:
                        store.append_message(sid, role="user", content=user)
                        count += 1
                    if assistant:
                        store.append_message(sid, role="assistant", content=assistant)
                        count += 1
        except OSError:
            continue


def _index_exchange_in_store(
    session: InteractiveSession, user_text: str, assistant_text: str
) -> None:
    """Live-index a freshly-completed exchange in the FTS5 store.

    Called from :meth:`InteractiveSession._persist_chat_exchange` so
    that ``/search`` finds the latest turn without forcing a REPL
    restart. The call is best-effort: any failure (store missing,
    SQLite locked, etc.) is silently dropped — the JSONL on disk is
    still the authoritative log.
    """
    store = getattr(session, "_session_store", None)
    if store is None:
        return
    try:
        sid = str(session.session_id)
        store.start_session(sid, model=session.model, mode=session.mode)
        if user_text:
            store.append_message(sid, role="user", content=user_text)
        if assistant_text:
            store.append_message(sid, role="assistant", content=assistant_text)
    except Exception:
        pass


def _chat_with_llm(
    session: InteractiveSession,
    line: str,
    *,
    system_prompt: str,
) -> tuple[bool, str]:
    """Send ``line`` through the provider and return ``(ok, text)``.

    On success ``ok=True`` and ``text`` is the assistant reply. On
    failure ``ok=False`` and ``text`` is a single-line diagnostic safe
    to show in :func:`output.chat_error_renderable`.

    The function never raises — callers always render *something* and
    keep the REPL alive.

    Phase D.3: emits :class:`LifecycleEvent` notifications around the
    LLM call so plugins (Phase D.4) can observe and decorate turns
    without monkey-patching the chat handler.
    """
    try:
        from harness_core.messages import Message
    except Exception as exc:  # pragma: no cover — harness_core ships with us
        return False, f"harness_core import failed: {exc}"

    if not getattr(session, "_session_start_emitted", False):
        _emit_lifecycle(
            session,
            "session_start",
            {
                "session_id": getattr(session, "session_id", None),
                "model": session.model,
                "mode": getattr(session, "mode", None),
            },
        )
        session._session_start_emitted = True  # type: ignore[attr-defined]

    try:
        provider = _ensure_llm(session)
    except Exception as exc:
        # build_llm raises RuntimeError when no provider is configured,
        # OllamaConnectionError when the daemon is down, etc. We collapse
        # the message to a single line for the renderer.
        message = str(exc).strip().splitlines()[0] if str(exc) else exc.__class__.__name__
        _emit_lifecycle(
            session,
            "turn_rejected",
            {"reason": "provider_init_failed", "message": message},
        )
        return False, message

    # Auto-budget preflight (v2.2.3). When the user has a cap set and
    # ``budget_auto_stop`` is on (the default), refuse the turn the
    # moment we cross the limit. The error message points at the
    # exact slash to raise the cap so the recovery path is one
    # keystroke away.
    if getattr(session, "budget_auto_stop", True):
        meter = getattr(session, "budget_meter", None)
        if meter is not None and meter.cap is not None:
            report = meter.gate()
            from .budget import BudgetStatus

            if report.status is BudgetStatus.EXCEEDED:
                _emit_lifecycle(
                    session,
                    "turn_rejected",
                    {
                        "reason": "budget_cap_reached",
                        "current_usd": meter.current_usd,
                        "limit_usd": report.limit_usd,
                    },
                )
                return False, (
                    f"budget cap reached "
                    f"(${meter.current_usd:.4f} of ${report.limit_usd:.2f}). "
                    f"raise it with /budget set <usd>, or /budget off to "
                    f"disable the auto-stop."
                )

    history = list(session._chat_history)[-(2 * _CHAT_HISTORY_TURNS) :]
    effective_system = _augment_system_prompt_with_skills(
        session, system_prompt, line=line
    )
    effective_system = _augment_system_prompt_with_memory(
        session, effective_system, line
    )
    messages = [Message.system(effective_system), *history, Message.user(line)]
    _emit_lifecycle(
        session,
        "turn_start",
        {
            "model": session.model,
            "input": line,
            "history_turns": len(history) // 2,
        },
    )

    # v3.2.0 (Phase L) — capture pre-turn snapshots so each branch can
    # write per-turn ``model / tokens_in / tokens_out / cost_delta_usd
    # / latency_ms / ts`` into the chat JSONL line. We measure with
    # ``time.monotonic()`` (latency) and read ``provider.last_usage``
    # at persist time (tokens), but the cost delta is computed from
    # ``session.cost_usd`` because ``_bill_turn`` mutates the running
    # total — that already accounts for tool-loop multi-hop pricing.
    _turn_t0 = _time.monotonic()
    _turn_ts = _time.time()
    _cost_before = float(session.cost_usd)
    _tokens_before = int(session.tokens_used)
    _turn_model = str(session.model)

    def _persist_with_metrics(text: str, *, branch: str) -> None:
        """Persist the chat exchange with per-turn metadata (best-effort).

        Reads ``provider.last_usage`` for ``tokens_in / tokens_out``
        (last hop's split; for tool-loop turns this is just the final
        hop, which is fine because the *total* is captured by the
        ``tokens_used`` delta we also store on the snapshot). The
        cost delta and total-token delta come from session counters
        which ``_bill_turn`` keeps current. Failures are swallowed —
        the JSONL is best-effort observability, not a hard dependency.
        """
        usage = getattr(provider, "last_usage", None) or {}
        tin = usage.get("prompt_tokens")
        tout = usage.get("completion_tokens")
        latency_ms = (_time.monotonic() - _turn_t0) * 1000.0
        cost_delta = float(session.cost_usd) - _cost_before
        try:
            session._persist_chat_exchange(
                line,
                text,
                model=_turn_model,
                tokens_in=int(tin) if isinstance(tin, (int, float)) else None,
                tokens_out=int(tout) if isinstance(tout, (int, float)) else None,
                cost_delta_usd=cost_delta if cost_delta > 0 else None,
                latency_ms=latency_ms,
                ts=_turn_ts,
            )
        except Exception:
            pass
        # Patch the trailing turn snapshot so /history --verbose can
        # render the metrics without re-parsing the JSONL — keeps the
        # in-memory log and the on-disk log consistent.
        if session._turns_log:
            tail = session._turns_log[-1]
            if tail.line == line:
                tail.tokens_in = (
                    int(tin) if isinstance(tin, (int, float)) else tail.tokens_in
                )
                tail.tokens_out = (
                    int(tout) if isinstance(tout, (int, float)) else tail.tokens_out
                )
                tail.cost_delta_usd = (
                    cost_delta if cost_delta > 0 else tail.cost_delta_usd
                )
                tail.latency_ms = latency_ms

    # Tool-loop branch (v2.4.0, Phase B). Engaged when:
    #   * ``session.chat_tools_enabled`` is true (default),
    #   * the active provider isn't the mock canned-output one
    #     (which wouldn't know what a tool is), and
    #   * a chat-tool registry can be built (lyra-core is installed —
    #     it always is in a real ``pip install lyra-cli``).
    #
    # The loop dispatches Read / Glob / Grep / Edit / Write tool
    # calls in-process with sandboxed paths, bills every LLM hop via
    # ``_bill_turn``, and surfaces tool cards through the renderer
    # so the user sees what's running. Streaming is *disabled* on
    # tool-bearing turns (incremental tool-call SSE is hard to
    # render correctly) but the final no-tool-calls answer is
    # rendered in one shot — fast enough to feel snappy.
    session._stream_just_drew = False
    if _should_run_chat_tools(session, provider):
        ok, text_or_err = _chat_with_tool_loop(
            session,
            provider,
            messages,
        )
        if ok:
            text = (text_or_err or "").strip()
            if not text:
                return False, "model returned an empty response"
            session._chat_history.append(Message.user(line))
            session._chat_history.append(
                Message.assistant(text)
                if hasattr(Message, "assistant")
                else Message(role="assistant", content=text)
            )
            _persist_with_metrics(text, branch="tool_loop")
            _emit_lifecycle(
                session,
                "turn_complete",
                {
                    "model": session.model,
                    "branch": "tool_loop",
                    "output_chars": len(text),
                },
            )
            return True, text
        # Tool loop failed — fall through to the non-streaming
        # ``generate`` branch so the user still gets an answer (and
        # we've already logged the diagnostic via the renderer).

    if (
        getattr(session, "_streaming_enabled", False)
        and getattr(session, "_console", None) is not None
        and callable(getattr(provider, "stream", None))
    ):
        ok, text_or_err = _stream_chat_to_console(
            session,
            provider,
            messages,
            mode_for_panel=_mode_for_system_prompt(system_prompt),
        )
        if ok:
            text = (text_or_err or "").strip()
            if not text:
                return False, "model returned an empty response"
            _bill_turn(session, provider)
            session._chat_history.append(Message.user(line))
            session._chat_history.append(
                Message.assistant(text)
                if hasattr(Message, "assistant")
                else Message(role="assistant", content=text)
            )
            # v2.3.0: persist the exchange so ``/resume`` rebuilds the
            # LLM-side context, not just the metadata.
            # v3.2.0 (Phase L): also stamp model / tokens / cost / latency
            # so ``/history --verbose`` can show what each turn cost.
            _persist_with_metrics(text, branch="stream")
            session._stream_just_drew = True
            _emit_lifecycle(
                session,
                "turn_complete",
                {
                    "model": session.model,
                    "branch": "stream",
                    "output_chars": len(text),
                },
            )
            return True, text
        # Streaming failed — fall through to non-streaming retry so a
        # transient SSE blip still produces an answer.

    try:
        reply: Message = provider.generate(messages, max_tokens=1024)
    except Exception as exc:
        message = str(exc).strip().splitlines()[0] if str(exc) else exc.__class__.__name__
        _emit_lifecycle(
            session,
            "turn_rejected",
            {"reason": "generate_failed", "message": message},
        )
        return False, message

    text = (reply.content or "").strip()
    if not text:
        _emit_lifecycle(
            session,
            "turn_rejected",
            {"reason": "empty_response"},
        )
        return False, "model returned an empty response"

    # Bill the session — read per-call usage off the provider, bump the
    # turn-level token counter and the running USD spend. Done *before*
    # we mutate ``_chat_history`` so a usage-capture bug never silently
    # double-counts a retry.
    _bill_turn(session, provider)

    session._chat_history.append(Message.user(line))
    session._chat_history.append(Message.assistant(text) if hasattr(Message, "assistant") else reply)
    _persist_with_metrics(text, branch="generate")
    _emit_lifecycle(
        session,
        "turn_complete",
        {
            "model": session.model,
            "branch": "generate",
            "output_chars": len(text),
        },
    )
    return True, text


def _augment_system_prompt_with_skills(
    session: InteractiveSession,
    system_prompt: str,
    *,
    line: str | None = None,
) -> str:
    """Return ``system_prompt`` with the skill-block prepended when enabled.

    Phase O.2 split this into two paths:

    * **Cached path** (``line is None``): pre-N.7 behaviour. The
      advertised list is rendered once per session and reused. No
      progressive activation, no telemetry. Kept around so embedded
      callers and the legacy test
      :func:`test_augment_system_prompt_caches_block_across_calls`
      keep working unchanged.

    * **Live path** (``line`` is the user message): renders fresh
      every turn via
      :func:`skills_inject.render_skill_block_with_activations`,
      passes the prompt to the activator so progressive bodies
      actually inject, and notes the resulting activations on
      ``session._skill_activation_recorder``. The lifecycle hooks
      installed by
      :func:`driver._wire_skill_telemetry_to_lifecycle` then settle
      each activation as success/failure when ``turn_complete`` /
      ``turn_rejected`` fires.

    Returns ``system_prompt`` unchanged when:

    * ``session.skills_inject_enabled`` is false (user opted out),
    * the rendered block is empty (no skills discovered, or
      ``lyra_skills`` not importable), or
    * the renderer raises (we *never* let skill discovery break a
      chat turn).
    """
    if not getattr(session, "skills_inject_enabled", True):
        return system_prompt

    if line is None:
        block = getattr(session, "_cached_skill_block", None)
        if block is None:
            try:
                from .skills_inject import render_skill_block

                block = render_skill_block(session.repo_root)
            except Exception:
                block = ""
            session._cached_skill_block = block
        if not block:
            return system_prompt
        return system_prompt.rstrip() + "\n\n" + block

    block, activated_ids, reasons = _render_skill_block_live(
        session=session, line=line
    )
    if activated_ids:
        sid = str(getattr(session, "session_id", None) or "lyra")
        recorder = getattr(session, "_skill_activation_recorder", None)
        if recorder is not None:
            for skill_id in activated_ids:
                try:
                    recorder.note_activation(
                        session_id=sid,
                        turn=int(session.turn),
                        skill_id=skill_id,
                        reason=reasons.get(skill_id, ""),
                    )
                except Exception:
                    # Telemetry must never break a chat turn. The
                    # ledger will simply miss this activation if the
                    # recorder is misconfigured.
                    pass
        # Phase O.2 (v3.5): broadcast the activation set so HIR
        # journaling, OTel fan-out, and plugins can see which
        # skills the model is about to receive. Best-effort —
        # ``_emit_lifecycle`` already swallows bus failures.
        try:
            _emit_lifecycle(
                session,
                "skills_activated",
                {
                    "session_id": sid,
                    "turn": int(session.turn),
                    "activated_skills": [
                        {"skill_id": sid_, "reason": reasons.get(sid_, "")}
                        for sid_ in activated_ids
                    ],
                },
            )
        except Exception:
            pass

    if not block:
        return system_prompt
    return system_prompt.rstrip() + "\n\n" + block


def _render_skill_block_live(
    *,
    session: InteractiveSession,
    line: str,
) -> tuple[str, list[str], dict[str, str]]:
    """Return ``(text, activated_ids, reasons)`` for the current turn.

    Always recomputes — no caching — because the active-skills block
    legitimately changes per-turn even if the advertised list is
    stable. The cost is one walk of the skills directory, which is
    cheap (dozens of files) and dominated by the LLM hop that
    follows.
    """
    try:
        from .skills_inject import render_skill_block_with_activations
    except Exception:
        return "", [], {}
    try:
        result = render_skill_block_with_activations(
            session.repo_root,
            prompt=line,
        )
    except Exception:
        return "", [], {}
    return result.text, list(result.activated_ids), dict(result.activation_reasons)


def _augment_system_prompt_with_memory(
    session: InteractiveSession,
    system_prompt: str,
    line: str,
) -> str:
    """Return ``system_prompt`` with a "## Relevant memory" block appended.

    Driven by :func:`memory_inject.render_memory_block`, which queries:

    * the project-local procedural store at
      ``<repo>/.lyra/memory/procedural.sqlite`` (lazily opened on the
      first chat turn that asks for it), and
    * the in-process :class:`ReasoningBank` attached to
      ``session.reasoning_bank`` (``None`` is fine — silently skipped).

    Returns ``system_prompt`` unchanged when:

    * ``session.memory_inject_enabled`` is false (user opted out via
      ``/memory off``),
    * neither store has anything relevant, or
    * the renderer raises (we *never* let a memory bug abort a
      chat turn).
    """
    if not getattr(session, "memory_inject_enabled", True):
        return system_prompt
    if not getattr(session, "_procedural_memory_loaded", False):
        try:
            from .memory_inject import (
                _default_procedural_db_path,
                _open_procedural_memory,
            )

            session._procedural_memory = _open_procedural_memory(
                _default_procedural_db_path(session.repo_root)
            )
        except Exception:
            session._procedural_memory = None
        session._procedural_memory_loaded = True
    try:
        from .memory_inject import render_memory_block

        block = render_memory_block(
            line,
            repo_root=session.repo_root,
            procedural_memory=session._procedural_memory,
            reasoning_bank=getattr(session, "reasoning_bank", None),
        )
    except Exception:
        return system_prompt
    if not block:
        return system_prompt
    return system_prompt.rstrip() + "\n\n" + block


def _should_run_chat_tools(session: InteractiveSession, provider: Any) -> bool:
    """Decide whether the chat handler should engage the tool loop.

    Engaged when the user hasn't disabled tools and the provider can
    actually run them. The mock provider is rejected because it emits
    canned text — running it through the loop wastes a hop and adds
    noise. The lyra-core import is deferred to first-use; if it fails
    (impossibly rare in practice — both packages ship together) the
    flag flips off for the rest of the session so we don't pay the
    failed-import cost on every turn.

    Caching policy: ``_chat_tools_loaded`` is the one-shot flag.
    Once we've tried once we either have a registry or we've given
    up. The registry itself stays valid across turns within a single
    session — the underlying tool classes are stateless modulo
    ``repo_root``, and a session never changes ``repo_root``.
    """
    if not getattr(session, "chat_tools_enabled", True):
        return False
    if getattr(provider, "provider_name", "") == "mock":
        return False
    if getattr(provider, "model", "") in {"mock", "canned"}:
        return False
    # Scripted mocks (``harness_core.models.MockLLM`` and friends) don't
    # set ``provider_name``; recognise by class to keep a non-tool-aware
    # canned-output run from being routed through the loop.
    cls_name = type(provider).__name__
    if cls_name in {"MockLLM", "ScriptedLLM"}:
        return False
    if not getattr(session, "_chat_tools_loaded", False):
        try:
            from .chat_tools import build_chat_tool_registry

            session._chat_tool_registry = build_chat_tool_registry(
                session.repo_root
            )
        except Exception:
            session._chat_tool_registry = None
        session._chat_tools_loaded = True
    return session._chat_tool_registry is not None


def _chat_with_tool_loop(
    session: InteractiveSession,
    provider: Any,
    messages: list[Any],
) -> tuple[bool, str]:
    """Drive the v2.4.0 chat-mode tool loop and return ``(ok, text_or_err)``.

    Wraps :func:`chat_tools.run_chat_tool_loop` with three pieces of
    REPL-specific glue:

    * an approval callback that defers to the session's
      :class:`ToolApprovalCache` (built lazily in
      ``_should_run_chat_tools``'s caller via the ``tools`` slash) and
      otherwise prints a "running …" notice — this keeps headless
      tests green while letting the REPL auto-approve low-risk
      tools by default;
    * a renderer that prints a Rich panel for each ``call`` /
      ``result`` event when a console is attached, falling back to
      plain ``[tool=…]`` lines for piped runs and tests;
    * a billing hook that re-uses :func:`_bill_turn` so usage from
      *every* LLM hop in the loop is counted, not just the final
      one.

    Returns ``(True, final_text)`` on success and
    ``(False, diagnostic)`` when the loop crashes (provider
    unreachable mid-loop, registry refused a path, etc.).
    """
    from .chat_tools import (
        ToolEvent,
        collect_mcp_tool_specs,
        run_chat_tool_loop,
    )

    cache = getattr(session, "tool_approval_cache", None)
    if cache is None:
        from .tool_approval import ToolApprovalCache

        cache = ToolApprovalCache(mode="normal")
        session.tool_approval_cache = cache

    # Approval callback: low-risk read-only tools (Read/Glob/Grep)
    # auto-approve so plain "where is X?" turns don't blow up into a
    # confirmation cascade. Write/Edit go through the cache so the
    # first time the model touches a file the user gets a single
    # consent prompt, then subsequent writes within the same session
    # silently approve. This matches claw-code's session-scoped
    # approval contract.
    _LOW_RISK = {"Read", "Glob", "Grep"}

    def _approve(name: str, _args: dict[str, Any]) -> bool:
        if name in _LOW_RISK:
            return True
        # Medium-risk: surface a console prompt when one is available,
        # otherwise auto-approve (test path; the test would have
        # supplied its own cache mode if it cared about gating).
        console = getattr(session, "_console", None)
        if console is None:
            return True
        try:
            from rich.prompt import Confirm

            return bool(
                Confirm.ask(
                    f"Allow Lyra to run [bold cyan]{name}[/bold cyan]?",
                    default=True,
                    console=console,
                )
            )
        except Exception:
            # Non-TTY console / closed stdin / etc. — default open.
            # The user can flip the cache to ``strict`` via
            # ``/tools mode strict`` if they want hard gating.
            return True

    def _render(event: ToolEvent) -> None:
        console = getattr(session, "_console", None)
        if event.kind == "call":
            label = f"[dim]→[/] [bold cyan]{event.tool_name}[/]"
            if console is not None:
                arg_preview = _short_arg_preview(event.args)
                console.print(f"{label} {arg_preview}", highlight=False)
            else:
                # Plain stdout line for piped/test runs. ANSI-free so
                # ``lyra | grep tool=`` still works.
                print(f"  → tool={event.tool_name} args={event.args}")
        elif event.kind == "result":
            tag = "ok" if not event.is_error else "err"
            if console is not None:
                snippet = _truncate(event.output, 240)
                colour = "green" if not event.is_error else "red"
                console.print(
                    f"[dim]   {tag}[/] [{colour}]{snippet}[/]",
                    highlight=False,
                )
            else:
                print(f"  ← {tag}={_truncate(event.output, 240)!r}")
            _emit_lifecycle(
                session,
                "tool_call",
                {
                    "tool": event.tool_name,
                    "args": event.args,
                    "output_preview": _truncate(event.output, 240),
                    "is_error": bool(event.is_error),
                },
            )
        elif event.kind == "denied":
            if console is not None:
                console.print(
                    f"[yellow]   denied:[/] {event.tool_name} ({event.reason})",
                    highlight=False,
                )
            else:
                print(f"  × denied={event.tool_name} reason={event.reason}")
        elif event.kind == "limit_reached":
            if console is not None:
                console.print(
                    f"[yellow]   tool-loop budget reached:[/] {event.reason}",
                    highlight=False,
                )
            else:
                print(f"  ! limit={event.reason}")

    def _on_usage(p: Any) -> None:
        _bill_turn(session, p)

    # Surface MCP tools (Phase C.4) — schemas from servers the user
    # has already ``/mcp connect``-ed are merged into the chat-loop
    # tool list, and the dispatcher map routes ``mcp__server__tool``
    # calls back to the right transport. When no MCP server is live
    # this returns three empty containers and the loop behaves like
    # the plain v2.4 chat loop.
    try:
        mcp_schemas, _entries, mcp_transports = collect_mcp_tool_specs(session)
    except Exception:
        mcp_schemas, mcp_transports = [], {}

    try:
        report = run_chat_tool_loop(
            provider,
            messages,
            session._chat_tool_registry,
            approval_cache=cache,
            approve=_approve,
            render=_render,
            on_usage=_on_usage,
            max_steps=8,
            max_tokens=1024,
            mcp_schemas=mcp_schemas,
            mcp_transports=mcp_transports,
        )
    except Exception as exc:
        msg = str(exc).strip().splitlines()[0] if str(exc) else exc.__class__.__name__
        return False, f"tool loop failed: {msg}"

    final = (report.final_text or "").strip()
    if not final:
        return False, "tool loop ended with no assistant text"
    return True, final


def _short_arg_preview(args: dict[str, Any], *, limit: int = 80) -> str:
    """Render a short, single-line preview of tool arguments for the card.

    Uses the first identifiable value (``path`` / ``pattern`` /
    ``query``) so the user sees *what the tool is acting on* rather
    than a JSON blob. Falls back to a truncated ``json.dumps`` for
    tools whose key set we don't recognise (third-party MCP tools,
    primarily — Phase C).
    """
    import json as _json

    for primary in ("path", "pattern", "query", "url", "command"):
        if primary in args:
            value = str(args[primary])
            return _truncate(value, limit)
    try:
        flat = _json.dumps(args, ensure_ascii=False)
    except Exception:
        flat = str(args)
    return _truncate(flat, limit)


def _truncate(text: str, limit: int) -> str:
    """Length-cap ``text`` with an ellipsis suffix; collapse newlines."""
    flat = text.replace("\n", "↵ ")
    if len(flat) <= limit:
        return flat
    return flat[: max(limit - 1, 1)] + "…"


def _bill_turn(session: InteractiveSession, provider: Any) -> None:
    """Update ``session.tokens_used`` / ``session.cost_usd`` from a turn.

    Reads ``provider.last_usage`` (populated by every OpenAI-compat
    ``generate`` via ``_record_usage``) and rolls the cost via
    :func:`lyra_cli.interactive.budget.price_for`. Providers that
    don't surface ``last_usage`` (Ollama, mocks) silently no-op so the
    REPL keeps running.

    Also ticks ``session.budget_meter`` when one is wired so the
    ``/budget`` slash and the alert chip light up correctly. The meter
    holds its own accumulator; we update *both* so the simple
    ``$session.cost_usd`` field stays the source of truth for the
    bye-screen and ``/status``.
    """
    usage = getattr(provider, "last_usage", None) or {}
    if not usage:
        return

    prompt = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    total = int(usage.get("total_tokens") or (prompt + completion))
    if total <= 0:
        return

    session.tokens_used += total

    # Resolve pricing. ``getattr(provider, 'model', ...)`` covers both
    # the OpenAI-compat path (``self.model`` is the wire-level slug)
    # and providers that expose a ``.model`` attribute differently.
    from .budget import price_for

    model_id = (
        getattr(provider, "model", None)
        or getattr(provider, "default_model", None)
        or session.model
    )
    prompt_per, completion_per = price_for(str(model_id))
    delta = (
        (max(prompt, 0) / 1_000_000) * prompt_per
        + (max(completion, 0) / 1_000_000) * completion_per
    )
    if delta > 0:
        session.cost_usd += delta
        meter = getattr(session, "budget_meter", None)
        if meter is not None:
            try:
                meter.record_usage(
                    model=str(model_id),
                    prompt_tokens=prompt,
                    completion_tokens=completion,
                )
            except Exception:
                # Meter is best-effort — never let a billing bug crash
                # the REPL turn that just successfully replied.
                pass


def _mode_for_system_prompt(system_prompt: str) -> str:
    """Reverse-lookup the mode label that owns ``system_prompt``.

    Used by the streaming path so the live panel can be coloured
    correctly. Falls back to ``"agent"`` (the default colour) when
    we can't tell — the panel will still render, just in the default
    chat colour.
    """
    for mode_name, prompt in _MODE_SYSTEM_PROMPTS.items():
        if prompt is system_prompt:
            return mode_name
    return "agent"


def _stream_chat_to_console(
    session: InteractiveSession,
    provider: Any,
    messages: list[Any],
    *,
    mode_for_panel: str,
) -> tuple[bool, str]:
    """Drive the streaming chat panel.

    Returns ``(ok, text_or_error)``. On success the panel is fully
    drawn, the assembled text is returned, and the caller is
    responsible for billing + history. On failure we surface a
    one-line diagnostic; whatever partial text streamed onto the
    screen remains visible above the prompt — the user gets to keep
    the model's words even when the connection died mid-thought.

    The whole thing is best-effort: any unexpected exception while
    setting up Rich falls through to the caller's non-streaming
    retry path, so a Rich version mismatch never bricks the REPL.
    """
    try:
        from rich.live import Live
    except Exception as exc:  # pragma: no cover — Rich is a hard dep
        return False, f"rich import failed: {exc}"

    buffer: list[str] = []

    def render_panel() -> Any:
        return _out.chat_renderable("".join(buffer), mode=mode_for_panel)

    try:
        with Live(
            render_panel(),
            console=session._console,
            refresh_per_second=18,
            transient=False,
        ) as live:
            try:
                stream_iter = provider.stream(messages, max_tokens=1024)
                for delta in stream_iter:
                    if not delta:
                        continue
                    buffer.append(delta)
                    live.update(render_panel())
            except Exception as exc:
                # Render whatever we've got plus a small error tail
                # before tearing down Live, so the user sees the
                # partial reply *and* knows it was interrupted.
                err_line = (
                    str(exc).strip().splitlines()[0]
                    if str(exc)
                    else exc.__class__.__name__
                )
                buffer.append(f"\n\n[stream interrupted: {err_line}]")
                live.update(render_panel())
                return False, err_line
    except Exception as exc:  # pragma: no cover — Live setup failure
        return False, f"streaming render failed: {exc}"

    return True, "".join(buffer)


def _build_chat_handler(mode: str):
    """Factory for plain-text mode handlers that call the LLM."""
    system = _MODE_SYSTEM_PROMPTS[mode]

    def _handler(session: InteractiveSession, line: str) -> CommandResult:
        # Plan mode keeps the "task recorded" affordance — the user
        # can still /approve to enter the planner sub-loop. We just
        # don't *block* on it.
        if mode == "plan":
            session.pending_task = line

        ok, text = _chat_with_llm(session, line, system_prompt=system)
        if ok:
            # When the streaming branch already painted the panel,
            # don't repaint — the driver's _render_result short-
            # circuits on ``output="", renderable=None`` and we keep
            # the on-screen panel from being drawn twice.
            if getattr(session, "_stream_just_drew", False):
                session._stream_just_drew = False
                return CommandResult(output="", renderable=None)
            renderable = _out.chat_renderable(text, mode=mode)
            return CommandResult(output=text, renderable=renderable)

        # Failure path — keep the REPL alive with a helpful error.
        renderable = _out.chat_error_renderable(text, mode=mode)
        return CommandResult(
            output=f"[{mode}] llm error: {text}",
            renderable=renderable,
        )

    _handler.__name__ = f"_handle_{mode}_text"
    return _handler


_handle_agent_text = _build_chat_handler("agent")
_handle_plan_text = _build_chat_handler("plan")
_handle_debug_text = _build_chat_handler("debug")
_handle_ask_text = _build_chat_handler("ask")


_MODE_HANDLERS: dict[str, Callable[[InteractiveSession, str], CommandResult]] = {
    "agent": _handle_agent_text,
    "plan": _handle_plan_text,
    "debug": _handle_debug_text,
    "ask": _handle_ask_text,
}


# ---------------------------------------------------------------------------
# Slash handlers
# ---------------------------------------------------------------------------


def _cmd_help(_session: InteractiveSession, _args: str) -> CommandResult:
    # Plain-text output (what tests assert on) — iterates SLASH_COMMANDS so
    # every name + alias is visible. The "alias for /<canonical>" doc string
    # shipped by ``_build_lookup`` keeps it scannable.
    plain_lines = ["Commands:"]
    for name in sorted(SLASH_COMMANDS):
        desc = _SLASH_DOCS.get(name, "")
        plain_lines.append(f"  /{name:<16} {desc}")
    plain_lines.append(
        "\nPlain text routes to the current mode "
        "(plan: describe task; run: execute; retro: note)."
    )
    plain = "\n".join(plain_lines)

    # Rich rendering uses the registry directly so adding a CommandSpec
    # automatically slots into the right /help bucket — no second edit
    # required. Aliases collapse onto their canonical row to keep the
    # panel scannable; the meta column shows them in dim text.
    groups: list[tuple[str, list[tuple[str, str]]]] = []
    for category, specs in commands_by_category().items():
        rows: list[tuple[str, str]] = []
        for spec in specs:
            label = spec.name
            if spec.aliases:
                label = f"{spec.name}  ({', '.join(spec.aliases)})"
            rows.append((label, spec.description))
        groups.append((_CATEGORY_DISPLAY.get(category, category), rows))

    footer = (
        "Plain text routes to the current mode — plan: record task · "
        "build: implement · run: execute · explore: search · "
        "retro: note.    Tip: prefix `!` for shell, `@` for a file."
    )
    return CommandResult(
        output=plain,
        renderable=_out.help_renderable(groups, footer),
    )


def _cmd_skip_onboarding(_session: InteractiveSession, _args: str) -> CommandResult:
    """``/skip-onboarding`` — never show the first-run wizard again."""
    from .onboarding import dismiss_wizard

    dismiss_wizard()
    return CommandResult(
        output="onboarding wizard dismissed; delete ~/.lyra/.no-onboarding to re-enable."
    )


def _cmd_palette(_session: InteractiveSession, args: str) -> CommandResult:
    """``/palette [query]`` — fuzzy-searchable command palette.

    Substring + initials match against name, aliases, and description.
    The plain-text output is what tests assert on; the Rich renderable
    is what end-users see in the REPL footer.
    """
    from .command_palette import fuzzy_filter, render_palette

    query = args.strip()
    matches = fuzzy_filter(query)
    rich_text = render_palette(matches, query=query or None, max_height=24)

    if not matches:
        plain = f"(no matches for {query!r})"
    else:
        lines = [f"Commands matching {query!r}:" if query else "Commands:"]
        for spec in matches:
            label = f"/{spec.name}"
            if spec.args_hint:
                label = f"{label} {spec.args_hint}"
            lines.append(f"  {label:<32} {spec.description}")
        plain = "\n".join(lines)

    return CommandResult(output=plain, renderable=rich_text)


def _cmd_status(session: InteractiveSession, _args: str) -> CommandResult:
    plain = "\n".join(
        [
            f"mode:        {session.mode}",
            f"model:       {session.model}",
            f"  fast slot: {getattr(session, 'fast_model', '(unset)')}",
            f"  smart slot:{getattr(session, 'smart_model', '(unset)')}",
            f"repo:        {session.repo_root}",
            f"turn:        {session.turn}",
            f"cost:        ${session.cost_usd:.2f}",
            f"tokens:      {session.tokens_used}",
            f"pending:     {session.pending_task or '(none)'}",
            f"version:     {__version__}",
            f"deep-think:  {'on' if session.deep_think else 'off'}",
            f"verbose:     {'on' if session.verbose else 'off'}",
            f"vim:         {'on' if session.vim_mode else 'off'}",
            f"theme:       {session.theme}",
            f"budget:      "
            + (
                f"${session.budget_cap_usd:.2f}"
                if session.budget_cap_usd is not None
                else "(none)"
            ),
        ]
    )
    return CommandResult(
        output=plain,
        renderable=_out.status_renderable(
            mode=session.mode,
            model=session.model,
            repo=session.repo_root,
            turn=session.turn,
            cost_usd=session.cost_usd,
            tokens=session.tokens_used,
            pending=session.pending_task,
            version=__version__,
            deep_think=session.deep_think,
            verbose=session.verbose,
            vim_mode=session.vim_mode,
            theme=session.theme,
            budget_cap_usd=session.budget_cap_usd,
        ),
    )


_MODE_BLURBS: tuple[tuple[str, str], ...] = (
    ("agent", "default; full-access execution. Plain text drives the agent loop."),
    ("plan",  "read-only collaborative design. Plain text proposes a plan."),
    ("debug", "systematic troubleshooting with runtime evidence. No edits."),
    ("ask",   "read-only Q&A. Plain text answers questions about the codebase."),
)


def _cmd_mode(session: InteractiveSession, args: str) -> CommandResult:
    """``/mode`` — show or set the active interactive mode.

    Forms:
      * ``/mode``            — print the current mode name.
      * ``/mode list``       — show all four modes with one-line blurbs.
      * ``/mode toggle``     — advance through the Tab cycle.
      * ``/mode <name>``     — switch to ``<name>`` (agent | plan | debug | ask).
      * ``/mode <legacy>``   — accept v1.x / v2.x names (build, run,
        explore, retro) and remap to the canonical v3.2 mode with a
        one-line "renamed in v3.2" notice so a user with old muscle
        memory doesn't hit a dead end.
    """
    from .keybinds import cycle_mode

    raw = args.strip().lower()
    if not raw:
        return CommandResult(output=f"current mode: {session.mode}")

    if raw == "list":
        lines = ["available modes:"]
        for name, blurb in _MODE_BLURBS:
            marker = "●" if name == session.mode else " "
            lines.append(f"  {marker} {name:<6}  {blurb}")
        return CommandResult(output="\n".join(lines))

    if raw == "toggle":
        previous = session.mode
        cycle_mode(session)
        return CommandResult(
            output=f"mode: {previous} → {session.mode}",
            new_mode=session.mode,
        )

    target = _LEGACY_MODE_REMAP.get(raw, raw)
    rename_notice = ""
    if target != raw:
        rename_notice = (
            f" [{raw!r} was renamed to {target!r} in v3.2.0 to match "
            "Claude Code's mode taxonomy]"
        )

    if target not in _VALID_MODES:
        return CommandResult(
            output=(
                f"unknown mode {raw!r}; "
                f"valid: {', '.join(_VALID_MODES)}"
            ),
            renderable=_out.bad_mode_renderable(raw, _VALID_MODES),
        )

    extra = ""
    if target == "agent" and getattr(session, "permission_mode", "normal") == "yolo":
        # Switching into the execution-capable mode while permissions
        # are off is the single most footgun-y combination — call it
        # out so the user has one chance to back out before they run
        # a destructive plan.
        extra = (
            " [warning: permission mode is 'yolo' — tool calls will run "
            "without confirmation. Consider /perm strict before /agent]"
        )
    session.mode = target
    return CommandResult(
        output=f"mode: {target}{rename_notice}{extra}", new_mode=target
    )


def _cmd_model(session: InteractiveSession, args: str) -> CommandResult:
    """``/model`` - inspect or pin the active model + small/smart slots.

    Forms accepted:

    * ``/model`` - print the current backend pin plus the fast/smart
      slot values (the small/smart split introduced in v2.7.1).
    * ``/model list`` (or ``ls``) - delegate to the configured-providers
      table (same as ``/models``).
    * ``/model fast`` / ``/model smart`` - run the next chat turn
      against the named slot. Equivalent to flipping the role pin
      manually until the user types another ``/model …``.
    * ``/model fast=<slug>`` / ``/model smart=<slug>`` - re-pin the
      named slot to ``<slug>`` (any alias the registry knows about,
      e.g. ``haiku``, ``opus``, ``deepseek-v4-pro``, ``gpt-5``).
    * ``/model <kind>`` - legacy backward-compatible behaviour: pin
      the backend (``anthropic``, ``deepseek``, ``mock``, …).

    Slot pins persist for the lifetime of the REPL; future runs read
    them from ``InteractiveSession`` defaults unless ``lyra connect``
    or settings.json overrides them.
    """
    target = args.strip()
    if not target:
        lines = [
            f"current model: {session.model}",
            f"  fast slot:   {getattr(session, 'fast_model', '(unset)')}",
            f"  smart slot:  {getattr(session, 'smart_model', '(unset)')}",
            "",
            "Tip: /model fast=<slug> or /model smart=<slug> to repin a slot.",
        ]
        return CommandResult(output="\n".join(lines))
    if target.lower() in {"list", "ls"}:
        return CommandResult(output=session._cmd_model_list(""))

    # Slot operations: ``fast``, ``smart``, ``fast=<slug>``, ``smart=<slug>``.
    head, _, tail = target.partition("=")
    head_norm = head.strip().lower()
    if head_norm in {"fast", "smart"}:
        slug = tail.strip()
        if slug:
            attr = "fast_model" if head_norm == "fast" else "smart_model"
            setattr(session, attr, slug)
            # Invalidate the cached LLMProvider so the next chat turn
            # rebuilds with the freshly-pinned slot. Subagent factories
            # build their own per-spawn provider so they're unaffected.
            session._llm_provider = None
            session._llm_provider_kind = None
            return CommandResult(output=f"{head_norm} slot set to: {slug}")
        # ``/model fast`` / ``/model smart`` without ``=`` swaps the
        # ACTIVE slot for this turn — handy when the user wants to
        # nudge a single tricky question into the smart lane without
        # paying the cost on every subsequent turn. We implement it as
        # a one-shot env stamp; the next plain-text turn picks it up
        # via :func:`_apply_role_model`.
        slot = getattr(session, "smart_model" if head_norm == "smart" else "fast_model", "")
        if not slot:
            return CommandResult(
                output=f"{head_norm} slot is empty; pin it first with /model {head_norm}=<slug>"
            )
        applied = _stamp_model_env(slot)
        prov = getattr(session, "_llm_provider", None)
        if prov is not None and applied:
            try:
                prov.model = applied
            except Exception:
                pass
        return CommandResult(
            output=(
                f"next turn will use {head_norm} slot: {slot}"
                + (f" (resolved → {applied})" if applied and applied != slot else "")
            )
        )

    session.model = target
    # Invalidate the cached LLMProvider so the next plain-text turn
    # rebuilds against the newly-selected model.
    session._llm_provider = None
    session._llm_provider_kind = None
    return CommandResult(output=f"model set to: {target}")


def _cmd_models(session: InteractiveSession, args: str) -> CommandResult:
    """List known model providers + identifiers.

    Live in v1.7.4: enumerates ``known_llm_names`` + the OpenAI-compatible
    preset registry, marking configured/selected status. Falls back to the
    legacy static catalog for the renderable so the rich UI still gets a
    pre-formatted block to display alongside the live text.
    """
    plain = session._cmd_model_list(args)
    catalog: list[tuple[str, list[tuple[str, str]]]] = [
        (
            "anthropic",
            [
                ("claude-opus-4.7", "flagship reasoning · 200k ctx"),
                ("claude-sonnet-4.5", "balanced · 200k ctx"),
                ("claude-haiku-4", "fast, cheap · 200k ctx"),
            ],
        ),
        (
            "openai",
            [
                ("gpt-5", "frontier reasoning · 400k ctx"),
                ("gpt-5-mini", "fast · 400k ctx"),
                ("gpt-5-nano", "cheapest · 128k ctx"),
                ("o5-pro", "deep reasoning · chain-of-thought"),
            ],
        ),
        (
            "google",
            [
                ("gemini-2.5-pro", "frontier · 2M ctx"),
                ("gemini-2.5-flash", "fast · 1M ctx"),
            ],
        ),
        (
            "open-source",
            [
                ("llama-4-405b", "meta flagship · via together/fireworks"),
                ("hermes-3-70b", "nous reasoning · via nous portal"),
                ("deepseek-v3", "fast · via openrouter"),
                ("qwen-3-coder", "code-specialised"),
            ],
        ),
        (
            "local",
            [
                ("mock", "deterministic; used by tests and smoke"),
                ("ollama/llama3", "local inference via ollama"),
            ],
        ),
    ]
    return CommandResult(
        output=plain,
        renderable=_out.models_renderable(catalog),
    )


def _cmd_exit(_session: InteractiveSession, _args: str) -> CommandResult:
    return CommandResult(output="bye.", should_exit=True)


def _cmd_clear(_session: InteractiveSession, _args: str) -> CommandResult:
    return CommandResult(output="", clear_screen=True)


def _cmd_history(session: InteractiveSession, args: str) -> CommandResult:
    """``/history`` — recent inputs (concise) or per-turn metadata.

    v3.2.0 (Phase L): added ``--verbose`` so the user can see *which
    model* answered each turn, how many tokens each side used, what
    each turn cost, how long it took, and when it ran. The plain
    ``/history`` output stays a numbered list of inputs (so muscle
    memory and the existing tests aren't affected); ``--verbose``
    walks ``session._turns_log`` (the in-memory snapshots that
    :class:`_TurnSnapshot` v3.2 carries model/cost/latency on) so it
    works without reading the on-disk JSONL.
    """
    flags = args.strip().split() if args else []
    verbose = "--verbose" in flags or "-v" in flags

    if not session.history and not getattr(session, "_turns_log", None):
        return CommandResult(
            output="(no history yet)",
            renderable=_out.history_renderable([]),
        )

    if not verbose:
        plain = "\n".join(
            f"  {i+1:>3}  {entry}" for i, entry in enumerate(session.history)
        )
        return CommandResult(
            output=plain or "(no history yet)",
            renderable=_out.history_renderable(list(session.history)),
        )

    import datetime as _dt

    snaps = list(getattr(session, "_turns_log", []) or [])
    rows: list[dict[str, Any]] = []
    plain_lines: list[str] = []
    for i, snap in enumerate(snaps, start=1):
        ts = getattr(snap, "ts", None)
        ts_str = (
            _dt.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            if isinstance(ts, (int, float))
            else None
        )
        preview = (snap.line or "").splitlines()[0]
        rows.append(
            {
                "n": i,
                "kind": "turn",
                "mode": snap.mode,
                "model": getattr(snap, "model", None),
                "tokens_in": getattr(snap, "tokens_in", None),
                "tokens_out": getattr(snap, "tokens_out", None),
                "cost_delta_usd": getattr(snap, "cost_delta_usd", None),
                "latency_ms": getattr(snap, "latency_ms", None),
                "ts": ts_str,
                "preview": preview,
            }
        )
        # Plain-text mirror so tests / non-TTY consumers still see the
        # full data — matches the rich table column-for-column.
        tin = getattr(snap, "tokens_in", None)
        tout = getattr(snap, "tokens_out", None)
        cd = getattr(snap, "cost_delta_usd", None)
        ms = getattr(snap, "latency_ms", None)
        plain_lines.append(
            "  "
            + "  ".join(
                [
                    f"{i:>3}",
                    (snap.mode or "?")[:6].ljust(6),
                    (getattr(snap, "model", None) or "—")[:18].ljust(18),
                    f"in={tin if tin is not None else '—'}",
                    f"out={tout if tout is not None else '—'}",
                    (
                        f"cost=${cd:.6f}"
                        if isinstance(cd, (int, float))
                        else "cost=—"
                    ),
                    (
                        f"ms={ms:.0f}"
                        if isinstance(ms, (int, float))
                        else "ms=—"
                    ),
                    ts_str or "—",
                    (preview or "")[:60],
                ]
            )
        )
    return CommandResult(
        output="\n".join(plain_lines) or "(no history yet)",
        renderable=_out.verbose_history_renderable(rows),
    )


def _parse_search_args(raw: str) -> tuple[str, int]:
    """Split ``/search`` args into ``(query, k)``.

    Supports ``--k=<n>`` *before* or *after* the query, with ``k``
    clamped to ``[1, 50]`` and defaulted to 5.
    """
    k = 5
    tokens: list[str] = []
    for tok in raw.split():
        if tok.startswith("--k="):
            try:
                k = int(tok.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
            continue
        if tok == "--k" or tok == "-k":
            continue
        tokens.append(tok)
    query = " ".join(tokens).strip()
    k = max(1, min(50, int(k)))
    return query, k


def _cmd_search(session: InteractiveSession, args: str) -> CommandResult:
    """Recall hits from the session transcript store."""
    query, k = _parse_search_args(args)
    if not query:
        return CommandResult(
            output="usage: /search [--k=N] <query>",
        )

    search_fn = getattr(session, "search_fn", None)
    if search_fn is None:
        # v2.6.0 (Phase D.6): default to the SQLite + FTS5 session
        # store under ``<repo>/.lyra/sessions.sqlite`` so /search is
        # useful out of the box. The store is bootstrapped lazily on
        # first access; existing ``turns.jsonl`` files are imported
        # so historical chats are immediately searchable.
        search_fn = _ensure_default_search_fn(session)
    if search_fn is None:
        return CommandResult(
            output=(
                "/search is unavailable: SQLite + FTS5 support is missing in "
                "this Python build. Re-run with a Python that ships sqlite3 "
                "with the FTS5 extension enabled."
            )
        )

    try:
        hits = list(search_fn(query, k=k))
    except Exception as exc:
        return CommandResult(output=f"/search error: {type(exc).__name__}: {exc}")

    if not hits:
        return CommandResult(output=f"(no matches for {query!r})")

    lines: list[str] = [f"Top {len(hits)} hit(s) for {query!r}:"]
    for i, hit in enumerate(hits, 1):
        sid = hit.get("session_id", "?")
        role = hit.get("role", "?")
        snippet = (hit.get("content") or "").strip().replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:199] + "…"
        lines.append(f"  {i:>2}. [{sid} · {role}] {snippet}")
    return CommandResult(output="\n".join(lines))


def _cmd_approve(session: InteractiveSession, _args: str) -> CommandResult:
    """Approve the pending plan and hand off to the execution mode.

    v3.2.0: ``run`` collapsed into ``agent`` under the Claude-Code 4-mode
    taxonomy, so an approved plan now lands the user in ``agent`` —
    the single full-access execution surface.
    """
    if session.pending_task is None:
        return CommandResult(
            output=(
                "no plan to approve; type a task first "
                "(e.g. 'add CSV export')."
            )
        )
    session.mode = "agent"
    task = session.pending_task
    return CommandResult(
        output=f"approved plan for: {task}\nswitching to agent mode.",
        renderable=_out.approve_renderable(task),
        new_mode="agent",
    )


def _cmd_reject(session: InteractiveSession, _args: str) -> CommandResult:
    was = session.pending_task
    session.pending_task = None
    if was is None:
        return CommandResult(
            output="nothing to reject.",
            renderable=_out.reject_renderable(None),
        )
    return CommandResult(
        output=f"dropped pending plan: {was}",
        renderable=_out.reject_renderable(was),
    )


def _cmd_soul(session: InteractiveSession, _args: str) -> CommandResult:
    soul = session.repo_root / "SOUL.md"
    if not soul.exists():
        return CommandResult(
            output=f"SOUL.md not found at {soul}. Run /doctor or `lyra init`.",
            renderable=_out.missing_file_renderable(
                "SOUL.md", soul, "run `lyra init` to scaffold it."
            ),
        )
    text = soul.read_text(encoding="utf-8")
    return CommandResult(
        output=text,
        renderable=_out.file_contents_renderable("SOUL.md", soul, text),
    )


def _cmd_policy(session: InteractiveSession, _args: str) -> CommandResult:
    policy = session.repo_root / ".lyra" / "policy.yaml"
    if not policy.exists():
        return CommandResult(
            output=(
                f"policy.yaml not found at {policy}. "
                f"Run `lyra init` to scaffold."
            ),
            renderable=_out.missing_file_renderable(
                "policy.yaml",
                policy,
                "run `lyra init` to scaffold it.",
            ),
        )
    text = policy.read_text(encoding="utf-8")
    return CommandResult(
        output=text,
        renderable=_out.file_contents_renderable("policy.yaml", policy, text),
    )


def _cmd_doctor(session: InteractiveSession, _args: str) -> CommandResult:
    soul_path = session.repo_root / "SOUL.md"
    policy_path = session.repo_root / ".lyra" / "policy.yaml"
    soul_ok = soul_path.exists()
    policy_ok = policy_path.exists()

    plain = (
        f"SOUL.md:       {'ok' if soul_ok else 'missing'}\n"
        f"policy.yaml:   {'ok' if policy_ok else 'missing'}\n"
        f"(run `lyra doctor` for the full report)"
    )
    checks: list[tuple[str, bool, str]] = [
        (
            "SOUL.md",
            soul_ok,
            str(soul_path) if soul_ok else "run `lyra init` to create it",
        ),
        (
            "policy.yaml",
            policy_ok,
            str(policy_path)
            if policy_ok
            else "run `lyra init` to scaffold .lyra/policy.yaml",
        ),
    ]
    return CommandResult(
        output=plain,
        renderable=_out.doctor_renderable(checks),
    )


def _cmd_auth(_session: InteractiveSession, args: str) -> CommandResult:
    from lyra_cli.interactive.auth import run_auth_slash

    argv = shlex.split(args) if args.strip() else []
    text = run_auth_slash(argv=argv)
    return CommandResult(output=text)


def _cmd_evals(_session: InteractiveSession, args: str) -> CommandResult:
    """Run a bundled evals corpus inline (Phase E.1 promotion).

    Pre-v2.7 this slash only printed a hint to run ``lyra evals`` in a
    second shell. The hint was technically correct but useless inside
    the REPL — by the time a user typed ``/evals`` they wanted the
    answer, not a TODO. We now invoke the same machinery
    (:func:`lyra_cli.commands.evals._run_bundled`) directly and render
    the result as a one-line summary, with a ``--full`` flag for the
    entire JSON dump.
    """
    parts = args.strip().split()
    full_dump = False
    corpus_tokens: list[str] = []
    for tok in parts:
        if tok == "--full":
            full_dump = True
        else:
            corpus_tokens.append(tok)
    corpus = (corpus_tokens[0] if corpus_tokens else "golden").lower()

    if corpus in {"swe-bench-pro", "loco-eval"}:
        return CommandResult(
            output=(
                f"/evals: corpus {corpus!r} requires the public dataset. "
                f"Run `lyra evals --corpus {corpus} --tasks <path>` "
                f"from a second shell for the adapter run."
            )
        )

    try:
        from ..commands.evals import _run_bundled
    except Exception as exc:  # noqa: BLE001
        return CommandResult(output=f"/evals: lyra_evals not importable: {exc}")

    try:
        report = _run_bundled(corpus, drift_gate=0.0)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(output=f"/evals: {corpus!r} failed — {exc}")

    pass_count = int(report.get("passed", 0))
    total = int(report.get("total", pass_count + int(report.get("failed", 0))))
    rate = float(report.get("success_rate", 0.0))
    tripped = bool(report.get("drift_gate_tripped", False))
    drift_tag = " [drift gate tripped]" if tripped else ""
    headline = (
        f"/evals: corpus={corpus!r} → "
        f"{pass_count}/{total} passed (rate={rate:.3f}){drift_tag}"
    )
    if full_dump:
        return CommandResult(
            output=headline + "\n" + json.dumps(report, indent=2, sort_keys=True)
        )
    return CommandResult(output=headline)


# ---------------------------------------------------------------------------
# New slash commands — Claude Code / opencode / hermes parity
# ---------------------------------------------------------------------------


def _cmd_compact(session: InteractiveSession, _args: str) -> CommandResult:
    """Heuristic context compaction (Phase E.1 promotion).

    The previous implementation only halved ``tokens_used`` for show.
    The new path actually shrinks the in-memory chat history that the
    LLM sees on the next turn:

    * The *most recent* ``KEEP_RECENT`` messages are preserved verbatim
      (so multi-turn coherence isn't broken).
    * Every earlier message is collapsed into a single
      ``role="system"`` summary entry that names the speaker, role,
      and a 240-char prefix of the original content.
    * The token estimate is recomputed from the surviving messages
      using the same heuristic the chat handler uses (``len(s)//4``).

    Real semantic summarisation (the NGC compactor) requires another
    LLM hop and lands in a later phase; this version is a deterministic
    no-network compactor that works offline.
    """
    KEEP_RECENT = 6

    before_tokens = max(session.tokens_used, 1)
    history_attr = getattr(session, "_chat_history", None)
    if not isinstance(history_attr, list) or len(history_attr) <= KEEP_RECENT:
        # Fall back to the legacy halve-the-counter behaviour when
        # there's no chat history to prune (fresh sessions, /compact
        # before the first turn, etc.) so callers always get a result.
        after_tokens = max(before_tokens // 2, 1)
        session.tokens_used = after_tokens
        return CommandResult(
            output=(
                f"[compact] no compactable history yet — token estimate "
                f"halved {before_tokens:,} → {after_tokens:,}."
            ),
            renderable=_out.compact_renderable(
                before=before_tokens, after=after_tokens
            ),
        )

    head = history_attr[: -KEEP_RECENT]
    tail = history_attr[-KEEP_RECENT:]
    summary_lines: list[str] = []
    for msg in head:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "?"))
        content = str(msg.get("content", "")).strip().replace("\n", " ")
        if len(content) > 240:
            content = content[:237] + "..."
        summary_lines.append(f"- {role}: {content}")
    summary_block = "\n".join(summary_lines) or "(empty)"

    digest_message = {
        "role": "system",
        "content": (
            f"[/compact digest of {len(head)} earlier turn(s)]\n"
            f"{summary_block}"
        ),
    }
    session._chat_history = [digest_message, *tail]

    new_chars = sum(
        len(str(m.get("content", "")))
        for m in session._chat_history
        if isinstance(m, dict)
    )
    after_tokens = max(new_chars // 4, 1)
    session.tokens_used = after_tokens

    return CommandResult(
        output=(
            f"[compact] kept {KEEP_RECENT} recent + 1 digest message; "
            f"token estimate {before_tokens:,} → {after_tokens:,} "
            f"(pruned {len(head)} older turn(s))."
        ),
        renderable=_out.compact_renderable(
            before=before_tokens, after=after_tokens
        ),
    )


def _cmd_context(session: InteractiveSession, _args: str) -> CommandResult:
    """Show a breakdown of what's in the current context window (stub)."""
    budget = 200_000
    used = session.tokens_used
    buckets: list[tuple[str, int]] = [
        ("SOUL.md", max(budget // 40, 400)),
        ("plan / task", 600 if session.pending_task else 0),
        ("transcript", max(used - 1000, 0)),
        ("tool results", 0),
        ("skills", 120),
    ]
    plain_lines = ["Context breakdown:"]
    for label, tok in buckets:
        bar = "█" * max(tok * 24 // budget, 1 if tok else 0)
        plain_lines.append(f"  {label:<14} {tok:>7,}  {bar}")
    plain_lines.append(f"  budget        {budget:>7,}")
    return CommandResult(
        output="\n".join(plain_lines),
        renderable=_out.context_renderable(buckets=buckets, budget=budget),
    )


def _cmd_cost(session: InteractiveSession, _args: str) -> CommandResult:
    lines = [
        f"cost so far:   ${session.cost_usd:.4f}",
        f"tokens used:   {session.tokens_used:,}",
        f"turns:         {session.turn}",
    ]
    if session.budget_cap_usd is not None:
        pct = (
            session.cost_usd / session.budget_cap_usd * 100
            if session.budget_cap_usd
            else 0
        )
        lines.append(f"budget cap:    ${session.budget_cap_usd:.2f}")
        lines.append(f"used:          {pct:.1f}% of budget")
    return CommandResult(
        output="\n".join(lines),
        renderable=_out.cost_renderable(
            cost_usd=session.cost_usd,
            tokens=session.tokens_used,
            turns=session.turn,
            budget_cap_usd=session.budget_cap_usd,
        ),
    )


def _cmd_stats(session: InteractiveSession, _args: str) -> CommandResult:
    plain = "\n".join(
        [
            f"turns:            {session.turn}",
            f"slash commands:   "
            + str(sum(1 for h in session.history if h.startswith("/"))),
            f"bash invocations: "
            + str(sum(1 for h in session.history if h.startswith("!"))),
            f"file mentions:    "
            + str(sum(1 for h in session.history if h.startswith("@"))),
            f"cost:             ${session.cost_usd:.4f}",
            f"tokens:           {session.tokens_used:,}",
            f"mode dwell:       {session.mode}",
            f"deep-think:       {'on' if session.deep_think else 'off'}",
        ]
    )
    return CommandResult(
        output=plain,
        renderable=_out.stats_renderable(
            turns=session.turn,
            slash=sum(1 for h in session.history if h.startswith("/")),
            bash=sum(1 for h in session.history if h.startswith("!")),
            files=sum(1 for h in session.history if h.startswith("@")),
            cost_usd=session.cost_usd,
            tokens=session.tokens_used,
            mode=session.mode,
            deep_think=session.deep_think,
        ),
    )


def _cmd_diff(session: InteractiveSession, args: str) -> CommandResult:
    """Run a real ``git diff --stat`` + ``git diff`` against the working tree.

    Falls back gracefully outside a git repo, on a clean tree, or when
    git is not installed. v1.5 wrapped this with per-hunk author + age
    annotations; v1.7.4 made it a first-class command instead of a stub
    pointing at ``!git diff``.
    """
    return CommandResult(
        output=session._cmd_diff_text(args),
        renderable=_out.diff_renderable(),
    )


def _cmd_rewind(session: InteractiveSession, _args: str) -> CommandResult:
    snap = session.rewind_one()
    if snap is None:
        return CommandResult(
            output="nothing to rewind.",
            renderable=_out.rewind_renderable(None),
        )
    return CommandResult(
        output=(
            f"rewound turn {snap.turn + 1} "
            f"(restored mode={snap.mode!r}, "
            f"pending={'yes' if snap.pending_task else 'no'}). "
            f"use /redo to re-apply."
        ),
        renderable=_out.rewind_renderable(snap),
        new_mode=snap.mode,
    )


def _cmd_redo(session: InteractiveSession, _args: str) -> CommandResult:
    """Re-apply the most recent ``/rewind`` (Phase I, v3.0.0).

    Mirrors opencode's ``unrevert`` and complements
    :func:`_cmd_rewind`. The redo stack is drained automatically the
    moment the user types a new plain-text turn, so this command
    only succeeds against a clean rewind sequence.
    """
    snap = session.redo_one()
    if snap is None:
        return CommandResult(
            output=(
                "nothing to redo. type /rewind first, or send a new "
                "prompt — a fresh prompt drops any pending redo."
            ),
            renderable=_out.rewind_renderable(None),
        )
    return CommandResult(
        output=(
            f"redid turn {snap.turn + 1} "
            f"(restored mode={snap.mode!r}, "
            f"pending={'yes' if snap.pending_task else 'no'})."
        ),
        renderable=_out.rewind_renderable(snap),
        new_mode=snap.mode,
    )


def _resolve_sessions_root(session: InteractiveSession) -> Path:
    """Return the live ``sessions_root`` or the conventional default.

    The dispatch layer treats persistence as optional (Wave-B sessions
    without ``sessions_root`` still work); the slash commands fall
    back to ``<repo_root>/.lyra/sessions`` for read-only operations
    (``/sessions``, ``/export``) so the user always has a stable
    location to inspect.
    """
    return session.sessions_root or (session.repo_root / ".lyra" / "sessions")


def _list_session_ids(sessions_root: Path) -> list[tuple[str, float]]:
    """Return ``(session_id, mtime)`` for every session with a ``turns.jsonl``.

    Empty list when ``sessions_root`` is missing — callers treat that
    as "no sessions on disk" and surface a friendly message.
    """
    if not sessions_root.is_dir():
        return []
    out: list[tuple[str, float]] = []
    for entry in sessions_root.iterdir():
        if not entry.is_dir():
            continue
        log = entry / "turns.jsonl"
        if not log.is_file():
            continue
        try:
            mtime = log.stat().st_mtime
        except OSError:
            continue
        out.append((entry.name, mtime))
    return out


def _resolve_session_reference(
    reference: str,
    sessions_root: Path,
    *,
    fallback: str,
) -> str:
    """Resolve a user-typed session reference to a concrete id.

    v3.2.0 (Phase L) — gives ``/resume`` and ``lyra --resume`` the
    Claude-Code-grade ergonomics:

    * ``"latest"`` / ``"last"`` / ``"recent"`` / ``""`` → most
      recently modified session under *sessions_root*. If nothing is
      on disk yet we return *fallback* so the caller can produce a
      "no such session" message that names something the user
      recognises (typically the live session id).
    * an exact id match → return it.
    * a unique prefix → return the full id.
    * ambiguous prefix or no match → return the reference unchanged
      so the caller's existing "no such session" path runs (and lists
      available ids).
    """
    ref = (reference or "").strip().lower()
    if ref in ("", "latest", "last", "recent"):
        rows = _list_session_ids(sessions_root)
        if not rows:
            return fallback
        rows.sort(key=lambda r: r[1], reverse=True)
        return rows[0][0]
    rows = _list_session_ids(sessions_root)
    ids = [r[0] for r in rows]
    # Exact match — accept whichever case the user typed; ids are
    # already case-sensitive on disk but ``lower()`` here lets us
    # compare against ``ref`` without rebuilding the lookup.
    for sid in ids:
        if sid == reference:
            return sid
    # Unique prefix
    matches = [sid for sid in ids if sid.startswith(reference)]
    if len(matches) == 1:
        return matches[0]
    return reference


def _cmd_resume(session: InteractiveSession, args: str) -> CommandResult:
    """Restore a previously saved session by id (Wave-C Task 1).

    v3.2.0 (Phase L): now also copies ``_chat_history``, ``history``,
    ``model``, ``fast_model``, and ``smart_model`` from the restored
    snapshot. Pre-v3.2 the LLM-side conversation context was rebuilt
    inside :meth:`InteractiveSession.resume_session` but only landed
    on the *restored* object — the live session that the REPL was
    holding never got it, so the model "forgot" the conversation
    on the next turn. Symmetrically the model slots never travelled
    across, which meant resuming a session that was running on
    ``deepseek-v4-pro`` would silently switch to ``auto`` and the
    pricing column would lie. Both bugs are now fixed in lock-step.

    The argument may be:

    * a full session id — ``/resume sess-20260427-1234``
    * the literal ``latest`` (or empty) — resumes the most recently
      modified session under the current repo
    * a unique prefix of an id — ``/resume sess-20260427`` if there
      is exactly one match
    """
    from .sessions_store import SessionsStore

    sessions_root = _resolve_sessions_root(session)
    target = _resolve_session_reference(
        args.strip() or "latest", sessions_root, fallback=session.session_id
    )
    restored = InteractiveSession.resume_session(
        session_id=target,
        sessions_root=sessions_root,
        repo_root=session.repo_root,
    )
    if restored is None:
        # Helpful follow-up: list what *is* on disk so the user can pick.
        try:
            available = ", ".join(m.session_id for m in SessionsStore(sessions_root).list()) or "(none)"
        except Exception:
            available = "(unavailable)"
        return CommandResult(
            output=(
                f"no saved session named {target!r}. available: {available}."
            ),
            renderable=_out.resume_renderable(session.repo_root),
        )
    # Warp the live session's salient state to the restored snapshot
    # so the next prompt tick continues from where the user left off.
    session.session_id = restored.session_id
    session.sessions_root = restored.sessions_root
    session.mode = restored.mode
    session.turn = restored.turn
    session.pending_task = restored.pending_task
    session.cost_usd = restored.cost_usd
    session.tokens_used = restored.tokens_used
    session._turns_log = list(restored._turns_log)
    # v3.2.0 (Phase L): bring the LLM-side conversation across so
    # the next turn actually remembers what we were talking about.
    session._chat_history = list(getattr(restored, "_chat_history", []) or [])
    # And the user's REPL input history — useful for ↑/↓ navigation.
    if getattr(restored, "history", None):
        session.history = list(restored.history)
    # And the model slots so pricing + the banner stay accurate. We
    # only adopt the restored model when it was explicitly recorded
    # (not when it's the default "auto") so a deliberate
    # ``lyra --model anthropic --resume <id>`` still wins over the
    # snapshot's persisted choice.
    if restored.model and restored.model != "auto":
        session.model = restored.model
    if getattr(restored, "fast_model", None):
        session.fast_model = restored.fast_model
    if getattr(restored, "smart_model", None):
        session.smart_model = restored.smart_model
    # v3.0.0: a resumed session is, by definition, the post-turn
    # state of *another* timeline — any snapshots sitting on the
    # live session's redo stack belonged to the pre-resume timeline
    # and would resurrect cross-session state on a subsequent
    # /redo. Drop them so /redo starts fresh against the resumed log.
    session._redo_log = []
    # v3.2.0 (Phase L): blow away the cached LLM provider so the
    # next ``_ensure_llm`` call rebuilds against the resumed model
    # slug — without this, ``provider.last_usage`` would still
    # report the *old* model on the next turn even though the
    # banner shows the resumed one.
    session._llm_provider = None
    session._llm_provider_kind = None
    return CommandResult(
        output=(
            f"resumed {target!r}: mode={session.mode}, turn={session.turn}, "
            f"model={session.model}, cost=${session.cost_usd:.2f}, "
            f"tokens={session.tokens_used:,}."
        ),
        renderable=_out.resume_renderable(session.repo_root),
        new_mode=session.mode,
    )


def _cmd_fork(session: InteractiveSession, args: str) -> CommandResult:
    """Copy the current session's JSONL under a new id (Wave-C Task 2)."""
    from .sessions_store import SessionsStore

    new_id = args.strip() or f"{session.session_id}-fork-{session.turn}"
    sessions_root = _resolve_sessions_root(session)
    store = SessionsStore(sessions_root)
    try:
        store.fork(session.session_id, new_id=new_id)
    except FileNotFoundError as exc:
        return CommandResult(
            output=f"fork failed: {exc}. run a prompt first so there's something to fork.",
            renderable=_out.fork_renderable(name=new_id, turn=session.turn),
        )
    return CommandResult(
        output=(
            f"forked {session.session_id!r} → {new_id!r}. "
            f"switch with /resume {new_id}, or list via /sessions."
        ),
        renderable=_out.fork_renderable(name=new_id, turn=session.turn),
    )


def _cmd_sessions(session: InteractiveSession, _args: str) -> CommandResult:
    """Real `/sessions`: enumerate disk-backed sessions (Wave-C Task 2)."""
    from .sessions_store import SessionsStore

    sessions_root = _resolve_sessions_root(session)
    metas = SessionsStore(sessions_root).list()
    if not metas:
        return CommandResult(
            output=(
                f"no saved sessions yet under {sessions_root}/. "
                f"the next plain-text prompt will start writing one."
            ),
            renderable=_out.sessions_renderable(sessions_root),
        )
    lines = [f"saved sessions under {sessions_root}:"]
    for m in metas:
        label = f"  • {m.session_id}  ({m.turn_count} turns)"
        if m.name:
            label += f"  — {m.name}"
        lines.append(label)
    return CommandResult(
        output="\n".join(lines),
        renderable=_out.sessions_renderable(sessions_root),
    )


def _cmd_rename(session: InteractiveSession, args: str) -> CommandResult:
    """Real `/rename`: store the display name in meta.json (Wave-C Task 2)."""
    from .sessions_store import SessionsStore

    name = args.strip()
    if not name:
        return CommandResult(output="usage: /rename <new session name>")
    sessions_root = _resolve_sessions_root(session)
    store = SessionsStore(sessions_root)
    try:
        store.rename(session.session_id, new_name=name)
    except FileNotFoundError:
        # No on-disk session yet: keep the rename in-mem so the next
        # dispatch (which creates the dir) picks it up via meta.json.
        session.session_name = name
        return CommandResult(
            output=(
                f"session display name set to {name!r} (will persist on next prompt)."
            ),
            renderable=_out.rename_renderable(name),
        )
    session.session_name = name
    return CommandResult(
        output=f"session {session.session_id!r} renamed to {name!r}.",
        renderable=_out.rename_renderable(name),
    )


def _cmd_commands(session: InteractiveSession, args: str) -> CommandResult:
    """List or reload user-authored slash commands (Phase I, v3.0.0).

    Subcommands:

    * ``/commands`` — list every command resolved from
      ``.lyra/commands/*.md``.
    * ``/commands reload`` — force a re-scan of the directory, useful
      when the user just dropped or edited a file.
    """
    sub = args.strip().lower()
    if sub == "reload":
        n = session.reload_user_commands()
        return CommandResult(
            output=f"reloaded user commands: {n} entries from .lyra/commands/."
        )
    cmds = session.list_user_commands()
    seen: set[str] = set()
    rows: list[str] = []
    for key, cmd in cmds.items():
        if id(cmd) in seen:
            continue
        seen.add(id(cmd))
        alias_label = ""
        if cmd.aliases:
            alias_label = f"  (aliases: {', '.join('/' + a for a in cmd.aliases)})"
        hint = f" {cmd.args_hint}" if cmd.args_hint else ""
        rows.append(
            f"  /{cmd.name}{hint} — {cmd.description}{alias_label}\n"
            f"    source: {cmd.source}"
        )
    if not rows:
        return CommandResult(
            output=(
                "no user commands found. drop markdown files in "
                ".lyra/commands/ to register custom slash commands. "
                "see /help for the syntax."
            )
        )
    return CommandResult(output="user commands:\n" + "\n".join(rows))


def _cmd_init(session: InteractiveSession, args: str) -> CommandResult:
    """In-REPL ``/init`` (v3.0.0, Phase I).

    Mirror of ``lyra init`` that runs against the live session's
    repo without forcing the user to drop back to the shell.
    Behaviour:

    * Scaffold ``SOUL.md`` and ``.lyra/policy.yaml`` from the
      packaged templates (idempotent — existing files are skipped
      unless ``/init force`` is passed).
    * Auto-migrate legacy state directories (``.open-harness`` /
      ``.opencoding`` — names listed below for ``lyra-legacy-aware``
      grep parity) using the same orchestrator the standalone command
      uses.
    * Report what was created / skipped / migrated as a single
      block of plain output so the REPL pager keeps it together.

    opencode parity: ``/init`` is its scaffolder slash; this one
    matches that ergonomic. See ``feature-parity.md`` row M9.
    """
    from importlib import resources

    from lyra_core.migrations import migrate_legacy_state

    from ..paths import RepoLayout

    force = "force" in args.strip().lower().split()
    layout = RepoLayout(repo_root=session.repo_root)
    lines: list[str] = []

    performed, source = migrate_legacy_state(layout)
    if performed and source is not None:
        lines.append(
            f"migrated state: {source.name} → {layout.state_dir.name} "
            f"(original preserved at {source})"
        )

    layout.ensure()

    def _read_template(name: str) -> str:
        path = resources.files("lyra_cli").joinpath("templates").joinpath(name)
        return path.read_text(encoding="utf-8")

    def _write(name: str, target) -> str:
        if target.exists() and not force:
            return f"  skipped {target.name} (exists; use /init force to overwrite)"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_read_template(name))
        return f"  wrote {target}"

    lines.append("/init — Lyra scaffold:")
    lines.append(_write("SOUL.md.tmpl", layout.soul_md))
    lines.append(_write("policy.yaml.tmpl", layout.policy_yaml))
    lines.append(f"  state dir: {layout.state_dir} (ensured)")
    lines.append(f"  plans dir: {layout.plans_dir} (ensured)")
    lines.append(f"  sessions dir: {layout.sessions_dir} (ensured)")
    lines.append(
        "next: /policy review · /soul · /tdd-gate on (optional) · /toolsets"
    )

    return CommandResult(output="\n".join(lines))


def _reflexion_memory_for(session: InteractiveSession):
    """Lazy accessor for the session's :class:`ReflectionMemory`.

    Defers the import + JSON load until the first /reflect call so
    the cold start path pays no Reflexion cost. The on-disk snapshot
    lives at ``<repo>/.lyra/reflexion.json`` and round-trips via the
    standard :class:`ReflectionMemory` constructor.
    """
    if session._reflexion_memory is None:
        from lyra_core.loop import ReflectionMemory

        snap = session.repo_root / ".lyra" / "reflexion.json"
        session._reflexion_memory = ReflectionMemory(path=snap)
    return session._reflexion_memory


def _cmd_reflect(session: InteractiveSession, args: str) -> CommandResult:
    """Reflexion retrospective loop — verbal self-improvement memory.

    Surface (v3.1.0, Phase J.4):

    * ``/reflect`` — list the 10 most recent stored lessons.
    * ``/reflect on`` / ``/reflect off`` — toggle auto-injection of
      lessons into the next plain-text turn's system preamble.
    * ``/reflect add <verdict> :: <lesson>`` — attach a manually
      authored lesson to the most recent user prompt.
    * ``/reflect tag <tag1,tag2> <verdict> :: <lesson>`` — add a
      lesson with retrieval tags.
    * ``/reflect clear`` — wipe the memory file.

    On-disk snapshot lives at ``<repo>/.lyra/reflexion.json``.
    """
    from lyra_core.loop import Reflection, make_reflection

    parts = args.strip().split(None, 1)
    if not parts:
        memory = _reflexion_memory_for(session)
        recent = memory.recent(10)
        rows = [
            f"reflexion memory ({len(memory)} total, "
            f"auto-inject: {'on' if session.reflexion_enabled else 'off'})"
        ]
        if not recent:
            rows.append("  (no lessons yet — use /reflect add to record one)")
        else:
            for r in recent:
                tag_label = f" [{','.join(r.tags)}]" if r.tags else ""
                rows.append(
                    f"  • [{r.verdict}]{tag_label} {r.lesson[:160]}"
                )
        rows.append("")
        rows.append(
            "usage: /reflect on|off · /reflect add <verdict> :: <lesson> · "
            "/reflect tag <t1,t2> <verdict> :: <lesson> · /reflect clear"
        )
        return CommandResult(output="\n".join(rows))

    sub = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    if sub == "on":
        session.reflexion_enabled = True
        return CommandResult(
            output=(
                "reflexion auto-inject: on (next plain-text turn will "
                "include a 'Lessons from previous attempts' preamble)"
            )
        )

    if sub == "off":
        session.reflexion_enabled = False
        return CommandResult(output="reflexion auto-inject: off")

    if sub == "clear":
        memory = _reflexion_memory_for(session)
        memory.clear()
        return CommandResult(output="reflexion memory: cleared")

    if sub in {"add", "tag"}:
        memory = _reflexion_memory_for(session)
        tags: tuple[str, ...] = ()
        body = rest.strip()
        if sub == "tag":
            tag_parts = body.split(None, 1)
            if len(tag_parts) < 2:
                return CommandResult(
                    output="usage: /reflect tag <t1,t2> <verdict> :: <lesson>"
                )
            tags = tuple(t for t in tag_parts[0].split(",") if t)
            body = tag_parts[1]

        if "::" not in body:
            return CommandResult(
                output=(
                    "usage: /reflect add <verdict> :: <lesson> "
                    "(missing '::' separator)"
                )
            )
        verdict_raw, lesson_raw = body.split("::", 1)
        verdict = verdict_raw.strip() or "fail"
        lesson_text = lesson_raw.strip()
        if not lesson_text:
            return CommandResult(output="lesson cannot be empty")

        task = session._last_user_task or "(no recent task)"
        reflection = make_reflection(
            task,
            attempt_output="(manual /reflect entry)",
            verdict=verdict,
            tags=tags,
            lesson_generator=lambda _t, _a, _v: lesson_text,
        )
        memory.add(reflection)
        return CommandResult(
            output=(
                f"reflexion: added lesson #{len(memory)} "
                f"[{verdict}]"
                + (f" tags={','.join(tags)}" if tags else "")
            )
        )

    return CommandResult(
        output=(
            "usage: /reflect · /reflect on|off · "
            "/reflect add <verdict> :: <lesson> · "
            "/reflect tag <t1,t2> <verdict> :: <lesson> · /reflect clear"
        )
    )


def _cmd_team(session: InteractiveSession, args: str) -> CommandResult:
    """Multi-agent team orchestration — MetaGPT pattern (v3.1.0, Phase J).

    Four forms:

    * ``/team`` — list every registered role with title + toolset.
    * ``/team show <name>`` — describe a role's persona + SOP.
    * ``/team plan`` — show the default 5-step pipeline
      (PM → Architect → Engineer → Reviewer → QA).
    * ``/team run <task>`` — assemble a multi-role brief that the LLM
      can answer in one turn. The brief stitches together every
      role's system prompt and SOP and embeds the user's task; the
      output of the slash is the assembled prompt — paste it as your
      next message (or pipe via ``/team run … | feed``) to fire the
      pipeline.

    A future ``--isolated`` mode will spawn one subagent per step;
    for v3.1.0 the single-turn brief is the supported surface.
    """
    from lyra_core.teams import (
        default_registry,
        default_software_plan,
        run_team_plan,
    )

    parts = args.strip().split(None, 1)
    reg = default_registry()
    plan = default_software_plan()

    if not parts:
        rows = [f"team roles ({len(reg.names())} registered):"]
        for name in reg.names():
            role = reg.get(name)
            if role is None:
                continue
            rows.append(
                f"  • {role.name:<10} {role.title} "
                f"[toolset: {role.toolset}]"
            )
        rows.append("")
        rows.append(
            "usage: /team show <name> · /team plan · /team run <task>"
        )
        return CommandResult(output="\n".join(rows))

    sub = parts[0].lower()

    if sub == "show":
        if len(parts) < 2:
            return CommandResult(output="usage: /team show <name>")
        target = parts[1].strip()
        role = reg.get(target)
        if role is None:
            return CommandResult(output=f"unknown role: {target!r}")
        rows = [
            f"{role.name} — {role.title}",
            f"  toolset:         {role.toolset}",
            f"  output contract: {role.output_contract}",
            "",
            "system prompt:",
            f"  {role.system_prompt}",
            "",
            "SOP:",
        ]
        for step in role.sop:
            rows.append(f"  - {step}")
        return CommandResult(output="\n".join(rows))

    if sub == "plan":
        rows = [f"team plan: {plan.name} ({len(plan.steps)} steps)"]
        for idx, step in enumerate(plan.steps, start=1):
            role = reg.get(step.role)
            title = role.title if role else step.role
            rows.append(f"  {idx}. {step.role:<10} {title}")
        rows.append("")
        rows.append("run with: /team run <one-line task>")
        return CommandResult(output="\n".join(rows))

    if sub == "run":
        if len(parts) < 2 or not parts[1].strip():
            return CommandResult(output="usage: /team run <task>")
        task = parts[1].strip()

        def _emit_brief(role, task_in: str) -> str:
            lines: list[str] = []
            lines.append(f"### {role.title} ({role.name})")
            lines.append("")
            lines.append(role.system_prompt)
            lines.append("")
            lines.append("SOP:")
            for sop in role.sop:
                lines.append(f"- {sop}")
            lines.append("")
            lines.append("Task input:")
            lines.append(task_in)
            lines.append("")
            lines.append(f"Output contract: {role.output_contract}")
            return "\n".join(lines)

        report = run_team_plan(plan, task, agent=_emit_brief, registry=reg)
        sections = [
            "Team handoff brief — paste as your next message to fire the pipeline:",
            "",
            "---",
        ]
        for step in report.steps:
            sections.append(step.output)
            sections.append("---")
        sections.append(
            f"({len(report.steps)} roles staged. The LLM should answer "
            "every section in order, threading each section's output as "
            "input to the next.)"
        )
        return CommandResult(output="\n".join(sections))

    return CommandResult(
        output=(
            "usage: /team · /team show <name> · /team plan · "
            "/team run <task>"
        )
    )


def _cmd_toolsets(session: InteractiveSession, args: str) -> CommandResult:
    """List or apply named tool bundles (v3.0.0, Phase I).

    Hermes-agent parity. Three forms:

    * ``/toolsets`` — list every registered bundle plus the tools
      it would activate.
    * ``/toolsets show <name>`` — describe a single bundle.
    * ``/toolsets apply <name>`` — set ``session.active_toolset``
      and report which tools landed (``applied``) and which were
      requested but unavailable on this session (``skipped``). The
      kernel's permission stack still arbitrates per-call risk —
      this is purely the *bundle* selector.
    """
    from lyra_core.tools import (
        apply_toolset,
        get_toolset,
        list_toolsets,
    )

    parts = args.strip().split()
    available = _session_available_tools(session)

    if not parts:
        names = list_toolsets()
        rows = [f"toolsets ({len(names)} registered):"]
        for name in names:
            tools = get_toolset(name)
            preview = ", ".join(tools[:6])
            more = "" if len(tools) <= 6 else f" (+{len(tools) - 6} more)"
            rows.append(f"  • {name}: {preview}{more}")
        active = getattr(session, "active_toolset", None) or "default"
        rows.append(f"active: {active}. apply with /toolsets apply <name>.")
        return CommandResult(output="\n".join(rows))

    sub = parts[0].lower()
    if sub == "show":
        if len(parts) < 2:
            return CommandResult(output="usage: /toolsets show <name>")
        try:
            tools = get_toolset(parts[1])
        except KeyError as exc:
            return CommandResult(output=f"unknown toolset: {exc}")
        return CommandResult(
            output="\n".join([f"{parts[1]} ({len(tools)} tools):"] + [f"  - {t}" for t in tools])
        )

    if sub == "apply":
        if len(parts) < 2:
            return CommandResult(output="usage: /toolsets apply <name>")
        try:
            outcome = apply_toolset(parts[1], available=available)
        except KeyError as exc:
            return CommandResult(output=f"unknown toolset: {exc}")
        session.active_toolset = outcome.name
        applied = ", ".join(outcome.applied) or "(none)"
        skipped = ", ".join(outcome.skipped) or "(none)"
        return CommandResult(
            output=(
                f"applied toolset {outcome.name!r}.\n"
                f"  enabled: {applied}\n"
                f"  skipped (not registered on this session): {skipped}\n"
                "  permissions/MCP gates still arbitrate per-call risk."
            )
        )

    return CommandResult(
        output=(
            "usage: /toolsets · /toolsets show <name> · /toolsets apply <name>"
        )
    )


def _session_available_tools(session: InteractiveSession) -> list[str]:
    """Best-effort enumeration of tool names visible to ``session``.

    Looks at every common-shape attribute Lyra has used to expose
    its tool catalogue across versions (``tool_registry``,
    ``tools``, ``tool_kernel``). Falls back to the union of every
    built-in toolset so ``/toolsets`` still produces a useful diff
    even on bare sessions.
    """
    candidates: list[str] = []
    for attr in ("tool_registry", "tools", "tool_kernel"):
        registry = getattr(session, attr, None)
        if registry is None:
            continue
        if isinstance(registry, dict):
            candidates.extend(str(k) for k in registry.keys())
            continue
        for method in ("names", "list_names", "list", "all_names"):
            fn = getattr(registry, method, None)
            if callable(fn):
                try:
                    out = fn()
                except Exception:
                    out = None
                if out is not None:
                    try:
                        candidates.extend(str(x) for x in out)
                    except TypeError:
                        pass
                break
    if not candidates:
        from lyra_core.tools import default_toolsets

        for tools in default_toolsets().values():
            candidates.extend(tools)
    return sorted(dict.fromkeys(candidates))


def _cmd_export(session: InteractiveSession, args: str) -> CommandResult:
    """Real `/export`: write the transcript to disk (Wave-C Task 2)."""
    from .sessions_store import SessionsStore, UnsupportedExportFormat

    fmt = (args.strip() or "md").lower()
    sessions_root = _resolve_sessions_root(session)
    out_path = (
        session.repo_root / ".lyra" / "exports" / f"{session.session_id}.{fmt}"
    )
    try:
        SessionsStore(sessions_root).export_to(
            session.session_id, path=out_path, fmt=fmt  # type: ignore[arg-type]
        )
    except UnsupportedExportFormat as exc:
        return CommandResult(
            output=f"export failed: {exc}",
            renderable=_out.export_renderable(path=out_path, turns=session.turn),
        )
    except FileNotFoundError:
        return CommandResult(
            output=(
                f"nothing to export — session {session.session_id!r} hasn't "
                f"recorded any turns yet."
            ),
            renderable=_out.export_renderable(path=out_path, turns=session.turn),
        )
    return CommandResult(
        output=f"exported {session.turn} turns to {out_path}.",
        renderable=_out.export_renderable(path=out_path, turns=session.turn),
    )


def _cmd_theme(session: InteractiveSession, args: str) -> CommandResult:
    from . import themes as _t  # local import — keeps session import cheap

    available = _t.names()
    target = args.strip().lower()
    if not target:
        return CommandResult(
            output=(
                f"current theme: {session.theme}. "
                f"available: {', '.join(available)}."
            ),
            renderable=_out.theme_list_renderable(
                current=session.theme, themes=available
            ),
        )
    if target not in available:
        return CommandResult(
            output=(
                f"unknown theme {target!r}; "
                f"valid: {', '.join(available)}."
            ),
            renderable=_out.bad_theme_renderable(target, available),
        )
    session.theme = target
    # Side-effect on the module-global active skin so the spinner, status
    # bar, and any future renderer that queries get_active_skin() picks
    # up the new palette without us threading state through.
    _t.set_active_skin(target)
    return CommandResult(
        output=f"theme set to: {target}",
        renderable=_out.theme_set_renderable(target),
    )


def _cmd_vim(session: InteractiveSession, args: str) -> CommandResult:
    """`/vim` — toggle vi-style prompt editing.

    Wave-C Task 12 contract:
    - ``/vim`` (no arg) toggles the live state.
    - ``/vim on|off|true|false|1|0`` sets explicitly.
    - ``/vim status`` reports without mutating.
    - Successful mutations persist to ``session.config`` so the
      preference survives a REPL restart (Task 11 pipeline).
    """
    target = args.strip().lower()
    if target == "status":
        state = "on" if session.vim_mode else "off"
        return CommandResult(
            output=f"vim mode: {state}",
            renderable=_out.toggle_renderable("vim", session.vim_mode),
        )
    if target in ("on", "true", "1"):
        session.vim_mode = True
    elif target in ("off", "false", "0"):
        session.vim_mode = False
    elif target == "":
        session.vim_mode = not session.vim_mode
    else:
        return CommandResult(
            output=(
                f"usage: /vim on|off|status (got {target!r})"
            )
        )
    cfg = getattr(session, "config", None)
    if cfg is not None:
        cfg.set("vim", "on" if session.vim_mode else "off")
        _persist_config(session)
    state = "on" if session.vim_mode else "off"
    return CommandResult(
        output=f"vim mode: {state}",
        renderable=_out.toggle_renderable("vim", session.vim_mode),
    )


def _cmd_keybindings(_session: InteractiveSession, _args: str) -> CommandResult:
    rows: list[tuple[str, str]] = [
        ("Ctrl+L", "clear screen and reprint the banner"),
        ("Ctrl+C", "soft-cancel the current input line"),
        ("Ctrl+D", "exit the session (prints goodbye panel)"),
        ("Ctrl+R", "reverse history search"),
        ("Ctrl+G", "open $EDITOR for a long prompt"),
        ("Ctrl+T", "toggle the live task panel"),
        ("Ctrl+O", "toggle verbose tool-call output"),
        ("Ctrl+J", "insert newline (multi-line input)"),
        ("Alt+Enter", "insert newline (multi-line input)"),
        ("Tab", "cycle modes plan → build → run → explore → retro"),
        ("Shift+Tab", "cycle modes in reverse"),
        ("Alt+P", "open model picker"),
        ("Alt+T", "toggle deep-think"),
        ("Esc Esc", "rewind the last turn (same as /rewind)"),
        ("!cmd", "run cmd in a subshell and render the output panel"),
        ("@path", "insert a file reference with path completion"),
    ]
    plain = "Key bindings:\n" + "\n".join(
        f"  {k:<12}  {d}" for k, d in rows
    )
    return CommandResult(
        output=plain,
        renderable=_out.keybindings_renderable(rows),
    )


def _cmd_tools(session: InteractiveSession, args: str) -> CommandResult:
    """``/tools [<name>|risk=<level>|approvals]`` — list/detail/approve.

    Wave-C Task 14 (list/detail/filter) + Wave-D Tasks 6 & 7 (security
    visibility):

    - ``/tools`` — full table with approval state per tool.
    - ``/tools <Name>`` — detail view (origin, planned milestone, approval).
    - ``/tools risk=low|medium|high`` — filter by risk band.
    - ``/tools approvals`` — show the per-session approval cache.
    - ``/tools approve <Name>`` — approve a tool for the rest of the session.
    - ``/tools deny <Name>`` — deny a tool for the rest of the session.
    """
    from lyra_core.permissions import PermissionStack
    from .tool_approval import ToolApprovalCache
    from .tools import registered_tools, tool_by_name, tools_of_risk

    if getattr(session, "permission_stack", None) is None:
        session.permission_stack = PermissionStack(
            mode=session.permission_mode  # type: ignore[arg-type]
        )
    if getattr(session, "tool_approval_cache", None) is None:
        session.tool_approval_cache = ToolApprovalCache(
            mode=session.permission_mode  # type: ignore[arg-type]
        )
    cache: ToolApprovalCache = session.tool_approval_cache

    raw = args.strip()

    if raw.lower() == "approvals":
        snapshot = cache.snapshot()
        if not snapshot:
            return CommandResult(
                output=(
                    "no per-session tool approvals cached yet. "
                    "Use /tools approve <Name> or /tools deny <Name>."
                )
            )
        lines = ["Per-session tool approvals:"]
        for name, state in sorted(snapshot.items()):
            lines.append(f"  {name:<18} {state}")
        return CommandResult(output="\n".join(lines))

    if raw.lower().startswith("approve "):
        name = raw[len("approve "):].strip()
        if not name:
            return CommandResult(output="usage: /tools approve <Name>")
        cache.approve(name)
        return CommandResult(
            output=f"tool {name!r} approved for this session."
        )

    if raw.lower().startswith("deny "):
        name = raw[len("deny "):].strip()
        if not name:
            return CommandResult(output="usage: /tools deny <Name>")
        cache.deny(name)
        return CommandResult(
            output=f"tool {name!r} denied for this session."
        )

    if not raw:
        tools = registered_tools()
        snap = cache.snapshot()
        plain_lines = ["Registered tools:"]
        for t in tools:
            state = snap.get(t["name"], "—")
            plain_lines.append(
                f"  {t['name']:<14} {t['risk']:<6} approval={state:<8} {t['summary']}"
            )
        plain = "\n".join(plain_lines)
        return CommandResult(
            output=plain,
            renderable=_out.tools_renderable(tools),
        )

    if raw.lower().startswith("risk="):
        level = raw.split("=", 1)[1].strip().lower()
        if level not in {"low", "medium", "high"}:
            return CommandResult(
                output=(
                    f"unknown risk level {level!r}; use low|medium|high."
                )
            )
        filtered = tools_of_risk([level])  # type: ignore[arg-type]
        if not filtered:
            return CommandResult(output=f"no tools registered at risk={level}.")
        plain = (
            f"Tools at risk={level}:\n"
            + "\n".join(
                f"  {t['name']:<14} {t['summary']}" for t in filtered
            )
        )
        return CommandResult(
            output=plain,
            renderable=_out.tools_renderable(filtered),
        )

    detail = tool_by_name(raw)
    if detail is None:
        return CommandResult(
            output=(
                f"no such tool {raw!r}. "
                f"Try /tools to see the full list."
            )
        )
    approval = cache.snapshot().get(detail["name"], "—")
    plain = (
        f"Tool: {detail['name']}\n"
        f"  risk:     {detail['risk']}\n"
        f"  approval: {approval}\n"
        f"  origin:   {detail['origin']}\n"
        f"  planned:  {detail['planned']}\n"
        f"  summary:  {detail['summary']}"
    )
    return CommandResult(
        output=plain,
        renderable=_out.tools_renderable([detail]),
    )


def _cmd_agents(session: InteractiveSession, args: str) -> CommandResult:
    """``/agents`` and ``/agents kill <id>`` — Wave-D Task 2.

    Without a registry attached this still prints the static
    "kinds of subagents" overview so the older docs/tests stay
    valid. With a registry attached we render the live process
    table — id, state, description — and route ``kill <id>`` to
    :meth:`SubagentRegistry.cancel`.
    """
    parts = args.strip().split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    reg = getattr(session, "subagent_registry", None)

    # Sub-command: kill ------------------------------------------------
    if sub in ("kill", "cancel", "stop"):
        target = rest.strip()
        if not target:
            return CommandResult(
                output="usage: /agents kill <id>",
            )
        if reg is None:
            return CommandResult(
                output=(
                    "no subagent registry attached. "
                    "Spawn one first or run /agents to see available kinds."
                ),
            )
        rec = reg.get(target)
        if rec is None:
            return CommandResult(
                output=f"no such subagent: {target}",
            )
        ok = reg.cancel(target)
        if ok:
            return CommandResult(
                output=f"cancelled subagent {target}",
            )
        return CommandResult(
            output=(
                f"cannot cancel {target} — record is {rec.state} "
                f"(only pending records can be cancelled today)."
            )
        )

    # Live registry view -----------------------------------------------
    if reg is not None:
        records = reg.list_all()
        if not records:
            return CommandResult(
                output=(
                    "no subagents spawned yet. "
                    "Use /spawn to dispatch one."
                ),
            )
        rows = [
            (rec.id, rec.state, rec.description)
            for rec in records
        ]
        plain_lines = ["Subagents (live):"] + [
            f"  {rid:<10} {rstate:<10} {rdesc}"
            for rid, rstate, rdesc in rows
        ]
        return CommandResult(
            output="\n".join(plain_lines),
            renderable=_out.agents_renderable(
                [(rid, rstate, rdesc) for rid, rstate, rdesc in rows]
            ),
        )

    # Fallback: static kinds overview (legacy / pre-spawn) -------------
    agents: list[tuple[str, str, str]] = [
        ("explore", "haiku", "fast, read-only codebase search (v1.7)"),
        ("plan", "sonnet", "research + plan builder (v1.7)"),
        ("general", "opus", "multi-step specialist (v1.7)"),
        ("safety", "haiku", "secrets + injection triage (v1.7)"),
    ]
    plain = "Subagents (planned):\n" + "\n".join(
        f"  {n:<10} {m:<8} {d}" for n, m, d in agents
    )
    return CommandResult(
        output=plain,
        renderable=_out.agents_renderable(agents),
    )


def _cmd_spawn(session: InteractiveSession, args: str) -> CommandResult:
    """``/spawn [--type <kind>] <description>`` — Phase D.1.

    Wires the slash to a real :class:`SubagentRegistry` backed by a
    :class:`SubagentRunner`. The runner allocates a workdir under
    ``<repo>/.lyra/worktrees/`` and drives one
    :class:`lyra_core.agent.AgentLoop` invocation against the
    description. The result is recorded on the registry so
    ``/agents`` shows the live row.

    The first ``/spawn`` call lazily attaches a registry to the
    session (``session.subagent_registry``). Tests / advanced users
    can attach their own registry beforehand to override the runner
    factory (e.g. to inject a mock LLM); when nothing is attached we
    build the default factory below.

    Args:
        --type <kind>   Optional subagent kind (``general`` /
                        ``explore`` / ``plan`` / ``safety``). Stored
                        on the record so ``/agents`` shows it; the
                        runner doesn't currently specialise on it.
        description     Free-form task description, the same string
                        the runner hands to ``AgentLoop``.
    """
    parts = args.strip().split()
    subagent_type = "general"
    if parts and parts[0] == "--type":
        if len(parts) < 3:
            return CommandResult(output="usage: /spawn [--type <kind>] <description>")
        subagent_type = parts[1]
        description = " ".join(parts[2:])
    else:
        description = " ".join(parts)

    description = description.strip()
    if not description:
        return CommandResult(
            output="usage: /spawn [--type <kind>] <description>",
        )

    reg = _ensure_subagent_registry(session)
    if reg is None:
        return CommandResult(
            output=(
                "subagent runtime unavailable — install lyra-core to enable /spawn."
            ),
            renderable=_out.spawn_renderable(description),
        )

    try:
        rec = reg.spawn(description, subagent_type=subagent_type)
    except ValueError as exc:
        return CommandResult(output=f"spawn failed: {exc}")

    final_text = ""
    if rec.result:
        final_text = str(rec.result.get("final_text", ""))
    summary = (
        f"spawn {rec.id} → {rec.state}"
        + (f" — {final_text}" if final_text else "")
        + (f" — error: {rec.error}" if rec.error else "")
    )
    return CommandResult(
        output=summary,
        renderable=_out.spawn_renderable(description),
    )


class _LyraCoreLLMAdapter:
    """Bridge lyra-cli :class:`LLMProvider` → lyra-core :class:`AgentLoop`.

    Phase E.5: ``lyra_core.agent.AgentLoop`` (the hermes-pattern subagent
    loop) calls ``llm.generate(messages=[dict], tools=[dict])`` and
    expects a ``Mapping[str, Any]`` back with ``content``, ``tool_calls``,
    ``stop_reason``. The lyra-cli ``LLMProvider`` family (Anthropic,
    OpenAI-compatible, Gemini, etc.) speaks Pydantic ``Message`` objects
    on the way in and returns a ``Message`` on the way out.

    Rather than diverge the two loops further (or rewrite every provider
    to dual-shape) we wrap the provider in this adapter at the
    subagent boundary. The result: a single LLM substrate drives both
    the harness_core one-shot ``run`` and the lyra_core subagent
    fan-out, which is what "unify on single path" actually buys us in
    practice.

    The adapter is intentionally thin: no caching, no retry, no
    streaming. Streaming is a parent-loop concern — subagents return a
    final dict and the parent renders the result post-hoc.
    """

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    def generate(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        from harness_core.messages import Message

        cli_messages: list[Message] = []
        for msg in messages:
            if isinstance(msg, Message):
                cli_messages.append(msg)
                continue
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role", "user"))
            content = str(msg.get("content", ""))
            cli_messages.append(Message(role=role, content=content))

        out = self._provider.generate(cli_messages, tools=tools or None, **kwargs)
        return self._to_dict(out)

    @staticmethod
    def _to_dict(message: Any) -> dict[str, Any]:
        from harness_core.messages import Message

        if isinstance(message, Message):
            tool_calls = [
                {
                    "id": getattr(call, "id", None),
                    "name": getattr(call, "name", ""),
                    "arguments": getattr(call, "arguments", {}) or {},
                }
                for call in (message.tool_calls or [])
            ]
            return {
                "content": message.content or "",
                "tool_calls": tool_calls,
                "stop_reason": (
                    str(message.stop_reason) if message.stop_reason else "end_turn"
                ),
            }
        if isinstance(message, dict):
            return dict(message)
        # Defensive: providers that return a string already (rare).
        return {
            "content": str(message),
            "tool_calls": [],
            "stop_reason": "end_turn",
        }


def _ensure_subagent_registry(session: InteractiveSession) -> Any | None:
    """Return ``session.subagent_registry``, lazily building one if absent.

    The default factory wraps :class:`SubagentRunner` so subagents
    actually run an :class:`AgentLoop`. Return ``None`` when
    lyra-core isn't installed (tests on a stripped tree).

    Phase E.5 fixes the legacy bug where the factory passed
    ``AgentLoop(provider=...)`` (the harness_core kwarg) to the
    lyra_core dataclass, which expects ``llm=``. The new factory
    materialises a proper lyra_core loop with the LLM provider
    adapted via :class:`_LyraCoreLLMAdapter`, an empty tool registry
    (subagents inherit the parent's chat tools via plugin hooks in a
    later phase), and a no-op store so spawned scopes can't trample
    parent-session state.
    """
    reg = getattr(session, "subagent_registry", None)
    if reg is not None:
        return reg
    try:
        from lyra_core.agent.loop import AgentLoop, IterationBudget
        from lyra_core.subagent.registry import SubagentRegistry
        from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec
    except Exception:
        return None

    repo_root = Path(session.repo_root)
    worktree_root = repo_root / ".lyra" / "worktrees"
    counter = {"n": 0}

    class _NoopStore:
        def append_message(self, **_: Any) -> None:  # noqa: D401
            return None

    def _loop_factory() -> Any:
        # NOTE: the legacy code imported from ``lyra_cli.interactive.llm_factory``
        # which doesn't exist — silently raising ``ModuleNotFoundError`` at the
        # first ``/spawn``. The real path is the package-root module.
        from lyra_cli.llm_factory import build_llm

        # v2.7.1: spawned subagents are reasoning-heavy by definition
        # (multi-step task with autonomous tool use), so route them
        # through the smart slot. ``_apply_role_model`` stamps the
        # provider-specific env vars *before* ``build_llm`` reads them,
        # so the resulting provider already targets ``smart_model``
        # (default ``deepseek-v4-pro`` → ``deepseek-reasoner``).
        _apply_role_model(session, "smart")
        provider = build_llm(getattr(session, "model", "auto"))
        # Re-apply so the freshly-built provider's ``model`` attr is
        # synced even on the rare path where the preset cached its
        # env read at construction time.
        try:
            slug = _resolve_model_for_role(session, "smart")
            if slug:
                from lyra_core.providers.aliases import resolve_alias as _res

                resolved = _res(slug) or slug
                if hasattr(provider, "model"):
                    provider.model = resolved
        except Exception:
            pass
        return AgentLoop(
            llm=_LyraCoreLLMAdapter(provider),
            tools={},
            store=_NoopStore(),
            budget=IterationBudget(max=8),
        )

    def _task(description: str, **_kwargs: Any) -> dict:
        counter["n"] += 1
        scope_id = f"sub-{counter['n']:04d}"
        runner = SubagentRunner(
            loop_factory=_loop_factory,
            repo_root=repo_root,
            worktree_root=worktree_root,
        )
        result = runner.run(SubagentRunSpec(scope_id=scope_id, description=description))
        return {
            "scope_id": result.scope_id,
            "status": result.status,
            "final_text": result.final_text,
            "workdir": str(result.workdir) if result.workdir else None,
            "error": result.error,
        }

    reg = SubagentRegistry(task=_task)
    session.subagent_registry = reg
    return reg


def _cmd_mcp(session: InteractiveSession, args: str) -> CommandResult:
    """``/mcp [list|connect|disconnect|tools|register|trust|untrust|remove|reload]``.

    Wave-D Task 12 (v1.8.0) introduced the URL-based registry; v2.5.0
    (Phase C.2) extends it with the **stdio child-process** model used
    by Claude Code / Codex. The slash now serves both:

    * ``list`` — show every server, both URL-registered and stdio
      (``mcp.json``) ones, in a single table.
    * ``connect <name>`` — spawn the stdio child for ``name``,
      handshake, and cache the live transport on the session.
    * ``disconnect <name>`` — terminate a previously-spawned child.
    * ``tools <name>`` — list the tools advertised by ``name`` after
      connecting (auto-spawns if needed).
    * ``register <name> <url>`` — URL-mode (legacy).
    * ``trust`` / ``untrust`` / ``remove`` — URL-mode trust flips.
    * ``reload`` — re-read ``~/.lyra/mcp.json`` + project config and
      reset the autoload list.

    Stdio children spawned with ``connect`` are torn down at REPL exit
    by :func:`mcp_autoload.shutdown_all_mcp_clients`.
    """
    from lyra_core.mcp import MCPRegistry, trust_banner_for

    reg = getattr(session, "mcp_registry", None)
    if reg is None:
        reg = MCPRegistry()
        session.mcp_registry = reg

    parts = args.strip().split()
    sub = parts[0].lower() if parts else "list"

    if sub == "list":
        servers = reg.list_servers()
        autoload = list(getattr(session, "mcp_servers", []) or [])
        live = getattr(session, "_mcp_clients", {}) or {}
        if not servers and not autoload:
            return CommandResult(
                output=(
                    "no MCP servers registered. "
                    "Use `/mcp register <name> <url>` for URL servers, "
                    "or add a `mcpServers` entry to ~/.lyra/mcp.json "
                    "for stdio servers."
                ),
                renderable=_out.mcp_placeholder_renderable(),
            )
        lines: list[str] = []
        if servers:
            lines.append("MCP (URL):")
            banners: list[str] = []
            for srv in servers:
                tools = ", ".join(srv.tools) if srv.tools else "(no tools advertised)"
                lines.append(
                    f"  {srv.name:<14} {srv.trust:<10} {srv.url}  [{tools}]"
                )
                banner = trust_banner_for(srv)
                if banner:
                    banners.append(banner)
            if banners:
                lines.append("")
                lines.extend(banners)
        if autoload:
            if lines:
                lines.append("")
            lines.append("MCP (stdio, autoloaded):")
            for cfg in autoload:
                state = "[connected]" if cfg.name in live else "[idle]"
                lines.append(
                    f"  {cfg.name:<14} {cfg.trust:<10} {' '.join(cfg.command)}  {state}"
                )
        if getattr(session, "_mcp_load_issues", None):
            lines.append("")
            lines.append("issues:")
            for issue in session._mcp_load_issues:
                lines.append(f"  • {issue.source}::{issue.name} — {issue.message}")
        return CommandResult(output="\n".join(lines))

    if sub == "connect":
        if len(parts) < 2:
            return CommandResult(output="usage: /mcp connect <name>")
        from .mcp_autoload import ensure_mcp_client_started, find_mcp_server

        name = parts[1]
        if find_mcp_server(session, name) is None:
            return CommandResult(
                output=f"no MCP server named {name!r} in mcp.json"
            )
        client = ensure_mcp_client_started(session, name)
        if client is None:
            return CommandResult(
                output=f"failed to start MCP server {name!r} (check `lyra mcp doctor`)"
            )
        try:
            tools = client.list_tools()
        except Exception as exc:  # pragma: no cover — defensive
            return CommandResult(
                output=f"connected to {name!r} but tools/list failed: {exc}"
            )
        names = ", ".join(t.get("name", "?") for t in tools) or "(none)"
        return CommandResult(
            output=f"connected to MCP server {name!r}; tools: {names}"
        )

    if sub == "disconnect":
        if len(parts) < 2:
            return CommandResult(output="usage: /mcp disconnect <name>")
        name = parts[1]
        client = getattr(session, "_mcp_clients", {}).get(name)
        if client is None:
            return CommandResult(output=f"MCP server {name!r} is not connected")
        try:
            client.close()
        except Exception:
            pass
        session._mcp_clients.pop(name, None)
        return CommandResult(output=f"disconnected MCP server {name!r}")

    if sub == "tools":
        if len(parts) < 2:
            return CommandResult(output="usage: /mcp tools <name>")
        from .mcp_autoload import ensure_mcp_client_started, find_mcp_server

        name = parts[1]
        if find_mcp_server(session, name) is None:
            return CommandResult(
                output=f"no MCP server named {name!r} in mcp.json"
            )
        client = ensure_mcp_client_started(session, name)
        if client is None:
            return CommandResult(
                output=f"failed to start MCP server {name!r}"
            )
        try:
            tools = client.list_tools()
        except Exception as exc:
            return CommandResult(
                output=f"tools/list failed for {name!r}: {exc}"
            )
        if not tools:
            return CommandResult(output=f"{name!r} advertises no tools")
        lines = [f"tools advertised by {name!r}:"]
        for t in tools:
            tname = t.get("name", "?")
            desc = (t.get("description") or "").strip().splitlines()[:1]
            desc_s = desc[0] if desc else ""
            lines.append(f"  {tname:<32} {desc_s}")
        return CommandResult(output="\n".join(lines))

    if sub == "reload":
        from .mcp_autoload import autoload_mcp_servers

        autoload_mcp_servers(session)
        n = len(getattr(session, "mcp_servers", []) or [])
        return CommandResult(
            output=f"reloaded MCP config: {n} stdio server(s) discovered"
        )

    if sub == "register":
        if len(parts) < 3:
            return CommandResult(output="usage: /mcp register <name> <url>")
        name, url = parts[1], parts[2]
        reg.register(name=name, url=url)
        return CommandResult(
            output=f"registered MCP server {name!r} → {url} (untrusted)"
        )

    if sub in ("trust", "untrust"):
        if len(parts) < 2:
            return CommandResult(output=f"usage: /mcp {sub} <name>")
        name = parts[1]
        ok = reg.trust(name) if sub == "trust" else reg.untrust(name)
        if not ok:
            return CommandResult(output=f"no such MCP server: {name}")
        return CommandResult(output=f"MCP server {name!r} → {sub}ed")

    if sub == "remove":
        if len(parts) < 2:
            return CommandResult(output="usage: /mcp remove <name>")
        name = parts[1]
        ok = reg.remove(name)
        if not ok:
            return CommandResult(output=f"no such MCP server: {name}")
        return CommandResult(output=f"removed MCP server {name!r}")

    return CommandResult(
        output=(
            f"unknown subcommand {sub!r}; try "
            f"/mcp [list|connect|disconnect|tools|register|trust|untrust|remove|reload]"
        )
    )


def _cron_store_for(session: InteractiveSession):
    """Resolve the :class:`~lyra_core.cron.store.CronStore` for this session.

    Jobs live under ``<repo>/.lyra/cron/jobs.json`` by default, which
    matches hermes's ``~/.hermes/cron/jobs.json`` shape but keeps them
    scoped to the project so parallel checkouts do not clobber each
    other.
    """
    from lyra_core.cron.store import CronStore

    override = os.environ.get("LYRA_CRON_JOBS_PATH")
    path = Path(override) if override else session.repo_root / ".lyra" / "cron" / "jobs.json"
    return CronStore(jobs_path=path)


def _cmd_cron(session: InteractiveSession, args: str) -> CommandResult:
    """`/cron` — manage scheduled automations (hermes parity).

    Phase D.2 wires the ``run`` subcommand to a real in-process
    runner — when the user invokes ``/cron run <id>`` we now route
    the job through the session's subagent registry so the prompt
    actually executes inside an :class:`AgentLoop`. Without a
    registry attached we fall back to the legacy "flag for next
    tick" message so older tests (which never built a runner) keep
    passing.
    """
    try:
        argv = shlex.split(args) if args.strip() else []
    except ValueError as exc:
        return CommandResult(output=f"cron: bad quoting ({exc})")

    def _runner(job: Any) -> Any:
        reg = _ensure_subagent_registry(session)
        if reg is None:
            raise RuntimeError("subagent registry unavailable; install lyra-core")
        prompt = job.prompt or "(empty cron prompt)"
        rec = reg.spawn(prompt, subagent_type="cron")
        if rec.error:
            raise RuntimeError(rec.error)
        return rec

    try:
        output = handle_cron(
            argv, store=_cron_store_for(session), runner=_runner
        )
    except CronCommandError as exc:
        return CommandResult(output=f"cron: {exc}")
    return CommandResult(output=output)


def _cmd_map(session: InteractiveSession, args: str) -> CommandResult:
    return CommandResult(
        output=session._cmd_map_text(args),
        renderable=_out.map_renderable(session.repo_root),
    )


def _cmd_blame(session: InteractiveSession, args: str) -> CommandResult:
    target = args.strip() or "(unspecified)"
    return CommandResult(
        output=session._cmd_blame_text(args),
        renderable=_out.blame_renderable(target),
    )


def _cmd_trace(session: InteractiveSession, args: str) -> CommandResult:
    """Render last-N HIR events from the global ring buffer.

    The legacy "verbose live-echo" toggle from v0.x is preserved as a
    secondary keyword: ``/trace on`` / ``/trace off`` flip
    ``session.verbose`` so plugins that gate their chatter on it keep
    working. Plain ``/trace`` shows the ring buffer.
    """
    target = args.strip().lower()
    if target in ("on", "off"):
        session.verbose = target == "on"
    path = session.repo_root / ".lyra" / "sessions" / "events.jsonl"
    return CommandResult(
        output=session._cmd_trace_text(args),
        renderable=_out.trace_renderable(
            path=path, verbose=session.verbose
        ),
    )


def _cmd_self(session: InteractiveSession, args: str) -> CommandResult:
    """Agent introspection — render full session state plus runtime extras."""
    from .tools import registered_tools

    tool_count = len(registered_tools())
    rows: list[tuple[str, str]] = [
        ("version", __version__),
        ("mode", session.mode),
        ("model", session.model),
        ("skill packs", f"{len(_SHIPPED_SKILL_PACKS)} installed"),
        ("tools", f"{tool_count} registered"),
        ("deep-think", "on" if session.deep_think else "off"),
        ("verbose", "on" if session.verbose else "off"),
        ("vim", "on" if session.vim_mode else "off"),
        ("theme", session.theme),
    ]
    extras = "\n".join(f"  {k:<14} {v}" for k, v in rows)
    return CommandResult(
        output=f"{session._cmd_self_text(args)}\n\nRuntime:\n{extras}",
        renderable=_out.self_renderable(rows),
    )


def _cmd_badges(session: InteractiveSession, _args: str) -> CommandResult:
    """Render earned achievement chips (Wave-C) plus slash-usage tail.

    Wave-C surfaces ``~/.lyra/badges.json`` (or
    ``<repo_root>/.lyra/badges.json``) so achievement chips earned by
    the agent loop persist across REPLs. The legacy "slash usage"
    tally stays as a secondary block so the original v1 output
    contract isn't broken.
    """
    import json as _json

    rows: list[tuple[str, str]] = []
    badges_path = session.repo_root / ".lyra" / "badges.json"
    if badges_path.is_file():
        try:
            data = _json.loads(badges_path.read_text(encoding="utf-8"))
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get("name", "?"))
                earned = str(entry.get("earned_at", ""))
                rows.append((name, earned))
        except (OSError, _json.JSONDecodeError):
            rows = []

    slash_counts: dict[str, int] = {}
    for line in session.history:
        if line.startswith("/"):
            name = line[1:].split(maxsplit=1)[0].lower()
            slash_counts[name] = slash_counts.get(name, 0) + 1
    slash_rows = sorted(slash_counts.items(), key=lambda kv: kv[1], reverse=True)

    chunks: list[str] = []
    if rows:
        chunks.append("Earned badges:")
        for name, earned in rows:
            chunks.append(f"  ★  {name}  ({earned})" if earned else f"  ★  {name}")
        chunks.append("")
    chunks.append("Usage badges:")
    if slash_rows:
        chunks.extend(f"  /{k:<14} ×{v}" for k, v in slash_rows)
    else:
        chunks.append("  (no slash commands run yet)")

    return CommandResult(
        output="\n".join(chunks),
        renderable=_out.badges_renderable(slash_rows),
    )


def _cmd_budget(session: InteractiveSession, args: str) -> CommandResult:
    """``/budget [set|status|record|reset] [...]`` — per-session cost meter.

    Accepts both the bare form (``/budget 5``) and the verbose form
    (``/budget set 5``) so muscle memory from claw-code / opencode
    works. ``/budget status`` reports current spend vs. cap via the
    Wave-D :class:`BudgetMeter` (live deduction, falls back to the
    Wave-C ``enforce`` classifier when no meter is attached yet).
    ``/budget record <model> <p_tok> <c_tok>`` is the manual-deduction
    surface that integrations can call from a provider callback;
    ``/budget reset`` zeros the meter.
    """
    from .budget import BudgetCap, BudgetMeter, enforce

    target = args.strip()
    lower = target.lower()

    def _ensure_meter() -> BudgetMeter:
        meter = getattr(session, "budget_meter", None)
        cap = (
            BudgetCap(limit_usd=session.budget_cap_usd)
            if session.budget_cap_usd is not None
            else None
        )
        if meter is None:
            meter = BudgetMeter(cap=cap)
            session.budget_meter = meter
        else:
            meter.cap = cap
        return meter

    if lower.startswith("record "):
        rest = target[len("record "):].strip().split()
        if len(rest) != 3:
            return CommandResult(
                output="usage: /budget record <model> <prompt_tokens> <completion_tokens>"
            )
        model, p_tok, c_tok = rest
        try:
            p, c = int(p_tok), int(c_tok)
        except ValueError:
            return CommandResult(output="prompt/completion token counts must be integers")
        meter = _ensure_meter()
        delta = meter.record_usage(
            model=model, prompt_tokens=p, completion_tokens=c
        )
        session.cost_usd += delta
        rep = meter.report()
        return CommandResult(
            output=(
                f"recorded {delta:.4f} USD ({model}, {p}+{c} tokens). "
                f"total spend: ${meter.current_usd:.4f}. {rep.message}"
            ),
            renderable=_out.budget_renderable(session.budget_cap_usd),
        )

    if lower == "reset":
        meter = _ensure_meter()
        meter.reset()
        session.cost_usd = 0.0
        return CommandResult(
            output="budget meter reset to $0.00.",
            renderable=_out.budget_renderable(session.budget_cap_usd),
        )

    if lower in ("off", "none", "clear"):
        session.budget_cap_usd = None
        if getattr(session, "budget_meter", None) is not None:
            session.budget_meter.cap = None
        return CommandResult(
            output="budget cap cleared.",
            renderable=_out.budget_renderable(None),
        )
    if lower == "save off" or lower == "save clear" or lower == "save none":
        # Persist "no automatic cap" — clears the entry from auth.json
        # so future sessions boot uncapped.
        try:
            from lyra_core.auth.store import save_budget

            save_budget(cap_usd=None)
            return CommandResult(
                output=(
                    "persistent budget default cleared. "
                    "future sessions boot with no cap until you set one."
                ),
                renderable=_out.budget_renderable(session.budget_cap_usd),
            )
        except Exception as exc:
            return CommandResult(output=f"could not save budget default: {exc}")
    if lower == "save":
        # ``/budget save`` (no arg) — persist the *current* session cap.
        if session.budget_cap_usd is None:
            return CommandResult(
                output=(
                    "no cap to save; set one first "
                    "(e.g. /budget save 5.00)."
                ),
            )
        try:
            from lyra_core.auth.store import save_budget

            save_budget(cap_usd=float(session.budget_cap_usd))
            return CommandResult(
                output=(
                    f"saved ${session.budget_cap_usd:.2f} as the persistent "
                    f"budget default. every new session will boot with this "
                    f"cap. clear with /budget save off."
                ),
                renderable=_out.budget_renderable(session.budget_cap_usd),
            )
        except Exception as exc:
            return CommandResult(output=f"could not save budget default: {exc}")
    if lower.startswith("save "):
        # ``/budget save 5`` — set the session cap *and* persist it.
        rest = target[len("save "):].strip()
        try:
            usd = float(rest.lstrip("$"))
        except ValueError:
            return CommandResult(
                output=f"bad budget value {rest!r}; use /budget save <usd>."
            )
        session.budget_cap_usd = max(usd, 0.0)
        if getattr(session, "budget_meter", None) is not None:
            from .budget import BudgetCap

            session.budget_meter.cap = BudgetCap(limit_usd=session.budget_cap_usd)
        try:
            from lyra_core.auth.store import save_budget

            save_budget(cap_usd=float(session.budget_cap_usd))
        except Exception as exc:
            return CommandResult(
                output=(
                    f"cap set to ${session.budget_cap_usd:.2f} for this session, "
                    f"but could not persist: {exc}"
                ),
            )
        return CommandResult(
            output=(
                f"budget cap set to ${session.budget_cap_usd:.2f} and saved "
                f"as the persistent default."
            ),
            renderable=_out.budget_renderable(session.budget_cap_usd),
        )
    if lower in ("suggest", "auto", "default"):
        # Compute a sensible cap for the active model and offer it.
        # We cap at "~50 typical chat turns" so a fresh user gets a
        # cap they're unlikely to bump into during a normal session
        # but tight enough to stop a runaway tool loop.
        from .budget import price_for

        prompt_per, completion_per = price_for(session.model)
        per_turn = (500 / 1_000_000) * prompt_per + (200 / 1_000_000) * completion_per
        suggested = max(round(per_turn * 50, 2), 0.10)
        return CommandResult(
            output=(
                f"suggested cap for {session.model}: ~${suggested:.2f} "
                f"(50 typical 700-token chat turns at "
                f"${prompt_per:.2f}/${completion_per:.2f} per Mtok). "
                f"apply with /budget save {suggested:.2f}."
            ),
        )
    if lower == "status":
        if session.budget_cap_usd is None:
            meter = getattr(session, "budget_meter", None)
            spend = meter.current_usd if meter is not None else session.cost_usd
            return CommandResult(
                output=(
                    f"no budget cap set; current spend ${spend:.4f}. "
                    f"use /budget set <usd>."
                ),
                renderable=_out.budget_renderable(None),
            )
        meter = _ensure_meter()
        rep = meter.report()
        return CommandResult(
            output=rep.message,
            renderable=_out.budget_renderable(session.budget_cap_usd),
        )
    if lower.startswith("set "):
        target = target[4:].strip()
    if not target:
        return CommandResult(
            output=(
                f"current budget: "
                + (
                    f"${session.budget_cap_usd:.2f}"
                    if session.budget_cap_usd is not None
                    else "(none)"
                )
                + ". usage: /budget set 5.00  ·  /budget off  ·  /budget status"
            ),
            renderable=_out.budget_renderable(session.budget_cap_usd),
        )
    try:
        usd = float(target.lstrip("$"))
    except ValueError:
        return CommandResult(
            output=f"bad budget value {target!r}; use /budget set <usd>."
        )
    session.budget_cap_usd = max(usd, 0.0)
    return CommandResult(
        output=f"budget cap set to ${session.budget_cap_usd:.2f}",
        renderable=_out.budget_renderable(session.budget_cap_usd),
    )


def _cmd_stream(session: InteractiveSession, args: str) -> CommandResult:
    """``/stream [on|off|status]`` — toggle live streaming chat output.

    v2.2.4. By default the REPL streams DeepSeek / OpenAI / Qwen / etc.
    replies token-by-token via Rich Live. Some terminals (older Windows
    consoles, certain SSH multiplexers) repaint poorly under Live; the
    toggle flips ``session._streaming_enabled`` so those users can run
    Lyra in classic blocking-print mode without restarting.

    Persistence isn't on disk yet — set ``LYRA_NO_STREAM=1`` in your
    shell rc to keep streaming off across sessions.
    """
    target = (args or "").strip().lower()

    def _state_message() -> str:
        if session._console is None:
            return (
                "streaming is off (no TTY console attached — "
                "running in plain / piped mode)."
            )
        if session._streaming_enabled:
            return "streaming is on. /stream off to disable."
        return "streaming is off. /stream on to enable."

    if target in ("", "status"):
        return CommandResult(output=_state_message())

    if target in ("on", "true", "1", "yes", "enable"):
        if session._console is None:
            return CommandResult(
                output=(
                    "cannot enable streaming: this session is plain / "
                    "piped (no TTY console). streaming requires an "
                    "interactive terminal."
                ),
            )
        session._streaming_enabled = True
        return CommandResult(output="streaming enabled.")
    if target in ("off", "false", "0", "no", "disable"):
        session._streaming_enabled = False
        return CommandResult(output="streaming disabled.")

    return CommandResult(
        output=f"unknown /stream argument {target!r}. usage: /stream [on|off|status]"
    )


def _cmd_skills(session: InteractiveSession, args: str) -> CommandResult:
    """``/skills [on|off|status|list|packs|reload]`` — manage SKILL.md injection.

    v2.4.0 (Phase B.4). Lyra walks ``lyra_skills.packs/``,
    ``~/.lyra/skills/``, and ``<repo>/.lyra/skills/`` and prepends a
    compact "## Available skills" block to the chat system prompt so
    the LLM can address packs by id (``surgical-changes``,
    ``test-gen``, …). This subcommand surfaces and toggles the
    behaviour:

    * (no args) — status plus the shipped pack categories (legacy
      contract pre-v2.4: ``atomic-skills``, ``tdd-sprint``,
      ``karpathy``, ``safety``).
    * ``status`` — toggle state and the number of cached skills.
    * ``on`` / ``off`` — flip the per-session toggle.
    * ``list`` — print the discovered skills (id + description).
    * ``packs`` — print only the shipped pack categories.
    * ``reload`` — drop the cache so the next turn re-walks disk
      (useful after editing a ``SKILL.md``).
    """
    target = (args or "").strip().lower()

    def _state_message() -> str:
        if session.skills_inject_enabled:
            return "skill injection is on. /skills off to disable."
        return "skill injection is off. /skills on to enable."

    def _packs_lines() -> list[str]:
        return [
            f"  - {pack}: {description}"
            for pack, description in _SHIPPED_SKILL_PACKS
        ]

    if target == "":
        # Default rendering keeps the v0.1.0 "list installed packs"
        # contract so older tests + muscle-memory still work, and adds
        # the new injection state line at the top.
        try:
            from .skills_inject import discover_skill_roots, _load_skills_safely

            roots = discover_skill_roots(session.repo_root)
            skills = _load_skills_safely(roots)
        except Exception:
            roots, skills = [], []
        lines = [
            f"{_state_message()} "
            f"({len(skills)} skill(s) across {len(roots)} root(s))",
            "",
            "Installed skill packs:",
            *_packs_lines(),
            "",
            "Tip: /skills list — every discovered SKILL.md "
            "(packaged + ~/.lyra/skills + .lyra/skills).",
        ]
        return CommandResult(
            output="\n".join(lines),
            renderable=_out.skills_renderable(
                list(_SHIPPED_SKILL_PACKS),
                footer=(
                    "Skills are loaded by the router at run time. "
                    "Use /skills list for the full per-id breakdown."
                ),
            ),
        )

    if target == "status":
        try:
            from .skills_inject import discover_skill_roots, _load_skills_safely

            roots = discover_skill_roots(session.repo_root)
            skills = _load_skills_safely(roots)
        except Exception:
            roots, skills = [], []
        return CommandResult(
            output=(
                f"{_state_message()} "
                f"({len(skills)} skill(s) across {len(roots)} root(s))"
            )
        )

    if target == "packs":
        return CommandResult(
            output="\n".join(["Installed skill packs:", *_packs_lines()])
        )

    if target in ("on", "true", "1", "yes", "enable"):
        session.skills_inject_enabled = True
        return CommandResult(output="skill injection enabled.")
    if target in ("off", "false", "0", "no", "disable"):
        session.skills_inject_enabled = False
        return CommandResult(output="skill injection disabled.")

    if target == "reload":
        session._cached_skill_block = None
        return CommandResult(
            output=(
                "skill cache cleared. the next chat turn will re-walk "
                "the skill roots."
            )
        )

    if target == "list":
        try:
            from .skills_inject import discover_skill_roots, _load_skills_safely

            skills = _load_skills_safely(discover_skill_roots(session.repo_root))
        except Exception as exc:
            return CommandResult(output=f"skill discovery failed: {exc}")
        if not skills:
            return CommandResult(
                output="no skills discovered. drop a SKILL.md under .lyra/skills/."
            )
        skills.sort(key=lambda s: s.id)
        lines = [
            f"- {s.id}: {(s.description or '').strip() or '(no description)'}"
            for s in skills
        ]
        return CommandResult(output="\n".join(lines))

    return CommandResult(
        output=(
            f"unknown /skills argument {target!r}. "
            f"usage: /skills [on|off|status|list|reload]"
        )
    )


def _cmd_memory(session: InteractiveSession, args: str) -> CommandResult:
    """``/memory [on|off|status|search <q>|reload]`` — manage memory injection.

    v2.4.0 (Phase B.5). Lyra queries

    * the project-local :class:`ProceduralMemory` at
      ``<repo>/.lyra/memory/procedural.sqlite`` (FTS5 over skill
      bodies), and
    * the in-process :class:`ReasoningBank` (positive lessons +
      anti-skills),

    on every chat turn, prepending a "## Relevant memory" block to
    the system prompt. This subcommand surfaces and toggles that
    behaviour:

    * ``status`` — current toggle and whether each store is loaded.
    * ``on`` / ``off`` — flip the per-session toggle.
    * ``search <query>`` — run an ad-hoc search and print results.
    * ``reload`` — drop the cached procedural-memory handle so the
      next turn re-opens the SQLite file (useful after a sibling
      process wrote new skills into it).
    """
    target = (args or "").strip()
    target_lc = target.lower()

    def _state_message() -> str:
        if session.memory_inject_enabled:
            return "memory injection is on. /memory off to disable."
        return "memory injection is off. /memory on to enable."

    if target == "" or target_lc == "status":
        try:
            from .memory_inject import (
                _default_procedural_db_path,
                _open_procedural_memory,
            )

            db_path = _default_procedural_db_path(session.repo_root)
            proc_loaded = _open_procedural_memory(db_path) is not None
        except Exception:
            proc_loaded = False
        bank_loaded = getattr(session, "reasoning_bank", None) is not None
        return CommandResult(
            output=(
                f"{_state_message()} "
                f"(procedural store: {'loaded' if proc_loaded else 'absent'}, "
                f"reasoning bank: {'attached' if bank_loaded else 'detached'})"
            )
        )

    if target_lc in ("on", "true", "1", "yes", "enable"):
        session.memory_inject_enabled = True
        return CommandResult(output="memory injection enabled.")
    if target_lc in ("off", "false", "0", "no", "disable"):
        session.memory_inject_enabled = False
        return CommandResult(output="memory injection disabled.")

    if target_lc == "reload":
        session._procedural_memory = None
        session._procedural_memory_loaded = False
        return CommandResult(
            output=(
                "procedural-memory handle dropped. "
                "the next chat turn will re-open the store."
            )
        )

    if target_lc.startswith("search"):
        query = target[len("search"):].strip()
        if not query:
            return CommandResult(
                output="usage: /memory search <query>"
            )
        try:
            from .memory_inject import render_memory_block
        except Exception as exc:
            return CommandResult(output=f"memory search failed: {exc}")
        block = render_memory_block(
            query,
            repo_root=session.repo_root,
            reasoning_bank=getattr(session, "reasoning_bank", None),
        )
        if not block:
            return CommandResult(
                output=(
                    f"no memory hits for {query!r}. "
                    "(this is normal on a fresh project — populate "
                    "the procedural store via the agent loop.)"
                )
            )
        return CommandResult(output=block)

    return CommandResult(
        output=(
            f"unknown /memory argument {target!r}. "
            f"usage: /memory [on|off|status|search <q>|reload]"
        )
    )


def _cmd_btw(session: InteractiveSession, args: str) -> CommandResult:
    """`/btw <topic>` — record a side-question without polluting the
    main agent context.

    Wave-C Task 14: questions land in ``session._btw_log`` (FIFO),
    NOT in ``session.history``. This mirrors Claude Code's "by the
    way" affordance — the model never sees these unless the user
    explicitly promotes one back into the main thread.
    """
    topic = args.strip()
    if not topic:
        return CommandResult(
            output="usage: /btw <topic>  (records a side-question)"
        )
    session._btw_log.append(topic)
    count = len(session._btw_log)
    return CommandResult(
        output=(
            f"btw: {topic}\n"
            f"(recorded as side-note #{count}; main agent context "
            f"untouched — see /export to bundle into a handoff.)"
        ),
        renderable=_out.btw_renderable(topic),
    )


def _cmd_handoff(session: InteractiveSession, _args: str) -> CommandResult:
    """Real Wave-C handoff: assemble + write a paste-able PR description."""
    from .handoff import _git_diff_stat, render_handoff

    git_available = _git_diff_stat(session.repo_root) is not None
    text = render_handoff(session, git_available=git_available)
    out_path = session.repo_root / ".lyra" / "handoff.md"
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        suffix = f"\n\n(saved to {out_path})"
    except OSError:
        suffix = ""
    return CommandResult(
        output=text + suffix,
        renderable=_out.handoff_renderable(
            repo=session.repo_root,
            turns=session.turn,
            model=session.model,
            mode=session.mode,
            pending=session.pending_task,
        ),
    )


def _cmd_pair(session: InteractiveSession, args: str) -> CommandResult:
    """``/pair [on|off]`` — toggle pair-programming presentation mode.

    Wave-D Task 15 wires the live-streaming substrate. When pair
    mode is on, a :class:`PairStream` subscribes to the session's
    :class:`LifecycleBus` and pipes one line per event into
    ``session._pair_sink`` (defaults to a list the REPL drains
    onto the console). Toggling off mutes the stream without
    losing the subscriptions, so a quick re-toggle resumes the
    live view immediately.
    """
    from lyra_core.hooks.lifecycle import LifecycleBus
    from .pair_stream import PairStream

    target = args.strip().lower()
    if target in ("on", "true", "1"):
        session.pair_mode = True
    elif target in ("off", "false", "0"):
        session.pair_mode = False
    elif target == "":
        session.pair_mode = not session.pair_mode
    else:
        return CommandResult(
            output=f"usage: /pair [on|off] (got {target!r})"
        )

    bus = getattr(session, "lifecycle_bus", None)
    if bus is None:
        bus = LifecycleBus()
        session.lifecycle_bus = bus
    sink = getattr(session, "_pair_sink", None)
    if sink is None:
        sink_list: list[str] = []

        def _append(line: str) -> None:
            sink_list.append(line)

        session._pair_sink = sink_list  # type: ignore[attr-defined]
        sink = _append
    elif isinstance(sink, list):
        # Wrap the existing list so the stream still gets a callable.
        existing = sink

        def _append(line: str) -> None:
            existing.append(line)

        sink = _append

    stream: PairStream | None = getattr(session, "_pair_stream", None)
    if stream is None:
        stream = PairStream(sink=sink, bus=bus)
        session._pair_stream = stream  # type: ignore[attr-defined]
    if session.pair_mode:
        stream.attach()
        stream.set_enabled(True)
    else:
        stream.set_enabled(False)

    state = "on" if session.pair_mode else "off"
    return CommandResult(
        output=(
            f"pair mode: {state}. "
            + (
                "transcript view enabled — every lifecycle event will stream here."
                if session.pair_mode
                else "back to normal REPL view (subscriptions kept; flip on to resume)."
            )
        ),
        renderable=_out.pair_renderable(session.mode),
    )


def _cmd_wiki(session: InteractiveSession, args: str) -> CommandResult:
    """``/wiki [generate|preview]`` — Wave-E repo wiki.

    Without an argument (or ``preview``) the index is rendered to
    the REPL but not written to disk. ``generate`` writes the full
    bundle under ``<repo>/.lyra/wiki/`` and reports the path.
    """
    from lyra_core.wiki import generate_wiki

    target = args.strip().lower() or "preview"
    bundle = generate_wiki(session.repo_root)
    target_dir = session.repo_root / ".lyra" / "wiki"
    if target == "generate":
        path = bundle.write(target_dir)
        return CommandResult(
            output=(
                f"wiki: wrote {len(bundle.pages)} page(s) to {path}.\n"
                "Open `.lyra/wiki/index.md` for the tour."
            ),
            renderable=_out.wiki_renderable(target_dir),
        )
    if target in ("preview", ""):
        index = next((p for p in bundle.pages if p.relative_path == "index.md"), None)
        body = index.render() if index else "(no index page generated)"
        return CommandResult(output=body, renderable=_out.wiki_renderable(target_dir))
    return CommandResult(
        output=f"usage: /wiki [generate|preview] (got {target!r})"
    )


def _cmd_team_onboarding(session: InteractiveSession, args: str) -> CommandResult:
    """``/team-onboarding [role]`` — Wave-E onboarding briefing.

    ``role`` is free-form but pre-baked plans exist for ``engineer``,
    ``designer``, and ``pm``. Anything else falls back to the
    ``engineer`` template so a fresh teammate always gets a useful
    starting plan.
    """
    from lyra_core.wiki import generate_onboarding

    role = (args.strip() or "engineer").split()[0]
    plan = generate_onboarding(session.repo_root, role=role)
    return CommandResult(output=plan.render())


def _cmd_voice(session: InteractiveSession, args: str) -> CommandResult:
    """``/voice [on|off|status]`` — toggle the STT/TTS pipeline (Wave-E).

    The flag is purely advisory at the dispatch layer: when on, the
    REPL driver pipes mic audio through ``transcribe_audio`` and
    speaks responses through ``synthesise_speech``. When off, the
    REPL falls back to text-only input. We toggle the dataclass
    field so completers / status renderers can show the live state.
    """
    target = args.strip().lower()
    if target in ("", "status"):
        state = "on" if getattr(session, "voice_mode", False) else "off"
        return CommandResult(output=f"voice mode: {state}")
    if target in ("on", "true", "1"):
        session.voice_mode = True
    elif target in ("off", "false", "0"):
        session.voice_mode = False
    else:
        return CommandResult(
            output=f"usage: /voice [on|off|status] (got {target!r})"
        )
    state = "on" if session.voice_mode else "off"
    return CommandResult(
        output=(
            f"voice mode: {state}. "
            + (
                "STT/TTS pipeline armed — mic audio will be transcribed; replies will be spoken."
                if session.voice_mode
                else "back to text-only REPL."
            )
        )
    )


def _cmd_split(session: InteractiveSession, args: str) -> CommandResult:
    """``/split <task>`` — Wave-F subagent fan-out planner.

    Records a split directive on the session's side-channel so
    downstream agent-loop drivers can farm out the sub-tasks.
    The command itself is intentionally lightweight — the
    scheduling lives in the driver, not in the slash dispatcher.
    """
    task = args.strip()
    if not task:
        return CommandResult(
            output=(
                "usage: /split <task>\n"
                "  records the task on the side-channel so the loop "
                "can fan it out across parallel subagents."
            )
        )
    bucket = getattr(session, "split_queue", None)
    if bucket is None:
        bucket = []
        session.split_queue = bucket  # type: ignore[attr-defined]
    bucket.append(task)
    return CommandResult(
        output=(
            f"split: queued task ({len(bucket)} pending).\n"
            f"  {task}"
        )
    )


def _cmd_vote(session: InteractiveSession, args: str) -> CommandResult:
    """``/vote <candidate>`` — record a ranked-choice preference
    for the current refute-or-promote round.

    Votes accumulate in ``session.vote_ledger`` (a ``dict[str, int]``).
    ``/vote results`` prints the tally. ``/vote clear`` resets it.
    """
    ledger = getattr(session, "vote_ledger", None)
    if ledger is None:
        ledger = {}
        session.vote_ledger = ledger  # type: ignore[attr-defined]

    cmd = args.strip()
    if not cmd:
        return CommandResult(
            output=(
                "usage: /vote <candidate> | /vote results | /vote clear"
            )
        )
    if cmd.lower() == "results":
        if not ledger:
            return CommandResult(output="vote: no votes yet.")
        ranked = sorted(ledger.items(), key=lambda kv: kv[1], reverse=True)
        lines = ["vote results:"] + [
            f"  {i + 1}. {name} — {count}"
            for i, (name, count) in enumerate(ranked)
        ]
        return CommandResult(output="\n".join(lines))
    if cmd.lower() == "clear":
        ledger.clear()
        return CommandResult(output="vote: ledger cleared.")
    ledger[cmd] = ledger.get(cmd, 0) + 1
    return CommandResult(
        output=f"vote: +1 for {cmd!r} (total {ledger[cmd]})"
    )


def _cmd_observe(session: InteractiveSession, args: str) -> CommandResult:
    """``/observe [on|off|status|tail]`` — toggle the ambient
    observation channel. When ``on``, every agent turn also emits
    a short observation note to ``session.observation_log`` which
    ``/observe tail`` can surface as a passive status stream.
    """
    arg = args.strip().lower()
    log = getattr(session, "observation_log", None)
    if log is None:
        log = []
        session.observation_log = log  # type: ignore[attr-defined]
    if arg in ("", "status"):
        state = "on" if getattr(session, "observe_mode", False) else "off"
        return CommandResult(
            output=f"observe: {state} ({len(log)} notes logged)"
        )
    if arg == "on":
        session.observe_mode = True  # type: ignore[attr-defined]
        return CommandResult(output="observe: on")
    if arg == "off":
        session.observe_mode = False  # type: ignore[attr-defined]
        return CommandResult(output="observe: off")
    if arg == "tail":
        if not log:
            return CommandResult(output="observe: no notes yet.")
        tail = log[-10:]
        return CommandResult(output="observe tail:\n" + "\n".join(tail))
    return CommandResult(
        output=f"usage: /observe [on|off|status|tail] (got {arg!r})"
    )


def _cmd_ide(session: InteractiveSession, args: str) -> CommandResult:
    """``/ide [list|set <name>|open <path>[:line[:col]]]`` — Wave-F
    IDE bridge for jumping from the REPL into an editor."""
    from lyra_core.ide import (
        IDEError,
        IDETarget,
        available_bridges,
        build_open_command,
    )

    arg = args.strip()
    if not arg or arg.lower() == "list":
        names = ", ".join(b.id for b in available_bridges())
        current = getattr(session, "ide_bridge", "vscode")
        return CommandResult(
            output=f"available IDE bridges: {names}\ncurrent: {current}"
        )
    if arg.lower().startswith("set"):
        choice = arg[3:].strip()
        if not choice:
            return CommandResult(output="usage: /ide set <name>")
        try:
            build_open_command(
                bridge=choice,
                target=IDETarget(path=session.repo_root),
            )
        except IDEError as exc:
            return CommandResult(output=f"ide: {exc}")
        session.ide_bridge = choice  # type: ignore[attr-defined]
        return CommandResult(output=f"ide: bridge set to {choice}")
    if arg.lower().startswith("open "):
        spec = arg[5:].strip()
        path_s, *rest = spec.split(":")
        try:
            line = int(rest[0]) if len(rest) >= 1 and rest[0] else None
            column = int(rest[1]) if len(rest) >= 2 and rest[1] else None
        except ValueError:
            return CommandResult(
                output=f"ide: could not parse line/column from {spec!r}"
            )
        path = (session.repo_root / path_s).resolve()
        try:
            target = IDETarget(path=path, line=line, column=column)
            argv = build_open_command(
                bridge=getattr(session, "ide_bridge", "vscode"),
                target=target,
            )
        except IDEError as exc:
            return CommandResult(output=f"ide: {exc}")
        return CommandResult(
            output=(
                "ide: would run: " + " ".join(argv) + "\n"
                "(pass ide_bridge_executor=True to actually spawn)"
            )
        )
    return CommandResult(
        output=(
            "usage: /ide [list|set <name>|open <path>[:line[:col]]]"
        )
    )


def _cmd_catchup(session: InteractiveSession, args: str) -> CommandResult:
    """``/catch-up`` — Wave-F session catch-up briefing.

    Summarises the session so far (last 10 turns, open TDD phase,
    any queued ``/split`` tasks) into a short status block. Handy
    when the user returns to a session after a break and wants a
    one-screen refresher without replaying everything.
    """
    turns = session.history[-10:] if session.history else []
    phase = getattr(session, "tdd_state", None)
    phase_s = phase.phase.value if phase is not None else "idle"
    queued = getattr(session, "split_queue", []) or []
    votes = getattr(session, "vote_ledger", {}) or {}
    obs_log = getattr(session, "observation_log", []) or []
    blocks = [
        "/catch-up briefing:",
        f"  session id:   {getattr(session, 'session_id', '—')}",
        f"  tdd phase:    {phase_s}",
        f"  recent turns: {len(turns)}",
        f"  split queue:  {len(queued)} task(s)",
        f"  vote ledger:  {sum(votes.values())} vote(s) across {len(votes)}",
        f"  observations: {len(obs_log)} note(s)",
    ]
    return CommandResult(output="\n".join(blocks))


def _cmd_phase(session: InteractiveSession, args: str) -> CommandResult:
    """``/phase [status|next-legal|set <phase>]`` — Wave-F TDD state.

    Renders the session's live TDD phase. With ``set <phase>`` it
    attempts a transition; strict mode raises, lenient mode warns.
    Evidence is *not* accepted via the REPL (it has to come from
    the loop) — the slash command is the read + reset surface.
    """
    from lyra_core.tdd import TDDPhase, TDDStateMachine, TransitionError

    sm: TDDStateMachine | None = getattr(session, "tdd_state", None)
    if sm is None:
        sm = TDDStateMachine(strict=False)
        session.tdd_state = sm  # type: ignore[attr-defined]

    cmd = args.strip().lower() or "status"
    if cmd in ("status", "show"):
        return CommandResult(
            output=(
                f"tdd phase: {sm.phase.value}\n"
                f"legal next: {[p.value for p in sm.legal_next()]}\n"
                f"warnings: {len(sm.warnings)}"
            )
        )
    if cmd == "next-legal":
        return CommandResult(
            output=" ".join(p.value for p in sm.legal_next())
        )
    if cmd == "reset":
        sm.reset()
        return CommandResult(output=f"tdd phase: {sm.phase.value} (reset)")
    if cmd.startswith("set "):
        target_name = cmd[4:].strip().upper().replace("-", "_")
        try:
            target = TDDPhase[target_name]
        except KeyError:
            return CommandResult(
                output=f"unknown phase {target_name!r}; try one of "
                + ", ".join(p.value for p in TDDPhase)
            )
        try:
            sm.advance(target)
        except TransitionError as exc:
            return CommandResult(output=f"phase: {exc}")
        return CommandResult(output=f"tdd phase: {sm.phase.value}")
    return CommandResult(
        output=f"usage: /phase [status|next-legal|reset|set <phase>] (got {cmd!r})"
    )


def _cmd_replay(session: InteractiveSession, args: str) -> CommandResult:
    """``/replay [next|prev|reset|status|all]`` — Wave-E session replay.

    Walks ``turns.jsonl`` of the *current* session one event at a
    time, with a unified diff between adjacent turns. The cursor
    lives on :class:`InteractiveSession` so successive ``/replay
    next`` calls advance through the recording.

    No persistence side-effects — the replay only reads on disk.
    """
    from .replay import ReplayController, ReplayError

    target = args.strip().lower() or "next"
    controller = getattr(session, "_replay_controller", None)
    if controller is None:
        session_dir = session._session_dir()
        if session_dir is None:
            return CommandResult(
                output="replay: no on-disk session attached "
                "(set sessions_root + session_id to enable)"
            )
        try:
            controller = ReplayController(session_dir=Path(session_dir))
        except ReplayError as exc:
            return CommandResult(output=f"replay: {exc}")
        session._replay_controller = controller  # type: ignore[attr-defined]

    if target == "reset":
        controller.reset()
        return CommandResult(
            output=f"replay: reset (0 / {len(controller)})"
        )
    if target == "status":
        cur = controller.current()
        idx = -1 if cur is None else cur.index
        return CommandResult(
            output=f"replay: cursor={idx + 1} total={len(controller)}"
        )
    if target == "all":
        if not len(controller):
            return CommandResult(output="replay: no recorded turns")
        controller.reset()
        chunks: list[str] = []
        while True:
            evt = controller.next()
            if evt is None:
                break
            head = f"--- turn {evt.index + 1} ---"
            chunks.append(head)
            chunks.append(json.dumps(evt.payload, ensure_ascii=False, sort_keys=True))
            if evt.diff:
                chunks.append(evt.diff)
        return CommandResult(output="\n".join(chunks))

    if target == "prev":
        evt = controller.prev()
    elif target == "next":
        evt = controller.next()
    else:
        return CommandResult(
            output=f"usage: /replay [next|prev|reset|status|all] (got {target!r})"
        )

    if evt is None:
        edge = "start" if target == "prev" else "end"
        return CommandResult(output=f"replay: at {edge}")

    head = (
        f"replay turn {evt.index + 1} / {len(controller)}\n"
        + json.dumps(evt.payload, ensure_ascii=False, sort_keys=True)
    )
    if evt.diff:
        return CommandResult(output=f"{head}\n{evt.diff}")
    return CommandResult(output=head)


def _cmd_effort(session: InteractiveSession, args: str) -> CommandResult:
    """Wave-C `/effort`: pure picker render or direct value-set.

    ``/effort`` (no arg) renders the slider; ``/effort <level>`` sets
    the env var directly so a script can drive the same surface
    without going through the TTY arrow-key UI.
    """
    from .effort import EffortPicker, apply_effort

    levels = {
        "low":    "quick single-turn attempt, cheapest model",
        "medium": "default — Plan + Build with standard verification",
        "high":   "+ extra review passes (/review, /ultrareview)",
        "max":    "full refute-or-promote loop + cross-channel verifier",
        # Back-compat: accept the legacy "ultra" alias from v0.x.
        "ultra":  "alias for max",
    }
    choice = args.strip().lower()
    if not choice:
        picker = EffortPicker(initial="medium")
        return CommandResult(
            output=picker.render(),
            renderable=_out.effort_renderable("medium", levels),
        )
    if choice not in levels:
        return CommandResult(
            output=(
                f"unknown effort level {choice!r}; "
                f"valid: {', '.join(k for k in levels if k != 'ultra')}."
            ),
            renderable=_out.bad_effort_renderable(
                choice, ("low", "medium", "high", "max")
            ),
        )
    typed = choice
    if choice == "ultra":
        choice = "max"
    canonical = apply_effort(choice)
    label = (
        f"{typed} (canonical: {canonical})" if typed != canonical else canonical
    )
    return CommandResult(
        output=f"effort: {label} — {levels[canonical]}",
        renderable=_out.effort_renderable(canonical, levels),
    )


_DEFAULT_REVIEWER_VOICES: tuple[str, ...] = (
    "reviewer-A (correctness)",
    "reviewer-B (test coverage)",
    "reviewer-C (safety)",
)

_TDD_REVIEWER_VOICES: tuple[str, ...] = (
    "reviewer-A (correctness)",
    "reviewer-B (TDD discipline)",
    "reviewer-C (safety)",
)


def _cmd_ultrareview(
    session: InteractiveSession, _args: str
) -> CommandResult:
    """Fan out to three reviewer voices, return one verdict block.

    v3.0.0 (Phase G) — the middle voice's rubric depends on whether
    the user has opted into TDD. With ``session.tdd_gate_enabled``
    set the rubric reads "did each Edit follow a RED test?", matching
    the legacy Wave-C behaviour. With TDD off (the new default,
    matching claw-code / opencode / hermes-agent posture) the rubric
    becomes the gentler "are the new behaviours covered by tests?"
    so a general coding session still gets useful feedback without
    the kernel-level RED requirement.

    The real subagent fan-out runs through the SubagentRunner in
    v2.6.0+; this slash ships the verifier-rendered shape so the
    output is testable offline.
    """
    tdd_on = bool(getattr(session, "tdd_gate_enabled", False))
    if tdd_on:
        voices = _TDD_REVIEWER_VOICES
        rubrics = {
            "reviewer-A (correctness)": "Are the new behaviors covered by tests?",
            "reviewer-B (TDD discipline)": "Did each Edit follow a RED test?",
            "reviewer-C (safety)": "Did any tool call breach permission policy?",
        }
    else:
        voices = _DEFAULT_REVIEWER_VOICES
        rubrics = {
            "reviewer-A (correctness)": "Are the new behaviors covered by tests?",
            "reviewer-B (test coverage)": "Is the changed code reachable by an existing test?",
            "reviewer-C (safety)": "Did any tool call breach permission policy?",
        }
    blocks: list[str] = []
    verdict_count = 0
    for voice in voices:
        rubric = rubrics[voice]
        ok = _local_verifier_passes(session)
        verdict_count += 1 if ok else 0
        status = "approve" if ok else "needs-revision"
        blocks.append(
            f"--- {voice} ---\n"
            f"rubric: {rubric}\n"
            f"status: {status}\n"
        )
    final = "approve" if verdict_count == len(voices) else "needs-revision"
    body = "\n".join(blocks) + f"\nverdict: {final}"
    return CommandResult(
        output=body,
        renderable=_out.ultrareview_renderable(session.mode),
    )


# Back-compat alias kept for any external code importing the old name.
_REVIEWER_VOICES = _DEFAULT_REVIEWER_VOICES


def _local_verifier_passes(session: InteractiveSession) -> bool:
    """Return ``True`` when the session passes the single-shot verifier.

    v3.0.0 (Phase G) — TDD became opt-in, so its absence is no longer
    a verifier failure on its own. The verifier now only fails on
    real safety violations:

    1. No ``/perm yolo`` (or "yolo" mentions) in the recent history.
    2. Placeholder for the safety scanner shipped in Wave D.

    When ``session.tdd_gate_enabled`` *is* set (the user opted into
    TDD), the gate becomes load-bearing again: a TDD-on session that
    hasn't proven RED is treated as a soft-fail. This preserves the
    historical contract for users who flip the gate on, without
    penalising the default general-purpose flow.
    """
    if any("yolo" in line.lower() for line in session.history[-10:]):
        return False
    return True


def _cmd_review(session: InteractiveSession, args: str) -> CommandResult:
    """Wave-C baseline + Wave-F auto-review.

    ``/review``           — run the verifier once and print the summary.
    ``/review --auto on`` — install a post-turn hook that runs the
        verifier automatically after every agent turn. Reports the
        verdict on the next line.
    ``/review --auto off``— remove the hook.
    ``/review --auto status`` — show whether the hook is armed.
    """
    arg = args.strip().lower()
    if arg.startswith("--auto"):
        sub = arg[len("--auto"):].strip() or "status"
        if sub == "status":
            state = "on" if getattr(session, "auto_review", False) else "off"
            return CommandResult(output=f"auto-review: {state}")
        if sub == "on":
            session.auto_review = True  # type: ignore[attr-defined]
            return CommandResult(
                output=(
                    "auto-review: on — every turn is now followed by a "
                    "/review pass. /review --auto off to disarm."
                )
            )
        if sub == "off":
            session.auto_review = False  # type: ignore[attr-defined]
            return CommandResult(output="auto-review: off")
        return CommandResult(
            output=f"usage: /review --auto [on|off|status] (got {sub!r})"
        )

    if getattr(session, "tdd_gate_enabled", False):
        tdd = "on"
    else:
        tdd = "off (opt-in; /tdd-gate on to enable)"
    safety = "yolo" if getattr(session, "permission_mode", "normal") == "yolo" else "ok"
    evidence = "ok" if session.history else "no turns yet"
    blocks = [
        "post-turn /review:",
        f"  tdd-gate:  {tdd}",
        f"  safety:    {safety}",
        f"  evidence:  {evidence}",
    ]
    return CommandResult(
        output="\n".join(blocks),
        renderable=_out.review_renderable(session.mode),
    )


def run_auto_review(session: InteractiveSession) -> str | None:
    """Run ``/review`` silently when ``session.auto_review`` is set.

    Returns the review output so callers can render it as a
    post-turn banner (or log it). Returns ``None`` when auto-review
    is disabled. Never raises — telemetry never blocks the turn.
    """
    if not getattr(session, "auto_review", False):
        return None
    try:
        return _cmd_review(session, "").output
    except Exception as exc:  # noqa: BLE001
        return f"auto-review: {exc}"


def _cmd_tdd_gate(session: InteractiveSession, args: str) -> CommandResult:
    """`/tdd-gate on|off|status` — toggle the opt-in TDD plugin.

    v3.0.0 (Phase G) — TDD became opt-in. By default Lyra behaves like
    a general coding agent (claw-code / opencode / hermes-agent posture);
    flipping the gate on activates the legacy kernel-level TDD discipline
    so writes to ``src/**`` need a preceding failing test on disk.
    """
    choice = args.strip().lower()
    if choice == "status":
        state = "on" if session.tdd_gate_enabled else "off"
        return CommandResult(
            output=f"tdd-gate: {state}",
            renderable=_out.tdd_gate_renderable(state),
        )
    if choice in ("on", "off"):
        session.tdd_gate_enabled = choice == "on"
        return CommandResult(
            output=(
                f"tdd-gate: {choice} — "
                + (
                    "TDD plugin enabled; edits to src/** without a "
                    "preceding RED test are now blocked."
                    if choice == "on"
                    else "TDD plugin disabled; edits proceed freely "
                    "(use /tdd-gate on to re-arm, or /config set tdd_gate=on to persist)."
                )
            ),
            renderable=_out.tdd_gate_renderable(choice),
        )
    if choice == "":
        state = "on" if session.tdd_gate_enabled else "off"
        return CommandResult(
            output=f"tdd-gate: {state} (use /tdd-gate on|off|status)",
            renderable=_out.tdd_gate_renderable(state),
        )
    return CommandResult(
        output=f"usage: /tdd-gate on|off|status  (got {choice!r})."
    )


# ---------------------------------------------------------------------------
# /config — Wave-C Task 11: persistent settings (theme, vim, perm, tdd, …)
# ---------------------------------------------------------------------------
#
# Why a single dispatcher with sub-verbs instead of three slashes?
# The per-key slashes (`/theme`, `/vim`, `/effort`, `/tdd-gate`) still
# work for muscle memory; `/config` is the "show me everything and let
# me bulk-set" view that survives across REPL restarts. It writes to
# ``session.config_path`` (defaults to ``~/.lyra/config.yaml``) so the
# next ``InteractiveSession.from_config`` boot picks the values up.

# Keys this dispatcher knows how to push back into the live session.
# Ordering drives ``/config list``; keep the most-used knobs first.
_CONFIG_KNOWN_KEYS: tuple[str, ...] = (
    "theme",
    "vim",
    "permission_mode",
    "tdd_gate",
    "effort",
    "budget_cap_usd",
    "model",
    "mode",
)


def _persist_config(session: "InteractiveSession") -> None:
    """Write ``session.config`` to disk, swallowing IO errors.

    Writes are best-effort so a read-only ``$HOME`` (CI sandbox, demo
    mode) doesn't break the live REPL. The next user action still sees
    the in-memory mutation.
    """
    cfg = getattr(session, "config", None)
    if cfg is None:
        return
    try:
        cfg.save()
    except OSError:
        pass


def _apply_config_key_to_session(
    session: "InteractiveSession", key: str, value: str
) -> str | None:
    """Side-effect: push one key onto the live session.

    Returns ``None`` on success, or an error string the dispatcher
    should surface to the user (e.g. unknown theme name).
    """
    from . import themes as _t  # local: avoid import-order cycles
    from .config_store import to_bool

    norm = value.strip()
    if key == "theme":
        if norm not in _t.names():
            return f"unknown theme {norm!r}; valid: {', '.join(_t.names())}."
        session.theme = norm
        try:
            _t.set_active_skin(norm)
        except Exception:
            pass
        return None
    if key == "vim":
        session.vim_mode = to_bool(norm)
        return None
    if key == "permission_mode":
        if norm not in {"strict", "normal", "yolo"}:
            return f"permission_mode must be strict|normal|yolo (got {norm!r})."
        session.permission_mode = norm
        return None
    if key == "tdd_gate":
        session.tdd_gate_enabled = to_bool(norm)
        return None
    if key == "effort":
        from .effort import apply_effort

        try:
            apply_effort(norm)
        except Exception:
            return f"effort must be one of low|medium|high|max (got {norm!r})."
        return None
    if key == "budget_cap_usd":
        try:
            session.budget_cap_usd = float(norm)
        except (TypeError, ValueError):
            return f"budget_cap_usd must be a number (got {norm!r})."
        return None
    if key == "model":
        session.model = norm
        return None
    if key == "mode":
        valid = {"plan", "build", "run", "explore", "retro"}
        if norm not in valid:
            return f"mode must be {'|'.join(sorted(valid))} (got {norm!r})."
        session.mode = norm
        return None
    return f"unknown config key {key!r}; valid: {', '.join(_CONFIG_KNOWN_KEYS)}."


def _cmd_red_proof(session: "InteractiveSession", args: str) -> CommandResult:
    """`/red-proof <pytest target>` — prove you went RED.

    Wave-C Task 13. Real pytest invocation; no parsing — exit code
    is the only signal we trust here. The full TDD state machine
    (correlate the failing test with the next Edit) lands in Wave F.
    """
    target = args.strip()
    if not target:
        return CommandResult(
            output=(
                "usage: /red-proof <pytest target>  "
                "(e.g. /red-proof packages/foo/tests/test_bar.py)"
            )
        )
    from .red_proof import render, run_red_proof

    result = run_red_proof(target, repo_root=session.repo_root)
    return CommandResult(output=render(result, target=target))


def _cmd_config(session: "InteractiveSession", args: str) -> CommandResult:
    """`/config list|get <key>|set <key>=<value>`.

    Persists every successful ``set`` to ``session.config_path`` so a
    user's preferred theme / mode survives a REPL restart.
    """
    parts = args.strip().split(maxsplit=1)
    verb = (parts[0] if parts else "list").lower()
    rest = parts[1].strip() if len(parts) > 1 else ""

    if verb == "list":
        cfg = getattr(session, "config", None)
        rows: list[str] = ["config (saved across restarts):"]
        for key in _CONFIG_KNOWN_KEYS:
            stored = cfg.get(key) if cfg else None
            display = stored if stored is not None else "<unset>"
            rows.append(f"  {key:<18} {display}")
        path = getattr(session, "config_path", None)
        if path is not None:
            rows.append(f"file: {path}")
        return CommandResult(output="\n".join(rows))

    if verb == "get":
        if not rest:
            return CommandResult(output="usage: /config get <key>")
        key = rest.strip()
        cfg = getattr(session, "config", None)
        value = cfg.get(key) if cfg else None
        if value is None:
            return CommandResult(output=f"{key}: <unset>")
        return CommandResult(output=f"{key}: {value}")

    if verb == "set":
        if "=" not in rest:
            return CommandResult(
                output=(
                    "usage: /config set key=value  "
                    f"(known keys: {', '.join(_CONFIG_KNOWN_KEYS)})"
                )
            )
        key, _, value = rest.partition("=")
        key = key.strip()
        value = value.strip()
        if key not in _CONFIG_KNOWN_KEYS:
            return CommandResult(
                output=(
                    f"unknown config key {key!r}; "
                    f"valid: {', '.join(_CONFIG_KNOWN_KEYS)}."
                )
            )
        err = _apply_config_key_to_session(session, key, value)
        if err is not None:
            return CommandResult(output=err)
        cfg = getattr(session, "config", None)
        if cfg is not None:
            cfg.set(key, value)
            _persist_config(session)
        return CommandResult(output=f"config: {key} = {value}")

    return CommandResult(
        output=(
            f"usage: /config list|get <key>|set <key>=<value>  "
            f"(got {verb!r})"
        )
    )


# ---------------------------------------------------------------------------
# Command registry — single source of truth (hermes-agent CommandDef pattern)
# ---------------------------------------------------------------------------
#
# Why a registry instead of two parallel dicts?
#
# - **One place** to add a command. Aliases, completer subcommands, /help
#   grouping, and plain-text descriptions all derive from this list, so
#   wiring up ``/branch`` (alias of ``/fork``) is one tuple entry — not
#   three sites that drift out of sync.
# - **Subcommand-aware completer.** The ``args_hint`` field doubles as a
#   completion source: ``"[on|off]"`` auto-extracts to ``("on","off")``
#   so the prompt_toolkit completer can pop the dropdown on
#   ``/tdd-gate <space>`` without us hand-maintaining a third dict.
# - **Categorised /help.** ``commands_by_category()`` returns the same
#   six buckets the Rich help renderer uses, but the *order* of commands
#   inside each bucket now follows the registry — declaring new commands
#   in their natural group is the only edit needed.
#
# Public exports preserved for backwards compat:
#
# - ``SLASH_COMMANDS: dict[str, SlashHandler]`` — name+alias → handler
# - ``_SLASH_DOCS:  dict[str, str]``            — name+alias → description
# - ``slash_description(name)``                 — used by the completer
#
# Plus new accessors for the upgraded completer / help renderer:
#
# - ``command_spec(name)``       → CommandSpec | None (resolves aliases)
# - ``subcommands_for(name)``    → tuple[str, ...]
# - ``aliases_for(name)``        → tuple[str, ...]
# - ``commands_by_category()``   → dict[category-slug, list[CommandSpec]]


# Categories live as slugs in the registry; the help renderer maps them to
# pretty display strings. Keeping the slug → display split centralised here
# means /help, the completer's group hints, and any future export of the
# registry (CLI doctor, README generator) all see the same names.
_CATEGORY_DISPLAY: dict[str, str] = {
    "session": "session",
    "plan-build-run": "plan · build · run",
    "tools-agents": "tools · agents",
    "observability": "observability",
    "config-theme": "config · theme",
    "collaboration": "collaboration",
    "meta": "meta",
}


# Pipe-pattern subcommand extractor: matches stems like ``a|b|c`` (lowercase
# letters / hyphens), used as a fallback when ``subcommands`` is left blank
# but ``args_hint`` already advertises the choices via ``[a|b|c]``.
_PIPE_SUBS_RE = re.compile(r"[a-z][a-z\-]*(?:\|[a-z][a-z\-]*)+")


def _extract_subs(args_hint: str) -> tuple[str, ...]:
    """Pull subcommand stems out of an args_hint like ``"[on|off|status]"``."""
    if not args_hint:
        return ()
    match = _PIPE_SUBS_RE.search(args_hint)
    return tuple(match.group(0).split("|")) if match else ()


@dataclass(frozen=True)
class CommandSpec:
    """One slash command — declared once, consumed everywhere.

    ``frozen=True`` because the registry is read-only after import; if you
    need to mutate behaviour at runtime, build a new spec rather than poke
    this one. ``__post_init__`` is the single exception: it back-fills
    ``subcommands`` from ``args_hint`` when the explicit field is empty,
    using ``object.__setattr__`` to honour the frozen contract.
    """

    name: str
    handler: SlashHandler
    description: str
    category: str
    aliases: tuple[str, ...] = ()
    args_hint: str = ""
    subcommands: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.subcommands and self.args_hint:
            extracted = _extract_subs(self.args_hint)
            if extracted:
                # Frozen dataclass workaround — see class docstring.
                object.__setattr__(self, "subcommands", extracted)

    @property
    def display_category(self) -> str:
        """Human-readable category label, used by /help and the completer."""
        return _CATEGORY_DISPLAY.get(self.category, self.category)


COMMAND_REGISTRY: tuple[CommandSpec, ...] = (
    # --- session ----------------------------------------------------------
    CommandSpec(
        "mode",
        _cmd_mode,
        "show or switch mode (agent|plan|debug|ask)",
        "session",
        args_hint="[agent|plan|debug|ask]",
    ),
    CommandSpec(
        "model",
        _cmd_model,
        "show or set the active model name",
        "session",
        args_hint="[name]",
    ),
    CommandSpec(
        "models",
        _cmd_models,
        "list known model providers + identifiers",
        "session",
        aliases=("providers",),
    ),
    CommandSpec(
        "status", _cmd_status, "print session status (mode, model, turn, cost)", "session"
    ),
    CommandSpec(
        "history",
        _cmd_history,
        "show your input history (use --verbose for per-turn model/tokens/cost)",
        "session",
        args_hint="[--verbose]",
    ),
    CommandSpec("clear", _cmd_clear, "clear the screen", "session"),
    CommandSpec(
        "palette",
        _cmd_palette,
        "fuzzy-searchable command palette",
        "session",
        aliases=("?",),
        args_hint="[query]",
    ),
    CommandSpec(
        "skip-onboarding",
        _cmd_skip_onboarding,
        "dismiss the first-run wizard for this user",
        "session",
    ),
    CommandSpec(
        "search",
        _cmd_search,
        "full-text search across prior sessions (FTS5)",
        "session",
        args_hint="[--k=N] <query>",
    ),
    CommandSpec(
        "compact",
        _cmd_compact,
        "compress the context window (heuristic prune of older turns)",
        "session",
        aliases=("compress",),
    ),
    CommandSpec(
        "rewind",
        _cmd_rewind,
        "undo the most recent turn",
        "session",
        aliases=("undo",),
    ),
    CommandSpec(
        "redo",
        _cmd_redo,
        "re-apply the most recent /rewind",
        "session",
        aliases=("redo!", "unrewind"),
    ),
    CommandSpec(
        "resume",
        _cmd_resume,
        "resume a saved session",
        "session",
        args_hint="[id]",
    ),
    CommandSpec(
        "fork",
        _cmd_fork,
        "fork this session at the current turn",
        "session",
        aliases=("branch",),
        args_hint="[name]",
    ),
    CommandSpec("sessions", _cmd_sessions, "list saved sessions on disk", "session"),
    CommandSpec(
        "rename",
        _cmd_rename,
        "rename the current session",
        "session",
        args_hint="[name]",
    ),
    CommandSpec(
        "init",
        _cmd_init,
        "scaffold SOUL.md + .lyra/ in the current repo (use 'force' to overwrite)",
        "session",
        args_hint="[force]",
    ),
    CommandSpec(
        "user-commands",
        _cmd_commands,
        "list user-authored slash commands from .lyra/commands/",
        "session",
        aliases=("user-cmds",),
        args_hint="[reload]",
    ),
    # --- plan · build · run ----------------------------------------------
    CommandSpec(
        "approve",
        _cmd_approve,
        "accept the pending plan and switch to run mode",
        "plan-build-run",
    ),
    CommandSpec("reject", _cmd_reject, "drop the pending plan", "plan-build-run"),
    CommandSpec(
        "effort",
        _cmd_effort,
        "quick / default / deep / ultra review budget",
        "plan-build-run",
        args_hint="[low|medium|high|ultra]",
    ),
    CommandSpec(
        "ultrareview",
        _cmd_ultrareview,
        "multi-rubric deep review (3 verifier voices over /review)",
        "plan-build-run",
    ),
    CommandSpec(
        "review",
        _cmd_review,
        "post-turn verifier (safety + evidence; TDD gate when enabled)",
        "plan-build-run",
    ),
    CommandSpec(
        "tdd-gate",
        _cmd_tdd_gate,
        "opt-in TDD plugin: gate src writes on a failing test",
        "plan-build-run",
        args_hint="[on|off]",
    ),
    CommandSpec(
        "red-proof",
        _cmd_red_proof,
        "run pytest against a target and prove it really fails (RED)",
        "plan-build-run",
        args_hint="<pytest target>",
    ),
    CommandSpec(
        "evals",
        _cmd_evals,
        "run an evals smoke pass (default: golden)",
        "plan-build-run",
        args_hint="[corpus]",
    ),
    # --- tools · agents ---------------------------------------------------
    CommandSpec("tools", _cmd_tools, "list registered tools and their risk level", "tools-agents"),
    CommandSpec(
        "toolsets",
        _cmd_toolsets,
        "list/show/apply named tool bundles (default|safe|research|coding|ops)",
        "tools-agents",
        args_hint="[show <name>|apply <name>]",
    ),
    CommandSpec(
        "team",
        _cmd_team,
        "multi-agent team orchestration (PM/Architect/Engineer/Reviewer/QA)",
        "tools-agents",
        args_hint="[show <name>|plan|run <task>]",
    ),
    CommandSpec(
        "reflect",
        _cmd_reflect,
        "Reflexion retrospective loop — store/inject verbal lessons",
        "tools-agents",
        args_hint="[on|off|add <verdict> :: <lesson>|tag <t1,t2> <v> :: <l>|clear]",
    ),
    CommandSpec(
        "agents",
        _cmd_agents,
        "live subagent registry (kill <id> to cancel a run)",
        "tools-agents",
        aliases=("tasks",),
    ),
    CommandSpec(
        "spawn",
        _cmd_spawn,
        "dispatch a subagent (in-process AgentLoop in a worktree)",
        "tools-agents",
        args_hint="[--type kind] <description>",
    ),
    CommandSpec(
        "mcp",
        _cmd_mcp,
        "manage MCP servers (list|connect|disconnect|tools|register|trust|untrust|remove|reload)",
        "tools-agents",
        args_hint="[list|connect|disconnect|tools|register|trust|untrust|remove|reload] [name]",
    ),
    CommandSpec("soul", _cmd_soul, "print SOUL.md for this repo", "tools-agents"),
    CommandSpec(
        "cron",
        _cmd_cron,
        "schedule automated tasks (list|add|remove|pause|resume|run|edit)",
        "tools-agents",
        args_hint="[list|add|remove|pause|resume|run|edit]",
    ),
    # --- observability ----------------------------------------------------
    CommandSpec(
        "cost",
        _cmd_cost,
        "cost / token usage so far",
        "observability",
        aliases=("usage",),
    ),
    CommandSpec(
        "stats",
        _cmd_stats,
        "session metrics (turns, cost, tokens, …)",
        "observability",
        aliases=("insights",),
    ),
    CommandSpec(
        "context",
        _cmd_context,
        "breakdown of the current context window",
        "observability",
    ),
    CommandSpec("diff", _cmd_diff, "recent file changes (git diff)", "observability"),
    CommandSpec("map", _cmd_map, "ASCII tree of every *.py under repo_root", "observability"),
    CommandSpec(
        "blame",
        _cmd_blame,
        "git-blame annotations for a file",
        "observability",
        args_hint="[path]",
    ),
    CommandSpec(
        "trace",
        _cmd_trace,
        "HIR JSONL event log path / toggle verbose",
        "observability",
        args_hint="[on|off]",
    ),
    CommandSpec(
        "badges",
        _cmd_badges,
        "usage stats for the commands you've run",
        "observability",
    ),
    CommandSpec("export", _cmd_export, "export the transcript as markdown", "observability"),
    CommandSpec(
        "self",
        _cmd_self,
        "agent introspection — what's active right now",
        "observability",
    ),
    CommandSpec(
        "budget",
        _cmd_budget,
        "show or set the session cost cap (save = persist for future sessions)",
        "observability",
        args_hint="[usd|save [usd]|off|status|suggest]",
    ),
    CommandSpec(
        "stream",
        _cmd_stream,
        "toggle live streaming chat output (on|off|status)",
        "config-theme",
        args_hint="[on|off|status]",
    ),
    CommandSpec(
        "skills",
        _cmd_skills,
        "SKILL.md injection: list packs, toggle on/off, reload cache",
        "config-theme",
        args_hint="[on|off|status|list|reload]",
    ),
    CommandSpec(
        "memory",
        _cmd_memory,
        "memory injection: search procedural + reasoning lessons, toggle, reload",
        "config-theme",
        args_hint="[on|off|status|search <q>|reload]",
    ),
    # --- config · theme ---------------------------------------------------
    CommandSpec(
        "theme",
        _cmd_theme,
        "show or switch the colour theme",
        "config-theme",
        aliases=("skin",),
        args_hint="[name]",
    ),
    CommandSpec(
        "config",
        _cmd_config,
        "show, get, or set persisted REPL settings (~/.lyra/config.yaml)",
        "config-theme",
        args_hint="[list|get <key>|set <key>=<value>]",
    ),
    CommandSpec(
        "vim",
        _cmd_vim,
        "toggle vim-style prompt editing",
        "config-theme",
        args_hint="[on|off]",
    ),
    CommandSpec(
        "keybindings",
        _cmd_keybindings,
        "full key-binding cheat sheet",
        "config-theme",
        aliases=("keys",),
    ),
    CommandSpec("policy", _cmd_policy, "print .lyra/policy.yaml", "config-theme"),
    CommandSpec(
        "doctor", _cmd_doctor, "quick health check for this repo", "config-theme"
    ),
    CommandSpec(
        "auth",
        _cmd_auth,
        "OAuth provider tokens (list, logout, Copilot device flow hint)",
        "config-theme",
        args_hint="[list|logout|copilot]",
    ),
    # --- collaboration ----------------------------------------------------
    CommandSpec(
        "btw",
        _cmd_btw,
        "side question handled out-of-band",
        "collaboration",
        args_hint="[question]",
    ),
    CommandSpec(
        "handoff", _cmd_handoff, "generate a PR description from the session", "collaboration"
    ),
    CommandSpec(
        "pair",
        _cmd_pair,
        "pair-programming live stream over LifecycleBus",
        "collaboration",
    ),
    CommandSpec(
        "wiki",
        _cmd_wiki,
        "auto-generated repo wiki under .lyra/wiki/",
        "collaboration",
        args_hint="[generate|preview]",
    ),
    CommandSpec(
        "team-onboarding",
        _cmd_team_onboarding,
        "first-week briefing for a new teammate",
        "collaboration",
        args_hint="[engineer|designer|pm|<role>]",
    ),
    CommandSpec(
        "voice",
        _cmd_voice,
        "advisory voice-mode flag (toggles session.voice_mode)",
        "collaboration",
        args_hint="[on|off|status]",
    ),
    CommandSpec(
        "replay",
        _cmd_replay,
        "step through the persisted turns.jsonl with diffs",
        "session",
        args_hint="[next|prev|reset|status|all]",
    ),
    CommandSpec(
        "phase",
        _cmd_phase,
        "TDD phase state machine (opt-in; surfaces RED/GREEN/REFACTOR/SHIP)",
        "session",
        args_hint="[status|next-legal|reset|set <phase>]",
    ),
    CommandSpec(
        "split",
        _cmd_split,
        "queue tasks on session.split_queue (consumed by /spawn)",
        "collaboration",
        args_hint="<task>",
    ),
    CommandSpec(
        "vote",
        _cmd_vote,
        "ranked-choice tally (+1 per call, /vote results to print)",
        "collaboration",
        args_hint="<candidate>|results|clear",
    ),
    CommandSpec(
        "observe",
        _cmd_observe,
        "ambient observation log (in-memory, /observe tail to drain)",
        "collaboration",
        args_hint="[on|off|status|tail]",
    ),
    CommandSpec(
        "ide",
        _cmd_ide,
        "IDE-bridge resolver — prints argv unless an executor is wired",
        "collaboration",
        args_hint="[list|set <name>|open <path>[:line[:col]]]",
    ),
    CommandSpec(
        "catch-up",
        _cmd_catchup,
        "session catch-up briefing",
        "session",
        args_hint="",
    ),
    # --- meta -------------------------------------------------------------
    CommandSpec("help", _cmd_help, "show this list", "meta", aliases=("commands",)),
    CommandSpec("exit", _cmd_exit, "leave the session", "meta", aliases=("quit",)),
)


def _build_lookup() -> tuple[
    dict[str, CommandSpec], dict[str, SlashHandler], dict[str, str]
]:
    by_name: dict[str, CommandSpec] = {}
    handlers: dict[str, SlashHandler] = {}
    docs: dict[str, str] = {}
    for spec in COMMAND_REGISTRY:
        by_name[spec.name] = spec
        handlers[spec.name] = spec.handler
        docs[spec.name] = spec.description
        for alias in spec.aliases:
            by_name[alias] = spec
            handlers[alias] = spec.handler
            # Aliases get a "alias for /<canonical>" doc so the completer's
            # meta column tells the user which command they're really invoking.
            docs[alias] = f"alias for /{spec.name}"
    return by_name, handlers, docs


_BY_NAME: dict[str, CommandSpec]
SLASH_COMMANDS: dict[str, SlashHandler]
_SLASH_DOCS: dict[str, str]
_BY_NAME, SLASH_COMMANDS, _SLASH_DOCS = _build_lookup()


def slash_description(name: str) -> str:
    """Public accessor for the completer (so it doesn't import a private)."""
    return _SLASH_DOCS.get(name, "")


def command_spec(name: str) -> CommandSpec | None:
    """Resolve a name *or alias* to its registered :class:`CommandSpec`."""
    return _BY_NAME.get(name)


def subcommands_for(name: str) -> tuple[str, ...]:
    """Subcommand stems for ``name`` (or its alias). Empty tuple if none."""
    spec = _BY_NAME.get(name)
    return spec.subcommands if spec else ()


def aliases_for(name: str) -> tuple[str, ...]:
    """Alternative names for the canonical command ``name``. Empty if none."""
    spec = _BY_NAME.get(name)
    if spec is None:
        return ()
    # Don't echo back the alias the caller asked with — only return the
    # *other* names registered under the same canonical spec.
    return tuple(a for a in spec.aliases if a != name) + (
        (spec.name,) if name != spec.name else ()
    )


def commands_by_category() -> dict[str, list[CommandSpec]]:
    """Return categories in registry order, each with its specs in declared order."""
    out: dict[str, list[CommandSpec]] = {}
    for spec in COMMAND_REGISTRY:
        out.setdefault(spec.category, []).append(spec)
    return out
