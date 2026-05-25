"""AST-level code transformation."""

from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass

from .exceptions import ASTTransformationError


@dataclass(frozen=True)
class TransformConfig:
    """Configuration governing AST transformation behaviour."""

    preserve_comments: bool = True
    preserve_formatting: bool = True
    max_line_length: int = 100


@dataclass(frozen=True)
class ASTNode:
    """Representation of a node in the parsed AST."""

    node_type: str
    name: str
    line: int
    col: int
    children: tuple[str, ...]


@dataclass(frozen=True)
class TransformResult:
    """Result of an AST transformation operation."""

    original: str
    transformed: str
    diff: str
    nodes_changed: int
    success: bool


class ASTTransformer:
    """AST-level code transformation with validation."""

    @staticmethod
    async def parse_to_ast(source: str) -> ASTNode:
        """Parse source code into an ASTNode tree."""
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ASTTransformationError(f"Failed to parse source: {e}") from e
        return ASTTransformer._build_node(tree)

    @staticmethod
    def _build_node(node: ast.AST) -> ASTNode:
        node_type = type(node).__name__
        name: str = getattr(node, "name", getattr(node, "id", node_type))
        line: int = getattr(node, "lineno", 0)
        col: int = getattr(node, "col_offset", 0)
        children: list[str] = []
        for child in ast.iter_child_nodes(node):
            children.append(ASTTransformer._build_node(child).node_type)
        return ASTNode(
            node_type=node_type,
            name=name,
            line=line,
            col=col,
            children=tuple(children),
        )

    @staticmethod
    async def apply_transform(
        source: str, transform_rules: tuple[str, ...]
    ) -> TransformResult:
        """Apply a sequence of transform rules to source code."""
        transformed = source
        nodes_changed = 0

        for rule in transform_rules:
            parts = rule.split(":", 1)
            if len(parts) < 2:
                raise ASTTransformationError(f"Invalid transform rule: {rule}")
            rule_type = parts[0]
            rule_body = parts[1]

            if rule_type == "wrap_in_function":
                func_name = rule_body
                indented = "\n    ".join(transformed.split("\n"))
                transformed = f"def {func_name}():\n    {indented}"
                nodes_changed += 1

            elif rule_type == "rename_function":
                old_name, new_name = rule_body.split(",", 1)
                try:
                    tree = ast.parse(transformed)
                except SyntaxError as e:
                    raise ASTTransformationError(
                        f"Cannot parse for rename: {e}"
                    ) from e

                class Renamer(ast.NodeTransformer):
                    def __init__(self) -> None:
                        self.changed = False

                    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
                        if node.name == old_name:
                            node.name = new_name
                            self.changed = True
                        return self.generic_visit(node)  # type: ignore[return-value]

                    def visit_AsyncFunctionDef(
                        self, node: ast.AsyncFunctionDef
                    ) -> ast.AsyncFunctionDef:
                        if node.name == old_name:
                            node.name = new_name
                            self.changed = True
                        return self.generic_visit(node)  # type: ignore[return-value]

                renamer = Renamer()
                new_tree = renamer.visit(tree)
                ast.fix_missing_locations(new_tree)
                if renamer.changed:
                    transformed = ast.unparse(new_tree)
                    nodes_changed += 1

            else:
                raise ASTTransformationError(
                    f"Unknown transform rule: {rule_type}"
                )

        diff = await ASTTransformer.generate_diff(source, transformed)
        return TransformResult(
            original=source,
            transformed=transformed,
            diff=diff,
            nodes_changed=nodes_changed,
            success=True,
        )

    @staticmethod
    async def validate_syntax(transformed: str) -> bool:
        """Check whether the transformed code is syntactically valid."""
        try:
            ast.parse(transformed)
            return True
        except SyntaxError:
            return False

    @staticmethod
    async def generate_diff(original: str, transformed: str) -> str:
        """Generate a unified diff between original and transformed code."""
        if original == transformed:
            return ""
        diff_lines = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                transformed.splitlines(keepends=True),
                fromfile="original",
                tofile="transformed",
            )
        )
        return "".join(diff_lines)
