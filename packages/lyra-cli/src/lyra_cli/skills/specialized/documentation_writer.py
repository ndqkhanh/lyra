"""
Documentation Writer Skill - Generate docstrings, README sections, and API docs.

Produces:
- Google-style docstrings for functions/classes
- README sections from code analysis
- API documentation with proper formatting
- Markdown output with correct formatting
"""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class DocstringSection:
    """A section within a generated docstring."""

    name: str
    content: str


@dataclass(frozen=True)
class GeneratedDocstring:
    """A complete generated docstring for a function or class."""

    target_name: str
    target_type: str
    line: int
    docstring: str
    sections: tuple[DocstringSection, ...]


@dataclass(frozen=True)
class ApiEndpoint:
    """Documentation for an API endpoint."""

    function_name: str
    line: int
    description: str
    parameters: tuple[dict[str, str], ...]
    returns: str
    raises: tuple[str, ...]


@dataclass(frozen=True)
class DocumentationReport:
    """Complete documentation report."""

    module_name: str
    docstrings: tuple[GeneratedDocstring, ...]
    api_endpoints: tuple[ApiEndpoint, ...]
    readme_section: str


class DocumentationWriterSkill:
    """Generate documentation from source code analysis."""

    def run(self, input_data: dict) -> dict:
        """Generate documentation for the provided source code.

        Args:
            input_data: Dictionary with keys:
                - source: Source code string
                - module_name: Module name (default "module")
                - output_format: "docstrings" or "readme" or "api" (default "docstrings")

        Returns:
            Dictionary with generated documentation.
        """
        source = input_data.get("source", "")
        if not source:
            return {"error": "No source code provided", "docstrings": []}

        module_name = input_data.get("module_name", "module")
        input_data.get("output_format", "docstrings")

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}", "docstrings": []}

        docstrings: list[GeneratedDocstring] = []
        endpoints: list[ApiEndpoint] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                gd = self._generate_function_docstring(node, source)
                if gd:
                    docstrings.append(gd)

                ep = self._generate_api_endpoint(node, source)
                if ep:
                    endpoints.append(ep)

            elif isinstance(node, ast.ClassDef):
                gd = self._generate_class_docstring(node, source)
                if gd:
                    docstrings.append(gd)

        readme = self._generate_readme(module_name, docstrings, source)

        return DocumentationReport(
            module_name=module_name,
            docstrings=tuple(docstrings),
            api_endpoints=tuple(endpoints),
            readme_section=readme,
        ).__dict__ | {
            "docstrings": [d.__dict__ for d in docstrings],
            "api_endpoints": [e.__dict__ for e in endpoints],
        }

    def _generate_function_docstring(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, source: str
    ) -> GeneratedDocstring | None:
        """Generate a Google-style docstring for a function."""
        if ast.get_docstring(node):
            return None  # Already has a docstring

        func_name = node.name
        args = node.args
        arg_names = [a.arg for a in args.args]
        has_return = node.returns is not None

        sections: list[DocstringSection] = []
        lines: list[str] = []

        # Description
        desc = f"Execute the {func_name} operation."
        lines.append(desc)
        lines.append("")

        # Args section
        if arg_names:
            lines.append("Args:")
            sections.append(DocstringSection(name="Args", content=""))
            for arg_name in arg_names:
                arg_type = self._infer_type(arg_name)
                lines.append(f"    {arg_name}: {arg_type}. Description needed.")
            lines.append("")

        # Returns section
        if has_return:
            return_type = self._get_return_type(node)
            lines.append("Returns:")
            lines.append(f"    {return_type}. Description needed.")
            lines.append("")
            sections.append(DocstringSection(name="Returns", content=return_type))

        # Raises section
        raises = self._find_raises(node)
        if raises:
            lines.append("Raises:")
            for exc in raises:
                lines.append(f"    {exc}: Description needed.")
            lines.append("")
            sections.append(
                DocstringSection(name="Raises", content=", ".join(raises))
            )

        docstring = '"""' + "\n".join(lines) + '"""'
        return GeneratedDocstring(
            target_name=func_name,
            target_type="function",
            line=node.lineno,
            docstring=docstring,
            sections=tuple(sections),
        )

    def _generate_class_docstring(
        self, node: ast.ClassDef, source: str
    ) -> GeneratedDocstring | None:
        """Generate a Google-style docstring for a class."""
        if ast.get_docstring(node):
            return None

        class_name = node.name
        methods = [
            n.name for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        lines: list[str] = []
        lines.append(f"{class_name} class for ...")
        lines.append("")
        lines.append("Attributes:")
        lines.append("    Description needed.")
        lines.append("")
        lines.append("Methods:")
        for m in methods:
            if not m.startswith("_"):
                lines.append(f"    - {m}: Description needed.")

        docstring = '"""' + "\n".join(lines) + '"""'
        return GeneratedDocstring(
            target_name=class_name,
            target_type="class",
            line=node.lineno,
            docstring=docstring,
            sections=(
                DocstringSection(name="Attributes", content=""),
                DocstringSection(name="Methods", content=", ".join(methods)),
            ),
        )

    def _generate_api_endpoint(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, source: str
    ) -> ApiEndpoint | None:
        """Generate API endpoint docs for functions that look like endpoints."""
        func_name = node.name
        args = node.args
        arg_names = [a.arg for a in args.args]

        params: list[dict[str, str]] = []
        for arg_name in arg_names:
            params.append(
                {
                    "name": arg_name,
                    "type": self._infer_type(arg_name),
                    "description": "Description needed.",
                }
            )

        returns = self._get_return_type(node)
        raises = list(self._find_raises(node))

        return ApiEndpoint(
            function_name=func_name,
            line=node.lineno,
            description=f"The {func_name} endpoint.",
            parameters=tuple(params),
            returns=returns if returns else "Any",
            raises=tuple(raises),
        )

    def _generate_readme(
        self,
        module_name: str,
        docstrings: list[GeneratedDocstring],
        source: str,
    ) -> str:
        """Generate a README section from code analysis."""
        lines: list[str] = []
        lines.append(f"# {module_name.replace('_', ' ').title()}")
        lines.append("")
        lines.append(
            "Auto-generated documentation from source code analysis."
        )
        lines.append("")

        functions = [d for d in docstrings if d.target_type == "function"]
        classes = [d for d in docstrings if d.target_type == "class"]

        if functions:
            lines.append("## Functions")
            lines.append("")
            for func in functions:
                lines.append(f"- `{func.target_name}`")
            lines.append("")

        if classes:
            lines.append("## Classes")
            lines.append("")
            for cls in classes:
                lines.append(f"- `{cls.target_name}`")
            lines.append("")

        lines.append("## Usage")
        lines.append("")
        lines.append("```python")
        if functions:
            lines.append(f"from {module_name} import {functions[0].target_name}")
            lines.append("")
            lines.append(f"result = {functions[0].target_name}(...)")
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    def _infer_type(self, name: str) -> str:
        """Infer type from parameter name conventions."""
        if "id" in name.lower():
            return "int | str"
        if "name" in name.lower():
            return "str"
        if "count" in name.lower() or "num" in name.lower():
            return "int"
        if "flag" in name.lower() or "is_" in name.lower():
            return "bool"
        if "data" in name.lower() or "content" in name.lower():
            return "Any"
        return "Any"

    def _get_return_type(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Extract return type annotation."""
        if node.returns:
            return ast.unparse(node.returns)
        return "None"

    def _find_raises(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
        """Find raise statements in function body."""
        raises: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Raise) and child.exc:
                if isinstance(child.exc, ast.Call) and isinstance(child.exc.func, ast.Name):
                    raises.add(child.exc.func.id)
                elif isinstance(child.exc, ast.Name):
                    raises.add(child.exc.id)
        return sorted(raises)
