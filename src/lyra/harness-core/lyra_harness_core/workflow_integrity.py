"""Workflow Integrity Verification — P4-B5 (HIGH impact, MEDIUM effort).

Cryptographic signing of per-agent outputs to build a chain-of-trust across
multi-agent workflows. Each agent output is hashed and HMAC-signed; downstream
agents verify signatures before consuming results.

Uses HMAC-SHA256 (stdlib, no external deps) for lightweight signing. For
production-grade asymmetric signing, swap in Ed25519 or ECDSA.

See: plan-phase5-master-plan.md §P4-B5
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass, field


# --- Keys --------------------------------------------------------------------


def generate_key() -> str:
    """Generate a new random signing key (64 hex chars = 256 bits)."""
    return secrets.token_hex(32)


# --- Hashes ------------------------------------------------------------------


def hash_content(content: str) -> str:
    """Compute SHA-256 hash of arbitrary content.

    Returns hex-encoded digest.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# --- Signatures --------------------------------------------------------------


def sign(key: str, content: str) -> str:
    """Create an HMAC-SHA256 signature for content using the given key.

    Args:
        key: Secret signing key (hex string).
        content: The content to sign.

    Returns:
        Hex-encoded HMAC signature.
    """
    return hmac.new(
        key.encode("utf-8"),
        content.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify(key: str, content: str, signature: str) -> bool:
    """Verify that a signature is valid for the given content and key.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        key: Secret signing key (hex string).
        content: The content that was signed.
        signature: The claimed HMAC signature (hex string).

    Returns:
        True if the signature is valid.
    """
    expected = sign(key, content)
    return hmac.compare_digest(expected, signature)


# --- Agent attestations ------------------------------------------------------


@dataclass(frozen=True)
class Attestation:
    """A signed attestation from an agent about its output.

    Carries the agent's identity, the content hash, a signature, and an
    optional link to the previous attestation in the workflow chain.

    Attributes:
        attestation_id: Unique identifier for this attestation.
        agent_id: Which agent produced this output.
        content_hash: SHA-256 hash of the agent's output content.
        signature: HMAC-SHA256 signature over (agent_id + content_hash + prev_hash).
        prev_hash: Hash of the previous attestation in the chain (empty for first).
        timestamp: Unix timestamp when the attestation was created.
        metadata: Arbitrary additional data.
    """

    attestation_id: str
    agent_id: str
    content_hash: str
    signature: str
    prev_hash: str = ""
    timestamp: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        agent_id: str,
        content: str,
        key: str,
        prev_hash: str = "",
        metadata: dict[str, str] | None = None,
    ) -> Attestation:
        """Create a signed attestation for agent output.

        Args:
            agent_id: Identifier for the agent (e.g., "planner", "executor").
            content: The agent's output content.
            key: The agent's signing key.
            prev_hash: Hash of the previous attestation in the chain.
            metadata: Optional metadata.

        Returns:
            A new signed Attestation.
        """
        content_hash = hash_content(content)
        attestation_id = uuid.uuid4().hex[:12]

        # Sign: agent_id + content_hash + prev_hash
        sig_payload = f"{agent_id}:{content_hash}:{prev_hash}"
        signature = sign(key, sig_payload)

        return cls(
            attestation_id=attestation_id,
            agent_id=agent_id,
            content_hash=content_hash,
            signature=signature,
            prev_hash=prev_hash,
            timestamp=time.time(),
            metadata=metadata or {},
        )

    def verify(self, key: str) -> bool:
        """Verify this attestation's signature against the given key.

        Returns True if the signature is valid.
        """
        sig_payload = f"{self.agent_id}:{self.content_hash}:{self.prev_hash}"
        return verify(key, sig_payload, self.signature)

    def hash(self) -> str:
        """Compute a deterministic hash of this attestation (for chain linking)."""
        raw = f"{self.attestation_id}:{self.agent_id}:{self.content_hash}:{self.signature}:{self.prev_hash}"
        return hash_content(raw)


# --- Trust chain -------------------------------------------------------------


