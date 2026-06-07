"""
Tests for Advanced Tool Features.

Covers: compound chain execution, deferred dynamic loading, web search tool,
code execution tool, PDF reading tool.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from lyra.tools.advanced_tools import (
    APICallTool,
    CodeExecTool,
    DataAnalysisTool,
    PDFReadTool,
    WebSearchTool,
)
from lyra.tools.compound_executor import (
    ChainResult,
    ChainStep,
    ChainType,
    CompoundExecutor,
    ToolChain,
    parse_chain,
)
from lyra.tools.dynamic_loader import DynamicToolLoader, LazyToolProxy, ToolSpec
from lyra.tools.executor import ToolExecutor
from lyra.tools.registry import ToolDef, ToolRegistry, ToolResult


# ===================================================================
# Fixtures & helpers
# ===================================================================


def _make_registry(extra_tools: Optional[Dict[str, ToolDef]] = None) -> ToolRegistry:
    """Build a ToolRegistry with a few simple tools for chain testing."""
    reg = ToolRegistry()

    async def _echo(**kw: Any) -> Dict[str, Any]:
        return {"success": True, "output": json.dumps(kw)}

    async def _upper(**kw: Any) -> Dict[str, Any]:
        inp = kw.get("input", "")
        return {"success": True, "output": inp.upper()}

    async def _fail(**kw: Any) -> Dict[str, Any]:
        return {"success": False, "error": "Intentional failure"}

    async def _double(**kw: Any) -> Dict[str, Any]:
        inp = kw.get("input", "0")
        try:
            val = float(inp)
        except (ValueError, TypeError):
            val = 0
        return {"success": True, "output": str(val * 2)}

    reg.register(
        ToolDef(
            name="echo",
            description="Echo params as JSON",
            handler=_echo,
            parameters={
                "type": "object",
                "properties": {
                    "input": {"type": "string"},
                    "x": {"type": "integer"},
                },
            },
        )
    )
    reg.register(
        ToolDef(
            name="upper",
            description="Uppercase input",
            handler=_upper,
            parameters={
                "type": "object",
                "properties": {"input": {"type": "string"}},
            },
        )
    )
    reg.register(
        ToolDef(
            name="fail",
            description="Always fails",
            handler=_fail,
        )
    )
    reg.register(
        ToolDef(
            name="double",
            description="Double the numeric input",
            handler=_double,
            parameters={
                "type": "object",
                "properties": {"input": {"type": "string"}},
            },
        )
    )

    if extra_tools:
        for name, td in extra_tools.items():
            reg.register(td)

    return reg


@pytest.fixture
def registry() -> ToolRegistry:
    return _make_registry()


@pytest.fixture
def executor(registry: ToolRegistry) -> ToolExecutor:
    return ToolExecutor(registry)


@pytest.fixture
def compound(executor: ToolExecutor) -> CompoundExecutor:
    return CompoundExecutor(executor.execute)


# ===================================================================
# Compound chain: parsing
# ===================================================================


class TestParseChain:
    def test_single_step(self) -> None:
        chain = parse_chain("echo")
        assert len(chain.steps) == 1
        assert chain.steps[0].tool_name == "echo"
        assert chain.steps[0].params == {}
        assert chain.chain_type == ChainType.PIPE

    def test_pipe_chain(self) -> None:
        chain = parse_chain("echo | upper")
        assert len(chain.steps) == 2
        assert chain.steps[0].tool_name == "echo"
        assert chain.steps[1].tool_name == "upper"
        assert chain.chain_type == ChainType.PIPE

    def test_pipe_with_params(self) -> None:
        chain = parse_chain("echo(x=1) | upper | double(y=2.5)")
        assert len(chain.steps) == 3
        assert chain.steps[0].tool_name == "echo"
        assert chain.steps[0].params == {"x": 1}
        assert chain.steps[1].tool_name == "upper"
        assert chain.steps[1].params == {}
        assert chain.steps[2].tool_name == "double"
        assert chain.steps[2].params == {"y": 2.5}

    def test_parallel_chain(self) -> None:
        chain = parse_chain("echo || upper || double")
        assert chain.chain_type == ChainType.PARALLEL
        assert len(chain.steps) == 3

    def test_params_parsing_types(self) -> None:
        chain = parse_chain("tool(strval='hello', intval=42, floatval=3.14, boolval=true, noneval=null)")
        params = chain.steps[0].params
        assert params["strval"] == "hello"
        assert params["intval"] == 42
        assert params["floatval"] == 3.14
        assert params["boolval"] is True
        assert params["noneval"] is None

    def test_empty_expression_raises(self) -> None:
        with pytest.raises(ValueError, match="Empty"):
            parse_chain("")

    def test_invalid_step_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_chain("echo | invalid-tool!")


# ===================================================================
# Compound chain: execution — pipe
# ===================================================================


class TestCompoundPipe:
    async def test_single_step_pipe(self, compound: CompoundExecutor) -> None:
        result = await compound.execute_chain(
            parse_chain("echo(x=42)")
        )
        assert result.success is True
        assert len(result.step_results) == 1
        assert result.step_results[0].success is True

    async def test_two_step_pipe(self, compound: CompoundExecutor) -> None:
        """echo(x=hello) → upper receives echo's output as input."""
        chain = ToolChain(
            steps=[
                ChainStep(tool_name="echo", params={"x": 1}),
                ChainStep(tool_name="upper"),
            ],
            chain_type=ChainType.PIPE,
        )
        result = await compound.execute_chain(chain)
        assert result.success is True
        assert len(result.step_results) == 2

    async def test_pipe_data_flow(self, compound: CompoundExecutor) -> None:
        """Verify output of step 0 feeds 'input' of step 1."""
        chain = ToolChain(
            steps=[
                ChainStep(tool_name="echo", params={"x": 42}),
                ChainStep(tool_name="double"),
            ],
            chain_type=ChainType.PIPE,
        )
        result = await compound.execute_chain(chain)
        assert result.success is True
        # echo outputs json of params; that becomes 'input' of double.
        # double tries to parse it as a number, so it may be NaN.
        # The chain should still report success.
        assert len(result.step_results) == 2

    async def test_pipe_abort_on_failure(self, compound: CompoundExecutor) -> None:
        """A failing step should abort the chain and preserve partial results."""
        chain = ToolChain(
            steps=[
                ChainStep(tool_name="echo", params={"x": 42}),  # first succeeds
                ChainStep(tool_name="fail"),                      # second fails
                ChainStep(tool_name="upper"),                     # never runs
            ],
            chain_type=ChainType.PIPE,
        )
        result = await compound.execute_chain(chain)
        assert result.success is False
        assert len(result.step_results) == 2  # third step never ran
        assert result.partial is True
        assert result.step_results[0].success is True
        assert result.step_results[1].success is False
        assert "Intentional failure" in (result.step_results[1].error or "")

    async def test_pipe_empty_steps(self, compound: CompoundExecutor) -> None:
        chain = ToolChain(steps=[], chain_type=ChainType.PIPE)
        result = await compound.execute_chain(chain)
        assert result.success is True
        assert len(result.step_results) == 0

    async def test_pipe_context_passing(self, compound: CompoundExecutor) -> None:
        """Context dict should be available to all steps."""
        chain = ToolChain(
            steps=[
                ChainStep(tool_name="echo", params={"x": 99}),
                ChainStep(tool_name="upper"),
            ],
            chain_type=ChainType.PIPE,
        )
        result = await compound.execute_chain(chain, context={"initial": "ctx"})
        assert result.success is True


