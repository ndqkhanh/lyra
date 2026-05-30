"""Comprehensive tests for EvoSkills validation gates.

Tests the 4-gate validation pipeline with extensive coverage:
- Gate 1: Syntax & Structure validation
- Gate 2: Semantic Correctness checking
- Gate 3: Performance Benchmark testing
- Gate 4: Safety Alignment screening
"""
from __future__ import annotations

import pytest

from lyra_core.skills.gates.benchmark_runner import BenchmarkRunner
from lyra_core.skills.gates.safety_screener import SafetyScreener
from lyra_core.skills.gates.semantic_checker import SemanticChecker
from lyra_core.skills.gates.syntax_validator import SyntaxValidator
from lyra_core.skills.validation_gate import (
    GateNumber,
    GateResult,
    GateStatus,
    SkillValidationPipeline,
    ValidationReport,
)

# ── Test Fixtures ─────────────────────────────────────────────────────

VALID_PYTHON_SKILL = '''"""A test skill that parses JSON files."""

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

VALID_SHELL_SKILL = """#!/bin/bash
# A test shell skill that counts files.

echo "Counting files..."
count=$(ls | wc -l)
echo "Found $count files"
"""

SKILL_WITH_SECRET = '''"""A skill with hardcoded secrets."""
import requests

API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"

def call_api():
    return requests.get("https://api.example.com", headers={"Authorization": f"Bearer {API_KEY}"})
