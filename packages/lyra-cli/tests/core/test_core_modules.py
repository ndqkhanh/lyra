"""Tests for core modules: orchestrator, dispatcher, validator, loader, executor."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from lyra_cli.core.agent_metadata import AgentMetadata
from lyra_cli.core.agent_orchestrator import AgentOrchestrator, AgentResult
from lyra_cli.core.agent_registry import AgentRegistry
from lyra_cli.core.command_dispatcher import CommandDispatcher, CommandResult
from lyra_cli.core.command_metadata import CommandMetadata
from lyra_cli.core.command_registry import CommandRegistry
from lyra_cli.core.hook_executor import HookExecutor, HookResult
from lyra_cli.core.hook_metadata import HookMetadata, HookType
from lyra_cli.core.hook_registry import HookRegistry
from lyra_cli.core.rule_metadata import RuleCategory, RuleMetadata, RuleSeverity
from lyra_cli.core.rule_registry import RuleRegistry
from lyra_cli.core.rule_validator import RuleValidator, ValidationResult
from lyra_cli.core.skill_loader import SkillContent, SkillLoader
from lyra_cli.core.skill_metadata import SkillMetadata


# ── AgentOrchestrator Tests ──


class TestAgentOrchestrator:
    @pytest.fixture
    def registry(self):
        reg = AgentRegistry()
        reg._agents = {
            "explore": AgentMetadata(
                name="explore", description="Search and find files",
                tools=["grep", "glob"], model="haiku",
            ),
            "executor": AgentMetadata(
                name="executor", description="Implement and build code",
                tools=["edit", "write"], model="sonnet",
            ),
            "code-reviewer": AgentMetadata(
                name="code-reviewer", description="Review code quality",
                tools=["read"], model="sonnet",
            ),
        }
        return reg

    @pytest.fixture
    def orch(self, registry):
        return AgentOrchestrator(registry)

    def test_delegate_known_agent(self, orch):
        result = orch.delegate("explore", "find all Python files")
        assert result.success
        assert result.agent_name == "explore"

    def test_delegate_unknown_agent(self, orch):
        result = orch.delegate("nonexistent", "do something")
        assert not result.success
        assert "not found" in (result.error or "")

    def test_auto_delegate_search_task(self, orch):
        result = orch.auto_delegate("search for API endpoints in the codebase")
        assert result.success
        assert result.agent_name == "explore"

    def test_auto_delegate_implement_task(self, orch):
        result = orch.auto_delegate("implement a new authentication system")
        assert result.success
        assert result.agent_name == "executor"

    def test_auto_delegate_review_task(self, orch):
        result = orch.auto_delegate("review the code for security issues and check quality")
        assert result.success
        assert result.agent_name == "code-reviewer"

    def test_auto_delegate_empty_registry(self):
        reg = AgentRegistry()
        orch = AgentOrchestrator(reg)
        result = orch.auto_delegate("do something")
        assert not result.success
        assert "No agents" in (result.error or "")

    def test_auto_delegate_no_match(self, orch):
        result = orch.auto_delegate("xyzzy zyxxy")
        assert not result.success
        assert "No suitable agent" in (result.error or "")

    def test_custom_executor(self, registry):
        orch = AgentOrchestrator(registry)

        def fake_executor(name: str, task: str, ctx: dict | None) -> AgentResult:
            return AgentResult(success=True, output=f"Exec: {task}", agent_name=name)

        orch.set_executor(fake_executor)
        result = orch.delegate("explore", "test task")
        assert result.success
        assert result.output == "Exec: test task"

    def test_immutability(self):
        r = AgentResult(success=True, output="ok", agent_name="a")
        with pytest.raises(Exception):
            r.success = False


# ── CommandDispatcher Tests ──


class TestCommandDispatcher:
    @pytest.fixture
    def registry(self):
        reg = CommandRegistry()
        reg._commands = {
            "lint": CommandMetadata(
                name="lint", description="Run linter", agent="code-reviewer",
            ),
            "test": CommandMetadata(
                name="test", description="Run tests", skill="tdd-workflow",
            ),
        }
        return reg

    @pytest.fixture
    def dispatcher(self, registry):
        return CommandDispatcher(registry)

    def test_dispatch_known_command(self, dispatcher):
        result = dispatcher.dispatch("lint")
        assert result.success
        assert result.command_name == "lint"

    def test_dispatch_unknown_command(self, dispatcher):
        result = dispatcher.dispatch("nonexistent")
        assert not result.success
        assert "not found" in (result.error or "")

    def test_dispatch_with_agent_handler(self, dispatcher):
        def agent_handler(agent_name: str, cmd_name: str, args: dict | None) -> str:
            return f"Agent {agent_name} handled {cmd_name}"

        dispatcher.set_agent_handler(agent_handler)
        result = dispatcher.dispatch("lint")
        assert result.success
        assert "Agent code-reviewer" in result.output

    def test_dispatch_with_skill_handler(self, dispatcher):
        def skill_handler(skill_name: str, cmd_name: str, args: dict | None) -> str:
            return f"Skill {skill_name} handled {cmd_name}"

        dispatcher.set_skill_handler(skill_handler)
        result = dispatcher.dispatch("test")
        assert result.success
        assert "Skill tdd-workflow" in result.output

    def test_dispatch_no_handler(self, dispatcher):
        result = dispatcher.dispatch("lint")
        assert result.success

    def test_immutability(self):
        r = CommandResult(success=True, output="ok")
        with pytest.raises(Exception):
            r.success = False


# ── RuleValidator Tests ──


class TestRuleValidator:
    @pytest.fixture
    def registry(self):
        reg = RuleRegistry()
        reg._rules = {
            "no-console-log": RuleMetadata(
                name="no-console-log", description="Do not use console.log",
                category=RuleCategory.CODING_STANDARDS, severity=RuleSeverity.MEDIUM,
                enabled=True,
            ),
            "no-hardcoded-secrets": RuleMetadata(
                name="no-hardcoded-secrets", description="No hardcoded secrets",
                category=RuleCategory.SECURITY, severity=RuleSeverity.CRITICAL,
                enabled=True,
            ),
            "disabled-rule": RuleMetadata(
                name="disabled-rule", description="Should not run",
                category=RuleCategory.TESTING, severity=RuleSeverity.LOW,
                enabled=False,
            ),
        }
        return reg

    @pytest.fixture
    def validator(self, registry):
        return RuleValidator(registry)

    def test_validate_no_context(self, validator):
        result = validator.validate()
        assert result.passed
        assert result.rules_checked == 2

    def test_validate_with_content_finds_console_log(self, validator):
        result = validator.validate({"content": 'console.log("debug")', "file_path": "test.js"})
        assert not result.passed
        assert any(v.rule_name == "no-console-log" for v in result.violations)

    def test_validate_with_clean_content(self, validator):
        result = validator.validate({"content": 'print("hello")', "file_path": "test.py"})
        assert result.passed

    def test_validate_finds_hardcoded_secret(self, validator):
        result = validator.validate({"content": 'password = "secret123"', "file_path": "config.py"})
        assert not result.passed
        assert any(v.rule_name == "no-hardcoded-secrets" for v in result.violations)

    def test_validate_file_nonexistent(self, validator):
        violations = validator.validate_file("/nonexistent/path/file.py")
        assert len(violations) == 1
        assert violations[0].rule_name == "file-exists"

    def test_validate_file_with_temp(self, validator):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write('console.log("test");')
            f.flush()
            violations = validator.validate_file(f.name)
        Path(f.name).unlink()
        assert len(violations) >= 1
        assert any(v.rule_name == "no-console-log" for v in violations)

    def test_validate_category(self, validator):
        result = validator.validate_category(RuleCategory.SECURITY)
        assert result.rules_checked == 1

    def test_disabled_rules_not_counted(self, validator):
        result = validator.validate()
        assert result.rules_checked == 2

    def test_immutability(self):
        v = ValidationResult(passed=True, violations=(), rules_checked=0)
        with pytest.raises(Exception):
            v.passed = False


# ── SkillLoader Tests ──


class TestSkillLoader:
    @pytest.fixture
    def loader(self):
        return SkillLoader()

    def test_load_python_skill_with_codemap(self, loader):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""def hello():
    return "world"

class Greeter:
    def greet(self):
        return hello()
""")
            f.flush()
            skill = SkillMetadata(
                name="greeter", description="A greeter skill", origin="test",
                tags=["test"], file_path=f.name,
            )

        result = loader.load_with_codemap(skill)
        Path(f.name).unlink()

        assert result.skill_name == "greeter"
        assert result.language == "python"
        assert "hello" in result.functions
        assert "Greeter" in result.classes

    def test_load_shell_skill_with_codemap(self, loader):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("""#!/bin/bash
function build() {
    echo "building..."
}

function deploy() {
    echo "deploying..."
}
""")
            f.flush()
            skill = SkillMetadata(
                name="deployer", description="Deploy script", origin="test",
                tags=["test"], file_path=f.name,
            )

        result = loader.load_with_codemap(skill)
        Path(f.name).unlink()

        assert result.skill_name == "deployer"
        assert result.language == "shell"

    def test_load_markdown_skill(self, loader):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# My Skill
