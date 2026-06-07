"""Twenty-one skill templates spanning all nine domains, registered in TEMPLATE_REGISTRY."""

from __future__ import annotations

from lyra.skill_generator.models import SkillDomain, SkillTemplate

# ── CODING (3) ──────────────────────────────────────────────────────────────

CODING_FUNCTION_GENERATOR = SkillTemplate(
    domain=SkillDomain.CODING,
    name="function_generator",
    description="Generate a well-typed, documented function with input validation and error handling from a natural-language specification.",
    trigger_keywords=["function", "implement", "write code", "utility", "helper"],
    sections=["specification", "signature", "implementation", "validation", "error_handling", "examples"],
    difficulty=0.4,
    dependencies=[],
)

CODING_REFACTOR = SkillTemplate(
    domain=SkillDomain.CODING,
    name="refactor",
    description="Refactor existing code for readability, performance, and maintainability while preserving behavior.",
    trigger_keywords=["refactor", "clean up", "improve", "simplify", "restructure"],
    sections=["input_analysis", "plan", "refactored_code", "diff", "rationale"],
    difficulty=0.6,
    dependencies=[],
)

CODING_API_CLIENT = SkillTemplate(
    domain=SkillDomain.CODING,
    name="api_client",
    description="Generate a typed API client wrapper with retry logic, error handling, and request/response models.",
    trigger_keywords=["api client", "rest client", "http wrapper", "endpoint", "axios", "requests"],
    sections=["specification", "models", "client", "retry_logic", "error_handling", "usage_examples"],
    difficulty=0.7,
    dependencies=["function_generator"],
)

# ── DEBUGGING (2) ───────────────────────────────────────────────────────────

DEBUGGING_ROOT_CAUSE = SkillTemplate(
    domain=SkillDomain.DEBUGGING,
    name="root_cause_analysis",
    description="Analyze error logs, stack traces, and reproduction steps to identify the root cause of a bug.",
    trigger_keywords=["debug", "bug", "error", "crash", "exception", "stack trace", "root cause"],
    sections=["symptoms", "reproduction", "hypothesis", "investigation", "root_cause", "fix"],
    difficulty=0.6,
    dependencies=[],
)

DEBUGGING_LOG_ANALYZER = SkillTemplate(
    domain=SkillDomain.DEBUGGING,
    name="log_analyzer",
    description="Parse and analyze application logs to detect anomalies, error patterns, and performance bottlenecks.",
    trigger_keywords=["log analysis", "log parsing", "anomaly", "pattern detection", "observability"],
    sections=["log_input", "parsing_strategy", "patterns", "anomalies", "summary"],
    difficulty=0.5,
    dependencies=[],
)

# ── TESTING (3) ─────────────────────────────────────────────────────────────

TESTING_UNIT_TEST = SkillTemplate(
    domain=SkillDomain.TESTING,
    name="unit_test_writer",
    description="Generate comprehensive unit tests for a given function or module, covering edge cases and error paths.",
    trigger_keywords=["unit test", "test case", "pytest", "jest", "spec", "coverage"],
    sections=["target", "test_plan", "test_cases", "edge_cases", "fixtures"],
    difficulty=0.4,
    dependencies=[],
)

TESTING_INTEGRATION_TEST = SkillTemplate(
    domain=SkillDomain.TESTING,
    name="integration_test_writer",
    description="Generate integration tests that exercise real dependencies and verify end-to-end behavior.",
    trigger_keywords=["integration test", "e2e test", "end to end", "smoke test", "contract test"],
    sections=["architecture", "test_scenarios", "setup", "test_cases", "teardown"],
    difficulty=0.7,
    dependencies=["unit_test_writer"],
)

TESTING_MOCK_DESIGNER = SkillTemplate(
    domain=SkillDomain.TESTING,
    name="mock_designer",
    description="Design mock objects, stubs, and fake implementations for isolating units under test.",
    trigger_keywords=["mock", "stub", "fake", "test double", "dependency injection"],
    sections=["interface_analysis", "mock_plan", "mock_implementations", "usage_examples", "verification"],
    difficulty=0.5,
    dependencies=[],
)

