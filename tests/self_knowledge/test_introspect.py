"""Tests for src/self_knowledge/introspect.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.self_knowledge.introspect import IntrospectionEngine, KnowledgeSource


class TestKnowledgeSource:
    """Tests for KnowledgeSource."""

    def test_default_content_empty(self):
        """KnowledgeSource defaults to empty content."""
        ks = KnowledgeSource(path="/a/b.py", source_type="skill", label="test")
        assert ks.content == ""


class TestIntrospectionEngine:
    """Tests for IntrospectionEngine."""

    def test_version_is_read(self):
        """Engine reads the version from the package."""
        engine = IntrospectionEngine()
        assert engine.version is not None
        assert isinstance(engine.version, str)

    def test_root_discovery(self):
        """Root is auto-discovered and contains src/__init__.py."""
        engine = IntrospectionEngine()
        init_path = engine.root / "src" / "__init__.py"
        assert init_path.exists(), f"Expected {init_path} to exist"

    def test_load_all_populates_sources(self):
        """load_all discovers docs, skills, configs, and modules."""
        engine = IntrospectionEngine()
        count = engine.load_all()
        # Should find several sources in a full Lyra repo
        assert count >= 4, f"Expected >=4 sources, got {count}"

    def test_list_sources_types(self):
        """list_sources returns correct types after load."""
        engine = IntrospectionEngine()
        engine.load_all()
        modules = engine.list_sources("module")
        docs = engine.list_sources("doc")
        configs = engine.list_sources("config")
        assert isinstance(modules, list)
        assert isinstance(docs, list)
        assert isinstance(configs, list)

    def test_ask_version(self):
        """ask returns version info for version questions."""
        engine = IntrospectionEngine()
        answer = engine.ask("What version is Lyra?")
        assert "version" in answer.lower()
        assert engine.version in answer

    def test_ask_skills(self):
        """ask returns skill info for skill questions."""
        engine = IntrospectionEngine()
        answer = engine.ask("What skills do I have?")
        assert "skill" in answer.lower()
        assert "found" in answer.lower()

    def test_ask_modules(self):
        """ask returns module info for module questions."""
        engine = IntrospectionEngine()
        answer = engine.ask("What modules are available?")
        assert "module" in answer.lower()

    def test_get_source_count(self):
        """get_source_count returns non-negative integer."""
        engine = IntrospectionEngine()
        engine.load_all()
        count = engine.get_source_count("skill")
        assert isinstance(count, int)
        assert count >= 0
