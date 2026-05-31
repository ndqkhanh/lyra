"""Tests for Cross-Platform Skill Format (P3-B2)."""
from __future__ import annotations

import os
import tempfile

import pytest

from lyra_harness_core.skill_format import (
    SkillInput,
    SkillManifest,
    SkillManifestRegistry,
    SkillOutput,
    SkillRetry,
    SkillTrigger,
    SkillValidationResult,
    load_skill,
    load_skill_from_markdown,
    load_skill_from_yaml,
    validate_skill_manifest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILL_MD = """---
name: deep-research
version: 2.1.0
description: |
  Multi-hop deep research with citation traversal.
triggers:
  keywords: ["research", "deep dive", "literature review"]
  contexts: ["research", "planning", "analysis"]
allowed_tools:
  - WebSearch
  - WebFetch
  - Read
  - Write
model: sonnet
inputs:
  query:
    type: string
    required: true
    description: "Research question or topic"
  depth:
    type: integer
    default: 3
    choices: [1, 2, 3, 4, 5]
outputs:
  report:
    type: markdown
    description: "Structured research report with citations"
timeout: 600
retry:
  max_attempts: 3
  backoff: exponential
---
# Deep Research Skill

This skill performs deep research using multi-hop traversal.
"""

SKILL_YAML = """\
name: code-review
version: 1.2.0
description: "Automated code review with severity ratings"
triggers:
  keywords: ["review", "code review", "audit"]
  contexts: ["development", "review"]
allowed_tools:
  - Read
  - Bash(git *)
model: sonnet
inputs:
  target:
    type: string
    required: true
    description: "File or directory to review"
outputs:
  verdict:
    type: json
    description: "Review verdict with severity ratings"
timeout: 120
retry:
  max_attempts: 2
  backoff: linear
"""


# ---------------------------------------------------------------------------
# SkillInput
# ---------------------------------------------------------------------------


class TestSkillInput:
    def test_minimal(self):
        si = SkillInput(name="query")
        assert si.name == "query"
        assert si.type == "string"
        assert not si.required

    def test_full(self):
        si = SkillInput(name="depth", type="integer", required=True, default=3, choices=[1, 2, 3])
        assert si.default == 3
        assert si.choices == [1, 2, 3]

    def test_frozen(self):
        si = SkillInput(name="x")
        with pytest.raises(Exception):
            si.name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SkillOutput
# ---------------------------------------------------------------------------


class TestSkillOutput:
    def test_minimal(self):
        so = SkillOutput(name="report")
        assert so.name == "report"
        assert so.type == "string"

    def test_frozen(self):
        so = SkillOutput(name="x")
        with pytest.raises(Exception):
            so.name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SkillTrigger
# ---------------------------------------------------------------------------


class TestSkillTrigger:
    def test_defaults(self):
        t = SkillTrigger()
        assert t.keywords == []
        assert t.contexts == []

    def test_with_data(self):
        t = SkillTrigger(keywords=["test"], contexts=["dev"])
        assert t.keywords == ["test"]

    def test_frozen(self):
        t = SkillTrigger()
        with pytest.raises(Exception):
            t.keywords = []  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SkillRetry
# ---------------------------------------------------------------------------


class TestSkillRetry:
    def test_defaults(self):
        r = SkillRetry()
        assert r.max_attempts == 1
        assert r.backoff == "exponential"

    def test_frozen(self):
        r = SkillRetry()
        with pytest.raises(Exception):
            r.max_attempts = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SkillManifest
# ---------------------------------------------------------------------------


class TestSkillManifest:
    def test_minimal(self):
        m = SkillManifest(name="test-skill")
        assert m.name == "test-skill"
        assert m.version == "1.0.0"
        assert m.timeout == 300

    def test_frozen(self):
        m = SkillManifest(name="x")
        with pytest.raises(Exception):
            m.name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SkillValidationResult
# ---------------------------------------------------------------------------


class TestSkillValidationResult:
    def test_valid_default(self):
        r = SkillValidationResult(valid=True)
        assert r.valid
        assert r.errors == []

    def test_with_errors(self):
        r = SkillValidationResult(valid=False, errors=["bad name"])
        assert not r.valid
        assert len(r.errors) == 1

    def test_frozen(self):
        r = SkillValidationResult(valid=True)
        with pytest.raises(Exception):
            r.valid = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# load_skill_from_markdown
# ---------------------------------------------------------------------------


class TestLoadSkillFromMarkdown:
    def test_loads_full_manifest(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(SKILL_MD)
            f.flush()
            path = f.name

        try:
            m = load_skill_from_markdown(path)
            assert m.name == "deep-research"
            assert m.version == "2.1.0"
            assert "citation traversal" in m.description
            assert len(m.triggers.keywords) == 3
            assert len(m.triggers.contexts) == 3
            assert len(m.allowed_tools) == 4
            assert m.model == "sonnet"
            assert len(m.inputs) == 2
            assert len(m.outputs) == 1
            assert m.timeout == 600
            assert m.retry.max_attempts == 3
            assert m.retry.backoff == "exponential"
            assert "Deep Research Skill" in m.body
            assert m.source == path
        finally:
            os.unlink(path)

    def test_input_required(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(SKILL_MD)
            f.flush()
            path = f.name

        try:
            m = load_skill_from_markdown(path)
            query_input = next(i for i in m.inputs if i.name == "query")
            assert query_input.required
            assert query_input.type == "string"
            depth_input = next(i for i in m.inputs if i.name == "depth")
            assert depth_input.default == 3
            assert depth_input.choices == [1, 2, 3, 4, 5]
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_skill_from_markdown("/nonexistent/skill.md")

    def test_no_frontmatter(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Just markdown, no frontmatter")
            f.flush()
            path = f.name

        try:
            with pytest.raises(ValueError, match="frontmatter"):
                load_skill_from_markdown(path)
        finally:
            os.unlink(path)

    def test_minimal_frontmatter(self):
        minimal = "---\nname: minimal-skill\n---\nBody here"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(minimal)
            f.flush()
            path = f.name

        try:
            m = load_skill_from_markdown(path)
            assert m.name == "minimal-skill"
            assert m.body == "Body here"
            assert m.inputs == []
            assert m.outputs == []
        finally:
            os.unlink(path)

    def test_inputs_as_list_format(self):
        alt_fmt = """---
name: alt-skill
inputs:
  - name: target
    type: string
    required: true
  - name: verbose
    type: boolean
    default: false
---
Body
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(alt_fmt)
            f.flush()
            path = f.name

        try:
            m = load_skill_from_markdown(path)
            assert len(m.inputs) == 2
            assert m.inputs[0].name == "target"
            assert m.inputs[1].default is False
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# load_skill_from_yaml
# ---------------------------------------------------------------------------


class TestLoadSkillFromYaml:
    def test_loads_standalone_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(SKILL_YAML)
            f.flush()
            path = f.name

        try:
            m = load_skill_from_yaml(path)
            assert m.name == "code-review"
            assert m.version == "1.2.0"
            assert len(m.triggers.keywords) == 3
            assert m.triggers.contexts == ["development", "review"]
            assert m.model == "sonnet"
            assert len(m.inputs) == 1
            assert m.inputs[0].name == "target"
            assert m.retry.max_attempts == 2
            assert m.retry.backoff == "linear"
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_skill_from_yaml("/nonexistent/skill.yaml")

    def test_root_not_dict(self):
        bad = "- not a mapping"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(bad)
            f.flush()
            path = f.name

        try:
            with pytest.raises(ValueError, match="mapping"):
                load_skill_from_yaml(path)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# load_skill (auto-detect)
# ---------------------------------------------------------------------------


class TestLoadSkill:
    def test_detects_markdown(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(SKILL_MD)
            f.flush()
            path = f.name

        try:
            m = load_skill(path)
            assert m.name == "deep-research"
        finally:
            os.unlink(path)

    def test_detects_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(SKILL_YAML)
            f.flush()
            path = f.name

        try:
            m = load_skill(path)
            assert m.name == "code-review"
        finally:
            os.unlink(path)

    def test_falls_back_for_unknown_extension(self):
        """Unknown extension tries frontmatter first, then YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(SKILL_YAML)
            f.flush()
            path = f.name

        try:
            m = load_skill(path)
            assert m.name == "code-review"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# validate_skill_manifest
# ---------------------------------------------------------------------------


class TestValidateSkillManifest:
    def test_valid_manifest(self):
        m = SkillManifest(name="test", version="1.0.0", timeout=300)
        r = validate_skill_manifest(m)
        assert r.valid
        assert r.errors == []

    def test_missing_name(self):
        m = SkillManifest(name="")
        r = validate_skill_manifest(m)
        assert not r.valid
        assert any("name" in e.lower() for e in r.errors)

    def test_invalid_version(self):
        m = SkillManifest(name="test", version="not-a-version")
        r = validate_skill_manifest(m)
        assert not r.valid

    def test_negative_timeout(self):
        m = SkillManifest(name="test", timeout=-1)
        r = validate_skill_manifest(m)
        assert not r.valid

    def test_zero_retry_attempts(self):
        m = SkillManifest(name="test", retry=SkillRetry(max_attempts=0))
        r = validate_skill_manifest(m)
        assert not r.valid

    def test_unknown_model_warning(self):
        m = SkillManifest(name="test", model="gpt-5")
        r = validate_skill_manifest(m)
        assert r.valid  # warnings don't invalidate
        assert len(r.warnings) >= 1

    def test_unknown_backoff_warning(self):
        m = SkillManifest(name="test", retry=SkillRetry(backoff="instant"))
        r = validate_skill_manifest(m)
        assert r.valid
        assert len(r.warnings) >= 1

    def test_duplicate_input_names(self):
        m = SkillManifest(
            name="test",
            inputs=[SkillInput(name="x"), SkillInput(name="x")],
        )
        r = validate_skill_manifest(m)
        assert not r.valid

    def test_duplicate_output_names(self):
        m = SkillManifest(
            name="test",
            outputs=[SkillOutput(name="y"), SkillOutput(name="y")],
        )
        r = validate_skill_manifest(m)
        assert not r.valid


# ---------------------------------------------------------------------------
# SkillManifestRegistry
# ---------------------------------------------------------------------------


class TestSkillManifestRegistry:
    @pytest.fixture
    def registry(self):
        return SkillManifestRegistry()

    @pytest.fixture
    def research_skill(self):
        return SkillManifest(
            name="deep-research",
            triggers=SkillTrigger(keywords=["research", "analyze"], contexts=["research"]),
            allowed_tools=["WebSearch", "Read", "Write"],
        )

    @pytest.fixture
    def review_skill(self):
        return SkillManifest(
            name="code-review",
            triggers=SkillTrigger(keywords=["review", "audit"], contexts=["development"]),
            allowed_tools=["Read", "Bash(git diff)"],
        )

    def test_register_and_get(self, registry, research_skill):
        registry.register(research_skill)
        assert "deep-research" in registry
        assert registry.get("deep-research") is research_skill

    def test_unregister(self, registry, research_skill):
        registry.register(research_skill)
        assert registry.unregister("deep-research")
        assert "deep-research" not in registry

    def test_unregister_nonexistent(self, registry):
        assert not registry.unregister("nope")

    def test_find_by_keyword(self, registry, research_skill, review_skill):
        registry.register(research_skill)
        registry.register(review_skill)
        results = registry.find_by_keyword("review")
        assert len(results) == 1
        assert results[0].name == "code-review"

    def test_find_by_keyword_case_insensitive(self, registry, research_skill):
        registry.register(research_skill)
        results = registry.find_by_keyword("RESEARCH")
        assert len(results) == 1

    def test_find_by_keyword_none(self, registry, research_skill):
        registry.register(research_skill)
        assert registry.find_by_keyword("nonexistent") == []

    def test_find_by_context(self, registry, research_skill, review_skill):
        registry.register(research_skill)
        registry.register(review_skill)
        results = registry.find_by_context("development")
        assert len(results) == 1
        assert results[0].name == "code-review"

    def test_find_by_tool_exact(self, registry, research_skill):
        registry.register(research_skill)
        results = registry.find_by_tool("WebSearch")
        assert len(results) == 1

    def test_find_by_tool_with_args(self, registry, review_skill):
        registry.register(review_skill)
        results = registry.find_by_tool("Bash")
        assert len(results) == 1

    def test_find_by_tool_none(self, registry, research_skill):
        registry.register(research_skill)
        assert registry.find_by_tool("UnknownTool") == []

    def test_list_names_sorted(self, registry):
        registry.register(SkillManifest(name="ccc"))
        registry.register(SkillManifest(name="aaa"))
        assert registry.list_names() == ["aaa", "ccc"]

    def test_len(self, registry, research_skill, review_skill):
        assert len(registry) == 0
        registry.register(research_skill)
        registry.register(review_skill)
        assert len(registry) == 2

    def test_register_duplicate_overwrites(self, registry, research_skill):
        registry.register(research_skill)
        updated = SkillManifest(name="deep-research", description="updated")
        registry.register(updated)
        assert registry.get("deep-research").description == "updated"


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


class TestSkillFormatIntegration:
    def test_full_pipeline_markdown(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(SKILL_MD)
            f.flush()
            path = f.name

        try:
            m = load_skill(path)
            assert m.name == "deep-research"

            validation = validate_skill_manifest(m)
            assert validation.valid

            registry = SkillManifestRegistry()
            registry.register(m)
            results = registry.find_by_keyword("research")
            assert len(results) == 1

            ctx_results = registry.find_by_context("planning")
            assert len(ctx_results) == 1

            tool_results = registry.find_by_tool("WebSearch")
            assert len(tool_results) == 1
        finally:
            os.unlink(path)

    def test_full_pipeline_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(SKILL_YAML)
            f.flush()
            path = f.name

        try:
            m = load_skill(path)
            assert m.name == "code-review"

            validation = validate_skill_manifest(m)
            assert validation.valid

            registry = SkillManifestRegistry()
            registry.register(m)
            assert len(registry) == 1
        finally:
            os.unlink(path)
