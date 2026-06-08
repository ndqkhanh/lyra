"""
Unit tests for the IntrospectionEngine (self-knowledge module).

Tests initialization, source scanning (docs, skills, config, modules),
the ask() method, list_sources(), get_source_count(), and load_all().
Uses temporary directories to avoid touching project files.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra.self_knowledge.introspect import (
    IntrospectionEngine,
    KnowledgeSource,
)


# ---------------------------------------------------------------------------
# KnowledgeSource
# ---------------------------------------------------------------------------


class TestKnowledgeSource:
    def test_init(self) -> None:
        src = KnowledgeSource(
            path="/path/to/file.md",
            source_type="doc",
            label="file.md",
            content="hello",
        )
        assert src.path == "/path/to/file.md"
        assert src.source_type == "doc"
        assert src.label == "file.md"
        assert src.content == "hello"

    def test_default_content_empty(self) -> None:
        src = KnowledgeSource(path="/x", source_type="doc", label="x")
        assert src.content == ""


# ---------------------------------------------------------------------------
# IntrospectionEngine - initialisation
# ---------------------------------------------------------------------------


class TestIntrospectionEngineInit:
    def test_with_explicit_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = IntrospectionEngine(root=tmpdir)
            assert str(engine.root) == tmpdir

    def test_auto_discover_root(self) -> None:
        """_discover_root falls back to CWD when src/__init__.py not found."""
        engine = IntrospectionEngine()
        # The auto-discovered root should exist
        assert engine.root is not None

    def test_version_unknown_when_no_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = IntrospectionEngine(root=tmpdir)
            assert engine.version == "unknown"

    def test_version_from_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir(parents=True)
            (src_dir / "__init__.py").write_text('__version__ = "2.0.0"')
            engine = IntrospectionEngine(root=tmpdir)
            assert engine.version == "2.0.0"

    def test_version_with_single_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir(parents=True)
            (src_dir / "__init__.py").write_text("__version__ = '1.5.0'")
            engine = IntrospectionEngine(root=tmpdir)
            assert engine.version == "1.5.0"

    def test_version_not_starting_with_version(self) -> None:
        """Lines not starting with __version__ are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir(parents=True)
            (src_dir / "__init__.py").write_text(
                '"""module doc"""\n__version__ = "3.0.0"\n'
            )
            engine = IntrospectionEngine(root=tmpdir)
            assert engine.version == "3.0.0"


# ---------------------------------------------------------------------------
# _safe_read
# ---------------------------------------------------------------------------


class TestSafeRead:
    def test_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("hello")
            engine = IntrospectionEngine(root=tmpdir)
            assert engine._safe_read(path) == "hello"

    def test_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.txt"
            engine = IntrospectionEngine(root=tmpdir)
            assert engine._safe_read(path) == ""

    def test_read_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("hello")
            engine = IntrospectionEngine(root=tmpdir)
            # Remove read permission to force an error
            path.chmod(0o000)
            try:
                assert engine._safe_read(path) == ""
            finally:
                path.chmod(0o644)  # restore permissions for cleanup


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------


def _make_project(tmpdir: str, has_docs: bool = True, has_skills: bool = True,
                  has_config: bool = True, has_modules: bool = True) -> Path:
    root = Path(tmpdir)
    src_dir = root / "src"
    src_dir.mkdir(parents=True)
    (src_dir / "__init__.py").write_text('__version__ = "1.0.0"')

    if has_docs:
        docs_dir = root / "docs"
        docs_dir.mkdir(parents=True)
        (docs_dir / "README.md").write_text("# Documentation")
        (docs_dir / "guide.txt").write_text("Guide content")

    if has_skills:
        skills_dir = src_dir / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "test_skill.py").write_text("def skill_func(): pass")
        (skills_dir / "another.py").write_text("pass")

    if has_config:
        (root / "pyproject.toml").write_text("[project]\nname = 'test'")
        (root / "setup.cfg").write_text("[metadata]\nname = test")

    if has_modules:
        module_dir = src_dir / "my_module"
        module_dir.mkdir(parents=True)
        (module_dir / "__init__.py").write_text("# my module")
        module_dir2 = src_dir / "another_module"
        module_dir2.mkdir(parents=True)
        (module_dir2 / "__init__.py").write_text("# another")

    return root