Description here.

```python
def example():
    pass
```
""")
            f.flush()
            skill = SkillMetadata(
                name="doc-skill", description="A doc", origin="test",
                tags=["test"], file_path=f.name,
            )

        result = loader.load_with_codemap(skill)
        Path(f.name).unlink()

        assert result.skill_name == "doc-skill"
        assert result.language == "python"

    def test_generate_codemap_from_dir(self, loader):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "my_skill"
            skill_dir.mkdir()
            (skill_dir / "__init__.py").write_text("")
            (skill_dir / "main.py").write_text("""
import os
from pathlib import Path

def run():
    pass

class Runner:
    pass
""")
            result = loader.generate_codemap("my_skill", skill_dir)

        assert result is not None
        assert result.skill_name == "my_skill"
        assert "run" in result.functions
        assert "Runner" in result.classes
        assert "os" in result.dependencies

    def test_generate_codemap_nonexistent_dir(self, loader):
        result = loader.generate_codemap("ghost", Path("/nonexistent"))
        assert result is None

    def test_generate_codemap_empty_dir(self, loader):
        with tempfile.TemporaryDirectory() as tmp:
            result = loader.generate_codemap("empty", Path(tmp))
        assert result is None

    def test_load_nonexistent_file(self, loader):
        skill = SkillMetadata(
            name="ghost", description="Ghost", origin="test",
            tags=["test"], file_path="/nonexistent/file.py",
        )
        result = loader.load_skill_content(skill)
        assert result == ""

    def test_load_no_file_path(self, loader):
        skill = SkillMetadata(
            name="inline", description="Inline skill", origin="test",
            tags=["test"],
        )
        result = loader.load_skill_content(skill)
        assert result == ""

    def test_skill_content_immutability(self):
        sc = SkillContent(skill_name="test", body="body")
        with pytest.raises(Exception):
            sc.body = "other"


# ── HookExecutor Tests ──


class TestHookExecutor:
    @pytest.fixture
    def registry(self):
        reg = HookRegistry()
        reg._hooks = {
            "formatter": HookMetadata(
                name="formatter", description="Format code",
                hook_type=HookType.POST_TOOL_USE, script="true",
                enabled=True,
            ),
            "failing-hook": HookMetadata(
                name="failing-hook", description="Always fails",
                hook_type=HookType.PRE_TOOL_USE, script="false",
                enabled=True,
            ),
            "disabled-hook": HookMetadata(
                name="disabled-hook", description="Disabled",
                hook_type=HookType.POST_TOOL_USE, script="true",
                enabled=False,
            ),
        }
        return reg

    @pytest.fixture
    def executor(self, registry):
        return HookExecutor(registry)

    def test_execute_successful_hook(self, executor):
        results = executor.execute_hooks(HookType.POST_TOOL_USE)
        assert len(results) == 1
        assert results[0].success
        assert results[0].hook_name == "formatter"

    def test_execute_failing_hook(self, executor):
        results = executor.execute_hooks(HookType.PRE_TOOL_USE)
        assert len(results) == 1
        assert not results[0].success

    def test_disabled_hooks_not_executed(self, executor):
        results = executor.execute_hooks(HookType.POST_TOOL_USE)
        hook_names = {r.hook_name for r in results}
        assert "disabled-hook" not in hook_names

    def test_empty_hooks_for_type(self, executor):
        results = executor.execute_hooks(HookType.SESSION_START)
        assert len(results) == 0

    def test_execute_with_context(self, executor):
        results = executor.execute_hooks(
            HookType.POST_TOOL_USE,
            context={"file": "test.py", "tool": "write"},
        )
        assert len(results) == 1
        assert results[0].success

    def test_result_has_duration(self, executor):
        results = executor.execute_hooks(HookType.POST_TOOL_USE)
        assert results[0].duration_ms >= 0

    def test_immutability(self):
        r = HookResult(success=True, output="ok", hook_name="h")
        with pytest.raises(Exception):
            r.success = False