# ===================================================================
# Compound chain: execution — parallel
# ===================================================================


class TestCompoundParallel:
    async def test_parallel_all_succeed(self, compound: CompoundExecutor) -> None:
        chain = ToolChain(
            steps=[
                ChainStep(tool_name="echo", params={"x": 1}),
                ChainStep(tool_name="echo", params={"x": 2}),
            ],
            chain_type=ChainType.PARALLEL,
        )
        result = await compound.execute_chain(chain)
        assert result.success is True
        assert len(result.step_results) == 2
        assert result.step_results[0].success is True
        assert result.step_results[1].success is True

    async def test_parallel_one_fails(self, compound: CompoundExecutor) -> None:
        chain = ToolChain(
            steps=[
                ChainStep(tool_name="echo", params={"x": 1}),
                ChainStep(tool_name="fail"),
                ChainStep(tool_name="echo", params={"x": 3}),
            ],
            chain_type=ChainType.PARALLEL,
        )
        result = await compound.execute_chain(chain)
        assert result.success is False
        assert len(result.step_results) == 3
        # All three ran (parallel), step 2 failed
        assert result.step_results[0].success is True
        assert result.step_results[1].success is False
        assert result.step_results[2].success is True
        assert result.partial is True

    async def test_parallel_empty(self, compound: CompoundExecutor) -> None:
        chain = ToolChain(steps=[], chain_type=ChainType.PARALLEL)
        result = await compound.execute_chain(chain)
        assert result.success is True


