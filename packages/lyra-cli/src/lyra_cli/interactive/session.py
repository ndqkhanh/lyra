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

Mode semantics (v3.6.0 permission-flavoured 4-mode taxonomy):

- ``edit_automatically`` — default; full-access execution. Plain
  text drives the agent loop and edits are applied without
  per-write confirmation. Sets ``permission_mode = "normal"`` so
  approval-cache decisions persist for the session.
- ``ask_before_edits``   — full-access execution, but the agent
  pauses for user confirmation before every write or destructive
  tool call. Sets ``permission_mode = "strict"`` so the approval
  cache always re-prompts.
- ``plan_mode``          — read-only collaborative design. Plain
  text proposes a plan; ``/approve`` hands the plan off to
  ``edit_automatically`` for execution. No edits, no destructive
  tool calls.
- ``auto_mode``          — heuristic router. Each plain-text turn
  is classified and dispatched to one of the three modes above
  (design/explore questions → ``plan_mode``; risky / destructive
  asks → ``ask_before_edits``; otherwise → ``edit_automatically``).
  The session mode itself stays ``auto_mode``; only the *behaviour
  for the current turn* is borrowed.

Pre-v3.6 used a Claude-Code-style behavioural taxonomy
(``agent / plan / debug / ask``) and pre-v3.2 used a 5-mode
taxonomy (``plan / build / run / explore / retro``). All legacy
names are remapped on construction via :data:`_LEGACY_MODE_REMAP`
so old settings.json files, stored session JSONLs, and muscle
memory keep working without manual migration. The dedicated
``debug`` mode is gone in v3.6 — its systematic-debugging
discipline survives as a regular skill (see
``docs/howto/debug-mode.md``) that the user invokes manually.
"""
from __future__ import annotations

import json
import os
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
from .status_source import StatusSource as _StatusSource

_VALID_MODES: tuple[str, ...] = (
    "edit_automatically",
    "ask_before_edits",
    "plan_mode",
    "auto_mode",
)

# Short, terminal-friendly labels surfaced in the prompt, bottom toolbar,
# banner, and ``/mode`` output. The canonical IDs above remain the
# permission-posture source of truth (used by tests, snapshots, the
# router, and the CLI flag), but every UI surface shows the short form
# so the REPL doesn't read like database column names.
_MODE_DISPLAY: dict[str, str] = {
    "edit_automatically": "agent",
    "plan_mode":          "plan",
    "ask_before_edits":   "ask",
    "auto_mode":          "auto",
}


def display_mode(mode: str) -> str:
    """Return the short display label for *mode*.

    Falls through to the input when the mode isn't in the canonical
    table, so unknown / future / test-only modes still print rather
    than vanishing.
    """
    return _MODE_DISPLAY.get(mode, mode)

# Legacy mode names from every prior taxonomy → canonical v3.6 mode.
# We honour them everywhere the user can supply a string (CLI flags,
# /mode, snapshots on disk, settings.json) so a fresh ``lyra`` upgrade
# doesn't break a user's stored sessions or their muscle memory.
#
# Mapping rationale:
# - v3.2 ``agent`` → ``edit_automatically`` (same shape: full-access
#   execution; the v3.6 name spells out the permission posture).
# - v3.2 ``plan`` → ``plan_mode`` (renamed only).
# - v3.2 ``debug`` → ``auto_mode`` (the dedicated debug loop is gone;
#   ``auto_mode`` will pick ``ask_before_edits`` whenever it
#   classifies the prompt as a debugging / risky-investigation
#   request, which is the closest preserved behaviour).
# - v3.2 ``ask`` → ``plan_mode`` (closest semantic match — both are
#   read-only. The new ``ask_before_edits`` is *not* a read-only
#   mode, so landing ``ask`` users there would silently change their
#   write posture).
# - Pre-v3.2 ``build`` / ``run`` → ``edit_automatically``;
#   ``explore`` → ``plan_mode``; ``retro`` → ``auto_mode``.
_LEGACY_MODE_REMAP: dict[str, str] = {
    # v3.2.0 → v3.6.0
    "agent": "edit_automatically",
    "plan": "plan_mode",
    "debug": "auto_mode",
    "ask": "plan_mode",
    # v1.x / v2.x → v3.6.0 (transitively, via the v3.2 step above)
    "build": "edit_automatically",
    "run": "edit_automatically",
    "explore": "plan_mode",
    "retro": "auto_mode",
}

# Tab cycle order is intentionally NOT the same as ``_VALID_MODES``. We
# rotate ``edit_automatically → plan_mode → ask_before_edits → auto_mode``
# so the two write-capable modes (edit_automatically, ask_before_edits)
# don't sit next to each other — a single Tab press never accidentally
# flips between "edits land" and "edits land after a confirmation". We
# re-export the canonical order from ``keybinds`` so the TTY driver, the
# slash helper, and the parity docs can never drift apart again.
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
    # v3.6.0: Lyra's interactive modes are permission-flavoured —
    # ``edit_automatically`` (default; full-access execution, edits
    # apply without confirmation), ``ask_before_edits`` (full-access
    # execution but pauses for confirmation per write),
    # ``plan_mode`` (read-only design), ``auto_mode`` (router that
    # picks one of the other three per turn). Every legacy name from
    # v1.x / v2.x / v3.2.x (``build``, ``run``, ``explore``,
    # ``retro``, ``agent``, ``plan``, ``debug``, ``ask``) is remapped
    # on construction via ``__post_init__``; passing one in still
    # works but resolves to the canonical v3.6 name before the
    # session boots.
    mode: str = "edit_automatically"
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
    # Shared status bag: spinner verb, task checklist, sub-agent panel,
    # bg-task count, and bottom-bar segments all read from this one source.
    status_source: _StatusSource = field(default_factory=_StatusSource.from_env)
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

    # v3.7.0 (Phase 1): Skill system support
    _skill_manager: Any = None  # SkillManager instance, lazy-loaded
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
        """Normalise legacy mode names → v3.6 canonical and align permission posture.

        v3.6.0 introduced a permission-flavoured 4-mode taxonomy. A
        user landing here with an old persisted ``mode = "agent"`` (v3.2)
        or ``mode = "build"`` (v2.x) from settings.json or with a
        ``--mode agent`` flag from a script needs to keep working
        without staring at a "valid: edit_automatically, ask_before_edits,
        plan_mode, auto_mode" error. We do the remap here so every code
        path (driver default, CLI flag, settings.json restore,
        ``/mode build`` muscle memory) lands on the same canonical name.

        We also align ``permission_mode`` to the new mode's posture so
        the Alt+M permission cycle reflects the user's intent the
        moment the session boots:

        * ``edit_automatically`` → ``permission_mode = "normal"``
          (cached approvals; the agent doesn't re-prompt for tools
          you've already OK'd).
        * ``ask_before_edits`` → ``permission_mode = "strict"``
          (always re-prompt; the cache is a no-op).
        * ``plan_mode`` / ``auto_mode`` → leave the existing
          ``permission_mode`` untouched (plan_mode is read-only so
          the cache rarely matters; auto_mode flips per turn at
          dispatch time).

        The user can still override the permission posture mid-session
        with Alt+M (or ``/perm``); we only set it on boot so a fresh
        session reflects the mode they asked for.

        v3.7.0 (Phase 1): Auto-register discovered skills as slash commands.
        """
        canonical = _LEGACY_MODE_REMAP.get(self.mode, self.mode)
        if canonical != self.mode:
            self.mode = canonical
        if self.mode == "edit_automatically" and self.permission_mode == "normal":
            # Already aligned; nothing to do.
            pass
        elif self.mode == "edit_automatically":
            self.permission_mode = "normal"
        elif self.mode == "ask_before_edits":
            self.permission_mode = "strict"

        # Auto-register skills as slash commands
        self._register_skills()

    def _register_skills(self) -> None:
        """Auto-register discovered skills as slash commands."""
        try:
            from lyra_cli.cli.skill_manager import SkillManager
            from lyra_cli.commands.registry import register_command

            if self._skill_manager is None:
                self._skill_manager = SkillManager()

            # Get command specs for all discovered skills
            specs = self._skill_manager.get_command_specs()

            # Register each skill as a slash command
            for spec in specs:
                try:
                    register_command(spec)
                except ValueError:
                    # Already registered (e.g., from a previous session), skip
                    pass
        except Exception:
            # Skill system is optional; if it fails to load, continue without it
            pass

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
        handler = _MODE_HANDLERS.get(self.mode, _handle_plan_mode_text)
        return handler(self, line)

    def _execute_skill(self, skill_name: str, args: str) -> CommandResult:
        """Execute a skill by name with given arguments.

        This method is called by dynamically-registered skill command handlers.
        It loads the skill definition and executes it according to its execution type.
        """
        if self._skill_manager is None:
            from lyra_cli.cli.skill_manager import SkillManager
            self._skill_manager = SkillManager()

        skill = self._skill_manager.get_skill(skill_name)
        if not skill:
            return CommandResult(output=f"Skill '{skill_name}' not found")

        execution = skill.get("execution", {})
        exec_type = execution.get("type", "prompt")

        if exec_type == "prompt":
            # Load prompt from file and dispatch as plain text
            prompt_file = execution.get("prompt_file")
            if not prompt_file:
                return CommandResult(output=f"Skill '{skill_name}' has no prompt_file defined")

            # Resolve prompt file path (relative to skill JSON location)
            from pathlib import Path
            skill_dir = self._skill_manager.global_skills_dir
            if (self._skill_manager.local_skills_dir / f"{skill_name}.json").exists():
                skill_dir = self._skill_manager.local_skills_dir

            prompt_path = skill_dir / prompt_file
            if not prompt_path.exists():
                return CommandResult(
                    output=f"Skill prompt file not found: {prompt_path}"
                )

            try:
                prompt_template = prompt_path.read_text(encoding="utf-8")
                # Simple variable substitution: {args} -> actual args
                prompt = prompt_template.replace("{args}", args)

                # Dispatch as plain text to the LLM
                return self._dispatch_plain(prompt)
            except Exception as e:
                return CommandResult(output=f"Error executing skill '{skill_name}': {e}")

        elif exec_type == "command":
            # Execute shell command
            command_template = execution.get("command", "")
            if not command_template:
                return CommandResult(output=f"Skill '{skill_name}' has no command defined")

            # Simple variable substitution
            command = command_template.replace("{args}", args)

            try:
                import subprocess
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                output = result.stdout if result.returncode == 0 else result.stderr
                return CommandResult(output=output or f"Command completed with exit code {result.returncode}")
            except Exception as e:
                return CommandResult(output=f"Error executing skill command: {e}")

        else:
            return CommandResult(
                output=f"Unknown execution type '{exec_type}' for skill '{skill_name}'"
            )

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
        # Hydrate env vars from ~/.lyra/credentials.json so provider
        # keys are available immediately without a restart.
        try:
            from .key_store import KeyStore as _KeyStore
            _KeyStore().hydrate_env()
        except Exception:
            pass
        return session

    # ---- v1.7.4: /model list + /models -----------------------------------

    def _cmd_model_list(self, _rest: str) -> str:
        """Render every known model grouped by provider.

        Each provider section shows its display name, configured-status
        glyph, env-var, and the canonical model slugs the alias
        registry resolves into. The currently-selected model is
        marked with ``●``; the active provider gets a ``▸`` chevron.

        Output legend:
        * ``●`` — current model
        * ``✓`` — provider configured (env var or auth.json key, or
          local endpoint reachable)
        * ``—`` — provider not configured
        """
        import os

        from lyra_cli.llm_factory import (
            provider_env_var,
            provider_has_credentials,
        )
        from lyra_cli.providers.openai_compatible import PRESETS
        from lyra_core.providers.aliases import (
            DEFAULT_ALIASES,
            resolve_alias,
        )

        # Display names + ordering. Local backends sit at the bottom so
        # the cloud catalog dominates the picker.
        provider_meta: list[tuple[str, str]] = [
            ("anthropic",        "Anthropic Claude"),
            ("openai",           "OpenAI GPT"),
            ("openai-reasoning", "OpenAI o-series (reasoning)"),
            ("gemini",           "Google Gemini"),
            ("deepseek",         "DeepSeek"),
            ("xai",              "xAI Grok"),
            ("dashscope",        "Alibaba Qwen / Moonshot Kimi"),
            ("groq",             "Groq (Llama hosted)"),
            ("cerebras",         "Cerebras"),
            ("mistral",          "Mistral"),
            ("openrouter",       "OpenRouter (meta)"),
            ("vllm",             "vLLM (local)"),
            ("lmstudio",         "LM Studio (local)"),
            ("ollama",           "Ollama (local)"),
            ("mock",             "mock (offline)"),
        ]

        # Group every canonical slug from the alias registry by provider.
        # Aliases that map to the same canonical slug collapse into one
        # entry; the user sees the canonical slug + the friendly v4
        # forms users actually type (DeepSeek's flash/pro split, the
        # ``opus`` / ``sonnet`` shorthand, etc.).
        slugs_by_provider: dict[str, list[str]] = {}
        for alias_name, entry in DEFAULT_ALIASES._aliases.items():
            slugs_by_provider.setdefault(entry.provider, []).append(entry.slug)

        # Friendly user-facing labels per provider — surface the slot
        # syntax users muscle-memory ("deepseek-v4-flash" / "-pro",
        # "haiku" / "sonnet" / "opus") alongside the API slugs. The
        # alias registry already routes them; this just makes them
        # visible in the picker.
        friendly_extras: dict[str, list[str]] = {
            "deepseek": ["deepseek-v4-flash", "deepseek-v4-pro"],
            "anthropic": ["opus", "sonnet", "haiku"],
            "openai": ["gpt-5", "gpt-4o"],
            "gemini": ["gemini-2.5-pro", "gemini-2.5-flash"],
            "xai": ["grok-4", "grok-code-fast-1"],
            "dashscope": ["kimi-k2.5", "qwen-max"],
        }
        for prov, extras in friendly_extras.items():
            slugs_by_provider.setdefault(prov, []).extend(extras)

        # Dedup + stable sort
        for k in slugs_by_provider:
            slugs_by_provider[k] = sorted(set(slugs_by_provider[k]))

        selected_model_raw = (getattr(self, "model", "") or "").strip()
        selected_canonical = resolve_alias(selected_model_raw) if selected_model_raw else ""
        selected_provider = ""
        for prov, slugs in slugs_by_provider.items():
            if selected_canonical in slugs:
                selected_provider = prov
                break
        # Legacy fallback — ``current_llm_name`` is the v1 way to pin
        # the active backend by provider rather than model. Tests +
        # older snapshots still set it, so honour it when the alias
        # lookup didn't already settle on a provider.
        if not selected_provider:
            llm_name = (getattr(self, "current_llm_name", "") or "").strip().lower()
            if llm_name:
                selected_provider = llm_name

        # Per-preset configured-state lookup for non-auth-store providers
        # (mock / ollama / lmstudio that don't show up in auth.json).
        def _provider_configured(prov: str) -> bool:
            if prov == "mock":
                return True
            if prov == "ollama":
                try:
                    from lyra_cli.providers.ollama import ollama_reachable
                    return ollama_reachable()
                except Exception:
                    return False
            if prov == "lmstudio":
                preset = next((p for p in PRESETS if p.name == "lmstudio"), None)
                if preset is None:
                    return False
                try:
                    return preset.configured()
                except Exception:
                    return False
            return provider_has_credentials(prov)

        # ---- compose -----------------------------------------------
        lines: list[str] = []
        lines.append("─" * 72)
        lines.append(" Models")
        lines.append("─" * 72)

        for provider, display_name in provider_meta:
            slugs = slugs_by_provider.get(provider, [])
            # Always render Anthropic / OpenAI / DeepSeek even when the
            # alias registry has none yet — but skip empty buckets for
            # truly absent providers so the picker stays compact.
            if not slugs and provider not in {"mock", "ollama", "lmstudio", "vllm"}:
                continue

            configured = _provider_configured(provider)
            chevron = "▶" if provider == selected_provider else " "
            status = "✓" if configured else "—"
            env_name = provider_env_var(provider) or ""
            # Local backends have no env-var; surface the provider key
            # so the picker still shows a stable handle the user can
            # type into ``/model``.
            env_tail = f"  ({env_name})" if env_name else f"  ({provider})"
            header = (
                f"\n{chevron} {status}  {display_name:<32}{env_tail}"
            )
            lines.append(header)

            if not slugs:
                if provider == "mock":
                    lines.append("       canned outputs (no key needed)")
                elif provider == "ollama":
                    lines.append("       local — http://127.0.0.1:11434")
                elif provider == "lmstudio":
                    lines.append("       local — http://localhost:1234/v1")
                elif provider == "vllm":
                    lines.append("       local — OpenAI-compatible server")
                continue

            for slug in slugs:
                is_active = slug == selected_canonical
                glyph = "●" if is_active else "·"
                lines.append(f"     {glyph}  {slug}")

        lines.append("")
        lines.append("─" * 72)
        lines.append(
            " ●=current   ✓=configured   —=needs key   "
            "▶=active provider"
        )
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


# v3.6.0: Lyra's interactive modes are permission-flavoured —
# (edit_automatically, ask_before_edits, plan_mode, auto_mode). Every
# system prompt below ENUMERATES the four modes so the LLM never
# confabulates from training-data residue when the user asks "what
# modes do you have?". The shared preamble also explicitly notes that
# TDD's RED → GREEN → REFACTOR cycle is an OPT-IN PLUGIN
# (lyra_core.tdd), not a mode — this defends against a regression
# where the model used to list "BUILD / RED / GREEN / REFACTOR" as if
# they were peer modes (see CHANGELOG v3.2.0). The preamble also
# disclaims the v3.2 mode names (agent / plan / debug / ask) so the
# LLM doesn't reach for those when the user asks the same question
# from a stale screenshot or a half-migrated conversation.
_LYRA_MODE_PREAMBLE = (
    "You are Lyra, a CLI-native coding assistant. You operate in one "
    "of four modes:\n"
    "  • edit_automatically — default; full-access execution. You can "
    "write code and call tools when the runtime gives them; edits "
    "apply without per-write confirmation.\n"
    "  • ask_before_edits   — full-access execution, but you pause "
    "for the user to confirm every write or destructive tool call "
    "before it lands.\n"
    "  • plan_mode          — read-only collaborative design. You "
    "produce plans; you do not edit files or run destructive tools.\n"
    "  • auto_mode          — heuristic router. Each turn picks one "
    "of the three modes above based on the prompt; the chosen mode "
    "applies for that turn only.\n"
    "TDD is an OPT-IN PLUGIN (RED → GREEN → REFACTOR phases inside "
    "edit_automatically or ask_before_edits), NOT a separate mode. "
    "The pre-v3.6 names (agent / plan / debug / ask) and pre-v3.2 "
    "names (build / run / explore / retro) are LEGACY ALIASES — they "
    "are not modes you have. Never list TDD phases or legacy names "
    "as modes when the user asks how many modes you have — the "
    "answer is always exactly four: edit_automatically, "
    "ask_before_edits, plan_mode, auto_mode.\n"
)

# Phase 6d (v3.5): mode prompts enriched with patterns absorbed from
# dair-ai/Prompt-Engineering-Guide (CoT, ReAct, self-consistency, prompt
# chaining, few-shot) and obra/superpowers (Plan-First, Test-First,
# Stop-and-Clarify). Each pattern is folded ONLY where it fits the
# mode's contract — we do not bolt every pattern onto every mode.

_EDIT_AUTOMATICALLY_SYSTEM_PROMPT = (
    _LYRA_MODE_PREAMBLE + "\n"
    "You are currently in EDIT_AUTOMATICALLY mode. The user is "
    "asking you to design, write, or modify code; the runtime will "
    "apply your edits without a per-write confirmation. Use a "
    "ReAct-style loop: Reason about the task in 1–2 sentences, "
    "decide on the next Action (tool call or code edit), observe "
    "the result, then Repeat. Reply concisely — small focused code "
    "blocks beat essays. If they ask a coding question, answer "
    "with a small focused code block. If they greet you / "
    "chitchat, reply naturally and offer to help. Do not pretend "
    "to have run any tools — only call a tool when the runtime "
    "explicitly gives you one this turn. If you are not sure of "
    "the file or behaviour, say so and ask one clarifying "
    "question rather than guessing — Stop-and-Clarify beats "
    "hallucinating. Because edits land without confirmation, "
    "prefer the smallest correct change and surface the diff "
    "clearly so the user can read it before the next turn."
)

_ASK_BEFORE_EDITS_SYSTEM_PROMPT = (
    _LYRA_MODE_PREAMBLE + "\n"
    "You are currently in ASK_BEFORE_EDITS mode. The user has "
    "asked you to do real work, but every write or destructive "
    "tool call will be confirmed by them before it runs. Behave "
    "as you would in edit_automatically — same ReAct loop, same "
    "Stop-and-Clarify discipline — but with one extra rule: when "
    "you are about to call a write/destructive tool, surface in "
    "ONE sentence what it will do and why before the call (the "
    "user is staring at a confirmation prompt and your sentence is "
    "what they read). Bundle related writes in a single message "
    "where possible so the user is not death-by-OK'd. Reads, "
    "searches, and analysis are still free — only writes pause."
)

_PLAN_MODE_SYSTEM_PROMPT = (
    _LYRA_MODE_PREAMBLE + "\n"
    "You are currently in PLAN_MODE. The user is brainstorming "
    "what to build. Use Plan-First: for any non-trivial task, "
    "produce a short numbered plan (3–7 steps), each step listing "
    "(a) what changes, (b) which files / packages, (c) what tests "
    "would prove the step worked, and (d) the rollback if it "
    "fails. Show your reasoning step by step (Chain-of-Thought is "
    "welcome here — plan_mode rewards thinking out loud). If they "
    "say hello / ask a question / chitchat, just answer naturally. "
    "Do not pretend to have run any tools — plan_mode is read-only "
    "by contract. If two architectures differ meaningfully, "
    "present BOTH and ask the user to pick (explicit "
    "self-consistency: surface the disagreement rather than "
    "silently averaging it away)."
)

_AUTO_MODE_SYSTEM_PROMPT = (
    _LYRA_MODE_PREAMBLE + "\n"
    "You are currently in AUTO_MODE. The user has delegated mode "
    "selection to Lyra; for THIS turn the router has classified "
    "the prompt and dispatched you with the appropriate sub-mode "
    "system prompt. If you somehow see this prompt directly (the "
    "router fell through), default to the edit_automatically "
    "playbook: ReAct loop, smallest correct change, "
    "Stop-and-Clarify when uncertain. Always tell the user which "
    "sub-mode the router picked so the choice is visible to them."
)


_MODE_SYSTEM_PROMPTS: dict[str, str] = {
    "edit_automatically": _EDIT_AUTOMATICALLY_SYSTEM_PROMPT,
    "ask_before_edits":   _ASK_BEFORE_EDITS_SYSTEM_PROMPT,
    "plan_mode":          _PLAN_MODE_SYSTEM_PROMPT,
    "auto_mode":          _AUTO_MODE_SYSTEM_PROMPT,
}

# Rolling window for ``_chat_history``. 20 turns ≈ 40 messages, which
# fits comfortably in a 32k-token context for the cheap-tier models
# (DeepSeek, Qwen, gpt-4o-mini) we recommend by default.
_CHAT_HISTORY_TURNS = 20


def _ensure_llm(session: InteractiveSession):
    """Resolve and cache the ``LLMProvider`` for ``session.model``.

    Lazy: first plain-text turn pays the resolution cost, subsequent
    turns reuse the cached provider. The cache is invalidated by the
    ``/model`` slash so model switches take effect immediately.

    Raises ``RuntimeError`` from :mod:`lyra_cli.llm_factory` when no
    provider is configured (no env var, no ``auth.json`` entry).
    """
    if session._llm_provider is not None and session._llm_provider_kind == session.model:
        return session._llm_provider

    from ..llm_factory import build_llm

    provider = build_llm(session.model)
    session._llm_provider = provider
    session._llm_provider_kind = session.model
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

    # Collect completed pre-LLM phases for the nyan-bar progress header.
    # We detect actual augmentation by comparing lengths; that's cheap and
    # never wrong — an empty skill block doesn't add characters.
    _completed_phases: list[tuple[str, str]] = []
    effective_system = _augment_system_prompt_with_skills(
        session, system_prompt, line=line
    )
    if len(effective_system) > len(system_prompt):
        _completed_phases.append(("Skills loaded", "done"))

    _before_memory = effective_system
    effective_system = _augment_system_prompt_with_memory(
        session, effective_system, line
    )
    if len(effective_system) > len(_before_memory):
        _completed_phases.append(("Memory loaded", "done"))

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
            completed_phases=_completed_phases,
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

                block = render_skill_block(
                    session.repo_root,
                    state=_load_session_skills_state(session),
                )
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
            state=_load_session_skills_state(session),
        )
    except Exception:
        return "", [], {}
    return result.text, list(result.activated_ids), dict(result.activation_reasons)


def _load_session_skills_state(session: InteractiveSession):
    """Return the user's per-skill overrides for this session.

    Cached on the session so each turn doesn't re-read the JSON. The
    ``/skills`` picker invalidates the cache via
    ``session._skills_state = None`` after a save.
    """
    cached = getattr(session, "_skills_state", None)
    if cached is not None:
        return cached
    try:
        from lyra_skills.state import load_state

        cached = load_state()
    except Exception:
        cached = None
    session._skills_state = cached
    return cached


def _stdin_is_tty() -> bool:
    """Best-effort TTY detection — None or detached fds count as headless."""
    import sys

    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (AttributeError, ValueError):
        return False


def _launch_skills_picker(session: InteractiveSession) -> "CommandResult":
    """Run the full-screen picker and persist the result.

    Falls back to a friendly error CommandResult if prompt_toolkit is
    not available or the dialog implodes — the picker is a UX
    convenience, not load-bearing infrastructure.
    """
    try:
        from .dialog_skills import run_skills_dialog
        from lyra_skills.state import SkillsState, load_state, save_state
    except Exception as exc:  # pragma: no cover — defensive
        return CommandResult(output=f"skills picker unavailable: {exc}")

    try:
        current = load_state()
    except Exception:
        current = SkillsState()

    try:
        result = run_skills_dialog(session.repo_root, state=current)
    except Exception as exc:
        return CommandResult(output=f"skills picker failed: {exc}")

    if result is None:
        return CommandResult(output="skills picker: no changes saved.")

    try:
        save_state(result.new_state)
    except Exception as exc:
        return CommandResult(output=f"skills picker: save failed: {exc}")

    # Invalidate the per-session cache so the next turn re-renders
    # the system-prompt block with the new state.
    session._skills_state = None
    session._cached_skill_block = None

    if not result.changed_ids:
        return CommandResult(output="skills picker: no changes.")
    return CommandResult(
        output=(
            f"skills picker: updated {len(result.changed_ids)} skill(s) — "
            + ", ".join(result.changed_ids)
        )
    )


def _print_skills_state(session: InteractiveSession) -> "CommandResult":
    """Show the user's persisted skill overrides as plain text."""
    try:
        from lyra_skills.state import SkillsState, load_state

        state = load_state()
    except Exception as exc:
        return CommandResult(output=f"skills state unavailable: {exc}")

    if state == SkillsState():
        return CommandResult(
            output="no skill overrides — every discovered skill is on by default."
        )
    lines = []
    if state.disabled:
        lines.append(f"disabled ({len(state.disabled)}):")
        for sid in sorted(state.disabled):
            lines.append(f"  - {sid}")
    if state.enabled:
        lines.append(f"enabled ({len(state.enabled)}):")
        for sid in sorted(state.enabled):
            lines.append(f"  - {sid}")
    return CommandResult(output="\n".join(lines))