@dataclass
class TrustChain:
    """A chain of attestations forming a verifiable workflow trace.

    Each attestation links to the previous one via prev_hash, creating
    an append-only log of agent outputs. The chain can be verified
    end-to-end to detect tampering or missing links.
    """

    attestations: list[Attestation] = field(default_factory=list)

    def append(
        self,
        agent_id: str,
        content: str,
        key: str,
        metadata: dict[str, str] | None = None,
    ) -> Attestation:
        """Append a new attestation to the chain.

        Args:
            agent_id: The agent producing this output.
            content: The agent's output content.
            key: The agent's signing key.
            metadata: Optional metadata.

        Returns:
            The newly created Attestation, now appended to the chain.
        """
        prev_hash = self.attestations[-1].hash() if self.attestations else ""
        att = Attestation.create(
            agent_id=agent_id,
            content=content,
            key=key,
            prev_hash=prev_hash,
            metadata=metadata,
        )
        self.attestations.append(att)
        return att

    def verify_all(self, keys: dict[str, str]) -> ChainVerification:
        """Verify every attestation in the chain.

        Args:
            keys: Mapping of agent_id → signing key.

        Returns:
            A ChainVerification with per-attestation and chain-level results.
        """
        results: list[AttestationVerdict] = []
        prev_hash = ""

        for att in self.attestations:
            key = keys.get(att.agent_id, "")

            # Check chain link integrity
            link_ok = att.prev_hash == prev_hash

            # Check signature
            sig_ok = att.verify(key) if key else False

            results.append(
                AttestationVerdict(
                    attestation_id=att.attestation_id,
                    agent_id=att.agent_id,
                    signature_valid=sig_ok,
                    chain_link_valid=link_ok,
                )
            )

            prev_hash = att.hash()

        all_ok = all(r.signature_valid and r.chain_link_valid for r in results)
        return ChainVerification(
            attestations=results,
            all_valid=all_ok,
            total=len(results),
            valid_count=sum(1 for r in results if r.signature_valid and r.chain_link_valid),
        )

    def last_hash(self) -> str:
        """Return the hash of the most recent attestation (empty if empty)."""
        if not self.attestations:
            return ""
        return self.attestations[-1].hash()

    def __len__(self) -> int:
        return len(self.attestations)


@dataclass(frozen=True)
class AttestationVerdict:
    """Verification result for a single attestation."""

    attestation_id: str
    agent_id: str
    signature_valid: bool
    chain_link_valid: bool

    @property
    def is_valid(self) -> bool:
        return self.signature_valid and self.chain_link_valid


@dataclass(frozen=True)
class ChainVerification:
    """Aggregate verification result for a full trust chain."""

    attestations: list[AttestationVerdict]
    all_valid: bool
    total: int
    valid_count: int


# --- Multi-agent workflow signing --------------------------------------------


@dataclass
class WorkflowIntegrity:
    """Manages signing keys and trust chains for a multi-agent workflow.

    Each agent gets its own signing key. The trust chain records every
    agent output in order, with cryptographic links between them.

    Usage::

        wi = WorkflowIntegrity()
        wi.register_agent("planner")
        wi.register_agent("executor")

        wi.attest("planner", "Decompose task into 3 subtasks")
        wi.attest("executor", "Implemented subtask 1")
        wi.attest("executor", "Implemented subtask 2")

        result = wi.verify()
        assert result.all_valid
    """

    def __init__(self) -> None:
        self._keys: dict[str, str] = {}          # agent_id → key
        self._chain = TrustChain()

    def register_agent(self, agent_id: str) -> str:
        """Register a new agent with a randomly generated key.

        Args:
            agent_id: Unique agent identifier.

        Returns:
            The generated signing key (store it securely).

        Raises:
            ValueError: If the agent_id is already registered.
        """
        if agent_id in self._keys:
            raise ValueError(f"agent already registered: {agent_id}")
        key = generate_key()
        self._keys[agent_id] = key
        return key

    def register_agent_with_key(self, agent_id: str, key: str) -> None:
        """Register an agent with a pre-existing key."""
        if agent_id in self._keys:
            raise ValueError(f"agent already registered: {agent_id}")
        self._keys[agent_id] = key

    def attest(
        self,
        agent_id: str,
        content: str,
        metadata: dict[str, str] | None = None,
    ) -> Attestation:
        """Create a signed attestation and append it to the chain.

        Args:
            agent_id: The agent producing this output.
            content: The agent's output content.
            metadata: Optional metadata.

        Returns:
            The new Attestation.

        Raises:
            ValueError: If the agent is not registered.
        """
        key = self._keys.get(agent_id)
        if key is None:
            raise ValueError(f"unknown agent: {agent_id}")
        return self._chain.append(agent_id, content, key, metadata)

    def verify(self) -> ChainVerification:
        """Verify the entire trust chain.

        Returns:
            A ChainVerification with per-attestation results.
        """
        return self._chain.verify_all(self._keys)

    def verify_content(self, agent_id: str, content: str, attestation: Attestation) -> bool:
        """Verify that content matches a specific attestation.

        Checks both signature validity and content hash match.
        """
        key = self._keys.get(agent_id, "")
        if not key or not attestation.verify(key):
            return False
        return hash_content(content) == attestation.content_hash

    @property
    def chain(self) -> TrustChain:
        return self._chain

    @property
    def agent_ids(self) -> list[str]:
        return list(self._keys.keys())

    def key_for(self, agent_id: str) -> str | None:
        """Get the signing key for an agent (None if not registered)."""
        return self._keys.get(agent_id)


__all__ = [
    "Attestation",
    "AttestationVerdict",
    "ChainVerification",
    "TrustChain",
    "WorkflowIntegrity",
    "generate_key",
    "hash_content",
    "sign",
    "verify",
]
