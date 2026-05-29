"""ECC Integration - External Code Context.

Provides deep repository analysis, dependency tracking, and impact analysis
for better code understanding and decision making.

Features:
- Repository structure analysis
- Dependency graph construction
- Impact analysis (blast radius)
- Code relationship mapping
- Cross-file references
- Symbol resolution

Usage:
    ecc = ECCEngine(repo_path)
    context = ecc.analyze_repository()
    impact = ecc.analyze_impact(file_path)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DependencyType(Enum):
    """Types of dependencies."""

    IMPORT = "import"
    INHERITANCE = "inheritance"
    COMPOSITION = "composition"
    CALL = "call"
    REFERENCE = "reference"


class SymbolType(Enum):
    """Types of symbols."""

    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    MODULE = "module"


@dataclass
class Symbol:
    """A code symbol."""

    name: str
    type: SymbolType
    file_path: str
    line_number: int
    definition: str = ""
    docstring: str | None = None
    references: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class Dependency:
    """A dependency between code elements."""

    source: str
    target: str
    type: DependencyType
    file_path: str
    line_number: int


@dataclass
class ImpactAnalysis:
    """Impact analysis result."""

    target_file: str
    direct_dependents: list[str]
    indirect_dependents: list[str]
    affected_symbols: list[Symbol]
    risk_level: str  # "low", "medium", "high"
    blast_radius: int


@dataclass
class RepositoryContext:
    """Repository context information."""

    root_path: Path
    total_files: int
    total_lines: int
    languages: dict[str, int]
    symbols: list[Symbol]
    dependencies: list[Dependency]
    entry_points: list[str]


class PythonAnalyzer:
    """
    Analyzes Python code for symbols and dependencies.

    Features:
    - AST-based analysis
    - Symbol extraction
    - Dependency detection
    - Cross-reference tracking
    """

    def __init__(self):
        """Initialize the Python analyzer."""
        self.symbols: dict[str, Symbol] = {}
        self.dependencies: list[Dependency] = []

    def analyze_file(self, file_path: Path) -> tuple[list[Symbol], list[Dependency]]:
        """Analyze a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (symbols, dependencies)
        """
        try:
            with open(file_path, encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            symbols = self._extract_symbols(tree, file_path)
            dependencies = self._extract_dependencies(tree, file_path)

            return symbols, dependencies
        except Exception:
            # Handle parse errors gracefully
            return [], []

    def _extract_symbols(self, tree: ast.AST, file_path: Path) -> list[Symbol]:
        """Extract symbols from AST.

        Args:
            tree: AST tree
            file_path: File path

        Returns:
            List of symbols
        """
        symbols = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                symbol = Symbol(
                    name=node.name,
                    type=SymbolType.CLASS,
                    file_path=str(file_path),
                    line_number=node.lineno,
                    docstring=ast.get_docstring(node),
                )
                symbols.append(symbol)

            elif isinstance(node, ast.FunctionDef):
                # Determine if method or function
                is_method = any(
                    isinstance(parent, ast.ClassDef)
                    for parent in ast.walk(tree)
                    if hasattr(parent, 'body') and node in parent.body
                )

                symbol = Symbol(
                    name=node.name,
                    type=SymbolType.METHOD if is_method else SymbolType.FUNCTION,
                    file_path=str(file_path),
                    line_number=node.lineno,
                    docstring=ast.get_docstring(node),
                )
                symbols.append(symbol)

        return symbols

    def _extract_dependencies(self, tree: ast.AST, file_path: Path) -> list[Dependency]:
        """Extract dependencies from AST.

        Args:
            tree: AST tree
            file_path: File path

        Returns:
            List of dependencies
        """
        dependencies = []

        for node in ast.walk(tree):
            # Import dependencies
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dep = Dependency(
                        source=str(file_path),
                        target=alias.name,
                        type=DependencyType.IMPORT,
                        file_path=str(file_path),
                        line_number=node.lineno,
                    )
                    dependencies.append(dep)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    dep = Dependency(
                        source=str(file_path),
                        target=node.module,
                        type=DependencyType.IMPORT,
                        file_path=str(file_path),
                        line_number=node.lineno,
                    )
                    dependencies.append(dep)

            # Inheritance dependencies
            elif isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        dep = Dependency(
                            source=node.name,
                            target=base.id,
                            type=DependencyType.INHERITANCE,
                            file_path=str(file_path),
                            line_number=node.lineno,
                        )
                        dependencies.append(dep)

        return dependencies


class DependencyGraph:
    """
    Builds and analyzes dependency graphs.

    Features:
    - Graph construction
    - Cycle detection
    - Path finding
    - Impact analysis
    """

    def __init__(self):
        """Initialize the dependency graph."""
        self.nodes: set[str] = set()
        self.edges: dict[str, set[str]] = {}
        self.reverse_edges: dict[str, set[str]] = {}

    def add_dependency(self, source: str, target: str) -> None:
        """Add a dependency edge.

        Args:
            source: Source node
            target: Target node
        """
        self.nodes.add(source)
        self.nodes.add(target)

        if source not in self.edges:
            self.edges[source] = set()
        self.edges[source].add(target)

        if target not in self.reverse_edges:
            self.reverse_edges[target] = set()
        self.reverse_edges[target].add(source)

    def get_dependents(self, node: str, max_depth: int = -1) -> set[str]:
        """Get all nodes that depend on this node.

        Args:
            node: Node to analyze
            max_depth: Maximum depth (-1 for unlimited)

        Returns:
            Set of dependent nodes
        """
        dependents = set()
        visited = set()
        queue = [(node, 0)]

        while queue:
            current, depth = queue.pop(0)

            if current in visited:
                continue

            visited.add(current)

            if current != node:
                dependents.add(current)

            if max_depth != -1 and depth >= max_depth:
                continue

            if current in self.reverse_edges:
                for dependent in self.reverse_edges[current]:
                    if dependent not in visited:
                        queue.append((dependent, depth + 1))

        return dependents

    def get_dependencies(self, node: str, max_depth: int = -1) -> set[str]:
        """Get all nodes this node depends on.

        Args:
            node: Node to analyze
            max_depth: Maximum depth (-1 for unlimited)

        Returns:
            Set of dependency nodes
        """
        dependencies = set()
        visited = set()
        queue = [(node, 0)]

        while queue:
            current, depth = queue.pop(0)

            if current in visited:
                continue

            visited.add(current)

            if current != node:
                dependencies.add(current)

            if max_depth != -1 and depth >= max_depth:
                continue

            if current in self.edges:
                for dependency in self.edges[current]:
                    if dependency not in visited:
                        queue.append((dependency, depth + 1))

        return dependencies

    def detect_cycles(self) -> list[list[str]]:
        """Detect cycles in the graph.

        Returns:
            List of cycles (each cycle is a list of nodes)
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            if node in self.edges:
                for neighbor in self.edges[node]:
                    if neighbor not in visited:
                        dfs(neighbor, path.copy())
                    elif neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(neighbor)
                        cycle = path[cycle_start:] + [neighbor]
                        cycles.append(cycle)

            rec_stack.remove(node)

        for node in self.nodes:
            if node not in visited:
                dfs(node, [])

        return cycles