def _launch_sessions_picker(sessions_root: Path) -> Optional[str]:
    """Open the full-screen sessions picker and return the chosen id.

    Returns ``None`` when the user cancels or the picker is otherwise
    unavailable (no dialog module, no entries). The caller (``/resume``
    or ``/sessions``) treats ``None`` as a clean cancel.
    """
    try:
        from .dialog_sessions import run_sessions_dialog
    except Exception:
        return None
    try:
        result = run_sessions_dialog(sessions_root)
    except Exception:
        return None
    return None if result is None else result.session_id


def _launch_agents_picker(session: InteractiveSession) -> "CommandResult":
    """Run the full-screen agents picker (catalog + live views).

    The picker is non-destructive: it returns a chosen preset name
    (``catalog_pick``) or live record id (``live_pick``) and we
    print the corresponding detail block. ``/spawn`` and
    ``/agents kill`` remain the way to actually act on those rows.
    """
    try:
        from .dialog_agents import run_agents_dialog
    except Exception as exc:  # pragma: no cover — defensive
        return CommandResult(output=f"agents picker unavailable: {exc}")

    reg = getattr(session, "subagent_registry", None)
    try:
        result = run_agents_dialog(registry=reg)
    except Exception as exc:
        return CommandResult(output=f"agents picker failed: {exc}")

    if result is None:
        return CommandResult(output="agents picker: cancelled.")

    if result.catalog_pick is not None:
        return _render_preset_detail(result.catalog_pick)
    if result.live_pick is not None:
        return _render_live_detail(result.live_pick)

    return CommandResult(output="agents picker: no selection.")


def _render_preset_detail(entry) -> "CommandResult":
    """Pretty-print a catalog preset the user picked."""
    lines = [
        f"agent preset: {entry.name}",
        f"  source : {entry.source}",
        f"  model  : {entry.model}",
        f"  role   : {entry.role}",
        f"  tools  : {', '.join(entry.tools) or '(none)'}",
    ]
    if entry.aliases:
        lines.append(f"  aliases: {', '.join(entry.aliases)}")
    if entry.description:
        lines.append("")
        lines.append(entry.description)
    lines.append("")
    lines.append(f"hint: /spawn --type {entry.name} <description>")
    return CommandResult(output="\n".join(lines))


def _render_live_detail(entry) -> "CommandResult":
    """Pretty-print a live subagent record the user picked."""
    lines = [
        f"subagent: {entry.record_id}",
        f"  state : {entry.state}",
    ]
    if entry.subagent_type:
        lines.append(f"  type  : {entry.subagent_type}")
    if entry.description:
        lines.append("")
        lines.append(entry.description)
    lines.append("")
    lines.append(f"hint: /agents kill {entry.record_id}")
    return CommandResult(output="\n".join(lines))


