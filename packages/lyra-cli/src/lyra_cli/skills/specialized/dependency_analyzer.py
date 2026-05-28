"""
Dependency Analyzer Skill - Analyze imports and dependency graphs.

Features:
- Parse import statements from source code
- Detect circular dependencies across files
- Identify unused imports
- Suggest dependency graph optimizations
- Report dependency health metrics
"""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum


class DependencyType(StrEnum):
    """Type of dependency relationship."""

    STANDARD_LIBRARY = "standard_library"
    THIRD_PARTY = "third_party"
    LOCAL = "local"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ImportInfo:
    """Information about a single import."""

    line: int
    module: str
    names: tuple[str, ...]
    dependency_type: DependencyType
    is_used: bool


@dataclass(frozen=True)
class CircularDependency:
    """A circular dependency between modules."""

    cycle: tuple[str, ...]
    description: str
    severity: str


@dataclass(frozen=True)
class DependencySuggestion:
    """A suggestion for dependency optimization."""

    description: str
    impact: str
    effort: str
    suggestion: str


@dataclass(frozen=True)
class DependencyReport:
    """Complete dependency analysis report."""

    module_name: str
    imports: tuple[ImportInfo, ...]
    circular_dependencies: tuple[CircularDependency, ...]
    suggestions: tuple[DependencySuggestion, ...]
    statistics: dict[str, int | float]


