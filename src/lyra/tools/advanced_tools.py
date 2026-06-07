"""
Advanced built-in tool handlers for Lyra.

Provides five tools beyond the built-in set: WebSearchTool, CodeExecTool,
PDFReadTool, DataAnalysisTool, and APICallTool.  Each tool exposes a
``ToolDef``-compatible schema and an async handler.

Tools that depend on optional third-party libraries (pandas, matplotlib,
PyMuPDF) gracefully degrade with a clear error message when the library
is not installed.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from lyra.tools.registry import ToolDef, ToolHandler


# ===================================================================
# WebSearchTool
# ===================================================================


class WebSearchTool:
    """Web search via configurable backend.

    Supports DuckDuckGo (via the ``duckduckgo_search`` library) and
    SerpAPI (via ``requests`` / ``aiohttp``).

    Parameters
    ----------
    backend:
        Search backend name (``"duckduckgo"`` or ``"serpapi"``).
    api_key:
        API key for SerpAPI (ignored for DuckDuckGo).
    max_results:
        Default maximum results per query.
    """

    def __init__(
        self,
        backend: str = "duckduckgo",
        api_key: Optional[str] = None,
        max_results: int = 5,
    ) -> None:
        self._backend = backend
        self._api_key = api_key or os.environ.get("SERPAPI_API_KEY", "")
        self._max_results = max_results

    @property
    def defs(self) -> List[ToolDef]:
        """Return ``ToolDef`` entries for each registered tool."""
        return [
            ToolDef(
                name="WebSearch",
                description="Search the web. Supports DuckDuckGo (default) and SerpAPI backends.",
                capabilities=["network"],
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 5)",
                            "default": 5,
                        },
                        "backend": {
                            "type": "string",
                            "description": "Search backend: 'duckduckgo' or 'serpapi'",
                            "default": "duckduckgo",
                        },
                    },
                    "required": ["query"],
                },
                handler=self.search,
            ),
        ]

    async def search(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute a web search.

        Kwargs
        ------
        query:
            Search query.
        max_results:
            Maximum results to return (default 5).
        backend:
            Backend override (default: instance default).
        """
        query = kwargs.get("query", "")
        if not query:
            return {"success": False, "error": "Missing required parameter: 'query'"}

        max_results = kwargs.get("max_results", self._max_results)
        backend = kwargs.get("backend", self._backend)

        if backend == "duckduckgo":
            return await self._search_duckduckgo(query, max_results)
        elif backend == "serpapi":
            return await self._search_serpapi(query, max_results)
        else:
            return {
                "success": False,
                "error": f"Unknown search backend: '{backend}'. "
                f"Supported: duckduckgo, serpapi",
            }

    async def _search_duckduckgo(self, query: str, max_results: int) -> Dict[str, Any]:
        """Search via DuckDuckGo.

        Runs the synchronous ``duckduckgo_search`` client in a thread pool
        executor to avoid blocking the event loop.
        """
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return {
                "success": False,
                "error": "DuckDuckGo backend requires 'duckduckgo_search' package. "
                "Install with: pip install duckduckgo_search",
            }

        loop = asyncio.get_event_loop()

        def _sync_search() -> List[Dict[str, str]]:
            results: List[Dict[str, str]] = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    })
                    if len(results) >= max_results:
                        break
            return results

        try:
            results = await loop.run_in_executor(None, _sync_search)
        except ImportError:
            return {
                "success": False,
                "error": "DuckDuckGo backend requires 'ddgs' package. "
                "Install with: pip install ddgs",
            }
        except Exception as exc:
            return {"success": False, "error": f"DuckDuckGo search failed: {exc}"}

        if not results:
            return {
                "success": True,
                "output": "No results found.",
                "error": None,
            }

        return {
            "success": True,
            "output": json.dumps(results, indent=2),
            "error": None,
        }

    async def _search_serpapi(self, query: str, max_results: int) -> Dict[str, Any]:
        """Search via SerpAPI."""
        if not self._api_key:
            return {
                "success": False,
                "error": "SerpAPI backend requires an API key. "
                "Set SERPAPI_API_KEY environment variable or pass api_key.",
            }

        try:
            import aiohttp
        except ImportError:
            return {"success": False, "error": "SerpAPI requires 'aiohttp' package"}

        params = {
            "q": query,
            "api_key": self._api_key,
            "num": min(max_results, 10),
            "engine": "google",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://serpapi.com/search",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        return {
                            "success": False,
                            "error": f"SerpAPI returned HTTP {resp.status}: {text[:500]}",
                        }
                    data = await resp.json()
        except asyncio.TimeoutError:
            return {"success": False, "error": "SerpAPI request timed out"}
        except aiohttp.ClientError as exc:
            return {"success": False, "error": f"SerpAPI request failed: {exc}"}

        organic = data.get("organic_results", [])
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": r.get("snippet", ""),
            }
            for r in organic[:max_results]
        ]

        if not results:
            return {"success": True, "output": "No results found."}

        return {
            "success": True,
            "output": json.dumps(results, indent=2),
        }


