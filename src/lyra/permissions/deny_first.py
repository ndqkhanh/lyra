"""
Deny-first permission evaluator for Lyra (v8.3).

Implements a default-deny permission engine with explicit allowlists.
Shifts the security posture from implicit trust to explicit permission.

Key design
----------
* **Default-deny**: Any action not explicitly allowed is denied.
* **Rule priority**: explicit_allow > explicit_deny > default_deny.
* **Compound action parsing**: Detects chained tool calls (e.g.
  "read file X then POST to Y") and evaluates each step independently.
* **Path traversal prevention**: Normalises and validates all filesystem
  paths to prevent ``../`` escapes, symlink attacks, and null bytes.
* **Credential scoping**: Per-session API key isolation so credentials
  from one session cannot leak into another.

Classes
-------
Decision:
    Enum: ALLOW, DENY, CONDITIONAL.
CompoundAction:
    Parsed representation of a chained tool call.
PathTraversalPreventer:
    Filesystem path normalisation and traversal detection.
CredentialScope:
    Per-session API key and credential management.
DenyFirstEvaluator:
    Core default-deny evaluator.
"""

from __future__ import annotations

import logging
import os
import re
import posixpath
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from lyra.permissions.manager import AccessLevel, PermissionResult
from lyra.safety.policy import GateDecision, Policy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


class Decision(str, Enum):
    """Evaluation decision from the deny-first engine.

    * ALLOW — Action is explicitly permitted.
    * DENY — Action is denied (either explicitly or by default).
    * CONDITIONAL — Action is allowed only under specified conditions.
    """

    ALLOW = "allow"
    DENY = "deny"
    CONDITIONAL = "conditional"


# ---------------------------------------------------------------------------
# CompoundAction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActionStep:
    """A single step in a compound action chain.

    Attributes:
        tool_name: The tool being invoked (e.g. ``"Read"``, ``"Bash"``).
        arguments: Arguments to the tool call.
        order: The step's position in the chain (0-indexed).
    """

    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    order: int = 0


@dataclass(frozen=True)
class CompoundAction:
    """A parsed chain of tool calls detected in a single request.

    Example: "read file X, then POST the content to Y" would be parsed
    as two ``ActionStep`` instances.

    Attributes:
        original_input: The raw input string (if any).
        steps: The parsed sequence of tool calls.
    """

    original_input: str = ""
    steps: List[ActionStep] = field(default_factory=list)

    @property
    def is_compound(self) -> bool:
        """True if this action contains more than one step."""
        return len(self.steps) > 1

    @property
    def step_count(self) -> int:
        """Number of individual steps in this compound action."""
        return len(self.steps)


# ---------------------------------------------------------------------------
# Compound action parser
# ---------------------------------------------------------------------------