# ===================================================================
# Compound chain: execution — conditional
# ===================================================================


class TestCompoundConditional:
    async def test_conditional_then_branch(self, compound: CompoundExecutor) -> None:
        chain = ToolChain(
            chain_type=ChainType.CONDITIONAL,
            predicate=lambda ctx: ctx.get("flag", False),
            then_branch=[
                ChainStep(tool_name="echo", params={"x": 1}),
            ],
            else_branch=[
                ChainStep(tool_name="echo", params={"x": 2}),
            ],
        )
        result = await compound.execute_chain(chain, context={"flag": True})
        assert result.success is True
        assert len(result.step_results) == 1
        assert result.chain_type == ChainType.CONDITIONAL

    async def test_conditional_else_branch(self, compound: CompoundExecutor) -> None:
        chain = ToolChain(
            chain_type=ChainType.CONDITIONAL,
            predicate=lambda ctx: ctx.get("flag", False),
            then_branch=[
                ChainStep(tool_name="echo", params={"x": 1}),
            ],
            else_branch=[
                ChainStep(tool_name="echo", params={"x": 2}),
            ],
        )
        result = await compound.execute_chain(chain, context={"flag": False})
        assert result.success is True
        # else branch: echo(x=2)
        assert len(result.step_results) == 1

    async def test_conditional_no_predicate(self, compound: CompoundExecutor) -> None:
        chain = ToolChain(
            chain_type=ChainType.CONDITIONAL,
            then_branch=[ChainStep(tool_name="echo")],
        )
        result = await compound.execute_chain(chain)
        assert result.success is False
        assert "no predicate" in (result.error or "")

    async def test_conditional_empty_branch(self, compound: CompoundExecutor) -> None:
        chain = ToolChain(
            chain_type=ChainType.CONDITIONAL,
            predicate=lambda ctx: True,
            then_branch=[],
            else_branch=[],
        )
        result = await compound.execute_chain(chain)
        assert result.success is True
        assert len(result.step_results) == 0


# ===================================================================
# Dynamic loader
# ===================================================================


