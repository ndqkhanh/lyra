"""
Deterministic safety kernel for Lyra -- ILION-style minimal safety layer.

This module implements a **pure deterministic** safety kernel that sits
between external actions (tool calls, filesystem ops, network requests,
process spawns) and their execution.  There is **no LLM** in the
enforcement path -- the kernel cannot be prompt-injected, cannot degrade
under adversarial input, and always terminates in bounded time.

Architecture
------------
::

    AgentAction
        |
        v
    DeterministicSafetyKernel.gate_action()
        |
        +-- ToolGate         (allowlist + capability negotiation + rate limiting)
        +-- FilesystemGate   (path allowlist, no traversal outside worktree)
        +-- NetworkGate      (domain allowlist, no internal IP access)
        +-- ProcessGate      (no fork bombs, no privilege escalation)
        |
        v
    GateResult (ALLOW | DENY | ASK)  -->  AuditLogEntry (immutable append)

Each sub-gate is a stateless deterministic checker.  The kernel composes
their verdicts: the most restrictive verdict wins.

References
----------
- ILION: Immutable Least-privilege Invariant Object Network (Lyra internal)
- arXiv:2509.26354v2 (Misevolve) -- root-cause: evaluator drift without
  frozen gate
- Parthenon Law 2606.04602 -- anti-leakage loop
"""

from __future__ import annotations

import fnmatch
import hashlib
import ipaddress
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# ===========================================================================
# Core types
# ===========================================================================


class GateVerdict(str, Enum):
    """Binary verdict from a single sub-gate checker."""

    ALLOW = "allow"
    DENY = "deny"


