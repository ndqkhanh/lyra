"""Canonical slash command registry (Phase 2a unification — v3.5).

Before v3.5 there were two parallel slash command registries: this module
held a stub list with `_noop_handler` placeholders, while the real specs
and `_cmd_*` handlers lived in `lyra_cli.interactive.session`. The unified
test (`tests/test_command_registry_unified.py`) was asserting against the
stub, so production behaviour was effectively untested for shape drift.

This module is now the single source of truth for:

- The :class:`CommandSpec` dataclass shape (frozen).
- The :data:`COMMAND_REGISTRY` list, populated at import time by
  ``lyra_cli.interactive.session`` extending it with its concrete specs
  (which reference live `_cmd_*` handlers tied to `InteractiveSession`).
- The :class:`SlashHandler` type alias.
- The :data:`_CATEGORY_DISPLAY` lookup, the :data:`_PIPE_SUBS_RE` pattern,
  and the :func:`_extract_subs` helper used to auto-derive ``subcommands``
  from ``args_hint`` like ``"<plan|agent|debug|ask>"``.
- :func:`resolve_command`, :func:`register_command`, and
  :func:`commands_by_category` — the user-facing dispatch surface.

Load-order safety: this module defines all types BEFORE the late import
of ``lyra_cli.interactive.session`` at the bottom. session.py imports
``CommandSpec`` etc. from here at its own module top, then at its own
module bottom extends ``COMMAND_REGISTRY`` with its concrete tuple. Both
import orders converge on the same fully-populated list.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# A SlashHandler takes (session, args_str) and returns a CommandResult.
# We avoid importing the concrete InteractiveSession + CommandResult here
# to keep this module a leaf: it's allowed to be imported by anything,
# and must not pull in the heavy interactive session module at type-check
# time. Use loose `Callable[..., Any]` and let session.py refine.
SlashHandler = Callable[..., Any]

_CATEGORY_DISPLAY: dict[str, str] = {
    "session": "session",
    "plan-build-run": "plan · build · run",
    "tools-agents": "tools · agents",
    "observability": "observability",
    "config-theme": "config · theme",
    "collaboration": "collaboration",
    "meta": "meta",
    # Phase 4-6 additions (registered by extension modules):
    "skill": "skills",
    "mcp": "mcp",
    "plugin": "plugins",
    "tdd": "tdd",
    "hud": "hud",
}

_PIPE_SUBS_RE = re.compile(r"[a-z][a-z\-]*(?:\|[a-z][a-z\-]*)+")


def _extract_subs(args_hint: str) -> tuple[str, ...]:
    """Pull a ``a|b|c`` style choice list out of an args hint.

    ``"[plan|agent|debug|ask]"`` → ``("plan", "agent", "debug", "ask")``.
    ``"[name]"`` (no pipes) → ``()``.
    Used by :class:`CommandSpec.__post_init__` to auto-fill ``subcommands``
    so the completer offers fuzzy-matching subcommands without each spec
    having to spell them out twice.
    """
    if not args_hint:
        return ()
    match = _PIPE_SUBS_RE.search(args_hint)
    return tuple(match.group(0).split("|")) if match else ()


@dataclass(frozen=True)
class CommandResult:
    """Lightweight outcome returned by registry helpers.

    The interactive session has its own richer ``CommandResult`` (with
    ``output``, ``renderable``, ``should_exit``, ``new_mode`` …) for
    actual REPL flow. This one is only used by registry-level utilities
    that need a structured return without dragging in the session module.
    """

    ok: bool = True
    message: str = ""
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CommandSpec:
    """One slash command — declared once, consumed everywhere.

    ``frozen=True`` because the registry is read-only after import; if
    you need to mutate behaviour at runtime, build a new spec rather
    than poke this one. ``__post_init__`` is the single exception: it
    back-fills ``subcommands`` from ``args_hint`` when the explicit
    field is empty, using ``object.__setattr__`` to honour the frozen
    contract.

    Fields:
      - ``name``: canonical command name (no leading ``/``).
      - ``handler``: callable invoked by the dispatcher.
      - ``description``: one-line summary rendered by ``/help`` and the
        completer's meta column.
      - ``category``: bucket name (see :data:`_CATEGORY_DISPLAY`).
      - ``aliases``: alternative names; each must be unique across the
        whole registry.
      - ``args_hint``: free-form usage string for ``/help`` and the
        completer (e.g. ``"[--verbose]"``).
      - ``subcommands``: explicit subcommand stems for the completer;
        auto-derived from ``args_hint`` when empty.
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


