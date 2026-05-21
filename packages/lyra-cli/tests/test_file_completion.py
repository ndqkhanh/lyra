"""Tests for TUI File Completion."""

import pytest
import tempfile
import time
from pathlib import Path

from lyra_cli.tui_v2.widgets.file_completion import (
    FileEntry,
    RecentFile,
    FileCompleter,
)


# ============================================================================
# FileEntry Tests
# ============================================================================

def test_file_entry_creation():
    """Test creating a file entry."""
    path = Path("/tmp/test.txt")
    
    entry = FileEntry(
        path=path,
        relative_path="test.txt",
        is_dir=False,
        size=1024,
        score=0.9,
    )
    
    assert entry.path == path
    assert entry.relative_path == "test.txt"
    assert entry.is_dir is False
    assert entry.size == 1024
    assert entry.score == 0.9


# ============================================================================
# RecentFile Tests
# ============================================================================

def test_recent_file_creation():
    """Test creating a recent file."""
    rf = RecentFile(path="/tmp/test.txt")
    
    assert rf.path == "/tmp/test.txt"
    assert rf.access_count == 1
    assert rf.last_accessed > 0


def test_recent_file_update_access():
    """Test updating access statistics."""
    rf = RecentFile(path="/tmp/test.txt")
    
    initial_count = rf.access_count
    initial_time = rf.last_accessed
    
    time.sleep(0.01)
    rf.update_access()
    
    assert rf.access_count == initial_count + 1
    assert rf.last_accessed > initial_time


def test_recent_file_frecency_score():
    """Test frecency score calculation."""
    rf = RecentFile(path="/tmp/test.txt")
    
    score = rf.frecency_score
    
    assert score > 0
    assert score <= 1.0


def test_recent_file_frecency_increases_with_access():
    """Test that frecency increases with more accesses."""
    rf = RecentFile(path="/tmp/test.txt")
    
    initial_score = rf.frecency_score
    
    # Access multiple times
    for _ in range(5):
        rf.update_access()
    
    new_score = rf.frecency_score
    
    assert new_score > initial_score


# ============================================================================
# FileCompleter Tests
# ============================================================================

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create test files
        (workspace / "file1.txt").touch()
        (workspace / "file2.py").touch()
        (workspace / "test.md").touch()
        
        # Create subdirectory
        subdir = workspace / "src"
        subdir.mkdir()
        (subdir / "main.py").touch()
        (subdir / "utils.py").touch()
        
        yield workspace


@pytest.fixture
def completer(temp_workspace):
    """Create a file completer."""
    return FileCompleter(workspace_root=temp_workspace)


def test_file_completer_creation(completer):
    """Test creating a file completer."""
    assert completer.workspace_root is not None
    assert isinstance(completer.recent_files, dict)
    assert isinstance(completer.gitignore_patterns, set)


def test_file_completer_load_gitignore(completer):
    """Test loading .gitignore patterns."""
    patterns = completer.gitignore_patterns
    
    # Should have default patterns
    assert "__pycache__" in patterns
    assert "*.pyc" in patterns
    assert ".git" in patterns


def test_file_completer_should_ignore(completer):
    """Test ignore checking."""
    # Should ignore
    assert completer.should_ignore(Path("__pycache__"))
    assert completer.should_ignore(Path(".git"))
    assert completer.should_ignore(Path("test.pyc"))
    
    # Should not ignore
    assert not completer.should_ignore(Path("test.py"))
    assert not completer.should_ignore(Path("README.md"))


def test_file_completer_complete_empty_query(completer):
    """Test completion with empty query."""
    results = completer.complete("")
    
    # Should return recent files (empty if none)
    assert isinstance(results, list)


def test_file_completer_complete_with_prefix(completer):
    """Test completion with prefix."""
    results = completer.complete("file")
    
    # Should find files starting with "file"
    assert len(results) > 0
    assert all("file" in e.relative_path.lower() for e in results)


def test_file_completer_complete_with_path(completer):
    """Test completion with path."""
    results = completer.complete("src/")
    
    # Should find files in src/
    assert len(results) > 0
    assert all("src" in e.relative_path for e in results)


def test_file_completer_calculate_score(completer):
    """Test score calculation."""
    # Exact match
    score1 = completer._calculate_score("test", "test")
    assert score1 == 1.0
    
    # Starts with
    score2 = completer._calculate_score("test", "testing")
    assert score2 == 0.9
    
    # Contains
    score3 = completer._calculate_score("test", "unittest")
    assert 0.5 <= score3 < 0.9


