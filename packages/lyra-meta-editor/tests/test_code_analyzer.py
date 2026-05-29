"""Tests for the code_analyzer module."""

from __future__ import annotations

import os
import tempfile

import pytest
from lyra_meta_editor import (
    AnalysisConfig,
    CodeAnalysisError,
    CodeAnalyzer,
    CodeMetrics,
    HotspotReport,
)


@pytest.fixture
def sample_py_file() -> str:
    """Create a temporary Python file for testing."""
    content = (
        "import os\n"
        "import sys\n"
        "from typing import Optional\n"
        "\n"
        "\n"
        "def greet(name: str) -> str:\n"
        '    return f"Hello {name}"\n'
        "\n"
        "\n"
        "async def process(items: list) -> None:\n"
        "    for item in items:\n"
        "        if item:\n"
        "            print(item)\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False
    ) as f:
        f.write(content)
        path = f.name
    yield path
    os.unlink(path)


class TestAnalysisConfig:
    """Tests for AnalysisConfig."""

    def test_default_values(self) -> None:
        cfg = AnalysisConfig()
        assert cfg.max_file_size == 100000
        assert cfg.ignore_patterns == ("__pycache__", ".git", "tests")
        assert cfg.complexity_threshold == 10

    def test_custom_values(self) -> None:
        cfg = AnalysisConfig(max_file_size=50000, complexity_threshold=5)
        assert cfg.max_file_size == 50000
        assert cfg.complexity_threshold == 5

    def test_immutable(self) -> None:
        cfg = AnalysisConfig()
        with pytest.raises(AttributeError):
            cfg.max_file_size = 999  # type: ignore[misc]

    def test_frozen_dataclass(self) -> None:
        cfg1 = AnalysisConfig()
        cfg2 = AnalysisConfig()
        assert cfg1 == cfg2


class TestCodeMetrics:
    """Tests for CodeMetrics."""

    def test_creation(self) -> None:
        m = CodeMetrics(
            file_path="/a.py",
            loc=10,
            complexity=3,
            functions=("foo",),
            imports=("os",),
            dependencies=("numpy",),
        )
        assert m.file_path == "/a.py"
        assert m.loc == 10
        assert m.complexity == 3

    def test_immutable(self) -> None:
        m = CodeMetrics("/a.py", 1, 1, (), (), ())
        with pytest.raises(AttributeError):
            m.loc = 99  # type: ignore[misc]


class TestHotspotReport:
    """Tests for HotspotReport."""

    def test_empty_report(self) -> None:
        r = HotspotReport(
            metrics=(),
            hotspots=(),
            suggestions=(),
            overall_health=100.0,
        )
        assert r.overall_health == 100.0
        assert len(r.metrics) == 0