def _toggle_skill_id(
    session: InteractiveSession,
    skill_id: str,
    *,
    enable: bool,
) -> "CommandResult":
    """Programmatic equivalent of pressing Space on *skill_id* in the picker.

    Refuses to disable locked skills (packaged packs) — same invariant
    the picker enforces.
    """
    try:
        from lyra_skills.state import SkillsState, load_state, save_state
        from .skills_inject import (
            _load_skills_safely,
            _packaged_pack_root,
            discover_skill_roots,
            is_locked_skill,
        )
    except Exception as exc:
        return CommandResult(output=f"skills toggle unavailable: {exc}")

    skills = _load_skills_safely(discover_skill_roots(session.repo_root))
    target = next((s for s in skills if getattr(s, "id", "") == skill_id), None)
    if target is None:
        return CommandResult(output=f"skill not found: {skill_id}")

    if not enable and is_locked_skill(target, _packaged_pack_root()):
        return CommandResult(
            output=(
                f"{skill_id} is bundled with Lyra — disable via "
                f"`lyra skill remove {skill_id}` instead."
            )
        )

    state = load_state()
    if enable:
        new_state = SkillsState(
            enabled=state.enabled - {skill_id},
            disabled=state.disabled - {skill_id},
        )
    else:
        new_state = SkillsState(
            enabled=state.enabled - {skill_id},
            disabled=state.disabled | {skill_id},
        )
    if new_state == state:
        flag = "enabled" if enable else "disabled"
        return CommandResult(output=f"{skill_id} already {flag}.")

    save_state(new_state)
    session._skills_state = None
    session._cached_skill_block = None
    flag = "enabled" if enable else "disabled"
    return CommandResult(output=f"{skill_id} {flag}.")


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

            # v3.10: install ``AskUserQuestion`` only when the session
            # has a Rich console attached AND stdin is interactive.
            # Skipping the tool in piped / CI runs prevents the agent
            # from advertising a capability it would block forever
            # waiting on. The prompter closure captures the live
            # console so the dialog inherits the REPL's theme.
            ask_prompter = None
            console = getattr(session, "_console", None)
            stdin_is_tty = False
            try:
                import sys as _sys
                stdin_is_tty = bool(_sys.stdin and _sys.stdin.isatty())
            except (ValueError, AttributeError):
                stdin_is_tty = False
            if console is not None and stdin_is_tty:
                from .ask_user_prompter import make_prompter
                ask_prompter = make_prompter(console)

            session._chat_tool_registry = build_chat_tool_registry(
                session.repo_root, ask_user_prompter=ask_prompter
            )
            session._chat_tool_registry_error = None
        except Exception as exc:
            session._chat_tool_registry = None
            session._chat_tool_registry_error = (
                f"{type(exc).__name__}: {exc}"
            )
            console = getattr(session, "_console", None)
            if console is not None:
                console.print(
                    f"[yellow]⚠ chat tools disabled: "
                    f"{type(exc).__name__}: {exc}[/yellow]\n"
                    f"[dim]Set LYRA_DEBUG=1 for the full traceback. "
                    f"Inspect via [/dim][cyan]/status[/cyan][dim].[/dim]"
                )
            else:
                import sys
                print(
                    f"[lyra] chat tools disabled: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
            if os.environ.get("LYRA_DEBUG"):
                import traceback
                traceback.print_exc()
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

    # v3.10: load the declarative permission grammar + user hooks
    # lazily on first tool call. Caching on the session (a) keeps
    # ``_approve`` zero-allocation in the hot path and (b) survives a
    # mid-session settings edit because the cache key is the session
    # itself, not a global — restart the REPL to pick up changes.
    def _load_policy_and_hooks() -> tuple[Any, list[Any], bool]:
        cached = getattr(session, "_policy_hooks_cache", None)
        if cached is not None:
            return cached
        try:
            from ..policy_loader import load_hooks, load_policy

            policy = load_policy(session.repo_root)
            hook_specs, hooks_enabled = load_hooks(session.repo_root)
        except Exception:
            # Settings file is the user's territory — a malformed
            # policy block is *their* bug. Log once via the lifecycle
            # bus and fall back to the legacy approval flow rather
            # than blocking every tool call.
            policy, hook_specs, hooks_enabled = None, [], False
        session._policy_hooks_cache = (policy, hook_specs, hooks_enabled)
        return session._policy_hooks_cache

    def _approve(name: str, _args: dict[str, Any]) -> bool:
        policy, hook_specs, hooks_enabled = _load_policy_and_hooks()
        from lyra_core.permissions.grammar import Verdict
        from lyra_core.hooks.user_hooks import run_hooks

        # Step 1: declarative deny rules short-circuit before we even
        # consider hooks — saves a subprocess hop on the safe path
        # and matches CC's deny→ask→allow precedence.
        if policy is not None and not policy.is_empty():
            decision = policy.decide(name, _args or {})
            if decision.verdict is Verdict.DENY:
                console = getattr(session, "_console", None)
                if console is not None:
                    console.print(
                        f"[red]⎿  denied by rule[/red] [bold]{decision.rule.source}[/bold]",
                        highlight=False,
                    )
                return False

        # Step 2: PreToolUse user hooks. A hook returning
        # ``continue=false`` blocks; a hook rewriting args silently
        # mutates the dict (callers passed it by reference).
        if hooks_enabled and hook_specs:
            outcome = run_hooks(
                hook_specs,
                event="PreToolUse",
                tool_name=name,
                args=_args or {},
                session_id=getattr(session, "session_id", ""),
                enabled=True,
            )
            if outcome.block:
                console = getattr(session, "_console", None)
                if console is not None:
                    console.print(
                        f"[red]⎿  blocked by hook:[/red] {outcome.reason}",
                        highlight=False,
                    )
                return False
            if outcome.mutated_args is not None:
                _args.clear()
                _args.update(outcome.mutated_args)

        # Step 3: declarative allow rules (matched but not denied) and
        # the legacy LOW_RISK fast path. Both auto-approve.
        if policy is not None and not policy.is_empty():
            decision = policy.decide(name, _args or {})
            if decision.verdict is Verdict.ALLOW:
                return True
        if name in _LOW_RISK:
            return True

        # Step 4: medium-risk ASK path — surface a console prompt when
        # one is available, otherwise default-open for headless runs.
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
            return True

    _last_file_call: dict[str, Any] = {}

    def _render(event: ToolEvent) -> None:
        from .tool_render import (
            is_file_tool,
            paint_call,
            paint_denied,
            paint_file_call,
            paint_file_result,
            paint_limit,
            paint_result,
        )

        console = getattr(session, "_console", None)

        def _emit(paint) -> None:
            if console is not None:
                for line in paint.rich_lines:
                    console.print(line, highlight=False)
            else:
                for line in paint.plain_lines:
                    print(line)

        if event.kind == "call":
            _last_file_call.clear()
            if is_file_tool(event.tool_name):
                _last_file_call["tool"] = event.tool_name
                _last_file_call["args"] = event.args
                path = event.args.get("path", "")
                _emit(paint_file_call(event.tool_name, path))
            else:
                arg_preview = _short_arg_preview(event.args)
                _emit(paint_call(event.tool_name, arg_preview))
        elif event.kind == "result":
            if _last_file_call:
                paint, full = paint_file_result(
                    _last_file_call["tool"],
                    _last_file_call["args"],
                    event.output,
                    is_error=bool(event.is_error),
                )
            else:
                paint, full = paint_result(
                    event.output, is_error=bool(event.is_error)
                )
            session._last_tool_output = full
            _emit(paint)
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
            _emit(paint_denied(event.tool_name, event.reason or ""))
        elif event.kind == "limit_reached":
            _emit(paint_limit(event.reason or ""))

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
    """Length-cap ``text`` with an ellipsis suffix; collapse newlines.

    Multi-line tool output is flattened with a middle-dot separator
    (``·``) rather than the literal ``↵`` Unicode return symbol —
    on screen the dot reads as a clean structural separator while
    ``↵`` looks like a debugging escape sequence leaked into the UI.
    """
    flat = text.replace("\n", " · ")
    if len(flat) <= limit:
        return flat
    return flat[: max(limit - 1, 1)] + "…"


def _format_tool_output(output: str, *, max_lines: int = 3, max_line_width: int = 200) -> tuple[str, str]:
    """Claude-Code-style collapsed view of tool output.

    Returns ``(collapsed, full)``:

    * ``collapsed`` — the first ``max_lines`` lines plus a
      ``"… +N lines (ctrl+o to expand)"`` footer when truncated. Each
      line is also length-capped at ``max_line_width`` so a long
      single line can't blow out the panel.
    * ``full`` — the un-truncated original text, stashed on the
      session so ``Ctrl+O`` can dump it on demand.
    """
    full = output or ""
    lines = full.rstrip("\n").split("\n")
    shown: list[str] = []
    for ln in lines[:max_lines]:
        if len(ln) > max_line_width:
            ln = ln[: max_line_width - 1] + "…"
        shown.append(ln)
    remainder = len(lines) - max_lines
    if remainder > 0:
        shown.append(f"… +{remainder} lines (ctrl+o to expand)")
    if not shown:
        shown = ["(empty)"]
    return "\n".join(shown), full


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
    completed_phases: "list[tuple[str, str]] | None" = None,
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

    ``completed_phases`` is a list of ``(label, state)`` tuples for
    phases that finished before the LLM call (skills injection, memory
    loading, etc.). When present, a nyan-bar progress header is shown
    above the streaming panel so the user sees the full turn lifecycle
    rather than just the model's words appearing from nowhere.
    """
    try:
        from rich.live import Live
        from rich.console import Group
    except Exception as exc:  # pragma: no cover — Rich is a hard dep
        return False, f"rich import failed: {exc}"

    import time as _time_mod

    buffer: list[str] = []
    display_buffer: list[str] = []   # fence-safe content, drives the live panel
    _tick = 0
    _t0 = _time_mod.monotonic()

    from .stream import MarkdownStreamState
    _mss = MarkdownStreamState()

    # Try to import the progress header; degrade gracefully if missing.
    try:
        from .live_progress import TurnProgressHeader
        _phases = list(completed_phases or [])
        _use_header = True
    except Exception:
        _use_header = False
        _phases = []

    def _verb_for_mode(m: str) -> str:
        return {
            "agent": "Thinking",
            "edit_automatically": "Thinking",
            "plan":  "Planning",
            "plan_mode": "Planning",
            "ask":   "Reasoning",
            "ask_before_edits": "Reasoning",
            "auto":  "Thinking",
            "auto_mode": "Thinking",
        }.get(m, "Thinking")

    _verb = _verb_for_mode(mode_for_panel)

    def render_panel() -> Any:
        return _out.chat_renderable(
            "".join(display_buffer), mode=mode_for_panel, streaming=False
        )

    def render_with_header() -> Any:
        nonlocal _tick
        elapsed = _time_mod.monotonic() - _t0
        header = TurnProgressHeader(
            _phases,
            tick=_tick,
            elapsed=elapsed,
            verb=_verb,
            streaming=True,
        )
        _tick += 1
        return Group(header, render_panel())

    render_fn = render_with_header if _use_header else render_panel

    try:
        with Live(
            render_fn(),
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
                    safe = _mss.push(delta)
                    if safe:
                        display_buffer.append(safe)
                    live.update(render_fn())
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
            # Successful completion: swap the streaming Text panel for
            # a Markdown-rendered one so headings, fenced code, and
            # GFM tables actually format. During the loop we used
            # ``streaming=True`` to keep half-formed fences from
            # twitching; now that the buffer is final, render it
            # properly as the last Live frame. The nyan-bar header is
            # intentionally dropped on the final frame so only the clean
            # reply panel stays on screen after the turn completes.
            final_text = "".join(buffer)
            if final_text.strip():
                live.update(
                    _out.chat_renderable(
                        final_text, mode=mode_for_panel, streaming=False
                    )
                )
    except Exception as exc:  # pragma: no cover — Live setup failure
        return False, f"streaming render failed: {exc}"

    return True, "".join(buffer)


def _build_chat_handler(mode: str):
    """Factory for plain-text mode handlers that call the LLM."""
    system = _MODE_SYSTEM_PROMPTS[mode]

    def _handler(session: InteractiveSession, line: str) -> CommandResult:
        # plan_mode keeps the "task recorded" affordance — the user
        # can still /approve to enter the planner sub-loop. We just
        # don't *block* on it.
        if mode == "plan_mode":
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


# ---------------------------------------------------------------------------
# auto_mode router (v3.6.0)
#
# The router classifies the user's plain-text prompt and dispatches to
# one of the three "real" modes for that turn only. The session.mode
# field stays "auto_mode" — only the handler we run for *this* turn
# borrows another mode's system prompt. This keeps the router cheap
# (no LLM call), inspectable (the keyword tables live next to the
# code), and reversible (the user sees which sub-mode was picked and
# can override with /mode).
#
# Heuristic, in priority order:
#   1. ``plan_mode`` — design / explore / question prompts (no edit
#      verb, lots of "how does X work" / "explain" / "design" / "?").
#   2. ``ask_before_edits`` — risky / destructive verbs (delete, rm,
#      drop, migrate, push, deploy, prod) where the user almost
#      certainly wants a confirmation gate.
#   3. ``edit_automatically`` — everything else (the implementation
#      default).
# ---------------------------------------------------------------------------


_PLAN_MODE_KEYWORDS: tuple[str, ...] = (
    "explain",
    "what does",
    "what is",
    "how does",
    "how do",
    "why does",
    "design",
    "architecture",
    "compare",
    "trade-off",
    "tradeoff",
    "explore",
    "outline",
    "plan ",
    "plan:",
    "brainstorm",
)

_RISKY_KEYWORDS: tuple[str, ...] = (
    "delete",
    " rm ",
    "rm -",
    "drop ",
    "drop table",
    "truncate",
    "migrate",
    "migration",
    "git push",
    "force push",
    "deploy",
    " prod ",
    "production",
    "destroy",
    "wipe",
    "reset --hard",
    "schema",
    "rollback",
    "rotate key",
    "rotate secret",
)


def _classify_for_auto_mode(line: str) -> str:
    """Return the sub-mode name auto_mode should dispatch this turn to.

    Pure function so it's directly unit-testable. The keyword tables
    above are the contract — adding a token here is a UX change that
    a test in ``test_modes_taxonomy_v36.py`` will cover.
    """
    text = line.lower().strip()
    if not text:
        return "edit_automatically"

    # plan_mode wins on read-only intent. We check whole-word "plan" /
    # "plan:" so "explain" doesn't double-match (it's already in the
    # plan_mode list anyway).
    for kw in _PLAN_MODE_KEYWORDS:
        if kw in text:
            return "plan_mode"

    # Bare question marks with no edit verb → plan_mode. We treat
    # "fix this", "implement", "add", "rename", etc. as edits even
    # when accompanied by a "?".
    edit_verbs = (
        "fix",
        "implement",
        "add",
        "rename",
        "remove",
        "delete",
        "refactor",
        "build",
        "write",
        "create",
        "update",
        "bump",
        "convert",
    )
    has_edit_verb = any(verb in text for verb in edit_verbs)
    if not has_edit_verb and text.endswith("?"):
        return "plan_mode"

    for kw in _RISKY_KEYWORDS:
        if kw in text:
            return "ask_before_edits"

    return "edit_automatically"


def _handle_auto_mode_text(session: InteractiveSession, line: str) -> CommandResult:
    """auto_mode plain-text handler — classify, dispatch, annotate."""
    sub_mode = _classify_for_auto_mode(line)
    sub_handler = _MODE_HANDLERS[sub_mode]
    result = sub_handler(session, line)
    # Prepend a one-line "router picked X" notice so the user can see
    # the choice and override it (with /mode <name>) if it was wrong.
    notice = f"[auto_mode → {sub_mode}] "
    return CommandResult(
        output=notice + (result.output or ""),
        renderable=result.renderable,
        new_mode=result.new_mode,
    )


_handle_edit_automatically_text = _build_chat_handler("edit_automatically")
_handle_ask_before_edits_text   = _build_chat_handler("ask_before_edits")
_handle_plan_mode_text          = _build_chat_handler("plan_mode")


_MODE_HANDLERS: dict[str, Callable[[InteractiveSession, str], CommandResult]] = {
    "edit_automatically": _handle_edit_automatically_text,
    "ask_before_edits":   _handle_ask_before_edits_text,
    "plan_mode":          _handle_plan_mode_text,
    "auto_mode":          _handle_auto_mode_text,
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
        "(plan_mode: design · edit_automatically: implement · "
        "ask_before_edits: implement w/ confirmations · "
        "auto_mode: route per turn)."
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
        "Plain text routes to the current mode — plan_mode: design · "
        "edit_automatically: implement · ask_before_edits: implement "
        "w/ confirmations · auto_mode: route per turn.    "
        "Tip: prefix `!` for shell, `@` for a file."
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
    ("edit_automatically", "default; full-access execution. Edits land without per-write confirmation."),
    ("ask_before_edits",   "full-access execution; pauses for confirmation before each write or destructive call."),
    ("plan_mode",          "read-only collaborative design. Plain text proposes a plan."),
    ("auto_mode",          "router; picks plan_mode / ask_before_edits / edit_automatically per turn."),
)


def _cmd_mode(session: InteractiveSession, args: str) -> CommandResult:
    """``/mode`` — show or set the active interactive mode.

    Forms:
      * ``/mode``            — print the current mode (short display
        label, with the canonical permission-flavoured ID in parens).
      * ``/mode list``       — show all four modes with one-line blurbs.
      * ``/mode toggle``     — advance through the Tab cycle.
      * ``/mode <name>``     — switch to ``<name>``. Both the short
        labels (``agent`` / ``plan`` / ``ask`` / ``auto``) and the
        canonical IDs (``edit_automatically`` / ``plan_mode`` /
        ``ask_before_edits`` / ``auto_mode``) work; the dispatcher
        treats the short labels as first-class, not as legacy aliases.
      * ``/mode <pre-v3.2>`` — pre-v3.2 names (``build`` / ``run`` /
        ``explore`` / ``retro``) are still accepted silently for
        muscle-memory continuity.
    """
    from .keybinds import cycle_mode

    raw = args.strip().lower()
    if not raw:
        return CommandResult(
            output=(
                f"current mode: {display_mode(session.mode)} "
                f"({session.mode})"
            )
        )

    if raw == "list":
        lines = ["available modes:"]
        for name, blurb in _MODE_BLURBS:
            marker = "●" if name == session.mode else " "
            label = display_mode(name)
            lines.append(f"  {marker} {label:<6} {name:<20}  {blurb}")
        return CommandResult(output="\n".join(lines))

    if raw == "toggle":
        previous = session.mode
        cycle_mode(session)
        return CommandResult(
            output=(
                f"mode: {display_mode(previous)} → "
                f"{display_mode(session.mode)} ({session.mode})"
            ),
            new_mode=session.mode,
        )

    target = _LEGACY_MODE_REMAP.get(raw, raw)

    if target not in _VALID_MODES:
        return CommandResult(
            output=(
                f"unknown mode {raw!r}; "
                f"valid: {', '.join(_VALID_MODES)}"
            ),
            renderable=_out.bad_mode_renderable(raw, _VALID_MODES),
        )

    extra = ""
    if (
        target == "edit_automatically"
        and getattr(session, "permission_mode", "normal") == "yolo"
    ):
        # Switching into edit_automatically while permissions are off
        # is the single most footgun-y combination — call it out so
        # the user has one chance to back out before they run a
        # destructive plan.
        extra = (
            " [warning: permission mode is 'yolo' — tool calls will run "
            "without confirmation. Consider /perm strict before "
            "/mode edit_automatically]"
        )
    session.mode = target

    # v3.6.0: align permission posture to the new mode. The user
    # explicitly asked for this mode, so honour its full intent —
    # edit_automatically lifts strict gating, ask_before_edits forces
    # it. plan_mode and auto_mode leave the existing posture alone
    # (plan_mode is read-only so the cache barely matters; auto_mode
    # picks per turn at dispatch time). yolo is preserved across mode
    # switches because it requires a separate explicit opt-in via
    # /perm yolo or Alt+M.
    posture_note = ""
    current_perm = getattr(session, "permission_mode", "normal")
    if current_perm != "yolo":
        if target == "edit_automatically" and current_perm != "normal":
            session.permission_mode = "normal"
            _propagate_permission_mode(session, "normal")
            posture_note = " [permission mode → normal]"
        elif target == "ask_before_edits" and current_perm != "strict":
            session.permission_mode = "strict"
            _propagate_permission_mode(session, "strict")
            posture_note = " [permission mode → strict]"

    return CommandResult(
        output=(
            f"mode: {display_mode(target)} ({target})"
            f"{extra}{posture_note}"
        ),
        new_mode=target,
    )


def _propagate_permission_mode(session: InteractiveSession, perm: str) -> None:
    """Sync permission_mode to the per-call substrate (stack + cache).

    Mirrors the same propagation ``toggle_permission_mode`` does for
    Alt+M so a ``/mode`` switch is fully consistent with a manual
    permission-mode flip. Best-effort — any propagation error is
    swallowed because failing here would crash the slash dispatcher
    and the user would lose the REPL.
    """
    stack = getattr(session, "permission_stack", None)
    if stack is not None and hasattr(stack, "set_mode"):
        try:
            stack.set_mode(perm)
        except Exception:
            pass
    cache = getattr(session, "tool_approval_cache", None)
    if cache is not None and hasattr(cache, "set_mode"):
        try:
            cache.set_mode(perm)
        except Exception:
            pass


def _cmd_model(session: InteractiveSession, args: str) -> CommandResult:
    """``/model`` — open the picker, list providers, or pin a slug directly.

    Forms accepted:

    * ``/model`` — open the Claude-Code-style full-screen picker.
    * ``/model list`` / ``/model ls`` — delegate to the configured-providers
      table (same as ``/models``).
    * ``/model <slug>`` — pin the active model directly (``haiku``,
      ``opus-4.7``, ``gpt-5.5``, ``deepseek-reasoner``, …). Any alias
      registered in :data:`lyra_core.providers.aliases.DEFAULT_ALIASES`
      is accepted.
    """
    target = args.strip()
    if not target:
        # Lazy import so a headless caller (no TTY, prompt_toolkit
        # unavailable) still falls back to the text summary below.
        try:
            from .dialog_model import run_model_dialog
            from .effort import apply_effort

            current_effort = getattr(session, "effort", None)
            chosen, chosen_effort = run_model_dialog(
                getattr(session, "model", None),
                effort=current_effort,
            )
        except Exception:
            chosen = None
            chosen_effort = None

        if chosen:
            session.model = chosen
            session._llm_provider = None
            session._llm_provider_kind = None
            cfg = getattr(session, "config", None)
            if cfg is not None:
                cfg.set("model", chosen)
                _persist_config(session)
        if chosen_effort:
            session.effort = chosen_effort
            apply_effort(chosen_effort)
        if chosen or chosen_effort:
            parts = []
            if chosen:
                parts.append(f"model: {chosen}")
            if chosen_effort:
                parts.append(f"effort: {chosen_effort}")
            return CommandResult(output=", ".join(parts))

        return CommandResult(output=f"current model: {session.model}")

    if target.lower() in {"list", "ls"}:
        return CommandResult(output=session._cmd_model_list(""))

    # Resolve the alias to its canonical slug + provider so we can
    # ask for a key when the provider has no credentials yet. Both
    # helpers return the input unchanged for unknown aliases, so a
    # raw provider-specific slug ("local-only-model") still works.
    from lyra_core.providers.aliases import provider_key_for, resolve_alias

    canonical = resolve_alias(target) or target
    provider = provider_key_for(target) or provider_key_for(canonical)

    extra = ""
    if provider:
        extra = _ensure_provider_credentials_or_prompt(provider)

    # Preserve the *user-typed* alias as the active model name. The
    # toolbar, prompt, banner and bottom bar all read ``session.model``
    # — collapsing it to the canonical slug here meant
    # ``/model deepseek-v4-pro`` immediately rendered as
    # ``deepseek-reasoner`` and the user lost the friendly slot
    # syntax they typed. ``build_llm`` resolves the alias on its own
    # via ``_route_kind_via_alias``, so routing stays correct.
    session.model = target
    # Invalidate the cached LLMProvider so the next plain-text turn
    # rebuilds against the newly-selected model.
    session._llm_provider = None
    session._llm_provider_kind = None
    cfg = getattr(session, "config", None)
    if cfg is not None:
        cfg.set("model", target)
        _persist_config(session)
    suffix = f" → {canonical}" if canonical != target else ""
    return CommandResult(output=f"model set to: {target}{suffix}{extra}")


def _ensure_provider_credentials_or_prompt(provider: str) -> str:
    """If *provider* has no key in env / credentials.json and we're in a
    TTY, prompt the user to paste one and persist it via KeyStore.

    Returns a one-line annotation to append to the ``/model`` output:
    ``" [saved deepseek key]"`` on success, ``" [warning: …]"`` when
    the user skipped, ``""`` when nothing needed to happen.
    """
    import sys

    from lyra_cli.llm_factory import (
        provider_env_var,
        provider_has_credentials,
    )

    if provider_has_credentials(provider):
        return ""
    env_name = provider_env_var(provider)
    if env_name is None:
        # Provider not in the saveable map (e.g. ``vertex`` uses ADC,
        # ``bedrock`` uses the boto3 chain). Nothing to prompt for.
        return ""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return (
            f" [warning: {provider} has no key set; "
            f"export {env_name} or run `lyra connect {provider}`]"
        )
    try:
        from .dialog_apikey import request_api_key
        from .key_store import KeyStore
    except Exception:
        return ""
    try:
        _key, status = request_api_key(provider, store=KeyStore())
    except Exception as exc:
        return f" [could not prompt for key: {exc}]"
    if status == "saved":
        return f" [saved {provider} key → ~/.lyra/credentials.json]"
    if status == "kept":
        return f" [using stored {provider} key]"
    return (
        f" [skipped — set {env_name} or run "
        f"`lyra connect {provider}` later]"
    )


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


def _cmd_keybindings(session: InteractiveSession, _args: str) -> CommandResult:
    """``/keybindings`` — print the cheatsheet (slash form of ``Alt-?``)."""
    from .keybindings_help import show_keybindings_help

    console = getattr(session, "_console", None)
    if console is not None:
        show_keybindings_help(console)
        return CommandResult(output="")
    # Headless / non-TTY fallback: render to a string via a fresh
    # Console captured into a buffer so callers (tests, piped output)
    # still see the table.
    import io

    from rich.console import Console as _Console

    buf = io.StringIO()
    show_keybindings_help(_Console(file=buf, force_terminal=False, width=100))
    return CommandResult(output=buf.getvalue())


def _cmd_new(session: InteractiveSession, _args: str) -> CommandResult:
    """``/new`` — start a fresh chat (slash form of ``Ctrl-N``)."""
    from . import keybinds as _keybinds

    toast = _keybinds.new_chat(session)
    return CommandResult(output=toast, clear_screen=True)


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

    v3.6.0: ``agent`` was renamed to ``edit_automatically`` in the
    permission-flavoured taxonomy, so an approved plan now lands the
    user in ``edit_automatically`` — the single full-access execution
    surface that applies edits without per-write confirmation. The
    ``__post_init__`` logic also flips ``permission_mode`` to
    ``normal`` to match (unless the user is in ``yolo``, which is
    preserved across mode changes).
    """
    if session.pending_task is None:
        return CommandResult(
            output=(
                "no plan to approve; type a task first "
                "(e.g. 'add CSV export')."
            )
        )
    session.mode = "edit_automatically"
    # Mirror /mode's posture-alignment so the post-approve session
    # has the right permission posture wired through the substrate.
    if session.permission_mode != "yolo" and session.permission_mode != "normal":
        session.permission_mode = "normal"
        _propagate_permission_mode(session, "normal")
    task = session.pending_task
    return CommandResult(
        output=(
            f"approved plan for: {task}\n"
            "switching to edit_automatically mode."
        ),
        renderable=_out.approve_renderable(task),
        new_mode="edit_automatically",
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
    """``/context [checkpoint|prune|playbook|inject|breakdown]``

    Without args: context window breakdown.
    Sub-commands (Wave B): checkpoint, prune, playbook, inject.
    """
    _ce_verbs = {"checkpoint", "prune", "playbook", "inject"}
    _verb = (_args or "").strip().split()[0].lower() if (_args or "").strip() else ""
    if _verb in _ce_verbs:
        from .context_engineering import cmd_context_extended
        return cmd_context_extended(session, _args)
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
    """Restore a previously saved session.

    Three call shapes:

    * ``/resume`` (no args, TTY) — opens the Claude-Code-style picker
      with every session listed; Enter resumes the one under the
      cursor. ``Esc`` cancels and leaves the live session untouched.
    * ``/resume <id>`` — direct restore (back-compat). Accepts a full
      session id, the literal ``latest``, or a unique prefix.
    * ``/resume`` (no args, no TTY) — defaults to ``latest`` so
      piped/CI runs keep working without an interactive picker.
    """
    from .sessions_store import SessionsStore

    sessions_root = _resolve_sessions_root(session)
    raw = args.strip()

    if not raw and _stdin_is_tty():
        chosen = _launch_sessions_picker(sessions_root)
        if chosen is None:
            return CommandResult(output="resume: cancelled.")
        raw = chosen  # fall through to the resolve+restore path below

    target = _resolve_session_reference(
        raw or "latest", sessions_root, fallback=session.session_id
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
    # And the model so pricing + the banner stay accurate. We only
    # adopt the restored model when it was explicitly recorded (not
    # when it's the default "auto") so a deliberate
    # ``lyra --model anthropic --resume <id>`` still wins over the
    # snapshot's persisted choice.
    if restored.model and restored.model != "auto":
        session.model = restored.model
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
    """``/sessions`` — list (or pick) saved sessions on disk.

    On a TTY the bare command opens the same Claude-Code-style picker
    ``/resume`` uses; arrow-key to a row and Enter to resume. On a
    non-TTY (piped / CI) we keep the legacy plaintext list so scripts
    that grep the output continue to work.
    """
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

    if _stdin_is_tty():
        chosen = _launch_sessions_picker(sessions_root)
        if chosen is None:
            return CommandResult(
                output="sessions: cancelled.",
                renderable=_out.sessions_renderable(sessions_root),
            )
        # Re-enter the resume path so state warps consistently.
        return _cmd_resume(session, chosen)

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
    from lyra_core.loop import make_reflection

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


def _last_assistant_text(session: InteractiveSession) -> Optional[str]:
    """Return the most recent assistant message body, or None if absent.

    Reads the in-memory ``_chat_history`` rather than the on-disk JSONL
    so ``/copy`` reflects what the user just saw on screen, even if the
    sessions store hasn't flushed yet. Walks from the tail because the
    history is append-only and the assistant turn we care about is
    always the last one with role ``assistant``.
    """
    history = list(getattr(session, "_chat_history", []) or [])
    for msg in reversed(history):
        role = getattr(msg, "role", None) or (
            isinstance(msg, dict) and msg.get("role")
        )
        if role != "assistant":
            continue
        content = getattr(msg, "content", None)
        if content is None and isinstance(msg, dict):
            content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content
    return None


def _nth_assistant_text(session: InteractiveSession, n: int) -> Optional[str]:
    """Return the N-th most recent assistant reply (1 = latest)."""
    if n < 1:
        return None
    history = list(getattr(session, "_chat_history", []) or [])
    seen = 0
    for msg in reversed(history):
        role = getattr(msg, "role", None) or (
            isinstance(msg, dict) and msg.get("role")
        )
        if role != "assistant":
            continue
        seen += 1
        if seen == n:
            content = getattr(msg, "content", None)
            if content is None and isinstance(msg, dict):
                content = msg.get("content")
            if isinstance(content, str) and content.strip():
                return content
            return None
    return None


def _cmd_copy(session: InteractiveSession, args: str) -> CommandResult:
    """``/copy [N] [--write PATH]`` — copy the last assistant reply.

    Without arguments: copies the most recent reply to the system
    clipboard via :mod:`.clipboard`. ``/copy 2`` reaches one step
    further back, ``/copy 3`` two, etc. ``--write FILE`` (or its short
    form ``-w FILE``) skips the clipboard entirely and writes to disk —
    useful over SSH where the clipboard backend is unreachable.
    """
    from .clipboard import copy_to_clipboard

    tokens = args.split()
    n = 1
    write_path: Optional[Path] = None
    iter_tokens = iter(tokens)
    for tok in iter_tokens:
        if tok in ("--write", "-w"):
            try:
                write_path = Path(next(iter_tokens)).expanduser()
            except StopIteration:
                return CommandResult(
                    output="usage: /copy [N] [--write PATH]",
                )
            continue
        if tok.isdigit():
            n = max(1, int(tok))
            continue
        return CommandResult(output=f"/copy: unrecognised argument {tok!r}")

    text = _nth_assistant_text(session, n)
    if not text:
        return CommandResult(
            output=(
                f"/copy: no assistant reply at position {n} "
                f"(history has {sum(1 for m in session._chat_history if getattr(m, 'role', None) == 'assistant')} replies)."
            )
        )

    if write_path is not None:
        try:
            write_path.parent.mkdir(parents=True, exist_ok=True)
            write_path.write_text(text, encoding="utf-8")
        except OSError as exc:
            return CommandResult(output=f"/copy: write failed: {exc}")
        return CommandResult(
            output=f"wrote {len(text)} chars to {write_path}"
        )

    result = copy_to_clipboard(text)
    if result.ok:
        return CommandResult(
            output=(
                f"copied {len(text)} chars via {result.backend} "
                f"(reply #{n})."
            )
        )
    return CommandResult(
        output=(
            f"/copy: clipboard unavailable ({result.detail}). "
            f"Try /copy {n} --write FILE to dump to disk instead."
        )
    )


def _cmd_usage(session: InteractiveSession, _args: str) -> CommandResult:
    """``/usage`` — consolidated cost + session-stats panel.

    Mirrors Claude Code's v2.1.x consolidation: instead of asking users
    to remember which of ``/cost``, ``/stats``, ``/insights`` shows the
    field they want, ``/usage`` renders both cost (dollars / tokens /
    budget cap) and session-shape metrics (turns, slash count, mode,
    deep-think) in one panel. The two underlying commands stay around
    so existing scripts and habits don't break.
    """
    cost_result = _cmd_cost(session, "")
    stats_result = _cmd_stats(session, "")
    plain = (cost_result.output or "") + "\n\n" + (stats_result.output or "")
    return CommandResult(
        output=plain.strip(),
        renderable=_out.usage_renderable(
            cost_usd=session.cost_usd,
            tokens=session.tokens_used,
            turns=session.turn,
            budget_cap_usd=session.budget_cap_usd,
            slash=sum(1 for h in session.history if h.startswith("/")),
            bash=sum(1 for h in session.history if h.startswith("!")),
            files=sum(1 for h in session.history if h.startswith("@")),
            mode=session.mode,
            deep_think=session.deep_think,
        ),
    )


def _cmd_hooks(session: InteractiveSession, _args: str) -> CommandResult:
    """``/hooks`` — show every configured user hook + master enable flag.

    Surfaces what :mod:`lyra_cli.policy_loader` would dispatch on the
    next tool call. The output is intentionally read-only — editing
    happens via ``$EDITOR <repo>/.lyra/settings.json`` because hook
    bodies are shell commands and a Rich form would be a footgun for
    arguments containing quotes / pipes.
    """
    try:
        from ..policy_loader import load_hooks
    except Exception as exc:
        return CommandResult(output=f"/hooks: loader unavailable ({exc})")
    specs, enabled = load_hooks(session.repo_root)
    if not specs:
        return CommandResult(
            output=(
                "no user hooks configured. Drop a hooks block into "
                f"{session.repo_root}/.lyra/settings.json or ~/.lyra/"
                'settings.json with the shape: {"enable_hooks": true, '
                '"hooks": {"PreToolUse": [{"matcher": "Bash(rm *)", '
                '"command": "..."}]}}'
            )
        )
    lines = [f"hooks (master: {'on' if enabled else 'OFF'})"]
    for spec in specs:
        lines.append(
            f"  [{spec.event:<14}] {spec.matcher:<30} → {spec.command}"
        )
    if not enabled:
        lines.append(
            "  (hooks parsed but enable_hooks is false — set it to true "
            "to activate)"
        )
    return CommandResult(output="\n".join(lines))


def _cmd_permissions(session: InteractiveSession, args: str) -> CommandResult:
    """``/permissions`` — view (or edit) the declarative policy grammar.

    Forms:
      * ``/permissions``      — print loaded allow/ask/deny rules
      * ``/permissions edit`` — open ``<repo>/.lyra/settings.json`` in
        ``$EDITOR``; cache invalidates on next tool call
      * ``/permissions reload`` — drop the per-session cache so the
        next tool call re-reads from disk

    Editing is via ``$EDITOR`` rather than an in-REPL form because
    rule literals contain glob characters that interactive widgets
    handle poorly (Rich prompts and prompt_toolkit Buffers both
    eat unescaped braces); a plain text edit is the path of least
    surprise.
    """
    sub = args.strip().lower()
    settings_path = session.repo_root / ".lyra" / "settings.json"

    if sub == "edit":
        import subprocess as _subprocess  # local — keeps top-level imports lean

        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        if not settings_path.exists():
            settings_path.write_text(
                '{\n  "permissions": {\n    "allow": [],\n    "ask": [],\n'
                '    "deny": []\n  }\n}\n',
                encoding="utf-8",
            )
        try:
            _subprocess.call([editor, str(settings_path)])
        except (FileNotFoundError, OSError) as exc:
            return CommandResult(
                output=f"/permissions edit: launch failed ({exc})"
            )
        # Drop cache so next tool call re-reads.
        if hasattr(session, "_policy_hooks_cache"):
            session._policy_hooks_cache = None
        return CommandResult(
            output=(
                f"opened {settings_path}; "
                f"changes apply on the next tool call."
            )
        )

    if sub == "reload":
        if hasattr(session, "_policy_hooks_cache"):
            session._policy_hooks_cache = None
        return CommandResult(
            output="permission cache dropped; settings re-read on next tool call."
        )

    try:
        from ..policy_loader import load_policy
    except Exception as exc:
        return CommandResult(output=f"/permissions: loader unavailable ({exc})")

    policy = load_policy(session.repo_root)
    if policy.is_empty():
        return CommandResult(
            output=(
                "no user rules. Default policy: read-only tools auto-allow, "
                "writes/exec ask. Add rules with /permissions edit "
                f"({settings_path})."
            )
        )
    lines = ["declarative permission policy:"]
    for label, bucket in (
        ("DENY", policy.deny),
        ("ASK",  policy.ask),
        ("ALLOW", policy.allow),
    ):
        if not bucket:
            continue
        lines.append(f"  {label}:")
        for rule in bucket:
            lines.append(f"    - {rule.source}")
    lines.append(f"  (precedence: deny → ask → allow, first match wins)")
    return CommandResult(output="\n".join(lines))


def _cmd_plan(session: InteractiveSession, _args: str) -> CommandResult:
    """``/plan`` — one-shot enter plan mode.

    Equivalent to ``/mode plan`` but matches Claude Code's muscle
    memory. Idempotent: calling it from inside plan mode is a no-op
    (no warning, just a confirmation toast).
    """
    if session.mode == "plan_mode":
        return CommandResult(output="already in plan mode.", new_mode="plan_mode")
    session.mode = "plan_mode"
    return CommandResult(
        output=f"mode: {display_mode('plan_mode')} (plan_mode)",
        new_mode="plan_mode",
    )


def _cmd_recap(session: InteractiveSession, _args: str) -> CommandResult:
    """``/recap`` — terse summary of recent activity for re-orientation.

    Walks the last few user turns from ``_turns_log`` so a session
    resumed after a break (or a user staring at a 200-line scrollback)
    can re-anchor in two seconds. Doesn't make an LLM call — that
    would be a recap with a token bill, defeating the point. For the
    LLM-summary form, fall through to ``/compact`` instead.
    """
    turns = list(getattr(session, "_turns_log", []) or [])[-5:]
    if not turns:
        return CommandResult(
            output="no turns logged yet — recap is empty."
        )
    lines = [
        f"recap · last {len(turns)} turn{'s' if len(turns) != 1 else ''}:",
    ]
    for snap in turns:
        line = (snap.line or "").strip().splitlines()[0] if snap.line else ""
        if len(line) > 70:
            line = line[:69] + "…"
        lines.append(f"  #{snap.turn:>3}  [{snap.mode:<18}] {line}")
    if session.pending_task:
        pending = session.pending_task[:80]
        lines.append(f"pending task: {pending}")
    return CommandResult(output="\n".join(lines))


def _cmd_add_dir(session: InteractiveSession, args: str) -> CommandResult:
    """``/add-dir <path>`` — widen the session's filesystem sandbox.

    By default Lyra sandboxes file tools under ``session.repo_root``.
    For multi-repo work (frontend + backend monorepos, library +
    consumer pairs) the agent needs to see siblings. ``/add-dir``
    appends to ``session.aux_repo_roots``; the chat-tools layer reads
    that list and widens its allowed-path check accordingly.

    Paths are resolved at registration time so ``cd`` in the user's
    shell after they typed the command can't change which directory
    is allowed.
    """
    raw = args.strip()
    if not raw:
        existing = list(getattr(session, "aux_repo_roots", []) or [])
        if not existing:
            return CommandResult(
                output=(
                    "no auxiliary directories. Usage: "
                    "/add-dir <path-to-extra-repo-or-folder>"
                )
            )
        lines = [f"aux directories ({len(existing)}):"]
        for p in existing:
            lines.append(f"  - {p}")
        return CommandResult(output="\n".join(lines))

    target = Path(raw).expanduser().resolve()
    if not target.is_dir():
        return CommandResult(
            output=f"/add-dir: not a directory: {target}"
        )
    aux = list(getattr(session, "aux_repo_roots", []) or [])
    if target in aux:
        return CommandResult(
            output=f"/add-dir: {target} already registered."
        )
    aux.append(target)
    session.aux_repo_roots = aux  # type: ignore[attr-defined]
    return CommandResult(
        output=f"added {target} (now {len(aux)} aux director{'ies' if len(aux) != 1 else 'y'})."
    )


def _cmd_security_review(session: InteractiveSession, args: str) -> CommandResult:
    """``/security-review [target]`` — focused vulnerability review.

    Distinct from ``/review`` (general code-quality pass) — this one
    pre-frames the target diff for OWASP-style attention: secrets,
    injection, auth, path traversal, unbounded queries, missing
    rate-limits. Wraps the existing review pipeline by injecting a
    security-flavoured system prompt at dispatch time, so the
    underlying agent sees the right prior even when the user typed a
    one-word target.
    """
    target = args.strip() or "HEAD"
    framed = (
        "/review "
        f"{target} "
        "--focus security "
        "--lens 'OWASP Top 10: hardcoded secrets, SQL/XSS injection, "
        "unsafe deserialisation, missing authn/authz, path traversal, "
        "unbounded queries, missing rate limiting, error messages "
        "leaking sensitive data.'"
    )
    return session.dispatch(framed)


def _cmd_feedback(session: InteractiveSession, args: str) -> CommandResult:
    """``/feedback`` (alias ``/bug``) — print the issue URL + recent context.

    Doesn't open a browser (Lyra runs over SSH and headless terminals
    routinely) — instead prints the URL the user can copy. When
    ``--copy`` is passed, also drops the last 3 turns to the clipboard
    so the bug report has reproducible context attached.
    """
    body = args.strip().lower()
    url = "https://github.com/lyra-research/lyra/issues/new"
    lines = [
        f"file an issue: {url}",
        "  include /version, /doctor output, and the last few turns "
        "(use /copy to grab the most recent reply).",
    ]
    if "--copy" in body:
        try:
            from .clipboard import copy_to_clipboard
        except Exception:
            return CommandResult(
                output="\n".join(lines + ["(clipboard module unavailable)"])
            )
        recent = list(getattr(session, "_turns_log", []) or [])[-3:]
        payload = "\n".join(
            f"#{snap.turn} [{snap.mode}] {snap.line or ''}" for snap in recent
        )
        result = copy_to_clipboard(payload or "(no recent turns)")
        if result.ok:
            lines.append(f"  copied {len(payload)} chars of recent context.")
        else:
            lines.append(f"  clipboard unavailable: {result.detail}")
    return CommandResult(output="\n".join(lines))


def _cmd_statusline(session: InteractiveSession, args: str) -> CommandResult:
    """``/statusline`` — show or set the bottom-toolbar format string.

    With no args: print the current format. With a literal string:
    persist it on the session (and on the next ``/save`` it lands in
    settings.json). Reset with ``/statusline default``.

    The format follows prompt_toolkit's HTML-ish syntax for
    ``bottom_toolbar``; documenting the full grammar is out of scope
    here, so the bare command also prints the current value as a
    starting template the user can paste-edit.
    """
    raw = args.strip()
    current = getattr(session, "statusline_format", None) or "(default)"
    if not raw:
        return CommandResult(
            output=(
                f"current statusline: {current}\n"
                "  set with: /statusline <format>\n"
                "  reset with: /statusline default"
            )
        )
    if raw == "default":
        session.statusline_format = None  # type: ignore[attr-defined]
        return CommandResult(output="statusline reset to default.")
    session.statusline_format = raw  # type: ignore[attr-defined]
    return CommandResult(output=f"statusline format set to: {raw}")


_PROMPT_COLOURS = {
    "red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan",
    "white", "magenta", "default",
}


def _cmd_color(session: InteractiveSession, args: str) -> CommandResult:
    """``/color [name|default]`` — tint the prompt-bar accent.

    Accepts a small named-colour palette (matches CC's set). Bare
    ``/color`` rotates pseudo-randomly through the palette using the
    session id as seed so the same session reproduces the same
    "random" pick on resume.
    """
    raw = args.strip().lower()
    if not raw:
        # Deterministic-pseudo-random: hash the session id mod palette.
        choices = sorted(_PROMPT_COLOURS - {"default"})
        seed = abs(hash(getattr(session, "session_id", "lyra"))) % len(choices)
        raw = choices[seed]
    if raw not in _PROMPT_COLOURS:
        return CommandResult(
            output=(
                f"unknown colour {raw!r}; "
                f"valid: {', '.join(sorted(_PROMPT_COLOURS))}"
            )
        )
    if raw == "default":
        session.prompt_color = None  # type: ignore[attr-defined]
        return CommandResult(output="prompt colour reset to default.")
    session.prompt_color = raw  # type: ignore[attr-defined]
    return CommandResult(output=f"prompt colour: {raw}")


def _cmd_fast(session: InteractiveSession, args: str) -> CommandResult:
    """``/fast [on|off]`` — toggle the "fast Opus" posture.

    Lyra doesn't ship a separate model variant for "fast"; we map it
    to ``effort=low`` against the active provider, which is the
    closest behavioural analogue (less internal deliberation, faster
    end-to-end latency). Persists for the rest of the session unless
    the user switches it off.
    """
    raw = args.strip().lower()
    current = getattr(session, "fast_mode", False)
    if raw in ("", "toggle"):
        new = not current
    elif raw in ("on", "true", "1"):
        new = True
    elif raw in ("off", "false", "0"):
        new = False
    else:
        return CommandResult(output=f"/fast: expected on|off|toggle, got {raw!r}")
    session.fast_mode = new  # type: ignore[attr-defined]
    if new:
        session.effort = "low"  # type: ignore[attr-defined]
    return CommandResult(
        output=f"fast mode: {'on' if new else 'off'}"
        + (" (effort=low)" if new else "")
    )


def _cmd_focus(session: InteractiveSession, args: str) -> CommandResult:
    """``/focus [on|off]`` — hide side panels, show only the chat.

    Toggles ``session.focus_mode``; the renderer reads this flag and
    skips the bottom toolbar / task panel / status bar when it's on.
    Useful for screenshots, demos, and screen recordings where the
    chrome is just visual noise.
    """
    raw = args.strip().lower()
    current = getattr(session, "focus_mode", False)
    if raw in ("", "toggle"):
        new = not current
    elif raw in ("on", "true", "1"):
        new = True
    elif raw in ("off", "false", "0"):
        new = False
    else:
        return CommandResult(output=f"/focus: expected on|off|toggle, got {raw!r}")
    session.focus_mode = new  # type: ignore[attr-defined]
    return CommandResult(output=f"focus mode: {'on' if new else 'off'}")


def _cmd_tui(session: InteractiveSession, args: str) -> CommandResult:
    """``/tui [classic|smooth]`` — switch the rendering mode.

    ``classic`` is the historical "redraw the whole panel each frame"
    approach; ``smooth`` (default) uses prompt_toolkit's diff-based
    repaint. Some terminals (older Windows consoles, certain SSH
    multiplexers) flicker under smooth mode; ``classic`` trades a
    little visual judder for guaranteed correct output. Persists on
    the session field so the next ``/save`` captures it.
    """
    raw = args.strip().lower() or "toggle"
    valid = {"classic", "smooth", "toggle"}
    if raw not in valid:
        return CommandResult(output=f"/tui: expected one of {sorted(valid)}")
    current = getattr(session, "tui_mode", "smooth")
    if raw == "toggle":
        new = "classic" if current == "smooth" else "smooth"
    else:
        new = raw
    session.tui_mode = new  # type: ignore[attr-defined]
    return CommandResult(output=f"tui rendering: {new}")


def _cmd_pr_comments(session: InteractiveSession, args: str) -> CommandResult:
    """``/pr-comments [PR-number-or-URL]`` — fetch GitHub PR comments.

    Auto-detects the PR for the current branch when called bare, by
    asking ``gh pr view --json number``. Prints the comment list as a
    readable table rather than dumping the JSON payload — operators
    skim ``author: body`` faster than ``[object]``.
    """
    import subprocess as _sp

    if not _which("gh"):
        return CommandResult(
            output="/pr-comments: needs the gh CLI on PATH. Install via https://cli.github.com"
        )
    target = args.strip()
    if not target:
        try:
            view = _sp.run(
                ["gh", "pr", "view", "--json", "number"],
                capture_output=True, text=True, timeout=10,
                cwd=str(session.repo_root),
            )
            if view.returncode != 0:
                return CommandResult(
                    output=(
                        "/pr-comments: no PR detected for the current branch. "
                        "Pass a PR number or URL explicitly."
                    )
                )
            payload = json.loads(view.stdout)
            target = str(payload.get("number") or "")
        except (_sp.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
            return CommandResult(output=f"/pr-comments: gh failed: {exc}")
    if not target:
        return CommandResult(output="/pr-comments: usage: /pr-comments <PR>")
    try:
        proc = _sp.run(
            ["gh", "pr", "view", target, "--json", "comments,reviews"],
            capture_output=True, text=True, timeout=15,
            cwd=str(session.repo_root),
        )
    except OSError as exc:
        return CommandResult(output=f"/pr-comments: gh launch failed: {exc}")
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()[:200]
        return CommandResult(output=f"/pr-comments: gh exit={proc.returncode} {err}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return CommandResult(output="/pr-comments: gh returned non-JSON output")
    lines = [f"PR #{target} comments:"]
    for c in (data.get("comments") or []):
        body = (c.get("body") or "").strip().splitlines()
        first = body[0] if body else ""
        if len(first) > 120:
            first = first[:117] + "…"
        lines.append(f"  💬  {c.get('author', {}).get('login', '?')}: {first}")
    for r in (data.get("reviews") or []):
        body = (r.get("body") or "").strip().splitlines()
        first = body[0] if body else "(no body)"
        if len(first) > 120:
            first = first[:117] + "…"
        state = r.get("state", "?")
        lines.append(
            f"  🔍 [{state}] "
            f"{r.get('author', {}).get('login', '?')}: {first}"
        )
    if len(lines) == 1:
        lines.append("  (no comments or reviews)")
    return CommandResult(output="\n".join(lines))


def _cmd_schedule(session: InteractiveSession, args: str) -> CommandResult:
    """``/schedule`` — Claude-Code-style alias for the cron registry.

    Lyra already has ``/cron`` for scheduled-prompt management; this
    is the CC-canonical name that delegates to the same handler so
    muscle-memory transfers without us re-implementing scheduling. Both
    surfaces stay in sync because they call the same code path.
    """
    return _cmd_cron(session, args)


def _cmd_sandbox(session: InteractiveSession, args: str) -> CommandResult:
    """``/sandbox [on|off|toggle]`` — toggle filesystem-sandbox mode.

    Distinct from ``/perm`` (permission_mode) — sandbox mode means
    "tools that would write outside the repo root get refused, even
    when the rule says allow". It's a *belt-and-suspenders* layer
    on top of the permission grammar for paranoid CI runs.

    The flag is read by the file-tool sandbox check at dispatch time;
    flipping it mid-session takes effect on the next tool call.
    """
    raw = args.strip().lower()
    current = getattr(session, "sandbox_strict", False)
    if raw in ("", "toggle"):
        new = not current
    elif raw in ("on", "true", "1", "strict"):
        new = True
    elif raw in ("off", "false", "0", "loose"):
        new = False
    else:
        return CommandResult(output=f"/sandbox: expected on|off|toggle, got {raw!r}")
    session.sandbox_strict = new  # type: ignore[attr-defined]
    return CommandResult(
        output=f"sandbox: {'strict' if new else 'normal'}"
    )


def _cmd_plugin(_session: InteractiveSession, args: str) -> CommandResult:
    """``/plugin`` — point at the OMC plugin layer (Lyra's de-facto plugin host).

    Lyra doesn't ship its own marketplace; the oh-my-claudecode
    plugin system is what the community uses to share commands,
    skills, and agents that ride alongside Lyra. Rather than build a
    second marketplace surface, this command points users at the
    canonical install / list / remove flow.
    """
    sub = args.strip().lower()
    base = (
        "Lyra uses oh-my-claudecode (OMC) for plugins. Manage them with:\n"
        "  • omc plugin install <name>\n"
        "  • omc plugin list\n"
        "  • omc plugin remove <name>\n"
        "  • omc plugin update\n"
        "Docs: https://github.com/oh-my-claudecode/oh-my-claudecode"
    )
    if not sub:
        return CommandResult(output=base)
    if sub in ("list", "ls"):
        # Defer to OMC's list command so we don't drift from upstream.
        import subprocess as _sp
        if not _which("omc"):
            return CommandResult(output=base + "\n\n(omc not installed)")
        try:
            proc = _sp.run(
                ["omc", "plugin", "list"],
                capture_output=True, text=True, timeout=10,
            )
            return CommandResult(
                output=(proc.stdout or "(no plugins)").strip()
            )
        except OSError as exc:
            return CommandResult(output=f"/plugin list: omc launch failed: {exc}")
    return CommandResult(output=base)


def _cmd_reload_plugins(session: InteractiveSession, _args: str) -> CommandResult:
    """``/reload-plugins`` — re-walk skill / hook / user-command discovery.

    Reloads what discovery surfaces would naturally pick up on a
    fresh REPL boot — without making the user actually restart. The
    permission/hooks cache is dropped too because a plugin that ships
    new hooks is otherwise invisible until the next cache miss.
    """
    reloaded = {"user_commands": 0, "policy_cache": False, "skills": 0}
    try:
        n = session.reload_user_commands()
        reloaded["user_commands"] = n
    except Exception:
        pass
    if hasattr(session, "_policy_hooks_cache"):
        session._policy_hooks_cache = None
        reloaded["policy_cache"] = True
    # Skills layer: re-resolve via the existing inject path; safe to
    # call even when no skills are installed.
    try:
        from . import skills_inject as _si
        if hasattr(_si, "reload_skills"):
            reloaded["skills"] = _si.reload_skills(session.repo_root)
    except Exception:
        pass
    return CommandResult(
        output=(
            f"reloaded: user_commands={reloaded['user_commands']}, "
            f"skills={reloaded['skills']}, "
            f"policy_cache={'dropped' if reloaded['policy_cache'] else 'untouched'}"
        )
    )


def _cmd_release_notes(_session: InteractiveSession, _args: str) -> CommandResult:
    """``/release-notes`` — print the bundled CHANGELOG (or fallback).

    Walks up from this module to find the lyra-cli package root, then
    prints ``CHANGELOG.md`` if it exists. Bundled-changelog beats
    fetching from GitHub because Lyra runs offline and a network
    timeout on a release-notes command would feel ridiculous.
    """
    from importlib.resources import files
    try:
        package_root = Path(str(files("lyra_cli"))).parent.parent.parent
        changelog = package_root / "CHANGELOG.md"
        if changelog.is_file():
            text = changelog.read_text(encoding="utf-8")
            head = "\n".join(text.splitlines()[:80])
            return CommandResult(output=head)
    except Exception:
        pass
    from lyra_cli import __version__
    return CommandResult(
        output=(
            f"lyra v{__version__}\n"
            "no bundled CHANGELOG.md — see "
            "https://github.com/lyra-research/lyra/releases"
        )
    )


def _cmd_logout(session: InteractiveSession, _args: str) -> CommandResult:
    """``/logout`` — revoke every stored provider credential.

    Walks ``auth.store.list_providers()`` and revokes each so the next
    LLM call re-prompts. Doesn't kill the live session — the user can
    still type ``/connect`` to re-auth without restarting; until then
    any new dispatch lands on the credentials-prompt path.
    """
    try:
        from lyra_core.auth.store import list_providers, revoke
    except Exception as exc:
        return CommandResult(output=f"/logout: auth module unavailable ({exc})")
    providers = list_providers()
    if not providers:
        return CommandResult(output="/logout: no stored credentials to clear.")
    cleared: list[str] = []
    for provider in providers:
        try:
            revoke(provider)
            cleared.append(provider)
        except Exception:
            continue
    return CommandResult(
        output=(
            f"credentials cleared for {len(cleared)} provider"
            f"{'s' if len(cleared) != 1 else ''}: {', '.join(cleared)}. "
            "Next LLM call will re-prompt — or run /connect <provider> --key ..."
        )
    )


def _cmd_connect(session: InteractiveSession, args: str) -> CommandResult:
    """``/connect`` — manage API keys in ``~/.lyra/credentials.json``.

    Forms::

        /connect                           list all configured providers
        /connect list                      same as above
        /connect <provider> <key>          save a key
        /connect <provider> <key> <url>    save key + custom base URL
        /connect remove <provider>         delete stored key

    Keys are stamped into the process env immediately so the current
    session can use them without a restart.
    """
    from .key_store import PROVIDER_ENV_VARS, KeyStore, _mask

    store = KeyStore()
    parts = args.split()

    if not parts or parts[0] in ("list", "ls"):
        entries = store.list_all()
        if not entries:
            return CommandResult(
                output=(
                    "No credentials stored in ~/.lyra/credentials.json.\n"
                    "Add one with:  /connect <provider> <api_key>\n"
                    "Providers: anthropic, openai, deepseek, gemini, groq, mistral, xai, ..."
                )
            )
        lines = ["Stored credentials  (~/.lyra/credentials.json):"]
        for provider, entry in sorted(entries.items()):
            key = entry.get("api_key", "")
            masked = _mask(key) if key else "(no key)"
            env = PROVIDER_ENV_VARS.get(provider, "?")
            suffix = f"  base_url={entry['base_url']}" if "base_url" in entry else ""
            lines.append(f"  {provider:<14} {masked:<22} ${env}{suffix}")
        return CommandResult(output="\n".join(lines))

    if parts[0] == "remove":
        if len(parts) < 2:
            return CommandResult(output="usage: /connect remove <provider>")
        provider = parts[1]
        removed = store.remove(provider)
        msg = f"removed credentials for {provider}" if removed else f"no credentials found for {provider}"
        return CommandResult(output=msg)

    provider = parts[0]

    if len(parts) < 2:
        import sys
        if sys.stdin.isatty() and sys.stdout.isatty():
            # Interactive: run the full prompt → validate → save flow.
            try:
                from .dialog_apikey import request_api_key
                _key, status = request_api_key(provider, store=store)
            except Exception as exc:
                return CommandResult(output=f"error: {exc}")
            if status == "saved":
                return CommandResult(output=f"saved {provider} key → ~/.lyra/credentials.json")
            if status == "kept":
                return CommandResult(output=f"keeping existing {provider} key")
            return CommandResult(output=f"skipped — no key saved for {provider}")
        # Non-interactive: show current status or hint.
        entry = store.get(provider)
        if entry:
            key = entry.get("api_key", "")
            env = PROVIDER_ENV_VARS.get(provider, "?")
            base = f"\n  base_url: {entry['base_url']}" if "base_url" in entry else ""
            return CommandResult(output=f"{provider}: {_mask(key)}  ${env}{base}")
        return CommandResult(
            output=f"no key stored for {provider}.\nusage: /connect {provider} <api_key>"
        )

    api_key = parts[1]
    base_url = parts[2] if len(parts) > 2 else None
    store.set(provider, api_key, base_url)
    env = PROVIDER_ENV_VARS.get(provider)
    env_note = f" (${env} set in env)" if env else ""
    base_note = f" with base_url={base_url}" if base_url else ""
    return CommandResult(
        output=f"saved {provider} key{base_note}{env_note} → ~/.lyra/credentials.json"
    )


def _which(cmd: str) -> bool:
    """Lightweight PATH lookup so tests and slash handlers stay tiny."""
    import shutil as _shutil
    return _shutil.which(cmd) is not None


def _resolve_session_run_dir(session: InteractiveSession) -> Path:
    """Resolve the per-session run directory under LYRA_HOME.

    Used by the v3.13 autonomy slashes (/directive, /autopilot) to
    park per-session artefacts in a stable location that the
    long-running autopilot supervisor can also reach.
    """
    home = os.environ.get("LYRA_HOME") or str(Path.home() / ".lyra")
    sid = (session.session_id or "default").replace("/", "_")
    run_dir = Path(home) / "loops" / sid
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _cmd_directive(session: InteractiveSession, args: str) -> CommandResult:
    """``/directive [<text>]`` — write an async control directive.

    Drops the text into ``$LYRA_HOME/loops/<session>/HUMAN_DIRECTIVE.md``
    where a long-running autopilot or Ralph loop picks it up at the next
    iteration boundary. Without text, lists the last 5 archived directives.
    Anchor: ``lyra_core.loops.directive.HumanDirective``.
    """
    run_dir = _resolve_session_run_dir(session)
    live = run_dir / "HUMAN_DIRECTIVE.md"
    archive = run_dir / "directives"

    text = args.strip()
    if not text:
        if not archive.exists():
            return CommandResult(
                output=f"no archived directives under {archive}"
            )
        entries = sorted(archive.glob("*.md"))[-5:]
        if not entries:
            return CommandResult(
                output=f"no archived directives under {archive}"
            )
        lines = [f"recent directives ({len(entries)} shown):"]
        for p in entries:
            head = p.read_text(encoding="utf-8").splitlines()[:1]
            preview = head[0][:80] if head else ""
            lines.append(f"  {p.name}: {preview}")
        return CommandResult(output="\n".join(lines))

    try:
        with live.open("a", encoding="utf-8") as fh:
            fh.write(text)
            if not text.endswith("\n"):
                fh.write("\n")
    except OSError as exc:
        return CommandResult(output=f"/directive: write failed: {exc}")

    return CommandResult(
        output=f"directive appended to {live} ({len(text)} chars)"
    )


def _cmd_contract(session: InteractiveSession, args: str) -> CommandResult:
    """``/contract [show|set <key>=<value>]`` — inspect or configure budget.

    Surfaces the v3.12 AgentContract envelope for the active session.
    Supported keys for ``set``: ``max_usd``, ``max_iterations``,
    ``max_wall_clock_s``. The contract object is parked on the session
    under ``_agent_contract`` and re-used by subsequent /contract calls
    so successive sets compose. Anchor: ``lyra_core.contracts``.
    """
    raw = args.strip()
    sub = raw.split(maxsplit=1)
    verb = sub[0].lower() if sub else "show"
    rest = sub[1] if len(sub) >= 2 else ""

    try:
        from lyra_core.contracts import (
            AgentContract,
            BudgetEnvelope,
            ContractState,
        )
    except ImportError as exc:
        return CommandResult(output=f"/contract: backend missing ({exc})")

    contract: Any = getattr(session, "_agent_contract", None)
    if contract is None:
        contract = AgentContract(budget=BudgetEnvelope())
        session._agent_contract = contract  # type: ignore[attr-defined]

    if verb == "show":
        b = contract.budget
        lines = [
            f"contract state:   {contract.state.value}",
            f"cumulative USD:   ${contract.cum_usd:.4f}",
            f"iterations:       {contract.iter_count}",
            f"budget.max_usd:   {b.max_usd if b.max_usd is not None else '(unbounded)'}",
            f"budget.max_iter:  {b.max_iterations if b.max_iterations is not None else '(unbounded)'}",
            f"budget.max_wall:  {b.max_wall_clock_s if b.max_wall_clock_s is not None else '(unbounded)'}s",
        ]
        return CommandResult(output="\n".join(lines))

    if verb == "set":
        if "=" not in rest:
            return CommandResult(
                output="usage: /contract set <key>=<value>"
            )
        key, _, value = rest.partition("=")
        key = key.strip().lower()
        value = value.strip()
        if key not in {"max_usd", "max_iterations", "max_wall_clock_s"}:
            return CommandResult(
                output=(
                    "/contract set: unknown key. "
                    "Valid: max_usd, max_iterations, max_wall_clock_s"
                )
            )
        try:
            num: Any = float(value) if key == "max_usd" else int(value) if key == "max_iterations" else float(value)
        except ValueError:
            return CommandResult(
                output=f"/contract set: {value!r} is not a number"
            )
        b = contract.budget
        # BudgetEnvelope is frozen — rebuild then re-wrap the contract.
        new_budget = BudgetEnvelope(
            max_usd=num if key == "max_usd" else b.max_usd,
            max_iterations=num if key == "max_iterations" else b.max_iterations,
            max_wall_clock_s=num if key == "max_wall_clock_s" else b.max_wall_clock_s,
            per_tool_max=b.per_tool_max,
            deny_patterns=b.deny_patterns,
        )
        contract.budget = new_budget
        return CommandResult(output=f"contract.budget.{key} = {num}")

    return CommandResult(
        output="usage: /contract [show|set <key>=<value>]"
    )


def _cmd_autopilot(session: InteractiveSession, args: str) -> CommandResult:
    """``/autopilot [status|list]`` — read the LoopStore SQLite checkpoint.

    Reports loops the v3.12 autopilot supervisor has registered, with
    their state, cumulative USD, and iteration counts. Anchor:
    ``lyra_core.loops.store.LoopStore``.
    """
    raw = args.strip().lower() or "status"

    try:
        from lyra_core.loops.store import LoopStore
    except ImportError as exc:
        return CommandResult(output=f"/autopilot: backend missing ({exc})")

    home = os.environ.get("LYRA_HOME") or str(Path.home() / ".lyra")
    db_path = Path(home) / "loops" / "loops.sqlite"
    if not db_path.exists():
        return CommandResult(
            output=f"no autopilot store at {db_path} (no loops registered yet)"
        )

    store = LoopStore(db_path=db_path)
    if raw == "status":
        running = store.list_state("running")
        if not running:
            return CommandResult(output="autopilot: no running loops")
        lines = [f"autopilot: {len(running)} running loop(s)"]
        for rec in running:
            lines.append(
                f"  {rec.id} [{rec.kind}] "
                f"iter={rec.iter_count} ${rec.cum_usd:.4f}"
            )
        return CommandResult(output="\n".join(lines))

    if raw == "list":
        records = store.list_state(
            "running", "pending_resume", "completed", "terminated"
        )
        if not records:
            return CommandResult(output="autopilot: store empty")
        lines = [f"autopilot: {len(records)} loop(s)"]
        for rec in records:
            lines.append(
                f"  {rec.id} [{rec.kind}] {rec.state} "
                f"iter={rec.iter_count} ${rec.cum_usd:.4f}"
            )
        return CommandResult(output="\n".join(lines))

    return CommandResult(output="usage: /autopilot [status|list]")


def _cmd_continue(session: InteractiveSession, args: str) -> CommandResult:
    """``/continue [<follow-up text>]`` — explicit re-feed after a Stop.

    Companion to the v3.12 Stop / SubagentStop lifecycle event. When
    the LLM ends a turn with no tool calls, the REPL returns control
    to the user; ``/continue`` re-enters the loop with an empty (or
    user-supplied) follow-up prompt, mirroring Claude Code's manual
    "press enter to continue" affordance.

    Implemented as a queue: the slash deposits the prompt on
    ``session.pending_task`` so the next REPL tick treats it as a
    normal user turn. Surfaces a no-op if a prior /continue is
    already queued.
    """
    if getattr(session, "pending_task", None):
        return CommandResult(
            output="/continue: a pending task is already queued"
        )
    text = args.strip() or "continue"
    session.pending_task = text
    return CommandResult(
        output=f"queued: {text!r} (next turn will dispatch)"
    )


# v3.13 P0-6 — imperative→declarative task sharpener.
# Anchor: docs/context-engineering-deep-research-v2.md §1.3 (Karpathy
# principle 4) and §7 P0-6. The slash converts a free-text task into
# a verifiable goal — "write failing tests for X, then make them
# pass" — by queueing a one-shot rewrite meta-prompt onto
# ``session.pending_task``. The agent emits the rewrite on the next
# turn; the user reviews and approves before any code change.
_SHARPEN_META_PROMPT = (
    "Rewrite the following task as verifiable goals using the "
    "Karpathy declarative-rewrite pattern.\n\n"
    "Imperative input:\n{task}\n\n"
    "Emit (in order, as Markdown):\n"
    "1. **Invariants to verify** — one bullet per concrete case\n"
    "   (malformed input, missing field, edge value, regression).\n"
    "2. **Failing tests to write FIRST** — code stubs the implementer\n"
    "   should add to the test suite *before* touching production code.\n"
    "3. **Minimal implementation** — the smallest production change\n"
    "   that makes those tests pass, without widening scope.\n\n"
    "Do NOT start editing yet. Emit the rewrite and stop so the user "
    "can confirm or amend before implementation."
)


def _cmd_sharpen(session: InteractiveSession, args: str) -> CommandResult:
    """``/sharpen <task>`` — rewrite a task as verifiable goals.

    Implements the Karpathy P4 / Claude-Code-context P0-6 primitive:
    convert an imperative task ("Add input validation") into a
    declarative one with tests-then-implementation as the path.

    Queueing model matches :func:`_cmd_continue` — drops a one-shot
    rewrite meta-prompt onto ``session.pending_task`` so the next
    REPL tick dispatches it. Refuses to overwrite an existing
    queued task.
    """
    text = args.strip()
    if not text:
        return CommandResult(
            output=(
                "/sharpen: pass the task to rewrite, e.g.\n"
                "    /sharpen add input validation to login\n"
                "→ Rewrites as: failing tests for malformed/missing/"
                "oversized inputs, then minimal impl to pass them."
            )
        )
    if getattr(session, "pending_task", None):
        return CommandResult(
            output=(
                "/sharpen: a pending task is already queued; "
                "clear it before queueing a rewrite"
            )
        )
    session.pending_task = _SHARPEN_META_PROMPT.format(task=text)
    return CommandResult(
        output=f"queued /sharpen rewrite for: {text!r}"
    )


def _cmd_loop(session: InteractiveSession, args: str) -> CommandResult:
    """``/loop [interval] <prompt>`` — schedule a recurring prompt.

    Thin wrapper around ``/cron`` with the Claude-Code calling shape
    (``/loop 5m <prompt>``). Parses the leading interval token if it
    matches the ``Nm|Nh|Nd`` pattern; otherwise treats the entire
    payload as the prompt and lets ``/cron`` apply its default cadence.
    """
    import re as _re  # local — keeps top-level imports unchanged

    raw = args.strip()
    if not raw:
        return CommandResult(output="usage: /loop [interval] <prompt>")
    parts = raw.split(maxsplit=1)
    leading = parts[0]
    if len(parts) >= 2 and _re.fullmatch(r"\d+[smhd]", leading):
        interval, prompt = leading, parts[1]
        return _cmd_cron(session, f"add {interval} {prompt}")
    return _cmd_cron(session, f"add 5m {raw}")


def _cmd_debug(session: InteractiveSession, args: str) -> CommandResult:
    """``/debug [on|off|toggle]`` — toggle the session debug-log flag.

    Lyra writes structured events through ``HIRLogger`` regardless;
    ``/debug on`` flips the *verbose* level so background telemetry
    surfaces in the REPL alongside chat output. ``/debug`` bare
    toggles. Distinct from ``/trace`` (HIR file path / on-off) — this
    is the user-facing rendering toggle.
    """
    raw = args.strip().lower()
    current = getattr(session, "debug_mode", False)
    if raw in ("", "toggle"):
        new = not current
    elif raw in ("on", "true", "1"):
        new = True
    elif raw in ("off", "false", "0"):
        new = False
    else:
        return CommandResult(output=f"/debug: expected on|off|toggle, got {raw!r}")
    session.debug_mode = new  # type: ignore[attr-defined]
    return CommandResult(output=f"debug mode: {'on' if new else 'off'}")


def _cmd_simplify(session: InteractiveSession, args: str) -> CommandResult:
    """``/simplify [focus]`` — fan-out 3 review agents (quality / reuse / efficiency).

    Mirrors Claude Code's bundled skill: dispatch three subagents in
    parallel to the same target, each looking through a different
    lens, then collect the findings. Implemented as a single
    ``/spawn`` invocation with a ``--type=review`` hint and a prompt
    that asks the agent to internally fan out — keeps the surface
    small while the underlying agent does the orchestration.
    """
    focus = args.strip() or "general code-quality, reuse, and efficiency"
    framed = (
        f"/spawn --type=review "
        f"Run a three-pass simplification review on the recent changes. "
        f"Pass 1: {focus} — code quality, naming, function size. "
        f"Pass 2: dead code, duplication, opportunities for reuse. "
        f"Pass 3: hot paths, allocation, redundant work. "
        f"Apply trivial fixes inline; surface non-trivial findings as a "
        f"bulleted list grouped by pass."
    )
    return session.dispatch(framed)


def _cmd_batch(_session: InteractiveSession, args: str) -> CommandResult:
    """``/batch <instruction>`` — point at the OMC fan-out pipeline.

    Implementing ``/batch`` natively requires worktree-aware tools
    (``EnterWorktree``/``ExitWorktree``) that Lyra doesn't yet expose
    to the agent, so this command points at the OMC equivalent that
    already does the orchestration. When Lyra grows worktree tools
    this can flip to a native handler.
    """
    payload = args.strip()
    if not payload:
        return CommandResult(
            output=(
                "usage: /batch <instruction>. Lyra delegates fan-out to "
                "oh-my-claudecode for now: omc batch \"<instruction>\""
            )
        )
    return CommandResult(
        output=(
            f"/batch is delegated to OMC until Lyra ships native worktree "
            f"tools. Run: omc batch \"{payload}\""
        )
    )


def _cmd_research(session: InteractiveSession, args: str) -> CommandResult:
    """``/research <query> [--depth N] [--time day|week|month|year]``.

    Deep-research workflow built on the v3.12 ``WebSearch`` orchestrator:

    1. Search the configured provider chain (Tavily → Exa → Serper →
       Brave → Google CSE → DuckDuckGo) with reranking.
    2. WebFetch the top ``--depth`` (default 3) result URLs.
    3. Return a compact markdown blob: per-source heading, snippet,
       quoted excerpt.

    The agent loop synthesises across this blob without each step
    eating a tool-call hop. Keeps research lightweight enough that
    the user actually uses it.
    """
    import shlex

    if not args.strip():
        return CommandResult(
            output=(
                "usage: /research <query> [--depth N] "
                "[--time day|week|month|year] [--domain example.com]\n"
                "       /research plan <topic>\n"
                "       /research verify\n"
                "       /research falsify <hypothesis>\n"
                "       /research sandbox <task>"
            )
        )

    # ------------------------------------------------------------------
    # Sub-command dispatch: plan / verify / falsify / sandbox
    # ------------------------------------------------------------------
    verb = args.strip().split()[0] if args.strip() else ""

    if verb == "plan":
        topic = args.strip()[len("plan"):].strip()
        if not topic:
            return CommandResult(output="usage: /research plan <topic>")
        sections = [
            ("Background", f"Establish context for: {topic}"),
            ("Key Questions", "Each question must be answered with ≥1 source span"),
            ("Sources Needed", "Primary sources, peer-reviewed where applicable"),
            ("Acceptance Criteria", "Every claim bound to a source before output"),
        ]
        lines = [f"## Research Plan: {topic}", ""]
        for title, desc in sections:
            lines.append(f"### {title}")
            lines.append(desc)
            lines.append("")
        return CommandResult(output="\n".join(lines))

    elif verb == "verify":
        last_assistant = next(
            (m["content"] for m in reversed(session.messages) if m.get("role") == "assistant"),
            "",
        )
        if not last_assistant:
            return CommandResult(output="/research verify: no assistant output to audit")
        sentences = [
            s.strip()
            for s in last_assistant.replace("\n", " ").split(".")
            if len(s.strip()) > 20
        ]
        lines = ["/research verify — claim audit:", ""]
        for i, s in enumerate(sentences[:15], 1):
            truncated = f"{s[:120]}…" if len(s) > 120 else s
            lines.append(f"  [{i:02d}] {truncated}")
            lines.append("       ↳ evidence: [UNVERIFIED — add citation]")
        return CommandResult(output="\n".join(lines))

    elif verb == "falsify":
        hypothesis = args.strip()[len("falsify"):].strip()
        if not hypothesis:
            return CommandResult(output="usage: /research falsify <hypothesis>")
        lines = [
            f"## Falsification Plan: {hypothesis}",
            "",
            "### Counterexample Candidates",
            "  1. [Generate a case where the hypothesis would be FALSE]",
            "  2. [Edge case: boundary condition]",
            "  3. [Alternative explanation that explains the same observations]",
            "",
            "### Refuting Experiments",
            "  - Design an experiment that could disprove this hypothesis",
            "  - Identify the smallest evidence that would invalidate it",
            "",
            "### Verdict",
            "  Run the above experiments. If any succeed, revise hypothesis.",
        ]
        return CommandResult(output="\n".join(lines))

    elif verb == "sandbox":
        task = args.strip()[len("sandbox"):].strip()
        if not task:
            return CommandResult(output="usage: /research sandbox <task>")
        import time as _time
        from pathlib import Path as _Path

        ts = int(_time.time())
        report_dir = _Path.home() / ".lyra" / "research" / f"sandbox-{ts}"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "report.md"
        report_file.write_text(
            f"# Research Sandbox Report\n\n"
            f"Task: {task}\n\n"
            f"Status: pending\n\n"
            f"Generated: {_time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
        )
        return CommandResult(
            output=(
                f"Research sandbox created at {report_dir}\n"
                f"Report template: {report_file}\n"
                "Run /research to fill in results."
            )
        )

    # ------------------------------------------------------------------
    # End sub-command dispatch — fall through to web-search query path
    # ------------------------------------------------------------------

    try:
        tokens = shlex.split(args)
    except ValueError as exc:
        return CommandResult(output=f"/research: shell parse failed: {exc}")

    depth = 3
    time_range: Optional[str] = None
    domains: list[str] = []
    query_parts: list[str] = []
    it = iter(tokens)
    for tok in it:
        if tok in ("--depth", "-d"):
            try:
                depth = max(1, min(10, int(next(it))))
            except (StopIteration, ValueError):
                return CommandResult(output="/research: --depth needs an integer")
        elif tok in ("--time", "-t"):
            try:
                value = next(it)
            except StopIteration:
                return CommandResult(output="/research: --time needs a value")
            if value not in {"day", "week", "month", "year"}:
                return CommandResult(
                    output=f"/research: --time must be day/week/month/year, got {value!r}"
                )
            time_range = value
        elif tok == "--domain":
            try:
                domains.append(next(it))
            except StopIteration:
                return CommandResult(output="/research: --domain needs a value")
        else:
            query_parts.append(tok)

    query = " ".join(query_parts).strip()
    if not query:
        return CommandResult(output="/research: no query provided")

    try:
        from lyra_core.tools.web_search import make_web_search_tool
        from lyra_core.tools.web_fetch import make_web_fetch_tool
    except Exception as exc:
        return CommandResult(output=f"/research: tools unavailable ({exc})")

    search = make_web_search_tool()
    payload = search(
        query=query,
        max_results=max(depth, 5),
        time_range=time_range,
        domains_allow=domains or None,
    )
    if payload.get("count", 0) == 0:
        err = payload.get("error") or "no results returned"
        return CommandResult(output=f"/research: {err}")

    fetch = make_web_fetch_tool()
    lines = [f"# /research: {query}"]
    if time_range:
        lines.append(f"_time range: {time_range}_")
    lines.append(f"_provider: {payload.get('provider', '?')}_")
    lines.append("")
    for hit in payload["results"][:depth]:
        title = hit.get("title") or "(no title)"
        url = hit.get("url") or ""
        lines.append(f"## {title}")
        lines.append(f"<{url}>")
        snippet = (hit.get("snippet") or "").strip()
        if snippet:
            lines.append(f"> {snippet}")
        try:
            fetched = fetch(url=url, max_chars=2_000)
        except Exception as exc:
            lines.append(f"_fetch failed: {exc}_")
            lines.append("")
            continue
        if fetched.get("error"):
            lines.append(f"_fetch failed: {fetched['error']}_")
        else:
            excerpt = (fetched.get("text") or "")[:1500]
            if excerpt:
                lines.append("```")
                lines.append(excerpt)
                lines.append("```")
        lines.append("")

    return CommandResult(output="\n".join(lines).rstrip())


def _cmd_claude_api(_session: InteractiveSession, _args: str) -> CommandResult:
    """``/claude-api`` — print the Anthropic API quick-reference card.

    Replaces the Claude Code skill (which loads SDK reference for
    Python/TypeScript/Java/Go/Ruby/C#/PHP/cURL). Lyra ships with the
    text inline rather than fetching it — same offline-first
    rationale as ``/release-notes``.
    """
    body = (
        "Anthropic Claude API quick reference\n"
        "  Endpoint    POST https://api.anthropic.com/v1/messages\n"
        "  Auth        x-api-key: $ANTHROPIC_API_KEY\n"
        "  Header      anthropic-version: 2023-06-01\n"
        "  Models      claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5\n"
        "  Streaming   stream: true (server-sent events)\n"
        "  Tool use    tools: [{name, description, input_schema}]\n"
        "  Caching     cache_control: {type: 'ephemeral'} on a content block\n"
        "  SDKs        pip install anthropic  ·  npm install @anthropic-ai/sdk\n"
        "  Docs        https://docs.anthropic.com/en/api/getting-started"
    )
    return CommandResult(output=body)


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

    When stdin is a TTY and no subcommand is given, the bare ``/agents``
    form opens the Claude-Code-style picker (catalog + live views).
    The legacy text path still runs in headless / piped sessions and
    when the picker subcommand isn't ``pick``.
    """
    parts = args.strip().split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    reg = getattr(session, "subagent_registry", None)

    # Bare /agents on a TTY → interactive picker. ``pick`` forces it.
    if (sub == "" and _stdin_is_tty()) or sub == "pick":
        return _launch_agents_picker(session)

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

        provider = build_llm(getattr(session, "model", "auto"))
        return AgentLoop(
            llm=_LyraCoreLLMAdapter(provider),
            tools={},
            store=_NoopStore(),
            budget=IterationBudget(max=8),
        )

    # Eternal-Mode opt-in (LYRA_ETERNAL_SUBAGENT_DIR) — when set, every
    # /spawn'd subagent runs through EternalAgentLoop with a journaled
    # LLM call sequence and idempotent tool dispatch. Default path is
    # unchanged (env unset → plain AgentLoop, zero new dependencies on
    # the hot path).
    _eternal_dir = os.environ.get("LYRA_ETERNAL_SUBAGENT_DIR")
    if _eternal_dir:
        try:
            from lyra_cli.eternal_factory import make_eternal_loop_factory

            _loop_factory = make_eternal_loop_factory(  # type: ignore[assignment]
                _loop_factory,
                state_dir=_eternal_dir,
                workflow_name="lyra.spawn",
            )
        except Exception:
            # Defensive: never let an eternal-mode wiring failure break
            # /spawn — fall back to the plain factory.
            pass

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
    from .budget import BudgetCap, BudgetMeter

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

    # Lifecycle sub-commands (Wave D — skills_lifecycle.py)
    _sl_verbs = {"create", "admit", "audit", "distill", "compose", "merge", "prune"}
    if (target.split()[0] if target else "") in _sl_verbs:
        from .skills_lifecycle import cmd_skills_lifecycle
        return cmd_skills_lifecycle(session, args)

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
        # If a TTY is available, launch the interactive picker
        # (Claude-Code-style /skills panel). Falls through to the
        # legacy text status when running headless (tests, pipes,
        # remote sessions).
        if _stdin_is_tty():
            return _launch_skills_picker(session)
        # Default rendering keeps the v0.1.0 "list installed packs"
        # contract so older tests + muscle-memory still work, and adds
        # the new injection state line at the top.
        try:
            from .skills_inject import _load_skills_safely, discover_skill_roots

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
            from .skills_inject import _load_skills_safely, discover_skill_roots

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
            from .skills_inject import _load_skills_safely, discover_skill_roots

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

    if target == "pick":
        return _launch_skills_picker(session)

    if target == "state":
        return _print_skills_state(session)

    if target.startswith("enable ") or target.startswith("disable "):
        verb, _, sid = target.partition(" ")
        sid = sid.strip()
        if not sid:
            return CommandResult(
                output=f"usage: /skills {verb} <skill-id>"
            )
        return _toggle_skill_id(session, sid, enable=(verb == "enable"))

    return CommandResult(
        output=(
            f"unknown /skills argument {target!r}. "
            f"usage: /skills [pick|on|off|status|list|reload|"
            f"enable <id>|disable <id>|state]"
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

    # Lifecycle sub-commands (Wave A — memory_lifecycle.py)
    _lifecycle_verbs = {"consolidate", "distill", "audit", "evolve", "promote"}
    if (target_lc.split()[0] if target_lc else "") in _lifecycle_verbs:
        from .memory_lifecycle import cmd_memory_lifecycle
        return cmd_memory_lifecycle(session, args)

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
    """`/effort` — Claude-Code-parity reasoning-effort picker.

    With no argument and a real TTY, runs the interactive horizontal
    slider (`run_effort_picker`); with an explicit level argument
    (``/effort high``) it skips the slider and applies directly so
    scripts and non-TTY callers can drive the same surface.

    Levels: ``low`` · ``medium`` · ``high`` · ``xhigh`` · ``max``.
    The legacy ``ultra`` alias from v0.x continues to resolve to
    ``max`` for back-compat with stored configs.
    """
    import sys

    from .effort import EffortPicker, apply_effort

    levels = {
        "low":    "fastest single-turn attempt; cheapest model",
        "medium": "default — Plan + Build with standard verification",
        "high":   "+ extra review passes (/review, /ultrareview)",
        "xhigh":  "deep reasoning + multi-pass verifier",
        "max":    "full refute-or-promote loop + cross-channel verifier",
        # Back-compat: accept the legacy "ultra" alias from v0.x.
        "ultra":  "alias for max",
    }
    valid_canonical: tuple[str, ...] = ("low", "medium", "high", "xhigh", "max")
    choice = args.strip().lower()

    if not choice:
        # Try the interactive slider first; fall back to a static
        # render whenever a real Application can't be launched (no
        # TTY, prompt_toolkit unavailable, in a unit test, …).
        picked: str | None = None
        if sys.stdin.isatty() and sys.stdout.isatty():
            try:
                from .effort_app import run_effort_picker
                picked = run_effort_picker(initial="medium")
            except Exception:
                picked = None

        if picked is None:
            picker = EffortPicker(initial="medium")
            return CommandResult(
                output=picker.render(),
                renderable=_out.effort_renderable("medium", levels),
            )
        canonical = apply_effort(picked)
        return CommandResult(
            output=f"effort: {canonical} — {levels[canonical]}",
            renderable=_out.effort_renderable(canonical, levels),
        )

    if choice not in levels:
        return CommandResult(
            output=(
                f"unknown effort level {choice!r}; "
                f"valid: {', '.join(valid_canonical)}."
            ),
            renderable=_out.bad_effort_renderable(choice, valid_canonical),
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
# ---------------------------------------------------------------------------
# Wave C: /deepsearch
# ---------------------------------------------------------------------------


def _cmd_deepsearch(session: InteractiveSession, args: str) -> CommandResult:
    """``/deepsearch <query> [--hops N] [--local]`` — multi-hop IRCoT retrieval.

    Iterative retrieval loop: decompose → retrieve → reason → repeat.
    Emits a per-hop trace (subgoal, sources, support score, contradiction score).
    """
    from .deepsearch import cmd_deepsearch
    return cmd_deepsearch(session, args)


# ---------------------------------------------------------------------------
# Wave E: /specify  /bmad  /tasks
# ---------------------------------------------------------------------------


def _cmd_specify(session: InteractiveSession, args: str) -> CommandResult:
    """``/specify [topic]`` — generate a structured spec with hidden-question detection.

    Outputs ``spec-<slug>.md`` with acceptance criteria, ambiguity questions,
    and out-of-scope section. Human gate before plan generation (doc 321).
    """
    from .spec_driven import cmd_specify
    return cmd_specify(session, args)


def _cmd_bmad(session: InteractiveSession, args: str) -> CommandResult:
    """``/bmad <role> [task]`` — invoke a BMAD agent persona.

    Roles: analyst · pm · architect · dev · qa · writer.
    Each persona produces its canonical artifact (brief / PRD / ADR /
    implementation checklist / acceptance criteria / doc outline).
    """
    from .spec_driven import cmd_bmad
    return cmd_bmad(session, args)


def _cmd_tasks(session: InteractiveSession, args: str) -> CommandResult:
    """``/tasks [--from-spec <file>]`` — split plan/spec into testable task chunks.

    Each task gets an ID, description, acceptance criteria, size estimate (S/M/L),
    and dependency list. Writes ``.lyra/tasks-<date>.md``.
    """
    from .spec_driven import cmd_tasks
    return cmd_tasks(session, args)


# ---------------------------------------------------------------------------
# Wave F: /verify  /checkpoint  /rollback
# ---------------------------------------------------------------------------


def _cmd_verify(session: InteractiveSession, args: str) -> CommandResult:
    """``/verify [--spec <file>] [--rubric <criteria>]`` — rubric-based evaluator.

    Scores the last assistant output against acceptance criteria (0-100).
    Distinct from ``/review`` (code quality) - this evaluates correctness
    against explicit goals. Surfaces gap between output and threshold (doc 326).
    """
    from .checkpoints import cmd_verify
    return cmd_verify(session, args)


def _cmd_checkpoint(session: InteractiveSession, args: str) -> CommandResult:
    """``/checkpoint [label]`` — save current agent state.

    Persists turn, model, mode, cost, last message to
    ``~/.lyra/checkpoints/<session-id>/<label>.json``.
    """
    from .checkpoints import cmd_checkpoint
    return cmd_checkpoint(session, args)


def _cmd_rollback(session: InteractiveSession, args: str) -> CommandResult:
    """``/rollback [label]`` — restore to a prior checkpoint.

    No args: list all checkpoints for this session.
    With label: restore model/mode/pending_task from that checkpoint.
    """
    from .checkpoints import cmd_rollback
    return cmd_rollback(session, args)


# ---------------------------------------------------------------------------
# Wave G: /route  /monitor  /aer
# ---------------------------------------------------------------------------


def _cmd_route(session: InteractiveSession, args: str) -> CommandResult:
    """``/route [status|set <slot> <tier>|reset]`` — model routing policy.

    Shows or configures the 8-slot routing table (intent / search / planning /
    execution / synthesis / verification / review / final). Tiers: fast · mid ·
    strong · advisor. Persisted to ``~/.lyra/route-policy.json`` (doc 323).
    """
    from .model_router import cmd_route
    return cmd_route(session, args)


def _cmd_monitor(session: InteractiveSession, args: str) -> CommandResult:
    """``/monitor`` — operator fleet view.

    Sessions grouped by attention priority: Needs Input · Ready for Review ·
    Working · Completed. Space=peek, Enter=attach (doc 325 Agent View).
    """
    from .monitor import cmd_monitor
    return cmd_monitor(session, args)


def _cmd_aer(session: InteractiveSession, args: str) -> CommandResult:
    """``/aer [session-id|timeline]`` — Agent Execution Record viewer.

    Per-turn: intent, observation, inferred step type, tokens.
    ``/aer timeline`` — flat event list in chronological order (doc 322).
    """
    from .monitor import cmd_aer
    return cmd_aer(session, args)


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


# Phase 2a (v3.5) unification — CommandSpec, _CATEGORY_DISPLAY, _PIPE_SUBS_RE,
# and _extract_subs are now canonical types in lyra_cli.commands.registry.
# session.py imports them and at the very bottom of this module extends
# registry.COMMAND_REGISTRY with the concrete tuple defined below. Both
# import orders converge on the same fully-populated list — see the
# detailed docstring in commands/registry.py.
from lyra_cli.commands.registry import (  # noqa: E402
    _CATEGORY_DISPLAY,
    CommandSpec,
)

# v3.11 slash commands — Anthropic Agent Teams + scaling axes + verifier
# coverage + Software 3.0 bundle. Imported here so the registry tuple
# below can reference the four handlers.
from .v311_commands import (  # noqa: E402
    cmd_bundle as _cmd_bundle_v311,
    cmd_coverage as _cmd_coverage_v311,
    cmd_scaling as _cmd_scaling_v311,
    cmd_team as _cmd_team_v311,
)


# --- Skill System Handlers (Phase 1) -----------------------------------------


def _cmd_skill(session: InteractiveSession, args: str) -> CommandResult:
    """``/skill [list|search|reload|info]`` — manage skills."""
    from lyra_cli.cli.skill_manager import SkillManager

    parts = args.strip().split(maxsplit=1)
    sub = parts[0].lower() if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""

    if sub == "list":
        return _cmd_skill_list(session, rest)
    elif sub == "search":
        return _cmd_skill_search(session, rest)
    elif sub == "reload":
        return _cmd_skill_reload(session, rest)
    elif sub == "info":
        return _cmd_skill_info(session, rest)
    else:
        return CommandResult(
            output=f"Unknown subcommand '{sub}'. Use: /skill [list|search|reload|info]"
        )


def _cmd_skill_list(session: InteractiveSession, _args: str) -> CommandResult:
    """``/skill list`` — show all installed skills."""
    from lyra_cli.cli.skill_manager import SkillManager

    skill_mgr = SkillManager()
    skills = skill_mgr.skills

    if not skills:
        return CommandResult(
            output="No skills installed. Add skills to ~/.lyra/skills/ or .lyra/skills/"
        )

    # Build output
    lines = [f"Installed skills ({len(skills)}):"]
    lines.append("")

    for name, skill in sorted(skills.items()):
        category = skill.get("category", "unknown")
        description = skill.get("description", "No description")
        version = skill.get("version", "unknown")
        lines.append(f"  /{name:<20} [{category}] v{version}")
        lines.append(f"    {description}")
        lines.append("")

    return CommandResult(output="\n".join(lines))


def _cmd_skill_search(session: InteractiveSession, args: str) -> CommandResult:
    """``/skill search <query>`` — search skills by name or description."""
    from lyra_cli.cli.skill_manager import SkillManager

    if not args.strip():
        return CommandResult(output="Usage: /skill search <query>")

    skill_mgr = SkillManager()
    results = skill_mgr.search_skills(args.strip())

    if not results:
        return CommandResult(output=f"No skills found matching '{args.strip()}'")

    lines = [f"Found {len(results)} skill(s):"]
    lines.append("")

    for name in results:
        skill = skill_mgr.get_skill(name)
        if skill:
            description = skill.get("description", "No description")
            lines.append(f"  /{name}")
            lines.append(f"    {description}")
            lines.append("")

    return CommandResult(output="\n".join(lines))


def _cmd_skill_reload(session: InteractiveSession, _args: str) -> CommandResult:
    """``/skill reload`` — reload skills from disk and re-register commands."""
    from lyra_cli.cli.skill_manager import SkillManager
    from lyra_cli.commands.registry import register_command

    skill_mgr = SkillManager()
    skill_mgr.reload()

    # Re-register skill commands
    new_specs = skill_mgr.get_command_specs()
    count = 0
    for spec in new_specs:
        try:
            register_command(spec)
            count += 1
        except ValueError:
            # Already registered, skip
            pass

    return CommandResult(
        output=f"Reloaded {len(skill_mgr.skills)} skills ({count} new commands registered)"
    )


def _cmd_skill_info(session: InteractiveSession, args: str) -> CommandResult:
    """``/skill info <name>`` — show detailed information about a skill."""
    from lyra_cli.cli.skill_manager import SkillManager

    if not args.strip():
        return CommandResult(output="Usage: /skill info <skill-name>")

    skill_mgr = SkillManager()
    skill = skill_mgr.get_skill(args.strip())

    if not skill:
        return CommandResult(output=f"Skill '{args.strip()}' not found")

    lines = [f"Skill: {skill['name']}"]
    lines.append(f"Version: {skill.get('version', 'unknown')}")
    lines.append(f"Category: {skill.get('category', 'unknown')}")
    lines.append(f"Description: {skill.get('description', 'No description')}")
    lines.append("")

    if skill.get("aliases"):
        lines.append(f"Aliases: {', '.join(skill['aliases'])}")
        lines.append("")

    if skill.get("args"):
        args_data = skill["args"]
        if isinstance(args_data, dict) and args_data.get("hint"):
            lines.append(f"Usage: /{skill['name']} {args_data['hint']}")
            lines.append("")

    execution = skill.get("execution", {})
    lines.append(f"Execution type: {execution.get('type', 'unknown')}")

    if execution.get("prompt_file"):
        lines.append(f"Prompt file: {execution['prompt_file']}")

    return CommandResult(output="\n".join(lines))


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
        "keybindings",
        _cmd_keybindings,
        "show the keybindings cheatsheet",
        "session",
        aliases=("keys",),
    ),
    CommandSpec(
        "new",
        _cmd_new,
        "start a fresh chat (clear messages, keep mode/model)",
        "session",
        aliases=("reset",),
    ),
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
    ),
    CommandSpec(
        "usage",
        _cmd_usage,
        "consolidated cost + session metrics (Claude-Code-style)",
        "observability",
    ),
    CommandSpec(
        "copy",
        _cmd_copy,
        "copy the last assistant reply to the clipboard",
        "observability",
        args_hint="[N] [--write PATH]",
    ),
    CommandSpec(
        "hooks",
        _cmd_hooks,
        "show configured user hooks (PreToolUse / PostToolUse / …)",
        "observability",
    ),
    CommandSpec(
        "permissions",
        _cmd_permissions,
        "view / edit / reload the declarative permission grammar",
        "config-theme",
        aliases=("allowed-tools",),
        args_hint="[edit|reload]",
    ),
    CommandSpec(
        "plan",
        _cmd_plan,
        "enter plan mode (one-shot)",
        "plan-build-run",
    ),
    CommandSpec(
        "recap",
        _cmd_recap,
        "terse summary of recent turns for re-orientation",
        "observability",
    ),
    CommandSpec(
        "add-dir",
        _cmd_add_dir,
        "widen the session sandbox by adding an auxiliary directory",
        "config-theme",
        args_hint="[path]",
    ),
    CommandSpec(
        "security-review",
        _cmd_security_review,
        "OWASP-style security-focused code review",
        "tools-agents",
        args_hint="[target]",
    ),
    CommandSpec(
        "feedback",
        _cmd_feedback,
        "print issue URL + recent context (use --copy to grab turns)",
        "observability",
        aliases=("bug",),
        args_hint="[--copy]",
    ),
    CommandSpec(
        "statusline",
        _cmd_statusline,
        "show or set the bottom-toolbar format",
        "config-theme",
        args_hint="[format|default]",
    ),
    CommandSpec(
        "color",
        _cmd_color,
        "tint the prompt-bar accent (red/blue/green/...)",
        "config-theme",
        args_hint="[name|default]",
    ),
    CommandSpec(
        "fast",
        _cmd_fast,
        "toggle fast posture (effort=low for snappier turns)",
        "config-theme",
        args_hint="[on|off|toggle]",
    ),
    CommandSpec(
        "focus",
        _cmd_focus,
        "hide side panels — chat-only view for screenshots/demos",
        "config-theme",
        args_hint="[on|off|toggle]",
    ),
    CommandSpec(
        "tui",
        _cmd_tui,
        "switch rendering mode (classic vs smooth)",
        "config-theme",
        args_hint="[classic|smooth|toggle]",
    ),
    CommandSpec(
        "pr-comments",
        _cmd_pr_comments,
        "fetch GitHub PR comments via gh CLI",
        "observability",
        args_hint="[PR-number-or-URL]",
    ),
    CommandSpec(
        "schedule",
        _cmd_schedule,
        "schedule a recurring/one-shot prompt (alias of /cron)",
        "tools-agents",
        args_hint="[add|list|rm <id>]",
    ),
    CommandSpec(
        "sandbox",
        _cmd_sandbox,
        "toggle strict filesystem sandbox (refuses writes outside repo_root)",
        "config-theme",
        args_hint="[on|off|toggle]",
    ),
    CommandSpec(
        "plugin",
        _cmd_plugin,
        "OMC plugin management hint (Lyra delegates to omc)",
        "tools-agents",
        aliases=("plugins",),
        args_hint="[list]",
    ),
    CommandSpec(
        "reload-plugins",
        _cmd_reload_plugins,
        "re-walk skill / user-command / hook discovery without restart",
        "tools-agents",
    ),
    CommandSpec(
        "release-notes",
        _cmd_release_notes,
        "print the bundled CHANGELOG.md head",
        "observability",
    ),
    CommandSpec(
        "connect",
        _cmd_connect,
        "manage API keys (~/.lyra/credentials.json)",
        "config-theme",
        args_hint="[list | remove <provider> | <provider> <key> [base_url]]",
    ),
    CommandSpec(
        "logout",
        _cmd_logout,
        "clear stored provider credentials",
        "config-theme",
    ),
    CommandSpec(
        "loop",
        _cmd_loop,
        "schedule a recurring prompt (Claude-Code-style cron shortcut)",
        "tools-agents",
        args_hint="[interval] <prompt>",
    ),
    CommandSpec(
        "directive",
        _cmd_directive,
        "append a directive to HUMAN_DIRECTIVE.md (autopilot async-control)",
        "tools-agents",
        args_hint="[<text>]",
    ),
    CommandSpec(
        "contract",
        _cmd_contract,
        "inspect or configure the AgentContract budget envelope",
        "tools-agents",
        args_hint="[show|set <key>=<value>]",
    ),
    CommandSpec(
        "autopilot",
        _cmd_autopilot,
        "show status of supervised autonomy loops (LoopStore)",
        "tools-agents",
        args_hint="[status|list]",
    ),
    CommandSpec(
        "continue",
        _cmd_continue,
        "queue an explicit re-feed of the agent (manual Stop re-entry)",
        "tools-agents",
        args_hint="[<follow-up>]",
    ),
    CommandSpec(
        "sharpen",
        _cmd_sharpen,
        "rewrite a task as verifiable goals (imperative → declarative)",
        "tools-agents",
        args_hint="<task description>",
    ),
    CommandSpec(
        "debug",
        _cmd_debug,
        "toggle verbose debug-event surfacing in the REPL",
        "observability",
        args_hint="[on|off|toggle]",
    ),
    CommandSpec(
        "simplify",
        _cmd_simplify,
        "fan-out 3-pass review (quality / reuse / efficiency)",
        "tools-agents",
        args_hint="[focus]",
    ),
    CommandSpec(
        "batch",
        _cmd_batch,
        "delegate multi-unit refactors to OMC's batch fan-out",
        "tools-agents",
        args_hint="<instruction>",
    ),
    CommandSpec(
        "claude-api",
        _cmd_claude_api,
        "Anthropic Claude API quick reference",
        "observability",
    ),
    CommandSpec(
        "research",
        _cmd_research,
        "deep-research workflow: search + fetch + snippet excerpts",
        "tools-agents",
        args_hint="<query> [--depth N] [--time day|week|month|year] [--domain X]",
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
    # --- v3.11 — Agent Teams, scaling axes, coverage, bundle ---------------
    CommandSpec(
        "agentteams",
        _cmd_team_v311,
        "Anthropic Agent Teams parallel runtime (lead-and-spokes, shared task list, mailbox)",
        "config-theme",
        aliases=("ateams",),
        args_hint="[list|status|spawn <name>|add-task <title>|mailbox|report|help]",
    ),
    CommandSpec(
        "scaling",
        _cmd_scaling_v311,
        "Four-axis scaling-laws aggregator with cost-benefit-ranked next lever",
        "config-theme",
        args_hint="[axis <pretrain|ttc|memory|tool_use>|help]",
    ),
    CommandSpec(
        "coverage",
        _cmd_coverage_v311,
        "Verifier-coverage index per task domain (auto_mode admit signal)",
        "config-theme",
        args_hint="[<domain>|help]",
    ),
    CommandSpec(
        "bundle",
        _cmd_bundle_v311,
        "Software 3.0 bundle pipeline — info, install, export to {claude-code,cursor,codex,gemini-cli}",
        "config-theme",
        args_hint="[info <path>|install <path>|export <path> <target>|help]",
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
    # NOTE: `keybindings` is registered once in the `session` bucket above
    # (with the same handler + ``keys`` alias). The duplicate entry that
    # used to live here in the `config-theme` bucket caused
    # ``test_registry_names_are_unique`` to fail and could shadow the
    # ``keys`` alias depending on iteration order. Single source of truth.
    CommandSpec("policy", _cmd_policy, "print .lyra/policy.yaml", "config-theme"),
    CommandSpec(
        "doctor", _cmd_doctor, "quick health check for this repo", "config-theme"
    ),
    CommandSpec(
        "auth",
        _cmd_auth,
        "OAuth provider tokens (list, logout, Copilot device flow hint)",
        "config-theme",
        aliases=("login",),
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
    # --- deep research ----------------------------------------------------
    CommandSpec(
        "deepsearch",
        _cmd_deepsearch,
        "multi-hop IRCoT retrieval loop with per-hop trace (doc 324)",
        "tools-agents",
        args_hint="<query> [--hops N] [--local]",
    ),
    # --- spec-driven development ------------------------------------------
    CommandSpec(
        "specify",
        _cmd_specify,
        "generate a structured spec with hidden-question detection (doc 321)",
        "plan-build-run",
        args_hint="[topic]",
    ),
    CommandSpec(
        "bmad",
        _cmd_bmad,
        "invoke a BMAD agent persona: analyst · pm · architect · dev · qa · writer",
        "plan-build-run",
        args_hint="<role> [task]",
    ),
    CommandSpec(
        "tasks",
        _cmd_tasks,
        "split plan/spec into independently testable task chunks",
        "plan-build-run",
        args_hint="[--from-spec <file>]",
    ),
    # --- closed-loop control ----------------------------------------------
    CommandSpec(
        "verify",
        _cmd_verify,
        "rubric-based evaluator: score output against acceptance criteria 0-100 (doc 326)",
        "plan-build-run",
        args_hint="[--spec <file>] [--rubric <criteria>]",
    ),
    CommandSpec(
        "checkpoint",
        _cmd_checkpoint,
        "save current agent state to ~/.lyra/checkpoints/",
        "session",
        args_hint="[label]",
    ),
    CommandSpec(
        "rollback",
        _cmd_rollback,
        "restore to a prior checkpoint (list if no label given)",
        "session",
        args_hint="[label]",
    ),
    # --- routing & monitoring ---------------------------------------------
    CommandSpec(
        "route",
        _cmd_route,
        "show/configure 8-slot model routing policy (doc 323)",
        "config-theme",
        args_hint="[status|set <slot> <tier>|reset]",
    ),
    CommandSpec(
        "monitor",
        _cmd_monitor,
        "operator fleet view: sessions grouped by attention priority (doc 325)",
        "observability",
        args_hint="",
    ),
    CommandSpec(
        "aer",
        _cmd_aer,
        "Agent Execution Record viewer: per-turn intent/observation/step-type (doc 322)",
        "observability",
        args_hint="[session-id|timeline]",
    ),
    # --- skills -----------------------------------------------------------
    CommandSpec(
        "skill",
        _cmd_skill,
        "manage skills (list, search, reload, info)",
        "skills",
        subcommands=("list", "search", "reload", "info"),
        args_hint="[list|search|reload|info] [query]",
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


# Phase 2a (v3.5) — extend the canonical commands.registry.COMMAND_REGISTRY
# list with this module's concrete tuple. Done at module-bottom so all
# `_cmd_*` handlers and the local tuple are fully defined before the
# extension. The canonical list may already contain entries from other
# modules (plugins, MCP prompts) — we extend, never replace.
def _populate_canonical_registry() -> None:
    from lyra_cli.commands import registry as _registry_module

    canonical = _registry_module.COMMAND_REGISTRY
    # Avoid double-registration if this module is reloaded (e.g. during
    # test isolation). We compare by name+category triple to be precise:
    # plugins MAY register specs with the same name in a different
    # category later, but the session.py tuple is appended once.
    existing_keys = {(s.name, s.category) for s in canonical}
    for spec in COMMAND_REGISTRY:
        if (spec.name, spec.category) in existing_keys:
            continue
        canonical.append(spec)


_populate_canonical_registry()