def test_file_completer_is_subsequence(completer):
    """Test subsequence checking."""
    # Is subsequence
    assert completer._is_subsequence("tst", "test")
    assert completer._is_subsequence("abc", "aabbcc")
    
    # Not subsequence
    assert not completer._is_subsequence("xyz", "test")
    assert not completer._is_subsequence("ba", "abc")


def test_file_completer_record_access(completer):
    """Test recording file access."""
    path = "/tmp/test.txt"
    
    completer.record_access(path)
    
    assert path in completer.recent_files
    assert completer.recent_files[path].access_count == 1


def test_file_completer_record_multiple_accesses(completer):
    """Test recording multiple accesses."""
    path = "/tmp/test.txt"
    
    completer.record_access(path)
    completer.record_access(path)
    completer.record_access(path)
    
    assert completer.recent_files[path].access_count == 3


def test_file_completer_get_recent_files(completer):
    """Test getting recent files."""
    # Record some accesses
    completer.record_access("/tmp/file1.txt")
    completer.record_access("/tmp/file2.txt")
    completer.record_access("/tmp/file3.txt")
    
    recent = completer.get_recent_files(limit=2)
    
    assert len(recent) <= 2
    assert all(isinstance(path, str) for path in recent)


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_completion_workflow(completer):
    """Test complete completion workflow."""
    # Complete with prefix
    results = completer.complete("file")
    
    # Should have results
    assert len(results) > 0
    
    # Record access
    if results:
        completer.record_access(str(results[0].path))
    
    # Complete again (should boost score)
    results2 = completer.complete("file")
    
    # Should still have results
    assert len(results2) > 0


def test_frecency_ranking(completer):
    """Test frecency-based ranking."""
    # Record multiple accesses to one file
    path1 = str(completer.workspace_root / "file1.txt")
    path2 = str(completer.workspace_root / "file2.py")
    
    # Access file1 multiple times
    for _ in range(5):
        completer.record_access(path1)
    
    # Access file2 once
    completer.record_access(path2)
    
    # Get recent files
    recent = completer.get_recent_files()
    
    # file1 should rank higher
    if len(recent) >= 2:
        assert path1 in recent
        assert recent.index(path1) < recent.index(path2)


def test_directory_traversal(completer):
    """Test directory traversal."""
    # Complete in subdirectory
    results = completer.complete("src/main")
    
    # Should find main.py
    assert len(results) > 0
    assert any("main" in e.relative_path for e in results)


def test_gitignore_filtering(completer):
    """Test .gitignore filtering."""
    # Create ignored file
    ignored = completer.workspace_root / "__pycache__"
    ignored.mkdir(exist_ok=True)
    
    # Complete
    results = completer.complete("")
    
    # Should not include ignored files
    assert not any("__pycache__" in e.relative_path for e in results)


# ============================================================================
# Edge Cases
# ============================================================================

def test_complete_nonexistent_directory(completer):
    """Test completion in nonexistent directory."""
    results = completer.complete("nonexistent/file")
    
    # Should return empty list
    assert len(results) == 0


def test_complete_with_absolute_path(completer):
    """Test completion with absolute path."""
    abs_path = str(completer.workspace_root / "file")
    
    results = completer.complete(abs_path)
    
    # Should handle absolute paths
    assert isinstance(results, list)


def test_empty_workspace():
    """Test with empty workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        completer = FileCompleter(workspace_root=workspace)
        
        results = completer.complete("")
        
        # Should return empty list
        assert len(results) == 0


def test_permission_error_handling(completer):
    """Test handling permission errors."""
    # This test is platform-dependent
    # Just ensure it doesn't crash
    results = completer.complete("/root/")
    
    # Should handle gracefully
    assert isinstance(results, list)


# ============================================================================
# Performance Tests
# ============================================================================

def test_completion_performance(completer):
    """Test completion performance."""
    import time
    
    start = time.time()
    
    for _ in range(100):
        completer.complete("file")
    
    duration = time.time() - start
    
    # Should be fast
    assert duration < 1.0  # 100 completions in <1s


def test_large_directory():
    """Test with large directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create many files
        for i in range(100):
            (workspace / f"file_{i}.txt").touch()
        
        completer = FileCompleter(workspace_root=workspace)
        
        # Should handle large directories
        results = completer.complete("file")
        
        assert len(results) > 0
        assert len(results) <= 10  # Respects max_results


def test_deep_directory_structure():
    """Test with deep directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # Create deep structure
        deep = workspace / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "file.txt").touch()
        
        completer = FileCompleter(workspace_root=workspace)
        
        # Should handle deep paths
        results = completer.complete("a/b/c/d/file")
        
        assert len(results) > 0
