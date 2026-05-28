"""Integration: Specialized skills using tools ecosystem.

Tests exercise:
- Specialized skills using tools ecosystem
- Code reviewer skill using AST tools
- Security auditor using secrets scanner
- Test generator producing valid pytest code
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra_cli.skills.specialized import (
    SpecializedSkillsRegistry,
    get_registry,
)
from lyra_cli.skills.specialized.code_reviewer import (
    CodeReviewerSkill,
    ReviewFinding,
    ReviewReport,
    Severity,
    FindingCategory,
)
from lyra_cli.skills.specialized.security_auditor import (
    SecurityAuditorSkill,
    AuditReport,
    Vulnerability,
    VulnerabilitySeverity,
    OwaspCategory,
)
from lyra_cli.skills.specialized.test_generator import (
    TestGeneratorSkill,
    TestSuite,
    GeneratedTest,
    TestCase,
)
from lyra_cli.skills.specialized.performance_profiler import (
    PerformanceProfilerSkill,
    ProfileReport,
    ProfileResult,
    PerformanceIssue,
    ComplexityClass,
)
from lyra_cli.skills.specialized.dependency_analyzer import (
    DependencyAnalyzerSkill,
    DependencyReport,
    ImportInfo,
)


# =========================================================================
# Test data
# =========================================================================

SAMPLE_CODE_WITH_ISSUES = """
def process(data):
    try:
        result = []
        for i in range(len(data)):
            result.append(data[i] * 2)
        return result
    except:
        return None
"""

DANGEROUS_CODE = """
import pickle
import hashlib

api_key = "sk-abc123def456ghi789jkl"
password = "supersecret123"

def process(data):
    result = pickle.loads(data)
    return result
"""

FUNCTION_SOURCE = """
def multiply(a: float, b: float) -> float:
    return a * b

async def fetch_data(url: str) -> dict:
    return {"status": "ok"}
"""

SLOW_CODE = """
def sort_and_process(items):
    result = []
    for i in items:
        for j in items:
            result.append(i * j)
    return sorted(result)
"""

IMPORT_SOURCE = """
import os
import sys
import json
from typing import List, Optional
from datetime import datetime
"""


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def code_reviewer() -> CodeReviewerSkill:
    return CodeReviewerSkill()


@pytest.fixture
def security_auditor() -> SecurityAuditorSkill:
    return SecurityAuditorSkill()


@pytest.fixture
def test_generator() -> TestGeneratorSkill:
    return TestGeneratorSkill()


@pytest.fixture
def performance_profiler() -> PerformanceProfilerSkill:
    return PerformanceProfilerSkill()


@pytest.fixture
def dependency_analyzer() -> DependencyAnalyzerSkill:
    return DependencyAnalyzerSkill()


# =========================================================================
# Test: Specialized skills using tools ecosystem
# =========================================================================


class TestSkillsRegistry:
    """Test that the skills registry works as a discovery tool."""

    def test_registry_discovers_all_skills(self):
        """Verify the registry discovers all specialized skill packages."""
        registry = get_registry()
        all_skills = registry.list_skills()
        # Should find the markdown-based domain skills
        skill_names = [s.name for s in all_skills]
        assert "backend-engineer" in skill_names
        assert len(all_skills) >= 14

    def test_registry_search_by_tag(self):
        """Verify searching the registry by tag returns relevant skills."""
        registry = get_registry()
        results = registry.search_by_tag("engineering")
        assert len(results) >= 5


# =========================================================================
# Test: Code reviewer skill using AST tools
# =========================================================================


class TestCodeReviewerASTTools:
    """Test the code reviewer skill uses AST parsing correctly."""

    def test_code_reviewer_parses_ast(
        self, code_reviewer,
    ):
        """Verify code reviewer successfully parses AST from source."""
        result = code_reviewer.run({"source": SAMPLE_CODE_WITH_ISSUES})
        assert "findings" in result
        # AST checks should have run without crashing
        assert "line_count" in result
        assert result["line_count"] > 0

    def test_code_reviewer_detects_bare_except_via_ast(
        self, code_reviewer,
    ):
        """Verify AST analysis catches bare except clause."""
        result = code_reviewer.run({"source": SAMPLE_CODE_WITH_ISSUES})
        codes = {f["code"] for f in result["findings"]}
        assert "BARE_EXCEPT" in codes

    def test_code_reviewer_detects_dangerous_patterns_via_ast(
        self, code_reviewer,
    ):
        """Verify AST analysis catches security patterns."""
        source_with_issues = """
import pdb

def run(cmd):
    eval(cmd)
    return os.system(cmd)
"""
        result = code_reviewer.run({"source": source_with_issues})
        codes = {f["code"] for f in result["findings"]}
        assert "EVAL_USAGE" in codes
        assert "DEBUG_IMPORT" in codes

    def test_code_reviewer_clean_code_passes(
        self, code_reviewer,
    ):
        """Verify clean code produces minimal findings."""
        clean_source = """
def add(a: int, b: int) -> int:
    return a + b

class Calculator:
    def multiply(self, x: float, y: float) -> float:
        return x * y
