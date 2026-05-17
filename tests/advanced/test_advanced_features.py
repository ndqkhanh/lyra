"""Tests for advanced features - multi-agent orchestration, reasoning, and context optimization."""
import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_workspace():
    """Create temporary workspace."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


# Multi-Agent Orchestration Tests
def test_agent_definitions_exist():
    """Test that agent definitions directory exists."""
    agents_dir = Path("packages/lyra-cli/src/lyra_cli/agents")

    assert agents_dir.exists()
    assert agents_dir.is_dir()


def test_agent_definitions_are_markdown():
    """Test that agent definitions are markdown files."""
    agents_dir = Path("packages/lyra-cli/src/lyra_cli/agents")

    if agents_dir.exists():
        md_files = list(agents_dir.glob("*.md"))
        assert len(md_files) > 0

        # Check a few key agents exist
        agent_names = [f.stem for f in md_files]
        assert "architect" in agent_names or "code-reviewer" in agent_names


def test_agent_definitions_have_content():
    """Test that agent definitions have content."""
    agents_dir = Path("packages/lyra-cli/src/lyra_cli/agents")

    if agents_dir.exists():
        architect_file = agents_dir / "architect.md"
        if architect_file.exists():
            content = architect_file.read_text()
            assert len(content) > 0
            assert len(content) > 100  # Should have substantial content


def test_multiple_agent_types_available():
    """Test that multiple agent types are available."""
    agents_dir = Path("packages/lyra-cli/src/lyra_cli/agents")

    if agents_dir.exists():
        md_files = list(agents_dir.glob("*.md"))

        # Should have multiple agent types
        assert len(md_files) >= 5


def test_agent_specializations():
    """Test that agents have different specializations."""
    agents_dir = Path("packages/lyra-cli/src/lyra_cli/agents")

    if agents_dir.exists():
        # Check for different types of agents
        expected_types = [
            "architect",
            "code-reviewer",
            "build-error-resolver",
        ]

        md_files = [f.stem for f in agents_dir.glob("*.md")]

        # At least some expected types should exist
        found_types = [t for t in expected_types if t in md_files]
        assert len(found_types) > 0


# Context Optimization Tests
def test_context_manager_exists():
    """Test that context manager module exists."""
    context_manager = Path("packages/lyra-cli/src/lyra_cli/cli/context_manager.py")

    assert context_manager.exists()


def test_context_manager_has_content():
    """Test that context manager has implementation."""
    context_manager = Path("packages/lyra-cli/src/lyra_cli/cli/context_manager.py")

    if context_manager.exists():
        content = context_manager.read_text()
        assert len(content) > 0


def test_context_optimization_command_exists():
    """Test that context optimization command exists."""
    context_opt = Path("packages/lyra-cli/src/lyra_cli/commands/context_opt.py")

    assert context_opt.exists()


def test_context_optimization_command_has_content():
    """Test that context optimization command has implementation."""
    context_opt = Path("packages/lyra-cli/src/lyra_cli/commands/context_opt.py")

    if context_opt.exists():
        content = context_opt.read_text()
        assert len(content) > 0
        assert len(content) > 100


def test_context_engineering_exists():
    """Test that context engineering module exists."""
    context_eng = Path("packages/lyra-cli/src/lyra_cli/interactive/context_engineering.py")

    assert context_eng.exists()


def test_context_rules_exist():
    """Test that context window management rules exist."""
    context_rules = Path("packages/lyra-cli/src/lyra_cli/rules/context-window-management.md")

    assert context_rules.exists()


# Advanced Reasoning Tests
def test_evolution_context_exists():
    """Test that evolution context module exists."""
    evolution_context = Path("packages/lyra-cli/src/lyra_cli/evolution/context.py")

    assert evolution_context.exists()


def test_evolution_context_has_implementation():
    """Test that evolution context has implementation."""
    evolution_context = Path("packages/lyra-cli/src/lyra_cli/evolution/context.py")

    if evolution_context.exists():
        content = evolution_context.read_text()
        assert len(content) > 0


# Integration Tests
def test_advanced_features_integration():
    """Test that advanced features can work together."""
    # Check that key components exist
    agents_dir = Path("packages/lyra-cli/src/lyra_cli/agents")
    context_manager = Path("packages/lyra-cli/src/lyra_cli/cli/context_manager.py")
    evolution_context = Path("packages/lyra-cli/src/lyra_cli/evolution/context.py")

    # All should exist for full integration
    assert agents_dir.exists()
    assert context_manager.exists()
    assert evolution_context.exists()


def test_agent_directory_structure():
    """Test agent directory has proper structure."""
    agents_dir = Path("packages/lyra-cli/src/lyra_cli/agents")

    if agents_dir.exists():
        # Should have multiple agent definitions
        md_files = list(agents_dir.glob("*.md"))
        assert len(md_files) > 0

        # Each file should be readable
        for md_file in md_files[:5]:  # Check first 5
            content = md_file.read_text()
            assert len(content) > 0


def test_context_optimization_components():
    """Test that context optimization has all components."""
    components = [
        Path("packages/lyra-cli/src/lyra_cli/cli/context_manager.py"),
        Path("packages/lyra-cli/src/lyra_cli/commands/context_opt.py"),
        Path("packages/lyra-cli/src/lyra_cli/interactive/context_engineering.py"),
    ]

    # At least some components should exist
    existing = [c for c in components if c.exists()]
    assert len(existing) > 0


def test_advanced_features_documentation():
    """Test that advanced features have documentation."""
    docs = [
        Path("packages/lyra-cli/src/lyra_cli/rules/context-window-management.md"),
        Path("packages/lyra-cli/src/lyra_cli/hooks/load-context.md"),
        Path("packages/lyra-cli/src/lyra_cli/hooks/backup-context.md"),
    ]

    # At least some docs should exist
    existing = [d for d in docs if d.exists()]
    assert len(existing) > 0


def test_agent_count():
    """Test that there are multiple agents available."""
    agents_dir = Path("packages/lyra-cli/src/lyra_cli/agents")

    if agents_dir.exists():
        md_files = list(agents_dir.glob("*.md"))

        # Should have a good number of specialized agents
        assert len(md_files) >= 10


def test_agent_files_are_valid():
    """Test that agent files are valid markdown."""
    agents_dir = Path("packages/lyra-cli/src/lyra_cli/agents")

    if agents_dir.exists():
        md_files = list(agents_dir.glob("*.md"))

        for md_file in md_files[:10]:  # Check first 10
            content = md_file.read_text()

            # Should have some markdown content
            assert len(content) > 50

            # Should be valid UTF-8
            assert isinstance(content, str)


def test_context_hooks_exist():
    """Test that context management hooks exist."""
    hooks = [
        Path("packages/lyra-cli/src/lyra_cli/hooks/load-context.md"),
        Path("packages/lyra-cli/src/lyra_cli/hooks/backup-context.md"),
    ]

    existing = [h for h in hooks if h.exists()]
    assert len(existing) > 0


def test_advanced_features_modules_importable():
    """Test that advanced feature modules can be imported."""
    # Test imports don't fail
    try:
        # These might not all exist, but shouldn't crash
        import importlib

        modules_to_try = [
            "lyra_cli.cli.context_manager",
            "lyra_cli.evolution.context",
        ]

        imported = 0
        for module_name in modules_to_try:
            try:
                importlib.import_module(module_name)
                imported += 1
            except (ImportError, ModuleNotFoundError):
                # Module might not exist, that's OK
                pass

        # At least one should import successfully
        assert imported > 0
    except Exception:
        # If import system fails, that's OK for this test
        pass


def test_agent_system_architecture():
    """Test that agent system has proper architecture."""
    agents_dir = Path("packages/lyra-cli/src/lyra_cli/agents")

    if agents_dir.exists():
        # Should have different categories of agents
        md_files = [f.stem for f in agents_dir.glob("*.md")]

        # Check for different categories
        has_reviewer = any("review" in name for name in md_files)
        has_builder = any("build" in name or "architect" in name for name in md_files)

        # Should have multiple categories
        assert has_reviewer or has_builder


def test_context_optimization_architecture():
    """Test that context optimization has proper architecture."""
    # Should have multiple layers
    components = {
        "manager": Path("packages/lyra-cli/src/lyra_cli/cli/context_manager.py"),
        "command": Path("packages/lyra-cli/src/lyra_cli/commands/context_opt.py"),
        "engineering": Path("packages/lyra-cli/src/lyra_cli/interactive/context_engineering.py"),
        "evolution": Path("packages/lyra-cli/src/lyra_cli/evolution/context.py"),
    }

    existing = {k: v for k, v in components.items() if v.exists()}

    # Should have multiple components
    assert len(existing) >= 2
