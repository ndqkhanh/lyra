"""Skill loader for loading skill content and generating codemaps."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .skill_metadata import SkillMetadata


@dataclass(frozen=True)
class SkillContent:
    skill_name: str
    body: str
    language: str = ""
    entry_point: str = ""
    dependencies: tuple[str, ...] = ()
    functions: tuple[str, ...] = ()
    classes: tuple[str, ...] = ()


class SkillLoader:
    """Loads skill content and generates codemaps.

    Supports Python (.py), shell (.sh), and markdown (.md) skill files.
    Codemaps extract function/class signatures and dependencies for
    Python skills via AST parsing.
    """

    PYTHON_EXTENSIONS = {".py"}
    SHELL_EXTENSIONS = {".sh", ".bash"}
    MARKDOWN_EXTENSIONS = {".md"}

    def load_skill_content(self, skill: SkillMetadata) -> str:
        if not skill.file_path:
            return ""
        file_path = Path(skill.file_path)
        if not file_path.exists():
            return ""
        return file_path.read_text()

    def load_with_codemap(self, skill: SkillMetadata) -> SkillContent:
        body = self.load_skill_content(skill)
        if not body:
            return SkillContent(skill_name=skill.name, body="")

        file_path = Path(skill.file_path) if skill.file_path else None
        if file_path and file_path.suffix in self.PYTHON_EXTENSIONS:
            return self._codemap_python(skill.name, body)
        if file_path and file_path.suffix in self.SHELL_EXTENSIONS:
            return self._codemap_shell(skill.name, body)
        if file_path and file_path.suffix in self.MARKDOWN_EXTENSIONS:
            return self._codemap_markdown(skill.name, body)

        return SkillContent(skill_name=skill.name, body=body)

    def generate_codemap(self, skill_name: str, skill_dir: Path) -> SkillContent | None:
        if not skill_dir.exists() or not skill_dir.is_dir():
            return None

        py_files = list(skill_dir.rglob("*.py"))
        if not py_files:
            return None

        combined_body = ""
        all_functions: list[str] = []
        all_classes: list[str] = []
        all_deps: set[str] = set()
        entry = ""

        for py_file in py_files:
            content = py_file.read_text()
            combined_body += content + "\n"
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        all_functions.append(node.name)
                    elif isinstance(node, ast.ClassDef):
                        all_classes.append(node.name)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            all_deps.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        all_deps.add(node.module.split(".")[0])
            except SyntaxError:
                pass

        if py_files:
            entry = str(py_files[0].relative_to(skill_dir))

        return SkillContent(
            skill_name=skill_name,
            body=combined_body.strip(),
            language="python",
            entry_point=entry,
            dependencies=tuple(sorted(all_deps)),
            functions=tuple(all_functions),
            classes=tuple(all_classes),
        )

    def _codemap_python(self, name: str, body: str) -> SkillContent:
        functions: list[str] = []
        classes: list[str] = []
        deps: set[str] = set()
        try:
            tree = ast.parse(body)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        deps.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom) and node.module:
                    deps.add(node.module.split(".")[0])
        except SyntaxError:
            return SkillContent(skill_name=name, body=body, language="python")

        return SkillContent(
            skill_name=name, body=body, language="python",
            dependencies=tuple(sorted(deps)),
            functions=tuple(functions), classes=tuple(classes),
        )

    def _codemap_shell(self, name: str, body: str) -> SkillContent:
        functions: list[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("function ") or (
                stripped and not stripped.startswith("#") and "()" in stripped and "{" in stripped
            ):
                parts = stripped.split()
                if parts:
                    fname = parts[0].rstrip("(){")
                    if fname:
                        functions.append(fname)
        return SkillContent(
            skill_name=name, body=body, language="shell",
            functions=tuple(functions),
        )

    def _codemap_markdown(self, name: str, body: str) -> SkillContent:
        code_blocks: list[str] = []
        in_block = False
        block_lang = ""
        for line in body.splitlines():
            if line.startswith("```") and not in_block:
                in_block = True
                block_lang = line[3:].strip()
            elif line.startswith("```") and in_block:
                in_block = False
            elif in_block:
                code_blocks.append(line)

        return SkillContent(
            skill_name=name, body=body, language=block_lang or "markdown",
        )
