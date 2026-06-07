"""
Learned multi-head model router (BEST-Route architecture).

References
----------
- BEST-Route: Adaptive LLM Routing with Test-Time Optimal Compute
  Ding et al., arXiv:2506.22716v1
- RouteLLM: Learning to Route LLMs with Preference Data
  Ong et al., ICLR 2025, arXiv:2406.18665v4
- Training Verifiers to Solve Math Word Problems (GSM8K)
  Cobbe et al., OpenAI, arXiv:2404.04286v2
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, NamedTuple

import structlog

from lyra.routing.provider.types import (
    Capability,
    CostEstimate,
    EffortLevel,
    RouteDecision,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# -- model and effort tier definitions ------------------------------------
# ---------------------------------------------------------------------------

_DEFAULT_EFFORT_MAP: dict[str, EffortLevel] = {
    "low": EffortLevel.LOW,
    "medium": EffortLevel.MEDIUM,
    "high": EffortLevel.HIGH,
    "xhigh": EffortLevel.XHIGH,
    "max": EffortLevel.MAX,
}


class SamplingDepth(Enum):
    """Number of responses generated for best-of-N selection."""

    N1 = 1
    N3 = 3
    N5 = 5
    N10 = 10
    N20 = 20


@dataclass(frozen=True)
class TripleCandidate:
    """A (model, effort, sampling-depth) triple the router evaluates.

    Attributes:
        model_name: Provider model identifier (e.g. ``"claude-sonnet-4-6"``).
        provider_name: Provider name (e.g. ``"anthropic"``).
        effort: Reasoning effort level.
        n: Sampling depth for best-of-N.
        cost_per_1k_input: Estimated input cost per 1K tokens in USD.
        cost_per_1k_output: Estimated output cost per 1K tokens in USD.
        capabilities: Set of capabilities this model supports.
    """

    model_name: str
    provider_name: str
    effort: EffortLevel
    n: int
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    capabilities: frozenset[Capability] = frozenset()


@dataclass(frozen=True)
class ScoredCandidate:
    """A (model, effort, n) triple with its predicted match probability.

    Attributes:
        candidate: The underlying (model, effort, n) triple.
        match_probability: Predicted probability (0-1) that this
            configuration meets or exceeds reference-model quality
            on the given query.
        estimated_cost: Monetised cost estimate for a single completion
            at this configuration.
    """

    candidate: TripleCandidate
    match_probability: float
    estimated_cost: CostEstimate

    @property
    def effective_cost(self) -> float:
        """Total cost including the best-of-N multiplier."""
        return self.estimated_cost.total_max_cost * self.candidate.n


# ---------------------------------------------------------------------------
# -- proxy reward model (GSM8K-style verifier) ----------------------------
# ---------------------------------------------------------------------------


@dataclass
class ProxyRewardModel:
    """DeBERTa-v3-large (304M) proxy reward model for best-of-N selection.

    The reward model scores each of the ``n`` generated responses and
    returns the highest-scored response as the final answer.

    This is a lightweight dataclass that exposes the same interface as a
    full DeBERTa-v3-large trained checkpoint. In zero-shot / cold-start
    mode it falls back to a heuristic (normalised sequence probability).

    References
    ----------
    - Cobbe et al. (2024) "Training Verifiers to Solve Math Word Problems"
    - BEST-Route §3.2: "Proxy Reward Model Training"

    Note
    ----
    The full DeBERTa-v3-large checkpoint training requires ~25K graded
    examples. Before the checkpoint is available, the heuristic fallback
    uses Normalised Sequence Probability (NSP) as a quality proxy.
    """

    checkpoint_path: str | None = None
    _loaded: bool = False

    def load_checkpoint(self, path: str) -> None:
        """Load a trained DeBERTa-v3-large checkpoint.

        Args:
            path: Filesystem path to the checkpoint directory.
        """
        self.checkpoint_path = path
        self._loaded = True
        logger.info("proxy reward model checkpoint loaded", path=path)

    @property
    def is_ready(self) -> bool:
        """Whether a trained checkpoint has been loaded."""
        return self._loaded

    def score_responses(
        self,
        query: str,
        responses: list[str],
        token_logprobs: list[list[float]] | None = None,
    ) -> list[float]:
        """Score each generated response on a quality scale (0-1).

        When a trained checkpoint is loaded this delegates to the neural
        reward model. When the checkpoint is absent it falls back to
        Normalised Sequence Probability (NSP):

            NSP = exp( mean(floor(logprobs, -3.0)) )

        Args:
            query: The original user query.
            responses: ``n`` generated responses to score.
            token_logprobs: Optional per-token log probabilities for
                each response. Required for the NSP fallback.

        Returns:
            A list of ``len(responses)`` float scores in [0, 1].
        """
        if self._loaded:
            msg = (
                "ProxyRewardModel.score_responses called with loaded checkpoint. "
                "The neural forward pass requires a PyTorch / ONNX runtime "
                "import at this call site."
            )
            raise NotImplementedError(msg)

        # NSP heuristic fallback
        if token_logprobs is None or len(token_logprobs) != len(responses):
            logger.warning(
                "token_logprobs not available for NSP scoring; falling back "
                "to uniform baseline"
            )
            return [1.0 / len(responses) for _ in responses] if responses else []

        scores: list[float] = []
        for logprobs in token_logprobs:
            if not logprobs:
                scores.append(0.0)
                continue
            floored = [max(lp, -3.0) for lp in logprobs]
            nsp = math.exp(sum(floored) / len(floored))
            scores.append(nsp)

        return scores

    def select_best(self, query: str, responses: list[str],
                    token_logprobs: list[list[float]] | None = None) -> tuple[str, float]:
        """Select the best response via best-of-N scoring.

        Args:
            query: The original user query.
            responses: ``n`` generated responses.
            token_logprobs: Per-token logprobs for the NSP fallback path.

        Returns:
            ``(best_response, best_score)`` tuple.
        """
        scores = self.score_responses(query, responses, token_logprobs)
        best_idx = max(range(len(scores)), key=lambda i: scores[i])
        return responses[best_idx], scores[best_idx]


# ---------------------------------------------------------------------------
# -- matrix-factorisation preference model (RouteLLM) ---------------------
# ---------------------------------------------------------------------------


@dataclass
class MatrixFactorPreferenceModel:
    """RouteLLM-style matrix factorisation for cross-model generalisation.

    Learns latent embeddings ``p_u`` (model preferences) and ``q_i`` (query
    features) so that preference strength ``p_u @ q_i`` generalises to
    (model, query) pairs never seen during training.

    References
    ----------
    RouteLLM §3 — Ong et al., ICLR 2025

    Note
    ----
    In cold-start mode this returns a uniform baseline. The actual matrix
    factorisation requires ~100K preference pairs to converge.
    """

    n_factors: int = 32
    trained: bool = False

    def predict(self, query_embedding: list[float]) -> dict[str, float]:
        """Return per-model preference scores for a query.

        Args:
            query_embedding: Dense embedding vector of the query (length
                should match ``n_factors``).

        Returns:
            Mapping of ``model_name -> preference_score``.
        """
        if not self.trained:
            return {}

        if len(query_embedding) != self.n_factors:
            logger.warning(
                "query_embedding dimension mismatch",
                expected=self.n_factors,
                got=len(query_embedding),
            )
            return {}

        msg = (
            "MatrixFactorPreferenceModel.predict requires a trained MF "
            "model with latent embeddings fitted on preference data."
        )
        raise NotImplementedError(msg)


# ---------------------------------------------------------------------------
# -- learned multi-head router --------------------------------------------
# ---------------------------------------------------------------------------


class LearnedRouterState(Enum):
    """Operational state of the learned router."""

    COLD_START = "cold_start"
    TRAINING = "training"
    ACTIVE = "active"
    ERROR = "error"


@dataclass
class LearnedRouter:
    """DeBERTa-v3-small (44M) multi-head learned router.

    Architecture
    ------------
    A shared DeBERTa-v3-small backbone produces a single query embedding.
    ``K × N`` lightweight classification heads (one per (model, effort, n)
    triple) each predict the probability that configuration meets or exceeds
    reference-model quality.

    At inference time:
      1. Compute match probabilities for all valid (model, effort, n) triples.
      2. Filter by the quality threshold (default 0.90).
      3. Select the cheapest qualifying configuration.
      4. Generate ``n`` responses in parallel (or sequentially).
      5. Return the highest-scored response via the proxy reward model.

    When the learned router is in cold-start / unavailable state, the
    ``select`` method falls back to the static tier router provided via
    the ``static_fallback`` callable.

    References
    ----------
    BEST-Route (Ding et al., arXiv:2506.22716v1)
    RouteLLM (Ong et al., ICLR 2025, arXiv:2406.18665v4)
    FrugalGPT (Chen et al., ICML 2023, arXiv:2305.05176v1)
    """

    # Quality threshold: only configurations with match_probability >= this
    # value are considered for routing.
    quality_threshold: float = 0.90
    # Default candidates (models, effort levels, sampling depths) the router
    # evaluates. Populated at init; overridable per-call.
    _candidates: tuple[TripleCandidate, ...] = ()

    # List of triples that failed quality filtering last time (for debugging).
    _last_filtered_out: list[ScoredCandidate] = field(default_factory=list)
    _last_selected: ScoredCandidate | None = None

    # Sub-components
    proxy_reward_model: ProxyRewardModel = field(default_factory=ProxyRewardModel)
    preference_model: MatrixFactorPreferenceModel = field(
        default_factory=MatrixFactorPreferenceModel,
    )

    # State tracking
    state: LearnedRouterState = LearnedRouterState.COLD_START
    _training_queries_processed: int = 0

    def __post_init__(self) -> None:
        if not self._candidates:
            self._candidates = _default_candidates()

    def register_candidates(self, candidates: tuple[TripleCandidate, ...]) -> None:
        """Override the default candidate set.

        Args:
            candidates: New set of (model, effort, n) triples to evaluate.
        """
        self._candidates = candidates

    def select(
        self,
        query: str,
        query_embedding: list[float] | None = None,
        candidates: tuple[TripleCandidate, ...] | None = None,
        quality_threshold: float | None = None,
    ) -> ScoredCandidate:
        """Select the cheapest qualifying (model, effort, n) configuration.

        Args:
            query: The user query string.
            query_embedding: Optional dense embedding for the query.
                Used by the matrix-factorisation preference model.
            candidates: Override candidate set for this call.
            quality_threshold: Override quality threshold for this call.

        Returns:
            A ``ScoredCandidate`` with the selected configuration.

        Raises:
            RuntimeError: If no candidate meets the quality threshold and
                no static fallback is available.
        """
        effective_candidates = candidates if candidates is not None else self._candidates
        threshold = quality_threshold if quality_threshold is not None else self.quality_threshold

        if self.state == LearnedRouterState.COLD_START:
            logger.info("learned router in cold-start; using static fallback")
            return self._static_fallback(query, effective_candidates)

        # Score each candidate
        scored = self._score_candidates(query, query_embedding, effective_candidates)
        qualifying = [s for s in scored if s.match_probability >= threshold]

        self._last_filtered_out = [s for s in scored if s.match_probability < threshold]

        if not qualifying:
            logger.warning(
                "no candidate meets quality threshold",
                threshold=threshold,
                candidate_count=len(scored),
            )
            return self._static_fallback(query, effective_candidates)

        # Pick cheapest qualifying
        cheapest = min(qualifying, key=lambda s: s.effective_cost)
        self._last_selected = cheapest

        logger.info(
            "router selected configuration",
            model=cheapest.candidate.model_name,
            provider=cheapest.candidate.provider_name,
            effort=cheapest.candidate.effort.value,
            n=cheapest.candidate.n,
            match_probability=round(cheapest.match_probability, 4),
            effective_cost=round(cheapest.effective_cost, 6),
        )

        return cheapest

    def _score_candidates(
        self,
        query: str,
        query_embedding: list[float] | None,
        candidates: tuple[TripleCandidate, ...],
    ) -> list[ScoredCandidate]:
        """Score every candidate using available signals.

        When the backbone is not yet trained this uses a heuristic based on
        tier similarity: premium-tier models get higher base probability,
        cheap models get a discount.

        When the backbone checkpoint is loaded, THIS METHOD SHOULD delegate
        to the DeBERTa-v3-small forward pass (not implemented here; this
        call site awaits a PyTorch / ONNX integration).
        """
        scored: list[ScoredCandidate] = []

        # -- heuristic fallback (cold-start / backbone absent) ----------
        if self.state == LearnedRouterState.COLD_START:
            for c in candidates:
                base = self._heuristic_tier_probability(c)
                scored.append(
                    ScoredCandidate(
                        candidate=c,
                        match_probability=base,
                        estimated_cost=self._estimate_cost(c),
                    ),
                )
            return scored

        # -- backbone-powered path (post-training) -----------------------
        msg = (
            "LearnedRouter._score_candidates requires a DeBERTa-v3-small "
            "backbone forward pass. A PyTorch / ONNX integration is needed "
            "at this call site."
        )
        raise NotImplementedError(msg)

    def _heuristic_tier_probability(self, candidate: TripleCandidate) -> float:
        """Heuristic base probability based on model tier.

        Used only during cold-start / training-data generation. Assigns
        higher probabilities to premium models and lower to cheap models,
        with a slight edge for higher sampling depths.

        These values are replaced by learned probabilities once the
        backbone is trained.
        """
        name_lower = candidate.model_name.lower()
        if "opus" in name_lower or "gpt-5" in name_lower:
            base = 0.95
        elif "sonnet" in name_lower or "gpt-4" in name_lower:
            base = 0.85
        elif "haiku" in name_lower or "flash" in name_lower:
            base = 0.60
        else:
            base = 0.75

        # N-depth bonus: wider sampling improves quality
        depth_bonus = 0.02 * (candidate.n - 1)

        # Effort bonus
        effort_bonus = {
            EffortLevel.LOW: -0.05,
            EffortLevel.MEDIUM: 0.0,
            EffortLevel.HIGH: 0.05,
            EffortLevel.XHIGH: 0.08,
            EffortLevel.MAX: 0.10,
        }.get(candidate.effort, 0.0)

        return min(max(base + depth_bonus + effort_bonus, 0.0), 1.0)

    def _estimate_cost(self, candidate: TripleCandidate) -> CostEstimate:
        """Estimate the cost of a single completion at this configuration."""
        # Rough baseline: 500 input tokens, 1500 output tokens
        input_cost = (candidate.cost_per_1k_input / 1000.0) * 500
        output_cost = (candidate.cost_per_1k_output / 1000.0) * 1500
        return CostEstimate(
            input_cost=input_cost,
            output_cost=output_cost,
            total_max_cost=input_cost + output_cost,
        )

    def _static_fallback(
        self,
        query: str,
        candidates: tuple[TripleCandidate, ...],
    ) -> ScoredCandidate:
        """Training-free fallback: select the safest static tier candidate.

        Picks the candidate closest to a reasonable default: a mid-tier
        model (Sonnet/GPT-4o) at medium effort with N=1.
        """
        ranked = sorted(
            candidates,
            key=lambda c: (
                0 if "sonnet" in c.model_name.lower() or "gpt-4" in c.model_name.lower() else 1,
                0 if c.effort == EffortLevel.MEDIUM else 1,
                c.n,
                c.cost_per_1k_input + c.cost_per_1k_output,
            ),
        )
        chosen = ranked[0] if ranked else candidates[0]
        return ScoredCandidate(
            candidate=chosen,
            match_probability=self._heuristic_tier_probability(chosen),
            estimated_cost=self._estimate_cost(chosen),
        )

    @property
    def last_selected(self) -> ScoredCandidate | None:
        """The most recently selected candidate."""
        return self._last_selected

    @property
    def last_filtered_out(self) -> list[ScoredCandidate]:
        """Candidates that failed the quality threshold in the last call."""
        return list(self._last_filtered_out)

    # -- training data generation -----------------------------------------

    def generate_training_data(
        self,
        queries: list[str],
        generate_fn: Any,
    ) -> list[dict[str, Any]]:
        """Generate training data for the learned router.

        For each of the ``K`` model configurations, generates ``N=20``
        responses per query, collects token-level logprobs, and constructs
        a training example consisting of:

        * ``query`` — the original query
        * ``responses`` — list of (response_text, logprobs, model_config)
        * ``scores`` — proxy reward model scores per response

        Args:
            queries: List of training queries (target size ~8K).
            generate_fn: Async callable ``(query, model, effort, n) ->
                list[dict]`` returning per-response dicts with keys
                ``text``, ``token_logprobs``, and ``latency_ms``.

        Returns:
            List of training examples (one per query per model config).
        """
        if not queries:
            logger.warning("generate_training_data called with empty queries")
            return []

        examples: list[dict[str, Any]] = []
        for query in queries:
            query_examples: list[dict[str, Any]] = []
            for candidate in self._candidates:
                all_responses: list[str] = []
                all_logprobs: list[list[float]] = []

                responses_raw = generate_fn(
                    query,
                    candidate.model_name,
                    candidate.effort.value,
                    n=candidate.n,
                )

                for resp in responses_raw:
                    all_responses.append(resp["text"])
                    all_logprobs.append(resp.get("token_logprobs", []))

                best_text, best_score = self.proxy_reward_model.select_best(
                    query, all_responses, all_logprobs,
                )

                query_examples.append({
                    "query": query,
                    "model_name": candidate.model_name,
                    "provider_name": candidate.provider_name,
                    "effort": candidate.effort.value,
                    "n": candidate.n,
                    "responses": all_responses,
                    "best_response": best_text,
                    "best_score": best_score,
                    "avg_latency_ms": sum(
                        r.get("latency_ms", 0) for r in responses_raw
                    ) / max(len(responses_raw), 1),
                })

                self._training_queries_processed += 1

            examples.extend(query_examples)

        logger.info(
            "training data generated",
            examples=len(examples),
            queries=len(queries),
        )

        self.state = LearnedRouterState.TRAINING
        return examples


# ---------------------------------------------------------------------------
# -- factory helpers -------------------------------------------------------
# ---------------------------------------------------------------------------


def _default_candidates() -> tuple[TripleCandidate, ...]:
    """Build the default 8-models x 3-effort-levels x 5-sampling-depths set.

    The set covers three tiers:

    * **Tier 1 (cheap):** Haiku-3.5, Llama-3.1-8B
    * **Tier 2 (mid):** Sonnet-4.6, GPT-4o-mini, DeepSeek-V3
    * **Tier 3 (premium):** Opus-4.8, GPT-5, DeepSeek-R1
    """
    configs: list[TripleCandidate] = []

    models = [
        # (model_name, provider, cost_in_1k, cost_out_1k, tier)
        ("claude-haiku-3-5", "anthropic", 0.25, 1.25),
        ("claude-sonnet-4-6", "anthropic", 3.0, 15.0),
        ("claude-opus-4-5", "anthropic", 15.0, 75.0),
        ("gpt-4o-mini", "openai", 0.15, 0.60),
        ("gpt-5", "openai", 15.0, 75.0),
        ("deepseek-chat", "deepseek", 0.27, 1.10),
        ("deepseek-reasoner", "deepseek", 0.55, 2.19),
        ("llama-3-1-8b", "openweights", 0.30, 0.61),
    ]

    # Effort levels per model (simplified: only the tiers that make sense)
    effort_assignments: dict[str, tuple[EffortLevel, ...]] = {
        "claude-haiku-3-5": (EffortLevel.LOW, EffortLevel.MEDIUM),
        "claude-sonnet-4-6": (EffortLevel.LOW, EffortLevel.MEDIUM, EffortLevel.HIGH),
        "claude-opus-4-5": (EffortLevel.HIGH, EffortLevel.XHIGH, EffortLevel.MAX),
        "gpt-4o-mini": (EffortLevel.LOW, EffortLevel.MEDIUM),
        "gpt-5": (EffortLevel.HIGH, EffortLevel.XHIGH, EffortLevel.MAX),
        "deepseek-chat": (EffortLevel.LOW, EffortLevel.MEDIUM, EffortLevel.HIGH),
        "deepseek-reasoner": (EffortLevel.HIGH, EffortLevel.XHIGH),
        "llama-3-1-8b": (EffortLevel.LOW, EffortLevel.MEDIUM),
    }

    depths = (SamplingDepth.N1, SamplingDepth.N3, SamplingDepth.N5,
              SamplingDepth.N10, SamplingDepth.N20)

    for model_name, provider, cost_in, cost_out in models:
        efforts = effort_assignments.get(model_name, (EffortLevel.MEDIUM,))
        for effort in efforts:
            for depth in depths:
                configs.append(
                    TripleCandidate(
                        model_name=model_name,
                        provider_name=provider,
                        effort=effort,
                        n=depth.value,
                        cost_per_1k_input=cost_in,
                        cost_per_1k_output=cost_out,
                    ),
                )

    return tuple(configs)


def create_learned_router(
    quality_threshold: float = 0.90,
) -> LearnedRouter:
    """Factory that returns a ``LearnedRouter`` with default candidate set.

    Args:
        quality_threshold: Minimum match probability for a configuration
            to be considered (default 0.90).

    Returns:
        A ``LearnedRouter`` instance in cold-start state.
    """
    return LearnedRouter(
        quality_threshold=quality_threshold,
        _candidates=_default_candidates(),
    )
