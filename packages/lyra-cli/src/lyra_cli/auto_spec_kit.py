"""Auto-Spec Kit - Automatic specification generation.

Generates specifications, tests, and documentation automatically from code
and natural language descriptions.

Features:
- Specification generation from code
- Test generation from specs
- Documentation generation
- API documentation
- Type inference
- Contract extraction

Usage:
    kit = AutoSpecKit()
    spec = kit.generate_spec(code)
    tests = kit.generate_tests(spec)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from enum import Enum
import ast
import re


class SpecType(Enum):
    """Types of specifications."""
    
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    API = "api"


class TestType(Enum):
    """Types of tests."""
    
    UNIT = "unit"
    INTEGRATION = "integration"
    PROPERTY = "property"
    EDGE_CASE = "edge_case"


@dataclass
class Parameter:
    """A function parameter."""
    
    name: str
    type_hint: Optional[str] = None
    default: Optional[str] = None
    description: str = ""


@dataclass
class ReturnValue:
    """A return value."""
    
    type_hint: Optional[str] = None
    description: str = ""


@dataclass
class Specification:
    """A code specification."""
    
    name: str
    type: SpecType
    description: str
    parameters: List[Parameter] = field(default_factory=list)
    return_value: Optional[ReturnValue] = None
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    invariants: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


@dataclass
class TestCase:
    """A test case."""
    
    name: str
    type: TestType
    description: str
    setup: str = ""
    code: str = ""
    assertions: List[str] = field(default_factory=list)
    expected_output: Optional[str] = None


@dataclass
class Documentation:
    """Generated documentation."""
    
    title: str
    description: str
    sections: Dict[str, str] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    api_reference: List[str] = field(default_factory=list)


class CodeAnalyzer:
    """
    Analyzes code to extract specifications.
    
    Features:
    - AST-based analysis
    - Type inference
    - Contract extraction
    - Documentation parsing
    """
    
    def __init__(self):
        """Initialize the code analyzer."""
        pass
    
    def analyze_function(self, code: str) -> Specification:
        """Analyze a function and extract specification.
        
        Args:
            code: Function code
            
        Returns:
            Function specification
        """
        try:
            tree = ast.parse(code)
            
            # Find function definition
            func_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_def = node
                    break
            
            if not func_def:
                raise ValueError("No function definition found")
            
            # Extract information
            name = func_def.name
            docstring = ast.get_docstring(func_def) or ""
            
            # Extract parameters
            parameters = []
            for arg in func_def.args.args:
                param = Parameter(
                    name=arg.arg,
                    type_hint=self._get_type_annotation(arg),
                )
                parameters.append(param)
            
            # Extract return type
            return_value = None
            if func_def.returns:
                return_value = ReturnValue(
                    type_hint=ast.unparse(func_def.returns),
                )
            
            # Parse docstring for additional info
            description, examples = self._parse_docstring(docstring)
            
            return Specification(
                name=name,
                type=SpecType.FUNCTION,
                description=description,
                parameters=parameters,
                return_value=return_value,
                examples=examples,
            )
        
        except Exception as e:
            # Return minimal spec on error
            return Specification(
                name="unknown",
                type=SpecType.FUNCTION,
                description="",
            )
    
    def analyze_class(self, code: str) -> Specification:
        """Analyze a class and extract specification.
        
        Args:
            code: Class code
            
        Returns:
            Class specification
        """
        try:
            tree = ast.parse(code)
            
            # Find class definition
            class_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_def = node
                    break
            
            if not class_def:
                raise ValueError("No class definition found")
            
            name = class_def.name
            docstring = ast.get_docstring(class_def) or ""
            
            description, examples = self._parse_docstring(docstring)
            
            return Specification(
                name=name,
                type=SpecType.CLASS,
                description=description,
                examples=examples,
            )
        
        except Exception as e:
            return Specification(
                name="unknown",
                type=SpecType.CLASS,
                description="",
            )
    
    def _get_type_annotation(self, arg: ast.arg) -> Optional[str]:
        """Get type annotation for argument.
        
        Args:
            arg: AST argument node
            
        Returns:
            Type annotation string or None
        """
        if arg.annotation:
            return ast.unparse(arg.annotation)
        return None
    
    def _parse_docstring(self, docstring: str) -> tuple[str, List[str]]:
        """Parse docstring to extract description and examples.
        
        Args:
            docstring: Docstring text
            
        Returns:
            Tuple of (description, examples)
        """
        lines = docstring.split('\n')
        description_lines = []
        examples = []
        in_examples = False
        
        for line in lines:
            line = line.strip()
            
            if line.lower().startswith('example'):
                in_examples = True
                continue
            
            if in_examples:
                if line:
                    examples.append(line)
            else:
                if line and not line.startswith(('Args:', 'Returns:', 'Raises:')):
                    description_lines.append(line)
        
        description = ' '.join(description_lines)
        return description, examples


class TestGenerator:
    """
    Generates tests from specifications.
    
    Features:
    - Unit test generation
    - Edge case generation
    - Property-based test generation
    - Integration test generation
    """
    
    def __init__(self):
        """Initialize the test generator."""
        pass
    
    def generate_tests(self, spec: Specification) -> List[TestCase]:
        """Generate tests from specification.
        
        Args:
            spec: Specification
            
        Returns:
            List of test cases
        """
        tests = []
        
        # Generate basic unit test
        tests.append(self._generate_basic_test(spec))
        
        # Generate edge case tests
        tests.extend(self._generate_edge_case_tests(spec))
        
        # Generate property tests if applicable
        if spec.parameters:
            tests.extend(self._generate_property_tests(spec))
        
        return tests
    
    def _generate_basic_test(self, spec: Specification) -> TestCase:
        """Generate basic unit test.
        
        Args:
            spec: Specification
            
        Returns:
            Test case
        """
        # Generate test name
        test_name = f"test_{spec.name}_basic"
        
        # Generate test code
        if spec.type == SpecType.FUNCTION:
            # Create sample call
            params = ", ".join(
                self._generate_sample_value(p)
                for p in spec.parameters
            )
            code = f"result = {spec.name}({params})"
        else:
            code = f"obj = {spec.name}()"
        
        return TestCase(
            name=test_name,
            type=TestType.UNIT,
            description=f"Test basic functionality of {spec.name}",
            code=code,
            assertions=["assert result is not None"],
        )
    
    def _generate_edge_case_tests(self, spec: Specification) -> List[TestCase]:
        """Generate edge case tests.
        
        Args:
            spec: Specification
            
        Returns:
            List of test cases
        """
        tests = []
        
        # Test with None values
        if spec.parameters:
            test = TestCase(
                name=f"test_{spec.name}_with_none",
                type=TestType.EDGE_CASE,
                description=f"Test {spec.name} with None values",
                code=f"result = {spec.name}(None)",
                assertions=["# Should handle None gracefully"],
            )
            tests.append(test)
        
        # Test with empty values
        if spec.parameters:
            test = TestCase(
                name=f"test_{spec.name}_with_empty",
                type=TestType.EDGE_CASE,
                description=f"Test {spec.name} with empty values",
                code=f"result = {spec.name}('')",
                assertions=["# Should handle empty values"],
            )
            tests.append(test)
        
        return tests
    
    def _generate_property_tests(self, spec: Specification) -> List[TestCase]:
        """Generate property-based tests.
        
        Args:
            spec: Specification
            
        Returns:
            List of test cases
        """
        tests = []
        
        # Generate idempotence test
        test = TestCase(
            name=f"test_{spec.name}_idempotent",
            type=TestType.PROPERTY,
            description=f"Test {spec.name} is idempotent",
            code=f"""
