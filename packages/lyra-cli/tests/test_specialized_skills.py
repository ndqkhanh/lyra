"""
Tests for specialized skills
"""

import pytest
from lyra_cli.skills.specialized import (
    get_registry,
    get_skill_by_name,
    list_all_skills,
    search_skills,
)
from lyra_cli.skills.specialized.ai_researcher import AIResearcher
from lyra_cli.skills.specialized.ba_analyzer import BAAnalyzer
from lyra_cli.skills.specialized.brainstorm_facilitator import BrainstormFacilitator
from lyra_cli.skills.specialized.cloud_architect import CloudArchitect
from lyra_cli.skills.specialized.code_reviewer import (
    CodeReviewerSkill,
)
from lyra_cli.skills.specialized.data_engineer import DataEngineer
from lyra_cli.skills.specialized.debugging_assistant import DebuggingAssistant
from lyra_cli.skills.specialized.dependency_analyzer import DependencyAnalyzerSkill
from lyra_cli.skills.specialized.design_reviewer import DesignReviewer
from lyra_cli.skills.specialized.documentation_writer import DocumentationWriterSkill
from lyra_cli.skills.specialized.performance_profiler import PerformanceProfilerSkill
from lyra_cli.skills.specialized.pm_planner import PMPlanner
from lyra_cli.skills.specialized.refactoring_advisor import RefactoringAdvisorSkill
from lyra_cli.skills.specialized.security_auditor import (
    SecurityAuditorSkill,
)
from lyra_cli.skills.specialized.solution_architect import SolutionArchitect
from lyra_cli.skills.specialized.sre_incident_responder import SREIncidentResponder
from lyra_cli.skills.specialized.test_generator import TestGeneratorSkill

# =========================================================================
# Existing Registry Tests
# =========================================================================


class TestSpecializedSkills:
    """Test specialized skills registry."""

    def test_registry_initialization(self):
        """Test that registry initializes correctly."""
        registry = get_registry()
        assert registry is not None
        assert len(registry.list_skills()) > 0

    def test_list_all_skills(self):
        """Test listing all skills."""
        skills = list_all_skills()
        assert len(skills) >= 14  # At least 14 skills created

        # Check for expected skills
        expected_skills = [
            "backend-engineer",
            "frontend-engineer",
            "testing-engineer",
            "devops-engineer",
            "fullstack-engineer",
            "ui-ux-designer",
            "system-designer",
            "sre-engineer",
            "ai-researcher",
            "solution-architect",
            "cloud-architect",
            "product-manager",
            "business-analyst",
            "brainstorming-facilitator",
        ]

        for skill in expected_skills:
            assert skill in skills, f"Expected skill {skill} not found"

    def test_get_skill_by_name(self):
        """Test getting skill by name."""
        skill = get_skill_by_name("backend-engineer")
        assert skill is not None
        assert skill.name == "backend-engineer"
        assert skill.domain == "engineering"
        assert "backend" in skill.tags
        assert len(skill.triggers) > 0

    def test_search_by_trigger(self):
        """Test searching skills by trigger."""
        results = search_skills("backend")
        assert len(results) > 0
        assert any(s.name == "backend-engineer" for s in results)

    def test_search_by_tag(self):
        """Test searching skills by tag."""
        results = search_skills("engineering")
        assert len(results) >= 5  # At least 5 engineering skills

    def test_list_by_domain(self):
        """Test listing skills by domain."""
        registry = get_registry()

        engineering_skills = registry.list_by_domain("engineering")
        assert len(engineering_skills) == 5

        design_skills = registry.list_by_domain("design")
        assert len(design_skills) == 2

        sre_skills = registry.list_by_domain("sre")
        assert len(sre_skills) == 1

    def test_skill_content(self):
        """Test getting skill content."""
        registry = get_registry()
        content = registry.get_skill_content("backend-engineer")
        assert content is not None
        assert "Backend Engineer" in content
        assert "API Design" in content

    def test_skill_metadata_completeness(self):
        """Test that all skills have complete metadata."""
        registry = get_registry()

        for skill in registry.list_skills():
            assert skill.name, f"Skill {skill.file_path} missing name"
            assert skill.description, f"Skill {skill.name} missing description"
            assert skill.tags, f"Skill {skill.name} missing tags"
            assert skill.triggers, f"Skill {skill.name} missing triggers"
            assert skill.model in [
                "haiku",
                "sonnet",
                "opus",
            ], f"Skill {skill.name} has invalid model: {skill.model}"
            assert (
                skill.file_path.exists()
            ), f"Skill {skill.name} file does not exist: {skill.file_path}"

    def test_skill_file_structure(self):
        """Test that skill files have proper structure."""
        registry = get_registry()

        for skill in registry.list_skills():
            content = skill.file_path.read_text()

            # Check for YAML frontmatter
            assert content.startswith("---"), f"Skill {skill.name} missing YAML frontmatter"

            # Check for required sections
            assert "# " in content, f"Skill {skill.name} missing main heading"

            # Check for core competencies section
            assert (
                "Core Competencies" in content or "Competencies" in content
            ), f"Skill {skill.name} missing competencies section"

    def test_no_duplicate_skills(self):
        """Test that there are no duplicate skill names."""
        skills = list_all_skills()
        assert len(skills) == len(set(skills)), "Duplicate skill names found"

    def test_skill_triggers_unique(self):
        """Test that skill triggers are reasonably unique."""
        registry = get_registry()

        # Check that each trigger doesn't match too many skills
        all_triggers = set()
        for skill in registry.list_skills():
            all_triggers.update(skill.triggers)

        for trigger in all_triggers:
            matches = search_skills(trigger)
            # Each trigger should match at most 3 skills
            assert (
                len(matches) <= 3
            ), f"Trigger '{trigger}' matches too many skills: {[s.name for s in matches]}"


