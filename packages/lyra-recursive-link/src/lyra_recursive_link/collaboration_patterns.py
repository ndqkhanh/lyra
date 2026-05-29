"""Four RecursiveMAS collaboration patterns for multi-agent workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import numpy as np

from lyra_recursive_link.exceptions import CollaborationError
from lyra_recursive_link.latent_encoder import LatentVector, similarity
from lyra_recursive_link.recursive_link import (
    AggregationMethod,
    LinkConfig,
    RecursiveLink,
)


class CollaborationPattern(Enum):
    MIXTURE = auto()
    DELIBERATION = auto()
    DISTILLATION = auto()
    SEQUENTIAL = auto()


@dataclass(frozen=True)
class CollaborationConfig:
    pattern: CollaborationPattern = CollaborationPattern.MIXTURE
    agents: tuple[str, ...] = ("agent_a", "agent_b")
    max_rounds: int = 5
    convergence_threshold: float = 0.05
    aggregation_method: AggregationMethod = AggregationMethod.MEAN


@dataclass(frozen=True)
class MixtureResult:
    aggregated_latent: LatentVector
    individual_latents: tuple[LatentVector, ...]
    weights: tuple[float, ...]
    convergence_rounds: int


@dataclass(frozen=True)
class DeliberationResult:
    refined_latent: LatentVector
    original_latent: LatentVector
    refinements: tuple[LatentVector, ...]
    convergence_rounds: int


@dataclass(frozen=True)
class DistillationResult:
    transferred_latent: LatentVector
    expert_latent: LatentVector
    learner_latent: LatentVector
    knowledge_fidelity: float


@dataclass(frozen=True)
class SequentialResult:
    final_latent: LatentVector
    stage_latents: tuple[LatentVector, ...]
    stage_names: tuple[str, ...]


CollaborationResult = (
    MixtureResult | DeliberationResult | DistillationResult | SequentialResult
)


def convergence_check(prev: LatentVector, current: LatentVector) -> bool:
    """Check if two latent vectors have converged (cosine similarity above threshold)."""
    if len(prev.vector) != len(current.vector):
        return False
    sim = similarity(prev, current)
    return sim >= 0.95


class CollaborationEngine:
    """Executes the four RecursiveMAS collaboration patterns."""

    def __init__(self) -> None:
        self._link = RecursiveLink()

    def execute_pattern(
        self,
        config: CollaborationConfig,
        input_latents: dict[str, LatentVector],
    ) -> CollaborationResult:
        if config.pattern == CollaborationPattern.MIXTURE:
            return self._execute_mixture(config, input_latents)
        elif config.pattern == CollaborationPattern.DELIBERATION:
            return self._execute_deliberation(config, input_latents)
        elif config.pattern == CollaborationPattern.DISTILLATION:
            return self._execute_distillation(config, input_latents)
        elif config.pattern == CollaborationPattern.SEQUENTIAL:
            return self._execute_sequential(config, input_latents)
        else:
            raise CollaborationError(f"Unknown pattern: {config.pattern}")

    def _execute_mixture(
        self,
        config: CollaborationConfig,
        input_latents: dict[str, LatentVector],
    ) -> MixtureResult:
        agents = list(input_latents.keys())
        if not agents:
            raise CollaborationError(
                "Mixture pattern requires at least one agent"
            )

        latents = [input_latents[a] for a in agents]
        link_cfg = LinkConfig(
            aggregation_method=config.aggregation_method,
            residual_connection=False,
        )
        aggregated = self._link.forward(latents, link_cfg)

        weights_list: list[float] = []
        for lv in latents:
            try:
                sim = similarity(lv, aggregated)
                weights_list.append(float(sim))
            except ValueError:
                weights_list.append(0.0)

        if sum(weights_list) > 0:
            weights_tuple = tuple(w / sum(weights_list) for w in weights_list)
        else:
            weights_tuple = tuple(1.0 / len(latents) for _ in latents)

        return MixtureResult(
            aggregated_latent=aggregated,
            individual_latents=tuple(latents),
            weights=weights_tuple,
            convergence_rounds=1,
        )

    def _execute_deliberation(
        self,
        config: CollaborationConfig,
        input_latents: dict[str, LatentVector],
    ) -> DeliberationResult:
        agent_names = list(input_latents.keys())
        if len(agent_names) < 1:
            raise CollaborationError(
                "Deliberation pattern requires at least one agent"
            )

        primary = agent_names[0]
        current = input_latents[primary]
        refinements: list[LatentVector] = [current]

        for _ in range(config.max_rounds):
            all_latents = list(input_latents.values())
            link_cfg = LinkConfig(
                aggregation_method=config.aggregation_method,
                residual_connection=True,
            )
            refined = self._link.forward(all_latents, link_cfg)

            if convergence_check(current, refined):
                refinements.append(refined)
                return DeliberationResult(
                    refined_latent=refined,
                    original_latent=input_latents[primary],
                    refinements=tuple(refinements),
                    convergence_rounds=len(refinements),
                )

            current = refined
            refinements.append(current)

        return DeliberationResult(
            refined_latent=current,
            original_latent=input_latents[primary],
            refinements=tuple(refinements),
            convergence_rounds=len(refinements),
        )

    def _execute_distillation(
        self,
        config: CollaborationConfig,
        input_latents: dict[str, LatentVector],
    ) -> DistillationResult:
        agent_names = list(input_latents.keys())
        if len(agent_names) < 2:
            raise CollaborationError(
                "Distillation pattern requires at least expert and learner agents"
            )

        expert_id = agent_names[0]
        learner_id = agent_names[-1]
        expert_latent = input_latents[expert_id]
        learner_latent = input_latents[learner_id]

        alpha = 0.7
        transferred_vec = (
            alpha * expert_latent.vector + (1.0 - alpha) * learner_latent.vector
        ).astype(np.float64)

        from lyra_recursive_link.latent_encoder import compute_compression_ratio

        transferred = LatentVector(
            vector=transferred_vec,
            original_length=expert_latent.original_length,
            compressed_length=expert_latent.compressed_length,
            compression_ratio=compute_compression_ratio(
                expert_latent.original_length, len(transferred_vec)
            ),
            semantic_hash=expert_latent.semantic_hash,
        )

        try:
            fidelity = similarity(transferred, expert_latent)
        except ValueError:
            fidelity = 0.0

        return DistillationResult(
            transferred_latent=transferred,
            expert_latent=expert_latent,
            learner_latent=learner_latent,
            knowledge_fidelity=float(fidelity),
        )

    def _execute_sequential(
        self,
        config: CollaborationConfig,
        input_latents: dict[str, LatentVector],
    ) -> SequentialResult:
        agent_names = list(input_latents.keys())
        if len(agent_names) < 1:
            raise CollaborationError(
                "Sequential pattern requires at least one agent"
            )

        stage_latents: list[LatentVector] = []
        current = input_latents[agent_names[0]]
        stage_latents.append(current)

        for agent in agent_names[1:]:
            next_latent = input_latents[agent]
            link_cfg = LinkConfig(
                aggregation_method=config.aggregation_method,
                residual_connection=True,
            )
            combined = self._link.forward([current, next_latent], link_cfg)
            stage_latents.append(combined)
            current = combined

        return SequentialResult(
            final_latent=current,
            stage_latents=tuple(stage_latents),
            stage_names=tuple(agent_names),
        )