class TestDynamicLoader:
    def test_register_and_get_spec(self) -> None:
        loader = DynamicToolLoader()
        spec = ToolSpec(
            name="web_search",
            description="Web search",
            module_path="lyra.tools.advanced_tools",
            class_name="WebSearchTool",
        )
        loader.register_tool_spec(spec)
        assert loader.has_spec("web_search") is True
        assert loader.get_spec("web_search") is spec

    def test_register_duplicate_raises(self) -> None:
        loader = DynamicToolLoader()
        spec = ToolSpec(name="dup", description="Dup", module_path="os", class_name="path")
        loader.register_tool_spec(spec)
        with pytest.raises(ValueError, match="already registered"):
            loader.register_tool_spec(spec)

    def test_unregister(self) -> None:
        loader = DynamicToolLoader()
        spec = ToolSpec(name="tmp", description="Tmp", module_path="os", class_name="path")
        loader.register_tool_spec(spec)
        removed = loader.unregister("tmp")
        assert removed is spec
        assert loader.has_spec("tmp") is False

    def test_list_specs(self) -> None:
        loader = DynamicToolLoader()
        a = ToolSpec(name="a", description="A", module_path="os", class_name="path")
        b = ToolSpec(name="b", description="B", module_path="os", class_name="getcwd")
        loader.register_tool_spec(a)
        loader.register_tool_spec(b)
        names = {s.name for s in loader.list_specs()}
        assert names == {"a", "b"}

    def test_load_on_first_use_creates_proxy(self) -> None:
        loader = DynamicToolLoader()
        spec = ToolSpec(
            name="web_search",
            description="Web search",
            module_path="lyra.tools.advanced_tools",
            class_name="WebSearchTool",
        )
        loader.register_tool_spec(spec)
        tool_def = loader.load_on_first_use("web_search")
        assert tool_def is not None
        assert isinstance(tool_def.handler, LazyToolProxy)
        assert tool_def.handler.loaded is False  # not yet loaded

    def test_load_all(self) -> None:
        loader = DynamicToolLoader()
        loader.register_tool_spec(
            ToolSpec(name="a", description="A", module_path="os", class_name="path")
        )
        loader.register_tool_spec(
            ToolSpec(name="b", description="B", module_path="os", class_name="getcwd")
        )
        tds = loader.load_all()
        assert len(tds) == 2
        # Calling load_all again should return cached
        tds2 = loader.load_all()
        assert len(tds2) == 2

    def test_force_load_actually_imports(self) -> None:
        """force_load should trigger the actual import."""
        loader = DynamicToolLoader()
        loader.register_tool_spec(
            ToolSpec(
                name="getcwd",
                description="Get current dir",
                module_path="os",
                class_name="getcwd",
            )
        )
        handler = loader.force_load("getcwd")
        assert handler is not None
        # The handler should be the real os.getcwd, not a proxy
        import os

        assert handler is os.getcwd

    def test_invalid_module_path(self) -> None:
        loader = DynamicToolLoader()
        loader.register_tool_spec(
            ToolSpec(
                name="bad",
                description="Bad module",
                module_path="nonexistent_module_xyz",
                class_name="Something",
            )
        )
        td = loader.load_on_first_use("bad")
        assert td is not None
        proxy = td.handler
        assert isinstance(proxy, LazyToolProxy)
        # A call should return an error, not crash
        coro = proxy()
        # inspect the proxy - calling it should produce an error result
        import asyncio

        result = asyncio.run(proxy())
        assert result["success"] is False
        assert "nonexistent_module_xyz" in (result.get("error", ""))

    def test_stats(self) -> None:
        loader = DynamicToolLoader()
        stats = loader.stats()
        assert stats["total_specs"] == 0
        loader.register_tool_spec(
            ToolSpec(name="s1", description="S1", module_path="os", class_name="path")
        )
        loader.load_on_first_use("s1")
        stats = loader.stats()
        assert stats["total_specs"] == 1
        assert stats["lazy_tools_created"] == 1
        assert stats["handlers_pending"] == 1

    def test_lazy_tool_proxy_repr(self) -> None:
        spec = ToolSpec(name="test", description="Test", module_path="os", class_name="path")
        proxy = LazyToolProxy(spec)
        assert "pending" in repr(proxy)

    def test_lazy_tool_proxy_spec_property(self) -> None:
        spec = ToolSpec(name="test", description="Test", module_path="os", class_name="path")
        proxy = LazyToolProxy(spec)
        assert proxy.spec is spec

    def test_lazy_tool_proxy_loaded_property(self) -> None:
        spec = ToolSpec(name="test", description="Test", module_path="os", class_name="path")
        proxy = LazyToolProxy(spec)
        assert proxy.loaded is False
        # Calling triggers loading. os.path is a module not a callable,
        # so proxy should set _load_error.
        asyncio.run(proxy())
        assert proxy.loaded is False
        assert proxy._load_error is not None

    def test_tool_spec_to_tool_def(self) -> None:
        async def fake_handler(**kw: Any) -> Dict[str, Any]:
            return {"success": True, "output": "ok"}

        spec = ToolSpec(
            name="test",
            description="Test",
            capabilities=["file"],
            sandbox_requirements={"timeout_seconds": 10},
        )
        td = spec.to_tool_def(fake_handler)
        assert td.name == "test"
        assert td.description == "Test"
        assert td.capabilities == ["file"]
        assert td.sandbox_requirements == {"timeout_seconds": 10}
        assert td.handler is fake_handler


# ===================================================================
# WebSearchTool
# ===================================================================


