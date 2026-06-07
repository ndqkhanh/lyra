"""
SABER Mutation-Gated Verification — gate mutating actions behind verification.

Implements the SABER pattern from the MemAgent Workshop (ICLR 2026):
distinguish mutating vs non-mutating tool calls and require verification
for any action that modifies state (writes files, runs commands, makes
network requests that change remote state).

Non-mutating actions (reads, searches, queries) are auto-approved.
Mutating actions require verification through the §4.25 panel.

References
----------
- SABER: Small Actions, Big Errors — Amazon AGI
  ICLR 2026 MemAgent Workshop. +28% on Airline, τ-Bench Verified dataset.
- Lyra §4.17 Safety Plan: plans/4.17-safety.md
- Lyra §4.25 Verification Panel Plan: plans/4.13-swarm-fleet.md
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ActionClass(str, Enum):
    """Classification of a tool call by its mutating potential."""

    READ = "read"           # Pure read — safe to auto-approve
    SEARCH = "search"       # Read-like, no side effects
    COMPUTE = "compute"     # Pure computation, no I/O side effects
    WRITE = "write"         # Mutates local filesystem
    EXECUTE = "execute"     # Runs arbitrary code/commands
    NETWORK_WRITE = "network_write"  # Mutates remote state (API POST/PUT/DELETE)
    NETWORK_READ = "network_read"    # Reads remote state (API GET)
    UNKNOWN = "unknown"     # Cannot classify — treat as mutating (safe default)


@dataclass(frozen=True)
class MutationVerdict:
    """Result of mutation classification for a tool call.

    Attributes:
        action_class: The classified action type.
        is_mutating: Whether this action changes state.
        requires_verification: Whether verification is required.
        reason: Human-readable explanation.
    """

    action_class: ActionClass
    is_mutating: bool
    requires_verification: bool
    reason: str


# Tool name → default ActionClass mapping (extensible per-deployment)
_DEFAULT_TOOL_CLASSIFICATIONS: dict[str, ActionClass] = {
    # Read tools — safe
    "read_file": ActionClass.READ,
    "list_files": ActionClass.READ,
    "search_file": ActionClass.SEARCH,
    "search_content": ActionClass.SEARCH,
    "grep": ActionClass.SEARCH,
    "find": ActionClass.SEARCH,
    "get_definition": ActionClass.READ,
    "hover": ActionClass.READ,
    "document_symbol": ActionClass.READ,
    # Compute tools — safe (pure computation)
    "evaluate_expression": ActionClass.COMPUTE,
    "run_analysis": ActionClass.COMPUTE,
    # Write tools — MUTATING (require verification)
    "write_file": ActionClass.WRITE,
    "edit_file": ActionClass.WRITE,
    "replace_in_file": ActionClass.WRITE,
    "delete_file": ActionClass.WRITE,
    "create_directory": ActionClass.WRITE,
    # Execute tools — MUTATING (require verification)
    "execute_command": ActionClass.EXECUTE,
    "run_terminal": ActionClass.EXECUTE,
    "bash": ActionClass.EXECUTE,
    "shell": ActionClass.EXECUTE,
    # Network read — safe (but log for monitoring)
    "web_fetch": ActionClass.NETWORK_READ,
    "web_search": ActionClass.NETWORK_READ,
    "api_get": ActionClass.NETWORK_READ,
    # Network write — MUTATING (require verification)
    "api_post": ActionClass.NETWORK_WRITE,
    "api_put": ActionClass.NETWORK_WRITE,
    "api_delete": ActionClass.NETWORK_WRITE,
    "git_push": ActionClass.NETWORK_WRITE,
    "create_pr": ActionClass.NETWORK_WRITE,
    "merge_pr": ActionClass.NETWORK_WRITE,
    "deploy": ActionClass.NETWORK_WRITE,
}


# Which action classes require verification
_MUTATING_CLASSES: frozenset[ActionClass] = frozenset({
    ActionClass.WRITE,
    ActionClass.EXECUTE,
    ActionClass.NETWORK_WRITE,
    ActionClass.UNKNOWN,
})


class MutationGate:
    """Classifies tool calls and gates mutating actions behind verification.

    Usage::

        gate = MutationGate()
        verdict = gate.classify("write_file", {"path": "/etc/config.json"})

        if verdict.requires_verification:
            # Route to §4.25 verification panel before executing
            panel_approved = await verification_panel.review(tool_call)
            if not panel_approved:
                raise SafetyBlockedError(verdict.reason)
    """

    def __init__(
        self,
        tool_classifications: dict[str, ActionClass] | None = None,
        auto_approve_patterns: list[str] | None = None,
    ) -> None:
        self._classifications = dict(_DEFAULT_TOOL_CLASSIFICATIONS)
        if tool_classifications:
            self._classifications.update(tool_classifications)

        # Path patterns or command prefixes that are safe despite being "write"
        self._auto_approve_patterns = auto_approve_patterns or [
            ".gitignore",
            ".lyrainclude",
            "README.md",
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MutationVerdict:
        """Classify a tool call and determine if verification is required.

        Args:
            tool_name: The tool being called (e.g. ``"write_file"``).
            arguments: Optional tool arguments for context-aware classification.

        Returns:
            ``MutationVerdict`` with classification and verification requirement.
        """
        action_class = self._classify_tool(tool_name)
        is_mutating = action_class in _MUTATING_CLASSES

        # Context-aware override: some write targets are safe
        if is_mutating and arguments:
            if self._is_safe_write(arguments):
                return MutationVerdict(
                    action_class=action_class,
                    is_mutating=True,
                    requires_verification=False,
                    reason=f"Write to safe target (auto-approved pattern)",
                )

        if not is_mutating:
            return MutationVerdict(
                action_class=action_class,
                is_mutating=False,
                requires_verification=False,
                reason=f"{action_class.value} action — auto-approved",
            )

        return MutationVerdict(
            action_class=action_class,
            is_mutating=True,
            requires_verification=True,
            reason=f"{action_class.value} action — verification required",
        )

    def classify_batch(
        self,
        tool_calls: list[tuple[str, dict[str, Any] | None]],
    ) -> list[MutationVerdict]:
        """Classify multiple tool calls at once.

        Args:
            tool_calls: List of (tool_name, arguments) tuples.

        Returns:
            List of ``MutationVerdict``, one per tool call.
        """
        return [self.classify(name, args) for name, args in tool_calls]

    def any_require_verification(self, verdicts: list[MutationVerdict]) -> bool:
        """Check if any verdict in a batch requires verification."""
        return any(v.requires_verification for v in verdicts)

    def register_tool(
        self, tool_name: str, action_class: ActionClass
    ) -> None:
        """Register or override a tool classification.

        Args:
            tool_name: The tool name to classify.
            action_class: Its mutation classification.
        """
        self._classifications[tool_name] = action_class

    def get_classification(self, tool_name: str) -> ActionClass:
        """Get the current classification for a tool.

        Args:
            tool_name: The tool name.

        Returns:
            Its ``ActionClass``, or ``UNKNOWN`` if not registered.
        """
        return self._classifications.get(tool_name, ActionClass.UNKNOWN)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _classify_tool(self, tool_name: str) -> ActionClass:
        """Classify a tool by name, with prefix/suffix heuristics."""
        if tool_name in self._classifications:
            return self._classifications[tool_name]

        name_lower = tool_name.lower()

        # Heuristic classification by name pattern
        if any(prefix in name_lower for prefix in ("read", "get", "list", "find", "search", "query")):
            return ActionClass.READ
        if any(prefix in name_lower for prefix in ("write", "create", "edit", "replace", "delete", "remove")):
            return ActionClass.WRITE
        if any(prefix in name_lower for prefix in ("run", "exec", "bash", "shell", "cmd")):
            return ActionClass.EXECUTE

        return ActionClass.UNKNOWN

    @staticmethod
    def _is_safe_write(arguments: dict[str, Any]) -> bool:
        """Check if a write targets a known-safe path."""
        path = arguments.get("path") or arguments.get("file") or arguments.get("file_path") or ""
        if not path:
            return False

        safe_suffixes = (".gitignore", ".lyrainclude", "README.md", "CHANGELOG.md")
        return any(str(path).endswith(suf) for suf in safe_suffixes)
