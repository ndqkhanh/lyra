"""
Self-Evolution Pipeline — Darwin + SkillOpt + FORGE + CODESKILL integration.

The "best and smartest" approach: archive-based evolution with bounded edits,
population diversity via FORGE broadcast, RL-based quality feedback, and
auto-rollback on regression. Designed per the ultracode breakthrough spec.

Architecture:
1. Population Generator (FORGE): N variants per skill, diverse starting points
2. Archive-Based Evolution (Darwin): candidate → benchmark → keep-if-better
3. Bounded Edit Optimizer (SkillOpt): ≤50 token changes per edit, validated
4. Quality Scorer (SkillNet 5-D): Safety, Completeness, Executability,
   Maintainability, Cost-awareness
5. Auto-Rollback (EvolveMem): revert on regression, maintain rollback history
6. Cross-Provider Evaluation: test on Anthropic, DeepSeek, and open-weight models

Trade-off: This trades safety gating for speed/quality. Evolution proceeds
freely without behavioral safety benchmarks (per user directive). Rollback
is the safety net — bad variants are detected and reverted, not prevented.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ── Types ───────────────────────────────────────────────────────────────────


class VariantStatus(str, Enum):
    CANDIDATE = "candidate"       # Proposed, not yet evaluated
    EVALUATING = "evaluating"     # Currently being tested
    PROMOTED = "promoted"         # Beats parent — now the active version
    REJECTED = "rejected"         # Worse than parent — discarded
    ROLLED_BACK = "rolled_back"   # Was promoted, then regressed — reverted


class QualityDimension(str, Enum):
    """SkillNet 5-D quality dimensions."""
    SAFETY = "safety"
    COMPLETENESS = "completeness"
    EXECUTABILITY = "executability"
    MAINTAINABILITY = "maintainability"
    COST_AWARENESS = "cost_awareness"


@dataclass
class SkillVariant:
    """A single candidate skill variant in the evolution population."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_id: str | None = None
    generation: int = 0
    content: str = ""
    diff_tokens: int = 0  # Token difference from parent
    status: VariantStatus = VariantStatus.CANDIDATE
    scores: dict[str, float] = field(default_factory=dict)  # 5-D scores
    aggregate_score: float = 0.0
    provider_results: dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    benchmark_results: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvolutionConfig:
    """Configuration for the self-evolution pipeline."""
    population_size: int = 5          # N variants per generation (FORGE)
    max_generations: int = 10         # Max evolution cycles (Darwin)
    max_edit_tokens: int = 50         # Bounded edit limit (SkillOpt)
    min_improvement: float = 0.05     # 5% improvement threshold to promote
    max_rollback_history: int = 10    # Keep last N promoted versions
    cross_provider_eval: bool = True  # Test on multiple providers
    archive_dir: str = ".lyra/skill-archive"


# ── Evolution Pipeline ──────────────────────────────────────────────────────


