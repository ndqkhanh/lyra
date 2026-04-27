"""Wave-D Task 7: per-session tool-approval cache.

The agent loop asks the cache "should this tool fire?" via
:meth:`ToolApprovalCache.inquire`. The cache returns one of:

* ``"allow"`` — the user has previously approved this tool *for the
  current session* (and we're not in ``strict`` mode).
* ``"deny"`` — the user has explicitly denied this tool; the loop
  should refuse without prompting again.
* ``"prompt"`` — the loop must prompt the user; on a yes the loop
  calls :meth:`approve`, on a no it calls :meth:`deny`.

Mode semantics mirror :class:`InteractiveSession.permission_mode`
(Wave C):

* ``yolo``   — always allow.
* ``normal`` — cache approvals/denials for the session.
* ``strict`` — always re-prompt (cache is a no-op).

The cache is intentionally session-scoped: a fresh REPL run starts
with no decisions, so the user always sees at least one prompt for
each high-risk tool. (Persisting approvals across sessions is a
Wave-E feature when the policy file lands.)
"""
from __future__ import annotations

from typing import Literal


PermissionMode = Literal["normal", "strict", "yolo"]
Verdict = Literal["allow", "deny", "prompt"]


class ToolApprovalCache:
    """Per-session approval ledger for tool calls."""

    def __init__(self, *, mode: PermissionMode = "normal") -> None:
        self.mode: PermissionMode = mode
        self._allow: set[str] = set()
        self._deny: set[str] = set()

    # ------------------------------------------------------------------ API
    def set_mode(self, mode: PermissionMode) -> None:
        """Update the live mode (the REPL flips this via Alt+M)."""
        self.mode = mode

    def inquire(self, tool_name: str) -> Verdict:
        """Return the cached verdict for ``tool_name``.

        Strict and yolo bypass the cache:

        * ``yolo``   → ``allow`` no matter what.
        * ``strict`` → ``prompt`` no matter what (re-confirm every call).
        * ``normal`` → cached decision wins; otherwise ``prompt``.
        """
        if self.mode == "yolo":
            return "allow"
        if self.mode == "strict":
            return "prompt"
        if tool_name in self._deny:
            return "deny"
        if tool_name in self._allow:
            return "allow"
        return "prompt"

    def approve(self, tool_name: str) -> None:
        self._allow.add(tool_name)
        self._deny.discard(tool_name)

    def deny(self, tool_name: str) -> None:
        self._deny.add(tool_name)
        self._allow.discard(tool_name)

    def forget(self, tool_name: str) -> None:
        self._allow.discard(tool_name)
        self._deny.discard(tool_name)

    def snapshot(self) -> dict[str, Verdict]:
        """Read-only view of the current decisions (for ``/tools approve``)."""
        out: dict[str, Verdict] = {}
        for name in self._allow:
            out[name] = "allow"
        for name in self._deny:
            out[name] = "deny"
        return out


__all__ = ["PermissionMode", "ToolApprovalCache", "Verdict"]
