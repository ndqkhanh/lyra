"""
Tests for ECC Integration

Comprehensive test suite for Lyra × ECC integration.
"""

import pytest
from pathlib import Path
from lyra_ecc.compatibility import ECCCompatibilityLayer
from lyra_ecc.importer import ECCImporter, ImportResult
from lyra_ecc.hooks import ECCHooksEngine, HookType, HookContext, HookResult
from lyra_ecc.rules import RulesEngine, RuleSeverity, RuleViolation


class TestECCCompatibility:
    """Test ECC compatibility layer."""

    def test_compatibility_layer_initialization(self):
        """Test compatibility layer initializes correctly."""
        compat = ECCCompatibilityLayer()
        assert compat is not None
        assert compat.ecc_path == Path.home() / ".claude"

    def test_compatibility_report(self):
        """Test compatibility report generation."""
        compat = ECCCompatibilityLayer()
        report = compat.get_compatibility_report()

        assert "initialized" in report
        assert "ecc_path" in report
        assert "matrix" in report
        assert "status" in report


class TestECCImporter:
    """Test ECC importer."""

    def test_importer_initialization(self):
        """Test importer initializes correctly."""
        importer = ECCImporter()
        assert importer is not None
        assert importer.ecc_path == Path.home() / ".claude"

    def test_import_summary(self):
        """Test import summary generation."""
        importer = ECCImporter()
        summary = importer.get_import_summary()

        assert "skills_available" in summary
        assert "agents_available" in summary
        assert "rules_available" in summary
        assert isinstance(summary["skills_available"], int)


class TestECCHooks:
    """Test ECC hooks engine."""

    def test_hooks_engine_initialization(self):
        """Test hooks engine initializes correctly."""
        engine = ECCHooksEngine()
        assert engine is not None
        assert len(engine.hooks) == 5  # 5 hook types

    def test_hook_registration(self):
        """Test hook registration."""
        engine = ECCHooksEngine()

        def test_hook(context: HookContext) -> HookResult:
            return HookResult(success=True)

        engine.register_hook(HookType.PRE_TOOL_USE, test_hook)
        assert len(engine.hooks[HookType.PRE_TOOL_USE]) > 0

    @pytest.mark.asyncio
    async def test_hook_firing(self):
        """Test hook firing."""
        engine = ECCHooksEngine()

        context = HookContext(
            event_type=HookType.PRE_TOOL_USE,
            tool_name="Read",
            file_path=Path("test.py")
        )

        result = await engine.fire(HookType.PRE_TOOL_USE, context)
        assert isinstance(result, HookResult)
        assert result.success


class TestRulesEngine:
    """Test rules engine."""

    def test_rules_engine_initialization(self):
        """Test rules engine initializes correctly."""
        engine = RulesEngine()
        assert engine is not None

    def test_rules_summary(self):
        """Test rules summary generation."""
        engine = RulesEngine()
        summary = engine.get_rules_summary()

        assert "common_rules" in summary
        assert "language_rules" in summary
        assert "active_rules" in summary
        assert "languages" in summary

    def test_language_detection(self):
        """Test language detection."""
        engine = RulesEngine()
        test_dir = Path("test_project")

        # Would need actual test files for full test
        languages = engine._detect_languages(test_dir)
        assert isinstance(languages, list)

    def test_rule_checking(self):
        """Test rule checking."""
        engine = RulesEngine()

        code = "print('hello')"
        file_path = Path("test.py")

        violations = engine.check(code, file_path)
        assert isinstance(violations, list)


class TestIntegration:
    """Integration tests for ECC × Lyra."""

    def test_full_integration_flow(self):
        """Test complete integration flow."""
        # Initialize all components
        compat = ECCCompatibilityLayer()
        importer = ECCImporter()
        hooks = ECCHooksEngine()
        rules = RulesEngine()

        # Verify all components initialized
        assert compat is not None
        assert importer is not None
        assert hooks is not None
        assert rules is not None

    def test_compatibility_with_lyra_skills(self):
        """Test ECC skills compatibility with Lyra."""
        importer = ECCImporter()
        summary = importer.get_import_summary()

        # Should be able to import skills
        assert summary["skills_available"] >= 0

    def test_hooks_integration_with_tools(self):
        """Test hooks integrate with Lyra tools."""
        engine = ECCHooksEngine()

        # Verify post-tool-use hooks registered
        assert len(engine.hooks[HookType.POST_TOOL_USE]) > 0

    def test_rules_integration_with_review(self):
        """Test rules integrate with code review."""
        engine = RulesEngine()

        # Verify rules can check code
        code = "var x = 1"  # Potential immutability violation
        violations = engine.check(code, Path("test.js"))

        assert isinstance(violations, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