# ===================================================================
# CodeExecTool
# ===================================================================


class CodeExecTool:
    """Execute code in an isolated subprocess.

    Supports Python, JavaScript (Node.js), and shell scripts.  Each
    invocation runs in a fresh subprocess with a configurable timeout.

    Parameters
    ----------
    default_timeout:
        Default execution timeout in seconds.
    max_output_bytes:
        Maximum bytes of stdout/stderr captured.
    """

    def __init__(
        self,
        default_timeout: int = 30,
        max_output_bytes: int = 1_048_576,
    ) -> None:
        self._default_timeout = default_timeout
        self._max_output_bytes = max_output_bytes

    @property
    def defs(self) -> List[ToolDef]:
        return [
            ToolDef(
                name="CodeExec",
                description="Execute code in a sandboxed subprocess. Supports Python (.py), JavaScript (.js), and shell (.sh).",
                capabilities=["shell"],
                sandbox_requirements={"timeout_seconds": self._default_timeout},
                parameters={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Source code to execute",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language: 'python', 'javascript', or 'shell' (default: 'python')",
                            "default": "python",
                        },
                        "timeout": {
                            "type": "number",
                            "description": f"Timeout in seconds (default: {self._default_timeout})",
                            "default": self._default_timeout,
                        },
                    },
                    "required": ["code"],
                },
                handler=self.execute,
            ),
        ]

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute code in a subprocess.

        Kwargs
        ------
        code:
            Source code string.
        language:
            One of ``python``, ``javascript``, ``shell``.
        timeout:
            Timeout in seconds.
        """
        code = kwargs.get("code", "")
        if not code:
            return {"success": False, "error": "Missing required parameter: 'code'"}

        language = kwargs.get("language", "python")
        timeout = float(kwargs.get("timeout", self._default_timeout))

        # Determine interpreter
        interpreter, ext = self._resolve_interpreter(language)
        if interpreter is None:
            return {
                "success": False,
                "error": f"Unsupported language: '{language}'. "
                f"Supported: python, javascript, shell",
            }

        # Write code to a temp file
        try:
            tmp_dir = Path(tempfile.mkdtemp(prefix="lyra-codeexec-"))
            src_file = tmp_dir / f"script{ext}"
            src_file.write_text(code, encoding="utf-8")
        except OSError as exc:
            return {"success": False, "error": f"Failed to write temp file: {exc}"}

        try:
            # Build the command
            if language == "shell":
                cmd = [interpreter, str(src_file)]
            else:
                cmd = [interpreter, str(src_file)]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(tmp_dir),
            )
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Interpreter '{interpreter}' not found. "
                f"Is it installed and on PATH?",
            }
        except OSError as exc:
            return {"success": False, "error": str(exc)}

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            proc.kill()
            await proc.wait()
            return {"success": False, "error": f"Code execution timed out after {timeout}s"}
        except OSError as exc:
            proc.kill()
            await proc.wait()
            return {"success": False, "error": str(exc)}

        out_text = stdout.decode("utf-8", errors="replace") if stdout else ""
        err_text = stderr.decode("utf-8", errors="replace") if stderr else ""

        # Truncate if too large
        if len(out_text.encode("utf-8")) > self._max_output_bytes:
            out_text = out_text[: self._max_output_bytes] + "\n... (truncated)"
        if len(err_text.encode("utf-8")) > self._max_output_bytes:
            err_text = err_text[: self._max_output_bytes] + "\n... (truncated)"

        # Cleanup temp dir
        try:
            import shutil

            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

        combined = out_text
        if err_text:
            if combined:
                combined += "\n" + err_text
            else:
                combined = err_text

        return {
            "success": proc.returncode == 0,
            "output": combined,
            "error": None if proc.returncode == 0 else err_text or f"Exit code {proc.returncode}",
        }

    @staticmethod
    def _resolve_interpreter(language: str) -> tuple[Optional[str], str]:
        """Return (interpreter_path, file_extension) for a language."""
        mapping: Dict[str, tuple[str, str]] = {
            "python": (sys.executable or "python3", ".py"),
            "javascript": ("node", ".js"),
            "shell": ("/bin/bash", ".sh"),
        }
        return mapping.get(language, (None, ""))


# ===================================================================
# PDFReadTool
# ===================================================================


class PDFReadTool:
    """Extract text from PDF files.

    Requires PyMuPDF (``fitz``) or ``pdfminer.six``.  Tries PyMuPDF
    first for speed, falls back to pdfminer.
    """

    @property
    def defs(self) -> List[ToolDef]:
        return [
            ToolDef(
                name="PDFRead",
                description="Extract text content from a PDF file.",
                capabilities=["file"],
                sandbox_requirements={"timeout_seconds": 30},
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the PDF file (absolute or workspace-relative)",
                        },
                        "max_pages": {
                            "type": "integer",
                            "description": "Maximum number of pages to extract (default: all)",
                            "default": -1,
                        },
                        "page_numbers": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Specific page numbers (0-indexed) to extract. Overrides max_pages.",
                        },
                    },
                    "required": ["path"],
                },
                handler=self.extract,
            ),
        ]

    async def extract(self, **kwargs: Any) -> Dict[str, Any]:
        """Extract text from a PDF file.

        Kwargs
        ------
        path:
            Path to the PDF file.
        max_pages:
            Maximum number of pages (default: all).
        page_numbers:
            Specific page numbers to extract (0-indexed).
        """
        path = kwargs.get("path", "")
        if not path:
            return {"success": False, "error": "Missing required parameter: 'path'"}

        pdf_path = Path(path)
        if not pdf_path.exists():
            return {"success": False, "error": f"File not found: '{path}'"}
        if not pdf_path.is_file():
            return {"success": False, "error": f"'{path}' is not a file"}

        max_pages = kwargs.get("max_pages", -1)
        page_numbers: Optional[List[int]] = kwargs.get("page_numbers")

        # Run extraction in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        try:
            text = await loop.run_in_executor(
                None,
                self._extract_sync,
                pdf_path,
                max_pages,
                page_numbers,
            )
        except Exception as exc:
            return {"success": False, "error": f"PDF extraction failed: {exc}"}

        if isinstance(text, dict) and "error" in text:
            return text  # pass through error dict from _extract_sync

        return {
            "success": True,
            "output": text,
        }

    @staticmethod
    def _extract_sync(
        pdf_path: Path,
        max_pages: int,
        page_numbers: Optional[List[int]],
    ) -> str:
        """Synchronous PDF extraction, called in a thread pool executor."""
        # Try PyMuPDF first
        try:
            return PDFReadTool._extract_with_fitz(pdf_path, max_pages, page_numbers)
        except ImportError:
            pass

        # Fallback to pdfminer
        try:
            return PDFReadTool._extract_with_pdfminer(pdf_path, max_pages, page_numbers)
        except ImportError:
            pass

        return json.dumps({
            "error": "PDF extraction requires 'PyMuPDF' or 'pdfminer.six'. "
            "Install with: pip install PyMuPDF  # or pdfminer.six",
        })

    @staticmethod
    def _extract_with_fitz(
        pdf_path: Path,
        max_pages: int,
        page_numbers: Optional[List[int]],
    ) -> str:
        """Extract text using PyMuPDF (fitz)."""
        import fitz  # type: ignore[import-untyped]

        doc = fitz.open(str(pdf_path))
        try:
            pages: List[str] = []
            num_pages = len(doc)

            if page_numbers is not None:
                indices = [p for p in page_numbers if 0 <= p < num_pages]
            elif max_pages > 0:
                indices = list(range(min(num_pages, max_pages)))
            else:
                indices = list(range(num_pages))

            for i in indices:
                page = doc[i]
                text = page.get_text()
                if text.strip():
                    pages.append(f"--- Page {i} ---\n{text}")

            return "\n\n".join(pages) if pages else "(empty PDF)"
        finally:
            doc.close()

    @staticmethod
    def _extract_with_pdfminer(
        pdf_path: Path,
        max_pages: int,
        page_numbers: Optional[List[int]],
    ) -> str:
        """Extract text using pdfminer.six."""
        from pdfminer.high_level import extract_text  # type: ignore[import-untyped]

        page_numbers_param = page_numbers if page_numbers else (
            list(range(max_pages)) if max_pages > 0 else None
        )

        text = extract_text(
            str(pdf_path),
            page_numbers=page_numbers_param,
        )
        return text.strip() or "(empty PDF)"


# ===================================================================
# DataAnalysisTool
# ===================================================================


class DataAnalysisTool:
    """Pandas-based data analysis with optional chart generation.

    Requires ``pandas`` and optionally ``matplotlib`` / ``seaborn`` for
    chart output.

    Parameters
    ----------
    output_dir:
        Directory where generated charts are saved.  Defaults to a temp dir.
    """

    def __init__(self, output_dir: Optional[str] = None) -> None:
        self._output_dir = output_dir

    @property
    def defs(self) -> List[ToolDef]:
        return [
            ToolDef(
                name="DataAnalysis",
                description="Analyse data using pandas. Supports CSV / JSON / Excel input, summary stats, filtering, grouping, aggregation, and optional chart generation.",
                capabilities=["file"],
                sandbox_requirements={"timeout_seconds": 60},
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to data file (CSV, JSON, Excel)",
                        },
                        "operation": {
                            "type": "string",
                            "description": "Analysis operation: 'describe', 'head', 'info', 'value_counts', 'groupby', 'filter', 'correlation', or 'chart'",
                            "default": "describe",
                        },
                        "columns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Columns to operate on",
                        },
                        "group_by": {
                            "type": "string",
                            "description": "Column to group by (for 'groupby' operation)",
                        },
                        "agg_func": {
                            "type": "string",
                            "description": "Aggregation function: 'mean', 'sum', 'count', 'min', 'max' (default: 'mean')",
                            "default": "mean",
                        },
                        "filter_expr": {
                            "type": "string",
                            "description": "Filter expression, e.g. 'column > 5' (for 'filter' operation)",
                        },
                        "chart_type": {
                            "type": "string",
                            "description": "Chart type: 'bar', 'line', 'scatter', 'hist', 'box' (for 'chart' operation)",
                            "default": "bar",
                        },
                        "x_column": {
                            "type": "string",
                            "description": "X-axis column (for 'chart' operation)",
                        },
                        "y_column": {
                            "type": "string",
                            "description": "Y-axis column (for 'chart' operation)",
                        },
                    },
                    "required": ["path"],
                },
                handler=self.analyze,
            ),
        ]

    async def analyze(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute a data analysis operation.

        Kwargs
        ------
        path, operation, columns, group_by, agg_func, filter_expr,
        chart_type, x_column, y_column.
        """
        path = kwargs.get("path", "")
        if not path:
            return {"success": False, "error": "Missing required parameter: 'path'"}

        data_path = Path(path)
        if not data_path.exists():
            return {"success": False, "error": f"File not found: '{path}'"}

        operation = kwargs.get("operation", "describe")

        try:
            import pandas as pd
        except ImportError:
            return {
                "success": False,
                "error": "DataAnalysisTool requires 'pandas'. Install with: pip install pandas",
            }

        loop = asyncio.get_event_loop()
        try:
            df = await loop.run_in_executor(
                None, self._load_dataframe, data_path, pd
            )
        except Exception as exc:
            return {"success": False, "error": f"Failed to load data: {exc}"}

        try:
            if operation == "describe":
                result = self._op_describe(df, kwargs, pd)
            elif operation == "head":
                result = self._op_head(df, kwargs)
            elif operation == "info":
                result = self._op_info(df)
            elif operation == "value_counts":
                result = self._op_value_counts(df, kwargs)
            elif operation == "groupby":
                result = self._op_groupby(df, kwargs, pd)
            elif operation == "filter":
                result = self._op_filter(df, kwargs)
            elif operation == "correlation":
                result = self._op_correlation(df, pd)
            elif operation == "chart":
                result = await loop.run_in_executor(
                    None, self._op_chart, df, kwargs
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: '{operation}'",
                }
        except Exception as exc:
            return {"success": False, "error": f"Analysis failed: {exc}"}

        return result

    @staticmethod
    def _load_dataframe(path: Path, pd: Any) -> Any:
        """Load a dataframe from a file."""
        ext = path.suffix.lower()
        if ext == ".csv":
            return pd.read_csv(path)
        elif ext in (".json",):
            return pd.read_json(path)
        elif ext in (".xls", ".xlsx"):
            return pd.read_excel(path)
        elif ext == ".parquet":
            return pd.read_parquet(path)
        else:
            raise ValueError(f"Unsupported file format: '{ext}'. Supported: .csv, .json, .xls/.xlsx, .parquet")

    @staticmethod
    def _op_describe(df: Any, kwargs: Dict[str, Any], pd: Any) -> Dict[str, Any]:
        """Describe / summary statistics."""
        columns = kwargs.get("columns")
        if columns:
            available = [c for c in columns if c in df.columns]
            if not available:
                return {"success": False, "error": f"None of the specified columns exist in the data"}
            subset = df[available]
        else:
            subset = df

        desc = subset.describe(include="all").to_string()
        nulls = df.isnull().sum().to_dict()
        dtypes = df.dtypes.astype(str).to_dict()

        return {
            "success": True,
            "output": json.dumps({
                "shape": list(df.shape),
                "columns": list(df.columns),
                "dtypes": dtypes,
                "null_counts": {str(k): int(v) for k, v in nulls.items()},
                "statistics": desc,
            }, indent=2),
        }

    @staticmethod
    def _op_head(df: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Show first N rows."""
        n = kwargs.get("n", 10)
        columns = kwargs.get("columns")
        subset = df[columns] if columns else df
        return {
            "success": True,
            "output": subset.head(n).to_string(),
        }

    @staticmethod
    def _op_info(df: Any) -> Dict[str, Any]:
        """DataFrame info as string."""
        import io

        buf = io.StringIO()
        df.info(buf=buf)
        return {
            "success": True,
            "output": buf.getvalue(),
        }

    @staticmethod
    def _op_value_counts(df: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Value counts for a column."""
        columns = kwargs.get("columns", [])
        if not columns:
            return {"success": False, "error": "value_counts requires at least one column"}
        col = columns[0]
        if col not in df.columns:
            return {"success": False, "error": f"Column '{col}' not found"}
        return {
            "success": True,
            "output": df[col].value_counts().to_string(),
        }

    @staticmethod
    def _op_groupby(df: Any, kwargs: Dict[str, Any], pd: Any) -> Dict[str, Any]:
        """Group by a column and aggregate."""
        group_by = kwargs.get("group_by")
        if not group_by:
            return {"success": False, "error": "groupby requires 'group_by' parameter"}

        agg_func = kwargs.get("agg_func", "mean")
        columns = kwargs.get("columns")

        if columns:
            available = [c for c in columns if c in df.columns]
            grouped = df.groupby(group_by)[available].agg(agg_func)
        else:
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            grouped = df.groupby(group_by)[numeric_cols].agg(agg_func)

        return {
            "success": True,
            "output": grouped.to_string(),
        }

    @staticmethod
    def _op_filter(df: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Filter rows by expression."""
        expr = kwargs.get("filter_expr", "")
        if not expr:
            return {"success": False, "error": "filter requires 'filter_expr' parameter"}

        try:
            filtered = df.query(expr)
        except Exception as exc:
            return {"success": False, "error": f"Filter expression error: {exc}"}

        return {
            "success": True,
            "output": filtered.to_string(),
        }

    @staticmethod
    def _op_correlation(df: Any, pd: Any) -> Dict[str, Any]:
        """Correlation matrix for numeric columns."""
        numeric = df.select_dtypes(include=["number"])
        if numeric.empty:
            return {"success": False, "error": "No numeric columns for correlation"}
        corr = numeric.corr().to_string()
        return {
            "success": True,
            "output": corr,
        }

    def _op_chart(self, df: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a chart and return its file path."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return {
                "success": False,
                "error": "Chart generation requires 'matplotlib'. Install with: pip install matplotlib",
            }

        chart_type = kwargs.get("chart_type", "bar")
        x_col = kwargs.get("x_column", "")
        y_col = kwargs.get("y_column", "")

        if not x_col or x_col not in df.columns:
            return {"success": False, "error": f"x_column '{x_col}' not found in data"}
        if not y_col or y_col not in df.columns:
            return {"success": False, "error": f"y_column '{y_col}' not found in data"}

        fig, ax = plt.subplots(figsize=(10, 6))

        try:
            if chart_type == "bar":
                df.plot(kind="bar", x=x_col, y=y_col, ax=ax, legend=True)
            elif chart_type == "line":
                df.plot(kind="line", x=x_col, y=y_col, ax=ax, legend=True)
            elif chart_type == "scatter":
                df.plot(kind="scatter", x=x_col, y=y_col, ax=ax)
            elif chart_type == "hist":
                df[y_col].plot(kind="hist", ax=ax, bins=20)
                ax.set_xlabel(y_col)
            elif chart_type == "box":
                df[[y_col]].plot(kind="box", ax=ax)
            else:
                plt.close(fig)
                return {"success": False, "error": f"Unknown chart type: '{chart_type}'"}

            ax.set_title(f"{chart_type.capitalize()} chart: {y_col} by {x_col}")
            ax.tick_params(axis="x", rotation=45)

            output_dir = self._output_dir or tempfile.mkdtemp(prefix="lyra-chart-")
            os.makedirs(output_dir, exist_ok=True)
            chart_path = str(Path(output_dir) / f"chart_{uuid.uuid4().hex[:8]}.png")
            plt.tight_layout()
            plt.savefig(chart_path, dpi=150)
            plt.close(fig)

        except Exception as exc:
            plt.close(fig)
            return {"success": False, "error": f"Chart generation failed: {exc}"}

        return {
            "success": True,
            "output": json.dumps({
                "message": f"Chart saved to {chart_path}",
                "chart_path": chart_path,
                "chart_type": chart_type,
            }),
        }


# ===================================================================
# APICallTool
# ===================================================================


class APICallTool:
    """Make HTTP API calls with auth handling.

    Supports GET, POST, PUT, PATCH, DELETE methods, Bearer / Basic / API-Key
    authentication, custom headers, and JSON / form / raw body payloads.
    """

    @property
    def defs(self) -> List[ToolDef]:
        return [
            ToolDef(
                name="APICall",
                description="Make HTTP API calls with configurable authentication, custom headers, and JSON / form / raw body payloads.",
                capabilities=["network"],
                sandbox_requirements={"timeout_seconds": 30},
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Request URL",
                        },
                        "method": {
                            "type": "string",
                            "description": "HTTP method: GET, POST, PUT, PATCH, DELETE (default: GET)",
                            "default": "GET",
                            "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                        },
                        "headers": {
                            "type": "object",
                            "description": "Additional HTTP headers as key-value pairs",
                            "default": {},
                        },
                        "body": {
                            "type": "object",
                            "description": "Request body (for POST, PUT, PATCH). Sent as JSON unless content-type is overridden.",
                            "default": None,
                        },
                        "body_type": {
                            "type": "string",
                            "description": "Body encoding: 'json', 'form', or 'raw' (default: 'json')",
                            "default": "json",
                        },
                        "auth_type": {
                            "type": "string",
                            "description": "Authentication type: 'bearer', 'basic', 'api_key', or None",
                        },
                        "auth_token": {
                            "type": "string",
                            "description": "Token for 'bearer' auth, or password for 'basic' auth",
                        },
                        "auth_username": {
                            "type": "string",
                            "description": "Username for 'basic' auth",
                        },
                        "auth_key_name": {
                            "type": "string",
                            "description": "Header name for 'api_key' auth (default: X-API-Key)",
                            "default": "X-API-Key",
                        },
                        "auth_key_value": {
                            "type": "string",
                            "description": "Value for 'api_key' auth",
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Request timeout in seconds (default: 30)",
                            "default": 30,
                        },
                    },
                    "required": ["url"],
                },
                handler=self.call_api,
            ),
        ]

    async def call_api(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute an HTTP API call.

        Kwargs
        ------
        url, method, headers, body, body_type, auth_type,
        auth_token, auth_username, auth_key_name, auth_key_value, timeout.
        """
        url = kwargs.get("url", "")
        if not url:
            return {"success": False, "error": "Missing required parameter: 'url'"}

        method = kwargs.get("method", "GET").upper()
        headers = dict(kwargs.get("headers", {}) or {})
        body = kwargs.get("body")
        body_type = kwargs.get("body_type", "json")
        timeout = float(kwargs.get("timeout", 30))

        # Apply authentication
        auth_type = kwargs.get("auth_type")
        if auth_type:
            auth_error = self._apply_auth(headers, kwargs)
            if auth_error:
                return {"success": False, "error": auth_error}

        try:
            import aiohttp
        except ImportError:
            return {"success": False, "error": "APICallTool requires 'aiohttp'"}

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                func = getattr(session, method.lower(), None)
                if func is None:
                    return {"success": False, "error": f"Unsupported HTTP method: '{method}'"}

                # Build request
                request_kwargs: Dict[str, Any] = {}
                if body is not None and method in ("POST", "PUT", "PATCH"):
                    if body_type == "json":
                        request_kwargs["json"] = body
                    elif body_type == "form":
                        request_kwargs["data"] = body
                    elif body_type == "raw":
                        import json as _json

                        request_kwargs["data"] = _json.dumps(body)
                        request_kwargs.setdefault("headers", {})["Content-Type"] = "text/plain"
                    else:
                        return {"success": False, "error": f"Unknown body_type: '{body_type}'"}

                async with func(
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    **request_kwargs,
                ) as resp:
                    status = resp.status
                    try:
                        resp_body = await resp.json()
                        body_str = json.dumps(resp_body, indent=2, default=str)
                        body_type = "json"
                    except Exception:
                        resp_text = await resp.text()
                        body_str = resp_text[:50000]  # limit response body
                        body_type = "text"

            return {
                "success": 200 <= status < 300,
                "output": json.dumps({
                    "status": status,
                    "body": body_str,
                    "body_type": body_type,
                }, indent=2),
                "error": None if 200 <= status < 300 else f"HTTP {status}",
            }

        except asyncio.TimeoutError:
            return {"success": False, "error": f"API call timed out after {timeout}s"}
        except aiohttp.ClientError as exc:
            return {"success": False, "error": f"API request failed: {exc}"}
        except Exception as exc:
            return {"success": False, "error": f"API call error: {exc}"}

    @staticmethod
    def _apply_auth(headers: Dict[str, str], kwargs: Dict[str, Any]) -> Optional[str]:
        """Apply authentication headers in-place.

        Returns an error string on misconfiguration, or None on success.
        """
        auth_type = kwargs.get("auth_type", "").lower()

        if auth_type == "bearer":
            token = kwargs.get("auth_token", "")
            if not token:
                return "Bearer auth requires 'auth_token'"
            headers["Authorization"] = f"Bearer {token}"

        elif auth_type == "basic":
            username = kwargs.get("auth_username", "")
            token = kwargs.get("auth_token", "")
            if not username or not token:
                return "Basic auth requires 'auth_username' and 'auth_token'"
            import base64

            credentials = f"{username}:{token}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        elif auth_type == "api_key":
            key_name = kwargs.get("auth_key_name", "X-API-Key")
            key_value = kwargs.get("auth_key_value", "")
            if not key_value:
                return "API key auth requires 'auth_key_value'"
            headers[key_name] = key_value

        elif auth_type:
            return f"Unknown auth_type: '{auth_type}'"

        return None
