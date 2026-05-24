"""
MoLEM — Mixture of Learnable Experts with Memory.

MoLEM tackles catastrophic forgetting by keeping a frozen base model and
routing inputs through a dynamic set of learnable experts. New knowledge is
stored in new or updated experts without perturbing the base model, and a
memory buffer interleaves past experiences during training.

Key properties:
- **Frozen base** — never updated, core reasoning stays intact.
- **Dynamic MoE router** — learns which experts to activate per input.
- **Expert lifecycle** — add, specialise, and prune experts over time.
- **Forgetting monitoring** — continuously tracks backward/forward transfer.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import (
    ContinualEpisode,
    ExpertStats,
    ForgettingMetrics,
    MoEExpert,
    MoELayer,
)

logger = logging.getLogger(__name__)


class MoLEMEngine:
    """Mixture of Learnable Experts with Memory engine.

    Routes each input to the top-k most relevant experts, updates only
    the router weights (not the frozen base), and tracks forgetting
    across sequentially presented tasks.

    Typical usage::

        engine = MoLEMEngine(base_experts=3)
        engine.add_expert("math", "mathematical_reasoning")
        experts = engine.route("Solve the quadratic equation")
        engine.learn(ContinualEpisode(task="algebra", ...))
    """

    def __init__(
        self,
        *,
        base_experts: int = 4,
        default_active_count: int = 2,
        router_temperature: float = 1.0,
        weight_decay: float = 0.001,
    ) -> None:
        self.default_active_count = default_active_count
        self.router_temperature = router_temperature
        self.weight_decay = weight_decay

        # Pre-populate with general-purpose base experts
        initial_experts = tuple(
            MoEExpert(
                expert_id=f"base_{i}",
                domain="general",
                specialization_score=0.5,
            )
            for i in range(base_experts)
        )
        initial_weights = tuple(1.0 / base_experts for _ in range(base_experts))

        self.layer = MoELayer(
            experts=initial_experts,
            router_weights=initial_weights,
            active_count=default_active_count,
        )

        self._episode_history: list[ContinualEpisode] = []
        self._performance_log: dict[str, list[float]] = {}
        self._expert_stats: dict[str, ExpertStats] = {}

    # ── Routing ───────────────────────────────────────────────────────────

    def route(self, input_text: str) -> tuple[MoEExpert, ...]:
        """Select top-k experts for this input.

        Routing is based on domain-keyword matching between *input_text*
        and each expert's declared domain, modulated by router weights.

        Args:
            input_text: The input text to route.

        Returns:
            Tuple of selected ``MoEExpert`` instances (up to *active_count*).
        """
        input_lower = input_text.lower()
        scored: list[tuple[float, MoEExpert]] = []

        for i, expert in enumerate(self.layer.experts):
            relevance = self._domain_match(input_lower, expert.domain)
            weight = self.layer.router_weights[i] if i < len(self.layer.router_weights) else 0.0
            combined = relevance * weight
            scored.append((combined, expert))

        # Sort by combined score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Apply softmax temperature to select
        top_k = min(self.layer.active_count, len(scored))
        selected = tuple(expert for _, expert in scored[:top_k])

        logger.debug(
            "Routed '%s' -> %s",
            input_text[:60],
            [e.expert_id for e in selected],
        )
        return selected

    # ── Learning ──────────────────────────────────────────────────────────

    def learn(self, episode: ContinualEpisode) -> dict[str, Any]:
        """Process a continual learning episode.

        Updates router weights to favour experts that match the episode's
        domain. Does NOT modify the frozen base experts' internals.

        Args:
            episode: A complete training episode.

        Returns:
            Learning statistics dict.
        """
        self._episode_history.append(episode)

        # Find experts matching this episode's domain
        matched_indices = [
            i for i, e in enumerate(self.layer.experts)
            if self._domain_match(episode.task.lower(), e.domain) > 0.5
        ]

        if not matched_indices:
            logger.info("No expert matched episode '%s' — consider add_expert()", episode.task)
            return {"matched_experts": 0, "weight_delta": 0.0, "episode": episode.task}

        # Update router weights: boost matching experts, decay others
        delta = episode.performance_delta if episode.performance_delta != 0 else 0.1
        new_weights = list(self.layer.router_weights)

        for i in range(len(new_weights)):
            if i in matched_indices:
                new_weights[i] += delta * (1.0 - new_weights[i])  # boost toward 1
            else:
                new_weights[i] -= self.weight_decay * new_weights[i]  # decay toward 0

        # Renormalize
        total = sum(new_weights)
        if total > 0:
            new_weights = [w / total for w in new_weights]

        self.layer = self.layer.update_weights(tuple(new_weights))

        # Update expert specialization scores
        new_experts = list(self.layer.experts)
        for i in matched_indices:
            expert = new_experts[i]
            new_score = min(1.0, expert.specialization_score + 0.05)
            new_experts[i] = MoEExpert(
                expert_id=expert.expert_id,
                domain=expert.domain,
                specialization_score=new_score,
                last_used=expert.last_used,
                usage_count=expert.usage_count + 1,
                metadata=expert.metadata,
            )
        self.layer = MoELayer(
            experts=tuple(new_experts),
            router_weights=self.layer.router_weights,
            active_count=self.layer.active_count,
        )

        # Track performance
        if episode.task not in self._performance_log:
            self._performance_log[episode.task] = []
        self._performance_log[episode.task].append(episode.performance_delta)

        stats = {
            "matched_experts": len(matched_indices),
            "weight_delta": delta,
            "episode": episode.task,
            "expert_ids": [new_experts[i].expert_id for i in matched_indices],
        }

        logger.info(
            "Learned episode '%s': matched=%d experts, weight_delta=%.4f",
            episode.task,
            len(matched_indices),
            delta,
        )
        return stats

    # ── Expert management ─────────────────────────────────────────────────

    def add_expert(self, domain: str, specialization: str) -> MoEExpert:
        """Add a new expert for a previously unseen domain.

        Args:
            domain: The domain this expert specialises in.
            specialization: Description of the expert's specialisation.

        Returns:
            The newly created ``MoEExpert``.
        """
        expert_id = f"expert_{len(self.layer.experts)}"
        expert = MoEExpert(
            expert_id=expert_id,
            domain=domain,
            specialization_score=0.5,
            metadata={"specialization": specialization},
        )

        new_experts = self.layer.experts + (expert,)
        new_weights = tuple(self.layer.router_weights) + (1.0 / len(new_experts),)

        # Renormalize weights
        total = sum(new_weights)
        new_weights = tuple(w / total for w in new_weights)

        self.layer = MoELayer(
            experts=new_experts,
            router_weights=new_weights,
            active_count=self.layer.active_count,
        )

        logger.info("Added expert '%s' for domain '%s'", expert_id, domain)
        return expert

    def prune_experts(self, threshold: float = 0.01) -> list[str]:
        """Remove experts with router weight below *threshold*.

        Base experts (id starting with ``base_``) are never pruned.

        Args:
            threshold: Minimum router weight to retain an expert.

        Returns:
            List of pruned expert IDs.
        """
        pruned_ids: list[str] = []
        keep_indices: list[int] = []

        for i, (expert, weight) in enumerate(zip(self.layer.experts, self.layer.router_weights)):
            if expert.expert_id.startswith("base_"):
                keep_indices.append(i)
            elif weight >= threshold:
                keep_indices.append(i)
            else:
                pruned_ids.append(expert.expert_id)

        if pruned_ids:
            new_experts = tuple(self.layer.experts[i] for i in keep_indices)
            new_weights = tuple(self.layer.router_weights[i] for i in keep_indices)
            total = sum(new_weights)
            new_weights = tuple(w / total for w in new_weights) if total > 0 else new_weights

            self.layer = MoELayer(
                experts=new_experts,
                router_weights=new_weights,
                active_count=self.layer.active_count,
            )

            logger.info("Pruned %d expert(s): %s", len(pruned_ids), pruned_ids)

        return pruned_ids

    def get_active_experts(self) -> tuple[MoEExpert, ...]:
        """Return experts with non-negligible router weight (> 0.01)."""
        threshold = 0.01
        return tuple(
            e for e, w in zip(self.layer.experts, self.layer.router_weights)
            if w > threshold
        )

    # ── Forgetting metrics ────────────────────────────────────────────────

    def compute_forgetting(self) -> ForgettingMetrics:
        """Compute catastrophic forgetting metrics across all episodes.

        Backward transfer measures how much a new task degrades earlier
        tasks. Forward transfer measures how much prior learning helps.

        Returns:
            ``ForgettingMetrics`` with backward/forward transfer and retention.
        """
        if len(self._performance_log) < 2:
            return ForgettingMetrics(task_count=len(self._performance_log))

        tasks = list(self._performance_log.keys())
        per_task: dict[str, float] = {}
        backward_deltas: list[float] = []

        for i, task in enumerate(tasks):
            perf = self._performance_log[task]
            if not perf:
                continue

            initial = perf[0]
            final = perf[-1]
            per_task[task] = final - initial

            # Backward transfer: check if later tasks degraded this one
            if i > 0 and len(perf) >= 2:
                before_new = perf[-2]
                after_new = perf[-1]
                backward_deltas.append(after_new - before_new)

        backward_transfer = sum(backward_deltas) / len(backward_deltas) if backward_deltas else 0.0

        # Forward transfer: improvement on first encounter of each task
        forward_deltas: list[float] = []
        for i, task in enumerate(tasks):
            perf = self._performance_log[task]
            if perf:
                forward_deltas.append(perf[0] - (0.5 if i > 0 else 0.4))

        forward_transfer = sum(forward_deltas) / len(forward_deltas) if forward_deltas else 0.0

        # Retention: 1 - (total negative deltas / task_count)
        total_negative = sum(abs(d) for d in backward_deltas if d < 0)
        retention = max(0.0, 1.0 - total_negative / len(tasks))

        logger.info(
            "Forgetting: backward=%.4f forward=%.4f retention=%.2f",
            backward_transfer,
            forward_transfer,
            retention,
        )

        return ForgettingMetrics(
            backward_transfer=backward_transfer,
            forward_transfer=forward_transfer,
            retention=retention,
            task_count=len(tasks),
            detailed_per_task=per_task,
        )

    # ── Expert statistics ─────────────────────────────────────────────────

    def get_expert_stats(self) -> list[ExpertStats]:
        """Return aggregated statistics for all experts."""
        stats: list[ExpertStats] = []

        for i, (expert, weight) in enumerate(zip(self.layer.experts, self.layer.router_weights)):
            prev = self._expert_stats.get(expert.expert_id)
            trend = (weight - prev.last_weight) if prev else 0.0

            stat = ExpertStats(
                expert_id=expert.expert_id,
                domain=expert.domain,
                total_uses=expert.usage_count,
                avg_weight=weight,
                last_weight=weight,
                weight_trend=trend,
            )
            self._expert_stats[expert.expert_id] = stat
            stats.append(stat)

        return stats

    @property
    def episode_count(self) -> int:
        return len(self._episode_history)

    @property
    def expert_count(self) -> int:
        return len(self.layer.experts)

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _domain_match(input_text: str, domain: str) -> float:
        """Compute keyword-overlap match between input and domain."""
        if domain == "general":
            return 0.6  # general experts match everything moderately

        input_tokens = set(input_text.split())
        domain_tokens = set(domain.replace("_", " ").split())

        overlap = len(input_tokens & domain_tokens)
        max_len = max(len(domain_tokens), 1)

        return min(1.0, overlap / max_len)