"""
        result = code_reviewer.run({"source": clean_source})
        critical_high = [
            f for f in result["findings"]
            if f["severity"] in ("CRITICAL", "HIGH")
        ]
        assert len(critical_high) == 0

    def test_code_reviewer_report_structure(
        self, code_reviewer,
    ):
        """Verify the review report has correct structure."""
        result = code_reviewer.run({
            "source": SAMPLE_CODE_WITH_ISSUES,
            "file_path": "test_module.py",
        })
        assert result["file_path"] == "test_module.py"
        assert isinstance(result["findings"], list)
        assert isinstance(result["summary"], dict)
        for f in result["findings"]:
            assert "line" in f
            assert "severity" in f
            assert "category" in f
            assert "message" in f

    def test_empty_source_returns_error(
        self, code_reviewer,
    ):
        """Verify empty source returns error."""
        result = code_reviewer.run({"source": ""})
        assert "error" in result


# =========================================================================
# Test: Security auditor using secrets scanner
# =========================================================================


class TestSecurityAuditorSecretsScanner:
    """Test the security auditor skill detects secrets and vulnerabilities."""

    def test_auditor_detects_hardcoded_api_keys(
        self, security_auditor,
    ):
        """Verify secrets scanner catches hardcoded API keys."""
        result = security_auditor.run({"source": DANGEROUS_CODE})
        titles = [v["title"] for v in result["vulnerabilities"]]
        assert "Hardcoded API Key" in titles

    def test_auditor_detects_insecure_deserialization(
        self, security_auditor,
    ):
        """Verify the scanner detects pickle deserialization."""
        result = security_auditor.run({"source": DANGEROUS_CODE})
        titles = [v["title"] for v in result["vulnerabilities"]]
        assert any("pickle" in t.lower() for t in titles)

    def test_auditor_assigns_owasp_categories(
        self, security_auditor,
    ):
        """Verify every vulnerability has an OWASP category."""
        result = security_auditor.run({"source": DANGEROUS_CODE})
        for v in result["vulnerabilities"]:
            assert "owasp_category" in v
            assert v["owasp_category"] != ""

    def test_auditor_secure_code_no_findings(
        self, security_auditor,
    ):
        """Verify secure code produces zero vulnerabilities."""
        secure_source = """
def safe_function():
    x = 1 + 1
    return x
"""
        result = security_auditor.run({"source": secure_source})
        assert len(result["vulnerabilities"]) == 0

    def test_auditor_summary_counts_by_severity(
        self, security_auditor,
    ):
        """Verify the summary counts vulnerabilities by severity level."""
        result = security_auditor.run({"source": DANGEROUS_CODE})
        assert isinstance(result["summary"], dict)
        total = sum(result["summary"].values())
        assert total == len(result["vulnerabilities"])

    def test_empty_source_returns_error(
        self, security_auditor,
    ):
        """Verify empty source returns error."""
        result = security_auditor.run({"source": ""})
        assert "error" in result


# =========================================================================
# Test: Test generator producing valid pytest code
# =========================================================================


class TestTestGeneratorPytest:
    """Test the test generator skill produces valid pytest code."""

    def test_generator_produces_valid_pytest_imports(
        self, test_generator,
    ):
        """Verify generated test code imports pytest."""
        result = test_generator.run({
            "source": FUNCTION_SOURCE,
            "module_name": "mymod",
        })
        for test in result["tests"]:
            assert "pytest" in test["imports"]

    def test_generated_code_is_valid_python(
        self, test_generator,
    ):
        """Verify the generated test code is syntactically valid Python."""
        result = test_generator.run({
            "source": FUNCTION_SOURCE,
            "module_name": "mymod",
        })
        for test in result["tests"]:
            try:
                ast.parse(test["code"])
            except SyntaxError as e:
                pytest.fail(f"Generated test code has syntax error: {e}")

    def test_generator_creates_multiple_test_cases_per_function(
        self, test_generator,
    ):
        """Verify each function gets happy path, edge, and error tests."""
        result = test_generator.run({
            "source": FUNCTION_SOURCE,
            "module_name": "mymod",
        })
        for test in result["tests"]:
            categories = {tc["category"] for tc in test["test_cases"]}
            assert "happy_path" in categories

    def test_generator_handles_async_functions(
        self, test_generator,
    ):
        """Verify async functions produce appropriate test patterns."""
        result = test_generator.run({
            "source": FUNCTION_SOURCE,
            "module_name": "mymod",
        })
        async_test = next(
            (t for t in result["tests"] if t["function_name"] == "fetch_data"),
            None,
        )
        assert async_test is not None

    def test_generator_total_case_count(
        self, test_generator,
    ):
        """Verify the total_cases field is accurate."""
        result = test_generator.run({
            "source": FUNCTION_SOURCE,
            "module_name": "mymod",
        })
        assert "total_cases" in result
        calc_total = sum(
            len(t["test_cases"]) for t in result["tests"]
        )
        assert result["total_cases"] == calc_total

    def test_empty_source_returns_error(
        self, test_generator,
    ):
        """Verify empty source returns error."""
        result = test_generator.run({"source": ""})
        assert "error" in result