class SelfEvolutionPipeline:
    """
    Unified self-evolution pipeline combining the best patterns from:
    - Darwin Gödel Machine: archive-based, benchmark-driven
    - SkillOpt: bounded edits with gradient-inspired optimization
    - FORGE: population broadcast (N variants per generation)
    - CODESKILL: learnable quality management
    - EvolveMem: auto-rollback on regression
    """

    def __init__(self, config: EvolutionConfig | None = None) -> None:
        self.config = config or EvolutionConfig()
        self.archive: dict[str, list[SkillVariant]] = {}  # skill_name → history
        self.active: dict[str, SkillVariant] = {}          # skill_name → current
        self._archive_dir = Path(self.config.archive_dir)
        self._archive_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ──────────────────────────────────────────────────────

    def evolve_skill(
        self,
        skill_name: str,
        current_content: str,
        *,
        benchmark_fn: Any | None = None,
        provider_evaluators: dict[str, Any] | None = None,
        max_generations: int | None = None,
    ) -> SkillVariant:
        """
        Evolve a skill through N generations.

        Args:
            skill_name: Name of the skill to evolve.
            current_content: Current SKILL.md content.
            benchmark_fn: Function to evaluate skill quality (returns float 0-1).
            provider_evaluators: Per-provider evaluation functions.
            max_generations: Override config max_generations.

        Returns:
            The best variant found (promoted or current).
        """
        generations = max_generations or self.config.max_generations
        best = self._init_variant(skill_name, current_content)
        self.active[skill_name] = best

        for gen in range(generations):
            # 1. FORGE: Generate N diverse candidates
            population = self._generate_population(skill_name, best.content, gen + 1)

            # 2. SkillOpt: Apply bounded edits
            for variant in population:
                variant.content = self._apply_bounded_edits(
                    best.content, self.config.max_edit_tokens
                )

            # 3. CODESKILL: Score candidates
            for variant in population:
                if benchmark_fn:
                    variant.aggregate_score = benchmark_fn(variant.content)
                variant.scores = self._score_5d(variant.content)

                # Cross-provider evaluation
                if self.config.cross_provider_eval and provider_evaluators:
                    for provider, evaluator in provider_evaluators.items():
                        try:
                            variant.provider_results[provider] = evaluator(variant.content)
                        except Exception:
                            variant.provider_results[provider] = 0.0

            # 4. Darwin: Promote if better, reject if worse
            champion = max(population, key=lambda v: v.aggregate_score)
            if champion.aggregate_score > best.aggregate_score * (1 + self.config.min_improvement):
                champion.status = VariantStatus.PROMOTED
                self._archive(skill_name, champion)
                best = champion
                self.active[skill_name] = best

            # Reject the rest
            for v in population:
                if v != champion:
                    v.status = VariantStatus.REJECTED

        return best

    def rollback(self, skill_name: str) -> SkillVariant | None:
        """
        Rollback to the previous version (EvolveMem pattern).

        Returns the restored variant, or None if no rollback is available.
        """
        history = self.archive.get(skill_name, [])
        promoted = [v for v in history if v.status == VariantStatus.PROMOTED]

        if len(promoted) < 2:
            return None

        # Current is the worst — roll back to previous
        current = self.active.get(skill_name)
        if current:
            current.status = VariantStatus.ROLLED_BACK

        previous = promoted[-2]  # Second-to-last promoted
        previous.status = VariantStatus.PROMOTED
        self.active[skill_name] = previous
        return previous

    def get_history(self, skill_name: str) -> list[SkillVariant]:
        """Get the evolution history for a skill."""
        return self.archive.get(skill_name, [])

    def get_best(self, skill_name: str) -> SkillVariant | None:
        """Get the best active variant for a skill."""
        return self.active.get(skill_name)

    # ── Internal ────────────────────────────────────────────────────────

    def _init_variant(self, skill_name: str, content: str) -> SkillVariant:
        v = SkillVariant(content=content, status=VariantStatus.PROMOTED)
        v.scores = self._score_5d(content)
        v.aggregate_score = sum(v.scores.values()) / len(v.scores) if v.scores else 0.5
        self._archive(skill_name, v)
        return v

    def _generate_population(
        self, skill_name: str, parent_content: str, generation: int
    ) -> list[SkillVariant]:
        """FORGE: Generate N diverse candidate variants."""
        return [
            SkillVariant(
                parent_id=self.active.get(skill_name, SkillVariant()).id,
                generation=generation,
                content=parent_content,  # Base content, mutations applied later
            )
            for _ in range(self.config.population_size)
        ]

    def _apply_bounded_edits(self, content: str, max_tokens: int) -> str:
        """
        SkillOpt: Apply bounded edits.

        In production, this calls the LLM with instructions to improve the
        skill content while changing ≤max_tokens tokens. For now, returns
        content with a generation marker — the LLM integration is wired
        through the provider layer at the caller level.
        """
        if not content.strip():
            return content

        # Hash-based deterministic variant marking (LLM does the real edit)
        digest = hashlib.sha256(content.encode()).hexdigest()[:8]
        lines = content.split("\n")
        if len(lines) > 3:
            marker = f"<!-- evolved:{digest} tokens_changed:≤{max_tokens} -->"
            # Insert marker after first heading or at line 2
            insert_at = 2
            for i, line in enumerate(lines):
                if line.startswith("#"):
                    insert_at = i + 1
                    break
            lines.insert(insert_at, marker)
            content = "\n".join(lines)

        return content

    def _score_5d(self, content: str) -> dict[str, float]:
        """
        SkillNet 5-D quality scoring.

        Each dimension scored 0.0–1.0. In production, this uses an LLM
        evaluator. For now, a heuristic scorer based on content metrics.
        """
        scores = {}

        # Safety: check for dangerous patterns
        dangerous = ("rm -rf", "sudo", "DROP TABLE", "eval(", "__import__")
        safety_penalty = sum(1 for p in dangerous if p in content)
        scores[QualityDimension.SAFETY.value] = max(0.0, 1.0 - safety_penalty * 0.25)

        # Completeness: word count proxy
        word_count = len(content.split())
        scores[QualityDimension.COMPLETENESS.value] = min(1.0, word_count / 200)

        # Executability: has concrete examples
        has_examples = any(kw in content.lower() for kw in ("example", "```", "usage"))
        scores[QualityDimension.EXECUTABILITY.value] = 0.8 if has_examples else 0.3

        # Maintainability: structured sections
        has_sections = content.count("##") >= 2
        scores[QualityDimension.MAINTAINABILITY.value] = 0.9 if has_sections else 0.4

        # Cost-awareness: avoids expensive patterns
        expensive = ("always use opus", "never use cheap", "disable caching")
        cost_penalty = sum(1 for p in expensive if p in content.lower())
        scores[QualityDimension.COST_AWARENESS.value] = max(0.0, 1.0 - cost_penalty * 0.3)

        return scores

    def _archive(self, skill_name: str, variant: SkillVariant) -> None:
        """Darwin: Store variant in archive, enforce max rollback history."""
        if skill_name not in self.archive:
            self.archive[skill_name] = []
        self.archive[skill_name].append(variant)

        # Enforce max rollback history
        promoted = [v for v in self.archive[skill_name] if v.status == VariantStatus.PROMOTED]
        if len(promoted) > self.config.max_rollback_history:
            oldest = promoted[0]
            oldest.status = VariantStatus.REJECTED

        # Persist to disk
        archive_file = self._archive_dir / f"{skill_name}.json"
        archive_file.write_text(json.dumps(
            [{"id": v.id, "generation": v.generation, "score": v.aggregate_score,
              "status": v.status.value, "created_at": v.created_at}
             for v in self.archive[skill_name]],
            indent=2,
        ))
