"""Zero-Trust Federation — cross-agent identity and authorization.

Implements zero-trust principles for multi-agent federation: every agent
authenticates, every action is authorized, no implicit trust between nodes.
Uses capability-based security with signed tokens for cross-agent operations.

Based on zero-trust architecture (NIST SP 800-207) adapted for agent swarms.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class FederationLevel(StrEnum):
    ISOLATED = "isolated"
    RESTRICTED = "restricted"
    STANDARD = "standard"
    ELEVATED = "elevated"


class AuthStatus(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(frozen=True)
class FederationIdentity:
    agent_id: str
    public_key_hash: str
    federation_level: FederationLevel
    registered_at: float
    last_seen: float


@dataclass(frozen=True)
class Capability:
    """A signed permission to perform an action."""

    capability_id: str
    issuer: str
    holder: str
    action: str
    resource: str
    issued_at: float
    expires_at: float
    max_uses: int
    use_count: int
    signature: str


@dataclass(frozen=True)
class AuthDecision:
    allowed: bool
    reason: str
    agent_id: str
    action: str
    status: AuthStatus


@dataclass
class FederationConfig:
    session_timeout_sec: float = 3600.0
    max_capability_depth: int = 3
    require_mtls: bool = False
    auto_revoke_on_timeout: bool = True


class FederationRegistry:
    """Registry of federated agent identities with trust levels."""

    def __init__(self) -> None:
        self._agents: dict[str, FederationIdentity] = {}
        self._revoked: set[str] = set()
        self._capabilities: dict[str, Capability] = {}

    def register(
        self,
        agent_id: str,
        public_key: str,
        level: FederationLevel = FederationLevel.STANDARD,
    ) -> FederationIdentity:
        key_hash = hashlib.sha256(public_key.encode()).hexdigest()[:16]
        identity = FederationIdentity(
            agent_id=agent_id,
            public_key_hash=key_hash,
            federation_level=level,
            registered_at=time.time(),
            last_seen=time.time(),
        )
        self._agents[agent_id] = identity
        return identity

    def revoke(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
        self._revoked.add(agent_id)

    def get_identity(self, agent_id: str) -> FederationIdentity | None:
        identity = self._agents.get(agent_id)
        if identity and agent_id not in self._revoked:
            return identity
        return None

    def heartbeat(self, agent_id: str) -> None:
        identity = self._agents.get(agent_id)
        if identity:
            self._agents[agent_id] = FederationIdentity(
                agent_id=identity.agent_id,
                public_key_hash=identity.public_key_hash,
                federation_level=identity.federation_level,
                registered_at=identity.registered_at,
                last_seen=time.time(),
            )

    @property
    def agent_count(self) -> int:
        return len(self._agents)


class ZeroTrustFederation:
    """Zero-trust federation gate for cross-agent operations.

    Every inter-agent action requires explicit authorization. No agent is
    trusted by default — trust is continuously verified through capability
    tokens, federation level checks, and session timeouts.
    """

    def __init__(self, config: FederationConfig | None = None) -> None:
        self.config = config or FederationConfig()
        self.registry = FederationRegistry()
        self._denial_count: int = 0
        self._allow_count: int = 0

    def authorize(
        self,
        agent_id: str,
        action: str,
        resource: str = "*",
    ) -> AuthDecision:
        """Authorize an agent to perform an action on a resource.

        Follows zero-trust principles: never trust, always verify.
        """
        identity = self.registry.get_identity(agent_id)
        if identity is None:
            self._denial_count += 1
            return AuthDecision(
                allowed=False,
                reason=f"Agent '{agent_id}' is not registered in the federation",
                agent_id=agent_id,
                action=action,
                status=AuthStatus.DENIED,
            )

        if agent_id in self.registry._revoked:
            self._denial_count += 1
            return AuthDecision(
                allowed=False,
                reason=f"Agent '{agent_id}' has been revoked",
                agent_id=agent_id,
                action=action,
                status=AuthStatus.REVOKED,
            )

        elapsed = time.time() - identity.last_seen
        if elapsed > self.config.session_timeout_sec:
            self._denial_count += 1
            return AuthDecision(
                allowed=False,
                reason=f"Agent '{agent_id}' session expired ({elapsed:.0f}s > {self.config.session_timeout_sec}s)",
                agent_id=agent_id,
                action=action,
                status=AuthStatus.EXPIRED,
            )

        # Level-based access control
        action_level = _required_level(action)
        if _level_rank(identity.federation_level) < _level_rank(action_level):
            self._denial_count += 1
            return AuthDecision(
                allowed=False,
                reason=f"Agent '{agent_id}' level {identity.federation_level.value} "
                       f"insufficient for {action} (requires {action_level.value})",
                agent_id=agent_id,
                action=action,
                status=AuthStatus.DENIED,
            )

        self.registry.heartbeat(agent_id)
        self._allow_count += 1
        return AuthDecision(
            allowed=True,
            reason=f"Agent '{agent_id}' authorized for {action}",
            agent_id=agent_id,
            action=action,
            status=AuthStatus.ALLOWED,
        )

    def issue_capability(
        self,
        issuer: str,
        holder: str,
        action: str,
        resource: str = "*",
        ttl_sec: float = 3600.0,
        max_uses: int = 1,
    ) -> Capability:
        """Issue a capability token to another agent."""
        now = time.time()
        cap_id = hashlib.sha256(
            f"{issuer}|{holder}|{action}|{resource}|{now}".encode()
        ).hexdigest()[:16]

        signature = hashlib.sha256(
            f"{cap_id}|{issuer}|{holder}|{action}|{resource}|{now}".encode()
        ).hexdigest()[:32]

        capability = Capability(
            capability_id=cap_id,
            issuer=issuer,
            holder=holder,
            action=action,
            resource=resource,
            issued_at=now,
            expires_at=now + ttl_sec,
            max_uses=max_uses,
            use_count=0,
            signature=signature,
        )
        self.registry._capabilities[cap_id] = capability
        return capability

    def verify_capability(self, capability_id: str) -> AuthDecision:
        """Verify a capability token before allowing an action."""
        cap = self.registry._capabilities.get(capability_id)
        if cap is None:
            return AuthDecision(
                allowed=False, reason="Unknown capability", agent_id="",
                action="", status=AuthStatus.DENIED,
            )

        if time.time() > cap.expires_at:
            return AuthDecision(
                allowed=False, reason="Capability expired",
                agent_id=cap.holder, action=cap.action, status=AuthStatus.EXPIRED,
            )

        if cap.use_count >= cap.max_uses:
            return AuthDecision(
                allowed=False, reason="Capability exhausted",
                agent_id=cap.holder, action=cap.action, status=AuthStatus.DENIED,
            )

        # Increment use count by replacing with updated capability
        updated = Capability(
            capability_id=cap.capability_id,
            issuer=cap.issuer,
            holder=cap.holder,
            action=cap.action,
            resource=cap.resource,
            issued_at=cap.issued_at,
            expires_at=cap.expires_at,
            max_uses=cap.max_uses,
            use_count=cap.use_count + 1,
            signature=cap.signature,
        )
        self.registry._capabilities[cap.capability_id] = updated

        return AuthDecision(
            allowed=True, reason="Capability verified",
            agent_id=cap.holder, action=cap.action, status=AuthStatus.ALLOWED,
        )

    def stats(self) -> dict:
        return {
            "agents": self.registry.agent_count,
            "allowed": self._allow_count,
            "denied": self._denial_count,
            "capabilities_issued": len(self.registry._capabilities),
            "denial_rate": round(
                self._denial_count / max(self._allow_count + self._denial_count, 1), 4
            ),
        }


def _required_level(action: str) -> FederationLevel:
    """Determine minimum federation level required for an action."""
    elevated_actions = {"deploy", "modify_config", "grant_capability", "modify_skills"}
    restricted_actions = {"read_metrics", "list_agents", "query_status"}

    if action in elevated_actions:
        return FederationLevel.ELEVATED
    if action in restricted_actions:
        return FederationLevel.RESTRICTED
    return FederationLevel.STANDARD


def _level_rank(level: FederationLevel) -> int:
    ranks = {
        FederationLevel.ISOLATED: 0,
        FederationLevel.RESTRICTED: 1,
        FederationLevel.STANDARD: 2,
        FederationLevel.ELEVATED: 3,
    }
    return ranks.get(level, 0)
