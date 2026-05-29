from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from .exceptions import PrivilegeError
from .governance_engine import ActionType


class PrivilegeLevel(Enum):
    NONE = 0
    READ_ONLY = 1
    RESTRICTED = 2
    STANDARD = 3
    ELEVATED = 4
    FULL = 5


@dataclass(frozen=True)
class Privilege:
    agent_id: str
    action_type: ActionType
    target_pattern: str
    granted: bool
    granted_by: str
    expires_at: datetime | None = None


@dataclass(frozen=True)
class AccessProfile:
    agent_id: str
    privilege_level: PrivilegeLevel
    granted_privileges: tuple[Privilege, ...] = ()
    denial_history: tuple[Privilege, ...] = ()
    trust_score: float = 0.5


@dataclass(frozen=True)
class LeastPrivilegeConfig:
    max_temp_duration: int = 3600
    auto_revoke_enabled: bool = True
    trust_threshold: float = 0.3


_LEVEL_REQUIRED_ACTIONS: dict[ActionType, PrivilegeLevel] = {
    ActionType.READ_FILE: PrivilegeLevel.READ_ONLY,
    ActionType.WRITE_FILE: PrivilegeLevel.RESTRICTED,
    ActionType.EXECUTE: PrivilegeLevel.STANDARD,
    ActionType.NETWORK: PrivilegeLevel.STANDARD,
    ActionType.SHELL: PrivilegeLevel.ELEVATED,
    ActionType.DELETE: PrivilegeLevel.ELEVATED,
    ActionType.UPLOAD: PrivilegeLevel.RESTRICTED,
    ActionType.API_CALL: PrivilegeLevel.STANDARD,
    ActionType.SEND_MESSAGE: PrivilegeLevel.READ_ONLY,
}


class LeastPrivilegeEngine:
    """Layer 2: Learned least-privilege access control for agent actions.

    Maintains per-agent access profiles, trust scores, and temporary privilege grants.
    """

    def __init__(self, config: LeastPrivilegeConfig | None = None) -> None:
        self._config = config or LeastPrivilegeConfig()
        self._privileges: dict[str, Privilege] = {}
        self._profiles: dict[str, AccessProfile] = {}
        self._trust_history: dict[str, tuple[int, int]] = {}

    @property
    def config(self) -> LeastPrivilegeConfig:
        return self._config

    def get_profile(self, agent_id: str) -> AccessProfile | None:
        return self._profiles.get(agent_id)

    def _ensure_profile(self, agent_id: str) -> AccessProfile:
        if agent_id not in self._profiles:
            self._profiles[agent_id] = AccessProfile(
                agent_id=agent_id,
                privilege_level=PrivilegeLevel.READ_ONLY,
            )
        return self._profiles[agent_id]

    def request_privilege(self, agent_id: str, action_type: ActionType, target: str) -> bool:
        """Check if an agent has the required privilege level for this action.

        Returns True if the agent's current privilege level is sufficient.
        """
        profile = self._ensure_profile(agent_id)
        required = _LEVEL_REQUIRED_ACTIONS.get(action_type, PrivilegeLevel.NONE)

        # Check for explicit matching privilege
        for priv in profile.granted_privileges:
            if priv.action_type == action_type and priv.granted:
                if priv.expires_at is not None and priv.expires_at < datetime.now(timezone.utc):
                    continue
                if self._target_matches(priv.target_pattern, target):
                    return True

        # Check level-based access
        if profile.privilege_level.value >= required.value:
            return True

        # Log denial to history
        denied_priv = Privilege(
            agent_id=agent_id,
            action_type=action_type,
            target_pattern=target,
            granted=False,
            granted_by="system",
        )
        self._profiles[agent_id] = AccessProfile(
            agent_id=agent_id,
            privilege_level=profile.privilege_level,
            granted_privileges=profile.granted_privileges,
            denial_history=profile.denial_history + (denied_priv,),
            trust_score=profile.trust_score,
        )
        return False

    def grant_temporary(self, agent_id: str, action_type: ActionType, target_pattern: str, duration: int) -> Privilege:
        """Grant a temporary privilege to an agent."""
        if duration > self._config.max_temp_duration:
            raise PrivilegeError(
                f"Duration {duration}s exceeds max temporary duration "
                f"{self._config.max_temp_duration}s"
            )

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=duration)
        priv_id = f"temp-{agent_id}-{action_type.value}-{expires_at.timestamp()}"

        privilege = Privilege(
            agent_id=agent_id,
            action_type=action_type,
            target_pattern=target_pattern,
            granted=True,
            granted_by="system",
            expires_at=expires_at,
        )

        self._privileges[priv_id] = privilege
        profile = self._ensure_profile(agent_id)
        self._profiles[agent_id] = AccessProfile(
            agent_id=agent_id,
            privilege_level=profile.privilege_level,
            granted_privileges=profile.granted_privileges + (privilege,),
            denial_history=profile.denial_history,
            trust_score=profile.trust_score,
        )
        return privilege

    def revoke(self, privilege_id: str) -> bool:
        """Revoke a privilege by its key. Returns True if found and revoked."""
        if privilege_id not in self._privileges:
            return False

        revoked = self._privileges.pop(privilege_id)
        profile = self._profiles.get(revoked.agent_id)
        if profile is not None:
            self._profiles[revoked.agent_id] = AccessProfile(
                agent_id=revoked.agent_id,
                privilege_level=profile.privilege_level,
                granted_privileges=tuple(
                    p for p in profile.granted_privileges
                    if not (p.action_type == revoked.action_type and p.target_pattern == revoked.target_pattern)
                ),
                denial_history=profile.denial_history,
                trust_score=profile.trust_score,
            )
        return True

    def escalation_required(self, current_level: PrivilegeLevel, requested_action: ActionType) -> bool:
        """Determine if escalation is needed for the requested action."""
        required = _LEVEL_REQUIRED_ACTIONS.get(requested_action, PrivilegeLevel.NONE)
        return current_level.value < required.value

    def update_trust_score(self, agent_id: str, outcome: bool) -> float:
        """Update trust score using Bayesian estimation (beta-binomial model).

        Args:
            agent_id: The agent to update.
            outcome: True for positive outcome, False for negative.

        Returns:
            The updated trust score.
        """
        successes, failures = self._trust_history.get(agent_id, (0, 0))
        if outcome:
            successes += 1
        else:
            failures += 1
        self._trust_history[agent_id] = (successes, failures)

        # Beta-binomial: uniform prior Beta(1, 1), posterior mean
        alpha = 1.0 + successes
        beta = 1.0 + failures
        trust_score = alpha / (alpha + beta)

        profile = self._ensure_profile(agent_id)
        self._profiles[agent_id] = AccessProfile(
            agent_id=agent_id,
            privilege_level=profile.privilege_level,
            granted_privileges=profile.granted_privileges,
            denial_history=profile.denial_history,
            trust_score=round(trust_score, 4),
        )
        return round(trust_score, 4)

    def _target_matches(self, pattern: str, target: str) -> bool:
        """Check if a target matches a pattern (simple glob-like matching)."""
        import fnmatch
        return fnmatch.fnmatch(target, pattern)
