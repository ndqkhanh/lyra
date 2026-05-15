"""Mount-bound, budget-aware tools for investigate mode.

Three tools — ``codesearch``, ``read_file``, ``execute_code`` — wrapped
in a factory that closes over the :class:`CorpusMount` (so every call
is gated to the mount root) and the :class:`InvestigationBudget` (so
every bash call ticks the bash counter and every read accounts bytes).
This mirrors :func:`lyra_core.tools.codesearch.make_codesearch_tool`'s
factory-with-closure pattern.

The wrappers do **not** modify the underlying tools' signatures; the
AgentLoop sees the same ``__tool_schema__`` shape it sees for every
other tool. Budget breaches raise :class:`KeyboardInterrupt` (after
recording the breach on the budget) so :meth:`AgentLoop._dispatch_tool`
propagates them as a clean ``stopped_by="interrupt"`` instead of
swallowing them into ``{"error": ..., "type": ...}``.

Cite: arXiv:2605.05242 §3 — direct corpus interaction; DCI-Agent-Lite
README "Turn budget (max 300)".
"""
from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ..tools.codesearch import make_codesearch_tool
from .budget import BudgetExceeded, InvestigationBudget
from .corpus import CorpusMount

# Commands allowed by ``execute_code`` in investigate mode. Matches the
# DCI-Agent-Lite system prompt's "rg, find, sed, head, tail, wc, awk,
# sort, uniq, xargs, cat" allowlist.
_ALLOWED_EXEC_COMMANDS: frozenset[str] = frozenset(
    {"rg", "grep", "find", "sed", "head", "tail", "wc", "awk",
     "sort", "uniq", "xargs", "cat", "ls"},
)


def _budget_breach_to_interrupt(budget: InvestigationBudget, fn: Callable[[], Any]) -> Any:
    """Run *fn* and convert any :class:`BudgetExceeded` into KeyboardInterrupt.

    The AgentLoop's ``_dispatch_tool`` propagates KeyboardInterrupt
    cleanly; any other exception gets swallowed into a tool-error dict,
    which would *hide* a budget breach. We translate at the boundary.
    The original ``BudgetExceeded`` is attached as ``__cause__`` so
    callers can inspect the axis if needed.
    """
    try:
        return fn()
    except BudgetExceeded as exc:
        raise KeyboardInterrupt(str(exc)) from exc


def make_read_file_tool(
    *, mount: CorpusMount, budget: InvestigationBudget,
) -> Callable[..., dict]:
    """Build a ``read_file`` callable bound to *mount* and *budget*."""

    def read_file(
        path: str,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> dict:
        """Read a slice of a file inside the corpus mount."""
        def _do() -> dict:
            target = mount.assert_readable(Path(mount.root) / path)
            text = target.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            lo = max(1, start_line or 1)
            hi = min(len(lines), end_line or len(lines))
            slice_lines = lines[lo - 1 : hi]
            body = "\n".join(slice_lines)
            budget.record_bytes(len(body.encode("utf-8")))
            return {
                "path": path,
                "start_line": lo,
                "end_line": hi,
                "total_lines": len(lines),
                "text": body,
            }

        return _budget_breach_to_interrupt(budget, _do)

    read_file.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "read_file",
        "description": (
            "Read a slice of a file inside the corpus mount. "
            "Use start_line/end_line to bound the read."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer"},
                "end_line": {"type": "integer"},
            },
            "required": ["path"],
        },
    }
    return read_file


def make_execute_code_tool(
    *, mount: CorpusMount, budget: InvestigationBudget,
) -> Callable[..., dict]:
    """Build an ``execute_code`` callable bound to *mount* and *budget*.

    The command is a single allowlisted binary plus its arguments — no
    pipes, no shell. The DCI paper's tool-usage RQ6 shows the agent
    rarely needs pipes; when it does, it can use multiple `codesearch`
    or chained `read_file` calls. Restricting to a single binary is
    the cheapest way to keep the sandbox honest.
    """

    def execute_code(cmd: list[str] | str) -> dict:
        def _do() -> dict:
            budget.record_bash_call()
            argv = cmd.split() if isinstance(cmd, str) else list(cmd)
            if not argv:
                return {"error": "empty command"}
            binary = argv[0]
            if binary not in _ALLOWED_EXEC_COMMANDS:
                return {
                    "error": f"command {binary!r} not allowed in investigate mode",
                    "allowed": sorted(_ALLOWED_EXEC_COMMANDS),
                }
            resolved_bin = shutil.which(binary)
            if resolved_bin is None:
                return {"error": f"binary not found on PATH: {binary}"}
            try:
                res = subprocess.run(
                    [resolved_bin, *argv[1:]],
                    cwd=mount.root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                return {"error": f"subprocess failed: {exc}"}
            stdout = res.stdout or ""
            budget.record_bytes(len(stdout.encode("utf-8")))
            return {
                "command": argv,
                "returncode": res.returncode,
                "stdout": stdout,
                "stderr": res.stderr or "",
            }

        return _budget_breach_to_interrupt(budget, _do)

    execute_code.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "execute_code",
        "description": (
            "Run one allow-listed binary inside the corpus mount. "
            f"Allowed: {sorted(_ALLOWED_EXEC_COMMANDS)}. Writes and "
            "network are denied."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "array", "items": {"type": "string"},
                    "description": "argv list, first entry is the binary",
                },
            },
            "required": ["cmd"],
        },
    }
    return execute_code


def make_investigate_tools(
    *, mount: CorpusMount, budget: InvestigationBudget,
) -> Mapping[str, Callable[..., Any]]:
    """Bundle the three investigate-mode tools as ``{name: callable}``.

    The returned mapping is suitable to pass directly to
    :class:`lyra_core.agent.loop.AgentLoop(tools=...)`.
    """
    return {
        "codesearch": make_codesearch_tool(repo_root=mount.root),
        "read_file": make_read_file_tool(mount=mount, budget=budget),
        "execute_code": make_execute_code_tool(mount=mount, budget=budget),
    }


__all__ = [
    "make_execute_code_tool",
    "make_investigate_tools",
    "make_read_file_tool",
]