# Populated at import time by ``lyra_cli.interactive.session`` extending
# this list with its concrete specs. Stays empty if session.py never
# loads (e.g. unit tests that exercise the registry helpers in isolation
# can populate it themselves via :func:`register_command`).
COMMAND_REGISTRY: list[CommandSpec] = []


def _index() -> dict[str, CommandSpec]:
    """Build a {name|alias → spec} lookup over the live registry.

    Recomputed per call because the registry is populated lazily by
    session.py and may be extended by plugins at any later point. The
    cost is a small dict comprehension — well under 1 ms for a registry
    with ~100 specs.
    """
    idx: dict[str, CommandSpec] = {}
    for spec in COMMAND_REGISTRY:
        idx[spec.name] = spec
        for alias in spec.aliases:
            idx[alias] = spec
    return idx


def resolve_command(line: str) -> tuple[CommandSpec | None, str]:
    """Parse a REPL line and return ``(spec_or_None, args_str)``.

    Accepts with or without the leading ``/``. Args are preserved
    verbatim (including whitespace) so handlers that want flag parsing
    can split further.

    Examples
    --------
    >>> resolve_command("/status")           # → (status_spec, "")
    >>> resolve_command("/mode plan")        # → (mode_spec,   "plan")
    >>> resolve_command("/q")                # → (exit_spec,   "")  via alias
    >>> resolve_command("/no-such-command")  # → (None,        "")
    """
    if not line:
        return None, ""
    raw = line.lstrip()
    if raw.startswith("/"):
        raw = raw[1:]
    if not raw:
        return None, ""
    name, _, rest = raw.partition(" ")
    spec = _index().get(name.strip())
    return spec, rest.strip()


def register_command(spec: CommandSpec) -> None:
    """Append a spec to :data:`COMMAND_REGISTRY` with collision guard.

    Used both internally (session.py extends with its tuple at module
    load) and by plugins (e.g. each MCP prompt becomes one
    ``CommandSpec`` with category ``"mcp"``).

    Raises
    ------
    ValueError
        If ``spec.name`` or any of its ``aliases`` collide with names
        or aliases already present in the registry.
    """
    idx = _index()
    if spec.name in idx or any(a in idx for a in spec.aliases):
        raise ValueError(
            f"command name/alias collision for {spec.name!r} (aliases={spec.aliases})"
        )
    COMMAND_REGISTRY.append(spec)


def commands_by_category() -> dict[str, list[CommandSpec]]:
    """Group specs by category in registry order — used by ``/help``."""
    grouped: dict[str, list[CommandSpec]] = {}
    for spec in COMMAND_REGISTRY:
        grouped.setdefault(spec.category, []).append(spec)
    return grouped


__all__ = [
    "COMMAND_REGISTRY",
    "_CATEGORY_DISPLAY",
    "_PIPE_SUBS_RE",
    "CommandResult",
    "CommandSpec",
    "SlashHandler",
    "_extract_subs",
    "commands_by_category",
    "register_command",
    "resolve_command",
]


# Late import: pull in session.py to trigger registration of the real
# specs. Wrapped because some test environments (and the binary's
# ``--collect-all`` PyInstaller path) may want the registry helpers
# without instantiating the heavy interactive session module.
def _populate_from_session() -> None:
    try:

        from lyra_cli.interactive import session as _session  # noqa: F401
    except ImportError:
        # session module unavailable — registry stays empty and callers
        # that need it will get an empty list. Plugins / tests can still
        # populate via :func:`register_command`.
        pass


_populate_from_session()
