"""Interactive REPL for ``lyra`` (Phase 13).

Running ``lyra`` with no arguments drops into a Claude-Code-style
shell: plain text is routed to the current mode, ``/``-prefixed words
are slash commands, and a bottom status bar keeps the operator oriented.

The module is intentionally layered:

- ``session`` — pure dispatch logic + slash registry. No I/O, no TTY.
- ``banner``  — Rich-rendered start screen. No I/O beyond returning a string.
- ``completer`` — prompt_toolkit slash completer (optional dep).
- ``driver``  — prompt_toolkit + Rich front-end, with a graceful fallback
                to plain ``input()`` when stdout isn't a TTY (or when
                prompt_toolkit isn't installed).

Only ``driver`` touches the terminal. Everything else is unit-testable.

Imports here are intentionally **lazy** (PEP 562 ``__getattr__``) so a
test or external script that only wants the pure dispatcher doesn't pay
the ~50 ms cost of importing :mod:`.banner` and Rich just to read the
package's ``__all__``. Cold ``lyra`` startup drops accordingly.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import-time only for type checkers
    from .banner import render_banner
    from .session import (
        SLASH_COMMANDS,
        CommandResult,
        InteractiveSession,
    )


__all__ = [
    "SLASH_COMMANDS",
    "CommandResult",
    "InteractiveSession",
    "render_banner",
]


# Map public name → (submodule, attribute). Resolved on first access.
_LAZY: dict[str, tuple[str, str]] = {
    "SLASH_COMMANDS": ("session", "SLASH_COMMANDS"),
    "CommandResult": ("session", "CommandResult"),
    "InteractiveSession": ("session", "InteractiveSession"),
    "render_banner": ("banner", "render_banner"),
}


def __getattr__(name: str) -> Any:  # PEP 562
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        )
    module_name, attr_name = target
    from importlib import import_module

    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, attr_name)
    # Cache on the package so subsequent lookups skip __getattr__ entirely.
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY))