class TestSkillIntegration:
    """Test integration with skill curator."""

    def test_skill_discovery(self):
        """Test that specialized skills are discoverable."""
        from lyra_cli.skills.skill_curator import SkillCurator

        curator = SkillCurator()
        discovered = curator.discover_skills()

        # Should discover at least the specialized skills
        assert discovered >= 14

    def test_skill_selection(self):
        """Test that skills can be selected based on context."""
        from lyra_cli.skills.skill_curator import SelectionContext, SkillCurator

        curator = SkillCurator()
        curator.discover_skills()

        # Test backend context
        context = SelectionContext(
            current_file="api.py",
            recent_tools=("Read", "Write", "Bash"),
            task_description="implement REST API endpoint",
            active_skills=(),
            error_history=(),
        )

        result = curator.select_skills(context, max_skills=5)
        assert len(result.selected_skills) > 0

        # Should select backend-related skills (may include other skills from ~/.claude/skills)
        skill_names = [s.skill_name for s in result.selected_skills]
        # Check that at least one backend-related skill is selected
        backend_related = any(
            "backend" in name or "api" in name or "fullstack" in name for name in skill_names
        )
        assert backend_related, f"No backend-related skills found in: {skill_names}"


class TestSkillContent:
    """Test skill content quality."""

    def test_backend_skill_content(self):
        """Test backend engineer skill content."""
        registry = get_registry()
        content = registry.get_skill_content("backend-engineer")

        # Check for key sections
        assert "API Design" in content
        assert "Database" in content
        assert "Authentication" in content
        assert "Caching" in content
        assert "Scalability" in content

    def test_frontend_skill_content(self):
        """Test frontend engineer skill content."""
        registry = get_registry()
        content = registry.get_skill_content("frontend-engineer")

        # Check for key sections
        assert "React" in content
        assert "Performance" in content
        assert "Accessibility" in content
        assert "Testing" in content

    def test_sre_skill_content(self):
        """Test SRE engineer skill content."""
        registry = get_registry()
        content = registry.get_skill_content("sre-engineer")

        # Check for key sections
        assert "Observability" in content
        assert "Incident" in content
        assert "SLO" in content or "SLI" in content
        assert "Monitoring" in content

    def test_product_manager_skill_content(self):
        """Test product manager skill content."""
        registry = get_registry()
        content = registry.get_skill_content("product-manager")

        # Check for key sections
        assert "Roadmap" in content
        assert "Prioritization" in content
        assert "User Stories" in content or "User Story" in content
        assert "OKR" in content


# =========================================================================
# Code Reviewer Skill Tests
# =========================================================================

GOOD_CODE = """
def add(a: int, b: int) -> int:
    return a + b
"""

BAD_CODE = """
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
import pdb

def run(cmd):
    eval(cmd)
    return os.system(cmd)
"""


class TestCodeReviewerSkill:
    """Tests for the CodeReviewerSkill."""

    def test_empty_source(self):
        skill = CodeReviewerSkill()
        result = skill.run({"source": ""})
        assert "error" in result

    def test_clean_code_no_findings(self):
        skill = CodeReviewerSkill()
        result = skill.run({"source": GOOD_CODE})
        assert "findings" in result
        # Good code should have minimal or no findings
        critical_high = [f for f in result["findings"] if f["severity"] in ("CRITICAL", "HIGH")]
        assert len(critical_high) == 0

    def test_bare_except_detected(self):
        skill = CodeReviewerSkill()
        result = skill.run({"source": BAD_CODE})
        findings = result["findings"]
        bare_excepts = [f for f in findings if f["code"] == "BARE_EXCEPT"]
        assert len(bare_excepts) >= 1
        assert bare_excepts[0]["severity"] == "HIGH"
        assert bare_excepts[0]["category"] == "error_prone"

    def test_dangerous_patterns_detected(self):
        skill = CodeReviewerSkill()
        result = skill.run({"source": DANGEROUS_CODE})
        findings = result["findings"]
        codes = {f["code"] for f in findings}
        assert "EVAL_USAGE" in codes
        assert "OS_SYSTEM" in codes
        assert "DEBUG_IMPORT" in codes
        assert result["summary"]["critical"] >= 1

    def test_review_report_structure(self):
        skill = CodeReviewerSkill()
        result = skill.run({"source": DANGEROUS_CODE, "file_path": "test.py"})
        assert "file_path" in result
        assert "findings" in result
        assert "summary" in result
        assert "line_count" in result
        assert result["file_path"] == "test.py"


