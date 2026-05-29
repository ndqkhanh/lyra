"""
Tests for ECC agent importer.
"""

import tempfile
from pathlib import Path

import pytest

from src.agents.ecc_importer import (
    ECCAgent,
    ECCAgentDefinition,
    ECCAgentImporter,
    ECCAgentParser,
    ImportResult,
    create_sample_ecc_agents,
)
from src.agents.unified_registry import UnifiedAgentRegistry
from src.core.task import Task, TaskType


class TestECCAgentDefinition:
    """Tests for ECCAgentDefinition class."""

    def test_definition_creation(self):
        """Test creating an agent definition."""
        definition = ECCAgentDefinition(
            name="test-agent",
            description="Test agent",
            model="sonnet",
            capabilities=["coding", "testing"],
            task_types=["code_generation"],
            languages=["python"],
            frameworks=["pytest"],
            tools=["read", "write"],
            instructions="Test instructions",
            priority=5,
        )

        assert definition.name == "test-agent"
        assert definition.model == "sonnet"
        assert len(definition.capabilities) == 2
        assert definition.priority == 5


class TestECCAgent:
    """Tests for ECCAgent class."""

    def test_agent_creation(self):
        """Test creating an ECC agent."""
        definition = ECCAgentDefinition(
            name="test-agent",
            description="Test agent",
            model="sonnet",
            capabilities=["coding"],
            task_types=["code_generation"],
            languages=["python"],
            frameworks=[],
            tools=["read"],
            instructions="Test instructions",
        )

        agent = ECCAgent("test-agent", definition)
        assert agent.agent_id == "test-agent"
        assert agent.description == "Test agent"
        assert agent.model == "sonnet"

    def test_can_handle_exact_match(self):
        """Test can_handle with exact task type match."""
        definition = ECCAgentDefinition(
            name="test-agent",
            description="Test agent",
            model="sonnet",
            capabilities=["coding"],
            task_types=["code_generation"],
            languages=["python"],
            frameworks=[],
            tools=["read"],
            instructions="Test instructions",
        )

        agent = ECCAgent("test-agent", definition)
        task = Task(
            task_id="test-task",
            type=TaskType.CODE_GENERATION,
            description="Generate code",
        )

        confidence = agent.can_handle(task)
        assert confidence == 0.9

    def test_can_handle_capability_match(self):
        """Test can_handle with capability keyword match."""
        definition = ECCAgentDefinition(
            name="test-agent",
            description="Test agent",
            model="sonnet",
            capabilities=["coding", "refactoring"],
            task_types=["implementation"],
            languages=["python"],
            frameworks=[],
            tools=["read"],
            instructions="Test instructions",
        )

        agent = ECCAgent("test-agent", definition)
        task = Task(
            task_id="test-task",
            type=TaskType.CODE_GENERATION,
            description="Need help with refactoring this code",
        )

        confidence = agent.can_handle(task)
        assert confidence == 0.7

    def test_can_handle_no_match(self):
        """Test can_handle with no match."""
        definition = ECCAgentDefinition(
            name="test-agent",
            description="Test agent",
            model="sonnet",
            capabilities=["coding"],
            task_types=["implementation"],
            languages=["python"],
            frameworks=[],
            tools=["read"],
            instructions="Test instructions",
        )

        agent = ECCAgent("test-agent", definition)
        task = Task(
            task_id="test-task",
            type=TaskType.SECURITY_SCAN,
            description="Scan for security issues",
        )

        confidence = agent.can_handle(task)
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_execute(self):
        """Test executing a task."""
        definition = ECCAgentDefinition(
            name="test-agent",
            description="Test agent",
            model="sonnet",
            capabilities=["coding"],
            task_types=["code_generation"],
            languages=["python"],
            frameworks=[],
            tools=["read"],
            instructions="Test instructions",
        )

        agent = ECCAgent("test-agent", definition)
        task = Task(
            task_id="test-task",
            type=TaskType.CODE_GENERATION,
            description="Generate code",
        )

        result = await agent.execute(task)
        assert result.success
        assert result.task_id == "test-task"
        assert result.agent_id == "test-agent"
        assert "message" in result.data


class TestECCAgentParser:
    """Tests for ECCAgentParser class."""

    def test_parse_file(self):
        """Test parsing an agent definition file."""
        content = """---
name: test-agent
description: Test agent
model: sonnet
capabilities: [coding, testing]
task_types: [code_generation]
languages: [python]
frameworks: [pytest]
tools: [read, write]
priority: 5
---

# Test Agent

This is a test agent for code generation.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test-agent.md"
            path.write_text(content)

            parser = ECCAgentParser()
            definition = parser.parse_file(path)

            assert definition is not None
            assert definition.name == "test-agent"
            assert definition.model == "sonnet"
            assert len(definition.capabilities) == 2
            assert definition.priority == 5
            assert "test agent" in definition.instructions.lower()

    def test_parse_file_invalid(self):
        """Test parsing invalid file."""
        content = """---