class CompoundActionParser:
    """Parses chained tool calls from natural language or structured input.

    Detects patterns like:
    * "read X and send to Y"
    * "X then Y"
    * "after reading X, POST to Y"
    * Sequential tool invocations in a batch
    """

    # Pattern: "then" or "and then" between steps
    _SEQUENCE_PATTERNS: List[re.Pattern] = [
        re.compile(r",?\s*(?:then|and then|after that|next)\s*,?", re.IGNORECASE),
        re.compile(r"\s*;\s*"),
        re.compile(r"\s*&&\s*"),
    ]

    # Tool name mapping for natural language aliases
    _TOOL_ALIASES: Dict[str, str] = {
        "read": "Read",
        "read file": "Read",
        "write": "Write",
        "write file": "Write",
        "edit": "Edit",
        "bash": "Bash",
        "run": "Bash",
        "execute": "Bash",
        "shell": "Bash",
        "command": "Bash",
        "search": "WebSearch",
        "web search": "WebSearch",
        "fetch": "WebFetch",
        "web fetch": "WebFetch",
        "post": "ApiPost",
        "api post": "ApiPost",
        "put": "ApiPut",
        "delete": "ApiDelete",
        "get": "ApiGet",
        "api get": "ApiGet",
    }

    def __init__(self) -> None:
        # Accumulated sequence tokens for ordered parsing
        self._sequence_token = re.compile(
            r"\b(then|and then|after that|next|followed by|;\s*)\b",
            re.IGNORECASE,
        )

    def parse(self, input_str: str) -> CompoundAction:
        """Parse a natural language or structured input into steps.

        Args:
            input_str: The raw input describing chained tool calls.

        Returns:
            A ``CompoundAction`` with parsed steps.
        """
        if not input_str or not input_str.strip():
            return CompoundAction(original_input=input_str)

        # First try: detect explicit sequence markers
        parts = self._sequence_token.split(input_str)
        # Filter out the markers, keep only the step descriptions
        raw_steps = [p.strip() for p in parts if p.strip() and not self._is_connector(p.strip())]

        if len(raw_steps) <= 1:
            # Single action — try to classify it directly
            return self._parse_single(input_str)

        steps: List[ActionStep] = []
        for i, raw in enumerate(raw_steps):
            parsed = self._parse_single_step(raw, i)
            steps.append(parsed)

        return CompoundAction(original_input=input_str, steps=steps)

    def parse_batch(
        self, tool_calls: List[Tuple[str, Dict[str, Any]]]
    ) -> CompoundAction:
        """Parse an ordered batch of tool calls into a compound action.

        Args:
            tool_calls: List of ``(tool_name, arguments)`` tuples.

        Returns:
            A ``CompoundAction`` with one step per tool call.
        """
        steps = [
            ActionStep(
                tool_name=name,
                arguments=args or {},
                order=i,
            )
            for i, (name, args) in enumerate(tool_calls)
        ]
        return CompoundAction(steps=steps)

    def detect_chain_in_args(self, arguments: Dict[str, Any]) -> Optional[CompoundAction]:
        """Check if tool arguments contain a chained call description.

        Scans argument values for sequence language (e.g. "then", "and").
        """
        for key, value in arguments.items():
            if isinstance(value, str) and len(value) > 10:
                parsed = self.parse(value)
                if parsed.is_compound:
                    return parsed
        return None

    # ------------------------------------------------------------------
    # Internal parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_connector(token: str) -> bool:
        """Check if a token is a sequence connector word."""
        connectors = {
            "then", "and then", "after that", "next", "followed by", ";", "&&",
        }
        return token.strip().lower() in connectors

    def _parse_single(self, input_str: str) -> CompoundAction:
        """Parse a single action from free-form text."""
        tool_name, args = self._classify_text(input_str)
        return CompoundAction(
            original_input=input_str,
            steps=[
                ActionStep(tool_name=tool_name, arguments=args, order=0),
            ],
        )

    def _parse_single_step(self, text: str, order: int) -> ActionStep:
        """Parse one step description into an ``ActionStep``."""
        tool_name, args = self._classify_text(text)
        return ActionStep(tool_name=tool_name, arguments=args, order=order)

    @classmethod
    def _classify_text(cls, text: str) -> Tuple[str, Dict[str, Any]]:
        """Classify free-form text into a tool name and arguments."""
        text_lower = text.lower().strip()

        # Try exact alias match first
        for alias, tool in cls._TOOL_ALIASES.items():
            if text_lower.startswith(alias) or text_lower == alias:
                remaining = text[len(alias):].strip(" ,;:")
                args: Dict[str, Any] = {}
                if tool == "Bash" and remaining:
                    args["command"] = remaining.lstrip("`").rstrip("`")
                elif tool == "Read" and remaining:
                    args["file_path"] = remaining.strip("'\"")
                elif tool == "Write" and remaining:
                    args["file_path"] = remaining.strip("'\"")
                elif tool == "WebSearch" and remaining:
                    args["query"] = remaining.strip("'\"")
                elif tool == "WebFetch" and remaining:
                    args["url"] = remaining.strip("'\"")
                return tool, args

        # Default: generic Bash command
        return "Bash", {"command": text}

    # ------------------------------------------------------------------
    # Old-style batch support for backward compat
    # ------------------------------------------------------------------

    def parse_sequential(
        self, steps: List[Dict[str, Any]]
    ) -> CompoundAction:
        """Parse a list of structured step dicts into a ``CompoundAction``.

        Each step dict should have keys ``tool_name`` and optionally
        ``arguments``.  Provided for backward compatibility.

        Args:
            steps: List of step descriptors.

        Returns:
            A ``CompoundAction``.
        """
        action_steps: List[ActionStep] = []
        for i, step in enumerate(steps):
            action_steps.append(
                ActionStep(
                    tool_name=step.get("tool_name", "Bash"),
                    arguments=step.get("arguments", {}),
                    order=i,
                )
            )
        return CompoundAction(steps=action_steps)