# =========================================================================
# Security Auditor Skill Tests
# =========================================================================

SECURE_CODE = """
def safe_function():
    x = 1 + 1
    return x
"""

INSECURE_CODE = """
import pickle
import hashlib

api_key = "sk-abc123def456ghi789jkl"
password = "supersecret123"

def process(data):
    result = pickle.loads(data)
    return result
"""


class TestSecurityAuditorSkill:
    """Tests for the SecurityAuditorSkill."""

    def test_empty_source(self):
        skill = SecurityAuditorSkill()
        result = skill.run({"source": ""})
        assert "error" in result

    def test_secure_code_no_vulnerabilities(self):
        skill = SecurityAuditorSkill()
        result = skill.run({"source": SECURE_CODE})
        if "vulnerabilities" in result:
            assert len(result["vulnerabilities"]) == 0

    def test_detects_hardcoded_secrets(self):
        skill = SecurityAuditorSkill()
        result = skill.run({"source": INSECURE_CODE})
        vulns = result["vulnerabilities"]
        titles = [v["title"] for v in vulns]
        assert "Hardcoded API Key" in titles
        assert "Hardcoded Password" in titles

    def test_detects_insecure_deserialization(self):
        skill = SecurityAuditorSkill()
        result = skill.run({"source": INSECURE_CODE})
        vulns = result["vulnerabilities"]
        titles = [v["title"] for v in vulns]
        assert "pickle deserialization" in titles

    def test_owasp_categories_assigned(self):
        skill = SecurityAuditorSkill()
        result = skill.run({"source": INSECURE_CODE})
        for v in result["vulnerabilities"]:
            assert "owasp_category" in v
            assert "severity" in v
            assert v["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_vulnerability_report_structure(self):
        skill = SecurityAuditorSkill()
        result = skill.run({"source": INSECURE_CODE, "file_path": "test.py"})
        assert "file_path" in result
        assert "vulnerabilities" in result
        assert "summary" in result
        assert result["file_path"] == "test.py"


# =========================================================================
# Test Generator Skill Tests
# =========================================================================

FUNCTION_SOURCE = """
def add(a: int, b: int) -> int:
    return a + b

def greet(name: str) -> str:
    return f"Hello, {name}!"

async def fetch_data(url: str) -> dict:
    return {"status": "ok"}
"""


class TestTestGeneratorSkill:
    """Tests for the TestGeneratorSkill."""

    def test_empty_source(self):
        skill = TestGeneratorSkill()
        result = skill.run({"source": ""})
        assert "error" in result

    def test_generates_tests_for_functions(self):
        skill = TestGeneratorSkill()
        result = skill.run({"source": FUNCTION_SOURCE})
        assert "tests" in result
        assert len(result["tests"]) == 3  # add, greet, fetch_data

    def test_generates_test_cases(self):
        skill = TestGeneratorSkill()
        result = skill.run({"source": FUNCTION_SOURCE, "module_name": "mymod"})
        for test in result["tests"]:
            assert "function_name" in test
            assert "test_cases" in test
            assert len(test["test_cases"]) >= 3  # happy, edge, error
            assert "code" in test

    def test_test_cases_have_categories(self):
        skill = TestGeneratorSkill()
        result = skill.run({"source": FUNCTION_SOURCE})
        for test in result["tests"]:
            categories = {tc["category"] for tc in test["test_cases"]}
            assert "happy_path" in categories
            assert "boundary" in categories
            assert "error_case" in categories

    def test_specific_function_filter(self):
        skill = TestGeneratorSkill()
        result = skill.run(
            {
                "source": FUNCTION_SOURCE,
                "function_names": ["add"],
            }
        )
        assert len(result["tests"]) == 1
        assert result["tests"][0]["function_name"] == "add"


# =========================================================================
# Refactoring Advisor Skill Tests
# =========================================================================

LONG_FUNCTION = """
def process_data(items, config=None, options=None, extra=None):
    result = []
    for item in items:
        if item.is_valid() or item.is_active() or item.has_permission():
            if item.value > 0 and item.value < 1000:
                transformed = item.value * 2
                if transformed < 100:
                    result.append(transformed)
                elif transformed < 200:
                    result.append(transformed // 2)
                elif transformed < 500:
                    result.append(transformed // 4)
                else:
                    result.append(100)
            else:
                result.append(0)
        else:
            result.append(-1)
    if config and config.get("sort"):
        result.sort(reverse=config.get("reverse", False))
    if options and options.get("deduplicate"):
        result = list(set(result))
    if extra and extra.get("normalize"):
        result = [x / max(result) for x in result]
    if config and config.get("limit"):
        result = result[: config.get("limit", 10)]
    validated = []
    for item in result:
        if item is not None:
            validated.append(item)
    return validated
"""

SIMPLE_CODE = """
def add(a, b):
    return a + b
"""


class TestRefactoringAdvisorSkill:
    """Tests for the RefactoringAdvisorSkill."""

    def test_empty_source(self):
        skill = RefactoringAdvisorSkill()
        result = skill.run({"source": ""})
        assert "error" in result

    def test_simple_code_no_suggestions(self):
        skill = RefactoringAdvisorSkill()
        result = skill.run({"source": SIMPLE_CODE})
        # Short functions should have minimal suggestions
        if "suggestions" in result:
            extract_methods = [s for s in result["suggestions"] if s["type"] == "extract_method"]
            assert len(extract_methods) == 0

    def test_complex_code_produces_suggestions(self):
        skill = RefactoringAdvisorSkill()
        result = skill.run({"source": LONG_FUNCTION})
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0

    def test_suggestion_has_required_fields(self):
        skill = RefactoringAdvisorSkill()
        result = skill.run({"source": LONG_FUNCTION})
        for s in result["suggestions"]:
            assert "type" in s
            assert "line" in s
            assert "description" in s
            assert "reason" in s
            assert "before_code" in s
            assert "after_code" in s
            assert "complexity_score" in s

    def test_summary_is_present(self):
        skill = RefactoringAdvisorSkill()
        result = skill.run({"source": LONG_FUNCTION})
        assert "summary" in result
        assert "file_path" in result


# =========================================================================
# Documentation Writer Skill Tests
# =========================================================================

UNDOCUMENTED = """
def calculate(value: int, factor: float = 1.0) -> float:
    if value < 0:
        raise ValueError("Value must be non-negative")
    return value * factor


class DataProcessor:
    def __init__(self, name: str):
        self.name = name

    def run(self) -> bool:
        return True
"""


class TestDocumentationWriterSkill:
    """Tests for the DocumentationWriterSkill."""

    def test_empty_source(self):
        skill = DocumentationWriterSkill()
        result = skill.run({"source": ""})
        assert "error" in result

    def test_generates_docstrings(self):
        skill = DocumentationWriterSkill()
        result = skill.run({"source": UNDOCUMENTED, "module_name": "testmod"})
        assert "docstrings" in result
        # Should find calculate, __init__, run (DataProcessor.run counts as public)
        assert len(result["docstrings"]) >= 2

    def test_docstrings_have_google_style(self):
        skill = DocumentationWriterSkill()
        result = skill.run({"source": UNDOCUMENTED})
        for ds in result["docstrings"]:
            assert "target_name" in ds
            assert "target_type" in ds
            assert "docstring" in ds
            assert '"""' in ds["docstring"]

    def test_generates_readme_section(self):
        skill = DocumentationWriterSkill()
        result = skill.run(
            {
                "source": UNDOCUMENTED,
                "module_name": "testmod",
                "output_format": "readme",
            }
        )
        assert "readme_section" in result
        assert "Functions" in result["readme_section"]
        assert "calculate" in result["readme_section"]

    def test_api_endpoints_detected(self):
        skill = DocumentationWriterSkill()
        result = skill.run({"source": UNDOCUMENTED})
        assert "api_endpoints" in result
        assert len(result["api_endpoints"]) >= 1


# =========================================================================
# Performance Profiler Skill Tests
# =========================================================================

SLOW_CODE = """
def sort_and_process(items):
    result = []
    for i in items:
        for j in items:
            result.append(i * j)
    return sorted(result)
"""

FAST_CODE = """
def constant_time():
    return 42
"""


class TestPerformanceProfilerSkill:
    """Tests for the PerformanceProfilerSkill."""

    def test_empty_source(self):
        skill = PerformanceProfilerSkill()
        result = skill.run({"source": ""})
        assert "error" in result

    def test_fast_code_no_issues(self):
        skill = PerformanceProfilerSkill()
        result = skill.run({"source": FAST_CODE})
        for r in result.get("results", []):
            assert len(r["issues"]) == 0

    def test_nested_loop_detected(self):
        skill = PerformanceProfilerSkill()
        result = skill.run({"source": SLOW_CODE})
        issues = []
        for r in result["results"]:
            issues.extend(r["issues"])
        nested = [i for i in issues if "Nested loops" in str(i)]
        assert len(nested) >= 1

    def test_complexity_estimated(self):
        skill = PerformanceProfilerSkill()
        result = skill.run({"source": SLOW_CODE, "module_name": "testmod"})
        for r in result["results"]:
            assert "estimated_complexity" in r
            assert r["estimated_complexity"] in (
                "O(1)",
                "O(log n)",
                "O(n)",
                "O(n log n)",
                "O(n^2)",
                "O(n^3)",
                "O(2^n)",
                "O(?)",
            )

    def test_profile_report_structure(self):
        skill = PerformanceProfilerSkill()
        result = skill.run({"source": SLOW_CODE})
        assert "results" in result
        assert "summary" in result
        assert "module_name" in result


# =========================================================================
# Dependency Analyzer Skill Tests
# =========================================================================

SIMPLE_IMPORTS = """
import os
import json
from typing import List, Optional
from datetime import datetime
import non_existent_package
"""

LOCAL_IMPORTS = """
import os
import sys
from lyra_cli.skills.skill_curator import SkillCurator
from lyra_tools.code_analysis import analyze
"""


class TestDependencyAnalyzerSkill:
    """Tests for the DependencyAnalyzerSkill."""

    def test_empty_source(self):
        skill = DependencyAnalyzerSkill()
        result = skill.run({"source": ""})
        assert "error" in result

    def test_parses_imports(self):
        skill = DependencyAnalyzerSkill()
        result = skill.run({"source": SIMPLE_IMPORTS})
        assert "imports" in result
        modules = {i["module"] for i in result["imports"]}
        assert "os" in modules
        assert "json" in modules
        assert "typing" in modules
        assert "datetime" in modules

    def test_classifies_dependency_types(self):
        skill = DependencyAnalyzerSkill()
        result = skill.run({"source": SIMPLE_IMPORTS})
        types_seen = {i["dependency_type"] for i in result["imports"]}
        assert "standard_library" in types_seen

    def test_statistics_computed(self):
        skill = DependencyAnalyzerSkill()
        result = skill.run({"source": LOCAL_IMPORTS, "module_name": "testmod"})
        assert "statistics" in result
        stats = result["statistics"]
        assert "total_imports" in stats
        assert "standard_library" in stats
        assert "local" in stats
        assert "health_score" in stats
        assert stats["total_imports"] == len(result["imports"])

    def test_suggestions_generated(self):
        skill = DependencyAnalyzerSkill()
        result = skill.run(
            {
                "source": LOCAL_IMPORTS,
                "all_sources": {
                    "mod_a": "import os\nfrom lyra_cli.skills import skill_curator",
                    "mod_b": "import json\nfrom lyra_cli.skills import skill_curator",
                },
            }
        )
        assert "suggestions" in result


# =========================================================================
# SRE Incident Responder Skill Tests
# =========================================================================


class TestSREIncidentResponder:
    """Tests for the SREIncidentResponder."""

    def test_empty_description(self):
        skill = SREIncidentResponder()
        result = skill.run({"incident_description": ""})
        assert "error" in result

    def test_sev1_classification(self):
        skill = SREIncidentResponder()
        result = skill.run(
            {
                "incident_description":(
                    "Production is completely down. All users affected. Critical outage in"
                    "progress."
                ),
            }
        )
        assert result["severity"] == "SEV1"
        assert "impact" in result
        assert result["impact"]["affected_users_percentage"] == "100%"

    def test_sev3_classification(self):
        skill = SREIncidentResponder()
        result = skill.run(
            {
                "incident_description": "Minor cosmetic issue on settings page for single user.",
            }
        )
        assert result["severity"] == "SEV3"

    def test_runbook_generated(self):
        skill = SREIncidentResponder()
        result = skill.run(
            {
                "incident_description":(
                    "Database connection pool exhausted. High error rates on API."
                ),
                "environment": "production",
                "incident_title": "DB Connection Exhaustion",
            }
        )
        assert "runbook" in result
        assert len(result["runbook"]["steps"]) > 0
        assert result["runbook"]["owner_team"] == "SRE Team (on-call)"

    def test_escalation_path_present(self):
        skill = SREIncidentResponder()
        result = skill.run(
            {
                "incident_description": "Security breach detected in authentication service.",
            }
        )
        assert "escalation_path" in result
        assert len(result["escalation_path"]) >= 2

    def test_post_mortem_template(self):
        skill = SREIncidentResponder()
        result = skill.run(
            {
                "incident_description": "Cache cluster failure caused increased latency.",
            }
        )
        assert "post_mortem_template" in result
        assert "Root Cause Analysis" in result["post_mortem_template"]["root_cause_section"]


# =========================================================================
# Cloud Architect Skill Tests
# =========================================================================


class TestCloudArchitect:
    """Tests for the CloudArchitect."""

    def test_empty_requirements(self):
        skill = CloudArchitect()
        result = skill.run({"requirements": ""})
        assert "error" in result

    def test_basic_architecture(self):
        skill = CloudArchitect()
        result = skill.run(
            {
                "requirements":(
                    "Need a web application with database storage and user authentication."
                ),
                "project_name": "MyApp",
                "provider": "AWS",
            }
        )
        assert result["title"] == "MyApp"
        assert len(result["components"]) >= 3
        assert any("auth" in c["name"] for c in result["components"])

    def test_gcp_provider(self):
        skill = CloudArchitect()
        result = skill.run(
            {
                "requirements": "Global application with CDN and caching.",
                "provider": "GCP",
            }
        )
        assert result["provider"] == "GCP"
        assert any("cdn" in c["name"].lower() for c in result["components"])

    def test_cost_breakdown(self):
        skill = CloudArchitect()
        result = skill.run(
            {
                "requirements": "Simple API service with database.",
                "budget_monthly": "5000",
            }
        )
        assert "cost" in result
        assert result["cost"]["currency"] == "USD"

    def test_high_availability_design(self):
        skill = CloudArchitect()
        result = skill.run(
            {
                "requirements":(
                    "System requires high availability and disaster recovery with multi-region"
                    "support."
                ),
            }
        )
        assert result["availability"]["multi_az"] is True
        assert result["availability"]["multi_region"] is True
        assert "99.99" in result["availability"]["sla_percentage"]


# =========================================================================
# Solution Architect Skill Tests
# =========================================================================


class TestSolutionArchitect:
    """Tests for the SolutionArchitect."""

    def test_empty_requirements(self):
        skill = SolutionArchitect()
        result = skill.run({"requirements": ""})
        assert "error" in result

    def test_basic_solution_architecture(self):
        skill = SolutionArchitect()
        result = skill.run(
            {
                "requirements":(
                    "Build a scalable e-commerce platform with real-time inventory updates."
                ),
                "project_name": "E-Commerce Platform",
            }
        )
        assert result["title"] == "E-Commerce Platform"
        assert len(result["components"]) >= 3
        assert "trade_offs" in result
        assert len(result["trade_offs"]) >= 1

    def test_trade_off_analysis(self):
        skill = SolutionArchitect()
        result = skill.run(
            {
                "requirements": "Financial transaction processing system.",
            }
        )
        # Financial systems should prefer CP
        cap_decision = next(t for t in result["trade_offs"] if "CAP" in t["title"])
        assert cap_decision["chosen"] == "CP"

    def test_sequence_diagrams(self):
        skill = SolutionArchitect()
        result = skill.run(
            {
                "requirements": "Build a REST API with external integrations.",
            }
        )
        assert "sequence_diagrams" in result
        assert "main_request_flow" in result["sequence_diagrams"]
        assert "error_handling_flow" in result["sequence_diagrams"]

    def test_tech_stack(self):
        skill = SolutionArchitect()
        result = skill.run(
            {
                "requirements": "Build a web application with ML capabilities.",
            }
        )
        layers = [t["layer"] for t in result["tech_stack"]]
        assert "ML/AI" in layers


# =========================================================================
# PM Planner Skill Tests
# =========================================================================


class TestPMPlanner:
    """Tests for the PMPlanner."""

    def test_empty_description(self):
        skill = PMPlanner()
        result = skill.run({"project_description": ""})
        assert "error" in result

    def test_wbs_generated(self):
        skill = PMPlanner()
        result = skill.run(
            {
                "project_description": "Build a new SaaS product with team of 5 engineers.",
                "project_name": "SaaS Product",
            }
        )
        assert "wbs" in result
        assert len(result["wbs"]["phases"]) >= 3
        assert result["wbs"]["total_estimated_hours"] > 0

    def test_milestones_created(self):
        skill = PMPlanner()
        result = skill.run(
            {
                "project_description": "Develop a mobile app with backend API.",
            }
        )
        assert "milestones" in result
        assert len(result["milestones"]) >= 4

    def test_risk_register(self):
        skill = PMPlanner()
        result = skill.run(
            {
                "project_description": "Build a system requiring security and compliance.",
            }
        )
        assert "risk_register" in result
        risks = result["risk_register"]
        categories = {r["category"] for r in risks}
        assert "technical" in categories or "schedule" in categories

    def test_stakeholder_analysis(self):
        skill = PMPlanner()
        result = skill.run(
            {
                "project_description": "Enterprise system with multiple teams.",
                "team_size": 8,
            }
        )
        assert "stakeholders" in result
        assert len(result["stakeholders"]) >= 4


# =========================================================================
# BA Analyzer Skill Tests
# =========================================================================


class TestBAAnalyzer:
    """Tests for the BAAnalyzer."""

    def test_empty_requirements(self):
        skill = BAAnalyzer()
        result = skill.run({"requirements": ""})
        assert "error" in result

    def test_use_cases_generated(self):
        skill = BAAnalyzer()
        result = skill.run(
            {
                "requirements": "Users need to log in and manage their data securely.",
                "project_name": "User Portal",
            }
        )
        assert result["title"] == "User Portal"
        assert "use_cases" in result
        assert len(result["use_cases"]) >= 1

    def test_user_stories(self):
        skill = BAAnalyzer()
        result = skill.run(
            {
                "requirements": "Build a notification system with email alerts.",
            }
        )
        assert "user_stories" in result
        stories = result["user_stories"]
        assert any(
            "notification" in s["i_want"].lower() or "notify" in s["i_want"].lower()
            for s in stories
        )

    def test_functional_and_non_functional(self):
        skill = BAAnalyzer()
        result = skill.run(
            {
                "requirements": "Build a reliable and secure system.",
            }
        )
        assert "functional_reqs" in result
        assert len(result["functional_reqs"]) >= 3
        assert "non_functional_reqs" in result
        assert len(result["non_functional_reqs"]) >= 3

    def test_gap_analysis(self):
        skill = BAAnalyzer()
        result = skill.run(
            {
                "requirements": "Basic CRUD operations.",
            }
        )
        assert "gaps" in result
        # Should flag missing performance/security requirements
        assert len(result["gaps"]) >= 2


# =========================================================================
# Brainstorm Facilitator Skill Tests
# =========================================================================


class TestBrainstormFacilitator:
    """Tests for the BrainstormFacilitator."""

    def test_empty_topic(self):
        skill = BrainstormFacilitator()
        result = skill.run({"topic": ""})
        assert "error" in result

    def test_scamper_method(self):
        skill = BrainstormFacilitator()
        result = skill.run(
            {
                "topic": "Improve our mobile app onboarding experience",
                "method": "SCAMPER",
            }
        )
        assert result["method"] == "SCAMPER"
        assert "ideas" in result
        assert len(result["top_ideas"]) > 0

    def test_six_hats_method(self):
        skill = BrainstormFacilitator()
        result = skill.run(
            {
                "topic": "New feature prioritization",
                "method": "six_thinking_hats",
            }
        )
        assert result["method"] == "six_thinking_hats"
        assert "hats" in result["ideas"]
        colors = {h["hat_color"] for h in result["ideas"]["hats"]}
        assert "White" in colors
        assert "Green" in colors
        assert "Black" in colors

    def test_random_stimulus(self):
        skill = BrainstormFacilitator()
        result = skill.run(
            {
                "topic": "Improve team collaboration",
                "method": "random_stimulus",
            }
        )
        assert result["method"] == "random_stimulus"
        assert "stimulus_ideas" in result["ideas"]

    def test_reverse_brainstorming(self):
        skill = BrainstormFacilitator()
        result = skill.run(
            {
                "topic": "Reduce customer churn",
                "method": "reverse_brainstorming",
            }
        )
        assert result["method"] == "reverse_brainstorming"
        assert "reverse_ideas" in result["ideas"]


# =========================================================================
# Data Engineer Skill Tests
# =========================================================================


class TestDataEngineer:
    """Tests for the DataEngineer."""

    def test_empty_requirements(self):
        skill = DataEngineer()
        result = skill.run({"requirements": ""})
        assert "error" in result

    def test_pipeline_design(self):
        skill = DataEngineer()
        result = skill.run(
            {
                "requirements": "Build a data pipeline for analytics with batch processing.",
                "project_name": "Analytics Pipeline",
            }
        )
        assert "pipeline" in result
        assert result["pipeline"]["mode"] == "batch"
        assert len(result["pipeline"]["steps"]) >= 3

    def test_streaming_pipeline(self):
        skill = DataEngineer()
        result = skill.run(
            {
                "requirements": "Real-time streaming data from Kafka with low latency.",
            }
        )
        assert result["pipeline"]["mode"] == "streaming"

    def test_data_model(self):
        skill = DataEngineer()
        result = skill.run(
            {
                "requirements": "Design star schema for e-commerce analytics.",
            }
        )
        assert "data_model" in result
        model = result["data_model"]
        assert model["schema_type"] == "star_schema"
        assert len(model["fact_tables"]) >= 1
        assert len(model["dimension_tables"]) >= 2

    def test_quality_checks(self):
        skill = DataEngineer()
        result = skill.run(
            {
                "requirements": "Need robust data quality monitoring.",
            }
        )
        assert "quality_checks" in result
        assert len(result["quality_checks"]) >= 4


# =========================================================================
# AI Researcher Skill Tests
# =========================================================================


class TestAIResearcher:
    """Tests for the AIResearcher."""

    def test_empty_question(self):
        skill = AIResearcher()
        result = skill.run({"research_question": ""})
        assert "error" in result

    def test_research_plan_structure(self):
        skill = AIResearcher()
        result = skill.run(
            {
                "research_question":(
                    "Can self-supervised learning improve few-shot classification accuracy?"
                ),
                "domain": "computer vision",
            }
        )
        assert "question" in result
        assert result["question"]["primary_question"] == result["title"]
        assert len(result["question"]["sub_questions"]) >= 2

    def test_literature_review(self):
        skill = AIResearcher()
        result = skill.run(
            {
                "research_question":(
                    "How effective are transformer models for time series forecasting?"
                ),
            }
        )
        assert "literature_review" in result
        assert len(result["literature_review"]) >= 2

    def test_experiment_design(self):
        skill = AIResearcher()
        result = skill.run(
            {
                "research_question": "Does model scaling improve NLP task performance?",
                "research_type": "empirical",
            }
        )
        assert "experiments" in result
        assert len(result["experiments"]) >= 3
        assert "evaluation" in result
        assert len(result["evaluation"]["primary_metrics"]) >= 2


# =========================================================================
# Design Reviewer Skill Tests
# =========================================================================


class TestDesignReviewer:
    """Tests for the DesignReviewer."""

    def test_empty_doc(self):
        skill = DesignReviewer()
        result = skill.run({"design_doc": ""})
        assert "error" in result

    def test_good_design_review(self):
        skill = DesignReviewer()
        result = skill.run(
            {
                "design_doc": (
                    "This system uses the repository pattern for data access. "
                    "We use dependency injection throughout. "
                    "The architecture uses CQRS for separating reads and writes. "
                    "Circuit breaker pattern is used for resilience. "
                    "Horizontal scaling is supported via stateless services. "
                    "Caching strategy includes Redis for hot data. "
                    "Error handling includes retries with exponential backoff."
                ),
                "design_title": "Order Processing System",
            }
        )
        assert result["design_title"] == "Order Processing System"
        assert result["overall_quality"] in ("EXCELLENT", "GOOD", "ADEQUATE")

    def test_pattern_assessment(self):
        skill = DesignReviewer()
        result = skill.run(
            {
                "design_doc": "Simple architecture with no specific patterns mentioned.",
            }
        )
        assert "pattern_assessments" in result
        assessments = result["pattern_assessments"]
        assert len(assessments) >= 5

    def test_scalability_analysis(self):
        skill = DesignReviewer()
        result = skill.run(
            {
                "design_doc": "Single server deployment with no caching or queue.",
            }
        )
        assert "scalability_findings" in result
        high_risk = [s for s in result["scalability_findings"] if s["risk_level"] == "HIGH"]
        assert len(high_risk) >= 2

    def test_improvement_suggestions(self):
        skill = DesignReviewer()
        result = skill.run(
            {
                "design_doc": "Basic CRUD API design.",
            }
        )
        assert "improvements" in result
        assert len(result["improvements"]) >= 2


# =========================================================================
# Debugging Assistant Skill Tests
# =========================================================================


class TestDebuggingAssistant:
    """Tests for the DebuggingAssistant."""

    def test_empty_error(self):
        skill = DebuggingAssistant()
        result = skill.run({"error_description": ""})
        assert "error" in result

    def test_five_whys_analysis(self):
        skill = DebuggingAssistant()
        result = skill.run(
            {
                "error_description": "NullPointerException when processing user profile data.",
                "environment": "Production - us-east-1",
            }
        )
        assert result["environment"] == "Production - us-east-1"
        assert "five_whys" in result
        assert len(result["five_whys"]) == 5

    def test_hypothesis_generation(self):
        skill = DebuggingAssistant()
        result = skill.run(
            {
                "error_description":(
                    "TypeError: expected str, got NoneType in user authentication flow."
                ),
                "stack_trace": "File auth.py line 42 in validate_token()",
            }
        )
        assert "hypotheses" in result
        assert len(result["hypotheses"]) >= 3

    def test_diagnostic_steps(self):
        skill = DebuggingAssistant()
        result = skill.run(
            {
                "error_description":(
                    "API timeout after recent deployment. Configuration may be wrong."
                ),
            }
        )
        assert "diagnostic_steps" in result
        assert len(result["diagnostic_steps"]) >= 5

    def test_fix_suggestions(self):
        skill = DebuggingAssistant()
        result = skill.run(
            {
                "error_description": "Null reference in payment processing module.",
            }
        )
        assert "fix_suggestions" in result
        assert len(result["fix_suggestions"]) >= 2
        assert any("confidence" in f for f in result["fix_suggestions"])

    def test_regression_tests(self):
        skill = DebuggingAssistant()
        result = skill.run(
            {
                "error_description": "Race condition in concurrent task scheduler.",
            }
        )
        assert "regression_tests" in result
        assert len(result["regression_tests"]) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