class TestIntrospectionEngineScanDocs:
    def test_scan_docs_with_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            engine._scan_docs()
            sources = [s for s in engine._sources if s.source_type == "doc"]
            labels = {s.label for s in sources}
            assert "README.md" in labels
            assert "guide.txt" in labels

    def test_scan_docs_no_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = IntrospectionEngine(root=tmpdir)
            engine._scan_docs()
            assert len(engine._sources) == 0

    def test_scan_docs_skips_non_text_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            docs_dir = root / "docs"
            docs_dir.mkdir(parents=True)
            (docs_dir / "image.png").write_bytes(b"PNG content")
            engine = IntrospectionEngine(root=root)
            engine._scan_docs()
            sources = [s for s in engine._sources if s.source_type == "doc"]
            assert len(sources) == 0


class TestIntrospectionEngineScanSkills:
    def test_scan_skills_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            engine._scan_skills()
            skills = [s for s in engine._sources if s.source_type == "skill"]
            labels = {s.label for s in skills}
            assert "test_skill" in labels
            assert "another" in labels

    def test_scan_skills_no_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = IntrospectionEngine(root=tmpdir)
            engine._scan_skills()
            assert len(engine._sources) == 0

    def test_scan_skills_skips_non_py_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            skills_dir = root / "src" / "skills"
            skills_dir.mkdir(parents=True)
            (skills_dir / "readme.txt").write_text("text")
            engine = IntrospectionEngine(root=root)
            engine._scan_skills()
            skills = [s for s in engine._sources if s.source_type == "skill"]
            assert len(skills) == 0


class TestIntrospectionEngineScanConfig:
    def test_scan_config_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            engine._scan_config()
            configs = [s for s in engine._sources if s.source_type == "config"]
            labels = {s.label for s in configs}
            assert "pyproject.toml" in labels
            assert "setup.cfg" in labels

    def test_scan_config_none_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = IntrospectionEngine(root=tmpdir)
            engine._scan_config()
            assert len([s for s in engine._sources if s.source_type == "config"]) == 0

    def test_scan_config_checks_all_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".lyra.yaml").write_text("key: value")
            engine = IntrospectionEngine(root=root)
            engine._scan_config()
            configs = [s for s in engine._sources if s.source_type == "config"]
            assert len(configs) == 1
            assert configs[0].label == ".lyra.yaml"


class TestIntrospectionEngineScanModules:
    def test_scan_modules_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            engine._scan_modules()
            modules = [s for s in engine._sources if s.source_type == "module"]
            labels = {s.label for s in modules}
            assert "my_module" in labels
            assert "another_module" in labels

    def test_scan_modules_no_src_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = IntrospectionEngine(root=tmpdir)
            engine._scan_modules()
            assert len([s for s in engine._sources if s.source_type == "module"]) == 0

    def test_scan_modules_skips_private_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src_dir = root / "src"
            src_dir.mkdir(parents=True)
            (src_dir / "__pycache__").mkdir()
            (src_dir / "__pycache__" / "__init__.py").write_text("# cache")
            engine = IntrospectionEngine(root=root)
            engine._scan_modules()
            modules = [s for s in engine._sources if s.source_type == "module"]
            labels = {s.label for s in modules}
            assert "__pycache__" not in labels


# ---------------------------------------------------------------------------
# load_all and list_sources
# ---------------------------------------------------------------------------