'''

SKILL_WITH_AWS_KEY = '''"""AWS credentials leak."""
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
'''

DESTRUCTIVE_SKILL = """#!/bin/bash
# Dangerous skill that deletes files
rm -rf /tmp/cache
DROP TABLE users;
echo "cleaned"
"""

SUBPROCESS_SKILL = """import subprocess
import os

def run_command(cmd):
    subprocess.run(cmd, shell=True)
    os.system(cmd)
"""

EVAL_EXEC_SKILL = """
def dangerous_eval(code):
    eval(code)
    exec(code)
"""

LARGE_SKILL = "\n".join(f"x{i} = {i}" for i in range(600))

NESTED_LOOPS_SKILL = """
def process_matrix(matrix):
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            for k in range(len(matrix[i][j])):
                for m in range(len(matrix[i][j][k])):
                    print(matrix[i][j][k][m])
"""

SKILL_WITH_PICKLE = """
import pickle

def load_data(path):
    with open(path, 'rb') as f:
        return pickle.load(f)
"""

SKILL_WITH_UNSAFE_YAML = """
import yaml

def load_config(path):
    with open(path) as f:
        return yaml.load(f)  # Unsafe!
"""

SKILL_WITH_NETWORK = """
import urllib.request
import ftplib

def fetch_data(url):
    return urllib.request.urlopen(url).read()
"""


# ── Test SyntaxValidator ──────────────────────────────────────────────


class TestSyntaxValidator:
    def test_valid_python_passes(self):
        validator = SyntaxValidator()
        result = validator.validate("json-parser", ("json", "parse"), VALID_PYTHON_SKILL)
        assert result.passed
        assert result.score == 1.0
        assert len(result.issues) == 0

    def test_valid_shell_passes(self):
        validator = SyntaxValidator()
        result = validator.validate("count-files", ("count",), VALID_SHELL_SKILL)
        assert result.passed
        assert result.score == 1.0

    def test_empty_body_rejected(self):
        validator = SyntaxValidator()
        result = validator.validate("empty", ("test",), "")
        assert not result.passed
        assert result.score == 0.0
        assert "empty" in result.recommendation.lower()

    def test_invalid_name_detected(self):
        validator = SyntaxValidator()
        result = validator.validate("", ("test",), "def foo(): pass")
        assert len(result.issues) > 0
        assert any("name" in issue.lower() for issue in result.issues)

    def test_no_triggers_detected(self):
        validator = SyntaxValidator()
        result = validator.validate("skill", (), "def foo(): pass")
        assert len(result.issues) > 0
        assert any("trigger" in issue.lower() for issue in result.issues)

    def test_no_description_detected(self):
        validator = SyntaxValidator()
        result = validator.validate("skill", ("test",), "def foo(): pass")
        assert len(result.issues) > 0
        assert any("description" in issue.lower() for issue in result.issues)

    def test_invalid_python_syntax(self):
        validator = SyntaxValidator()
        result = validator.validate("bad", ("test",), "def foo(\n  pass")
        assert len(result.issues) > 0
        assert any("python" in issue.lower() for issue in result.issues)

    def test_threshold_is_1_0(self):
        validator = SyntaxValidator()
        assert validator.THRESHOLD == 1.0


# ── Test SemanticChecker ──────────────────────────────────────────────


class TestSemanticChecker:
    def test_valid_python_passes(self):
        checker = SemanticChecker()
        result = checker.validate("skill", ("test",), VALID_PYTHON_SKILL)
        assert result.passed
        assert result.score >= checker.THRESHOLD

    def test_hardcoded_secret_detected(self):
        checker = SemanticChecker()
        result = checker.validate("skill", ("test",), SKILL_WITH_SECRET)
        assert not result.passed
        assert any("api" in issue.lower() or "key" in issue.lower() or "secret" in issue.lower() for issue in result.issues)

    def test_aws_key_detected(self):
        checker = SemanticChecker()
        result = checker.validate("skill", ("test",), SKILL_WITH_AWS_KEY)
        assert not result.passed
        assert any("api" in issue.lower() or "key" in issue.lower() or "secret" in issue.lower() for issue in result.issues)

    def test_destructive_defaults_detected(self):
        checker = SemanticChecker()
        result = checker.validate("skill", ("test",), DESTRUCTIVE_SKILL)
        assert not result.passed
        assert any("destructive" in issue.lower() for issue in result.issues)

    def test_no_function_detected(self):
        checker = SemanticChecker()
        result = checker.validate("skill", ("test",), "x = 1\ny = 2")
        assert len(result.issues) > 0
        assert any("function" in issue.lower() or "entry" in issue.lower() for issue in result.issues)

    def test_shell_without_shebang(self):
        checker = SemanticChecker()
        result = checker.validate("skill", ("test",), "#invalid\necho hello")
        assert len(result.issues) > 0

    def test_threshold_is_0_95(self):
        checker = SemanticChecker()
        assert checker.THRESHOLD == 0.95


# ── Test BenchmarkRunner ──────────────────────────────────────────────


class TestBenchmarkRunner:
    def test_small_skill_passes(self):
        runner = BenchmarkRunner()
        result = runner.validate("skill", ("test",), VALID_PYTHON_SKILL)
        assert result.passed
        assert result.score >= runner.THRESHOLD

    def test_large_skill_flagged(self):
        runner = BenchmarkRunner()
        result = runner.validate("large", ("test",), LARGE_SKILL)
        assert any("large" in issue.lower() or "line" in issue.lower() for issue in result.issues)

    def test_nested_loops_detected(self):
        runner = BenchmarkRunner()
        result = runner.validate("nested", ("test",), NESTED_LOOPS_SKILL)
        assert any("loop" in issue.lower() or "complexity" in issue.lower() for issue in result.issues)

    def test_excessive_imports_detected(self):
        runner = BenchmarkRunner()
        many_imports = "\n".join(f"import module{i}" for i in range(25))
        result = runner.validate("imports", ("test",), many_imports)
        assert any("import" in issue.lower() for issue in result.issues)

    def test_metrics_included(self):
        runner = BenchmarkRunner()
        result = runner.validate("skill", ("test",), VALID_PYTHON_SKILL)
        assert "line_count" in result.metrics
        assert "import_count" in result.metrics
        assert "nested_loops" in result.metrics
        assert "trigger_quality" in result.metrics

    def test_short_trigger_penalized(self):
        runner = BenchmarkRunner()
        result = runner.validate("skill", ("a", "b"), "def foo(): pass")
        assert result.metrics["trigger_quality"] < 0.9

    def test_long_trigger_penalized(self):
        runner = BenchmarkRunner()
        long_trigger = "a" * 100
        result = runner.validate("skill", (long_trigger,), "def foo(): pass")
        assert result.metrics["trigger_quality"] < 0.9

    def test_threshold_is_0_80(self):
        runner = BenchmarkRunner()
        assert runner.THRESHOLD == 0.80


# ── Test SafetyScreener ───────────────────────────────────────────────


class TestSafetyScreener:
    def test_clean_skill_passes(self):
        screener = SafetyScreener()
        result = screener.validate("skill", ("test",), VALID_PYTHON_SKILL)
        assert result.passed
        assert result.score >= screener.THRESHOLD

    def test_subprocess_detected(self):
        screener = SafetyScreener()
        result = screener.validate("skill", ("test",), SUBPROCESS_SKILL)
        assert not result.passed
        assert any("subprocess" in v for v in result.violations)

    def test_eval_exec_detected(self):
        screener = SafetyScreener()
        result = screener.validate("skill", ("test",), EVAL_EXEC_SKILL)
        assert not result.passed
        assert len(result.violations) >= 2

    def test_pickle_detected(self):
        screener = SafetyScreener()
        result = screener.validate("skill", ("test",), SKILL_WITH_PICKLE)
        assert not result.passed
        assert any("pickle" in issue.lower() for issue in result.issues)

    def test_unsafe_yaml_detected(self):
        screener = SafetyScreener()
        result = screener.validate("skill", ("test",), SKILL_WITH_UNSAFE_YAML)
        assert not result.passed
        assert any("yaml" in issue.lower() for issue in result.issues)

    def test_network_operations_detected(self):
        screener = SafetyScreener()
        result = screener.validate("skill", ("test",), SKILL_WITH_NETWORK)
        assert not result.passed
        assert any("network" in v for v in result.violations)

    def test_multiple_file_writes_detected(self):
        screener = SafetyScreener()
        skill = """
with open('a', 'w') as f:
    f.write('a')
with open('b', 'w') as f:
    f.write('b')
with open('c', 'w') as f:
    f.write('c')
"""
        result = screener.validate("skill", ("test",), skill)
        assert any("file write" in issue.lower() for issue in result.issues)

    def test_threshold_is_0_98(self):
        screener = SafetyScreener()
        assert screener.THRESHOLD == 0.98


# ── Test SkillValidationPipeline ──────────────────────────────────────


class TestSkillValidationPipeline:
    def test_valid_skill_passes_all_gates(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("json-parser", ("json", "parse"), VALID_PYTHON_SKILL)
        assert report.passed
        assert not report.needs_human_review
        assert len(report.gate_results) == 4

    def test_skill_with_secrets_fails(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("secret", ("api",), SKILL_WITH_SECRET)
        assert not report.passed or report.needs_human_review

    def test_destructive_skill_fails(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("destroy", ("rm",), DESTRUCTIVE_SKILL)
        assert not report.passed or report.needs_human_review

    def test_subprocess_skill_fails_safety(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("sub", ("cmd",), SUBPROCESS_SKILL)
        assert not report.passed or report.needs_human_review

    def test_gate_results_in_order(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("skill", ("test",), VALID_PYTHON_SKILL)
        gates = [r.gate for r in report.gate_results]
        assert gates == [GateNumber.GATE_1, GateNumber.GATE_2, GateNumber.GATE_3, GateNumber.GATE_4]

    def test_early_rejection_stops_pipeline(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("empty", ("test",), "")
        # Should only have Gate 1 result since it rejected
        assert len(report.gate_results) == 1
        assert report.gate_results[0].gate == GateNumber.GATE_1

    def test_skip_performance_gate(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("skill", ("test",), VALID_PYTHON_SKILL, skip_performance=True)
        gates = {r.gate for r in report.gate_results}
        assert GateNumber.GATE_3 not in gates

    def test_skip_safety_gate(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("skill", ("test",), VALID_PYTHON_SKILL, skip_safety=True)
        gates = {r.gate for r in report.gate_results}
        assert GateNumber.GATE_4 not in gates

    def test_composite_score_calculation(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("skill", ("test",), VALID_PYTHON_SKILL)
        assert 0.0 <= report.composite_score <= 1.0
        # Composite should be average of gate scores
        avg_score = sum(r.score for r in report.gate_results) / len(report.gate_results)
        assert abs(report.composite_score - avg_score) < 0.01

    def test_history_tracking(self):
        pipeline = SkillValidationPipeline()
        pipeline.validate("a", ("x",), VALID_PYTHON_SKILL)
        pipeline.validate("b", ("y",), VALID_SHELL_SKILL)
        assert len(pipeline.history) == 2

    def test_clear_history(self):
        pipeline = SkillValidationPipeline()
        pipeline.validate("a", ("x",), VALID_PYTHON_SKILL)
        pipeline.clear_history()
        assert len(pipeline.history) == 0

    def test_pass_rate_calculation(self):
        pipeline = SkillValidationPipeline()
        pipeline.validate("good", ("x",), VALID_PYTHON_SKILL)
        pipeline.validate("bad", ("y",), "")
        assert 0.0 <= pipeline.pass_rate <= 1.0

    def test_report_id_uniqueness(self):
        pipeline = SkillValidationPipeline()
        r1 = pipeline.validate("a", ("x",), VALID_PYTHON_SKILL)
        r2 = pipeline.validate("b", ("y",), VALID_PYTHON_SKILL)
        assert r1.report_id != r2.report_id

    def test_summary_includes_skill_name(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("my-awesome-skill", ("test",), VALID_PYTHON_SKILL)
        assert "my-awesome-skill" in report.summary


# ── Test Integration Scenarios ────────────────────────────────────────


class TestIntegrationScenarios:
    def test_skill_with_multiple_issues(self):
        """Test skill that fails multiple gates."""
        bad_skill = """
api_key = "sk-12345678901234567890"
subprocess.run("rm -rf /", shell=True)
eval(input())
"""
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("bad", ("test",), bad_skill)
        assert not report.passed
        # Should fail semantic (secrets) and/or safety gates
        failed_or_review = [
            r for r in report.gate_results
            if r.status in (GateStatus.REJECTED, GateStatus.NEEDS_REVIEW)
        ]
        assert len(failed_or_review) >= 1

    def test_skill_needing_review(self):
        """Test skill that needs human review but isn't outright rejected."""
        review_skill = """#!/bin/bash
# Slightly large script
""" + "\n".join(f"echo 'line {i}'" for i in range(550))

        pipeline = SkillValidationPipeline()
        report = pipeline.validate("review", ("test",), review_skill)
        assert report.needs_human_review or not report.passed

    def test_perfect_score_skill(self):
        """Test skill that gets perfect scores on all gates."""
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("perfect", ("json", "parse"), VALID_PYTHON_SKILL)
        assert report.passed
        assert report.composite_score >= 0.95

    def test_shell_script_validation(self):
        """Test complete validation of shell script."""
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("counter", ("count", "files"), VALID_SHELL_SKILL)
        assert report.passed
        assert all(r.status in (GateStatus.PASSED, GateStatus.AUTO_FIXED) for r in report.gate_results)


# ── Test Edge Cases ───────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_triggers_tuple(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("skill", (), "def foo(): pass")
        assert len(report.gate_results[0].issues) > 0

    def test_whitespace_only_body(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("skill", ("test",), "   \n\n   ")
        assert not report.passed

    def test_very_short_skill(self):
        pipeline = SkillValidationPipeline()
        report = pipeline.validate("tiny", ("test",), "pass")
        # Should pass performance but may have other issues
        assert any(r.gate == GateNumber.GATE_3 for r in report.gate_results)

    def test_unicode_in_skill(self):
        pipeline = SkillValidationPipeline()
        unicode_skill = '''"""Unicode skill 中文."""
def greet():
    print("你好世界")
'''
        report = pipeline.validate("unicode", ("test",), unicode_skill)
        # Should handle unicode gracefully
        assert len(report.gate_results) > 0

    def test_mixed_line_endings(self):
        pipeline = SkillValidationPipeline()
        mixed = "def foo():\r\n    pass\n"
        report = pipeline.validate("mixed", ("test",), mixed)
        assert len(report.gate_results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
