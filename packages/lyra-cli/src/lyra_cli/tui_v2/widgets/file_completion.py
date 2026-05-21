"""TUI File Completion - Path completion for file operations.

Phase 3 of TUI Autocomplete. Provides intelligent file path completion
with fuzzy matching, recent files, and directory traversal.

Features:
- Path completion (absolute and relative)
- Fuzzy file search
- Recent files tracking
- Directory traversal
- Git-aware filtering (.gitignore)
- File type filtering
- Smart ranking (frecency)

Usage:
    # In TUI input field
    /edit src/ma<Tab>  # Shows matching files in src/
    
    # Recent files
    /edit <Tab>  # Shows recently edited files
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set
import os


@dataclass
class FileEntry:
    """A file entry for completion."""
    
    path: Path
    relative_path: str
    is_dir: bool
    size: int = 0
    modified: float = 0.0
    access_count: int = 0
    last_accessed: float = 0.0
    score: float = 1.0


@dataclass
class RecentFile:
    """A recently accessed file."""
    
    path: str
    access_count: int = 1
    last_accessed: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def update_access(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.now().timestamp()
    
    @property
    def frecency_score(self) -> float:
        """Calculate frecency score (frequency + recency).
        
        Returns:
            Score (higher is better)
        """
        import time
        
        # Time decay (half-life of 7 days)
        age_seconds = time.time() - self.last_accessed
        age_days = age_seconds / 86400
        recency = 0.5 ** (age_days / 7)
        
        # Frequency (log scale)
        import math
        frequency = math.log(self.access_count + 1)
        
        # Combined score
        return recency * frequency


class FileCompleter:
    """
    Intelligent file path completion.
    
    Features:
    - Fuzzy file search
    - Recent files tracking
    - Directory traversal
    - Git-aware filtering
    - Smart ranking (frecency)
    """
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize the file completer.
        
        Args:
            workspace_root: Root directory for file search
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.recent_files: dict[str, RecentFile] = {}
        self.gitignore_patterns: Set[str] = self._load_gitignore()
    
    def _load_gitignore(self) -> Set[str]:
        """Load .gitignore patterns.
        
        Returns:
            Set of patterns to ignore
        """
        patterns = {
            "__pycache__",
            "*.pyc",
            ".git",
            "node_modules",
            ".venv",
            "venv",
            ".pytest_cache",
            ".mypy_cache",
            "*.egg-info",
        }
        
        gitignore_path = self.workspace_root / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.add(line)
            except Exception:
                pass
        
        return patterns
    
    def should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored.
        
        Args:
            path: Path to check
            
        Returns:
            True if should be ignored
        """
        name = path.name
        
        # Check exact matches
        if name in self.gitignore_patterns:
            return True
        
        # Check patterns
        for pattern in self.gitignore_patterns:
            if "*" in pattern:
                # Simple glob matching
                if pattern.startswith("*"):
                    if name.endswith(pattern[1:]):
                        return True
                elif pattern.endswith("*"):
                    if name.startswith(pattern[:-1]):
                        return True
        
        return False
    
    def complete(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[FileEntry]:
        """Complete file path.
        
        Args:
            query: Partial file path
            max_results: Maximum results to return
            
        Returns:
            List of matching file entries
        """
        if not query:
            # Show recent files
            return self._get_recent_files(max_results)
        
        # Parse query
        query_path = Path(query)
        
        if query_path.is_absolute():
            # Absolute path
            base_dir = query_path.parent
            prefix = query_path.name
        else:
            # Relative path
            if "/" in query or "\\" in query:
                base_dir = self.workspace_root / query_path.parent
                prefix = query_path.name
            else:
                base_dir = self.workspace_root
                prefix = query
        
        # Find matching files
        matches = self._find_matches(base_dir, prefix, max_results)
        
        return matches
    
    def _get_recent_files(self, max_results: int) -> List[FileEntry]:
        """Get recent files sorted by frecency.
        
        Args:
            max_results: Maximum results
            
        Returns:
            List of recent file entries
        """
        # Sort by frecency score
        recent = sorted(
            self.recent_files.values(),
            key=lambda f: f.frecency_score,
            reverse=True,
        )[:max_results]
        
        entries = []
        for rf in recent:
            path = Path(rf.path)
            if path.exists():
                try:
                    relative = path.relative_to(self.workspace_root)
                except ValueError:
                    relative = path
                
                entry = FileEntry(
                    path=path,
                    relative_path=str(relative),
                    is_dir=path.is_dir(),
                    size=path.stat().st_size if path.is_file() else 0,
                    modified=path.stat().st_mtime,
                    access_count=rf.access_count,
                    last_accessed=rf.last_accessed,
                    score=rf.frecency_score,
                )
                entries.append(entry)
        
        return entries
    
    def _find_matches(
        self,
        base_dir: Path,
        prefix: str,
        max_results: int,
    ) -> List[FileEntry]:
        """Find matching files in directory.
        
        Args:
            base_dir: Base directory to search
            prefix: File name prefix
            max_results: Maximum results
            
        Returns:
            List of matching entries
        """
        if not base_dir.exists():
            return []
        
        matches = []
        prefix_lower = prefix.lower()
        
        try:
            for item in base_dir.iterdir():
                # Skip ignored files
                if self.should_ignore(item):
                    continue
                
                # Check if matches prefix
                name_lower = item.name.lower()
                if prefix_lower in name_lower:
                    # Calculate score
                    score = self._calculate_score(prefix_lower, name_lower)
                    
                    # Get relative path
                    try:
                        relative = item.relative_to(self.workspace_root)
                    except ValueError:
                        relative = item
                    
                    # Create entry
                    entry = FileEntry(
                        path=item,
                        relative_path=str(relative),
                        is_dir=item.is_dir(),
                        size=item.stat().st_size if item.is_file() else 0,
                        modified=item.stat().st_mtime,
                        score=score,
                    )
                    
                    # Boost score if in recent files
                    if str(item) in self.recent_files:
                        rf = self.recent_files[str(item)]
                        entry.score *= (1 + rf.frecency_score)
                        entry.access_count = rf.access_count
                        entry.last_accessed = rf.last_accessed
                    
                    matches.append(entry)
        except PermissionError:
            pass
        
        # Sort by score
        matches.sort(key=lambda e: e.score, reverse=True)
        
        return matches[:max_results]
    
    def _calculate_score(self, query: str, text: str) -> float:
        """Calculate fuzzy match score.
        
        Args:
            query: Search query
            text: Text to match against
            
        Returns:
            Score (0-1, higher is better)
        """
        # Exact match
        if query == text:
            return 1.0
        
        # Starts with
        if text.startswith(query):
            return 0.9
        
        # Contains (with position bonus)
        if query in text:
            pos = text.index(query)
            return 0.7 - (pos / len(text)) * 0.2
        
        # Fuzzy match (subsequence)
        if self._is_subsequence(query, text):
            return 0.5
        
        return 0.0
    
    def _is_subsequence(self, query: str, text: str) -> bool:
        """Check if query is a subsequence of text.
        
        Args:
            query: Query string
            text: Text to search in
            
        Returns:
            True if query is subsequence
        """
        query_idx = 0
        
        for char in text:
            if query_idx < len(query) and char == query[query_idx]:
                query_idx += 1
        
        return query_idx == len(query)
    
    def record_access(self, path: str) -> None:
        """Record file access for frecency tracking.
        
        Args:
            path: File path that was accessed
        """
        if path in self.recent_files:
            self.recent_files[path].update_access()
        else:
            self.recent_files[path] = RecentFile(path=path)
    
    def get_recent_files(self, limit: int = 10) -> List[str]:
        """Get list of recent files.
        
        Args:
            limit: Maximum number of files
            
        Returns:
            List of file paths
        """
        recent = sorted(
            self.recent_files.values(),
            key=lambda f: f.frecency_score,
            reverse=True,
        )[:limit]
        
        return [rf.path for rf in recent]


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "FileEntry",
    "RecentFile",
    "FileCompleter",
]
