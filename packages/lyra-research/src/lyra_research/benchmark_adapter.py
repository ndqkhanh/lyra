"""ResearcherBench adapter — Phase 7 of the Deep Research Agent plan.

Provides a curated set of frontier AI research questions and an evaluation
adapter that tracks per-question faithfulness and groundedness so Lyra's
research quality can be benchmarked against an external standard.

The benchmark is offline: questions live in code (or in a JSON override),
and scoring runs against a research report or progress record using the
existing ``ResearchQualityEvaluator``.

Grounding:
- ResearcherBench (Liu et al. 2026) — 65 frontier AI research questions
- DeepResearch-ReportEval — faithfulness / groundedness axes
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lyra_research.orchestrator import ResearchProgress


__all__ = [
    "BenchmarkQuestion",
    "BenchmarkResult",
    "BenchmarkAdapter",
]


# ---------------------------------------------------------------------------
# Question schema
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkQuestion:
    """One ResearcherBench-style frontier research question."""

    id: str
    domain: str  # "ml" | "nlp" | "agents" | "systems" | "alignment"
    question: str
    difficulty: str = "medium"  # "easy" | "medium" | "hard"
    expected_sources: int = 5
    expected_gaps: int = 1


# ---------------------------------------------------------------------------
# Default question set — 65 frontier AI research questions
# ---------------------------------------------------------------------------

_DEFAULT_QUESTIONS: tuple[BenchmarkQuestion, ...] = (
    # --- Agents (13) ---
    BenchmarkQuestion(
        "Q01", "agents", "Compare ReAct, Reflexion, and Voyager memory strategies", "medium"
    ),
    BenchmarkQuestion(
        "Q02", "agents", "Survey closed-loop self-rewriting agent architectures since 2024", "hard"
    ),
    BenchmarkQuestion(
        "Q03", "agents", "What are the SOTA benchmarks for multi-hop agent reasoning?", "medium"
    ),
    BenchmarkQuestion(
        "Q04", "agents", "Describe LightRAG and HippoRAG graph-memory designs", "medium"
    ),
    BenchmarkQuestion(
        "Q05", "agents", "Compare IRCoT, Search-R1, and BAAR routing for agent trajectories", "hard"
    ),
    BenchmarkQuestion(
        "Q06",
        "agents",
        "Survey agent observability frameworks (Phoenix, Langfuse, OpenTelemetry GenAI)",
        "easy",
    ),
    BenchmarkQuestion(
        "Q07",
        "agents",
        "Compare model context protocol (MCP) and agent-2-agent (A2A) standards",
        "medium",
    ),
    BenchmarkQuestion(
        "Q08", "agents", "What stability budgets work best for self-rewriting agents?", "hard"
    ),
    BenchmarkQuestion(
        "Q09", "agents", "Identify gaps in trace-grounded reflection methods", "hard"
    ),
    BenchmarkQuestion(
        "Q10", "agents", "Best frameworks for fleet-managed parallel agent evolution", "medium"
    ),
    BenchmarkQuestion(
        "Q11", "agents", "Compare Voyager, SKILL, and ATLAS-RTC skill accumulation", "hard"
    ),
    BenchmarkQuestion(
        "Q12", "agents", "Survey HITL-interrupt patterns in LangGraph-style checkpointing", "medium"
    ),
    BenchmarkQuestion(
        "Q13",
        "agents",
        "What evaluators detect prompt-injection in retrieval-augmented agents?",
        "medium",
    ),
    # --- ML (13) ---
    BenchmarkQuestion(
        "Q14", "ml", "Transformer architecture variants since GPT-4 (2024-2026)", "medium"
    ),
    BenchmarkQuestion(
        "Q15", "ml", "Compare DPO, IPO, and SimPO preference-tuning algorithms", "hard"
    ),
    BenchmarkQuestion(
        "Q16", "ml", "Survey speculative decoding methods and their speedups", "medium"
    ),
    BenchmarkQuestion("Q17", "ml", "Mixture-of-experts routing: granular vs coarse", "medium"),
    BenchmarkQuestion(
        "Q18", "ml", "State-space models vs transformers on long-context tasks", "hard"
    ),
    BenchmarkQuestion("Q19", "ml", "Test-time scaling laws for reasoning models", "hard"),
    BenchmarkQuestion("Q20", "ml", "Compare RoPE, ALiBi, and YaRN positional encodings", "medium"),
    BenchmarkQuestion("Q21", "ml", "Distillation strategies for small reasoning models", "medium"),
    BenchmarkQuestion(
        "Q22", "ml", "Efficient attention: FlashAttention v1, v2, v3 differences", "easy"
    ),
    BenchmarkQuestion("Q23", "ml", "Quantisation: GPTQ vs AWQ vs SmoothQuant", "medium"),
    BenchmarkQuestion("Q24", "ml", "Best practices for SFT data curation in 2026", "medium"),
    BenchmarkQuestion("Q25", "ml", "Hybrid attention models combining sparse + dense", "hard"),
    BenchmarkQuestion("Q26", "ml", "Survey reasoning RL methods (RLOO, GRPO, REINFORCE++)", "hard"),
    # --- NLP (13) ---
    BenchmarkQuestion(
        "Q27", "nlp", "Survey retrieval-augmented generation evaluation methods", "medium"
    ),
    BenchmarkQuestion(
        "Q28", "nlp", "Long-context reasoning benchmarks (RULER, ZeroSCROLLS, Loong)", "medium"
    ),
    BenchmarkQuestion("Q29", "nlp", "Compare BM25, Contriever, and BGE retrievers in 2026", "easy"),
    BenchmarkQuestion(
        "Q30", "nlp", "Cross-encoder vs late-interaction (ColBERT) ranking", "medium"
    ),
    BenchmarkQuestion(
        "Q31", "nlp", "Hallucination detection methods in long-form generation", "hard"
    ),
    BenchmarkQuestion("Q32", "nlp", "Multilingual reasoning benchmark gaps", "hard"),
    BenchmarkQuestion("Q33", "nlp", "Survey query rewriting techniques for RAG", "medium"),
    BenchmarkQuestion("Q34", "nlp", "Compare GraphRAG variants for enterprise documents", "medium"),
    BenchmarkQuestion(
        "Q35", "nlp", "Citation faithfulness metrics for AI research reports", "hard"
    ),
    BenchmarkQuestion("Q36", "nlp", "Code-switching evaluation in multilingual LLMs", "medium"),
    BenchmarkQuestion("Q37", "nlp", "Best evaluation of structured-output JSON generation", "easy"),
    BenchmarkQuestion("Q38", "nlp", "Survey constraint-aware decoding methods", "medium"),
    BenchmarkQuestion(
        "Q39", "nlp", "Tokeniser quality for non-Latin scripts in 2026 models", "medium"
    ),
    # --- Systems (13) ---
    BenchmarkQuestion(
        "Q40", "systems", "Compare vLLM, SGLang, and LMDeploy serving frameworks", "medium"
    ),
    BenchmarkQuestion(
        "Q41", "systems", "Prefix caching strategies in production LLM serving", "medium"
    ),
    BenchmarkQuestion(
        "Q42",
        "systems",
        "Distributed training: ZeRO-Infinity vs FSDP2 vs DeepSpeed-Ulysses",
        "hard",
    ),
    BenchmarkQuestion(
        "Q43", "systems", "Survey GPU kernel libraries (Triton, CUTLASS, ThunderKittens)", "hard"
    ),
    BenchmarkQuestion(
        "Q44", "systems", "Compare paged attention and continuous batching tradeoffs", "medium"
    ),
    BenchmarkQuestion(
        "Q45", "systems", "Best practices for LLM checkpoint sharding in 2026", "medium"
    ),
    BenchmarkQuestion(
        "Q46", "systems", "Survey HBM3e and HBM4 memory bandwidth implications", "easy"
    ),
    BenchmarkQuestion("Q47", "systems", "Compare H100, B200, and MI300X for inference", "easy"),
    BenchmarkQuestion("Q48", "systems", "Cost-aware autoscaling for LLM serving fleets", "medium"),
    BenchmarkQuestion("Q49", "systems", "Multi-tenant isolation in shared GPU serving", "hard"),
    BenchmarkQuestion(
        "Q50",
        "systems",
        "Compare TensorRT-LLM, ONNX Runtime, and vLLM for edge inference",
        "medium",
    ),
    BenchmarkQuestion("Q51", "systems", "Survey speculative-decoding kernel optimisations", "hard"),
    BenchmarkQuestion(
        "Q52", "systems", "Throughput vs latency tradeoffs in chunked-prefill", "medium"
    ),
    # --- Alignment (13) ---
    BenchmarkQuestion("Q53", "alignment", "Compare RLHF, DPO, and KTO alignment methods", "medium"),
    BenchmarkQuestion("Q54", "alignment", "Survey constitutional AI variants in 2026", "medium"),
    BenchmarkQuestion(
        "Q55", "alignment", "Best practices for jailbreak robustness evaluation", "hard"
    ),
    BenchmarkQuestion(
        "Q56", "alignment", "Compare red-teaming frameworks for frontier models", "medium"
    ),
    BenchmarkQuestion(
        "Q57",
        "alignment",
        "Survey scalable oversight methods (debate, recursive reward modeling)",
        "hard",
    ),
    BenchmarkQuestion(
        "Q58", "alignment", "Interpretability: SAE vs probing vs causal tracing in 2026", "hard"
    ),
    BenchmarkQuestion("Q59", "alignment", "Compare alignment-faking detection methods", "hard"),
    BenchmarkQuestion("Q60", "alignment", "Survey deception and sandbagging benchmarks", "hard"),
    BenchmarkQuestion(
        "Q61", "alignment", "Best evaluations for tool-use safety in agents", "medium"
    ),
    BenchmarkQuestion(
        "Q62", "alignment", "Compare model-organisms-of-misalignment programs", "hard"
    ),
    BenchmarkQuestion(
        "Q63", "alignment", "Survey CBRN safeguards in frontier model evals", "medium"
    ),
    BenchmarkQuestion(
        "Q64", "alignment", "Mechanistic anomaly detection methods 2024-2026", "hard"
    ),
    BenchmarkQuestion(
        "Q65", "alignment", "Compare control evaluations vs capability evaluations", "medium"
    ),
)

assert len(_DEFAULT_QUESTIONS) == 65, "ResearcherBench requires exactly 65 questions"


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    """Outcome of running one benchmark question through Lyra."""

    question_id: str
    domain: str
    difficulty: str

    faithfulness: float = 0.0  # 1.0 if all claims map to real sources
    groundedness: float = 0.0  # fraction of claims with >=1 supporting source
    coverage_score: float = 0.0
    citation_fidelity: float = 0.0
    overall_score: float = 0.0
    passed: bool = False
    notes: str = ""
    measured_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "domain": self.domain,
            "difficulty": self.difficulty,
            "faithfulness": self.faithfulness,
            "groundedness": self.groundedness,
            "coverage_score": self.coverage_score,
            "citation_fidelity": self.citation_fidelity,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "notes": self.notes,
            "measured_at": self.measured_at,
        }


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class BenchmarkAdapter:
    """Run Lyra's research pipeline against ResearcherBench questions and
    track faithfulness + groundedness over time.

    Faithfulness is enforced via the existing CitationBinder (zero hallucinations);
    groundedness is derived from the evaluator's citation fidelity axis.

    Usage::

        adapter = BenchmarkAdapter()
        question = adapter.questions[0]
        # User code runs the research pipeline and supplies the ResearchProgress
        result = adapter.score(question, progress)
        adapter.save(result)
        summary = adapter.summary()
    """

    DEFAULT_PATH = Path(".lyra/benchmark/researcherbench.jsonl")

    def __init__(
        self,
        questions: tuple[BenchmarkQuestion, ...] | None = None,
        results_path: Path | None = None,
    ) -> None:
        self.questions = questions if questions is not None else _DEFAULT_QUESTIONS
        self.results_path = results_path or self.DEFAULT_PATH

    # ------------------------------------------------------------------
    # Question selection
    # ------------------------------------------------------------------

    def get(self, question_id: str) -> BenchmarkQuestion | None:
        return next((q for q in self.questions if q.id == question_id), None)

    def by_domain(self, domain: str) -> list[BenchmarkQuestion]:
        return [q for q in self.questions if q.domain == domain]

    def by_difficulty(self, difficulty: str) -> list[BenchmarkQuestion]:
        return [q for q in self.questions if q.difficulty == difficulty]

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score(
        self,
        question: BenchmarkQuestion,
        progress: ResearchProgress,
        verified_citations: int = 0,
        total_claims: int = 0,
    ) -> BenchmarkResult:
        """Score a research session against one benchmark question.

        Faithfulness: 1.0 iff every claim has a real, fetched citation
        (delegated to existing CitationBinder pipeline; we treat
        ``citation_fidelity`` from the evaluator as the canonical value).

        Groundedness: fraction of claims with >= 1 supporting source.
        """
        # Compute groundedness
        if total_claims > 0:
            groundedness = verified_citations / total_claims
        else:
            groundedness = 0.0

        # Pull whatever metrics exist on the progress object.
        report = getattr(progress, "report", None)
        citation_fidelity = float(getattr(report, "citation_fidelity", 0.0) or 0.0)
        coverage_score = float(getattr(report, "coverage_score", 0.0) or 0.0)
        overall_score = float(getattr(report, "quality_score", 0.0) or 0.0)

        # Faithfulness equals citation_fidelity by definition (no halluc.)
        faithfulness = citation_fidelity

        # Pass gates: citation fidelity 1.0 AND groundedness >= 0.8
        passed = faithfulness >= 1.0 and groundedness >= 0.8 and coverage_score >= 0.75

        return BenchmarkResult(
            question_id=question.id,
            domain=question.domain,
            difficulty=question.difficulty,
            faithfulness=faithfulness,
            groundedness=groundedness,
            coverage_score=coverage_score,
            citation_fidelity=citation_fidelity,
            overall_score=overall_score,
            passed=passed,
            notes=(
                f"sources={getattr(progress, 'papers_analyzed', 0)} papers, "
                f"{getattr(progress, 'repos_analyzed', 0)} repos"
            ),
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, result: BenchmarkResult) -> None:
        """Append result to the benchmark log (JSONL)."""
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        with self.results_path.open("a") as f:
            f.write(json.dumps(result.to_dict()) + "\n")

    def load_all(self) -> list[BenchmarkResult]:
        if not self.results_path.exists():
            return []
        out: list[BenchmarkResult] = []
        for line in self.results_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                out.append(BenchmarkResult(**d))
            except (json.JSONDecodeError, TypeError):
                continue
        return out

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Aggregate stats across all logged results."""
        results = self.load_all()
        if not results:
            return {
                "total_questions": len(self.questions),
                "answered": 0,
                "pass_rate": 0.0,
                "mean_faithfulness": 0.0,
                "mean_groundedness": 0.0,
                "by_domain": {},
            }
        n = len(results)
        passed = sum(1 for r in results if r.passed)
        mean_faith = sum(r.faithfulness for r in results) / n
        mean_ground = sum(r.groundedness for r in results) / n

        by_domain: dict[str, dict] = {}
        for r in results:
            d = by_domain.setdefault(r.domain, {"n": 0, "passed": 0})
            d["n"] += 1
            if r.passed:
                d["passed"] += 1
        for d in by_domain.values():
            d["pass_rate"] = d["passed"] / d["n"] if d["n"] else 0.0

        return {
            "total_questions": len(self.questions),
            "answered": n,
            "pass_rate": passed / n,
            "mean_faithfulness": mean_faith,
            "mean_groundedness": mean_ground,
            "by_domain": by_domain,
        }