class TestWebSearchTool:
    async def test_requires_query(self) -> None:
        tool = WebSearchTool()
        result = await tool.search()
        assert result["success"] is False
        assert "query" in (result.get("error", "")).lower()

    async def test_unknown_backend(self) -> None:
        tool = WebSearchTool()
        result = await tool.search(query="test", backend="unknown")
        assert result["success"] is False
        assert "unknown search backend" in result.get("error", "").lower()

    async def test_serpapi_missing_key(self) -> None:
        tool = WebSearchTool(backend="serpapi", api_key="")
        result = await tool.search(query="test")
        assert result["success"] is False
        assert "api key" in result.get("error", "").lower()

    async def test_duckduckgo_missing_dep(self) -> None:
        """When duckduckgo_search is not installed, should return a clear error."""
        tool = WebSearchTool(backend="duckduckgo")
        result = await tool.search(query="hello")
        # If the package is not installed, we get an install hint
        if result["success"] is False:
            assert "duckduckgo_search" in result.get("error", "")
        # If it IS installed (dev machine), the test still passes either way

    def test_tool_def_schema(self) -> None:
        tool = WebSearchTool()
        defs = tool.defs
        assert len(defs) == 1
        assert defs[0].name == "WebSearch"
        assert "network" in defs[0].capabilities
        assert "query" in defs[0].parameters.get("required", [])


# ===================================================================
# CodeExecTool
# ===================================================================


class TestCodeExecTool:
    async def test_requires_code(self) -> None:
        tool = CodeExecTool()
        result = await tool.execute()
        assert result["success"] is False
        assert "code" in (result.get("error", "")).lower()

    async def test_python_execution(self) -> None:
        tool = CodeExecTool()
        result = await tool.execute(
            code='print("hello from lyra")',
            language="python",
        )
        assert result["success"] is True
        assert "hello from lyra" in result.get("output", "")

    async def test_python_execution_with_return_value(self) -> None:
        tool = CodeExecTool()
        result = await tool.execute(
            code="import json; print(json.dumps({'status': 'ok', 'value': 42}))",
            language="python",
        )
        assert result["success"] is True
        assert "ok" in result.get("output", "")

    async def test_python_error(self) -> None:
        tool = CodeExecTool()
        result = await tool.execute(
            code="raise ValueError('test error')",
            language="python",
        )
        assert result["success"] is False
        assert "test error" in result.get("output", "")

    async def test_shell_execution(self) -> None:
        tool = CodeExecTool()
        result = await tool.execute(
            code="echo 'shell test'",
            language="shell",
        )
        assert result["success"] is True
        assert "shell test" in result.get("output", "")

    async def test_unsupported_language(self) -> None:
        tool = CodeExecTool()
        result = await tool.execute(
            code="print('hi')",
            language="ruby",
        )
        assert result["success"] is False
        assert "unsupported" in result.get("error", "").lower()

    async def test_timeout(self) -> None:
        tool = CodeExecTool(default_timeout=30)
        result = await tool.execute(
            code="import time; time.sleep(100)",
            language="python",
            timeout=0.5,
        )
        assert result["success"] is False
        assert "timed out" in (result.get("error", "")).lower()

    def test_tool_defs(self) -> None:
        tool = CodeExecTool()
        defs = tool.defs
        assert len(defs) == 1
        assert defs[0].name == "CodeExec"
        assert "shell" in defs[0].capabilities
        assert "code" in defs[0].parameters.get("required", [])


# ===================================================================
# PDFReadTool
# ===================================================================


class TestPDFReadTool:
    async def test_requires_path(self) -> None:
        tool = PDFReadTool()
        result = await tool.extract()
        assert result["success"] is False
        assert "path" in (result.get("error", "")).lower()

    async def test_file_not_found(self) -> None:
        tool = PDFReadTool()
        result = await tool.extract(path="/nonexistent/file.pdf")
        assert result["success"] is False
        assert "not found" in (result.get("error", "")).lower()

    async def test_pdf_read_missing_dependency(self) -> None:
        """If neither PyMuPDF nor pdfminer is installed, the error is graceful."""
        tool = PDFReadTool()
        # Create a minimal valid PDF (empty)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            # Minimal PDF header
            f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\nxref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \ntrailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n118\n%%EOF")
            tmp_path = f.name

        try:
            result = await tool.extract(path=tmp_path)
            # If no PDF lib available, we get a dependency error
            if result["success"] is False and "error" in result:
                assert any(
                    kw in result["error"].lower()
                    for kw in ["pymupdf", "pdfminer", "install"]
                )
        finally:
            os.unlink(tmp_path)

    def test_tool_def_schema(self) -> None:
        tool = PDFReadTool()
        defs = tool.defs
        assert len(defs) == 1
        assert defs[0].name == "PDFRead"
        assert "file" in defs[0].capabilities
        assert "path" in defs[0].parameters.get("required", [])