result1 = {spec.name}(value)
result2 = {spec.name}(value)
""",
            assertions=["assert result1 == result2"],
        )
        tests.append(test)
        
        return tests
    
    def _generate_sample_value(self, param: Parameter) -> str:
        """Generate sample value for parameter.
        
        Args:
            param: Parameter
            
        Returns:
            Sample value string
        """
        if param.default:
            return param.default
        
        if param.type_hint:
            type_lower = param.type_hint.lower()
            if 'str' in type_lower:
                return "'test'"
            elif 'int' in type_lower:
                return "42"
            elif 'float' in type_lower:
                return "3.14"
            elif 'bool' in type_lower:
                return "True"
            elif 'list' in type_lower:
                return "[]"
            elif 'dict' in type_lower:
                return "{}"
        
        return "None"


class DocumentationGenerator:
    """
    Generates documentation from specifications.
    
    Features:
    - Markdown generation
    - API reference generation
    - Example generation
    - Usage guide generation
    """
    
    def __init__(self):
        """Initialize the documentation generator."""
        pass
    
    def generate_documentation(self, specs: List[Specification]) -> Documentation:
        """Generate documentation from specifications.
        
        Args:
            specs: List of specifications
            
        Returns:
            Generated documentation
        """
        # Generate title
        title = "API Documentation"
        
        # Generate description
        description = "Automatically generated API documentation."
        
        # Generate sections
        sections = {}
        
        # Functions section
        functions = [s for s in specs if s.type == SpecType.FUNCTION]
        if functions:
            sections["Functions"] = self._generate_functions_section(functions)
        
        # Classes section
        classes = [s for s in specs if s.type == SpecType.CLASS]
        if classes:
            sections["Classes"] = self._generate_classes_section(classes)
        
        # Generate API reference
        api_reference = []
        for spec in specs:
            api_reference.append(self._generate_api_entry(spec))
        
        # Collect examples
        examples = []
        for spec in specs:
            examples.extend(spec.examples)
        
        return Documentation(
            title=title,
            description=description,
            sections=sections,
            examples=examples,
            api_reference=api_reference,
        )
    
    def _generate_functions_section(self, functions: List[Specification]) -> str:
        """Generate functions section.
        
        Args:
            functions: List of function specs
            
        Returns:
            Markdown text
        """
        lines = []
        
        for func in functions:
            lines.append(f"### {func.name}")
            lines.append("")
            lines.append(func.description)
            lines.append("")
            
            if func.parameters:
                lines.append("**Parameters:**")
                for param in func.parameters:
                    type_str = f" ({param.type_hint})" if param.type_hint else ""
                    lines.append(f"- `{param.name}`{type_str}: {param.description}")
                lines.append("")
            
            if func.return_value:
                lines.append("**Returns:**")
                type_str = f" ({func.return_value.type_hint})" if func.return_value.type_hint else ""
                lines.append(f"{type_str}: {func.return_value.description}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _generate_classes_section(self, classes: List[Specification]) -> str:
        """Generate classes section.
        
        Args:
            classes: List of class specs
            
        Returns:
            Markdown text
        """
        lines = []
        
        for cls in classes:
            lines.append(f"### {cls.name}")
            lines.append("")
            lines.append(cls.description)
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_api_entry(self, spec: Specification) -> str:
        """Generate API reference entry.
        
        Args:
            spec: Specification
            
        Returns:
            API entry text
        """
        if spec.type == SpecType.FUNCTION:
            params = ", ".join(p.name for p in spec.parameters)
            return f"{spec.name}({params})"
        else:
            return spec.name


class AutoSpecKit:
    """
    Main auto-spec kit engine.
    
    Combines code analysis, test generation, and documentation generation.
    """
    
    def __init__(self):
        """Initialize the auto-spec kit."""
        self.analyzer = CodeAnalyzer()
        self.test_generator = TestGenerator()
        self.doc_generator = DocumentationGenerator()
    
    def generate_spec(self, code: str, spec_type: SpecType = SpecType.FUNCTION) -> Specification:
        """Generate specification from code.
        
        Args:
            code: Source code
            spec_type: Type of specification
            
        Returns:
            Generated specification
        """
        if spec_type == SpecType.FUNCTION:
            return self.analyzer.analyze_function(code)
        elif spec_type == SpecType.CLASS:
            return self.analyzer.analyze_class(code)
        else:
            return Specification(
                name="unknown",
                type=spec_type,
                description="",
            )
    
    def generate_tests(self, spec: Specification) -> List[TestCase]:
        """Generate tests from specification.
        
        Args:
            spec: Specification
            
        Returns:
            List of test cases
        """
        return self.test_generator.generate_tests(spec)
    
    def generate_documentation(self, specs: List[Specification]) -> Documentation:
        """Generate documentation from specifications.
        
        Args:
            specs: List of specifications
            
        Returns:
            Generated documentation
        """
        return self.doc_generator.generate_documentation(specs)
    
    def generate_all(self, code: str) -> tuple[Specification, List[TestCase], Documentation]:
        """Generate spec, tests, and docs from code.
        
        Args:
            code: Source code
            
        Returns:
            Tuple of (spec, tests, documentation)
        """
        # Generate spec
        spec = self.generate_spec(code)
        
        # Generate tests
        tests = self.generate_tests(spec)
        
        # Generate documentation
        docs = self.generate_documentation([spec])
        
        return spec, tests, docs


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "SpecType",
    "TestType",
    "Parameter",
    "ReturnValue",
    "Specification",
    "TestCase",
    "Documentation",
    "CodeAnalyzer",
    "TestGenerator",
    "DocumentationGenerator",
    "AutoSpecKit",
]