# ── SECURITY (2) ────────────────────────────────────────────────────────────

SECURITY_VULNERABILITY_SCAN = SkillTemplate(
    domain=SkillDomain.SECURITY,
    name="vulnerability_scanner",
    description="Scan source code for common security vulnerabilities and generate a prioritized remediation report.",
    trigger_keywords=["security", "vulnerability", "cve", "owasp", "injection", "xss", "csrf"],
    sections=["scope", "scan_results", "findings", "risk_assessment", "remediation"],
    difficulty=0.7,
    dependencies=[],
)

SECURITY_AUDIT_REVIEW = SkillTemplate(
    domain=SkillDomain.SECURITY,
    name="security_audit",
    description="Perform a structured security audit of a codebase, architecture, or deployment configuration.",
    trigger_keywords=["audit", "security review", "compliance", "threat model", "penetration test"],
    sections=["scope", "threat_model", "findings", "risk_matrix", "recommendations"],
    difficulty=0.8,
    dependencies=["vulnerability_scanner"],
)

# ── DEVOPS (2) ──────────────────────────────────────────────────────────────

DEVOPS_CI_PIPELINE = SkillTemplate(
    domain=SkillDomain.DEVOPS,
    name="ci_pipeline_generator",
    description="Generate CI/CD pipeline configuration for common platforms including build, test, lint, and deploy stages.",
    trigger_keywords=["ci/cd", "pipeline", "github actions", "gitlab ci", "jenkins", "deploy"],
    sections=["requirements", "stages", "configuration", "secrets", "deployment_strategy"],
    difficulty=0.6,
    dependencies=[],
)

DEVOPS_INFRASTRUCTURE = SkillTemplate(
    domain=SkillDomain.DEVOPS,
    name="infrastructure_code",
    description="Generate infrastructure-as-code templates for cloud resources with security best practices baked in.",
    trigger_keywords=["infrastructure", "terraform", "cloudformation", "iac", "kubernetes", "docker"],
    sections=["requirements", "architecture", "resources", "security", "cost_estimation"],
    difficulty=0.8,
    dependencies=[],
)

# ── DATA (3) ────────────────────────────────────────────────────────────────

DATA_PIPELINE = SkillTemplate(
    domain=SkillDomain.DATA,
    name="data_pipeline",
    description="Design a data pipeline for extraction, transformation, and loading with validation and monitoring.",
    trigger_keywords=["data pipeline", "etl", "elt", "data processing", "extract", "transform", "load"],
    sections=["source_analysis", "schema", "transformation", "validation", "monitoring"],
    difficulty=0.7,
    dependencies=[],
)

DATA_ANALYSIS = SkillTemplate(
    domain=SkillDomain.DATA,
    name="data_analysis",
    description="Perform exploratory data analysis with statistical summaries, visualizations, and actionable insights.",
    trigger_keywords=["data analysis", "eda", "exploratory", "statistics", "visualization", "dashboard"],
    sections=["dataset", "descriptive_stats", "visualizations", "insights", "recommendations"],
    difficulty=0.5,
    dependencies=[],
)

DATA_SCHEMA_DESIGN = SkillTemplate(
    domain=SkillDomain.DATA,
    name="schema_designer",
    description="Design a normalized database schema or data model from a domain specification.",
    trigger_keywords=["schema", "database design", "data model", "normalization", "ddl", "migration"],
    sections=["domain_analysis", "entities", "relationships", "indexes", "migration_plan"],
    difficulty=0.6,
    dependencies=[],
)

# ── DESIGN (2) ──────────────────────────────────────────────────────────────

DESIGN_COMPONENT = SkillTemplate(
    domain=SkillDomain.DESIGN,
    name="component_designer",
    description="Design a reusable UI or software component with props, states, and accessibility considerations.",
    trigger_keywords=["component", "ui design", "react", "reusable", "widget", "interface"],
    sections=["requirements", "api_design", "states", "accessibility", "examples"],
    difficulty=0.5,
    dependencies=[],
)

