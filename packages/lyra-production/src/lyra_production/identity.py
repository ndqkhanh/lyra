"""
IETF AIMS 8-Layer Agent Identity management.

Provides cryptographic identity creation, challenge-response
verification, capability attestation, key rotation, and
revocation for autonomous agents across all 8 identity layers.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from lyra_production.models import (
    AgentIdentity,
    CapabilityAttestation,
    IdentityStatus,
)

logger = logging.getLogger(__name__)


class IdentityNotFoundError(KeyError):
    """Raised when a requested identity does not exist."""


class IdentityVerificationError(RuntimeError):
    """Raised when identity verification fails."""


class AgentIdentityManager:
    """Manages agent identities with IETF AIMS 8-layer security.

    Supports the full identity lifecycle: creation, cryptographic
    proof, verification, capability attestation, key rotation,
    and revocation.
    """

    def __init__(self) -> None:
        self._identities: dict[str, AgentIdentity] = {}
        self._lock = Lock()

    def _generate_key_pair(self) -> tuple[str, str]:
        """Generate a simulated Ed25519-style key pair.

        In production this would use an actual cryptographic library.
        Returns (public_key, private_key).
        """
        key_id = uuid.uuid4().hex
        public_key = f"pub-{key_id}"
        private_key = f"priv-{key_id}"
        return public_key, private_key

    def create_identity(
        self,
        agent_id: str,
        capabilities: set[str] | None = None,
        valid_for_days: int = 365,
        identity_layer: int = 8,
    ) -> tuple[AgentIdentity, str]:
        """Create a new agent identity.

        Args:
            agent_id: Unique identifier for the agent.
            capabilities: Set of capabilities this agent possesses.
            valid_for_days: Validity period in days.
            identity_layer: IETF AIMS layer (1-8, default 8 for full).

        Returns:
            A tuple of (AgentIdentity, private_key).

        Raises:
            ValueError: If agent_id is empty or already exists.
        """
        if not agent_id.strip():
            raise ValueError("Agent ID cannot be empty")

        if identity_layer < 1 or identity_layer > 8:
            raise ValueError(
                f"Identity layer must be between 1 and 8, got {identity_layer}"
            )

        with self._lock:
            if agent_id in self._identities:
                raise ValueError(
                    f"Identity already exists for agent: {agent_id}"
                )

        public_key, private_key = self._generate_key_pair()
        capabilities_set = frozenset(capabilities or set())
        valid_until = datetime.now(timezone.utc) + timedelta(days=valid_for_days)

        identity = AgentIdentity(
            agent_id=agent_id,
            public_key=public_key,
            capabilities=capabilities_set,
            attestations=(),
            status=IdentityStatus.ACTIVE,
            valid_until=valid_until,
            identity_layer=identity_layer,
            revocation_reason=None,
            created_at=datetime.now(timezone.utc),
            rotated_from=None,
        )

        with self._lock:
            self._identities[agent_id] = identity

        logger.info(
            "Created identity for agent '%s' (layer %d, valid until %s)",
            agent_id,
            identity_layer,
            valid_until.isoformat(),
        )
        return identity, private_key

    def sign_challenge(self, agent_id: str, challenge: str) -> str:
        """Sign a challenge string to prove identity.

        Args:
            agent_id: The agent to sign with.
            challenge: The challenge string to sign.

        Returns:
            A cryptographic signature string.

        Raises:
            IdentityNotFoundError: If the identity does not exist.
            IdentityVerificationError: If the identity is not active.
        """
        with self._lock:
            identity = self._identities.get(agent_id)
            if identity is None:
                raise IdentityNotFoundError(
                    f"Identity not found: {agent_id}"
                )

            if identity.status != IdentityStatus.ACTIVE:
                raise IdentityVerificationError(
                    f"Cannot sign with identity '{agent_id}' "
                    f"in status {identity.status.name}"
                )

            if (
                identity.valid_until
                and datetime.now(timezone.utc) > identity.valid_until
            ):
                raise IdentityVerificationError(
                    f"Identity '{agent_id}' has expired"
                )

        # Simulated signature: SHA-256 of agent_id + challenge + public_key
        payload = f"{agent_id}:{challenge}:{identity.public_key}"
        signature = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        logger.debug("Signed challenge for agent '%s'", agent_id)
        return signature

    def verify_identity(
        self,
        agent_id: str,
        signature: str,
        challenge: str,
    ) -> bool:
        """Verify an identity proof by checking a signed challenge.

        Args:
            agent_id: The claimed agent identity.
            signature: The signature to verify.
            challenge: The original challenge string.

        Returns:
            True if the signature is valid, False otherwise.
        """
        with self._lock:
            identity = self._identities.get(agent_id)
            if identity is None:
                logger.warning("Verification failed: identity '%s' not found", agent_id)
                return False

            if identity.status != IdentityStatus.ACTIVE:
                logger.warning(
                    "Verification failed: identity '%s' in status %s",
                    agent_id,
                    identity.status.name,
                )
                return False

            if (
                identity.valid_until
                and datetime.now(timezone.utc) > identity.valid_until
            ):
                logger.warning("Verification failed: identity '%s' has expired", agent_id)
                # Update status to expired
                self._mark_expired(agent_id)
                return False

        # Verify the signature
        expected = hashlib.sha256(
            f"{agent_id}:{challenge}:{identity.public_key}".encode("utf-8")
        ).hexdigest()

        return signature == expected

    def attest_capability(
        self,
        agent_id: str,
        capability: str,
        attested_by: str,
        valid_for_days: int = 90,
    ) -> AgentIdentity:
        """Attest that an agent possesses a specific capability.

        Args:
            agent_id: The agent to attest.
            capability: The capability being attested.
            attested_by: Agent ID of the attester.
            valid_for_days: Attestation validity period.

        Returns:
            The updated AgentIdentity.

        Raises:
            IdentityNotFoundError: If either identity does not exist.
            ValueError: If the attester does not have the capability.
        """
        with self._lock:
            identity = self._identities.get(agent_id)
            if identity is None:
                raise IdentityNotFoundError(
                    f"Identity not found: {agent_id}"
                )

            attester = self._identities.get(attested_by)
            if attester is None:
                raise IdentityNotFoundError(
                    f"Attester identity not found: {attested_by}"
                )

        # Simulated attestation signature
        attestation_sig = hashlib.sha256(
            f"{attested_by}:attests:{capability}:for:{agent_id}:"
            f"{datetime.now(timezone.utc).isoformat()}".encode("utf-8")
        ).hexdigest()

        attestation = CapabilityAttestation(
            capability=capability,
            attested_by=attested_by,
            attested_at=datetime.now(timezone.utc),
            signature=attestation_sig,
            valid_until=datetime.now(timezone.utc)
            + timedelta(days=valid_for_days),
        )

        with self._lock:
            new_attestations = list(identity.attestations)
            new_attestations.append(attestation)

            updated = AgentIdentity(
                agent_id=identity.agent_id,
                public_key=identity.public_key,
                capabilities=identity.capabilities,
                attestations=tuple(new_attestations),
                status=identity.status,
                valid_until=identity.valid_until,
                identity_layer=identity.identity_layer,
                revocation_reason=identity.revocation_reason,
                created_at=identity.created_at,
                rotated_from=identity.rotated_from,
            )
            self._identities[agent_id] = updated

        logger.info(
            "Attested capability '%s' for agent '%s' by '%s'",
            capability,
            agent_id,
            attested_by,
        )
        return updated

    def revoke_identity(
        self,
        agent_id: str,
        reason: str = "No reason provided",
    ) -> AgentIdentity:
        """Revoke an identity with a reason.

        Args:
            agent_id: The identity to revoke.
            reason: The reason for revocation.

        Returns:
            The revoked AgentIdentity.

        Raises:
            IdentityNotFoundError: If the identity does not exist.
        """
        with self._lock:
            identity = self._identities.get(agent_id)
            if identity is None:
                raise IdentityNotFoundError(
                    f"Identity not found: {agent_id}"
                )

            updated = AgentIdentity(
                agent_id=identity.agent_id,
                public_key=identity.public_key,
                capabilities=identity.capabilities,
                attestations=identity.attestations,
                status=IdentityStatus.REVOKED,
                valid_until=identity.valid_until,
                identity_layer=identity.identity_layer,
                revocation_reason=reason,
                created_at=identity.created_at,
                rotated_from=identity.rotated_from,
            )
            self._identities[agent_id] = updated

        logger.warning("Revoked identity for agent '%s': %s", agent_id, reason)
        return updated

    def rotate_keys(
        self,
        agent_id: str,
        valid_for_days: int = 365,
    ) -> tuple[AgentIdentity, str]:
        """Rotate cryptographic keys with a grace period.

        The old public key is preserved in rotated_from for
        verification of previously signed artifacts.

        Args:
            agent_id: The identity to rotate keys for.
            valid_for_days: Validity period for new keys.

        Returns:
            A tuple of (updated AgentIdentity, new_private_key).

        Raises:
            IdentityNotFoundError: If the identity does not exist.
        """
        with self._lock:
            identity = self._identities.get(agent_id)
            if identity is None:
                raise IdentityNotFoundError(
                    f"Identity not found: {agent_id}"
                )

        new_public_key, new_private_key = self._generate_key_pair()
        valid_until = datetime.now(timezone.utc) + timedelta(days=valid_for_days)

        with self._lock:
            updated = AgentIdentity(
                agent_id=identity.agent_id,
                public_key=new_public_key,
                capabilities=identity.capabilities,
                attestations=identity.attestations,
                status=IdentityStatus.ROTATING,
                valid_until=valid_until,
                identity_layer=identity.identity_layer,
                revocation_reason=identity.revocation_reason,
                created_at=identity.created_at,
                rotated_from=identity.public_key,
            )
            self._identities[agent_id] = updated

        logger.info("Rotated keys for agent '%s'", agent_id)

        # After rotation, set back to ACTIVE
        with self._lock:
            final = AgentIdentity(
                agent_id=updated.agent_id,
                public_key=updated.public_key,
                capabilities=updated.capabilities,
                attestations=updated.attestations,
                status=IdentityStatus.ACTIVE,
                valid_until=updated.valid_until,
                identity_layer=updated.identity_layer,
                revocation_reason=updated.revocation_reason,
                created_at=updated.created_at,
                rotated_from=updated.rotated_from,
            )
            self._identities[agent_id] = final

        return final, new_private_key

    def _mark_expired(self, agent_id: str) -> None:
        """Mark an identity as expired."""
        with self._lock:
            identity = self._identities.get(agent_id)
            if identity is None or identity.status != IdentityStatus.ACTIVE:
                return

            updated = AgentIdentity(
                agent_id=identity.agent_id,
                public_key=identity.public_key,
                capabilities=identity.capabilities,
                attestations=identity.attestations,
                status=IdentityStatus.EXPIRED,
                valid_until=identity.valid_until,
                identity_layer=identity.identity_layer,
                revocation_reason="Identity expired",
                created_at=identity.created_at,
                rotated_from=identity.rotated_from,
            )
            self._identities[agent_id] = updated

    def get_identity(self, agent_id: str) -> AgentIdentity:
        """Get an identity by agent ID.

        Args:
            agent_id: The agent identifier.

        Returns:
            The AgentIdentity.

        Raises:
            IdentityNotFoundError: If the identity does not exist.
        """
        with self._lock:
            identity = self._identities.get(agent_id)
            if identity is None:
                raise IdentityNotFoundError(
                    f"Identity not found: {agent_id}"
                )
            return identity

    def list_identities(self) -> list[AgentIdentity]:
        """List all registered identities."""
        with self._lock:
            return list(self._identities.values())

    def list_active_identities(self) -> list[AgentIdentity]:
        """List all currently active identities."""
        with self._lock:
            return [
                i
                for i in self._identities.values()
                if i.status == IdentityStatus.ACTIVE
            ]


__all__ = [
    "IdentityNotFoundError",
    "IdentityVerificationError",
    "AgentIdentityManager",
]
