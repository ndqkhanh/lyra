"""Pre-index codebases into queryable knowledge graphs.

Scans directory structures, extracts symbols (functions, classes, imports),
builds dependency graphs, and indexes file contents for search.
Supports framework-aware routing (Python: functions/classes/imports).
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SymbolEntry:
    """A code symbol extracted from a file."""
    name: str
    symbol_type: str
    file_path: str
    line_number: int
    docstring: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "symbol_type": self.symbol_type,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "docstring": self.docstring,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class DependencyEntry:
    """A dependency between two code symbols or files."""
    source_path: str
    target_path: str
    dependency_type: str = "import"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "target_path": self.target_path,
            "dependency_type": self.dependency_type,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class FileIndex:
    """Indexed content of a single file."""
    file_path: str
    symbols: tuple[SymbolEntry, ...] = ()
    dependencies: tuple[DependencyEntry, ...] = ()
    content_hash: str = ""
    lines: int = 0


class PreIndexer:
    """Index codebases into queryable knowledge graph structures.

    Supports framework-aware routing for Python, JavaScript/TypeScript,
    and generic code files.
    """

    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
        ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
        ".rb", ".php", ".swift", ".kt", ".scala", ".c", ".cpp", ".h",
        ".hpp", ".cs", ".sh", ".bash", ".zsh", ".yaml", ".yml",
        ".json", ".toml", ".cfg", ".ini",
    })

    def __init__(self, project_root: str = ".") -> None:
        self.project_root = os.path.abspath(project_root)
        self._file_indices: dict[str, FileIndex] = {}
        self._symbols: list[SymbolEntry] = []
        self._dependencies: list[DependencyEntry] = []

    # ── Directory Scanning ─────────────────────────────────────────────────

    def index_directory(self, path: str | None = None,
                        exclude_dirs: frozenset[str] | None = None) -> PreIndexer:
        """Scan a directory and index all supported files. Returns self for chaining."""
        scan_path = os.path.join(self.project_root, path) if path else self.project_root
        excludes = exclude_dirs or frozenset({
            "__pycache__", ".git", ".hg", ".svn", "node_modules",
            ".venv", "venv", "env", ".tox", "dist", "build",
            ".next", ".nuxt", ".output", ".idea", ".vscode",
            ".coverage", "htmlcov", ".benchmarks", ".deepeval",
            ".pytest_cache", ".mypy_cache", ".ruff_cache",
            "*.egg-info", ".omc", ".claude",
        })

        result: PreIndexer = self
        for root, dirs, files in os.walk(scan_path):
            dirs[:] = [d for d in dirs if d not in excludes]
            for filename in files:
                _, ext = os.path.splitext(filename)
                if ext.lower() not in self.SUPPORTED_EXTENSIONS:
                    continue
                file_path = os.path.join(root, filename)
                try:
                    result = result.index_file(file_path)
                except (OSError, SyntaxError, ValueError):
                    continue

        return result

    def index_file(self, file_path: str) -> PreIndexer:
        """Index a single file, extracting symbols and dependencies.

        Returns a new PreIndexer with the updated indices.
        """
        abs_path = os.path.abspath(file_path)
        if not os.path.isfile(abs_path):
            from .exceptions import IndexingError
            raise IndexingError(abs_path, "File does not exist")

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as e:
            from .exceptions import IndexingError
            raise IndexingError(abs_path, str(e))

        content_hash = str(hash(content))
        lines = content.count("\n") + 1

        symbols: list[SymbolEntry] = []
        dependencies: list[DependencyEntry] = []
        ext = os.path.splitext(abs_path)[1].lower()

        if ext == ".py":
            py_symbols, py_deps = self._extract_python(abs_path, content)
            symbols.extend(py_symbols)
            dependencies.extend(py_deps)
        elif ext in {".js", ".ts", ".jsx", ".tsx"}:
            js_symbols, js_deps = self._extract_js_ts(abs_path, content)
            symbols.extend(js_symbols)
            dependencies.extend(js_deps)
        else:
            generic_symbols = self._extract_generic(abs_path, content)
            symbols.extend(generic_symbols)

        rel_path = os.path.relpath(abs_path, self.project_root)
        new_file_indices = dict(self._file_indices)
        new_file_indices[rel_path] = FileIndex(
            file_path=rel_path,
            symbols=tuple(symbols),
            dependencies=tuple(dependencies),
            content_hash=content_hash,
            lines=lines,
        )

        new_symbols = list(self._symbols)
        new_symbols.extend(symbols)
        new_deps = list(self._dependencies)
        new_deps.extend(dependencies)

        result = PreIndexer.__new__(PreIndexer)
        result.project_root = self.project_root
        result._file_indices = new_file_indices
        result._symbols = new_symbols
        result._dependencies = new_deps
        return result

    # ── Python Extraction ──────────────────────────────────────────────────

    def _extract_python(self, file_path: str,
                        content: str) -> tuple[list[SymbolEntry], list[DependencyEntry]]:
        """Extract symbols and deps from Python files using AST."""
        symbols: list[SymbolEntry] = []
        deps: list[DependencyEntry] = []

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            return symbols, deps

        rel_path = os.path.relpath(file_path, self.project_root)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                doc = ast.get_docstring(node) or ""
                symbols.append(SymbolEntry(
                    name=node.name,
                    symbol_type="function",
                    file_path=rel_path,
                    line_number=node.lineno,
                    docstring=doc,
                    metadata={"decorators": [d.id for d in node.decorator_list
                                             if isinstance(d, ast.Name)]},
                ))
            elif isinstance(node, ast.AsyncFunctionDef):
                doc = ast.get_docstring(node) or ""
                symbols.append(SymbolEntry(
                    name=node.name,
                    symbol_type="async_function",
                    file_path=rel_path,
                    line_number=node.lineno,
                    docstring=doc,
                ))
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or ""
                bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                symbols.append(SymbolEntry(
                    name=node.name,
                    symbol_type="class",
                    file_path=rel_path,
                    line_number=node.lineno,
                    docstring=doc,
                    metadata={"bases": bases},
                ))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    deps.append(DependencyEntry(
                        source_path=rel_path,
                        target_path=alias.name.replace(".", "/") + ".py",
                        dependency_type="import",
                    ))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    target = module.replace(".", "/") + ".py"
                    deps.append(DependencyEntry(
                        source_path=rel_path,
                        target_path=target,
                        dependency_type="import",
                        metadata={"name": alias.name},
                    ))

        return symbols, deps

    # ── JS/TS Extraction ───────────────────────────────────────────────────

    def _extract_js_ts(self, file_path: str,
                       content: str) -> tuple[list[SymbolEntry], list[DependencyEntry]]:
        """Extract symbols and deps from JS/TS files using regex."""
        symbols: list[SymbolEntry] = []
        deps: list[DependencyEntry] = []
        rel_path = os.path.relpath(file_path, self.project_root)

        # Function declarations
        for match in re.finditer(
            r'(?:export\s+)?(?:async\s+)?function\s+(\w+)',
            content
        ):
            symbols.append(SymbolEntry(
                name=match.group(1),
                symbol_type="function",
                file_path=rel_path,
                line_number=content[:match.start()].count("\n") + 1,
            ))

        # Arrow functions assigned to const/let
        for match in re.finditer(
            r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(?.*?\)?\s*=>',
            content
        ):
            symbols.append(SymbolEntry(
                name=match.group(1),
                symbol_type="arrow_function",
                file_path=rel_path,
                line_number=content[:match.start()].count("\n") + 1,
            ))

        # Class declarations
        for match in re.finditer(
            r'(?:export\s+)?class\s+(\w+)',
            content
        ):
            symbols.append(SymbolEntry(
                name=match.group(1),
                symbol_type="class",
                file_path=rel_path,
                line_number=content[:match.start()].count("\n") + 1,
            ))

        # Imports
        for match in re.finditer(
            r"(?:import\s+(?:\w+\s*,?\s*)?\{?\s*[\w\s,]+\}?\s*from\s+['\"])([^'\"]+)",
            content
        ):
            deps.append(DependencyEntry(
                source_path=rel_path,
                target_path=match.group(1),
                dependency_type="import",
            ))

        return symbols, deps

    # ── Generic Extraction ─────────────────────────────────────────────────

    def _extract_generic(self, file_path: str,
                         content: str) -> list[SymbolEntry]:
        """Extract basic symbols from generic files."""
        symbols: list[SymbolEntry] = []
        rel_path = os.path.relpath(file_path, self.project_root)

        for match in re.finditer(r'^(?:def|fn|func|fun)\s+(\w+)', content, re.MULTILINE):
            symbols.append(SymbolEntry(
                name=match.group(1),
                symbol_type="function",
                file_path=rel_path,
                line_number=content[:match.start()].count("\n") + 1,
            ))

        for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
            symbols.append(SymbolEntry(
                name=match.group(1),
                symbol_type="class",
                file_path=rel_path,
                line_number=content[:match.start()].count("\n") + 1,
            ))

        return symbols

    # ── Graph Building ─────────────────────────────────────────────────────

    def build_dependency_graph(self) -> dict[str, dict[str, list[str]]]:
        """Build a dependency graph: for each file, list its deps and dependents."""
        deps_out: dict[str, set[str]] = {}
        for dep in self._dependencies:
            deps_out.setdefault(dep.source_path, set()).add(dep.target_path)

        deps_in: dict[str, set[str]] = {}
        for dep in self._dependencies:
            deps_in.setdefault(dep.target_path, set()).add(dep.source_path)

        return {
            "dependencies": {k: sorted(v) for k, v in deps_out.items()},
            "dependents": {k: sorted(v) for k, v in deps_in.items()},
        }

    def to_graph(self, graph: Any) -> Any:
        """Import indexed symbols and files into a KnowledgeGraph."""
        from .graph_builder import KnowledgeNode, KnowledgeEdge, NodeType, EdgeRelation

        result = graph
        for idx in self._file_indices.values():
            file_node = KnowledgeNode(
                node_id=f"file:{idx.file_path}",
                node_type=NodeType.SOURCE,
                label=os.path.basename(idx.file_path),
                properties={
                    "file_path": idx.file_path,
                    "lines": idx.lines,
                },
            )
            result = result.add_node(file_node)

            for sym in idx.symbols:
                sym_id = f"sym:{sym.file_path}:{sym.name}"
                sym_node = KnowledgeNode(
                    node_id=sym_id,
                    node_type=NodeType.CONCEPT,
                    label=sym.name,
                    properties={
                        "symbol_type": sym.symbol_type,
                        "file_path": sym.file_path,
                        "line_number": sym.line_number,
                        "docstring": sym.docstring[:200],
                    },
                )
                result = result.add_node(sym_node)
                result = result.add_edge(KnowledgeEdge(
                    edge_id=f"defines:{sym_id}",
                    source_id=f"file:{idx.file_path}",
                    target_id=sym_id,
                    relation=EdgeRelation.DEPENDS_ON,
                    label="defines",
                ))

        return result

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def file_indices(self) -> dict[str, FileIndex]:
        return dict(self._file_indices)

    @property
    def symbols(self) -> list[SymbolEntry]:
        return list(self._symbols)

    @property
    def dependencies(self) -> list[DependencyEntry]:
        return list(self._dependencies)

    @property
    def indexed_files_count(self) -> int:
        return len(self._file_indices)

    def find_symbol(self, name: str) -> list[SymbolEntry]:
        """Find all symbols matching a name."""
        return [s for s in self._symbols if s.name == name]