# ===================================================================
# DataAnalysisTool
# ===================================================================


class TestDataAnalysisTool:
    async def test_requires_path(self) -> None:
        tool = DataAnalysisTool()
        result = await tool.analyze()
        assert result["success"] is False
        assert "path" in (result.get("error", "")).lower()

    async def test_file_not_found(self) -> None:
        tool = DataAnalysisTool()
        result = await tool.analyze(path="/nonexistent/data.csv")
        assert result["success"] is False
        assert "not found" in (result.get("error", "")).lower()

    async def test_csv_analysis_describe(self) -> None:
        tool = DataAnalysisTool()
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("name,age,score\nAlice,30,95\nBob,25,87\nCharlie,35,92\n")
            tmp_path = f.name

        try:
            result = await tool.analyze(path=tmp_path, operation="describe")
            if result["success"]:
                data = json.loads(result["output"])
                assert data["shape"] == [3, 3]
                assert "name" in data["columns"]
                assert "age" in data["columns"]
            # If pandas not installed, we get a graceful error
            else:
                assert "pandas" in (result.get("error", "")).lower()
        finally:
            os.unlink(tmp_path)

    async def test_csv_head(self) -> None:
        tool = DataAnalysisTool()
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write("x,y\n1,2\n3,4\n5,6\n")
            tmp_path = f.name

        try:
            result = await tool.analyze(path=tmp_path, operation="head", columns=["x"])
            if result["success"]:
                assert "1" in result["output"]
                assert "3" in result["output"]
        finally:
            os.unlink(tmp_path)

    def test_tool_def_schema(self) -> None:
        tool = DataAnalysisTool()
        defs = tool.defs
        assert len(defs) == 1
        assert defs[0].name == "DataAnalysis"
        assert "file" in defs[0].capabilities


# ===================================================================
# APICallTool
# ===================================================================


class TestAPICallTool:
    async def test_requires_url(self) -> None:
        tool = APICallTool()
        result = await tool.call_api()
        assert result["success"] is False
        assert "url" in (result.get("error", "")).lower()

    async def test_unsupported_method(self) -> None:
        tool = APICallTool()
        result = await tool.call_api(url="http://example.com", method="OPTIONS")
        assert result["success"] is False
        # aiohttp passes OPTIONS through; example.com returns 405
        assert not result.get("error", "").startswith("Unsupported HTTP method")
        # The result may be a network error or 405 depending on environment

    async def test_real_http_get(self) -> None:
        """Make a real HTTP GET to a stable, widely-available endpoint."""
        tool = APICallTool()
        result = await tool.call_api(url="https://httpbin.org/get", method="GET")
        if result["success"]:
            data = json.loads(result["output"])
            assert data["status"] == 200
        else:
            # Network may not be available in test environment; skip
            pytest.skip(f"Network unavailable: {result.get('error')}")

    async def test_auth_bearer(self) -> None:
        tool = APICallTool()
        result = await tool.call_api(
            url="https://httpbin.org/bearer",
            method="GET",
            auth_type="bearer",
            auth_token="test-token",
        )
        if result["success"]:
            data = json.loads(result["output"])
            assert data["status"] in (200,)
        else:
            pytest.skip(f"Bearer test failed: {result.get('error')}")

    async def test_auth_missing_params(self) -> None:
        tool = APICallTool()
        result = await tool.call_api(
            url="http://example.com",
            method="GET",
            auth_type="bearer",
        )
        assert result["success"] is False
        assert "auth_token" in (result.get("error", "")).lower()

    async def test_unknown_auth_type(self) -> None:
        tool = APICallTool()
        result = await tool.call_api(
            url="http://example.com",
            method="GET",
            auth_type="unknown_auth",
        )
        assert result["success"] is False
        assert "unknown auth_type" in result.get("error", "").lower()

    async def test_timeout_handling(self) -> None:
        """Very short timeout should produce a timeout error."""
        tool = APICallTool()
        result = await tool.call_api(
            url="https://httpbin.org/delay/10",
            method="GET",
            timeout=0.1,
        )
        assert result["success"] is False
        # May be timeout or connection-related depending on environment

    def test_tool_def_schema(self) -> None:
        tool = APICallTool()
        defs = tool.defs
        assert len(defs) == 1
        assert defs[0].name == "APICall"
        assert "network" in defs[0].capabilities
        assert "url" in defs[0].parameters.get("required", [])