class TestLoadAll:
    def test_load_all_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            count = engine.load_all()
            # 2 docs + 2 skills + 2 configs + 2 modules = 8
            assert count == 8

    def test_load_all_clears_previous(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            engine.load_all()
            count1 = len(engine._sources)
            # Load again -- should clear and re-scan
            count2 = engine.load_all()
            assert count2 == count1


class TestListSources:
    def test_list_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            engine.load_all()
            all_src = engine.list_sources()
            assert len(all_src) == 8

    def test_filter_by_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            engine.load_all()
            docs = engine.list_sources(source_type="doc")
            assert len(docs) == 2
            for d in docs:
                assert d.source_type == "doc"

    def test_list_sources_auto_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            # Without calling load_all, list_sources should auto-load
            sources = engine.list_sources()
            assert len(sources) > 0

    def test_get_source_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            assert engine.get_source_count("doc") == 2
            assert engine.get_source_count("skill") == 2
            assert engine.get_source_count("config") == 2
            assert engine.get_source_count("module") == 2
            assert engine.get_source_count("nonexistent") == 0


# ---------------------------------------------------------------------------
# ask()
# ---------------------------------------------------------------------------


class TestAsk:
    def test_ask_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            answer = engine.ask("What is the version?")
            assert "1.0.0" in answer

    def test_ask_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            answer = engine.ask("What skills do I have?")
            assert "2" in answer  # 2 skills
            assert "test_skill" in answer
            assert "another" in answer

    def test_ask_no_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir, has_skills=False)
            engine = IntrospectionEngine(root=root)
            answer = engine.ask("skills")
            assert "No skills found." in answer

    def test_ask_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            answer = engine.ask("What modules are available?")
            assert "my_module" in answer
            assert "another_module" in answer

    def test_ask_no_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir, has_modules=False)
            engine = IntrospectionEngine(root=root)
            answer = engine.ask("modules")
            assert "No modules found." in answer

    def test_ask_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            answer = engine.ask("What configuration do I have?")
            assert "pyproject.toml" in answer
            assert "setup.cfg" in answer

    def test_ask_no_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir, has_config=False)
            engine = IntrospectionEngine(root=root)
            answer = engine.ask("config")
            assert "No configuration files found." in answer

    def test_ask_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            answer = engine.ask("What documentation exists?")
            assert "README.md" in answer
            assert "guide.txt" in answer

    def test_ask_no_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir, has_docs=False)
            engine = IntrospectionEngine(root=root)
            answer = engine.ask("documentation")
            assert "No documentation files found." in answer

    def test_ask_general_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            answer = engine.ask("Tell me about yourself")
            assert "Lyra" in answer
            assert "1.0.0" in answer
            assert "knowledge sources" in answer

    def test_ask_auto_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            # Without calling load_all, ask should auto-load
            answer = engine.ask("version")
            assert "1.0.0" in answer
            assert engine._loaded is True

    def test_ask_component_keyword(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            answer = engine.ask("What components exist?")
            assert "my_module" in answer


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = IntrospectionEngine(root=tmpdir)
            count = engine.load_all()
            assert count == 0

    def test_discover_root_uses_cwd_as_fallback(self) -> None:
        """_discover_root falls back to Path.cwd() when no markers exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                engine = IntrospectionEngine(root=None)
                # Should use the _discover_root method
                discovered = engine._discover_root()
                assert discovered == Path.cwd()
            finally:
                os.chdir(old_cwd)

    def test_read_version_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = IntrospectionEngine(root=tmpdir)
            version = engine._read_version()
            assert version == "unknown"

    def test_read_version_no_version_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src_dir = root / "src"
            src_dir.mkdir(parents=True)
            (src_dir / "__init__.py").write_text('"""Just a docstring."""')
            engine = IntrospectionEngine(root=root)
            assert engine.version == "unknown"

    def test_properties(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _make_project(tmpdir)
            engine = IntrospectionEngine(root=root)
            assert engine.root is not None
            assert engine.version is not None