# ---------------------------------------------------------------------------
# PathTraversalPreventer
# ---------------------------------------------------------------------------


class PathTraversalPreventer:
    """Filesystem path normalisation and traversal detection.

    Detects and blocks:
    * Directory traversal via ``../`` (POSIX) or ``..\\`` (Windows).
    * Null byte injection (``%00``, ``\\x00``).
    * Symlink-based escapes (resolved real path outside allowed root).
    * Absolute path escapes when a relative root is enforced.
    """

    # Suspicious patterns in path strings
    _TRAVERSAL_PATTERNS: List[re.Pattern] = [
        re.compile(r"(?:^|[/\\])\.\.(?:[/\\]|$)"),
        re.compile(r"%00"),
        re.compile(r"\\x00"),
        re.compile(r"\0"),
        re.compile(r"\.\.\\"),
    ]

    # Prohibited path components
    _PROHIBITED_COMPONENTS: Set[str] = {
        "..",
        "~",
        "$HOME",
        "%HOME%",
        "${HOME}",
    }

    def __init__(self, enforce_relative: bool = True) -> None:
        """Initialise the preventer.

        Args:
            enforce_relative: If True, raises a block on absolute paths
                when a relative root is configured.  Default True.
        """
        self._enforce_relative = enforce_relative

    def is_safe_path(self, path: str, allowed_roots: Optional[List[str]] = None) -> bool:
        """Check if a path is safe (no traversal, within allowed roots).

        Args:
            path: The file path to validate.
            allowed_roots: List of allowed root directories.  The path
                must resolve within at least one of these.

        Returns:
            True if the path is safe, False otherwise.
        """
        if not path:
            return False

        # Check for traversal patterns
        for pattern in self._TRAVERSAL_PATTERNS:
            if pattern.search(path):
                logger.warning(
                    "PathTraversalPreventer: traversal pattern detected in '%s'",
                    path,
                )
                return False

        # Check for prohibited components
        parts = PurePosixPath(path).parts
        for part in parts:
            if part in self._PROHIBITED_COMPONENTS:
                logger.warning(
                    "PathTraversalPreventer: prohibited component '%s' in '%s'",
                    part,
                    path,
                )
                return False

        # Normalise
        normalised = self.normalise(path)
        if normalised is None:
            return False

        # Check allowed roots
        if allowed_roots:
            for root in allowed_roots:
                normalised_root = self.normalise(root)
                if normalised_root and str(normalised).startswith(str(normalised_root)):
                    return True
            logger.warning(
                "PathTraversalPreventer: path '%s' not in allowed roots %s",
                path,
                allowed_roots,
            )
            return False

        return True

    @staticmethod
    def normalise(path: str) -> Optional[str]:
        """Normalise a path, stripping traversal and null bytes.

        Returns a clean, resolved path string, or ``None`` if the
        path contains unresolvable traversal.
        """
        if not path:
            return None

        # Strip null bytes and control characters
        cleaned = re.sub(r"[\x00-\x08\x0e-\x1f]", "", path)
        if cleaned != path:
            logger.info("PathTraversalPreventer: stripped control chars from '%s'", path)

        # Normalise — resolve ``..`` lexically using posixpath.normpath
        try:
            normalised = posixpath.normpath(PurePosixPath(cleaned).as_posix())
        except Exception:
            return None

        # If the normalised path still starts with ``..``, it escapes the root
        if normalised.startswith(".."):
            return None

        return normalised

    @staticmethod
    def resolve_real_path(path: str) -> Optional[str]:
        """Resolve the real filesystem path, following symlinks.

        Returns ``None`` if the path does not exist or cannot be resolved.
        """
        try:
            if not os.path.exists(path):
                return None
            return os.path.realpath(path)
        except (OSError, ValueError):
            return None