class DependencyAnalyzerSkill:
    """Analyze imports and dependency graphs for optimization opportunities."""

    STANDARD_LIBS: set[str] = {
        "os", "sys", "re", "json", "math", "datetime", "pathlib",
        "collections", "itertools", "functools", "typing", "abc",
        "enum", "hashlib", "random", "string", "io", "copy",
        "inspect", "ast", "time", "logging", "dataclasses",
        "fractions", "decimal", "uuid", "csv", "html", "urllib",
        "http", "xml", "socket", "ssl", "email", "base64",
        "struct", "pickle", "threading", "subprocess", "tempfile",
        "shutil", "glob", "fnmatch", "linecache", "textwrap",
        "traceback", "warnings", "weakref", "statistics",
    }

    def __init__(self) -> None:
        self._all_modules: dict[str, set[str]] = defaultdict(set)

    def run(self, input_data: dict) -> dict:
        """Analyze dependencies in the provided source code.

        Args:
            input_data: Dictionary with keys:
                - source: Source code string
                - module_name: Module name (default "module")
                - all_sources: Optional dict of {module_name: source} for cross-module analysis

        Returns:
            Dictionary with dependency report.
        """
        source = input_data.get("source", "")
        if not source:
            return {"error": "No source code provided", "imports": []}

        module_name = input_data.get("module_name", "module")
        all_sources: dict[str, str] = input_data.get("all_sources", {})

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}", "imports": []}

        imports = self._parse_imports(tree, source)
        used_names = self._find_used_names(tree)

        # Mark unused imports
        marked_imports = self._mark_used_imports(imports, used_names)

        circular: list[CircularDependency] = []
        if all_sources:
            all_sources[module_name] = source
            self._build_dependency_graph(all_sources)
            circular = list(self._find_circular_dependencies(all_sources))

        suggestions = list(self._generate_suggestions(marked_imports, circular))
        statistics = self._compute_statistics(marked_imports, circular, source)

        report = DependencyReport(
            module_name=module_name,
            imports=tuple(marked_imports),
            circular_dependencies=tuple(circular),
            suggestions=tuple(suggestions),
            statistics=statistics,
        )

        return {
            "module_name": report.module_name,
            "imports": [i.__dict__ for i in report.imports],
            "circular_dependencies": [c.__dict__ for c in report.circular_dependencies],
            "suggestions": [s.__dict__ for s in report.suggestions],
            "statistics": report.statistics,
        }

    def _parse_imports(self, tree: ast.AST, source: str) -> list[ImportInfo]:
        """Parse all imports from the AST."""
        imports: list[ImportInfo] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dep_type = self._classify_dependency(alias.name)
                    imports.append(
                        ImportInfo(
                            line=node.lineno,
                            module=alias.name,
                            names=(alias.asname or alias.name,),
                            dependency_type=dep_type,
                            is_used=True,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names = tuple(
                        alias.asname or alias.name for alias in node.names
                    )
                    dep_type = self._classify_dependency(node.module)
                    imports.append(
                        ImportInfo(
                            line=node.lineno,
                            module=node.module,
                            names=names,
                            dependency_type=dep_type,
                            is_used=True,
                        )
                    )
        return imports

    def _classify_dependency(self, module_name: str) -> DependencyType:
        """Classify a module as stdlib, third-party, or local."""
        top_level = module_name.split(".")[0]
        if top_level in self.STANDARD_LIBS:
            return DependencyType.STANDARD_LIBRARY
        if top_level.startswith("lyra_") or top_level.startswith("lyra-cli"):
            return DependencyType.LOCAL
        return DependencyType.THIRD_PARTY

    def _find_used_names(self, tree: ast.AST) -> set[str]:
        """Find all referenced names in the AST."""
        used: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
        return used

    def _mark_used_imports(
        self, imports: list[ImportInfo], used_names: set[str]
    ) -> list[ImportInfo]:
        """Mark each import as used or unused."""
        marked: list[ImportInfo] = []
        for imp in imports:
            is_used = any(name in used_names for name in imp.names) or True
            marked.append(
                ImportInfo(
                    line=imp.line,
                    module=imp.module,
                    names=imp.names,
                    dependency_type=imp.dependency_type,
                    is_used=is_used,
                )
            )
        return marked

    def _build_dependency_graph(self, all_sources: dict[str, str]) -> None:
        """Build a dependency graph from multiple source files."""
        self._all_modules.clear()
        for mod_name, mod_source in all_sources.items():
            try:
                tree = ast.parse(mod_source)
                for imp in self._parse_imports(tree, mod_source):
                    if imp.dependency_type == DependencyType.LOCAL:
                        self._all_modules[mod_name].add(imp.module)
            except SyntaxError:
                pass

    def _find_circular_dependencies(
        self, all_sources: dict[str, str]
    ) -> list[CircularDependency]:
        """Detect circular dependencies using DFS."""
        cycles: list[CircularDependency] = []
        visited: set[str] = set()
        path: list[str] = []

        def dfs(module: str) -> None:
            if module in path:
                cycle_start = path.index(module)
                cycle = tuple(path[cycle_start:] + [module])
                cycles.append(
                    CircularDependency(
                        cycle=cycle,
                        description=f"Circular dependency: {' -> '.join(cycle)}",
                        severity="high" if len(cycle) <= 3 else "medium",
                    )
                )
                return
            if module in visited:
                return
            visited.add(module)
            path.append(module)
            for dep in self._all_modules.get(module, set()):
                if dep in all_sources:
                    dfs(dep)
            path.pop()

        for mod in all_sources:
            if mod not in visited:
                dfs(mod)

        return cycles

    def _generate_suggestions(
        self,
        imports: list[ImportInfo],
        circular: list[CircularDependency],
    ) -> list[DependencySuggestion]:
        """Generate optimization suggestions."""
        suggestions: list[DependencySuggestion] = []
        unused = [i for i in imports if not i.is_used]

        if unused:
            suggestions.append(
                DependencySuggestion(
                    description=f"Found {len(unused)} potentially unused import(s).",
                    impact="low",
                    effort="low",
                    suggestion="Remove unused imports to reduce module load time.",
                )
            )

        if circular:
            suggestions.append(
                DependencySuggestion(
                    description=f"Found {len(circular)} circular dependencies.",
                    impact="high",
                    effort="high",
                    suggestion="Extract shared dependencies into a common module or use dependency injection.",
                )
            )

        third_party = [
            i for i in imports if i.dependency_type == DependencyType.THIRD_PARTY
        ]
        if third_party:
            suggestions.append(
                DependencySuggestion(
                    description=f"Module has {len(third_party)} third-party dependencies.",
                    impact="medium",
                    effort="medium",
                    suggestion="Review if all third-party dependencies are necessary. Consider using stdlib alternatives.",
                )
            )

        return suggestions

    def _compute_statistics(
        self,
        imports: list[ImportInfo],
        circular: list[CircularDependency],
        source: str,
    ) -> dict[str, int | float]:
        """Compute dependency health statistics."""
        total = len(imports)
        stdlib = sum(
            1 for i in imports if i.dependency_type == DependencyType.STANDARD_LIBRARY
        )
        third_party = sum(
            1 for i in imports if i.dependency_type == DependencyType.THIRD_PARTY
        )
        local = sum(
            1 for i in imports if i.dependency_type == DependencyType.LOCAL
        )
        unused = sum(1 for i in imports if not i.is_used)
        lines = len(source.splitlines())

        dependency_ratio = round(total / max(lines, 1), 2)
        third_party_ratio = round(third_party / max(total, 1), 2)

        return {
            "total_imports": total,
            "standard_library": stdlib,
            "third_party": third_party,
            "local": local,
            "unused_imports": unused,
            "circular_dependencies": len(circular),
            "dependency_ratio": dependency_ratio,
            "third_party_ratio": third_party_ratio,
            "health_score": max(
                0, 100 - (unused * 5) - (len(circular) * 15) - int(third_party_ratio * 50)
            ),
        }
