"""Diversity-preservation contracts (response to arXiv:2604.18005).

GREEN today: the four ``lyra_core.diversity`` primitives.
RED (xfail strict) until v1.8 Phase 6 / v1.9 Phase 1:

- ``TournamentTts`` must not collapse: mean pairwise distance of its
  attempt pool must exceed a configurable threshold (defends against
  the Compute Efficiency Paradox + Echo Chamber).
- ``ReasoningBank.matts_prefix`` must produce attempt-distinct prefixes
  whose pairwise distance exceeds a configurable threshold (already
  partially asserted by ``test_matts_prefix_diversifies_per_attempt``;
  this is the *quantitative* upgrade).
- The future ``SoftwareOrgMode`` v1.9 default topology must be
  ``vertical+subgroups``, never ``leader_led`` or ``interdisciplinary``
  (the two collapse modes from §4 Figure 3).
"""
from __future__ import annotations

import pytest

from lyra_core.diversity import (
    effective_diversity,
    mean_pairwise_distance,
    mmr_select,
    ngt_attempt_independence_guard,
)

# ---------- §1 GREEN: primitive contracts ----------


def test_mean_pairwise_distance_is_zero_for_identical_pool() -> None:
    """Single-mode pool == 0 dispersion, no exceptions for trivially small pools."""
    assert mean_pairwise_distance(["abc"] * 5) == 0.0
    assert mean_pairwise_distance([]) == 0.0
    assert mean_pairwise_distance(["only-one"]) == 0.0


def test_mean_pairwise_distance_grows_with_disjointness() -> None:
    """A perfectly redundant pool ≪ a disjoint pool. The fallback metric is
    sequence-matcher-based, so disjointness must mean *no shared substrings*.
    """
    redundant = ["aaa", "aaa", "aaa", "aaa"]
    disjoint = ["abc", "xyz", "qrs", "klm"]  # zero shared chars across all pairs
    assert mean_pairwise_distance(redundant) == 0.0
    assert mean_pairwise_distance(disjoint) > mean_pairwise_distance(redundant)


def test_effective_diversity_zeroes_a_pure_echo_chamber() -> None:
    """N copies of one string == 0 effective diversity (matches paper's Vendi == 1)."""
    assert effective_diversity(["x"] * 10) == 0.0


def test_effective_diversity_grows_with_distinct_modes() -> None:
    pool_2_modes = ["alpha", "alpha", "beta", "beta"]
    pool_4_modes = ["alpha", "beta", "gamma", "delta"]
    assert effective_diversity(pool_2_modes) < effective_diversity(pool_4_modes)


def test_mmr_lambda_one_recovers_top_k_relevance() -> None:
    """With ``lambda_=1.0`` the rerank reduces to plain top-k by relevance."""
    candidates = ["alpha", "beta", "gamma"]
    relevance = {"alpha": 0.1, "beta": 0.9, "gamma": 0.5}
    out = mmr_select(candidates, k=2, relevance=relevance, lambda_=1.0)
    assert out == ("beta", "gamma")


def test_mmr_lambda_zero_maximises_novelty_over_relevance() -> None:
    """With ``lambda_=0.0`` the second pick is the *least similar* to the first."""
    candidates = ["alpha-zero", "alpha-one", "delta-omega"]
    relevance = {c: 1.0 for c in candidates}  # tie on relevance
    out = mmr_select(candidates, k=2, relevance=relevance, lambda_=0.0)
    assert out[1] == "delta-omega"


def test_mmr_rejects_lambda_outside_unit_interval() -> None:
    with pytest.raises(ValueError):
        mmr_select(["a", "b"], k=1, relevance={"a": 1.0}, lambda_=1.5)


def test_ngt_guard_passes_for_unique_fingerprints() -> None:
    """The control case: every parallel attempt has its own context fingerprint."""
    ngt_attempt_independence_guard(["fp-0", "fp-1", "fp-2", "fp-3"])


def test_ngt_guard_raises_on_collision_with_helpful_message() -> None:
    """A collision is the smoking gun for Echo Chamber; the message must help debugging."""
    with pytest.raises(ValueError) as excinfo:
        ngt_attempt_independence_guard(["fp-0", "fp-1", "fp-0"])
    msg = str(excinfo.value)
    assert "fp-0" in msg
    assert "Echo-Chamber" in msg
    assert "2604.18005" in msg