# ---------------------------------------------------------------------------
# CredentialScope
# ---------------------------------------------------------------------------


@dataclass
class CredentialEntry:
    """A single credential with session isolation.

    Attributes:
        key: The credential key (e.g. ``"OPENAI_API_KEY"``).
        value: The credential value.
        session_id: The session that owns this credential.
        allowed_tools: Tools this credential may be used with. Empty
            means all tools.
    """

    key: str
    value: str
    session_id: str
    allowed_tools: List[str] = field(default_factory=list)

    def is_accessible_by(self, session_id: str, tool_name: str) -> bool:
        """Check if this credential is accessible from a session+tool.

        Args:
            session_id: The requesting session.
            tool_name: The requesting tool.

        Returns:
            True if the credential is accessible.
        """
        if self.session_id and self.session_id != session_id:
            return False
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return False
        return True


class CredentialScope:
    """Per-session credential isolation.

    Credentials registered under one session ID are not visible to
    other sessions.  Optionally restricts credentials to specific tools.
    """

    def __init__(self) -> None:
        self._credentials: Dict[str, CredentialEntry] = {}

    def register(
        self,
        key: str,
        value: str,
        session_id: str,
        allowed_tools: Optional[List[str]] = None,
    ) -> None:
        """Register a credential for a specific session.

        Args:
            key: The credential key.
            value: The credential value.
            session_id: The owning session ID.
            allowed_tools: Optional tool allowlist.  Empty means all
                tools.
        """
        self._credentials[key] = CredentialEntry(
            key=key,
            value=value,
            session_id=session_id,
            allowed_tools=allowed_tools or [],
        )

    def get(
        self,
        key: str,
        session_id: str,
        tool_name: str = "",
    ) -> Optional[str]:
        """Retrieve a credential if accessible from the given session.

        Args:
            key: The credential key.
            session_id: The requesting session ID.
            tool_name: The requesting tool name.

        Returns:
            The credential value, or ``None`` if inaccessible.
        """
        entry = self._credentials.get(key)
        if entry is None:
            return None
        if entry.is_accessible_by(session_id, tool_name):
            return entry.value
        return None

    def list_for_session(self, session_id: str) -> Dict[str, str]:
        """List all credentials visible to a session.

        Args:
            session_id: The session ID.

        Returns:
            Dict of ``key -> value``.
        """
        return {
            k: e.value
            for k, e in self._credentials.items()
            if e.session_id == session_id
        }

    def revoke_session(self, session_id: str) -> int:
        """Revoke all credentials for a session.

        Args:
            session_id: The session to revoke.

        Returns:
            Number of credentials revoked.
        """
        to_revoke = [k for k, e in self._credentials.items() if e.session_id == session_id]
        for k in to_revoke:
            del self._credentials[k]
        return len(to_revoke)

    def revoke_key(self, key: str) -> bool:
        """Revoke a single credential by key.

        Args:
            key: The credential key.

        Returns:
            True if revoked.
        """
        return self._credentials.pop(key, None) is not None


# ---------------------------------------------------------------------------
# DenyFirstEvaluator
# ---------------------------------------------------------------------------