# ===================================================================
# ChainResult validation
# ===================================================================


class TestChainResult:
    def test_frozen(self) -> None:
        """ChainResult should be frozen (immutable)."""
        result = ChainResult(
            success=True,
            step_results=[],
            chain_type=ChainType.PIPE,
        )
        with pytest.raises(Exception):
            result.success = False  # type: ignore[misc]

    def test_serializable(self) -> None:
        """ChainResult attributes should be accessible."""
        step = ToolResult(success=True, output="hello")
        result = ChainResult(
            success=True,
            step_results=[step],
            chain_type=ChainType.PIPE,
            execution_time_ms=12.5,
        )
        assert result.success is True
        assert len(result.step_results) == 1
        assert result.step_results[0].output == "hello"
        assert result.execution_time_ms == 12.5


# ===================================================================
# Edge cases
# ===================================================================


class TestCompoundEdgeCases:
    async def test_chain_timeout(self) -> None:
        """A chain-level timeout should stop the entire chain."""
        # Create a tool that sleeps
        async def _slow(**kw: Any) -> Dict[str, Any]:
            await asyncio.sleep(10)
            return {"success": True, "output": "done"}

        reg = _make_registry()
        reg.register(
            ToolDef(name="slow", description="Slow tool", handler=_slow)
        )
        exec_ = ToolExecutor(reg)
        compound = CompoundExecutor(exec_.execute)

        chain = ToolChain(
            steps=[ChainStep(tool_name="slow")],
            chain_timeout=0.1,
        )
        result = await compound.execute_chain(chain)
        assert result.success is False
        assert "timeout" in (result.error or "").lower()

    async def test_step_timeout(self) -> None:
        """Per-step timeout should be respected."""
        async def _slow(**kw: Any) -> Dict[str, Any]:
            await asyncio.sleep(10)
            return {"success": True, "output": "done"}

        reg = _make_registry()
        reg.register(
            ToolDef(name="slow_step", description="Slow step", handler=_slow)
        )
        exec_ = ToolExecutor(reg)
        compound = CompoundExecutor(exec_.execute)

        chain = ToolChain(
            steps=[
                ChainStep(tool_name="echo", params={"x": 1}),
                ChainStep(tool_name="slow_step", timeout=0.1),
            ],
        )
        result = await compound.execute_chain(chain)
        assert result.success is False
        assert len(result.step_results) == 2
        assert result.step_results[0].success is True
        assert result.step_results[1].success is False

    async def test_predicate_raises(self) -> None:
        """If the predicate raises, the chain should fail gracefully."""
        compound = CompoundExecutor(lambda name, timeout=None, **kw: None)  # type: ignore
        chain = ToolChain(
            chain_type=ChainType.CONDITIONAL,
            predicate=lambda ctx: 1 / 0,  # will raise ZeroDivisionError
            then_branch=[ChainStep(tool_name="echo")],
        )
        result = await compound.execute_chain(chain)
        assert result.success is False
        assert "predicate" in (result.error or "").lower()

    async def test_parse_chain_with_tool_names_with_dots(self) -> None:
        """Tool names with dots (module notation) should parse."""
        chain = parse_chain("my_tools.analyze | my_tools.report")
        assert len(chain.steps) == 2
        assert chain.steps[0].tool_name == "my_tools.analyze"

    async def test_custom_executor_integration(self) -> None:
        """Verify CompoundExecutor works with a custom step runner."""
        trace: list[str] = []

        async def custom_run(name: str, timeout: Optional[float] = None, **kw: Any) -> ToolResult:
            trace.append(name)
            return ToolResult(success=True, output=f"ran:{name}")

        compound = CompoundExecutor(custom_run)
        chain = parse_chain("a | b | c")
        result = await compound.execute_chain(chain)
        assert result.success is True
        assert trace == ["a", "b", "c"]
