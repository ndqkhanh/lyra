"""15+ tests for SkillGenerator — generation, fallback, quality scoring, and domain generation."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import pytest
from lyra_skill_generator.generator import SkillGenerator
from lyra_skill_generator.models import (
    GeneratedSkill,
    GeneratorConfig,
    SkillCatalog,
    SkillDomain,
    SkillQualityReport,
    SkillTemplate,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_output() -> str:
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def generator(tmp_output: str) -> SkillGenerator:
    cfg = GeneratorConfig(output_dir=tmp_output, enable_llm=False)
    return SkillGenerator(config=cfg)


@pytest.fixture
def generator_with_catalog(tmp_output: str) -> SkillGenerator:
    cfg = GeneratorConfig(output_dir=tmp_output, enable_llm=False)
    catalog = SkillCatalog()
    custom = SkillTemplate(
        domain=SkillDomain.SECURITY,
        name="custom_audit",
        description="Custom security audit",
        trigger_keywords=["custom", "audit"],
        sections=["scope", "findings"],
        difficulty=0.9,
    )
    catalog.register(custom)
    return SkillGenerator(config=cfg, catalog=catalog)


# ── Initialization ──────────────────────────────────────────────────────────


class TestGeneratorInit:
    def test_default_initialization(self) -> None:
        gen = SkillGenerator()
        assert gen.catalog.count == 21  # all 21 built-in templates
        assert gen.config.enable_llm is True
        assert gen.generated_count == 0

    def test_custom_config(self) -> None:
        cfg = GeneratorConfig(enable_llm=False)
        gen = SkillGenerator(config=cfg)
        assert gen.config.enable_llm is False

    def test_custom_catalog(self) -> None:
        catalog = SkillCatalog()
        gen = SkillGenerator(catalog=catalog)
        assert gen.catalog.count == 21  # still registers built-in templates

    def test_repr(self) -> None:
        gen = SkillGenerator()
        r = repr(gen)
        assert "SkillGenerator" in r
        assert "catalog_size=21" in r


# ── Fallback Generation ─────────────────────────────────────────────────────


class TestFallbackGeneration:
    def test_fallback_generates_content(self, generator: SkillGenerator) -> None:
        skill = generator.generate("function_generator")
        assert isinstance(skill, GeneratedSkill)
        assert skill.template_name == "function_generator"
        assert len(skill.content) > 0

    def test_fallback_has_metadata(self, generator: SkillGenerator) -> None:
        skill = generator.generate("ci_pipeline_generator")
        assert "metadata" in skill.content.lower()
        assert "domain:" in skill.content.lower()

    def test_fallback_has_triggers(self, generator: SkillGenerator) -> None:
        skill = generator.generate("unit_test_writer")
        assert "triggers" in skill.content.lower()
        assert "keywords" in skill.content.lower()

    def test_fallback_has_sections(self, generator: SkillGenerator) -> None:
        skill = generator.generate("root_cause_analysis")
        assert "sections" in skill.content.lower()

    def test_fallback_has_quality_checks(self, generator: SkillGenerator) -> None:
        skill = generator.generate("data_pipeline")
        assert "quality_checks" in skill.content.lower()

    def test_fallback_generated_version(self, generator: SkillGenerator) -> None:
        skill = generator.generate("api_client")
        assert skill.version == "1.0.0"

    def test_fallback_unknown_template(self, generator: SkillGenerator) -> None:
        with pytest.raises(ValueError, match="Unknown template"):
            generator.generate("nonexistent_template")


# ── Domain Generation ───────────────────────────────────────────────────────


class TestDomainGeneration:
    def test_generate_domain_returns_all(self, generator: SkillGenerator) -> None:
        skills = generator.generate_domain(SkillDomain.CODING)
        assert len(skills) == 3  # 3 coding templates

    def test_generate_domain_correct_domain(self, generator: SkillGenerator) -> None:
        skills = generator.generate_domain(SkillDomain.TESTING)
        for s in skills:
            assert s.domain == SkillDomain.TESTING

    def test_generate_domain_appends_to_generated(self, generator: SkillGenerator) -> None:
        assert generator.generated_count == 0
        generator.generate_domain(SkillDomain.DESIGN)
        assert generator.generated_count == 2  # 2 design templates

    def test_generate_domain_empty_if_no_templates(self, tmp_output: str) -> None:
        cfg = GeneratorConfig(output_dir=tmp_output, enable_llm=False)
        catalog = SkillCatalog()
        gen = SkillGenerator(config=cfg, catalog=catalog)
        # The built-in templates are always pre-registered. Create a fresh catalog.
        gen.catalog = SkillCatalog()
        skills = gen.generate_domain(SkillDomain.CODING)
        assert skills == []


# ── Generate All ────────────────────────────────────────────────────────────


class TestGenerateAll:
    def test_generate_all_counts(self, generator: SkillGenerator) -> None:
        results = generator.generate_all()
        assert len(results) == 21  # one per built-in template

    def test_generate_all_domains(self, generator: SkillGenerator) -> None:
        results = generator.generate_all()
        domains = {s.domain for s in results}
        assert domains == set(SkillDomain)

    def test_generate_all_all_have_content(self, generator: SkillGenerator) -> None:
        results = generator.generate_all()
        for s in results:
            assert len(s.content) > 0

    def test_generate_all_tracks_generated(self, generator: SkillGenerator) -> None:
        generator.generate_all()
        assert generator.generated_count >= 21


# ── Quality Scoring ─────────────────────────────────────────────────────────


class TestQualityScoring:
    def test_evaluate_quality_defaults(self, generator: SkillGenerator) -> None:
        report = generator._evaluate_quality("")
        assert isinstance(report, SkillQualityReport)
        assert report.overall == 0.0

    def test_evaluate_quality_with_content(self, generator: SkillGenerator) -> None:
        content = (
            "metadata:\n"
            "  domain: coding\n"
            "  name: test\n"
            "error: handled\n"
            "validated: true\n"
            "steps:\n"
            "  - step1\n"
            "  - step2\n"
        )
        report = generator._evaluate_quality(content)
        assert report.correctness > 0.5
        assert report.completeness > 0.0
        assert report.overall > 0.0

    def test_evaluate_quality_min_max(self, generator: SkillGenerator) -> None:
        content = "x: 1\ny: 2\n" * 50
        report = generator._evaluate_quality(content)
        assert all(0.0 <= v <= 1.0 for v in report.dimensions.values())

    def test_evaluate_generated_skill(self, generator: SkillGenerator) -> None:
        skill = generator.generate("refactor")
        q = skill.quality_report
        assert 0.0 <= q.overall <= 1.0
        assert len(q.dimensions) == 5

    def test_generated_saved_quality(self, generator: SkillGenerator) -> None:
        skills = generator.generate_domain(SkillDomain.RESEARCH)
        for s in skills:
            assert 0.0 <= s.quality_report.overall <= 1.0


# ── Persistence ─────────────────────────────────────────────────────────────


class TestPersistence:
    def test_save_skill_creates_file(self, generator: SkillGenerator) -> None:
        skill = generator.generate("log_analyzer")
        # The generator saves internally; check the file exists
        domain_dir = os.path.join(generator.config.output_dir, "debugging")
        files = os.listdir(domain_dir)
        assert any("log_analyzer" in f for f in files)

    def test_save_skill_content(self, generator: SkillGenerator) -> None:
        skill = generator.generate("schema_designer")
        domain_dir = os.path.join(generator.config.output_dir, "data")
        files = os.listdir(domain_dir)
        yaml_files = [f for f in files if f.endswith(".yaml")]
        assert len(yaml_files) >= 1


# ── Custom Catalog ──────────────────────────────────────────────────────────


class TestCustomCatalog:
    def test_generate_custom_template(self, generator_with_catalog: SkillGenerator) -> None:
        skill = generator_with_catalog.generate("custom_audit")
        assert skill.template_name == "custom_audit"
        assert skill.domain == SkillDomain.SECURITY

    def test_custom_template_content(self, generator_with_catalog: SkillGenerator) -> None:
        skill = generator_with_catalog.generate("custom_audit")
        assert len(skill.content) > 0
        assert "security" in skill.content.lower()


# ── Prompt Building ─────────────────────────────────────────────────────────


class TestPromptBuilding:
    def test_build_prompt_contains_sections(self, generator: SkillGenerator) -> None:
        template = SkillTemplate(
            domain=SkillDomain.CODING,
            name="test_fn",
            description="A test",
            trigger_keywords=["test"],
            sections=["setup", "run", "verify"],
        )
        prompt = generator._build_prompt(template, "Test specification")
        assert "setup" in prompt
        assert "run" in prompt
        assert "verify" in prompt
        assert "Test specification" in prompt

    def test_build_prompt_structure(self, generator: SkillGenerator) -> None:
        template = SkillTemplate(
            domain=SkillDomain.DEVOPS,
            name="deploy",
            description="Deploy skill",
            trigger_keywords=["deploy"],
            sections=["build", "deploy", "monitor"],
            dependencies=["ci_pipeline_generator"],
        )
        prompt = generator._build_prompt(template, "")
        assert "Devops" in prompt
        assert "ci_pipeline_generator" in prompt
        assert "Required Sections" in prompt


# ── GeneratedSkill Property ─────────────────────────────────────────────────


class TestGeneratorProperties:
    def test_generated_property_returns_copy(self, generator: SkillGenerator) -> None:
        generator.generate("mock_designer")
        assert len(generator.generated) == 1

    def test_generated_property_order(self, generator: SkillGenerator) -> None:
        generator.generate("unit_test_writer")
        generator.generate("refactor")
        names = [s.template_name for s in generator.generated]
        assert names == ["unit_test_writer", "refactor"]

    def test_generated_count_multiple(self, generator: SkillGenerator) -> None:
        for _ in range(5):
            generator.generate("unit_test_writer")
        assert generator.generated_count == 5

    def test_generated_count_reset_on_new_instance(self) -> None:
        g1 = SkillGenerator()
        assert g1.generated_count == 0
