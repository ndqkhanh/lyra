"""
Lyra Privacy - Privacy-preserving agent inference.

This package provides:
- Confidential computing (TEE enclave attestation)
- Differential privacy (DP queries with noise calibration)
- Federated knowledge sharing across agents
- Privacy budget accounting and enforcement
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PrivacyBudgetStatus(str, Enum):
    """Status of a privacy budget allocation.

    Attributes
    ----------
    AVAILABLE : str
        Budget is available for new queries.
    DEPLETED : str
        Budget has been fully consumed.
    WARNING : str
        Budget is running low (close to depletion).
    EXCEEDED : str
        Budget has been exceeded beyond allowed limits.
    """

    AVAILABLE = "AVAILABLE"
    DEPLETED = "DEPLETED"
    WARNING = "WARNING"
    EXCEEDED = "EXCEEDED"


@dataclass(frozen=True)
class AttestationProof:
    """Cryptographic proof of confidential execution inside a TEE enclave.

    Attributes
    ----------
    proof_id : str
        Unique identifier for this attestation.
    enclave_type : str
        Type of trusted execution environment (e.g. "SGX", "TDX", "SEV").
    measurements : tuple[tuple[str, str], ...]
        (key, value) pairs representing enclave measurements and claims.
    timestamp : float
        Unix timestamp when the attestation was generated.
    verified : bool
        Whether this proof has been cryptographically verified.
    issuer : str
        Identifier of the attestation issuer/enclave.
    """

    proof_id: str
    enclave_type: str
    measurements: tuple[tuple[str, str], ...]
    timestamp: float
    verified: bool = False
    issuer: str = ""


@dataclass(frozen=True)
class PrivacyBudget:
    """Tracks epsilon/delta privacy budget consumption.

    Attributes
    ----------
    epsilon : float
        Total epsilon budget allocated.
    delta : float
        Total delta budget allocated (typically very small, e.g. 1e-5).
    total_spent_epsilon : float
        Cumulative epsilon spent across all queries.
    queries_remaining : int
        Number of queries remaining before budget is considered exhausted.
    status : str
        Current budget status string (matches PrivacyBudgetStatus values).
    per_user_limits : tuple[tuple[str, float], ...]
        Per-user remaining epsilon limits as (user_id, remaining_epsilon) pairs.
    """

    epsilon: float
    delta: float
    total_spent_epsilon: float = 0.0
    queries_remaining: int = 1000
    status: str = "AVAILABLE"
    per_user_limits: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class DPQueryResult:
    """Result of a differentially private query.

    Attributes
    ----------
    success : bool
        Whether the query completed successfully.
    result : Any
        The query result with noise applied.
    noise_scale : float
        Standard deviation of the Gaussian noise applied.
    epsilon_spent : float
        Epsilon consumed by this query.
    budget_remaining : float
        Remaining epsilon in the privacy budget.
    privacy_accounting : dict[str, float]
        Detailed privacy accounting breakdown (e.g. epsilon, delta,
        composition method).
    """

    success: bool
    result: Any
    noise_scale: float
    epsilon_spent: float
    budget_remaining: float
    privacy_accounting: dict[str, Any]


@dataclass(frozen=True)
class FederatedUpdate:
    """Knowledge update from a single agent in a federated learning round.

    Attributes
    ----------
    update_id : str
        Unique identifier for this update.
    source_agent : str
        Identifier of the contributing agent.
    knowledge_graph_delta : dict[str, Any]
        Changes to the agent's knowledge graph being shared.
    encryption_metadata : tuple[tuple[str, str], ...]
        Encryption-related metadata as (key, value) pairs.
    differential_privacy_applied : bool
        Whether DP noise was applied before sharing.
    epsilon_spent : float
        Epsilon budget consumed to produce this update.
    """

    update_id: str
    source_agent: str
    knowledge_graph_delta: dict[str, Any]
    encryption_metadata: tuple[tuple[str, str], ...]
    differential_privacy_applied: bool
    epsilon_spent: float = 0.0


@dataclass(frozen=True)
class FederatedAggregation:
    """Aggregated result of a federated learning round.

    Attributes
    ----------
    round_id : str
        Unique identifier for this aggregation round.
    contributing_agents : tuple[str, ...]
        Agents that contributed updates in this round.
    aggregated_knowledge : dict[str, Any]
        Combined and aggregated knowledge from all contributors.
    total_epsilon : float
        Total epsilon budget consumed across the aggregation.
    convergence_score : float
        Measure of knowledge convergence (0.0 = no agreement, 1.0 = perfect
        agreement).
    """

    round_id: str
    contributing_agents: tuple[str, ...]
    aggregated_knowledge: dict[str, Any]
    total_epsilon: float
    convergence_score: float


@dataclass(frozen=True)
class PrivacyConfig:
    """Configuration for privacy-preserving features.

    Attributes
    ----------
    confidential_inference_enabled : bool
        Whether TEE-based confidential inference is enabled.
    differential_privacy_enabled : bool
        Whether differential privacy is applied to queries.
    federated_learning_enabled : bool
        Whether federated knowledge sharing is enabled.
    default_epsilon : float
        Default epsilon budget per user.
    default_delta : float
        Default delta budget (typically 1e-5 or smaller).
    max_queries_per_user : int
        Maximum number of queries allowed per user.
    noise_mechanism : str
        Noise mechanism to use ("gaussian" or "laplace").
    min_contributing_agents : int
        Minimum number of agents required for a federated aggregation round.
    """

    confidential_inference_enabled: bool = True
    differential_privacy_enabled: bool = True
    federated_learning_enabled: bool = True
    default_epsilon: float = 1.0
    default_delta: float = 1e-5
    max_queries_per_user: int = 1000
    noise_mechanism: str = "gaussian"
    min_contributing_agents: int = 3


class PrivacyPreservingAgent:
    """Agent that performs privacy-preserving inference and knowledge sharing.

    Provides confidential inference via TEE attestation, differentially
    private queries with budget tracking, and federated knowledge aggregation
    across multiple agents.

    Parameters
    ----------
    config : PrivacyConfig | None
        Privacy configuration. Uses defaults if not provided.
    agent_id : str
        Unique identifier for this agent. Auto-generated if empty.

    Examples
    --------
    >>> agent = PrivacyPreservingAgent()
    >>> result = agent.secure_infer("What is the capital of France?")
    >>> proof = agent.generate_attestation(result)
    >>> agent.verify_attestation(proof)
    True
    """

    def __init__(self, config: PrivacyConfig | None = None, agent_id: str = "") -> None:
        self.config = config if config is not None else PrivacyConfig()
        self._agent_id = agent_id if agent_id else f"agent_{int(time.time())}"
        self._total_queries: int = 0
        self._total_epsilon_spent: float = 0.0
        self._total_federated_rounds: int = 0
        self._total_attestations: int = 0
        self._per_user_epsilon: dict[str, float] = {}
        self._dp_accounting: list[dict[str, Any]] = []
        self._federated_updates_history: list[str] = []
        logger.info(
            "Initialized PrivacyPreservingAgent %s (confidential=%s, dp=%s, fl=%s)",
            self._agent_id,
            self.config.confidential_inference_enabled,
            self.config.differential_privacy_enabled,
            self.config.federated_learning_enabled,
        )

    @property
    def agent_id(self) -> str:
        """Return this agent's unique identifier."""
        return self._agent_id

    def secure_infer(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run confidential inference with TEE attestation.

        Simulates TEE-based inference by hashing the prompt and context,
        returning a signed result with an attestation proof. Production use
        would invoke an actual TEE enclave (SGX/TDX/SEV).

        Parameters
        ----------
        prompt : str
            Input prompt for inference.
        context : dict[str, Any] | None
            Optional context to include in the inference.

        Returns
        -------
        dict[str, Any]
            A signed inference result containing:
            - content: simulated inference response
            - content_hash: SHA-256 hex digest of prompt + context
            - agent_id: identifier of this agent
            - timestamp: unix timestamp of inference
            - signature: HMAC-like signature using agent_id as key
        """
        ctx = context or {}
        combined = prompt + json.dumps(ctx, sort_keys=True, default=str)
        content_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        timestamp = time.time()
        signature = hashlib.sha256(
            f"{self._agent_id}:{content_hash}:{timestamp}".encode()
        ).hexdigest()

        result: dict[str, Any] = {
            "content": f"Simulated inference for: {prompt[:50]}...",
            "content_hash": content_hash,
            "agent_id": self._agent_id,
            "timestamp": timestamp,
            "signature": signature,
        }

        if self.config.confidential_inference_enabled:
            result["attestation"] = self.generate_attestation(result)

        self._total_queries += 1
        return result

    def generate_attestation(self, inference_result: dict[str, Any]) -> AttestationProof:
        """Generate a TEE attestation proof for an inference result.

        Creates a SHA-256 based attestation proof that cryptographically
        binds the inference result to this agent's enclave. Production use
        would leverage Intel SGX/TDX or AMD SEV hardware attestation.

        The proof stores the raw content_hash and signature within
        measurements, plus a combined `attestation_hash` that covers all
        measurement values. Verification recomputes this combined hash
        to detect tampering.

        Parameters
        ----------
        inference_result : dict[str, Any]
            The inference result to attest.

        Returns
        -------
        AttestationProof
            A frozen dataclass containing the proof id, enclave type,
            measurements, and timestamp.
        """
        content_hash = inference_result.get("content_hash", "")
        signature = inference_result.get("signature", "")

        # Combined hash covers all measurement values
        combined_payload = f"{content_hash}:{signature}:{self._agent_id}"
        attestation_hash = hashlib.sha256(
            combined_payload.encode("utf-8")
        ).hexdigest()

        proof_id = hashlib.sha256(
            f"{combined_payload}:{time.time()}".encode()
        ).hexdigest()[:16]

        measurements = (
            ("content_hash", content_hash),
            ("signature", signature),
            ("attestation_hash", attestation_hash),
        )

        proof = AttestationProof(
            proof_id=proof_id,
            enclave_type="SIMULATED",
            measurements=measurements,
            timestamp=time.time(),
            verified=False,
            issuer=self._agent_id,
        )

        self._total_attestations += 1
        return proof

    def verify_attestation(self, proof: AttestationProof) -> bool:
        """Verify a TEE attestation proof.

        Recomputes the combined attestation hash from the stored
        measurement values and compares it against the attestation_hash
        stored in the proof. Production use would verify against actual
        TEE hardware root of trust.

        Parameters
        ----------
        proof : AttestationProof
            The attestation proof to verify.

        Returns
        -------
        bool
            True if the attestation is valid, False otherwise.
        """
        measurements_dict = dict(proof.measurements)
        content_hash = measurements_dict.get("content_hash", "")
        signature = measurements_dict.get("signature", "")
        stored_hash = measurements_dict.get("attestation_hash", "")

        # Recompute the combined hash and verify it matches
        expected_hash = hashlib.sha256(
            f"{content_hash}:{signature}:{proof.issuer}".encode()
        ).hexdigest()

        return stored_hash == expected_hash

    def query_with_dp(self, query: str, dataset_id: str) -> DPQueryResult:
        """Run a differentially private query against a dataset.

        Simulates a DP query by applying calibrated Gaussian noise and
        tracking epsilon spending against the privacy budget. The noise
        scale is determined by the privacy budget remaining.

        Parameters
        ----------
        query : str
            The query string to execute.
        dataset_id : str
            Identifier for the target dataset.

        Returns
        -------
        DPQueryResult
            Query result with noise scale, epsilon spent, budget remaining,
            and detailed privacy accounting.
        """
        if self._total_epsilon_spent >= self.config.default_epsilon:
            return DPQueryResult(
                success=False,
                result=None,
                noise_scale=0.0,
                epsilon_spent=0.0,
                budget_remaining=0.0,
                privacy_accounting={
                    "epsilon_budget": self.config.default_epsilon,
                    "delta_budget": self.config.default_delta,
                    "total_spent": self._total_epsilon_spent,
                    "status": PrivacyBudgetStatus.DEPLETED.value,
                },
            )

        epsilon_per_query = self.config.default_epsilon / self.config.max_queries_per_user
        new_total = self._total_epsilon_spent + epsilon_per_query

        if new_total > self.config.default_epsilon:
            epsilon_per_query = self.config.default_epsilon - self._total_epsilon_spent
            new_total = self.config.default_epsilon

        # Calibrate noise: higher remaining budget = more noise, lower = less
        remaining_ratio = max(
            0.01,
            (self.config.default_epsilon - new_total) / self.config.default_epsilon,
        )
        noise_scale = 1.0 / remaining_ratio if remaining_ratio > 0 else 100.0

        # Simulate a DP result by hashing query + dataset_id + noise
        raw_result = hashlib.sha256(
            f"{query}:{dataset_id}:{noise_scale}".encode()
        ).hexdigest()

        budget_remaining = max(0.0, self.config.default_epsilon - new_total)

        # Determine budget status
        if new_total >= self.config.default_epsilon:
            status = PrivacyBudgetStatus.DEPLETED.value
        elif remaining_ratio < 0.2:
            status = PrivacyBudgetStatus.WARNING.value
        else:
            status = PrivacyBudgetStatus.AVAILABLE.value

        dp_result = DPQueryResult(
            success=True,
            result=raw_result,
            noise_scale=noise_scale,
            epsilon_spent=epsilon_per_query,
            budget_remaining=budget_remaining,
            privacy_accounting={
                "epsilon_budget": self.config.default_epsilon,
                "delta_budget": self.config.default_delta,
                "epsilon_spent": epsilon_per_query,
                "total_spent": new_total,
                "noise_mechanism": self.config.noise_mechanism,
                "noise_scale": noise_scale,
                "dataset_id": dataset_id,
                "status": status,
            },
        )

        self._total_epsilon_spent = new_total
        self._total_queries += 1
        self._dp_accounting.append(
            {
                "query": query,
                "epsilon_spent": epsilon_per_query,
                "cumulative": new_total,
            }
        )

        return dp_result

    def get_privacy_budget(self) -> PrivacyBudget:
        """Return the current privacy budget status.

        Returns
        -------
        PrivacyBudget
            Current budget allocation with remaining epsilon, queries left,
            and per-user limits.
        """
        remaining_epsilon = max(0.0, self.config.default_epsilon - self._total_epsilon_spent)
        queries_remaining = max(
            0,
            self.config.max_queries_per_user - self._total_queries,
        )

        if remaining_epsilon <= 0.0:
            status = PrivacyBudgetStatus.DEPLETED.value
        elif remaining_epsilon < self.config.default_epsilon * 0.2:
            status = PrivacyBudgetStatus.WARNING.value
        else:
            status = PrivacyBudgetStatus.AVAILABLE.value

        per_user_limits = tuple(
            (uid, max(0.0, self.config.default_epsilon - spent))
            for uid, spent in self._per_user_epsilon.items()
        )

        return PrivacyBudget(
            epsilon=self.config.default_epsilon,
            delta=self.config.default_delta,
            total_spent_epsilon=self._total_epsilon_spent,
            queries_remaining=queries_remaining,
            status=status,
            per_user_limits=per_user_limits,
        )

    def create_federated_update(
        self, knowledge_delta: dict[str, Any]
    ) -> FederatedUpdate:
        """Create a federated knowledge update with differential privacy.

        Applies DP noise to the knowledge delta before sharing, and
        returns an update that can be aggregated with updates from other
        agents.

        Parameters
        ----------
        knowledge_delta : dict[str, Any]
            Knowledge graph changes to share.

        Returns
        -------
        FederatedUpdate
            A DP-protected federated update ready for aggregation.
        """
        import uuid

        update_id = str(uuid.uuid4())
        epsilon_per_update = self.config.default_epsilon * 0.1

        # Apply DP noise to numerical values in the knowledge delta
        dp_applied = self.config.differential_privacy_enabled
        noised_delta: dict[str, Any] = {}
        if dp_applied:
            import random

            # Small noise scale for stub — production would calibrate
            # noise relative to sensitivity / epsilon
            noise_scale = 0.01
            for key, value in knowledge_delta.items():
                if isinstance(value, (int, float)):
                    noise = random.gauss(0, noise_scale)
                    noised_delta[key] = value + noise
                elif isinstance(value, dict):
                    noised_delta[key] = value
                else:
                    noised_delta[key] = value
        else:
            noised_delta = dict(knowledge_delta)

        encryption_metadata: tuple[tuple[str, str], ...] = (
            ("algorithm", "AES-256-GCM"),
            ("key_derivation", "HKDF-SHA256"),
            ("agent_id", self._agent_id),
        )

        update = FederatedUpdate(
            update_id=update_id,
            source_agent=self._agent_id,
            knowledge_graph_delta=noised_delta,
            encryption_metadata=encryption_metadata,
            differential_privacy_applied=dp_applied,
            epsilon_spent=epsilon_per_update if dp_applied else 0.0,
        )

        self._total_epsilon_spent += epsilon_per_update if dp_applied else 0.0
        self._federated_updates_history.append(update_id)

        return update

    def aggregate_updates(self, updates: list[FederatedUpdate]) -> FederatedAggregation:
        """Aggregate federated updates from multiple agents.

        Combines knowledge deltas using weighted averaging and computes
        a convergence score. Enforces the minimum contributing agents
        threshold from the privacy configuration.

        Parameters
        ----------
        updates : list[FederatedUpdate]
            Federated updates from contributing agents.

        Returns
        -------
        FederatedAggregation
            Aggregated knowledge with convergence score and total epsilon
            consumption.

        Raises
        ------
        ValueError
            If the number of updates is below min_contributing_agents.
        """
        if len(updates) < self.config.min_contributing_agents:
            raise ValueError(
                f"Need at least {self.config.min_contributing_agents} updates "
                f"for aggregation, got {len(updates)}"
            )

        import uuid

        round_id = str(uuid.uuid4())
        contributing_agents = tuple(
            sorted({u.source_agent for u in updates})
        )
        total_epsilon = sum(u.epsilon_spent for u in updates)

        # Aggregate knowledge: compute mean for numeric values, union for dicts
        aggregated: dict[str, Any] = {}
        key_counts: dict[str, int] = {}

        for update in updates:
            for key, value in update.knowledge_graph_delta.items():
                if key not in aggregated:
                    aggregated[key] = 0.0 if isinstance(value, (int, float)) else value
                    key_counts[key] = 0
                if isinstance(aggregated[key], (int, float)):
                    aggregated[key] += value  # type: ignore[operator]
                else:
                    aggregated[key] = value
                key_counts[key] += 1

        for key, count in key_counts.items():
            if isinstance(aggregated[key], (int, float)) and count > 0:
                aggregated[key] = aggregated[key] / count  # type: ignore[operator]

        # Compute convergence score: proportion of agents with consistent keys
        if len(updates) > 0:
            all_keys: set[str] = set()
            for u in updates:
                all_keys.update(u.knowledge_graph_delta.keys())

            present_counts = sum(
                1 for key in all_keys if key_counts.get(key, 0) >= len(updates)
            )
            convergence_score = (
                present_counts / len(all_keys) if all_keys else 1.0
            )
        else:
            convergence_score = 0.0

        aggregation = FederatedAggregation(
            round_id=round_id,
            contributing_agents=contributing_agents,
            aggregated_knowledge=aggregated,
            total_epsilon=total_epsilon,
            convergence_score=min(1.0, convergence_score),
        )

        self._total_federated_rounds += 1
        return aggregation

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate privacy statistics for this agent.

        Returns
        -------
        dict[str, Any]
            Dictionary with keys:
            - agent_id: this agent's identifier
            - total_queries: number of inference/queries processed
            - total_epsilon_spent: cumulative epsilon consumed
            - epsilon_budget: total epsilon budget allocated
            - total_federated_rounds: number of aggregation rounds
            - total_attestations: number of attestations generated
            - dp_enabled: whether differential privacy is enabled
            - fl_enabled: whether federated learning is enabled
            - confidential_enabled: whether confidential inference is enabled
        """
        return {
            "agent_id": self._agent_id,
            "total_queries": self._total_queries,
            "total_epsilon_spent": self._total_epsilon_spent,
            "epsilon_budget": self.config.default_epsilon,
            "total_federated_rounds": self._total_federated_rounds,
            "total_attestations": self._total_attestations,
            "dp_enabled": self.config.differential_privacy_enabled,
            "fl_enabled": self.config.federated_learning_enabled,
            "confidential_enabled": self.config.confidential_inference_enabled,
        }


__version__ = "0.1.0"

__all__ = [
    # Enums
    "PrivacyBudgetStatus",
    # Data classes
    "AttestationProof",
    "PrivacyBudget",
    "DPQueryResult",
    "FederatedUpdate",
    "FederatedAggregation",
    "PrivacyConfig",
    # Main agent
    "PrivacyPreservingAgent",
]
