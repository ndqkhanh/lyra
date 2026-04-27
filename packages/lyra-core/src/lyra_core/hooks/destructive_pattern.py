"""destructive-pattern hook.

Blocks shell / tool calls whose command string matches catastrophic patterns.
Pre-tool-use only. Conservative by default; falsely blocked commands surface
as user-visible errors.

Covered:
    - ``rm -rf /`` and variants (``/``, ``~``, ``$HOME``, globs expanding to root)
    - ``dd if=... of=/dev/…`` (raw disk writes)
    - ``mkfs.*`` and ``fdisk`` on block devices
    - ``chmod 777 -R /``
    - ``shred`` on root paths
    - ``git push --force`` to protected refs (main, master, release/*)
    - ``:(){ :|:& };:`` style fork bombs (basic pattern)
"""
from __future__ import annotations

import re

from harness_core.hooks import HookDecision
from harness_core.messages import ToolCall, ToolResult

_DESTRUCTIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "rm_rf_root_like",
        re.compile(
            r"\brm\s+(?:-[a-zA-Z]*[rf][a-zA-Z]*\s+|-r\s+-f\s+|-f\s+-r\s+)[^\n]*?"
            r"(?:/\s*$|/\s+|\s+/\s|~\s*$|~\s+|\$HOME\b|\$\{?HOME\}?)"
        ),
    ),
    (
        "rm_rf_root_simple",
        re.compile(r"\brm\s+-[rRf]+\s+(?:/|~|\$HOME)\s*(?:$|\s)"),
    ),
    (
        "dd_to_disk",
        re.compile(r"\bdd\s+.*\bof=/dev/(?:sd[a-z]|nvme|hd[a-z]|disk\d)"),
    ),
    (
        "mkfs_on_device",
        re.compile(r"\bmkfs(?:\.\w+)?\s+/dev/(?:sd[a-z]|nvme|hd[a-z]|disk\d)"),
    ),
    (
        "chmod_777_root",
        re.compile(r"\bchmod\s+(?:-R\s+)?0?777\s+(?:-R\s+)?/\b"),
    ),
    (
        "force_push_protected",
        re.compile(
            r"\bgit\s+push\s+(?:[^\n]*\s)?(?:-f\b|--force\b)"
            r"(?:[^\n]*\s)?(?:main|master|release/\S+)"
        ),
    ),
    (
        "fork_bomb",
        re.compile(r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:"),
    ),
    (
        "shred_root",
        re.compile(r"\bshred\s+(?:-[a-zA-Z]*\s+)?(?:/|~|\$HOME)(?:\s|$)"),
    ),
)


def destructive_pattern_hook(call: ToolCall, _result: ToolResult | None) -> HookDecision:
    """Block calls matching destructive patterns.

    Scans string-valued args; non-string args are coerced via ``repr``.
    Only triggers on Bash / shell-style tools in practice, but scanning all
    tool calls is cheap and catches unusual invocations.
    """
    for key, value in call.args.items():
        if not isinstance(value, str):
            value = repr(value)
        for name, pat in _DESTRUCTIVE_PATTERNS:
            if pat.search(value):
                return HookDecision(
                    block=True,
                    reason=(
                        f"destructive-pattern: matched {name!r} in arg {key!r}; "
                        f"this is a catastrophic / irreversible command"
                    ),
                )
    return HookDecision(block=False)
