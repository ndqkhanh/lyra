"""12+ tests for lyra-skill-generator models — domains, templates, configs, quality, and catalog."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from lyra_skill_generator.models import (
    GeneratedSkill,
    GeneratorConfig,
    SkillCatalog,
    SkillDomain,
    SkillQualityReport,
    SkillTemplate,
)


# ── Tests for SkillDomain ───────────────────────────────────────────────────


class TestSkillDomain:
    def test_enum_values(self) -> None:
        assert SkillDomain.CODING.value == "coding"
        assert SkillDomain.DEBUGGING.value == "debugging"
        assert SkillDomain.TESTING.value == "testing"
        assert SkillDomain.SECURITY.value == "security"
        assert SkillDomain.DEVOPS.value == "devops"
        assert SkillDomain.DATA.value == "data"
        assert SkillDomain.DESIGN.value == "design"
        assert SkillDomain.MANAGEMENT.value == "management"
        assert SkillDomain.RESEARCH.value == "research"

    def test_enum_count(self) -> None:
        assert len(SkillDomain) == 9

    def test_display_name(self) -> None:
        assert SkillDomain.CODING.display_name == "Coding"
        assert SkillDomain.DEVOPS.display_name == "Devops"
        assert SkillDomain.RESEARCH.display_name == "Research"

    def test_from_string_valid(self) -> None:
        assert SkillDomain.from_string("coding") == SkillDomain.CODING
        assert SkillDomain.from_string("  TESTING  ") == SkillDomain.TESTING
        assert SkillDomain.from_string("Security") == SkillDomain.SECURITY

    def test_from_string_invalid(self) -> None:
        with pytest.raises(ValueError, match="Unknown domain"):
            SkillDomain.from_string("nonexistent")

    def test_members_are_unique(self) -> None:
        values = [d.value for d in SkillDomain]
        assert len(values) == len(set(values))


# ── Tests for SkillTemplate ─────────────────────────────────────────────────


class TestSkillTemplate:
    def test_template_frozen(self) -> None:
        t = SkillTemplate(
            domain=SkillDomain.CODING,
            name="test",
            description="desc",
            trigger_keywords=["code"],
            sections=["impl"],
        )
        with pytest.raises(Exception):
            t.name = "changed"  # type: ignore[misc]

    def test_template_default_difficulty(self) -> None:
        t = SkillTemplate(
            domain=SkillDomain.TESTING,
            name="default_test",
            description="desc",
            trigger_keywords=["test"],
            sections=["plan"],
        )
        assert t.difficulty == 0.5

    def test_template_default_dependencies(self) -> None:
        t = SkillTemplate(
            domain=SkillDomain.DATA,
            name="no_deps",
            description="desc",
            trigger_keywords=["data"],
            sections=["eda"],
        )
        assert t.dependencies == []

    def test_template_all_fields(self) -> None:
        t = SkillTemplate(
            domain=SkillDomain.SECURITY,
            name="secure_code",
            description="Security audit skill",
            trigger_keywords=["audit", "vuln"],
            sections=["scope", "findings", "fix"],
            difficulty=0.8,
            dependencies=["vulnerability_scanner"],
        )
        assert t.domain == SkillDomain.SECURITY
        assert t.name == "secure_code"
        assert t.difficulty == 0.8
        assert t.dependencies == ["vulnerability_scanner"]


# ── Tests for GeneratorConfig ───────────────────────────────────────────────


class TestGeneratorConfig:
    def test_default_values(self) -> None:
        cfg = GeneratorConfig()
        assert cfg.output_dir == "./generated_skills"
        assert cfg.model_name == "claude-sonnet-4-6"
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 4096
        assert cfg.quality_threshold == 0.7
        assert cfg.enable_llm is True

    def test_custom_values(self) -> None:
        cfg = GeneratorConfig(
            output_dir="/tmp/skills",
            model_name="claude-opus-4-5",
            temperature=0.5,
            max_tokens=8192,
            quality_threshold=0.8,
            enable_llm=False,
        )
        assert cfg.output_dir == "/tmp/skills"
        assert cfg.model_name == "claude-opus-4-5"
        assert cfg.temperature == 0.5
        assert cfg.enable_llm is False

    def test_config_frozen(self) -> None:
        cfg = GeneratorConfig()
        with pytest.raises(Exception):
            cfg.output_dir = "/other"  # type: ignore[misc]


# ── Tests for SkillQualityReport ────────────────────────────────────────────


class TestSkillQualityReport:
    def test_default_all_zero(self) -> None:
        r = SkillQualityReport()
        assert r.correctness == 0.0
        assert r.completeness == 0.0
        assert r.efficiency == 0.0
        assert r.readability == 0.0
        assert r.maintainability == 0.0
        assert r.overall == 0.0

    def test_overall_average(self) -> None:
        r = SkillQualityReport(
            correctness=1.0,
            completeness=0.5,
            efficiency=0.5,
            readability=0.5,
            maintainability=0.5,
        )
        assert r.overall == 0.6

    def test_dimensions_dict(self) -> None:
        r = SkillQualityReport(
            correctness=0.9, completeness=0.8, efficiency=0.7, readability=0.6, maintainability=0.5
        )
        d = r.dimensions
        assert d["correctness"] == 0.9
        assert d["maintainability"] == 0.5
        assert len(d) == 5

    def test_meets_threshold(self) -> None:
        r = SkillQualityReport(
            correctness=0.8, completeness=0.8, efficiency=0.8, readability=0.8, maintainability=0.8
        )
        assert r.meets_threshold(0.7) is True

    def test_below_threshold(self) -> None:
        r = SkillQualityReport(correctness=0.5, completeness=0.5, efficiency=0.5, readability=0.5, maintainability=0.5)
        assert r.meets_threshold(0.7) is False

    def test_report_frozen(self) -> None:
        r = SkillQualityReport()
        with pytest.raises(Exception):
            r.correctness = 1.0  # type: ignore[misc]


# ── Tests for GeneratedSkill ────────────────────────────────────────────────


class TestGeneratedSkill:
    def test_default_quality_report(self) -> None:
        skill = GeneratedSkill(template_name="test", domain=SkillDomain.CODING, content="code")
        assert skill.quality_report.overall == 0.0

    def test_default_generated_at(self) -> None:
        skill = GeneratedSkill(template_name="test", domain=SkillDomain.CODING, content="code")
        assert isinstance(skill.generated_at, datetime)

    def test_default_version(self) -> None:
        skill = GeneratedSkill(template_name="test", domain=SkillDomain.CODING, content="code")
        assert skill.version == "1.0.0"

    def test_frozen_skill(self) -> None:
        skill = GeneratedSkill(template_name="t", domain=SkillDomain.DATA, content="c")
        with pytest.raises(Exception):
            skill.content = "changed"  # type: ignore[misc]


# ── Tests for SkillCatalog ──────────────────────────────────────────────────


class TestSkillCatalog:
    def test_empty_catalog(self) -> None:
        c = SkillCatalog()
        assert c.count == 0
        assert c.templates == {}

    def test_register_and_get(self) -> None:
        c = SkillCatalog()
        t = SkillTemplate(
            domain=SkillDomain.CODING,
            name="func_gen",
            description="desc",
            trigger_keywords=["func"],
            sections=["impl"],
        )
        c.register(t)
        assert c.count == 1
        assert c.get("func_gen") is t

    def test_register_many(self) -> None:
        c = SkillCatalog()
        t1 = SkillTemplate(domain=SkillDomain.CODING, name="a", description="d", trigger_keywords=["k"], sections=["s"])
        t2 = SkillTemplate(domain=SkillDomain.CODING, name="b", description="d", trigger_keywords=["k"], sections=["s"])
        c.register_many(t1, t2)
        assert c.count == 2

    def test_get_nonexistent(self) -> None:
        c = SkillCatalog()
        assert c.get("missing") is None

    def test_by_domain(self) -> None:
        c = SkillCatalog()
        t1 = SkillTemplate(domain=SkillDomain.CODING, name="a", description="d", trigger_keywords=["k"], sections=["s"])
        t2 = SkillTemplate(domain=SkillDomain.TESTING, name="b", description="d", trigger_keywords=["k"], sections=["s"])
        t3 = SkillTemplate(domain=SkillDomain.CODING, name="c", description="d", trigger_keywords=["k"], sections=["s"])
        c.register_many(t1, t2, t3)
        coding = c.by_domain(SkillDomain.CODING)
        assert len(coding) == 2
        assert all(t.domain == SkillDomain.CODING for t in coding)

    def test_list_domains(self) -> None:
        c = SkillCatalog()
        t1 = SkillTemplate(domain=SkillDomain.DEVOPS, name="ci", description="d", trigger_keywords=["k"], sections=["s"])
        c.register(t1)
        domains = c.list_domains()
        assert SkillDomain.DEVOPS in domains
        assert "ci" in domains[SkillDomain.DEVOPS]

    def test_list_domains_empty(self) -> None:
        c = SkillCatalog()
        assert c.list_domains() == {}

    def test_overwrite_template(self) -> None:
        c = SkillCatalog()
        t1 = SkillTemplate(domain=SkillDomain.CODING, name="t", description="v1", trigger_keywords=["k"], sections=["s"])
        t2 = SkillTemplate(domain=SkillDomain.CODING, name="t", description="v2", trigger_keywords=["k"], sections=["s"])
        c.register(t1)
        c.register(t2)
        assert c.get("t").description == "v2"  # type: ignore[union-attr]