invalid yaml: [
---

Content
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid.md"
            path.write_text(content)

            parser = ECCAgentParser()
            definition = parser.parse_file(path)

            assert definition is None

    def test_parse_directory(self):
        """Test parsing directory of agent definitions."""
        agent1 = """---
name: agent1
description: Agent 1
model: sonnet
capabilities: [coding]
task_types: [code_generation]
languages: [python]
frameworks: []
tools: [read]
---

Agent 1 instructions
"""

        agent2 = """---
name: agent2
description: Agent 2
model: opus
capabilities: [planning]
task_types: [planning]
languages: []
frameworks: []
tools: [read]
---

Agent 2 instructions
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "agent1.md").write_text(agent1)
            (tmpdir / "agent2.md").write_text(agent2)

            parser = ECCAgentParser()
            definitions = parser.parse_directory(tmpdir)

            assert len(definitions) == 2
            assert "agent1" in definitions
            assert "agent2" in definitions


class TestECCAgentImporter:
    """Tests for ECCAgentImporter class."""

    def test_import_agent(self):
        """Test importing a single agent."""
        registry = UnifiedAgentRegistry()
        importer = ECCAgentImporter(registry)

        definition = ECCAgentDefinition(
            name="test-agent",
            description="Test agent",
            model="sonnet",
            capabilities=["coding"],
            task_types=["code_generation"],
            languages=["python"],
            frameworks=["pytest"],
            tools=["read"],
            instructions="Test instructions",
            priority=5,
        )

        qualified_name = importer.import_agent(definition)
        assert qualified_name == "ecc:test-agent"
        assert len(registry.agents) == 1

        # Verify agent is registered correctly
        agent = registry.get(qualified_name)
        assert agent is not None
        assert agent.agent_id == "test-agent"

    def test_import_directory(self):
        """Test importing directory of agents."""
        agent1 = """---
name: agent1
description: Agent 1
model: sonnet
capabilities: [coding]
task_types: [code_generation]
languages: [python]
frameworks: []
tools: [read]
---

Agent 1 instructions
"""

        agent2 = """---
name: agent2
description: Agent 2
model: opus
capabilities: [planning]
task_types: [planning]
languages: []
frameworks: []
tools: [read]
---

Agent 2 instructions
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "agent1.md").write_text(agent1)
            (tmpdir / "agent2.md").write_text(agent2)

            registry = UnifiedAgentRegistry()
            importer = ECCAgentImporter(registry)

            result = importer.import_directory(tmpdir)

            assert result.total_files == 2
            assert result.parsed_successfully == 2
            assert result.registered_successfully == 2
            assert result.success_rate == 1.0
            assert len(result.failed) == 0

    def test_import_with_failures(self):
        """Test importing with some failures."""
        valid_agent = """---
name: valid-agent
description: Valid agent
model: sonnet
capabilities: [coding]
task_types: [code_generation]
languages: [python]
frameworks: []
tools: [read]
---

Valid instructions
"""

        invalid_agent = """---
invalid yaml: [
---

Invalid content
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "valid.md").write_text(valid_agent)
            (tmpdir / "invalid.md").write_text(invalid_agent)

            registry = UnifiedAgentRegistry()
            importer = ECCAgentImporter(registry)

            result = importer.import_directory(tmpdir)

            assert result.total_files == 2
            assert result.registered_successfully == 1
            assert len(result.failed) == 1
            assert result.success_rate == 0.5


class TestImportResult:
    """Tests for ImportResult class."""

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        result = ImportResult(
            total_files=10,
            parsed_successfully=9,
            registered_successfully=8,
            failed=["agent1", "agent2"],
            agents={},
        )

        assert result.success_rate == 0.8

    def test_success_rate_no_files(self):
        """Test success rate with no files."""
        result = ImportResult(
            total_files=0,
            parsed_successfully=0,
            registered_successfully=0,
            failed=[],
            agents={},
        )

        assert result.success_rate == 0.0


class TestSampleAgents:
    """Tests for sample agent creation."""

    def test_create_sample_agents(self):
        """Test creating sample agents."""
        agents = create_sample_ecc_agents()

        assert len(agents) == 10
        assert "planner" in agents
        assert "architect" in agents
        assert "executor" in agents
        assert "code-reviewer" in agents

        # Verify planner agent
        planner = agents["planner"]
        assert planner.name == "planner"
        assert planner.model == "opus"
        assert "planning" in planner.capabilities

    def test_sample_agents_can_be_imported(self):
        """Test that sample agents can be imported."""
        registry = UnifiedAgentRegistry()
        importer = ECCAgentImporter(registry)

        agents = create_sample_ecc_agents()
        for definition in agents.values():
            qualified_name = importer.import_agent(definition)
            assert qualified_name is not None
            assert qualified_name.startswith("ecc:")

        assert len(registry.agents) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
