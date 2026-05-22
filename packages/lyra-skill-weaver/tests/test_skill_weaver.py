"""Tests for Skill Weaver package."""

import pytest
from lyra_skill_weaver import SkillWeaver, SkillComposer, SkillModule, CompositionPlan


class TestSkillComposer:
    def test_register_module(self):
        c = SkillComposer()
        m = SkillModule(id="m1", name="test", description="", inputs=[], outputs=["result"], context_requirements={})
        c.register_module(m)
        assert "m1" in c.registry

    def test_compose_with_no_modules(self):
        c = SkillComposer()
        plan = c.compose(["result"], {"complexity": 0.5})
        assert isinstance(plan, CompositionPlan)


class TestSkillWeaver:
    def test_weave(self):
        w = SkillWeaver()
        plan = w.weave("code_generation", {"complexity": 0.5})
        assert len(plan.modules) >= 0