# ---------- §2 RED: wiring contracts (xfail until v1.8 Phase 6 lands) ----------


def test_tournament_result_exposes_pool_diversity_score() -> None:
    """Phase 6 contract: TtsResult gains a ``pool_diversity`` attribute that
    callers can drift-gate on. Today TtsResult has no such field."""
    from lyra_core.tts import TtsResult

    fields = {f.name for f in TtsResult.__dataclass_fields__.values()}
    assert "pool_diversity" in fields, (
        "v1.8 Phase 6 must add `pool_diversity: float` to TtsResult so the "
        "verifier / drift-gate can detect mode-collapse before it ships."
    )


def test_tournament_calls_ngt_guard_during_run() -> None:
    """Phase 6 contract: TournamentTts must register the guard call.

    We probe by monkey-patching ``ngt_attempt_independence_guard`` and
    expecting the run to invoke it at least once.
    """
    from lyra_core import diversity
    from lyra_core.tts import (
        Attempt,
        AttemptGenerator,
        Discriminator,
        TournamentTts,
        TtsBudget,
    )

    calls: list[int] = []
    original = diversity.ngt_attempt_independence_guard

    def _spy(fps):
        calls.append(len(list(fps)))
        return original(fps)

    diversity.ngt_attempt_independence_guard = _spy  # type: ignore[assignment]
    try:
        class _Gen(AttemptGenerator):
            def generate(self, task_description, attempt_index):
                return Attempt(id=f"a{attempt_index}", artefact=f"draft-{attempt_index}")

        class _Disc(Discriminator):
            def compare(self, a, b):
                return a if a.id <= b.id else b

        tts = TournamentTts(
            generator=_Gen(),
            discriminator=_Disc(),
            budget=TtsBudget(max_attempts=4, max_wall_clock_s=5.0, max_total_tokens=10_000),
        )
        tts.run("anything")
    finally:
        diversity.ngt_attempt_independence_guard = original  # type: ignore[assignment]

    assert calls, (
        "v1.8 Phase 6 must call ngt_attempt_independence_guard inside "
        "TournamentTts.run before the discriminator pairs are formed."
    )


def test_reasoning_bank_recall_supports_diversity_weighted_mode() -> None:
    """Phase 6 contract: ReasoningBank.recall must accept a
    ``diversity_weighted=True`` flag that switches the ranker from plain
    top-k to ``mmr_select``. Probed by signature inspection."""
    import inspect

    from lyra_core.memory import ReasoningBank

    sig = inspect.signature(ReasoningBank.recall)
    assert "diversity_weighted" in sig.parameters, (
        "v1.8 Phase 6 must add `diversity_weighted: bool = False` to "
        "ReasoningBank.recall so callers can opt in to MMR selection."
    )


def test_software_org_mode_default_persona_topology_avoids_collapse_modes() -> None:
    """Phase 7 contract: when SoftwareOrgMode lands, its default config must
    not be the two collapse modes the paper identifies (``leader_led`` or
    ``interdisciplinary``). Today the module doesn't exist; that's the RED
    state. When v1.9 Phase 1 lands, this test plus a ``DEFAULT_PERSONA_MIX``
    constant of ``"vertical"`` and ``DEFAULT_TOPOLOGY`` of ``"subgroups"``
    must be present."""
    from lyra_core import org  # noqa: F401 — module may not exist yet
    from lyra_core.org import DEFAULT_PERSONA_MIX, DEFAULT_TOPOLOGY  # type: ignore[attr-defined]

    assert DEFAULT_PERSONA_MIX in {"vertical", "horizontal"}, (
        "default must be either Vertical (Pareto-optimum) or Horizontal "
        "(max-diversity); never Leader-Led or Interdisciplinary "
        "(arXiv:2604.18005 §4 Figure 3)."
    )
    assert DEFAULT_TOPOLOGY in {"subgroups", "ngt"}, (
        "default must be Subgroups (max sustained constructive conflict) "
        "or NGT (max initial diversity); never Standard "
        "(arXiv:2604.18005 §5.2 Figure 10)."
    )