class TestCodeAnalyzer:
    """Tests for CodeAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyze_file(self, sample_py_file: str) -> None:
        metrics = await CodeAnalyzer.analyze_file(sample_py_file)
        assert metrics.file_path == sample_py_file
        assert metrics.loc > 0
        assert metrics.complexity >= 1
        assert "greet" in metrics.functions
        assert "process" in metrics.functions

    @pytest.mark.asyncio
    async def test_analyze_file_not_found(self) -> None:
        with pytest.raises(CodeAnalysisError, match="not found"):
            await CodeAnalyzer.analyze_file("/nonexistent/file.py")

    @pytest.mark.asyncio
    async def test_analyze_file_file_size_exceeded(self) -> None:
        cfg = AnalysisConfig(max_file_size=100)
        old = CodeAnalyzer.CONFIG
        CodeAnalyzer.CONFIG = cfg
        large = "x = 1\n" * 1000
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(large)
            path = f.name
        try:
            with pytest.raises(CodeAnalysisError, match="exceeds max size"):
                await CodeAnalyzer.analyze_file(path)
        finally:
            os.unlink(path)
            CodeAnalyzer.CONFIG = old

    @pytest.mark.asyncio
    async def test_analyze_package_not_found(self) -> None:
        with pytest.raises(CodeAnalysisError, match="not found"):
            await CodeAnalyzer.analyze_package("/nonexistent/dir")

    @pytest.mark.asyncio
    async def test_analyze_package_empty_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = await CodeAnalyzer.analyze_package(tmpdir)
            assert len(report.metrics) == 0
            assert report.overall_health == 100.0

    @pytest.mark.asyncio
    async def test_analyze_package_with_files(self, sample_py_file: str) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            import shutil
            dest = os.path.join(tmpdir, os.path.basename(sample_py_file))
            shutil.copy2(sample_py_file, dest)
            report = await CodeAnalyzer.analyze_package(tmpdir)
            assert len(report.metrics) >= 1

    def test_compute_complexity_simple(self) -> None:
        source = "x = 1\n"
        c = CodeAnalyzer.compute_complexity(source)
        assert c == 1  # base complexity

    def test_compute_complexity_with_if(self) -> None:
        source = "if x:\n    pass\n"
        c = CodeAnalyzer.compute_complexity(source)
        assert c == 2  # base + if

    def test_compute_complexity_with_loop(self) -> None:
        source = "for i in range(10):\n    if i > 5:\n        pass\n"
        c = CodeAnalyzer.compute_complexity(source)
        assert c == 3  # base + for + if

    def test_compute_complexity_with_bool_op(self) -> None:
        source = "if x and y:\n    pass\n"
        c = CodeAnalyzer.compute_complexity(source)
        # base (1) + if (1) + boolop (1 for and)
        assert c >= 2

    def test_compute_complexity_syntax_error(self) -> None:
        source = "if x:\n"
        c = CodeAnalyzer.compute_complexity(source)
        assert c == 1  # falls back to 1

    def test_extract_imports_standard(self) -> None:
        source = "import os\nimport sys\n"
        imports = CodeAnalyzer.extract_imports(source)
        assert "os" in imports
        assert "sys" in imports

    def test_extract_imports_from(self) -> None:
        source = "from typing import Optional, List\n"
        imports = CodeAnalyzer.extract_imports(source)
        assert "typing.Optional" in imports
        assert "typing.List" in imports

    def test_extract_imports_no_imports(self) -> None:
        source = "x = 1\n"
        imports = CodeAnalyzer.extract_imports(source)
        assert imports == ()

    def test_extract_imports_syntax_error(self) -> None:
        source = "if x:\n"
        imports = CodeAnalyzer.extract_imports(source)
        assert imports == ()

    def test_complexity_with_while_and_except(self) -> None:
        source = (
            "while True:\n"
            "    try:\n"
            "        pass\n"
            "    except ValueError:\n"
            "        break\n"
        )
        c = CodeAnalyzer.compute_complexity(source)
        # base (1) + while (1) + except (1) = 3
        assert c >= 3

    def test_analyze_file_with_directory_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(CodeAnalysisError, match="not found"):
                # This is a directory, not a file
                import asyncio
                asyncio.run(CodeAnalyzer.analyze_file(tmpdir))

    @pytest.mark.asyncio
    async def test_hotspot_detection(self, sample_py_file: str) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, "test.py")
            # Create a file with high complexity
            complex_code = (
                "if a:\n"
                "    if b:\n"
                "        if c:\n"
                "            if d:\n"
                "                pass\n"
            )
            with open(dest, "w") as f:
                f.write(complex_code)
            report = await CodeAnalyzer.analyze_package(tmpdir)
            assert len(report.metrics) == 1
            metric = report.metrics[0]
            assert metric.complexity >= 5

    def test_analyze_file_non_python_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
                f.write("hello")
            import asyncio
            report = asyncio.run(CodeAnalyzer.analyze_package(tmpdir))
            assert len(report.metrics) == 0

    @pytest.mark.asyncio
    async def test_dependencies_extraction(self, sample_py_file: str) -> None:
        metrics = await CodeAnalyzer.analyze_file(sample_py_file)
        # os and sys are stdlib, typing is stdlib, so no dependencies
        assert len(metrics.dependencies) == 0

    @pytest.mark.asyncio
    async def test_dependencies_third_party(self) -> None:
        content = "import numpy\nimport pandas\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(content)
            path = f.name
        try:
            metrics = await CodeAnalyzer.analyze_file(path)
            assert "numpy" in metrics.dependencies
            assert "pandas" in metrics.dependencies
        finally:
            os.unlink(path)
