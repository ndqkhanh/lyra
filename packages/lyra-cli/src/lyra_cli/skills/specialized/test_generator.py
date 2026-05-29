"""
Test Generator Skill - Generate pytest test skeletons from function signatures.

Analyzes functions to produce:
- Happy path tests
- Edge case tests
- Error case tests
- Boundary value tests

Outputs complete pytest test file content.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class TestCase:
    """A single generated test case."""

    name: str
    category: str
    input_example: str
    expected_behavior: str


@dataclass(frozen=True)
class GeneratedTest:
    """A complete generated test for one function."""

    function_name: str
    test_cases: tuple[TestCase, ...]
    imports: tuple[str, ...]
    code: str


@dataclass(frozen=True)
class TestSuite:
    """Complete generated test suite."""

    source_module: str
    tests: tuple[GeneratedTest, ...]
    total_cases: int


class TestGeneratorSkill:
    """Generate pytest test skeletons from function signatures and source."""

    def run(self, input_data: dict) -> dict:
        """Generate test suite for the provided source code.

        Args:
            input_data: Dictionary with keys:
                - source: Source code string to analyze
                - module_name: Optional module name for imports (default "module")
                - function_names: Optional list of specific functions to test (default all)

        Returns:
            Dictionary with generated test suite.
        """
        source = input_data.get("source", "")
        if not source:
            return {"error": "No source code provided", "tests": []}

        module_name = input_data.get("module_name", "module")
        specific_functions = input_data.get("function_names", None)

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return {"error": f"Syntax error in source: {e}", "tests": []}

        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
            and (specific_functions is None or node.name in specific_functions)
        ]

        if not functions:
            return {"error": "No public functions found to generate tests for.", "tests": []}

        generated_tests: list[GeneratedTest] = []
        for func_node in functions:
            gt = self._generate_test(func_node, module_name, source)
            if gt:
                generated_tests.append(gt)

        return TestSuite(
            source_module=module_name,
            tests=tuple(generated_tests),
            total_cases=sum(len(t.test_cases) for t in generated_tests),
        ).__dict__ | {
            "tests": [self._serialize_test(t) for t in generated_tests],
        }

    def _serialize_test(self, test: GeneratedTest) -> dict:
        return {
            "function_name": test.function_name,
            "test_cases": [tc.__dict__ for tc in test.test_cases],
            "imports": list(test.imports),
            "code": test.code,
        }

    def _generate_test(
        self, func_node: ast.FunctionDef | ast.AsyncFunctionDef, module_name: str, source: str
    ) -> GeneratedTest | None:
        """Generate a complete test for one function."""
        test_cases: list[TestCase] = []
        imports: set[str] = set()
        imports.add("pytest")

        func_name = func_node.name
        is_async = isinstance(func_node, ast.AsyncFunctionDef)

        # Determine arguments
        args = func_node.args
        arg_names = [a.arg for a in args.args]
        has_return_annotation = func_node.returns is not None
        has_defaults = len(args.defaults) > 0

        # Generate happy path test
        happy_inputs = ", ".join(f"{name}=None" if has_defaults else name for name in arg_names)
        test_cases.append(
            TestCase(
                name=f"test_{func_name}_happy_path",
                category="happy_path",
                input_example=f"result = {func_name}({happy_inputs})",
                expected_behavior=(
                    f"Returns expected output for valid "
                    f"{', '.join(arg_names) if arg_names else 'input'}"
                ),
            )
        )

        # Generate edge case tests
        if arg_names:
            test_cases.append(
                TestCase(
                    name=f"test_{func_name}_empty_input",
                    category="edge_case",
                    input_example=f"result = {func_name}()",
                    expected_behavior="Handles empty/missing input gracefully",
                )
            )

        # Generate boundary value tests for numeric params
        for arg_name in arg_names:
            test_cases.append(
                TestCase(
                    name=f"test_{func_name}_boundary_{arg_name}",
                    category="boundary",
                    input_example=f"result = {func_name}({arg_name}=0)",
                    expected_behavior=f"Handles boundary value for {arg_name}",
                )
            )

        # Generate error case tests
        if is_async:
            test_cases.append(
                TestCase(
                    name=f"test_{func_name}_error_handling",
                    category="error_case",
                    input_example=(
                        f"with pytest.raises(Exception):\\n        await {func_name}(invalid_input)"
                    ),
                    expected_behavior="Raises appropriate exception for invalid input",
                )
            )
        else:
            test_cases.append(
                TestCase(
                    name=f"test_{func_name}_error_handling",
                    category="error_case",
                    input_example=(
                        f"with pytest.raises(Exception):\\n        {func_name}(invalid_input)"
                    ),
                    expected_behavior="Raises appropriate exception for invalid input",
                )
            )

        # Generate test code
        test_code = self._build_test_code(
            func_name, arg_names, is_async, has_return_annotation, source
        )

        return GeneratedTest(
            function_name=func_name,
            test_cases=tuple(test_cases),
            imports=tuple(sorted(imports)),
            code=test_code,
        )

    def _build_test_code(
        self,
        func_name: str,
        arg_names: list[str],
        is_async: bool,
        has_return: bool,
        source: str,
    ) -> str:
        """Build the actual test file content."""
        lines: list[str] = []
        lines.append('"""')
        lines.append(f"Auto-generated tests for {func_name}.")
        lines.append('"""')
        lines.append("")
        lines.append("import pytest")
        lines.append("")
        lines.append(f"from module import {func_name}")
        lines.append("")

        # Happy path
        args_str = ", ".join(arg_names) if arg_names else ""
        lines.append("")
        lines.append(f"def test_{func_name}_happy_path():")
        lines.append(f'    """Test {func_name} with valid inputs."""')
        if is_async:
            lines.append("    result = await _run_async()")
        else:
            lines.append(f"    result = {func_name}({args_str})")
        if has_return:
            lines.append("    assert result is not None")
        lines.append("")

        # Edge case
        lines.append("")
        lines.append(f"def test_{func_name}_edge_cases():")
        lines.append(f'    """Test {func_name} with edge case inputs."""')
        if is_async:
            lines.append("    result = await _run_async()")
        else:
            lines.append(f"    result = {func_name}()")
        lines.append("")

        # Error handling
        lines.append("")
        lines.append(f"def test_{func_name}_errors():")
        lines.append(f'    """Test {func_name} error handling."""')
        lines.append("    with pytest.raises(Exception):")
        if is_async:
            lines.append("        await _run_async()")
        else:
            lines.append(f"        {func_name}(None)")
        lines.append("")

        return "\n".join(lines)
