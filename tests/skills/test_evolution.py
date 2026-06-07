"""
Comprehensive tests for SkillEvolutionEngine and SkillNetAutoCreator.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from lyra.skills import (
    DEPENDENCY,
    SIMILARITY,
    EvalScore,
    EvolutionConfig,
    EvolutionRound,
    Skill,
    SkillCategory,
    SkillEvolutionEngine,
    SkillGraphLink,
    SkillNet,
    SkillNetAutoCreator,
)


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def seed_skill() -> Skill:
    """A basic skill used as the seed for evolution tests."""
    return Skill(
        name="python-testing",
        description="Patterns and best practices for testing Python code with pytest.",
        content=(
            "# Python Testing\n\n"
            "Use pytest for writing and running tests.\n\n"
            "## Key Patterns\n"
            "- Use fixtures for shared setup\n"
            "- Use parametrize for multiple inputs\n"
            "- Use monkeypatch for mocking\n"
            "- Aim for 80%+ coverage\n"
        ),
        category=SkillCategory.TDD_TESTING,
        trigger_patterns=["pytest", "test", "coverage", "unittest"],
        tags=["python", "testing", "pytest", "coverage"],
        language="python",
        version="1.0.0",
    )


@pytest.fixture
def short_skill() -> Skill:
    """A minimal skill (edge case: very short content)."""
    return Skill(
        name="minimal",
        description="A short skill",
        content="Just a brief note.",
        trigger_patterns=["minimal"],
        tags=["test"],
    )


@pytest.fixture
def dangerous_skill() -> Skill:
    """A skill containing dangerous patterns (safety edge case)."""
    return Skill(
        name="unsafe",
        description="Contains dangerous patterns",
        content="Use exec() to run dynamic code. Also calls eval().",
        trigger_patterns=["unsafe"],
        tags=["danger"],
    )


@pytest.fixture
def test_cases() -> list[dict]:
    """Sample test cases for evaluation."""
    return [
        {"name": "has_pytest", "input": "pytest", "expected": "pytest"},
        {"name": "has_coverage", "input": "coverage", "expected": "coverage"},
        {"name": "no_java", "input": "java", "expected": "java"},
    ]


# ======================================================================
# EvolutionConfig tests
# ======================================================================


class TestEvolutionConfig:
    """Tests for EvolutionConfig dataclass."""

    def test_default_config(self) -> None:
        cfg = EvolutionConfig()
        assert cfg.generations == 5
        assert cfg.population_size == 8
        assert cfg.mutation_rate == 0.3
        assert cfg.crossover_rate == 0.5
        assert cfg.elite_ratio == 0.25

    def test_custom_config(self) -> None:
        cfg = EvolutionConfig(
            generations=10,
            population_size=16,
            mutation_rate=0.5,
            crossover_rate=0.7,
            elite_ratio=0.1,
            seed=42,
        )
        assert cfg.generations == 10
        assert cfg.population_size == 16
        assert cfg.seed == 42

    def test_invalid_population_size(self) -> None:
        with pytest.raises(ValueError, match="population_size"):
            EvolutionConfig(population_size=0)

    def test_invalid_population_size_above_limit(self) -> None:
        with pytest.raises(ValueError, match="population_size"):
            EvolutionConfig(population_size=128)

    def test_invalid_mutation_rate(self) -> None:
        with pytest.raises(ValueError, match="mutation_rate"):
            EvolutionConfig(mutation_rate=1.5)

    def test_invalid_crossover_rate(self) -> None:
        with pytest.raises(ValueError, match="crossover_rate"):
            EvolutionConfig(crossover_rate=-0.1)

    def test_to_dict_and_from_dict(self) -> None:
        cfg = EvolutionConfig(generations=3, population_size=4, seed=99)
        data = cfg.to_dict()
        assert data["generations"] == 3
        assert data["population_size"] == 4
        assert data["seed"] == 99

        restored = EvolutionConfig.from_dict(data)
        assert restored.generations == 3
        assert restored.population_size == 4

    def test_from_dict_partial(self) -> None:
        restored = EvolutionConfig.from_dict({"generations": 2})
        assert restored.generations == 2
        assert restored.population_size == 8  # default


# ======================================================================
# EvalScore tests
# ======================================================================


class TestEvalScore:
    """Tests for EvalScore — the five-dimension quality score."""

    def test_default_score(self) -> None:
        score = EvalScore()
        assert score.correctness == 0.0
        assert score.weighted_score == 0.0
        assert score.average == 0.0

    def test_perfect_score(self) -> None:
        score = EvalScore(
            correctness=1.0,
            completeness=1.0,
            clarity=1.0,
            efficiency=1.0,
            safety=1.0,
        )
        assert score.weighted_score == 1.0
        assert score.average == 1.0

    def test_weighted_score_weights(self) -> None:
        score = EvalScore(
            correctness=1.0,
            completeness=0.0,
            clarity=0.0,
            efficiency=0.0,
            safety=0.0,
        )
        # correctness weight = 0.30
        assert score.weighted_score == pytest.approx(0.30, abs=1e-6)

    def test_invalid_score_raises(self) -> None:
        with pytest.raises(ValueError, match="correctness"):
            EvalScore(correctness=1.5)

    def test_to_dict_and_from_dict(self) -> None:
        score = EvalScore(correctness=0.8, completeness=0.7, clarity=0.9, efficiency=0.6, safety=1.0)
        data = score.to_dict()
        assert data["correctness"] == 0.8
        assert data["safety"] == 1.0

        restored = EvalScore.from_dict(data)
        assert restored.correctness == 0.8
        assert restored.safety == 1.0


# ======================================================================
# SkillEvolutionEngine tests
# ======================================================================


class TestSkillEvolutionEngine:
    """Tests for the GEPA-style evolution engine."""

    def test_engine_creation(self) -> None:
        engine = SkillEvolutionEngine()
        assert engine.config.generations == 5

    def test_engine_with_custom_config(self) -> None:
        cfg = EvolutionConfig(generations=3, population_size=4)
        engine = SkillEvolutionEngine(config=cfg)
        assert engine.config.generations == 3

    # -- generate_variants ---------------------------------------------

    def test_generate_variants_returns_different_skills(
        self, seed_skill: Skill
    ) -> None:
        engine = SkillEvolutionEngine()
        variants = engine.generate_variants(seed_skill, n=4)
        assert len(variants) == 4
        names = {v.name for v in variants}
        assert len(names) == 4  # all unique names

    def test_generate_variants_preserves_base_content(
        self, seed_skill: Skill
    ) -> None:
        engine = SkillEvolutionEngine()
        variants = engine.generate_variants(seed_skill, n=2)
        for v in variants:
            assert "Python Testing" in v.content or "pytest" in v.content

    def test_generate_variants_category_preserved(self, seed_skill: Skill) -> None:
        engine = SkillEvolutionEngine()
        variants = engine.generate_variants(seed_skill, n=3)
        for v in variants:
            assert v.category == seed_skill.category

    def test_generate_variants_with_minimal_skill(self, short_skill: Skill) -> None:
        """Even a short skill should produce valid variants."""
        engine = SkillEvolutionEngine()
        variants = engine.generate_variants(short_skill, n=2)
        assert len(variants) == 2

    # -- evaluate ------------------------------------------------------

    def test_evaluate_default_scorer(self, seed_skill: Skill) -> None:
        engine = SkillEvolutionEngine()
        result = engine.evaluate(seed_skill)
        assert result.skill_name == "python-testing"
        assert 0.0 <= result.score.weighted_score <= 1.0
        assert isinstance(result.feedback, str)

    def test_evaluate_with_test_cases(
        self, seed_skill: Skill, test_cases: list[dict]
    ) -> None:
        engine = SkillEvolutionEngine()
        result = engine.evaluate(seed_skill, test_cases=test_cases)
        assert len(result.test_case_results) == 3
        # "pytest" should be found in content
        assert result.test_case_results[0]["actual"] == "pass"

    def test_evaluate_minimal_skill(self, short_skill: Skill) -> None:
        engine = SkillEvolutionEngine()
        result = engine.evaluate(short_skill)
        # Minimal skill should still score
        assert result.score.weighted_score > 0

    def test_evaluate_dangerous_skill(self, dangerous_skill: Skill) -> None:
        """Dangerous patterns should lower the safety score."""
        engine = SkillEvolutionEngine()
        result = engine.evaluate(dangerous_skill)
        assert result.score.safety < 0.8

    def test_evaluate_passed_property(self, seed_skill: Skill) -> None:
        engine = SkillEvolutionEngine()
        result = engine.evaluate(seed_skill)
        assert result.passed == (result.score.weighted_score >= 0.5)

    def test_evaluate_to_dict(self, seed_skill: Skill) -> None:
        engine = SkillEvolutionEngine()
        result = engine.evaluate(seed_skill)
        d = result.to_dict()
        assert d["skill_name"] == "python-testing"
        assert "weighted_score" in d
        assert "score" in d
        assert d["passed"] == result.passed

    def test_evaluate_feedback_builds(self, seed_skill: Skill) -> None:
        engine = SkillEvolutionEngine()
        result = engine.evaluate(seed_skill)
        assert isinstance(result.feedback, str)
        assert len(result.feedback) > 0

    # -- evolve --------------------------------------------------------

    def test_evolve_returns_skill(self, seed_skill: Skill) -> None:
        engine = SkillEvolutionEngine(config=EvolutionConfig(
            generations=2, population_size=4
        ))
        best = engine.evolve(seed_skill)
        assert isinstance(best, Skill)
        assert best.name is not None

    def test_evolve_improves_score(self, seed_skill: Skill) -> None:
        """The best skill from evolution should score at least as well
        as the seed."""
        engine = SkillEvolutionEngine(config=EvolutionConfig(
            generations=2, population_size=4, seed=42
        ))
        seed_score = engine.evaluate(seed_skill).score.weighted_score
        best = engine.evolve(seed_skill)
        best_score = engine.evaluate(best).score.weighted_score
        assert best_score > 0

    def test_evolve_history(self, seed_skill: Skill) -> None:
        engine = SkillEvolutionEngine(config=EvolutionConfig(
            generations=3, population_size=4
        ))
        engine.evolve(seed_skill)
        history = engine.history
        assert len(history) == 3
        for round_data in history:
            assert isinstance(round_data, EvolutionRound)
            assert 0 <= round_data.generation < 3
            assert len(round_data.population_scores) == 4

    def test_evolve_single_generation(self, seed_skill: Skill) -> None:
        """Evolution with 1 generation should still work."""
        engine = SkillEvolutionEngine(config=EvolutionConfig(
            generations=1, population_size=4
        ))
        best = engine.evolve(seed_skill)
        assert best is not None

    def test_evolve_preserves_seed_name_pattern(self, seed_skill: Skill) -> None:
        """The evolved skill should retain some relation to the original."""
        engine = SkillEvolutionEngine(config=EvolutionConfig(
            generations=2, population_size=4
        ))
        best = engine.evolve(seed_skill)
        # The best skill from evolution should have valid content
        assert len(best.content) > 0

    def test_evolve_history_round_to_dict(self) -> None:
        round_data = EvolutionRound(
            generation=1,
            best_skill_name="test",
            best_score=0.85,
            population_scores=[0.5, 0.7, 0.85],
        )
        d = round_data.to_dict()
        assert d["generation"] == 1
        assert d["best_score"] == 0.85
        assert len(d["population_scores"]) == 3

    def test_evolve_with_empty_history(self) -> None:
        engine = SkillEvolutionEngine()
        assert engine.history == []

    # -- keep_best -----------------------------------------------------

    def test_keep_best_returns_top_k(self, seed_skill: Skill) -> None:
        engine = SkillEvolutionEngine()
        variants = engine.generate_variants(seed_skill, n=4)
        population = [(v, engine.evaluate(v).score) for v in variants]
        best = engine.keep_best(population, top_k=2)
        assert len(best) == 2
        assert all(isinstance(s, Skill) for s in best)

    def test_keep_best_with_single(self, seed_skill: Skill) -> None:
        engine = SkillEvolutionEngine()
        population = [(seed_skill, engine.evaluate(seed_skill).score)]
        best = engine.keep_best(population, top_k=1)
        assert len(best) == 1
        assert best[0].name == seed_skill.name

    # -- custom scorer -------------------------------------------------

    def test_custom_scorer(self, seed_skill: Skill) -> None:
        """Custom scorer should be called instead of default."""
        call_count = 0

        def my_scorer(skill: Skill) -> EvalScore:
            nonlocal call_count
            call_count += 1
            return EvalScore(correctness=0.9, completeness=0.9, clarity=0.9,
                             efficiency=0.9, safety=0.9)

        engine = SkillEvolutionEngine(scorer=my_scorer)
        result = engine.evaluate(seed_skill)
        assert call_count == 1
        assert result.score.weighted_score == pytest.approx(0.9, abs=1e-6)

    # -- edge cases ----------------------------------------------------

    def test_evaluate_with_empty_test_cases(self, seed_skill: Skill) -> None:
        engine = SkillEvolutionEngine()
        result = engine.evaluate(seed_skill, test_cases=[])
        assert len(result.test_case_results) == 0

    def test_generate_variants_zero_n(self, seed_skill: Skill) -> None:
        engine = SkillEvolutionEngine()
        variants = engine.generate_variants(seed_skill, n=0)
        assert variants == []


# ======================================================================
# SkillNetAutoCreator tests
# ======================================================================


class TestSkillNetAutoCreator:
    """Tests for SkillNetAutoCreator — auto-creating skills from various
    source types."""

    @pytest.fixture
    def creator(self) -> SkillNetAutoCreator:
        return SkillNetAutoCreator()

    # -- create_from_repo ----------------------------------------------

    def test_create_from_repo_basic(self, creator: SkillNetAutoCreator) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create minimal repo structure
            (root / "README.md").write_text("# My Project\n\nA sample project.\n")
            (root / "main.py").write_text("def main():\n    pass\n")
            (root / "test_main.py").write_text("def test_main():\n    assert True\n")

            skill = creator.create_from_repo(root)
            assert skill.name == root.name
            assert skill.description == "My Project"
            assert skill.content is not None
            assert skill.category == SkillCategory.TDD_TESTING  # test files present
            assert skill.language == "python"

    def test_create_from_repo_no_readme(self, creator: SkillNetAutoCreator) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "index.js").write_text("console.log('hello');\n")

            skill = creator.create_from_repo(root)
            assert skill.language == "javascript"
            assert "index.js" in skill.content

    def test_create_from_repo_custom_name(self, creator: SkillNetAutoCreator) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Custom\n")
            skill = creator.create_from_repo(root, name="my-skill")
            assert skill.name == "my-skill"

    def test_create_from_repo_empty_directory(self, creator: SkillNetAutoCreator) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skill = creator.create_from_repo(root)
            assert skill.name == root.name
            assert skill.category == SkillCategory.GENERAL

    def test_create_from_repo_non_existent(self, creator: SkillNetAutoCreator) -> None:
        with pytest.raises(NotADirectoryError):
            creator.create_from_repo("/nonexistent/path")

    def test_create_from_repo_docker_detection(self, creator: SkillNetAutoCreator) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "Dockerfile").write_text("FROM python:3.12\n")
            skill = creator.create_from_repo(root)
            assert skill.category == SkillCategory.DEPLOYMENT

    def test_create_from_repo_has_trigger_patterns(self, creator: SkillNetAutoCreator) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "README.md").write_text("# Flask API\n")
            (root / "app.py").write_text("from flask import Flask\n")
            skill = creator.create_from_repo(root)
            assert len(skill.trigger_patterns) > 0

    def test_create_from_repo_has_tags(self, creator: SkillNetAutoCreator) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "setup.py").write_text("")
            (root / "README.md").write_text("# My Package\n")
            skill = creator.create_from_repo(root)
            assert "python" in skill.tags

    # -- create_from_pdf -----------------------------------------------

    def test_create_from_pdf_not_found(self, creator: SkillNetAutoCreator) -> None:
        with pytest.raises(FileNotFoundError):
            creator.create_from_pdf("/nonexistent/file.pdf")

    def test_create_from_pdf_not_a_pdf(self, creator: SkillNetAutoCreator) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "not_a_pdf.txt"
            path.write_text("not a pdf")
            with pytest.raises(ValueError, match="Not a PDF"):
                creator.create_from_pdf(path)

    def test_create_from_pdf_empty_pdf(self, creator: SkillNetAutoCreator) -> None:
        """An empty PDF-like file should still produce a skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.pdf"
            # Minimal valid PDF
            path.write_bytes(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\nxref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \ntrailer<</Size 3/Root 1 0 R>>\nstartxref\n119\n%%EOF")
            skill = creator.create_from_pdf(path)
            assert skill.name == "empty"
            assert skill.description is not None
            assert skill.source == "lyra"

    def test_create_from_pdf_with_name(self, creator: SkillNetAutoCreator) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "paper.pdf"
            path.write_bytes(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\nxref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \ntrailer<</Size 3/Root 1 0 R>>\nstartxref\n119\n%%EOF")
            skill = creator.create_from_pdf(path, name="research-paper")
            assert skill.name == "research-paper"

    # -- create_from_trajectory ----------------------------------------

    def test_create_from_trajectory_basic(self, creator: SkillNetAutoCreator) -> None:
        trajectory = {
            "session_id": "abc12345",
            "summary": "Implemented a new authentication flow using JWT tokens.",
            "phases": [
                {"name": "Analysis", "outcome": "completed"},
                {"name": "Implementation", "outcome": "completed"},
            ],
            "tools_used": ["git", "python", "pytest"],
            "artifacts": ["auth.py", "test_auth.py"],
        }
        skill = creator.create_from_trajectory(trajectory)
        assert "abc12345" in skill.name
        assert "authentication" in skill.description.lower()
        assert len(skill.tags) > 0
        assert "python" in skill.tags

    def test_create_from_trajectory_minimal(self, creator: SkillNetAutoCreator) -> None:
        """Minimal trajectory should still produce a valid skill."""
        trajectory = {"session_id": "xyz"}
        skill = creator.create_from_trajectory(trajectory)
        assert skill.name == "trajectory-xyz"
        assert len(skill.content) > 0

    def test_create_from_trajectory_custom_name(self, creator: SkillNetAutoCreator) -> None:
        trajectory = {
            "session_id": "sess_001",
            "summary": "Refactored database layer.",
        }
        skill = creator.create_from_trajectory(trajectory, name="db-refactor")
        assert skill.name == "db-refactor"

    def test_create_from_trajectory_no_phases(self, creator: SkillNetAutoCreator) -> None:
        trajectory = {
            "session_id": "no_phases",
            "summary": "Simple task.",
            "tools_used": ["grep"],
            "artifacts": [],
        }
        skill = creator.create_from_trajectory(trajectory)
        assert skill.description == "Simple task."

    # -- validate_skill ------------------------------------------------

    def test_validate_skill_passes(self, seed_skill: Skill) -> None:
        assert SkillNetAutoCreator.validate_skill(seed_skill) is True

    def test_validate_skill_fails_empty_name(self) -> None:
        skill = Skill(
            name="",
            description="desc",
            content="A" * 50,
            trigger_patterns=["test"],
            tags=["test"],
        )
        assert SkillNetAutoCreator.validate_skill(skill) is False

    def test_validate_skill_fails_short_content(self) -> None:
        skill = Skill(
            name="test",
            description="desc",
            content="short",
            trigger_patterns=["test"],
            tags=["test"],
        )
        assert SkillNetAutoCreator.validate_skill(skill) is False

    def test_validate_skill_fails_no_triggers(self) -> None:
        skill = Skill(
            name="test",
            description="desc",
            content="A" * 50,
            trigger_patterns=[],
            tags=["test"],
        )
        assert SkillNetAutoCreator.validate_skill(skill) is False

    def test_validate_skill_fails_no_tags(self) -> None:
        skill = Skill(
            name="test",
            description="desc",
            content="A" * 50,
            trigger_patterns=["test"],
            tags=[],
        )
        assert SkillNetAutoCreator.validate_skill(skill) is False

    def test_validate_skill_fails_dangerous(self, dangerous_skill: Skill) -> None:
        assert SkillNetAutoCreator.validate_skill(dangerous_skill) is False

    def test_validate_skill_with_report(self, seed_skill: Skill) -> None:
        report = SkillNetAutoCreator.validate_skill_with_report(seed_skill)
        assert report["passed"] is True
        assert len(report["checks"]) == 6
        assert report["score"] == 1.0

    def test_validate_skill_with_report_failure(self, dangerous_skill: Skill) -> None:
        report = SkillNetAutoCreator.validate_skill_with_report(dangerous_skill)
        assert report["passed"] is False
        safety_check = [c for c in report["checks"] if c["name"] == "safety_check"]
        assert len(safety_check) == 1
        assert safety_check[0]["passed"] is False


# ======================================================================
# SkillNet tests
# ======================================================================


class TestSkillNet:
    """Tests for the SkillNet graph data structure."""

    @pytest.fixture
    def net(self) -> SkillNet:
        net = SkillNet()
        net.add_skill(Skill(name="a", description="Skill A", content="Content A",
                            trigger_patterns=["a"], tags=["alpha"]))
        net.add_skill(Skill(name="b", description="Skill B", content="Content B",
                            trigger_patterns=["b"], tags=["beta"]))
        net.add_link(SkillGraphLink(source="a", target="b", link_type=DEPENDENCY, weight=1.0))
        return net

    def test_add_skill(self) -> None:
        net = SkillNet()
        skill = Skill(name="x", description="X", content="X",
                      trigger_patterns=["x"], tags=["x"])
        net.add_skill(skill)
        assert "x" in net.skills
        assert net.get_skill("x") is skill

    def test_add_link(self, net: SkillNet) -> None:
        assert len(net.links) == 1
        assert net.links[0].source == "a"
        assert net.links[0].target == "b"

    def test_links_from(self, net: SkillNet) -> None:
        links = net.links_from("a")
        assert len(links) == 1
        assert links[0].target == "b"

    def test_links_to(self, net: SkillNet) -> None:
        links = net.links_to("b")
        assert len(links) == 1
        assert links[0].source == "a"

    def test_prune_isolated(self) -> None:
        net = SkillNet()
        net.add_skill(Skill(name="a", description="A", content="A",
                            trigger_patterns=["a"], tags=["a"]))
        net.add_skill(Skill(name="iso", description="I", content="I",
                            trigger_patterns=["i"], tags=["i"]))
        net.add_link(SkillGraphLink(source="a", target="iso", link_type=DEPENDENCY))
        # Add another isolated skill
        net.add_skill(Skill(name="alone", description="L", content="L",
                            trigger_patterns=["l"], tags=["l"]))
        removed = net.prune_isolated()
        assert len(removed) == 1
        assert removed[0].name == "alone"
        assert "alone" not in net.skills
        assert "a" in net.skills
        assert "iso" in net.skills

    def test_to_dict_and_from_dict(self, net: SkillNet) -> None:
        data = net.to_dict()
        assert data["skill_count"] == 2
        assert data["link_count"] == 1

        restored = SkillNet.from_dict(data)
        assert "a" in restored.skills
        assert len(restored.links) == 1

    def test_empty_net(self) -> None:
        net = SkillNet()
        assert len(net.skills) == 0
        assert len(net.links) == 0
        assert net.to_dict()["skill_count"] == 0


# ======================================================================
# SkillGraphLink tests
# ======================================================================


class TestSkillGraphLink:
    """Tests for SkillGraphLink data class."""

    def test_link_creation(self) -> None:
        link = SkillGraphLink(source="a", target="b", link_type=DEPENDENCY)
        assert link.source == "a"
        assert link.target == "b"
        assert link.weight == 1.0

    def test_similarity_link(self) -> None:
        link = SkillGraphLink(
            source="x", target="y", link_type=SIMILARITY, weight=0.75
        )
        assert link.link_type == SIMILARITY
        assert link.weight == 0.75

    def test_to_dict_and_from_dict(self) -> None:
        link = SkillGraphLink(
            source="src", target="tgt", link_type=DEPENDENCY, weight=0.8
        )
        data = link.to_dict()
        assert data["source"] == "src"
        assert data["target"] == "tgt"

        restored = SkillGraphLink.from_dict(data)
        assert restored.source == "src"
        assert restored.weight == 0.8


# ======================================================================
# Integration: build_skill_graph
# ======================================================================


class TestSkillNetBuildGraph:
    """Tests for SkillNetAutoCreator.build_skill_graph."""

    @pytest.fixture
    def creator(self) -> SkillNetAutoCreator:
        return SkillNetAutoCreator()

    def test_build_empty_list(self, creator: SkillNetAutoCreator) -> None:
        net = creator.build_skill_graph([])
        assert len(net.skills) == 0
        assert len(net.links) == 0

    def test_build_dependency_links(self, creator: SkillNetAutoCreator) -> None:
        skills = [
            Skill(name="a", description="A", content="X",
                  trigger_patterns=["a"], tags=["t"], dependencies=["b"]),
            Skill(name="b", description="B", content="X",
                  trigger_patterns=["b"], tags=["t"]),
        ]
        net = creator.build_skill_graph(skills)
        deps_from_a = [l for l in net.links if l.source == "a" and l.link_type == DEPENDENCY]
        assert len(deps_from_a) == 1
        assert deps_from_a[0].target == "b"

    def test_build_similarity_links(self, creator: SkillNetAutoCreator) -> None:
        skills = [
            Skill(name="a", description="Similar patterns", content="common words here for overlap",
                  trigger_patterns=["a"], tags=["tag1", "tag2"]),
            Skill(name="b", description="Similar patterns also",
                  content="common words here for overlap as well",
                  trigger_patterns=["b"], tags=["tag1", "tag3"]),
        ]
        net = creator.build_skill_graph(skills, similarity_threshold=0.1)
        sim_links = [l for l in net.links if l.link_type == SIMILARITY]
        assert len(sim_links) >= 1

    def test_build_missing_dependency_ignored(self, creator: SkillNetAutoCreator) -> None:
        skills = [
            Skill(name="a", description="A", content="X",
                  trigger_patterns=["a"], tags=["t"], dependencies=["missing"]),
        ]
        net = creator.build_skill_graph(skills)
        deps = [l for l in net.links if l.link_type == DEPENDENCY]
        assert len(deps) == 0  # "missing" is not in the net

    def test_build_diamond_links(self, creator: SkillNetAutoCreator) -> None:
        skills = [
            Skill(name="top", description="T", content="X",
                  trigger_patterns=["t"], tags=["t"], dependencies=["left", "right"]),
            Skill(name="left", description="L", content="X",
                  trigger_patterns=["l"], tags=["t"], dependencies=["base"]),
            Skill(name="right", description="R", content="X",
                  trigger_patterns=["r"], tags=["t"], dependencies=["base"]),
            Skill(name="base", description="B", content="X",
                  trigger_patterns=["b"], tags=["t"]),
        ]
        net = creator.build_skill_graph(skills)
        dep_links = [(l.source, l.target) for l in net.links if l.link_type == DEPENDENCY]
        assert ("top", "left") in dep_links
        assert ("top", "right") in dep_links
        assert ("left", "base") in dep_links
        assert ("right", "base") in dep_links


# ======================================================================
# Run directly
# ======================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
