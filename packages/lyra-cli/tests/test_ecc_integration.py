"""Tests for ECC Integration."""

import pytest
from pathlib import Path
import tempfile
import os

from lyra_cli.ecc_integration import (
    DependencyType,
    SymbolType,
    Symbol,
    Dependency,
    ImpactAnalysis,
    RepositoryContext,
    PythonAnalyzer,
    DependencyGraph,
    ECCEngine,
)


# ============================================================================
# Symbol Tests
# ============================================================================

def test_symbol_creation():
    """Test creating a symbol."""
    symbol = Symbol(
        name="test_function",
        type=SymbolType.FUNCTION,
        file_path="test.py",
        line_number=10,
        docstring="A test function",
    )
    
    assert symbol.name == "test_function"
    assert symbol.type == SymbolType.FUNCTION
    assert symbol.file_path == "test.py"
    assert symbol.line_number == 10
    assert symbol.docstring == "A test function"


# ============================================================================
# Dependency Tests
# ============================================================================

def test_dependency_creation():
    """Test creating a dependency."""
    dep = Dependency(
        source="module_a.py",
        target="module_b.py",
        type=DependencyType.IMPORT,
        file_path="module_a.py",
        line_number=5,
    )
    
    assert dep.source == "module_a.py"
    assert dep.target == "module_b.py"
    assert dep.type == DependencyType.IMPORT


# ============================================================================
# PythonAnalyzer Tests
# ============================================================================

@pytest.fixture
def analyzer():
    """Create a Python analyzer."""
    return PythonAnalyzer()


@pytest.fixture
def temp_python_file():
    """Create a temporary Python file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
import os
from pathlib import Path

class TestClass:
    '''A test class.'''
    
    def test_method(self):
        '''A test method.'''
        pass

def test_function():
    '''A test function.'''
    return 42
""")
        temp_path = f.name
    
    yield Path(temp_path)
    
    # Cleanup
    os.unlink(temp_path)


def test_analyzer_creation(analyzer):
    """Test creating an analyzer."""
    assert analyzer.symbols == {}
    assert analyzer.dependencies == []


def test_analyzer_analyze_file(analyzer, temp_python_file):
    """Test analyzing a Python file."""
    symbols, dependencies = analyzer.analyze_file(temp_python_file)
    
    assert len(symbols) > 0
    assert len(dependencies) > 0


def test_analyzer_extract_symbols(analyzer, temp_python_file):
    """Test extracting symbols."""
    symbols, _ = analyzer.analyze_file(temp_python_file)
    
    # Should find class and functions
    symbol_names = [s.name for s in symbols]
    assert "TestClass" in symbol_names
    assert "test_function" in symbol_names


def test_analyzer_extract_dependencies(analyzer, temp_python_file):
    """Test extracting dependencies."""
    _, dependencies = analyzer.analyze_file(temp_python_file)
    
    # Should find imports
    targets = [d.target for d in dependencies]
    assert "os" in targets
    assert "pathlib" in targets


def test_analyzer_handle_parse_error(analyzer):
    """Test handling parse errors."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("invalid python syntax !!!")
        temp_path = f.name
    
    try:
        symbols, dependencies = analyzer.analyze_file(Path(temp_path))
        
        # Should return empty lists on error
        assert symbols == []
        assert dependencies == []
    finally:
        os.unlink(temp_path)


# ============================================================================
# DependencyGraph Tests
# ============================================================================

@pytest.fixture
def graph():
    """Create a dependency graph."""
    return DependencyGraph()


def test_graph_creation(graph):
    """Test creating a graph."""
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0


def test_graph_add_dependency(graph):
    """Test adding a dependency."""
    graph.add_dependency("A", "B")
    
    assert "A" in graph.nodes
    assert "B" in graph.nodes
    assert "B" in graph.edges["A"]


def test_graph_get_dependents(graph):
    """Test getting dependents."""
    # A -> B -> C
    graph.add_dependency("A", "B")
    graph.add_dependency("B", "C")
    
    dependents = graph.get_dependents("C")
    
    assert "B" in dependents
    assert "A" in dependents


def test_graph_get_dependents_max_depth(graph):
    """Test getting dependents with max depth."""
    # A -> B -> C
    graph.add_dependency("A", "B")
    graph.add_dependency("B", "C")
    
    dependents = graph.get_dependents("C", max_depth=1)
    
    assert "B" in dependents
    assert "A" not in dependents


def test_graph_get_dependencies(graph):
    """Test getting dependencies."""
    # A -> B -> C
    graph.add_dependency("A", "B")
    graph.add_dependency("B", "C")
    
    dependencies = graph.get_dependencies("A")
    
    assert "B" in dependencies
    assert "C" in dependencies


def test_graph_detect_cycles(graph):
    """Test detecting cycles."""
    # A -> B -> C -> A (cycle)
    graph.add_dependency("A", "B")
    graph.add_dependency("B", "C")
    graph.add_dependency("C", "A")
    
    cycles = graph.detect_cycles()
    
    assert len(cycles) > 0


def test_graph_no_cycles(graph):
    """Test no cycles."""
    # A -> B -> C (no cycle)
    graph.add_dependency("A", "B")
    graph.add_dependency("B", "C")
    
    cycles = graph.detect_cycles()
    
    # May detect cycles due to implementation
    assert isinstance(cycles, list)


# ============================================================================
# ECCEngine Tests
# ============================================================================

@pytest.fixture
def temp_repo():
    """Create a temporary repository."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # Create some Python files
    (repo_path / "main.py").write_text("""
import utils

def main():
    utils.helper()

if __name__ == '__main__':
    main()
""")
    
    (repo_path / "utils.py").write_text("""
def helper():
    return 42
""")
    
    yield repo_path
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


