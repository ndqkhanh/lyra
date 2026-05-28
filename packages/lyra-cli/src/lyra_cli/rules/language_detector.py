"""Language detector - Detect programming language from file"""

from pathlib import Path


class LanguageDetector:
    """Detects programming language from file path or content"""

    # File extension to language mapping
    EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".kt": "kotlin",
        ".go": "golang",
        ".rs": "rust",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".m": "objective-c",
        ".scala": "scala",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".sql": "sql",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
    }

    @staticmethod
    def detect_from_path(file_path: Path) -> str | None:
        """Detect language from file path"""
        if isinstance(file_path, str):
            file_path = Path(file_path)

        extension = file_path.suffix.lower()
        return LanguageDetector.EXTENSIONS.get(extension)

    @staticmethod
    def detect_from_content(content: str) -> str | None:
        """Detect language from file content (basic heuristics)"""
        # Check for shebang
        if content.startswith("#!/usr/bin/env python") or content.startswith("#!/usr/bin/python"):
            return "python"
        if content.startswith("#!/usr/bin/env node") or content.startswith("#!/usr/bin/node"):
            return "javascript"
        if content.startswith("#!/bin/bash") or content.startswith("#!/bin/sh"):
            return "shell"

        # Check for common patterns
        if "def " in content and "import " in content:
            return "python"
        if "function " in content or "const " in content or "let " in content:
            return "javascript"
        if "interface " in content and ": " in content:
            return "typescript"
        if "public class " in content or "private class " in content:
            return "java"
        if "package main" in content and "func " in content:
            return "golang"

        return None

    @staticmethod
    def detect(file_path: Path | None = None, content: str | None = None) -> str | None:
        """Detect language from path or content"""
        if file_path:
            lang = LanguageDetector.detect_from_path(file_path)
            if lang:
                return lang

        if content:
            return LanguageDetector.detect_from_content(content)

        return None

    @staticmethod
    def get_supported_languages() -> list:
        """Get list of supported languages"""
        return sorted(set(LanguageDetector.EXTENSIONS.values()))
