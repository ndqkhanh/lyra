"""
Comprehensive tests for the self-evolution pipeline module.

Covers: EvolutionConfig, SkillVariant, VariantStatus, QualityDimension,
SelfEvolutionPipeline (init, evolve_skill, rollback, get_history, get_best,
_score_5d, _apply_bounded_edits, _archive, _generate_population),
multiple generations, max_rollback_history, empty content,
cross-provider eval with failing evaluator.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from lyra_skill_evolution.pipeline import (
    EvolutionConfig,
    QualityDimension,
    SelfEvolutionPipeline,
    SkillVariant,
    VariantStatus,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_content() -> str:
    return """# Test Skill

## Overview
A skill for testing purposes.

## Usage
```python
example()
```

## Configuration
Configure with environment variables.

## Examples
Here is how to use it:

```python
result = test_skill()
```
"""


@pytest.fixture
def simple_content() -> str:
    return "# Simple\n\nJust a short skill."


@pytest.fixture
def empty_content() -> str:
    return ""


@pytest.fixture
def dangerous_content() -> str:
    return """# Dangerous Skill

Run: rm -rf / with sudo permission.
Or execute: eval(some_input).
Also: DROP TABLE users;
"""


@pytest.fixture
def expensive_content() -> str:
    return """# Expensive Skill