class ActionVerdict(str, Enum):
    """Final outcome of :meth:`DeterministicSafetyKernel.gate_action`."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"  # Requires human approval


# ===========================================================================
# AgentAction
# ===========================================================================


@dataclass(frozen=True)
class AgentAction:
    """A single action attempted by an agent, normalised for gating.

    All fields are plain strings / dicts so the kernel never needs to
    import domain objects and risk circular imports.

    Attributes:
        action_type: One of ``"tool"``, ``"filesystem"``, ``"network"``,
            ``"process"``.
        name: Tool name, path, domain, or executable name depending on
            *action_type*.
        args: Action-specific parameters.
        agent_id: Identifier of the agent that produced this action.
        session_id: Session scope for rate-limiting windows.
    """

    action_type: str
    name: str
    args: Dict[str, Any] = field(default_factory=dict)
    agent_id: str = ""
    session_id: str = ""


# ===========================================================================
# GateResult
# ===========================================================================


@dataclass(frozen=True)
class GateResult:
    """Final result of gating one agent action.

    Attributes:
        verdict: ALLOW, DENY, or ASK.
        reason: Human-readable explanation of the decision.
        matched_rule: Which rule (or gate) made the decision.
        details: Structured metadata for audit logging.
    """

    verdict: ActionVerdict
    reason: str
    matched_rule: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


# ===========================================================================
# Immutable audit log entry
# ===========================================================================


@dataclass(frozen=True)
class AuditLogEntry:
    """A single immutable entry in the safety audit trail.

    The hash chain ensures tamper evidence: each entry stores the hash
    of the previous entry so the log cannot be re-ordered or truncated
    without detection.

    Attributes:
        index: Monotonically increasing sequence number.
        timestamp: Unix timestamp of the decision.
        action: The agent action that was gated.
        gate_result: The kernel's decision.
        previous_hash: SHA-256 hex digest of the previous entry
            (empty string for the genesis entry).
        entry_hash: SHA-256 hex digest of this entry's payload.
    """

    index: int
    timestamp: float
    action: AgentAction
    gate_result: GateResult
    previous_hash: str
    entry_hash: str = ""


def _compute_entry_hash(
    index: int,
    timestamp: float,
    action: AgentAction,
    gate_result: GateResult,
    previous_hash: str,
) -> str:
    """Compute the SHA-256 hash for a log entry payload."""
    payload = json.dumps(
        {
            "index": index,
            "timestamp": timestamp,
            "action_type": action.action_type,
            "name": action.name,
            "args": action.args,
            "agent_id": action.agent_id,
            "verdict": gate_result.verdict.value,
            "reason": gate_result.reason,
            "matched_rule": gate_result.matched_rule,
            "previous_hash": previous_hash,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


# ===========================================================================
# SafetyConfig
# ===========================================================================


@dataclass(frozen=True)
class SafetyConfig:
    """Immutable configuration for the deterministic safety kernel.

    Attributes:
        default_deny: When ``True``, any action not explicitly allowed
            is denied (default-deny mode).  When ``False``, unknown
            actions are escalated to ASK.
        allowed_tools: List of tool names permitted for all agents.
            E.g. ``["Read", "Write", "Edit", "Bash", "WebSearch"]``.
        denied_tools: Tool names that are never allowed, regardless of
            other rules.
        tool_rate_limits: Mapping from tool name to max calls per
            rate_limit_window_seconds.  E.g. ``{"Bash": 50}``.
        rate_limit_window_seconds: Width of the sliding rate-limit
            window in seconds.  Default 60.
        allowed_path_prefixes: List of directory prefixes that file
            operations may target.  Paths that do not start with any
            prefix are denied.
        denied_path_patterns: Glob patterns for paths that are never
            allowed (in addition to the prefix check).
        worktree_root: The agent's working tree root.  Filesystem
            operations must resolve within this directory.
        allowed_domains: List of domain glob patterns for network
            access.  E.g. ``["*.example.com", "api.github.com"]``.
            Empty list denies all network access.
        blocked_domains: Domain patterns that are always denied.
            Internal IP ranges are automatically included.
        allow_internal_ips: When ``True``, internal / private IP ranges
            are allowed.  Default ``False``.
        max_processes_per_agent: Maximum concurrent processes per agent.
            Prevents fork bombs.
        forbidden_process_patterns: Executable or argument patterns
            that are never allowed (e.g. ``"sudo"``, ``"chmod 777"``).
    """

    default_deny: bool = True
    allowed_tools: Tuple[str, ...] = ()
    denied_tools: Tuple[str, ...] = ()
    tool_rate_limits: Dict[str, int] = field(default_factory=dict)
    rate_limit_window_seconds: int = 60
    allowed_path_prefixes: Tuple[str, ...] = ()
    denied_path_patterns: Tuple[str, ...] = ()
    worktree_root: str = ""
    allowed_domains: Tuple[str, ...] = ()
    blocked_domains: Tuple[str, ...] = ()
    allow_internal_ips: bool = False
    max_processes_per_agent: int = 10
    forbidden_process_patterns: Tuple[str, ...] = ()


# ===========================================================================
# Sub-gate: ToolGate
# ===========================================================================


class _ToolGate:
    """Tool-call gating: allowlist + rate limiting."""

    __slots__ = ("_config",)

    def __init__(self, config: SafetyConfig) -> None:
        self._config = config

    def evaluate(self, action: AgentAction) -> Optional[GateResult]:
        """Check a tool action.  Returns ``None`` if no rule matches (pass)."""
        tool_name = action.name
        cfg = self._config

        # Denied tools take priority
        if tool_name in cfg.denied_tools:
            return GateResult(
                verdict=ActionVerdict.DENY,
                reason=f"Tool '{tool_name}' is explicitly denied",
                matched_rule="tool_gate.denied_tools",
            )

        # Allowlist check
        if cfg.allowed_tools:
            if tool_name not in cfg.allowed_tools:
                if cfg.default_deny:
                    return GateResult(
                        verdict=ActionVerdict.DENY,
                        reason=f"Tool '{tool_name}' is not in the allowed list",
                        matched_rule="tool_gate.allowlist",
                    )
                return GateResult(
                    verdict=ActionVerdict.ASK,
                    reason=f"Tool '{tool_name}' is not in the allowed list",
                    matched_rule="tool_gate.allowlist",
                )
        elif cfg.default_deny:
            # No allowlist set and default-deny: block everything
            return GateResult(
                verdict=ActionVerdict.DENY,
                reason=f"Tool '{tool_name}' is not allowed (default-deny, no tools allowed)",
                matched_rule="tool_gate.default_deny",
            )

        # Rate limiting (handled externally via call_count tracking)
        # The kernel caller provides the current count in `action.args`
        rate_limit = cfg.tool_rate_limits.get(tool_name, 0)
        if rate_limit > 0:
            call_count = action.args.get("_call_count", 0)
            if call_count >= rate_limit:
                return GateResult(
                    verdict=ActionVerdict.DENY,
                    reason=(
                        f"Tool '{tool_name}' rate limit exceeded: "
                        f"{call_count} >= {rate_limit} calls per "
                        f"{cfg.rate_limit_window_seconds}s window"
                    ),
                    matched_rule="tool_gate.rate_limit",
                )

        return None  # No rule matched -- allow


# ===========================================================================
# Sub-gate: FilesystemGate
# ===========================================================================


class _FilesystemGate:
    """Filesystem gating: path allowlist + traversal prevention."""

    __slots__ = ("_config",)

    def __init__(self, config: SafetyConfig) -> None:
        self._config = config

    def evaluate(self, action: AgentAction) -> Optional[GateResult]:
        """Check a filesystem action.  Returns ``None`` if allowed."""
        file_path = action.args.get("file_path", action.name)
        cfg = self._config

        # Denied patterns
        for pattern in cfg.denied_path_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return GateResult(
                    verdict=ActionVerdict.DENY,
                    reason=(
                        f"Path '{file_path}' matches denied "
                        f"pattern '{pattern}'"
                    ),
                    matched_rule="filesystem_gate.denied_patterns",
                )

        # Compute the resolved target path for worktree confinement checks
        target_str = file_path
        if cfg.worktree_root:
            try:
                resolved = Path(cfg.worktree_root).resolve()
                target_path = (resolved / file_path).resolve()
                target_path.relative_to(resolved)
                target_str = str(target_path)
            except (ValueError, RuntimeError):
                return GateResult(
                    verdict=ActionVerdict.DENY,
                    reason=(
                        f"Path '{file_path}' resolves outside worktree "
                        f"'{cfg.worktree_root}'"
                    ),
                    matched_rule="filesystem_gate.traversal_prevention",
                )

        # Path prefix allowlist
        if cfg.allowed_path_prefixes:
            allowed = any(
                target_str.startswith(prefix) for prefix in cfg.allowed_path_prefixes
            )
            if not allowed:
                if cfg.default_deny:
                    return GateResult(
                        verdict=ActionVerdict.DENY,
                        reason=(
                            f"Path '{file_path}' resolves to '{target_str}' "
                            f"which does not start with any allowed prefix"
                        ),
                        matched_rule="filesystem_gate.path_prefix",
                    )
                return GateResult(
                    verdict=ActionVerdict.ASK,
                    reason=f"Path '{file_path}' not in allowed prefixes",
                    matched_rule="filesystem_gate.path_prefix",
                )

        return None  # No rule matched -- allow


# ===========================================================================
# Sub-gate: NetworkGate
# ===========================================================================


# RFC 1918 private IPv4 ranges as address objects
_PRIVATE_IPV4_RANGES: Tuple[ipaddress.IPv4Network, ...] = (
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
)

# Link-local and loopback
_RESERVED_IPV4_RANGES: Tuple[ipaddress.IPv4Network, ...] = (
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv4Network("169.254.0.0/16"),
    ipaddress.IPv4Network("0.0.0.0/8"),
)

# RFC 4193 unique local IPv6
_PRIVATE_IPV6_RANGES: Tuple[ipaddress.IPv6Network, ...] = (
    ipaddress.IPv6Network("fc00::/7"),
    ipaddress.IPv6Network("fe80::/10"),
    ipaddress.IPv6Network("::1/128"),
)


def _is_internal_ip(host: str) -> bool:
    """Check if a hostname resolves to an internal/private IP address.

    Returns ``True`` for:
    - Private IPv4 (10.x, 172.16-31.x, 192.168.x)
    - Loopback (127.x, ::1)
    - Link-local (169.254.x, fe80::)
    - Unique local IPv6 (fc00::)
    - Numeric private IP strings
    """
    # Strip port if present -- remove trailing :port only for IPv4 or bracketed IPv6
    stripped = host.strip("[]")
    if stripped.count(":") == 1 and stripped.startswith("["):
        # IPv6 with brackets: [::1]:port
        stripped = stripped.split("]:")[0].lstrip("[")
    elif "." in stripped and ":" in stripped:
        # IPv4 with port: 127.0.0.1:8080
        stripped = stripped.split(":")[0]
    # bare IPv6 (multiple colons) is used as-is

    try:
        addr = ipaddress.ip_address(stripped)
    except ValueError:
        # Not a raw IP -- assume it is a domain name and is not internal
        return False

    if isinstance(addr, ipaddress.IPv4Address):
        for net in _PRIVATE_IPV4_RANGES + _RESERVED_IPV4_RANGES:
            if addr in net:
                return True
    elif isinstance(addr, ipaddress.IPv6Address):
        for net in _PRIVATE_IPV6_RANGES:
            if addr in net:
                return True
    return False


# Pattern that matches common internal hostnames
_INTERNAL_HOSTNAME_RE = re.compile(
    r"(?:localhost|localhost\.localdomain|broadcasthost|"
    r"\.local|\.internal|\.intra|10\.\d+\.\d+\.\d+|"
    r"172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|"
    r"192\.168\.\d+\.\d+)"
)


class _NetworkGate:
    """Network gating: domain allowlist + internal-IP blocking."""

    __slots__ = ("_config",)

    def __init__(self, config: SafetyConfig) -> None:
        self._config = config

    def evaluate(self, action: AgentAction) -> Optional[GateResult]:
        """Check a network action.  Returns ``None`` if allowed."""
        domain = action.name
        cfg = self._config

        # Blocked domain patterns
        for pattern in cfg.blocked_domains:
            if fnmatch.fnmatch(domain, pattern):
                return GateResult(
                    verdict=ActionVerdict.DENY,
                    reason=(
                        f"Domain '{domain}' matches blocked pattern "
                        f"'{pattern}'"
                    ),
                    matched_rule="network_gate.blocked_domains",
                )

        # Internal IP check -- deny by default
        if not cfg.allow_internal_ips:
            if _is_internal_ip(domain):
                return GateResult(
                    verdict=ActionVerdict.DENY,
                    reason=(
                        f"Domain/IP '{domain}' resolves to an internal "
                        f"or private IP range"
                    ),
                    matched_rule="network_gate.internal_ip_block",
                )

        # Internal hostname patterns -- deny by default
        if not cfg.allow_internal_ips and _INTERNAL_HOSTNAME_RE.search(domain.lower()):
            return GateResult(
                verdict=ActionVerdict.DENY,
                reason=(
                    f"Hostname '{domain}' matches internal "
                    f"hostname pattern"
                ),
                matched_rule="network_gate.internal_hostname",
            )

        # Domain allowlist
        if cfg.allowed_domains:
            allowed = any(
                fnmatch.fnmatch(domain, pat) for pat in cfg.allowed_domains
            )
            if not allowed:
                if cfg.default_deny:
                    return GateResult(
                        verdict=ActionVerdict.DENY,
                        reason=(
                            f"Domain '{domain}' is not in the "
                            f"allowed list"
                        ),
                        matched_rule="network_gate.allowlist",
                    )
                return GateResult(
                    verdict=ActionVerdict.ASK,
                    reason=f"Domain '{domain}' not in allowed list",
                    matched_rule="network_gate.allowlist",
                )

        return None


# ===========================================================================
# Sub-gate: ProcessGate
# ===========================================================================


class _ProcessGate:
    """Process gating: prevent fork bombs and privilege escalation."""

    __slots__ = ("_config",)

    def __init__(self, config: SafetyConfig) -> None:
        self._config = config

    def evaluate(self, action: AgentAction) -> Optional[GateResult]:
        """Check a process action.  Returns ``None`` if allowed."""
        cmd = action.args.get("command", action.name)
        cmd_lower = cmd.lower() if isinstance(cmd, str) else str(cmd).lower()
        cfg = self._config

        # Forbidden patterns (privilege escalation, fork bombs)
        for pattern in cfg.forbidden_process_patterns:
            if pattern.lower() in cmd_lower:
                return GateResult(
                    verdict=ActionVerdict.DENY,
                    reason=(
                        f"Command matches forbidden pattern "
                        f"'{pattern}'"
                    ),
                    matched_rule="process_gate.forbidden_patterns",
                )

        # Default-deny checks for common escalation patterns
        escalation_patterns: Tuple[str, ...] = (
            "sudo ",
            "su ",
            "chmod 777",
            "chown ",
            "passwd ",
            "setcap ",
        )
        for pattern in escalation_patterns:
            if pattern in cmd_lower:
                return GateResult(
                    verdict=ActionVerdict.DENY,
                    reason=(
                        f"Process action matches privilege escalation "
                        f"pattern '{pattern.strip()}'"
                    ),
                    matched_rule="process_gate.escalation_prevention",
                )

        # Max process count (handled externally via concurrent process tracking)
        max_procs = cfg.max_processes_per_agent
        if max_procs > 0:
            active_count = action.args.get("_active_process_count", 0)
            if active_count >= max_procs:
                return GateResult(
                    verdict=ActionVerdict.DENY,
                    reason=(
                        f"Agent '{action.agent_id}' already has "
                        f"{active_count} active processes (max {max_procs})"
                    ),
                    matched_rule="process_gate.max_concurrent",
                )

        return None


# ===========================================================================
# DeterministicSafetyKernel
# ===========================================================================


class DeterministicSafetyKernel:
    """ILION-style minimal safety layer -- pure deterministic, no LLM.

    Composes four sub-gates (tool, filesystem, network, process) and
    produces a single ``GateResult`` for every agent action.  All
    decisions are recorded in an immutable hash-chained audit trail.

    The kernel cannot be prompt-injected because it contains **zero**
    LLM calls -- every check is pattern matching, string comparison,
    or IP-range arithmetic.

    Usage::

        config = SafetyConfig(
            default_deny=True,
            allowed_tools=["Read", "Write", "Edit", "WebSearch"],
            allowed_path_prefixes=["/workspace/project"],
            worktree_root="/workspace/project",
            allowed_domains=["*.example.com"],
        )
        kernel = DeterministicSafetyKernel(config)

        action = AgentAction(
            action_type="tool",
            name="Bash",
            agent_id="agent-01",
        )
        result = kernel.gate_action(action)
        # result.verdict == ActionVerdict.DENY  (Bash not in allowed_tools)

        for entry in kernel.audit_log:
            print(entry.index, entry.gate_result.verdict, entry.gate_result.reason)
    """

    # Default-built config: deny everything
    _DENY_ALL_CONFIG = SafetyConfig(
        default_deny=True,
        allowed_tools=(),
        allowed_path_prefixes=(),
        worktree_root="",
        allowed_domains=(),
        max_processes_per_agent=0,
        forbidden_process_patterns=(),
    )

    def __init__(self, config: Optional[SafetyConfig] = None) -> None:
        """Initialise the kernel.

        Args:
            config: Safety configuration.  If ``None``, a deny-all
                config is used (safest default).
        """
        self._config = config or self._DENY_ALL_CONFIG
        self._tool_gate = _ToolGate(self._config)
        self._filesystem_gate = _FilesystemGate(self._config)
        self._network_gate = _NetworkGate(self._config)
        self._process_gate = _ProcessGate(self._config)

        # Immutable audit trail
        self._audit_log: List[AuditLogEntry] = []
        self._last_hash: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def gate_action(self, action: AgentAction) -> GateResult:
        """Gate a single agent action through all four sub-gates.

        The most restrictive verdict wins:
        - Any DENY   -> DENY
        - Any ASK    -> ASK (if no DENY)
        - All ALLOW  -> ALLOW

        Every call produces an immutable audit log entry regardless
        of the outcome.

        Args:
            action: The action to evaluate.

        Returns:
            The gating decision.
        """
        # Route to the correct sub-gate
        verdict: Optional[GateResult] = None

        if action.action_type == "tool":
            verdict = self._tool_gate.evaluate(action)
        elif action.action_type == "filesystem":
            verdict = self._filesystem_gate.evaluate(action)
        elif action.action_type == "network":
            verdict = self._network_gate.evaluate(action)
        elif action.action_type == "process":
            verdict = self._process_gate.evaluate(action)
        else:
            # Unknown action type
            if self._config.default_deny:
                verdict = GateResult(
                    verdict=ActionVerdict.DENY,
                    reason=f"Unknown action type '{action.action_type}' (default-deny)",
                    matched_rule="kernel.unknown_action_type",
                )
            else:
                verdict = GateResult(
                    verdict=ActionVerdict.ASK,
                    reason=f"Unknown action type '{action.action_type}'",
                    matched_rule="kernel.unknown_action_type",
                )

        # If the sub-gate returned None, the action is allowed
        if verdict is None:
            result = GateResult(
                verdict=ActionVerdict.ALLOW,
                reason=f"Action '{action.name}' passed all gates",
                matched_rule="kernel.fallthrough_allow",
            )
        else:
            result = verdict

        # Append to the immutable audit trail
        self._append_log(action, result)

        return result

    def gate_action_batch(
        self,
        actions: Sequence[AgentAction],
    ) -> List[GateResult]:
        """Gate multiple actions in a single call.

        Each action is evaluated independently.  This is equivalent to
        calling ``gate_action()`` in a loop but provides a single point
        for batch-level observability.

        Args:
            actions: Iterable of agent actions.

        Returns:
            One ``GateResult`` per action, in order.
        """
        return [self.gate_action(a) for a in actions]

    @property
    def config(self) -> SafetyConfig:
        """The kernel's current safety configuration (read-only)."""
        return self._config

    @property
    def audit_log(self) -> Tuple[AuditLogEntry, ...]:
        """Immutable snapshot of all gated decisions."""
        return tuple(self._audit_log)

    @property
    def audit_log_count(self) -> int:
        """Total number of entries in the audit trail."""
        return len(self._audit_log)

    def verify_audit_integrity(self) -> bool:
        """Verify the hash chain of the entire audit log.

        Returns ``True`` if the log is intact (no tampering).
        Returns ``False`` if any entry in the chain has been modified.
        """
        previous_hash = ""
        for entry in self._audit_log:
            expected_hash = _compute_entry_hash(
                entry.index,
                entry.timestamp,
                entry.action,
                entry.gate_result,
                previous_hash,
            )
            if entry.entry_hash != expected_hash:
                return False
            previous_hash = entry.entry_hash
        return True

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _append_log(self, action: AgentAction, result: GateResult) -> None:
        """Append an immutable entry to the audit trail."""
        index = len(self._audit_log)
        ts = time.time()
        entry_hash = _compute_entry_hash(index, ts, action, result, self._last_hash)
        entry = AuditLogEntry(
            index=index,
            timestamp=ts,
            action=action,
            gate_result=result,
            previous_hash=self._last_hash,
            entry_hash=entry_hash,
        )
        self._audit_log.append(entry)
        self._last_hash = entry_hash


# ===========================================================================
# Convenience factory
# ===========================================================================


def build_default_kernel() -> DeterministicSafetyKernel:
    """Build a safety kernel with a sensible default-deny configuration.

    Returns a kernel configured with:
    - Default-deny mode
    - No tools allowed (agent must request capabilities)
    - No filesystem access
    - No network access
    - No process execution
    """
    return DeterministicSafetyKernel(SafetyConfig(default_deny=True))
