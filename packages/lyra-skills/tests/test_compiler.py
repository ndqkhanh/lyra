"""Tests for lyra-skills compiler."""
from lyra_skills.compiler import SkillCompiler, SkillModule


class TestSkillCompiler:
    def test_register_and_compile(self):
        c = SkillCompiler()
        m = SkillModule("code_review", "Review code for bugs and style issues")
        c.register(m)
        results = c.compile_all()
        assert len(results) == 1

    def test_compile_signature(self):
        c = SkillCompiler()
        sp = c.compile_signature("code → issues, suggestions, score")
        assert "issues" in sp.output_schema
        assert "code" in sp.input_schema

    def test_skill_module_forward(self):
        m = SkillModule("test", "Test skill")
        sp = m.compile({"input": "str"}, {"output": "str"})
        assert sp is not None
        assert sp.optimized is False