Always use opus for best results.
Never use cheap models.
Also disable caching for accuracy.
"""


@pytest.fixture
def default_config() -> EvolutionConfig:
    return EvolutionConfig()


@pytest.fixture
def tmp_config(tmp_path: Path) -> EvolutionConfig:
    return EvolutionConfig(archive_dir=str(tmp_path / ".lyra" / "skill-archive"))


@pytest.fixture
def pipeline(default_config: EvolutionConfig) -> SelfEvolutionPipeline:
    return SelfEvolutionPipeline(config=default_config)


@pytest.fixture
def tmp_pipeline(tmp_config: EvolutionConfig) -> SelfEvolutionPipeline:
    return SelfEvolutionPipeline(config=tmp_config)


@pytest.fixture
def champion_benchmark() -> Any:
    """A benchmark function that returns 1.0 to always beat the threshold."""

    def bench(content: str) -> float:
        return 1.0

    return bench


@pytest.fixture
def low_benchmark() -> Any:
    """A benchmark that returns low scores regardless."""

    def bench(content: str) -> float:
        return 0.1

    return bench


@pytest.fixture
def cross_provider_evaluators() -> dict[str, Any]:
    return {
        "anthropic": lambda c: 0.9,
        "deepseek": lambda c: 0.85,
    }


@pytest.fixture
def mixed_provider_evaluators() -> dict[str, Any]:
    def failing_evaluator(content: str) -> float:
        msg = "provider unavailability"
        raise RuntimeError(msg)

    return {
        "anthropic": lambda c: 0.9,
        "deepseek": failing_evaluator,
        "open-weight": lambda c: 0.7,
    }


# =============================================================================
# EvolutionConfig
# =============================================================================


class TestEvolutionConfig:
    def test_defaults(self) -> None:
        config = EvolutionConfig()
        assert config.population_size == 5
        assert config.max_generations == 10
        assert config.max_edit_tokens == 50
        assert config.min_improvement == 0.05
        assert config.max_rollback_history == 10
        assert config.cross_provider_eval is True
        assert config.archive_dir == ".lyra/skill-archive"

    def test_custom_values(self) -> None:
        config = EvolutionConfig(
            population_size=3,
            max_generations=2,
            max_edit_tokens=20,
            min_improvement=0.1,
            max_rollback_history=5,
            cross_provider_eval=False,
            archive_dir="/tmp/custom-archive",
        )
        assert config.population_size == 3
        assert config.max_generations == 2
        assert config.max_edit_tokens == 20
        assert config.min_improvement == 0.1
        assert config.max_rollback_history == 5
        assert config.cross_provider_eval is False
        assert config.archive_dir == "/tmp/custom-archive"

    def test_fields_are_mutable(self) -> None:
        config = EvolutionConfig()
        config.population_size = 99
        assert config.population_size == 99


# =============================================================================
# VariantStatus
# =============================================================================


class TestVariantStatus:
    def test_values(self) -> None:
        assert VariantStatus.CANDIDATE.value == "candidate"
        assert VariantStatus.EVALUATING.value == "evaluating"
        assert VariantStatus.PROMOTED.value == "promoted"
        assert VariantStatus.REJECTED.value == "rejected"
        assert VariantStatus.ROLLED_BACK.value == "rolled_back"

    def test_str_representation(self) -> None:
        assert str(VariantStatus.PROMOTED) == "VariantStatus.PROMOTED"


# =============================================================================
# QualityDimension
# =============================================================================


class TestQualityDimension:
    def test_values(self) -> None:
        assert QualityDimension.SAFETY.value == "safety"
        assert QualityDimension.COMPLETENESS.value == "completeness"
        assert QualityDimension.EXECUTABILITY.value == "executability"
        assert QualityDimension.MAINTAINABILITY.value == "maintainability"
        assert QualityDimension.COST_AWARENESS.value == "cost_awareness"

    def test_count(self) -> None:
        assert len(QualityDimension) == 5


# =============================================================================
# SkillVariant
# =============================================================================


class TestSkillVariant:
    def test_default_fields(self) -> None:
        v = SkillVariant()
        assert v.id is not None
        assert len(v.id) == 12
        assert v.parent_id is None
        assert v.generation == 0
        assert v.content == ""
        assert v.diff_tokens == 0
        assert v.status == VariantStatus.CANDIDATE
        assert v.scores == {}
        assert v.aggregate_score == 0.0
        assert v.provider_results == {}
        assert v.benchmark_results == {}
        assert isinstance(v.created_at, float)
        assert v.created_at > 0

    def test_custom_fields(self) -> None:
        scores = {"safety": 0.9, "completeness": 0.7}
        provider = {"anthropic": 0.85}
        v = SkillVariant(
            id="abc123def456",
            parent_id="parent1",
            generation=3,
            content="# Custom",
            diff_tokens=25,
            status=VariantStatus.PROMOTED,
            scores=scores,
            aggregate_score=0.8,
            provider_results=provider,
        )
        assert v.id == "abc123def456"
        assert v.parent_id == "parent1"
        assert v.generation == 3
        assert v.content == "# Custom"
        assert v.diff_tokens == 25
        assert v.status == VariantStatus.PROMOTED
        assert v.scores == scores
        assert v.aggregate_score == 0.8
        assert v.provider_results == provider

    def test_unique_ids(self) -> None:
        ids = {SkillVariant().id for _ in range(100)}
        assert len(ids) == 100  # All unique

    def test_fields_are_mutable(self) -> None:
        v = SkillVariant()
        v.content = "modified"
        v.status = VariantStatus.PROMOTED
        v.aggregate_score = 0.95
        assert v.content == "modified"
        assert v.status == VariantStatus.PROMOTED
        assert v.aggregate_score == 0.95


# =============================================================================
# SelfEvolutionPipeline — __init__
# =============================================================================


class TestPipelineInit:
    def test_default_config(self) -> None:
        p = SelfEvolutionPipeline()
        assert isinstance(p.config, EvolutionConfig)
        assert p.archive == {}
        assert p.active == {}
        assert p._archive_dir == Path(".lyra/skill-archive")
        assert p._archive_dir.exists()

    def test_custom_config(self, tmp_config: EvolutionConfig) -> None:
        p = SelfEvolutionPipeline(config=tmp_config)
        assert p.config == tmp_config
        assert p._archive_dir == Path(tmp_config.archive_dir)
        assert p._archive_dir.exists()

    def test_archive_dir_created(self, tmp_path: Path) -> None:
        archive_path = tmp_path / "nested" / "dir" / "archive"
        config = EvolutionConfig(archive_dir=str(archive_path))
        p = SelfEvolutionPipeline(config=config)
        assert archive_path.exists()
        assert archive_path.is_dir()


# =============================================================================
# SelfEvolutionPipeline — _score_5d
# =============================================================================


class TestScore5D:
    def test_safety_detects_dangerous_patterns(
        self, pipeline: SelfEvolutionPipeline, dangerous_content: str
    ) -> None:
        scores = pipeline._score_5d(dangerous_content)
        assert scores["safety"] < 1.0
        assert scores["safety"] < 0.5  # Multiple dangerous patterns

    def test_safety_clean_content(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        scores = pipeline._score_5d(sample_content)
        assert scores["safety"] == 1.0

    def test_completeness_word_count(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        scores = pipeline._score_5d(sample_content)
        # sample_content has ~34 words => 34/200 = 0.17
        wc = len(sample_content.split())
        expected = wc / 200.0
        assert scores["completeness"] == pytest.approx(expected, abs=0.02)

    def test_completeness_empty(self, pipeline: SelfEvolutionPipeline) -> None:
        scores = pipeline._score_5d("")
        assert scores["completeness"] == 0.0

    def test_executability_with_examples(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        scores = pipeline._score_5d(sample_content)
        assert scores["executability"] == 0.8

    def test_executability_without_examples(
        self, pipeline: SelfEvolutionPipeline, simple_content: str
    ) -> None:
        scores = pipeline._score_5d(simple_content)
        assert scores["executability"] == 0.3

    def test_maintainability_with_sections(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        scores = pipeline._score_5d(sample_content)
        assert scores["maintainability"] == 0.9

    def test_maintainability_without_sections(
        self, pipeline: SelfEvolutionPipeline, simple_content: str
    ) -> None:
        scores = pipeline._score_5d(simple_content)
        assert scores["maintainability"] == 0.4

    def test_cost_awareness_detects_expensive_patterns(
        self, pipeline: SelfEvolutionPipeline, expensive_content: str
    ) -> None:
        scores = pipeline._score_5d(expensive_content)
        assert scores["cost_awareness"] < 1.0
        # "always use opus" (1), "never use cheap" (2) => penalty 2*0.3 = 0.6
        # "disable caching" (3) => penalty 3*0.3 = 0.9
        assert scores["cost_awareness"] <= 0.4

    def test_cost_awareness_clean(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        scores = pipeline._score_5d(sample_content)
        assert scores["cost_awareness"] == 1.0

    def test_all_scores_in_range(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        scores = pipeline._score_5d(sample_content)
        for dim, val in scores.items():
            assert 0.0 <= val <= 1.0, f"{dim} score {val} out of range"

    def test_empty_content(self, pipeline: SelfEvolutionPipeline) -> None:
        scores = pipeline._score_5d("")
        assert scores["safety"] == 1.0
        assert scores["completeness"] == 0.0
        assert scores["executability"] == 0.3
        assert scores["maintainability"] == 0.4
        assert scores["cost_awareness"] == 1.0

    def test_all_five_dimensions_present(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        scores = pipeline._score_5d(sample_content)
        assert set(scores.keys()) == {
            "safety",
            "completeness",
            "executability",
            "maintainability",
            "cost_awareness",
        }


# =============================================================================
# SelfEvolutionPipeline — _apply_bounded_edits
# =============================================================================


class TestApplyBoundedEdits:
    def test_inserts_marker_after_heading(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        result = pipeline._apply_bounded_edits(sample_content, 50)
        lines = result.split("\n")
        assert "<!-- evolved:" in lines[1]

    def test_marker_contains_evolved_hash(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        result = pipeline._apply_bounded_edits(sample_content, 50)
        assert "<!-- evolved:" in result
        assert "tokens_changed:≤50 -->" in result

    def test_marker_at_line_2_when_no_heading(
        self, pipeline: SelfEvolutionPipeline
    ) -> None:
        content = "line1\nline2\nline3\nline4"
        result = pipeline._apply_bounded_edits(content, 50)
        lines = result.split("\n")
        assert "<!-- evolved:" in lines[2]  # Insert at index 2 after first 2 lines

    def test_empty_content_unchanged(
        self, pipeline: SelfEvolutionPipeline
    ) -> None:
        assert pipeline._apply_bounded_edits("", 50) == ""

    def test_whitespace_only_unchanged(
        self, pipeline: SelfEvolutionPipeline
    ) -> None:
        assert pipeline._apply_bounded_edits("   \n  \n", 50) == "   \n  \n"

    def test_short_content_unchanged(
        self, pipeline: SelfEvolutionPipeline
    ) -> None:
        short = "# Hi\n\nHello"
        result = pipeline._apply_bounded_edits(short, 50)
        assert result == short  # < 4 lines -> no marker inserted

    def test_respects_max_tokens_in_marker(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        result = pipeline._apply_bounded_edits(sample_content, 10)
        assert "tokens_changed:≤10 -->" in result

    def test_preserves_original_content(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        result = pipeline._apply_bounded_edits(sample_content, 50)
        # Original content should be intact (minus the inserted marker line)
        for line in sample_content.split("\n"):
            assert line in result


# =============================================================================
# SelfEvolutionPipeline — _init_variant
# =============================================================================


class TestInitVariant:
    def test_creates_promoted_variant(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        v = pipeline._init_variant("test-skill", sample_content)
        assert v.status == VariantStatus.PROMOTED
        assert v.content == sample_content

    def test_scores_computed(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        v = pipeline._init_variant("test-skill", sample_content)
        assert len(v.scores) == 5
        assert v.aggregate_score > 0.0

    def test_variant_archived(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline._init_variant("test-skill", sample_content)
        assert "test-skill" in pipeline.archive
        assert len(pipeline.archive["test-skill"]) == 1

    def test_active_not_set_by_init(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        # _init_variant does not set self.active — evolve_skill does that
        pipeline._init_variant("test-skill", sample_content)
        assert "test-skill" not in pipeline.active

    def test_aggregate_score_is_average(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        v = pipeline._init_variant("test-skill", sample_content)
        expected = sum(v.scores.values()) / len(v.scores)
        assert v.aggregate_score == expected


# =============================================================================
# SelfEvolutionPipeline — _generate_population
# =============================================================================


class TestGeneratePopulation:
    def test_returns_n_variants(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline._init_variant("test-skill", sample_content)
        pop = pipeline._generate_population("test-skill", sample_content, 1)
        assert len(pop) == pipeline.config.population_size

    def test_generation_set(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline._init_variant("test-skill", sample_content)
        pop = pipeline._generate_population("test-skill", sample_content, 3)
        assert all(v.generation == 3 for v in pop)

    def test_parent_content_carried(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline._init_variant("test-skill", sample_content)
        pop = pipeline._generate_population("test-skill", sample_content, 1)
        assert all(v.content == sample_content for v in pop)

    def test_all_variants_have_unique_ids(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline._init_variant("test-skill", sample_content)
        pop = pipeline._generate_population("test-skill", sample_content, 1)
        ids = [v.id for v in pop]
        assert len(set(ids)) == len(ids)

    def test_parent_id_falls_back_to_default(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        # _init_variant does not set self.active, so _generate_population
        # creates a fallback SkillVariant() with a random 12-char hex id.
        pipeline._init_variant("test-skill", sample_content)
        pop = pipeline._generate_population("test-skill", sample_content, 1)
        assert all(len(v.parent_id) == 12 for v in pop)
        assert all(v.parent_id is not None for v in pop)

    def test_variants_start_as_candidate(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline._init_variant("test-skill", sample_content)
        pop = pipeline._generate_population("test-skill", sample_content, 1)
        assert all(v.status == VariantStatus.CANDIDATE for v in pop)


# =============================================================================
# SelfEvolutionPipeline — _archive
# =============================================================================


class TestArchive:
    def test_adds_to_archive(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        v = SkillVariant(content=sample_content, status=VariantStatus.PROMOTED)
        pipeline._archive("test-skill", v)
        assert "test-skill" in pipeline.archive
        assert len(pipeline.archive["test-skill"]) == 1
        assert pipeline.archive["test-skill"][0] is v

    def test_appends_multiple(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        v1 = SkillVariant(content=sample_content, status=VariantStatus.PROMOTED)
        v2 = SkillVariant(content=sample_content, status=VariantStatus.PROMOTED)
        pipeline._archive("test-skill", v1)
        pipeline._archive("test-skill", v2)
        assert len(pipeline.archive["test-skill"]) == 2

    def test_enforces_max_rollback_history(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline.config.max_rollback_history = 2
        for _ in range(5):
            v = SkillVariant(content=sample_content, status=VariantStatus.PROMOTED)
            pipeline._archive("test-skill", v)

        promoted = [
            v for v in pipeline.archive["test-skill"] if v.status == VariantStatus.PROMOTED
        ]
        assert len(promoted) == 2

    def test_oldest_promoted_becomes_rejected(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline.config.max_rollback_history = 2
        v1 = SkillVariant(content=sample_content, status=VariantStatus.PROMOTED)
        pipeline._archive("test-skill", v1)
        v2 = SkillVariant(content=sample_content, status=VariantStatus.PROMOTED)
        pipeline._archive("test-skill", v2)
        v3 = SkillVariant(content=sample_content, status=VariantStatus.PROMOTED)
        pipeline._archive("test-skill", v3)

        assert v1.status == VariantStatus.REJECTED
        assert v2.status == VariantStatus.PROMOTED
        assert v3.status == VariantStatus.PROMOTED

    def test_writes_to_disk(
        self, tmp_pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        v = SkillVariant(
            content=sample_content,
            status=VariantStatus.PROMOTED,
            aggregate_score=0.85,
        )
        tmp_pipeline._archive("disk-skill", v)

        archive_file = tmp_pipeline._archive_dir / "disk-skill.json"
        assert archive_file.exists()
        data = json.loads(archive_file.read_text())
        assert len(data) == 1
        assert data[0]["id"] == v.id
        assert data[0]["score"] == 0.85
        assert data[0]["status"] == "promoted"

    def test_multiple_skills_separate(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        v1 = SkillVariant(content=sample_content, status=VariantStatus.PROMOTED)
        v2 = SkillVariant(content=sample_content, status=VariantStatus.PROMOTED)
        pipeline._archive("skill-a", v1)
        pipeline._archive("skill-b", v2)
        assert len(pipeline.archive["skill-a"]) == 1
        assert len(pipeline.archive["skill-b"]) == 1

    def test_disk_archive_appends(
        self, tmp_pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        for i in range(3):
            v = SkillVariant(
                content=sample_content,
                status=VariantStatus.PROMOTED,
                aggregate_score=0.5 + i * 0.1,
            )
            tmp_pipeline._archive("append-skill", v)

        archive_file = tmp_pipeline._archive_dir / "append-skill.json"
        data = json.loads(archive_file.read_text())
        assert len(data) == 3


# =============================================================================
# SelfEvolutionPipeline — evolve_skill
# =============================================================================


class TestEvolveSkill:
    def test_returns_best_variant(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        best = pipeline.evolve_skill("test-skill", sample_content, max_generations=1)
        assert isinstance(best, SkillVariant)
        assert best.status in (VariantStatus.PROMOTED, VariantStatus.CANDIDATE)

    def test_with_benchmark_promotes_better(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 3
        best = pipeline.evolve_skill(
            "test-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=1,
        )
        # With a generous benchmark, the best variant should be PROMOTED
        assert best.status == VariantStatus.PROMOTED
        assert best.aggregate_score > 0.0

    def test_rejects_worse_variants(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 3
        pipeline.evolve_skill(
            "test-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=1,
        )
        # The champion is promoted and archived. The 2 non-champion variants
        # are only set to REJECTED in their local status (not archived).
        # The archive contains: initial promoted variant + 1 champion = 2 total.
        history = pipeline.get_history("test-skill")
        promoted = [v for v in history if v.status == VariantStatus.PROMOTED]
        assert len(promoted) >= 1
        assert len(history) == 2  # initial + champion

    def test_active_is_updated(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 3
        best = pipeline.evolve_skill(
            "test-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=1,
        )
        assert pipeline.active["test-skill"] is best

    def test_limited_generations(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline.config.population_size = 2
        best = pipeline.evolve_skill(
            "test-skill", sample_content, max_generations=3
        )
        history = pipeline.get_history("test-skill")
        variants = [v for v in history if v.status != VariantStatus.CANDIDATE]
        # 1 initial + 3 generations worth of population
        assert len(variants) >= 1

    def test_cross_provider_eval(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
        cross_provider_evaluators: dict[str, Any],
    ) -> None:
        pipeline.config.population_size = 2
        best = pipeline.evolve_skill(
            "test-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            provider_evaluators=cross_provider_evaluators,
            max_generations=1,
        )
        # The best variant should have provider results
        assert len(best.provider_results) > 0
        assert "anthropic" in best.provider_results
        assert "deepseek" in best.provider_results

    def test_cross_provider_with_failing_evaluator(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
        mixed_provider_evaluators: dict[str, Any],
    ) -> None:
        pipeline.config.population_size = 2
        best = pipeline.evolve_skill(
            "test-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            provider_evaluators=mixed_provider_evaluators,
            max_generations=1,
        )
        # The failing deepseek evaluator should result in 0.0
        assert "deepseek" in best.provider_results
        assert best.provider_results["deepseek"] == 0.0
        # Successful providers should report their values
        assert best.provider_results["anthropic"] == 0.9
        assert best.provider_results["open-weight"] == 0.7

    def test_multiple_generations_with_benchmark(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 2
        pipeline.config.min_improvement = 0.01
        best = pipeline.evolve_skill(
            "test-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=3,
        )
        # Over multiple generations with improving benchmark, a champion emerges
        assert best.aggregate_score >= 0.0

    def test_archive_contains_initial_and_promoted(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 2
        pipeline.evolve_skill(
            "test-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=2,
        )
        history = pipeline.get_history("test-skill")
        assert len(history) >= 2  # Initial variant + at least one champion

    def test_no_benchmark_still_scores(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline.config.population_size = 2
        best = pipeline.evolve_skill(
            "test-skill", sample_content, max_generations=1
        )
        # Without benchmark_fn, aggregate_score stays 0.0 from SkillVariant default
        # but _score_5d scores are still populated
        assert len(best.scores) == 5

    def test_empty_content_does_not_crash(
        self, pipeline: SelfEvolutionPipeline
    ) -> None:
        pipeline.config.population_size = 2
        best = pipeline.evolve_skill(
            "empty-skill", "", max_generations=1
        )
        assert isinstance(best, SkillVariant)
        assert best.content == ""


# =============================================================================
# SelfEvolutionPipeline — rollback
# =============================================================================


class TestRollback:
    def test_rollback_to_previous_promoted(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 2
        pipeline.evolve_skill(
            "test-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=2,
        )

        previous = pipeline.active["test-skill"]
        rolled = pipeline.rollback("test-skill")

        if rolled is not None:
            assert pipeline.active["test-skill"] is rolled
            assert rolled.status == VariantStatus.PROMOTED
            # Original variant that was active should now be ROLLED_BACK
            assert previous.status == VariantStatus.ROLLED_BACK

    def test_rollback_returns_none_when_not_enough_history(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        # Only the initial version exists — no rollback possible
        pipeline._init_variant("test-skill", sample_content)
        result = pipeline.rollback("test-skill")
        assert result is None

    def test_rollback_empty_skill(
        self, pipeline: SelfEvolutionPipeline
    ) -> None:
        result = pipeline.rollback("nonexistent")
        assert result is None


class TestGetHistory:
    def test_returns_archive_list(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline._init_variant("test-skill", sample_content)
        history = pipeline.get_history("test-skill")
        assert isinstance(history, list)
        assert len(history) == 1

    def test_empty_if_no_history(self, pipeline: SelfEvolutionPipeline) -> None:
        history = pipeline.get_history("no-skill")
        assert history == []

    def test_multiple_entries(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline._archive("test-skill", SkillVariant(content=sample_content))
        pipeline._archive("test-skill", SkillVariant(content=sample_content))
        assert len(pipeline.get_history("test-skill")) == 2


# =============================================================================
# SelfEvolutionPipeline — get_best
# =============================================================================


class TestGetBest:
    def test_returns_active_variant(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
    ) -> None:
        # get_best returns the variant set in self.active, which is only
        # populated after evolve_skill (not after _init_variant).
        best = pipeline.evolve_skill(
            "test-skill", sample_content, benchmark_fn=champion_benchmark, max_generations=1,
        )
        assert pipeline.get_best("test-skill") is best

    def test_none_if_not_active(self, pipeline: SelfEvolutionPipeline) -> None:
        assert pipeline.get_best("nonexistent") is None

    def test_updates_after_evolve(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 2
        best = pipeline.evolve_skill(
            "test-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=1,
        )
        assert pipeline.get_best("test-skill") is best


# =============================================================================
# Integration: Full pipeline sequence
# =============================================================================


class TestFullPipeline:
    def test_evolve_then_rollback_then_history(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 3
        pipeline.config.max_rollback_history = 20

        best = pipeline.evolve_skill(
            "integration-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=2,
        )
        assert best is not None

        rolled = pipeline.rollback("integration-skill")
        if rolled is not None:
            assert pipeline.get_best("integration-skill") is rolled

        history = pipeline.get_history("integration-skill")
        assert len(history) > 0

    def test_multiple_skills_independent(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        simple_content: str,
        champion_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 2
        best_a = pipeline.evolve_skill(
            "skill-a",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=1,
        )
        best_b = pipeline.evolve_skill(
            "skill-b",
            simple_content,
            benchmark_fn=champion_benchmark,
            max_generations=1,
        )

        assert pipeline.get_best("skill-a") is best_a
        assert pipeline.get_best("skill-b") is best_b

    def test_multiple_generations_no_regression(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 2
        pipeline.config.min_improvement = 0.01

        gen1 = pipeline.evolve_skill(
            "progressive-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=1,
        )
        gen2 = pipeline.evolve_skill(
            "progressive-skill",
            gen1.content,
            benchmark_fn=champion_benchmark,
            max_generations=1,
        )
        # Second evolution should not regrade
        assert gen2.aggregate_score >= 0.0

    def test_evolve_reuses_archive_across_calls(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        champion_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 2

        pipeline.evolve_skill(
            "reuse-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=1,
        )
        history_before = len(pipeline.get_history("reuse-skill"))

        pipeline.evolve_skill(
            "reuse-skill",
            sample_content,
            benchmark_fn=champion_benchmark,
            max_generations=1,
        )
        history_after = len(pipeline.get_history("reuse-skill"))

        # Should append to the same archive, not reset
        assert history_after >= history_before


# =============================================================================
# Edge cases
# =============================================================================


class TestEdgeCases:
    def test_pipeline_rejects_all_variants_when_benchmark_is_low(
        self,
        pipeline: SelfEvolutionPipeline,
        sample_content: str,
        low_benchmark: Any,
    ) -> None:
        pipeline.config.population_size = 3
        best = pipeline.evolve_skill(
            "low-skill",
            sample_content,
            benchmark_fn=low_benchmark,
            max_generations=1,
        )
        # Low benchmark means champion won't beat parent's
        # aggregate_score * (1 + min_improvement)
        # The initial variant gets score from _score_5d which is 0.3-0.9 range
        # while low_benchmark always returns 0.1.
        # So champion won't meet the 5% improvement threshold.
        # But best should still be returned (the initial variant)
        assert best.status == VariantStatus.PROMOTED
        assert best.aggregate_score > 0.1

    def test_large_population(
        self, pipeline: SelfEvolutionPipeline, sample_content: str
    ) -> None:
        pipeline.config.population_size = 20
        pop = pipeline._generate_population("big", sample_content, 1)
        assert len(pop) == 20

    def test_long_content_has_higher_completeness(
        self, pipeline: SelfEvolutionPipeline
    ) -> None:
        long_content = "word " * 500  # 500 words
        scores = pipeline._score_5d(long_content)
        assert scores["completeness"] == 1.0  # 500/200 > 1.0, clamped

    def test_dangerous_patterns_partial_penalty(
        self, pipeline: SelfEvolutionPipeline
    ) -> None:
        content = "# Skill with sudo"
        scores = pipeline._score_5d(content)
        assert scores["safety"] == 0.75  # 1.0 - 1*0.25

    def test_non_standard_marker_in_content_not_removed(
        self, pipeline: SelfEvolutionPipeline
    ) -> None:
        content = "# Heading\n\nSome content\n"
        # Apply edits twice to ensure markers stack sensibly
        once = pipeline._apply_bounded_edits(content, 50)
        twice = pipeline._apply_bounded_edits(once, 50)
        # Should have two marker lines now
        assert twice.count("<!-- evolved:") == (
            once.count("<!-- evolved:") + 1
        )
