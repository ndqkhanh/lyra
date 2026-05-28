"""Tests for Phase 3.1 Skill Validation Gates."""
from __future__ import annotations

import pytest
from lyra_core.skills.validation_gate import (
    GateNumber,
    GateResult,
    GateStatus,
    SkillValidationPipeline,
)

VALID_PYTHON = '''"""A test skill that parses JSON files."""

import json
import os


def parse_json_file(path: str) -> dict:
    """Read and parse a JSON file."""
    with open(path) as f:
        return json.load(f)


def validate(data: dict) -> bool:
    """Validate the parsed data."""
    return "name" in data and "version" in data
'''

VALID_SHELL = """#!/bin/bash
# A test shell skill that counts files.

echo "Counting files..."
count=$(ls | wc -l)
echo "Found $count files"
"""

EMPTY_SKILL = ""

SECRET_SKILL = '''"""A skill with secrets."""
api_key="sk-abcdefghijklmnopqrstuvwxyz123456"
print(api_key)
'''

DESTRUCTIVE_SKILL = """#!/bin/bash
# Dangerous skill
rm -rf /tmp/cache
echo "cleaned"
"""

SUB_SKILL = """import subprocess
import os

def run_command(cmd):
    subprocess.run(cmd, shell=True)
    os.system(cmd)
"""


class TestGate1Syntax:
    def test_valid_python_passes(self):
        result = _gate1("my-skill", ("json", "parse"), VALID_PYTHON)
        assert result.status == GateStatus.PASSED
        assert result.score == 1.0

    def test_valid_shell_passes(self):
        result = _gate1("count-files", ("count", "files"), VALID_SHELL)
        assert result.status == GateStatus.PASSED

    def test_empty_body_rejected(self):
        result = _gate1("bad", ("test",), "")
        assert result.status == GateStatus.REJECTED
        assert result.score == 0.0

    def test_no_triggers_issues(self):
        result = _gate1("skill", (), "print('hello')")
        assert len(result.issues) > 0

    def test_no_description_issues(self):
        result = _gate1("skill", ("test",), "print('hello')\nprint('world')")
        assert len(result.issues) > 0


class TestGate2Semantic:
    def test_valid_python_passes(self):
        result = _gate2(VALID_PYTHON)
        assert result.status == GateStatus.PASSED

    def test_hardcoded_secret_detected(self):
        result = _gate2(SECRET_SKILL)
        assert len(result.issues) > 0
        assert result.score < 1.0

    def test_destructive_default_detected(self):
        result = _gate2(DESTRUCTIVE_SKILL)
        assert any("destructive" in i.lower() for i in result.issues)

    def test_no_function_issues(self):
        result = _gate2("pass")
        assert len(result.issues) > 0


class TestGate3Performance:
    def test_small_skill_passes(self):
        result = _gate3(VALID_PYTHON, ("json", "parse"))
        assert result.status == GateStatus.PASSED

    def test_large_skill_warns(self):
        large = "\n".join(f"x{i} = {i}" for i in range(600))
        result = _gate3(large, ("test",))
        assert "too large" in " ".join(result.issues).lower() or result.status != GateStatus.REJECTED


class TestGate4Safety:
    def test_clean_skill_passes(self):
        result = _gate4(VALID_PYTHON)
        assert result.status == GateStatus.PASSED

    def test_dangerous_calls_detected(self):
        result = _gate4(SUB_SKILL)
        assert len(result.issues) > 0
        assert result.score < 1.0

    def test_eval_detected(self):
        result = _gate4("eval(input())")
        assert len(result.issues) >= 1


class TestSkillValidationPipeline:
    def test_valid_python_passes_all_gates(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("json-parser", ("json", "parse"), VALID_PYTHON)
        assert report.passed
        assert not report.needs_human_review

    def test_empty_skill_rejected(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("bad", ("test",), "")
        assert not report.passed

    def test_dangerous_skill_triggers_safety_issues(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("sub", ("cmd",), SUB_SKILL)
        assert not report.passed or report.needs_human_review

    def test_skip_performance_gate(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate(
            "json-parser", ("json",), VALID_PYTHON, skip_performance=True
        )
        gate_nums = {r.gate for r in report.gate_results}
        assert GateNumber.GATE_3 not in gate_nums

    def test_skip_safety_gate(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate(
            "json-parser", ("json",), VALID_PYTHON, skip_safety=True
        )
        gate_nums = {r.gate for r in report.gate_results}
        assert GateNumber.GATE_4 not in gate_nums

    def test_composite_score_between_0_and_1(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("skill", ("t",), "def foo(): pass")
        assert 0.0 <= report.composite_score <= 1.0

    def test_report_id_is_unique(self):
        pipeline = SkillValidationPipeline()
        r1 = pipeline.validate("a", ("x",), "def a(): pass")
        r2 = pipeline.validate("b", ("y",), "def b(): pass")
        assert r1.report_id != r2.report_id

    def test_history_accumulates(self):
        pipeline = SkillValidationPipeline()
        pipeline.validate("a", ("x",), "def a(): pass")
        pipeline.validate("b", ("y",), "def b(): pass")
        assert len(pipeline.history) == 2

    def test_clear_history(self):
        pipeline = SkillValidationPipeline()
        pipeline.validate("a", ("x",), "def a(): pass")
        pipeline.clear_history()
        assert len(pipeline.history) == 0

    def test_pass_rate(self):
        pipeline = SkillValidationPipeline()
        pipeline.validate("a", ("x",), VALID_PYTHON)
        pipeline.validate("b", ("y",), "")
        assert 0.0 <= pipeline.pass_rate <= 1.0

    def test_valid_shell_passes(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("count", ("count",), VALID_SHELL)
        assert report.passed

    def test_secret_skill_fails_safety(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("secret", ("key",), SECRET_SKILL)
        assert not report.passed or report.needs_human_review

    def test_summary_includes_skill_name(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("my-skill", ("test",), "def foo(): pass")
        assert "my-skill" in report.summary


class TestGateResult:
    def test_frozen_dataclass(self):
        gr = GateResult(
            gate=GateNumber.GATE_1,
            status=GateStatus.PASSED,
            score=1.0,
            threshold=1.0,
            issues=(),
            auto_fixes_applied=(),
            recommendation="ok",
            timestamp=1000.0,
        )
        with pytest.raises(Exception):
            gr.score = 0.5  # type: ignore[misc]


class TestValidationReport:
    def test_report_contains_gate_results(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("skill", ("t",), "def foo(): pass")
        assert len(report.gate_results) >= 2


# Helpers — import internal functions for direct gate testing
from lyra_core.skills.validation_gate import (
    _gate1_syntax as _gate1,
)
from lyra_core.skills.validation_gate import (
    _gate2_semantic as _gate2,
)
from lyra_core.skills.validation_gate import (
    _gate3_performance as _gate3,
)
from lyra_core.skills.validation_gate import (
    _gate4_safety as _gate4,
)
