"""Tests for Phase 7 agents."""
import pytest
from pathlib import Path
from lyra_cli.core.agent_registry import AgentRegistry


# List of all 50 Phase 7 agents
PHASE_7_AGENTS = [
    # Language-Specific (20)
    "typescript-reviewer", "go-reviewer", "rust-reviewer", "kotlin-reviewer",
    "cpp-reviewer", "java-reviewer", "swift-reviewer", "php-reviewer",
    "ruby-reviewer", "elixir-reviewer", "scala-reviewer", "clojure-reviewer",
    "haskell-reviewer", "ocaml-reviewer", "fsharp-reviewer", "dart-reviewer",
    "lua-reviewer", "r-reviewer", "julia-reviewer", "zig-reviewer",
    # Domain-Specific (15)
    "database-reviewer", "frontend-patterns", "backend-patterns", "api-design",
    "devops-specialist", "cloud-infrastructure", "mobile-development",
    "ml-ai-specialist", "data-engineering", "security-specialist",
    "performance-specialist", "accessibility-specialist", "i18n-specialist",
    "testing-specialist", "documentation-specialist",
    # Workflow (15)
    "e2e-runner", "integration-test-runner", "load-test-runner",
    "benchmark-runner", "migration-specialist", "deployment-specialist",
    "monitoring-specialist", "incident-response", "code-migration",
    "legacy-modernizer", "tech-debt-analyzer", "dependency-updater",
    "license-checker", "code-metrics", "architecture-auditor",
]


@pytest.fixture
def agents_dir():
    """Get the agents directory."""
    return Path(__file__).parent.parent.parent / "src" / "lyra_cli" / "agents"


def test_phase_7_agents_exist(agents_dir):
    """Test that all Phase 7 agent files exist."""
    for agent_name in PHASE_7_AGENTS:
        agent_file = agents_dir / f"{agent_name}.md"
        assert agent_file.exists(), f"Agent file {agent_name}.md not found"


def test_phase_7_agents_load(agents_dir):
    """Test that all Phase 7 agents can be loaded."""
    registry = AgentRegistry(agent_dirs=[agents_dir])
    agents = registry.load_agents()

    for agent_name in PHASE_7_AGENTS:
        assert agent_name in agents, f"Agent {agent_name} not loaded"


def test_phase_7_agents_metadata(agents_dir):
    """Test that all Phase 7 agents have valid metadata."""
    registry = AgentRegistry(agent_dirs=[agents_dir])
    agents = registry.load_agents()

    for agent_name in PHASE_7_AGENTS:
        agent = agents[agent_name]
        assert agent.name == agent_name
        assert agent.description
        assert agent.model in ["sonnet", "opus", "haiku"]
        assert agent.tools is not None