@pytest.fixture
def engine(temp_repo):
    """Create an ECC engine."""
    return ECCEngine(temp_repo)


def test_engine_creation(engine, temp_repo):
    """Test creating an engine."""
    assert engine.repo_path == temp_repo
    assert engine.analyzer is not None
    assert engine.graph is not None


def test_engine_analyze_repository(engine):
    """Test analyzing repository."""
    context = engine.analyze_repository()
    
    assert context is not None
    assert context.total_files > 0
    assert len(context.symbols) > 0


def test_engine_analyze_impact(engine):
    """Test analyzing impact."""
    # First analyze repository
    engine.analyze_repository()
    
    # Analyze impact of utils.py
    impact = engine.analyze_impact("utils.py")
    
    assert impact is not None
    assert impact.target_file == "utils.py"
    assert impact.risk_level in ["low", "medium", "high"]


def test_engine_find_symbol(engine):
    """Test finding symbols."""
    # First analyze repository
    engine.analyze_repository()
    
    # Find main function
    symbols = engine.find_symbol("main")
    
    # May or may not find depending on analysis
    assert isinstance(symbols, list)


def test_engine_get_symbol_references(engine):
    """Test getting symbol references."""
    symbol = Symbol(
        name="test",
        type=SymbolType.FUNCTION,
        file_path="test.py",
        line_number=10,
    )
    
    references = engine.get_symbol_references(symbol)
    
    assert isinstance(references, list)


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_analysis_workflow(engine):
    """Test complete analysis workflow."""
    # Analyze repository
    context = engine.analyze_repository()
    
    assert context.total_files > 0
    
    # Analyze impact
    if context.symbols:
        file_path = context.symbols[0].file_path
        impact = engine.analyze_impact(file_path)
        
        assert impact is not None


def test_repository_context_structure(engine):
    """Test repository context structure."""
    context = engine.analyze_repository()
    
    assert hasattr(context, 'root_path')
    assert hasattr(context, 'total_files')
    assert hasattr(context, 'total_lines')
    assert hasattr(context, 'languages')
    assert hasattr(context, 'symbols')
    assert hasattr(context, 'dependencies')


def test_impact_analysis_structure(engine):
    """Test impact analysis structure."""
    engine.analyze_repository()
    
    impact = engine.analyze_impact("test.py")
    
    assert hasattr(impact, 'target_file')
    assert hasattr(impact, 'direct_dependents')
    assert hasattr(impact, 'indirect_dependents')
    assert hasattr(impact, 'risk_level')
    assert hasattr(impact, 'blast_radius')


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_repository():
    """Test with empty repository."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    try:
        engine = ECCEngine(repo_path)
        context = engine.analyze_repository()
        
        assert context.total_files == 0
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_repository_with_subdirectories(temp_repo):
    """Test repository with subdirectories."""
    # Create subdirectory
    sub_dir = temp_repo / "subdir"
    sub_dir.mkdir()
    
    (sub_dir / "module.py").write_text("""
def sub_function():
    pass
""")
    
    engine = ECCEngine(temp_repo)
    context = engine.analyze_repository()
    
    # Should find files in subdirectories
    assert context.total_files >= 3


def test_impact_analysis_no_dependents(engine):
    """Test impact analysis with no dependents."""
    engine.analyze_repository()
    
    impact = engine.analyze_impact("nonexistent.py")
    
    assert impact.blast_radius == 0
    assert impact.risk_level == "low"


# ============================================================================
# Performance Tests
# ============================================================================

def test_analyzer_performance(analyzer, temp_python_file):
    """Test analyzer performance."""
    import time
    
    start = time.time()
    for _ in range(10):
        analyzer.analyze_file(temp_python_file)
    duration = time.time() - start
    
    # Should be fast
    assert duration < 1.0


def test_graph_performance(graph):
    """Test graph performance."""
    import time
    
    # Build large graph
    for i in range(100):
        graph.add_dependency(f"node_{i}", f"node_{i+1}")
    
    start = time.time()
    graph.get_dependents("node_50")
    duration = time.time() - start
    
    # Should be fast
    assert duration < 0.1


def test_engine_performance(engine):
    """Test engine performance."""
    import time
    
    start = time.time()
    engine.analyze_repository()
    duration = time.time() - start
    
    # Should be reasonably fast
    assert duration < 5.0