DESIGN_SYSTEM = SkillTemplate(
    domain=SkillDomain.DESIGN,
    name="system_designer",
    description="Design a high-level system architecture covering components, data flow, trade-offs, and scaling.",
    trigger_keywords=["architecture", "system design", "high level design", "hld", "distributed"],
    sections=["requirements", "architecture", "data_flow", "trade_offs", "scaling"],
    difficulty=0.9,
    dependencies=["component_designer"],
)

# ── MANAGEMENT (2) ──────────────────────────────────────────────────────────

MANAGEMENT_TASK_BREAKDOWN = SkillTemplate(
    domain=SkillDomain.MANAGEMENT,
    name="task_breakdown",
    description="Break down a high-level goal or feature into granular, actionable tasks with estimates and dependencies.",
    trigger_keywords=["task breakdown", "sprint planning", "estimation", "work breakdown", "ticket"],
    sections=["goal", "epics", "tasks", "estimates", "dependencies", "acceptance_criteria"],
    difficulty=0.4,
    dependencies=[],
)

MANAGEMENT_PROJECT_PLAN = SkillTemplate(
    domain=SkillDomain.MANAGEMENT,
    name="project_plan",
    description="Generate a full project plan with milestones, resource allocation, risk register, and timeline.",
    trigger_keywords=["project plan", "milestone", "roadmap", "gantt", "risk register", "timeline"],
    sections=["objectives", "milestones", "resources", "risks", "timeline", "success_criteria"],
    difficulty=0.6,
    dependencies=["task_breakdown"],
)

# ── RESEARCH (2) ────────────────────────────────────────────────────────────

RESEARCH_LITERATURE_REVIEW = SkillTemplate(
    domain=SkillDomain.RESEARCH,
    name="literature_review",
    description="Conduct a structured literature review with source summaries, thematic analysis, and research gaps.",
    trigger_keywords=["literature review", "related work", "survey", "sota", "state of the art"],
    sections=["research_question", "search_strategy", "sources", "thematic_analysis", "gaps", "conclusion"],
    difficulty=0.8,
    dependencies=[],
)

RESEARCH_EXPERIMENT_DESIGN = SkillTemplate(
    domain=SkillDomain.RESEARCH,
    name="experiment_design",
    description="Design a rigorous experiment with hypothesis, methodology, metrics, and statistical power analysis.",
    trigger_keywords=["experiment", "a/b test", "hypothesis", "methodology", "statistical test", "ab testing"],
    sections=["hypothesis", "design", "methodology", "metrics", "power_analysis", "limitations"],
    difficulty=0.7,
    dependencies=[],
)

# ── REGISTRY ────────────────────────────────────────────────────────────────

TEMPLATE_REGISTRY: dict[str, SkillTemplate] = {
    t.name: t
    for t in [
        CODING_FUNCTION_GENERATOR,
        CODING_REFACTOR,
        CODING_API_CLIENT,
        DEBUGGING_ROOT_CAUSE,
        DEBUGGING_LOG_ANALYZER,
        TESTING_UNIT_TEST,
        TESTING_INTEGRATION_TEST,
        TESTING_MOCK_DESIGNER,
        SECURITY_VULNERABILITY_SCAN,
        SECURITY_AUDIT_REVIEW,
        DEVOPS_CI_PIPELINE,
        DEVOPS_INFRASTRUCTURE,
        DATA_PIPELINE,
        DATA_ANALYSIS,
        DATA_SCHEMA_DESIGN,
        DESIGN_COMPONENT,
        DESIGN_SYSTEM,
        MANAGEMENT_TASK_BREAKDOWN,
        MANAGEMENT_PROJECT_PLAN,
        RESEARCH_LITERATURE_REVIEW,
        RESEARCH_EXPERIMENT_DESIGN,
    ]
}

__all__ = ["TEMPLATE_REGISTRY"]
