"""Tests for Context Profiler package."""

import pytest
from lyra_context_profiler import ContextProfiler, ProfileMatcher, ContextProfile


class TestContextProfiler:
    def test_analyze_code_task_sync(self):
        p = ContextProfiler()
        import asyncio
        profile = asyncio.run(p.analyze("Write a Python function to sort a list", ["git", "python"], {"language": "python"}))
        assert profile.task_type == "code_generation"

    def test_analyze_research_task_sync(self):
        p = ContextProfiler()
        import asyncio
        profile = asyncio.run(p.analyze("Research the latest LLM papers", ["search", "web"], {}))
        assert profile.task_type == "research"

    def test_current_profile(self):
        p = ContextProfiler()
        assert p.current is None


class TestProfileMatcher:
    def test_register_and_match(self):
        m = ProfileMatcher()
        m.register_pattern("code", {"complexity": 0.5})
        profile = ContextProfile(task_type="code", complexity=0.6, tools_available=[], user_preferences={}, environment_tags=[])
        result = m.match(profile)
        assert isinstance(result, str)