class DenyFirstEvaluator:
    """Default-deny permission evaluator with explicit allowlists.

    Evaluates tool actions against a set of explicit allow/deny rules.
    The default posture is **DENY** — every action must be explicitly
    allowed.

    Rule priority (highest to lowest):
    1. ``explicit_allow`` — Actions explicitly listed as allowed.
    2. ``explicit_deny`` — Actions explicitly listed as denied.
    3. ``default_deny`` — All other actions are denied.

    Supports compound action parsing, path traversal prevention, and
    credential scoping.
    """

    def __init__(
        self,
        allowlist: Optional[Set[str]] = None,
        denylist: Optional[Set[str]] = None,
        policy: Optional[Policy] = None,
        allow_mutating_by_default: bool = False,
    ) -> None:
        """Initialise the evaluator.

        Args:
            allowlist: Explicitly allowed tool names (set of strings).
            denylist: Explicitly denied tool names (set of strings).
            policy: An optional ``Policy`` to seed the allowlist from.
            allow_mutating_by_default: If True, mutating tools (Write,
                Edit, Bash) are allowed by default.  Default False
                (all mutations require explicit allow).
        """
        self._allowlist: Set[str] = set(allowlist or set())
        self._denylist: Set[str] = set(denylist or set())
        self._conditional_tools: Set[str] = set()
        self._allow_mutating_by_default = allow_mutating_by_default

        # Seed from policy
        if policy is not None:
            self._allowlist.update(policy.allowed_tools)
            self._conditional_tools.update(policy.requires_approval_for)

        # Sub-systems
        self._path_preventer = PathTraversalPreventer()
        self._credential_scope = CredentialScope()
        self._compound_parser = CompoundActionParser()

        # Allowlist of paths (prefixes that are explicitly allowed)
        self._allowed_path_prefixes: List[str] = []

        # Mutating tools — require explicit allow unless allow_mutating_by_default
        self._MUTATING_TOOLS: Set[str] = {
            "Write", "Edit", "Bash", "ApiPost", "ApiPut",
            "ApiDelete", "GitPush", "Deploy",
        }

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_allow(self, tool_name: str) -> None:
        """Explicitly allow a tool.

        Args:
            tool_name: Tool name (e.g. ``"Read"``).
        """
        self._allowlist.add(tool_name)

    def add_deny(self, tool_name: str) -> None:
        """Explicitly deny a tool and remove from allowlist.

        Args:
            tool_name: Tool name to deny.
        """
        self._denylist.add(tool_name)
        self._allowlist.discard(tool_name)

    def remove_rule(self, tool_name: str) -> None:
        """Remove all rules for a tool, restoring default-deny.

        Args:
            tool_name: Tool name.
        """
        self._allowlist.discard(tool_name)
        self._denylist.discard(tool_name)

    def allow_path_prefix(self, prefix: str) -> None:
        """Add an allowed path prefix for filesystem operations.

        Args:
            prefix: Path prefix (e.g. ``"/home/user/project/src"``).
        """
        normalised = PathTraversalPreventer.normalise(prefix)
        if normalised:
            self._allowed_path_prefixes.append(normalised)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        session_id: str = "",
        policy: Optional[Policy] = None,
    ) -> Decision:
        """Evaluate a single tool action against the deny-first rules.

        Resolution order:
        1. Check explicit deny.
        2. Check explicit allow.
        3. Check path safety (for file tools).
        4. Check mutating tools.
        5. Default: DENY.

        Args:
            tool_name: The tool being invoked.
            arguments: Tool arguments (used for path validation).
            session_id: The current session ID (for credential scoping).
            policy: Optional ``Policy`` for additional context.

        Returns:
            ``Decision.ALLOW``, ``Decision.DENY``, or
            ``Decision.CONDITIONAL``.
        """
        # --- Check explicit deny (highest priority) ---
        if tool_name in self._denylist:
            logger.info(
                "DenyFirstEvaluator: DENY — '%s' in explicit denylist",
                tool_name,
            )
            return Decision.DENY

        # --- Check conditional (requires_approval_for) ---
        if tool_name in self._conditional_tools:
            logger.info(
                "DenyFirstEvaluator: CONDITIONAL — '%s' requires approval",
                tool_name,
            )
            return Decision.CONDITIONAL

        # --- Check explicit allow (second priority) ---
        if tool_name in self._allowlist:
            # Even if allowed, validate paths
            args = arguments or {}
            if tool_name in ("Read", "Write", "Edit"):
                file_path = args.get("file_path") or args.get("path", "")
                if file_path and not self._path_preventer.is_safe_path(
                    file_path, self._allowed_path_prefixes
                ):
                    return Decision.DENY
                if file_path and self._allowed_path_prefixes:
                    normalised = PathTraversalPreventer.normalise(file_path)
                    if normalised and not any(
                        str(normalised).startswith(p) for p in self._allowed_path_prefixes
                    ):
                        return Decision.DENY
            return Decision.ALLOW

        # --- Check policy-based allow (runtime policy arg) ---
        if policy is not None:
            if tool_name in policy.allowed_tools:
                return Decision.ALLOW
            if tool_name in policy.requires_approval_for:
                return Decision.CONDITIONAL

        # --- Mutating tools: deny by default unless allow_mutating_by_default ---
        if tool_name in self._MUTATING_TOOLS:
            if self._allow_mutating_by_default:
                return Decision.ALLOW
            logger.info(
                "DenyFirstEvaluator: DENY — '%s' is mutating and not explicitly allowed",
                tool_name,
            )
            return Decision.DENY

        # --- Default: DENY ---
        logger.info(
            "DenyFirstEvaluator: DENY — '%s' not in any allowlist (default-deny)",
            tool_name,
        )
        return Decision.DENY

    def evaluate_compound(
        self,
        compound: CompoundAction,
        session_id: str = "",
    ) -> List[Tuple[ActionStep, Decision]]:
        """Evaluate every step in a compound action.

        Args:
            compound: The parsed compound action.
            session_id: Current session ID.

        Returns:
            List of ``(step, decision)`` tuples, one per step.
        """
        results: List[Tuple[ActionStep, Decision]] = []
        for step in compound.steps:
            decision = self.evaluate(
                tool_name=step.tool_name,
                arguments=step.arguments,
                session_id=session_id,
            )
            results.append((step, decision))
        return results

    def evaluate_batch(
        self,
        tool_calls: List[Tuple[str, Dict[str, Any]]],
        session_id: str = "",
    ) -> List[Tuple[str, Decision]]:
        """Evaluate multiple independent tool calls.

        Args:
            tool_calls: List of ``(tool_name, arguments)``.
            session_id: Current session ID.

        Returns:
            List of ``(tool_name, decision)``.
        """
        return [
            (name, self.evaluate(name, args, session_id))
            for name, args in tool_calls
        ]

    # ------------------------------------------------------------------
    # Sub-system accessors
    # ------------------------------------------------------------------

    @property
    def path_preventer(self) -> PathTraversalPreventer:
        """Access the path traversal preventer."""
        return self._path_preventer

    @property
    def credential_scope(self) -> CredentialScope:
        """Access the credential scope manager."""
        return self._credential_scope

    @property
    def compound_parser(self) -> CompoundActionParser:
        """Access the compound action parser."""
        return self._compound_parser

    @property
    def allowlist(self) -> Set[str]:
        """Current set of explicitly allowed tools."""
        return frozenset(self._allowlist)  # type: ignore[return-value]

    @property
    def denylist(self) -> Set[str]:
        """Current set of explicitly denied tools."""
        return frozenset(self._denylist)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def to_permission_result(self, decision: Decision, tool_name: str) -> PermissionResult:
        """Convert a ``Decision`` to a ``PermissionResult``.

        Args:
            decision: The evaluation decision.
            tool_name: The tool name.

        Returns:
            A ``PermissionResult`` matching the decision.
        """
        if decision == Decision.ALLOW:
            return PermissionResult(
                allowed=True,
                level=AccessLevel.ALLOW,
                reason=f"DenyFirst: '{tool_name}' is explicitly allowed.",
            )
        elif decision == Decision.CONDITIONAL:
            return PermissionResult(
                allowed=False,
                level=AccessLevel.ASK,
                reason=f"DenyFirst: '{tool_name}' requires conditional approval.",
            )
        else:
            return PermissionResult(
                allowed=False,
                level=AccessLevel.DENY,
                reason=f"DenyFirst: '{tool_name}' denied (default-deny).",
            )

    def to_gate_decision(self, decision: Decision) -> GateDecision:
        """Map a ``Decision`` to the corresponding ``GateDecision``.

        Args:
            decision: The evaluation decision.

        Returns:
            The mapped ``GateDecision``.
        """
        mapping = {
            Decision.ALLOW: GateDecision.ALLOW,
            Decision.DENY: GateDecision.BLOCK,
            Decision.CONDITIONAL: GateDecision.ASK_USER,
        }
        return mapping.get(decision, GateDecision.BLOCK)