class ECCEngine:
    """
    Main engine for External Code Context.

    Provides repository analysis, dependency tracking, and impact analysis.
    """

    def __init__(self, repo_path: Path):
        """Initialize the ECC engine.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = repo_path
        self.analyzer = PythonAnalyzer()
        self.graph = DependencyGraph()
        self.symbols: dict[str, Symbol] = {}
        self.context: RepositoryContext | None = None

    def analyze_repository(self) -> RepositoryContext:
        """Analyze the entire repository.

        Returns:
            Repository context
        """
        all_symbols = []
        all_dependencies = []
        total_files = 0
        total_lines = 0
        languages = {}

        # Find all Python files
        python_files = list(self.repo_path.rglob("*.py"))

        for file_path in python_files:
            # Skip virtual environments and caches
            if any(part in file_path.parts for part in ['.venv', 'venv', '__pycache__', '.git']):
                continue

            total_files += 1

            # Count lines
            try:
                with open(file_path, encoding='utf-8') as f:
                    lines = len(f.readlines())
                    total_lines += lines
            except Exception:
                pass

            # Analyze file
            symbols, dependencies = self.analyzer.analyze_file(file_path)
            all_symbols.extend(symbols)
            all_dependencies.extend(dependencies)

            # Build dependency graph
            for dep in dependencies:
                self.graph.add_dependency(dep.source, dep.target)

        # Store symbols
        for symbol in all_symbols:
            key = f"{symbol.file_path}:{symbol.name}"
            self.symbols[key] = symbol

        # Detect entry points (files with __main__)
        entry_points = []
        for file_path in python_files:
            try:
                with open(file_path, encoding='utf-8') as f:
                    content = f.read()
                    if '__main__' in content:
                        entry_points.append(str(file_path))
            except Exception:
                pass

        languages['python'] = total_files

        self.context = RepositoryContext(
            root_path=self.repo_path,
            total_files=total_files,
            total_lines=total_lines,
            languages=languages,
            symbols=all_symbols,
            dependencies=all_dependencies,
            entry_points=entry_points,
        )

        return self.context

    def analyze_impact(self, file_path: str) -> ImpactAnalysis:
        """Analyze impact of changes to a file.

        Args:
            file_path: Path to file

        Returns:
            Impact analysis
        """
        # Get direct dependents
        direct = self.graph.get_dependents(file_path, max_depth=1)

        # Get all dependents
        all_dependents = self.graph.get_dependents(file_path)
        indirect = all_dependents - direct

        # Calculate blast radius
        blast_radius = len(all_dependents)

        # Determine risk level
        if blast_radius == 0:
            risk_level = "low"
        elif blast_radius < 5:
            risk_level = "low"
        elif blast_radius < 20:
            risk_level = "medium"
        else:
            risk_level = "high"

        # Find affected symbols
        affected_symbols = [
            symbol for symbol in self.symbols.values()
            if symbol.file_path == file_path
        ]

        return ImpactAnalysis(
            target_file=file_path,
            direct_dependents=list(direct),
            indirect_dependents=list(indirect),
            affected_symbols=affected_symbols,
            risk_level=risk_level,
            blast_radius=blast_radius,
        )

    def find_symbol(self, name: str) -> list[Symbol]:
        """Find symbols by name.

        Args:
            name: Symbol name

        Returns:
            List of matching symbols
        """
        return [
            symbol for symbol in self.symbols.values()
            if symbol.name == name
        ]

    def get_symbol_references(self, symbol: Symbol) -> list[tuple[str, int]]:
        """Get all references to a symbol.

        Args:
            symbol: Symbol to find references for

        Returns:
            List of (file_path, line_number) tuples
        """
        return symbol.references


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "DependencyType",
    "SymbolType",
    "Symbol",
    "Dependency",
    "ImpactAnalysis",
    "RepositoryContext",
    "PythonAnalyzer",
    "DependencyGraph",
    "ECCEngine",
]
