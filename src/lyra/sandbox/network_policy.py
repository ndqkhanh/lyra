"""Network isolation and traffic filtering for sandboxed environments."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4



class NetworkDirection(str, Enum):
    """Direction of network traffic."""

    INGRESS = "ingress"
    EGRESS = "egress"
    BOTH = "both"


class NetworkAction(str, Enum):
    """Action to apply to matching traffic."""

    ALLOW = "allow"
    DENY = "deny"
    LOG = "log"


class DefaultPolicy(str, Enum):
    """Default network behaviour when no rule matches."""

    DENY_ALL = "deny_all"
    ALLOW_LOOPBACK_ONLY = "allow_loopback_only"
    ALLOW_LIST = "allow_list"


class IsolationLevel(str, Enum):
    """Pre-defined network isolation levels."""

    FULL_ISOLATION = "full_isolation"
    LOOPBACK_ONLY = "loopback_only"
    RESTRICTED_NETWORK = "restricted_network"
    INTERNAL_NETWORK = "internal_network"


@dataclass(frozen=True)
class NetworkRule:
    """Single network access rule."""

    rule_id: str = field(default_factory=lambda: uuid4().hex[:12])
    direction: NetworkDirection = NetworkDirection.EGRESS
    action: NetworkAction = NetworkAction.DENY
    protocol: str = "tcp"
    port: int | None = None
    cidr: str | None = None
    domain: str | None = None


@dataclass(frozen=True)
class NetworkPolicy:
    """Complete network policy for a sandbox instance."""

    name: str
    default_action: DefaultPolicy = DefaultPolicy.DENY_ALL
    rules: tuple[NetworkRule, ...] = ()


# Pre-built network policies
AIR_GAPPED = NetworkPolicy(
    name="air_gapped",
    default_action=DefaultPolicy.DENY_ALL,
)

LOOPBACK_ONLY = NetworkPolicy(
    name="loopback_only",
    default_action=DefaultPolicy.DENY_ALL,
    rules=(
        NetworkRule(
            rule_id="allow_loopback",
            direction=NetworkDirection.BOTH,
            action=NetworkAction.ALLOW,
            cidr="127.0.0.0/8",
        ),
    ),
)

DEVELOPMENT = NetworkPolicy(
    name="development",
    default_action=DefaultPolicy.ALLOW_LIST,
    rules=(
        NetworkRule(
            rule_id="allow_loopback",
            direction=NetworkDirection.BOTH,
            action=NetworkAction.ALLOW,
            cidr="127.0.0.0/8",
        ),
        NetworkRule(
            rule_id="allow_dns",
            direction=NetworkDirection.EGRESS,
            action=NetworkAction.ALLOW,
            protocol="udp",
            port=53,
        ),
        NetworkRule(
            rule_id="allow_https",
            direction=NetworkDirection.EGRESS,
            action=NetworkAction.ALLOW,
            protocol="tcp",
            port=443,
        ),
    ),
)

UNRESTRICTED = NetworkPolicy(
    name="unrestricted",
    default_action=DefaultPolicy.ALLOW_LIST,
    rules=(),
)


class NetworkPolicyManager:
    """Manages network policies for sandboxed environments."""

    _policies: dict[str, NetworkPolicy] = {}

    @classmethod
    def apply_policy(cls, policy: NetworkPolicy) -> bool:
        """Register and activate a network policy."""
        cls._policies[policy.name] = policy
        return True

    @classmethod
    def check_connection(
        cls,
        source: str,
        destination: str,
        direction: NetworkDirection = NetworkDirection.EGRESS,
        port: int | None = None,
        protocol: str = "tcp",
    ) -> NetworkAction:
        """Evaluate whether a connection is allowed under the active policies."""
        for _name, policy in cls._policies.items():
            if policy.default_action == DefaultPolicy.DENY_ALL:
                for rule in policy.rules:
                    if rule.direction in (direction, NetworkDirection.BOTH):
                        if rule.action == NetworkAction.ALLOW:
                            if rule.cidr and _cidr_matches(rule.cidr, destination):
                                return NetworkAction.ALLOW
                            if rule.domain and rule.domain in destination:
                                return NetworkAction.ALLOW
                            if rule.port == port and rule.protocol == protocol:
                                return NetworkAction.ALLOW
                return NetworkAction.DENY
            if policy.default_action == DefaultPolicy.ALLOW_LIST:
                for rule in policy.rules:
                    if rule.direction in (direction, NetworkDirection.BOTH):
                        if rule.action == NetworkAction.DENY:
                            if rule.cidr and _cidr_matches(rule.cidr, destination):
                                return NetworkAction.DENY
                            if rule.port == port and rule.protocol == protocol:
                                return NetworkAction.DENY
                return NetworkAction.ALLOW
        return NetworkAction.ALLOW

    @classmethod
    def remove_policy(cls, name: str) -> bool:
        """Remove a previously registered policy."""
        return cls._policies.pop(name, None) is not None

    @classmethod
    def clear_policies(cls) -> None:
        """Remove all registered policies."""
        cls._policies.clear()

    @classmethod
    def get_isolation_level(cls) -> IsolationLevel:
        """Determine the current effective isolation level."""
        if not cls._policies:
            return IsolationLevel.FULL_ISOLATION
        names = list(cls._policies.keys())
        if any("unrestricted" in n for n in names):
            return IsolationLevel.INTERNAL_NETWORK
        if any("development" in n for n in names):
            return IsolationLevel.RESTRICTED_NETWORK
        if any("loopback" in n for n in names):
            return IsolationLevel.LOOPBACK_ONLY
        return IsolationLevel.FULL_ISOLATION


def _cidr_matches(cidr: str, address: str) -> bool:
    """Crude CIDR match for policy evaluation (non-exhaustive)."""
    if cidr == "0.0.0.0/0":
        return True
    if cidr == "127.0.0.0/8" and address.startswith("127."):
        return True
    if "/" in cidr:
        prefix = cidr.rsplit(".", 1)[0]
        return address.startswith(prefix)
    return cidr == address
