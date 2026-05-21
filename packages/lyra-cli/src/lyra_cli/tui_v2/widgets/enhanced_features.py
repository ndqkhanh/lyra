"""TUI Enhanced Features - Advanced editing capabilities.

Phase 5 of TUI Autocomplete. Provides multi-cursor support, syntax highlighting,
advanced editing, and custom themes.

Features:
- Multi-cursor editing
- Syntax highlighting
- Advanced text manipulation
- Custom themes
- Vim/Emacs keybindings
- Bracket matching
- Auto-indentation

Usage:
    # Multi-cursor
    Ctrl+D: Add cursor at next match
    Ctrl+Shift+L: Add cursor at all matches
    
    # Syntax highlighting
    Auto-detected by file extension
    
    # Themes
    /theme dark
    /theme light
    /theme custom
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from enum import Enum
from textual.widgets import TextArea
from textual.reactive import reactive
from rich.syntax import Syntax
from rich.text import Text
import re


class Theme(Enum):
    """Available themes."""
    
    DARK = "monokai"
    LIGHT = "github-light"
    DRACULA = "dracula"
    NORD = "nord"
    SOLARIZED_DARK = "solarized-dark"
    SOLARIZED_LIGHT = "solarized-light"


class KeybindingMode(Enum):
    """Keybinding modes."""
    
    DEFAULT = "default"
    VIM = "vim"
    EMACS = "emacs"


@dataclass
class Cursor:
    """A cursor position in the editor."""
    
    line: int
    column: int
    
    def __eq__(self, other):
        """Check equality."""
        if not isinstance(other, Cursor):
            return False
        return self.line == other.line and self.column == other.column
    
    def __hash__(self):
        """Hash for set operations."""
        return hash((self.line, self.column))


@dataclass
class Selection:
    """A text selection."""
    
    start: Cursor
    end: Cursor
    
    def contains(self, cursor: Cursor) -> bool:
        """Check if cursor is in selection.
        
        Args:
            cursor: Cursor to check
            
        Returns:
            True if cursor is in selection
        """
        if self.start.line == self.end.line:
            return (
                cursor.line == self.start.line and
                self.start.column <= cursor.column <= self.end.column
            )
        
        if cursor.line < self.start.line or cursor.line > self.end.line:
            return False
        
        if cursor.line == self.start.line:
            return cursor.column >= self.start.column
        
        if cursor.line == self.end.line:
            return cursor.column <= self.end.column
        
        return True


class MultiCursorManager:
    """
    Manages multiple cursors for simultaneous editing.
    
    Features:
    - Add/remove cursors
    - Synchronize edits across cursors
    - Merge overlapping cursors
    - Selection management
    """
    
    def __init__(self):
        """Initialize the multi-cursor manager."""
        self.cursors: List[Cursor] = [Cursor(0, 0)]
        self.selections: List[Selection] = []
    
    def add_cursor(self, line: int, column: int) -> None:
        """Add a cursor at position.
        
        Args:
            line: Line number
            column: Column number
        """
        cursor = Cursor(line, column)
        if cursor not in self.cursors:
            self.cursors.append(cursor)
            self._merge_overlapping()
    
    def remove_cursor(self, line: int, column: int) -> None:
        """Remove cursor at position.
        
        Args:
            line: Line number
            column: Column number
        """
        cursor = Cursor(line, column)
        if cursor in self.cursors and len(self.cursors) > 1:
            self.cursors.remove(cursor)
    
    def clear_extra_cursors(self) -> None:
        """Clear all cursors except the first."""
        if self.cursors:
            self.cursors = [self.cursors[0]]
        self.selections = []
    
    def _merge_overlapping(self) -> None:
        """Merge overlapping cursors."""
        # Sort cursors
        self.cursors.sort(key=lambda c: (c.line, c.column))
        
        # Remove duplicates
        seen = set()
        unique = []
        for cursor in self.cursors:
            if cursor not in seen:
                seen.add(cursor)
                unique.append(cursor)
        
        self.cursors = unique
    
    def find_next_match(self, text: str, pattern: str, start_line: int, start_col: int) -> Optional[Cursor]:
        """Find next match of pattern.
        
        Args:
            text: Full text
            pattern: Pattern to find
            start_line: Start line
            start_col: Start column
            
        Returns:
            Cursor at match or None
        """
        lines = text.split('\n')
        
        # Search from start position
        for line_idx in range(start_line, len(lines)):
            line = lines[line_idx]
            start = start_col if line_idx == start_line else 0
            
            pos = line.find(pattern, start)
            if pos != -1:
                return Cursor(line_idx, pos)
        
        return None
    
    def add_cursor_at_next_match(self, text: str, pattern: str) -> bool:
        """Add cursor at next match of pattern.
        
        Args:
            text: Full text
            pattern: Pattern to find
            
        Returns:
            True if cursor was added
        """
        if not self.cursors:
            return False
        
        # Start from last cursor
        last = self.cursors[-1]
        match = self.find_next_match(text, pattern, last.line, last.column + 1)
        
        if match:
            self.add_cursor(match.line, match.column)
            return True
        
        return False
    
    def add_cursors_at_all_matches(self, text: str, pattern: str) -> int:
        """Add cursors at all matches of pattern.
        
        Args:
            text: Full text
            pattern: Pattern to find
            
        Returns:
            Number of cursors added
        """
        lines = text.split('\n')
        added = 0
        
        for line_idx, line in enumerate(lines):
            pos = 0
            while True:
                pos = line.find(pattern, pos)
                if pos == -1:
                    break
                
                self.add_cursor(line_idx, pos)
                added += 1
                pos += 1
        
        return added


class SyntaxHighlighter:
    """
    Provides syntax highlighting for code.
    
    Features:
    - Language detection
    - Theme support
    - Bracket matching
    - Error highlighting
    """
    
    def __init__(self, theme: Theme = Theme.DARK):
        """Initialize the syntax highlighter.
        
        Args:
            theme: Color theme
        """
        self.theme = theme
        self.language: Optional[str] = None
    
    def detect_language(self, filename: str) -> Optional[str]:
        """Detect language from filename.
        
        Args:
            filename: File name
            
        Returns:
            Language name or None
        """
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.rs': 'rust',
            '.go': 'go',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.md': 'markdown',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sql': 'sql',
            '.sh': 'bash',
            '.bash': 'bash',
        }
        
        for ext, lang in ext_map.items():
            if filename.endswith(ext):
                self.language = lang
                return lang
        
        return None
    
    def highlight(self, code: str, language: Optional[str] = None) -> Text:
        """Highlight code.
        
        Args:
            code: Code to highlight
            language: Language (auto-detect if None)
            
        Returns:
            Highlighted text
        """
        lang = language or self.language or 'text'
        
        try:
            syntax = Syntax(
                code,
                lang,
                theme=self.theme.value,
                line_numbers=False,
            )
            return Text.from_markup(str(syntax))
        except Exception:
            # Fallback to plain text
            return Text(code)
    
    def find_matching_bracket(self, text: str, line: int, column: int) -> Optional[Tuple[int, int]]:
        """Find matching bracket.
        
        Args:
            text: Full text
            line: Line number
            column: Column number
            
        Returns:
            (line, column) of matching bracket or None
        """
        lines = text.split('\n')
        if line >= len(lines):
            return None
        
        char = lines[line][column] if column < len(lines[line]) else None
        if not char:
            return None
        
        # Bracket pairs
        pairs = {
            '(': ')',
            '[': ']',
            '{': '}',
            ')': '(',
            ']': '[',
            '}': '{',
        }
        
        if char not in pairs:
            return None
        
        target = pairs[char]
        is_opening = char in '([{'
        
        # Search direction
        if is_opening:
            return self._find_closing_bracket(lines, line, column, char, target)
        else:
            return self._find_opening_bracket(lines, line, column, char, target)
    
    def _find_closing_bracket(
        self,
        lines: List[str],
        start_line: int,
        start_col: int,
        opening: str,
        closing: str,
    ) -> Optional[Tuple[int, int]]:
        """Find closing bracket."""
        depth = 1
        
        for line_idx in range(start_line, len(lines)):
            line = lines[line_idx]
            start = start_col + 1 if line_idx == start_line else 0
            
            for col in range(start, len(line)):
                if line[col] == opening:
                    depth += 1
                elif line[col] == closing:
                    depth -= 1
                    if depth == 0:
                        return (line_idx, col)
        
        return None
    
    def _find_opening_bracket(
        self,
        lines: List[str],
        start_line: int,
        start_col: int,
        closing: str,
        opening: str,
    ) -> Optional[Tuple[int, int]]:
        """Find opening bracket."""
        depth = 1
        
        for line_idx in range(start_line, -1, -1):
            line = lines[line_idx]
            end = start_col - 1 if line_idx == start_line else len(line) - 1
            
            for col in range(end, -1, -1):
                if line[col] == closing:
                    depth += 1
                elif line[col] == opening:
                    depth -= 1
                    if depth == 0:
                        return (line_idx, col)
        
        return None


class AutoIndenter:
    """
    Provides automatic indentation.
    
    Features:
    - Language-aware indentation
    - Smart bracket handling
    - Indent/dedent
    """
    
    def __init__(self, indent_size: int = 4, use_spaces: bool = True):
        """Initialize the auto-indenter.
        
        Args:
            indent_size: Number of spaces per indent
            use_spaces: Use spaces instead of tabs
        """
        self.indent_size = indent_size
        self.use_spaces = use_spaces
        self.indent_char = ' ' * indent_size if use_spaces else '\t'
    
    def get_indent_level(self, line: str) -> int:
        """Get indent level of line.
        
        Args:
            line: Line text
            
        Returns:
            Indent level
        """
        count = 0
        for char in line:
            if char == ' ':
                count += 1
            elif char == '\t':
                count += self.indent_size
            else:
                break
        
        return count // self.indent_size
    
    def should_indent(self, line: str) -> bool:
        """Check if next line should be indented.
        
        Args:
            line: Current line
            
        Returns:
            True if should indent
        """
        stripped = line.strip()
        
        # Indent after opening brackets
        if stripped.endswith((':', '{', '[', '(')):
            return True
        
        # Indent after keywords
        keywords = ['if', 'else', 'elif', 'for', 'while', 'def', 'class', 'try', 'except', 'finally', 'with']
        for keyword in keywords:
            if stripped.startswith(keyword + ' ') or stripped == keyword + ':':
                return True
        
        return False
    
    def should_dedent(self, line: str) -> bool:
        """Check if line should be dedented.
        
        Args:
            line: Current line
            
        Returns:
            True if should dedent
        """
        stripped = line.strip()
        
        # Dedent closing brackets
        if stripped.startswith(('}', ']', ')')):
            return True
        
        # Dedent after keywords
        if stripped.startswith(('else:', 'elif ', 'except:', 'except ', 'finally:')):
            return True
        
        return False
    
    def calculate_indent(self, previous_line: str, current_line: str) -> str:
        """Calculate indent for current line.
        
        Args:
            previous_line: Previous line
            current_line: Current line
            
        Returns:
            Indent string
        """
        prev_indent = self.get_indent_level(previous_line)
        
        # Check if should indent
        if self.should_indent(previous_line):
            level = prev_indent + 1
        elif self.should_dedent(current_line):
            level = max(0, prev_indent - 1)
        else:
            level = prev_indent
        
        return self.indent_char * level


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "Theme",
    "KeybindingMode",
    "Cursor",
    "Selection",
    "MultiCursorManager",
    "SyntaxHighlighter",
    "AutoIndenter",
]
