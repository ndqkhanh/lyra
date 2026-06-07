"""
Self-knowledge — IntrospectionEngine that reads Lyra's own docs, skills, and config
to answer questions about itself.

Enables Lyra to answer questions like:
  - "What skills do I have?"
  - "What is my version?"
  - "What modules are available?"
  - "What configuration do I use?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class KnowledgeSource:
    """A discovered knowledge source.

    Attributes:
        path: Filesystem path of the source.
        source_type: Type of source ("doc", "skill", "config", "module").
        label: Human-readable label.
        content: Text content (loaded on demand).
    """

    path: str
    source_type: str
    label: str
    content: str = ""


class IntrospectionEngine:
    """Reads Lyra's own codebase to answer questions about itself.

    Scans documentation, skills, configuration, and source modules
    to build a knowledge base that the engine can query.
    """

    def __init__(self, root: str | Path | None = None):
        """Initialize IntrospectionEngine.

        Args:
            root: Path to Lyra project root. Auto-detects if None.
        """
        self._root = Path(root) if root else self._discover_root()
        self._sources: list[KnowledgeSource] = []
        self._version: str = self._read_version()
        self._loaded: bool = False

    @property
    def root(self) -> Path:
        """Project root directory."""
        return self._root

    @property
    def version(self) -> str:
        """Lyra version string."""
        return self._version

    def _discover_root(self) -> Path:
        """Auto-discover project root by looking for src/__init__.py."""
        candidate = Path(__file__).resolve().parent.parent.parent  # src/self_knowledge -> src -> lyra root
        if (candidate / "src" / "__init__.py").exists():
            return candidate
        # Fall back to CWD
        return Path.cwd()

    def _read_version(self) -> str:
        """Read version from src/__init__.py."""
        init_path = self._root / "src" / "__init__.py"
        if init_path.exists():
            for line in init_path.read_text().splitlines():
                if line.startswith("__version__"):
                    # Extract quoted value
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
        return "unknown"

    def load_all(self) -> int:
        """Scan and load all knowledge sources.

        Returns:
            Number of sources loaded.
        """
        self._sources.clear()
        self._scan_docs()
        self._scan_skills()
        self._scan_config()
        self._scan_modules()
        self._loaded = True
        return len(self._sources)

    def _scan_docs(self) -> None:
        """Scan documentation files in the docs/ directory."""
        docs_dir = self._root / "docs"
        if not docs_dir.is_dir():
            return
        for path in sorted(docs_dir.rglob("*")):
            if path.is_file() and path.suffix in (".md", ".txt", ".rst", ".pdf"):
                self._sources.append(
                    KnowledgeSource(
                        path=str(path),
                        source_type="doc",
                        label=path.name,
                        content=self._safe_read(path),
                    )
                )

    def _scan_skills(self) -> None:
        """Scan skill files in src/skills/."""
        skills_dir = self._root / "src" / "skills"
        if not skills_dir.is_dir():
            return
        for path in sorted(skills_dir.iterdir()):
            if path.is_file() and path.suffix == ".py":
                self._sources.append(
                    KnowledgeSource(
                        path=str(path),
                        source_type="skill",
                        label=path.stem,
                        content=self._safe_read(path),
                    )
                )

    def _scan_config(self) -> None:
        """Scan configuration files."""
        for candidate in (
            self._root / "pyproject.toml",
            self._root / "setup.cfg",
            self._root / "setup.py",
            self._root / ".lyra.yaml",
        ):
            if candidate.is_file():
                self._sources.append(
                    KnowledgeSource(
                        path=str(candidate),
                        source_type="config",
                        label=candidate.name,
                        content=self._safe_read(candidate),
                    )
                )

    def _scan_modules(self) -> None:
        """Scan source modules in src/."""
        src_dir = self._root / "src"
        if not src_dir.is_dir():
            return
        for path in sorted(src_dir.iterdir()):
            if path.is_dir() and not path.name.startswith("_"):
                init_file = path / "__init__.py"
                if init_file.exists():
                    self._sources.append(
                        KnowledgeSource(
                            path=str(init_file),
                            source_type="module",
                            label=path.name,
                            content=self._safe_read(init_file),
                        )
                    )

    def _safe_read(self, path: Path) -> str:
        """Safely read a file, returning empty string on error."""
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def ask(self, question: str) -> str:
        """Answer a question about Lyra using discovered knowledge.

        Args:
            question: Natural-language question.

        Returns:
            Answer string based on scanned sources.
        """
        if not self._loaded:
            self.load_all()

        q = question.lower()

        if "version" in q:
            return f"Lyra version {self._version}"

        if "skill" in q:
            skills = [s for s in self._sources if s.source_type == "skill"]
            if not skills:
                return "No skills found."
            names = [s.label for s in skills]
            return f"Found {len(skills)} skill(s): {', '.join(sorted(names))}"

        if "module" in q or "component" in q:
            modules = [s for s in self._sources if s.source_type == "module"]
            if not modules:
                return "No modules found."
            names = [s.label for s in modules]
            return f"Found {len(modules)} module(s): {', '.join(sorted(names))}"

        if "config" in q or "configure" in q:
            configs = [s for s in self._sources if s.source_type == "config"]
            if not configs:
                return "No configuration files found."
            names = [s.label for s in configs]
            return f"Found {len(configs)} config file(s): {', '.join(sorted(names))}"

        if "doc" in q or "document" in q or "readme" in q:
            docs = [s for s in self._sources if s.source_type == "doc"]
            if not docs:
                return "No documentation files found."
            names = [s.label for s in docs]
            return f"Found {len(docs)} documentation file(s): {', '.join(sorted(names))}"

        return (
            f"I am Lyra (v{self._version}). "
            f"I have {len(self._sources)} knowledge sources across "
            f"{len([s for s in self._sources if s.source_type == 'doc'])} docs, "
            f"{len([s for s in self._sources if s.source_type == 'skill'])} skills, "
            f"{len([s for s in self._sources if s.source_type == 'config'])} configs, and "
            f"{len([s for s in self._sources if s.source_type == 'module'])} modules."
        )

    def list_sources(self, source_type: str | None = None) -> list[KnowledgeSource]:
        """List knowledge sources, optionally filtered by type.

        Args:
            source_type: Filter by source type ("doc", "skill", "config", "module").

        Returns:
            List of matching KnowledgeSource instances.
        """
        if not self._loaded:
            self.load_all()
        if source_type is None:
            return list(self._sources)
        return [s for s in self._sources if s.source_type == source_type]

    def get_source_count(self, source_type: str) -> int:
        """Count sources of a given type.

        Args:
            source_type: Source type to count.

        Returns:
            Number of matching sources.
        """
        return len(self.list_sources(source_type))
