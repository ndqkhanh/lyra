"""Tests for lyra-ux-framework."""
from lyra_ux_framework import UXFramework

class TestUXFramework:
    def test_suggest_mode(self):
        u = UXFramework()
        mode = u.suggest_mode("code review", user_expertise=0.9)
        assert mode == "command"

    def test_register_pattern(self):
        u = UXFramework()
        u.register_pattern("auto_complete", "Suggest completions", "typing")
        assert u.stats["patterns"] == 1
