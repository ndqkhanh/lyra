"""L311-7 — Four-axis scaling-laws aggregator.

Operationalizes the 2026 scaling-law synthesis ([`docs/225-agent-era-scaling-synthesis.md`](../../../../../../docs/225-agent-era-scaling-synthesis.md))
as a *roadmap input* the operator can read in one place. The four
axes:

* ``pretrain`` — base-model parameter / pretraining-token investment
  ([`docs/216`](../../../../../../docs/216-pretraining-scaling-laws-foundation.md)).
* ``ttc`` — test-time compute (verifier × samples × CoT depth)
  ([`docs/217`](../../../../../../docs/217-test-time-compute-scaling.md),
  [`docs/223`](../../../../../../docs/223-verifier-and-best-of-n-scaling.md)).
* ``memory`` — context length × memory-tier depth × retrieval quality
  ([`docs/233`](../../../../../../docs/233-memory-scaling-for-agents.md),
  [`docs/234`](../../../../../../docs/234-context-length-scaling.md)).
* ``tool_use`` — ACI density × MCP coverage × tool reliability
  ([`docs/236`](../../../../../../docs/236-tool-use-and-aci-scaling.md)).

The aggregator does *not* benchmark. It surfaces *position* — what the
current Lyra install has on each axis — and *next-lever* — what the
cheapest meaningful upgrade is. Reading ``/scaling`` answers the
question "which axis should I invest in next?" without vibes.

The score on each axis is bounded in [0, 1] for readability; weights
are deliberate, transparent, and printable. Production callers can
replace the heuristic with empirical data via :meth:`record_*` calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Axis = Literal["pretrain", "ttc", "memory", "tool_use"]


# ---- per-axis position record ----------------------------------------


@dataclass(frozen=True)
class ScalingPosition:
    """Where the current install sits on one of the four axes."""

    axis: Axis
    score: float                # in [0, 1]
    current: str                # human-readable summary of the current state
    next_lever: str             # the cheapest single upgrade
    cost_hint: float            # 0 (free) to 1 (expensive); rough only
    benefit_hint: float         # 0 (no measurable lift) to 1 (large lift)

    @property
    def cost_benefit(self) -> float:
        if self.cost_hint <= 0.0:
            return self.benefit_hint  # free upgrades dominate
        return round(self.benefit_hint / max(self.cost_hint, 0.01), 4)


# ---- the aggregator --------------------------------------------------


@dataclass
class ScalingAxes:
    """Mutable per-axis state. Populate via ``record_*`` then ``snapshot()``."""

    # pretrain inputs -------------------------------------------------
    pretrain_model: str = "unknown"
    pretrain_param_b: float = 0.0      # billions; e.g. 70 for Llama-3-70B
    pretrain_quality: float = 0.5      # subjective in [0, 1]; defaults mid

    # ttc inputs ------------------------------------------------------
    ttc_max_samples: int = 1            # best-of-N width
    ttc_verifier_count: int = 0         # registered verifiers across domains
    ttc_avg_pass_rate: float = 0.0      # rolling pass rate

    # memory inputs ---------------------------------------------------
    memory_context_tokens: int = 8192   # current model's context window
    memory_tier_count: int = 1          # 1=flat, 2=hot+cold, 3=hot/warm/cold
    memory_retrieval_score: float = 0.5 # subjective quality

    # tool_use inputs -------------------------------------------------
    tool_native_count: int = 0
    tool_mcp_server_count: int = 0
    tool_avg_success_rate: float = 0.5

    notes: dict[Axis, list[str]] = field(default_factory=lambda: {
        "pretrain": [], "ttc": [], "memory": [], "tool_use": [],
    })

    # ---- recorders -----------------------------------------------

    def record_pretrain(
        self,
        *,
        model: str,
        param_b: float,
        quality: float | None = None,
    ) -> None:
        self.pretrain_model = model
        self.pretrain_param_b = max(param_b, 0.0)
        if quality is not None:
            if not 0.0 <= quality <= 1.0:
                raise ValueError(f"quality {quality} outside [0,1]")
            self.pretrain_quality = quality

    def record_ttc(
        self,
        *,
        max_samples: int,
        verifier_count: int,
        avg_pass_rate: float,
    ) -> None:
        if not 0.0 <= avg_pass_rate <= 1.0:
            raise ValueError(f"avg_pass_rate {avg_pass_rate} outside [0,1]")
        self.ttc_max_samples = max(max_samples, 1)
        self.ttc_verifier_count = max(verifier_count, 0)
        self.ttc_avg_pass_rate = avg_pass_rate

    def record_memory(
        self,
        *,
        context_tokens: int,
        tier_count: int,
        retrieval_score: float,
    ) -> None:
        if not 0.0 <= retrieval_score <= 1.0:
            raise ValueError(f"retrieval_score {retrieval_score} outside [0,1]")
        self.memory_context_tokens = max(context_tokens, 0)
        self.memory_tier_count = max(min(tier_count, 3), 1)
        self.memory_retrieval_score = retrieval_score

    def record_tool_use(
        self,
        *,
        native_count: int,
        mcp_server_count: int,
        avg_success_rate: float,
    ) -> None:
        if not 0.0 <= avg_success_rate <= 1.0:
            raise ValueError(f"avg_success_rate {avg_success_rate} outside [0,1]")
        self.tool_native_count = max(native_count, 0)
        self.tool_mcp_server_count = max(mcp_server_count, 0)
        self.tool_avg_success_rate = avg_success_rate

    # ---- snapshot ------------------------------------------------

    def snapshot(self) -> tuple[ScalingPosition, ...]:
        return (
            self._pretrain_position(),
            self._ttc_position(),
            self._memory_position(),
            self._tool_use_position(),
        )

    def best_lever(self) -> ScalingPosition:
        """Return the axis with the highest cost_benefit ratio."""
        return max(self.snapshot(), key=lambda p: p.cost_benefit)

    # ---- per-axis logic -----------------------------------------

    def _pretrain_position(self) -> ScalingPosition:
        # Score: log-scaled param-billions blended with quality.
        if self.pretrain_param_b <= 0:
            param_norm = 0.0
        else:
            # 70B (frontier-ish) → 0.7, 405B → 0.9, 1T+ → 1.0
            import math

            param_norm = min(math.log10(self.pretrain_param_b + 1) / 3.0, 1.0)
        score = round(0.6 * param_norm + 0.4 * self.pretrain_quality, 4)
        if param_norm < 0.4:
            lever = (
                "Switch to a larger base model (e.g. ≥70B)."
                " Cheapest single move; everything downstream lifts."
            )
            cost, benefit = 0.4, 0.7
        elif self.pretrain_quality < 0.7:
            lever = (
                "Investigate model variant: reasoner / coder / vision"
                " specialization where applicable."
            )
            cost, benefit = 0.2, 0.4
        else:
            lever = (
                "Pretrain axis saturated; spend goes to ttc/memory/tool_use."
            )
            cost, benefit = 1.0, 0.05
        return ScalingPosition(
            axis="pretrain",
            score=score,
            current=f"{self.pretrain_model} ({self.pretrain_param_b:.0f}B)",
            next_lever=lever,
            cost_hint=cost,
            benefit_hint=benefit,
        )

    def _ttc_position(self) -> ScalingPosition:
        # Score: blend of verifier-coverage, sampling width, pass rate.
        verifier_norm = min(self.ttc_verifier_count / 5.0, 1.0)
        samples_norm = min((self.ttc_max_samples - 1) / 7.0, 1.0)
        score = round(
            0.4 * verifier_norm + 0.3 * samples_norm + 0.3 * self.ttc_avg_pass_rate,
            4,
        )
        if verifier_norm < 0.4:
            lever = (
                "Add domain verifiers (target: ≥5 domains covered)."
                " Per Karpathy 2026-04, verifier density gates automation."
            )
            cost, benefit = 0.3, 0.8
        elif samples_norm < 0.4:
            lever = (
                "Raise best-of-N sampling for high-stakes turns (try N=4)."
            )
            cost, benefit = 0.5, 0.5
        elif self.ttc_avg_pass_rate < 0.7:
            lever = (
                "Investigate failed verifier traces; verifiers exist but "
                "are misaligned. Tune rubric, not capacity."
            )
            cost, benefit = 0.2, 0.6
        else:
            lever = "TTC axis healthy; consider memory or tool_use next."
            cost, benefit = 1.0, 0.1
        return ScalingPosition(
            axis="ttc",
            score=score,
            current=(
                f"verifiers={self.ttc_verifier_count}, "
                f"max_samples={self.ttc_max_samples}, "
                f"pass={self.ttc_avg_pass_rate:.2f}"
            ),
            next_lever=lever,
            cost_hint=cost,
            benefit_hint=benefit,
        )

    def _memory_position(self) -> ScalingPosition:
        # Score blends context-token capacity, tier depth, retrieval quality.
        # 200K tokens ≈ 1.0; 8K ≈ 0.2; 32K ≈ 0.5
        if self.memory_context_tokens <= 0:
            ctx_norm = 0.0
        else:
            import math

            ctx_norm = min(math.log10(self.memory_context_tokens) / 5.5, 1.0)
        tier_norm = (self.memory_tier_count - 1) / 2.0  # 1→0, 2→0.5, 3→1
        score = round(
            0.35 * ctx_norm + 0.25 * tier_norm + 0.4 * self.memory_retrieval_score,
            4,
        )
        if tier_norm < 0.5:
            lever = (
                "Promote auto-memory to a 3-tier (hot/warm/cold) MEMTIER. "
                "Per docs/151, flat memory breaks at 72-hour horizons."
            )
            cost, benefit = 0.4, 0.6
        elif self.memory_retrieval_score < 0.6:
            lever = (
                "Add a reranker tier to retrieval; current scores leave "
                "headroom from BM25-only baseline."
            )
            cost, benefit = 0.3, 0.5
        elif ctx_norm < 0.5:
            lever = (
                "Bump model context window where economical (cost grows "
                "quadratically; check usage histogram first)."
            )
            cost, benefit = 0.7, 0.3
        else:
            lever = "Memory axis saturated."
            cost, benefit = 1.0, 0.05
        return ScalingPosition(
            axis="memory",
            score=score,
            current=(
                f"ctx={self.memory_context_tokens}, "
                f"tiers={self.memory_tier_count}, "
                f"retrieval={self.memory_retrieval_score:.2f}"
            ),
            next_lever=lever,
            cost_hint=cost,
            benefit_hint=benefit,
        )

    def _tool_use_position(self) -> ScalingPosition:
        native_norm = min(self.tool_native_count / 12.0, 1.0)
        mcp_norm = min(self.tool_mcp_server_count / 6.0, 1.0)
        score = round(
            0.3 * native_norm + 0.3 * mcp_norm + 0.4 * self.tool_avg_success_rate,
            4,
        )
        if mcp_norm < 0.5:
            lever = (
                "Wire more MCP servers (target ≥6). MCP is the cross-"
                "harness extension surface (docs/07, docs/239)."
            )
            cost, benefit = 0.3, 0.6
        elif self.tool_avg_success_rate < 0.7:
            lever = (
                "Tool-call success is below 70%. Improve ACI: better "
                "schemas, error messages, retries (docs/236)."
            )
            cost, benefit = 0.2, 0.5
        elif native_norm < 0.5:
            lever = (
                "Add specialised native tools for high-frequency ops "
                "(read/edit/grep/bash already in)."
            )
            cost, benefit = 0.4, 0.3
        else:
            lever = "Tool-use axis saturated."
            cost, benefit = 1.0, 0.05
        return ScalingPosition(
            axis="tool_use",
            score=score,
            current=(
                f"native={self.tool_native_count}, "
                f"mcp={self.tool_mcp_server_count}, "
                f"success={self.tool_avg_success_rate:.2f}"
            ),
            next_lever=lever,
            cost_hint=cost,
            benefit_hint=benefit,
        )


# ---- formatting helper -----------------------------------------------


def render_scaling_table(positions: tuple[ScalingPosition, ...]) -> str:
    """Pretty-print the four axes as a table for the ``/scaling`` slash."""
    rows = [
        f"| {p.axis:<8} | {p.score:>5.2f} | "
        f"{p.cost_hint:>4.2f} | {p.benefit_hint:>5.2f} | "
        f"{p.current[:34]:<34} | {p.next_lever[:60]} |"
        for p in positions
    ]
    header = (
        "| axis     | score |  cost | benft | current"
        " " * 27
        + "| next lever                                                   |"
    )
    sep = (
        "|----------|-------|-------|-------|"
        "------------------------------------|"
        "--------------------------------------------------------------|"
    )
    return "\n".join([header, sep, *rows])


__all__ = [
    "Axis",
    "ScalingAxes",
    "ScalingPosition",
    "render_scaling_table",
]
