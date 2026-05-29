"""Tests for Auto-Spec Kit."""

import pytest
from lyra_cli.auto_spec_kit import (
    AutoSpecKit,
    CodeAnalyzer,
    DocumentationGenerator,
    Parameter,
    Specification,
    SpecType,
    TestCase,
    TestGenerator,
    TestType,
)

# ============================================================================
# Parameter Tests
# ============================================================================

def test_parameter_creation():
    """Test creating a parameter."""
    param = Parameter(
        name="value",
        type_hint="int",
        default="42",
        description="A test parameter",
    )

    assert param.name == "value"
    assert param.type_hint == "int"
    assert param.default == "42"


# ============================================================================
# Specification Tests
# ============================================================================

def test_specification_creation():
    """Test creating a specification."""
    spec = Specification(
        name="test_function",
        type=SpecType.FUNCTION,
        description="A test function",
    )

    assert spec.name == "test_function"
    assert spec.type == SpecType.FUNCTION
    assert spec.description == "A test function"


# ============================================================================
# TestCase Tests
# ============================================================================

def test_test_case_creation():
    """Test creating a test case."""
    test = TestCase(
        name="test_example",
        type=TestType.UNIT,
        description="A test case",
        code="result = function()",
    )

    assert test.name == "test_example"
    assert test.type == TestType.UNIT
    assert test.code == "result = function()"


# ============================================================================
# CodeAnalyzer Tests
# ============================================================================

@pytest.fixture
def analyzer():
    """Create a code analyzer."""
    return CodeAnalyzer()


def test_analyzer_creation(analyzer):
    """Test creating an analyzer."""
    assert analyzer is not None


def test_analyzer_analyze_function(analyzer):
    """Test analyzing a function."""
    code = """
def add(a: int, b: int) -> int:
    '''Add two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    '''
    return a + b
"""

    spec = analyzer.analyze_function(code)

    assert spec.name == "add"
    assert spec.type == SpecType.FUNCTION
    assert len(spec.parameters) == 2


def test_analyzer_analyze_function_no_type_hints(analyzer):
    """Test analyzing function without type hints."""
    code = """
def multiply(x, y):
    return x * y
"""

    spec = analyzer.analyze_function(code)

    assert spec.name == "multiply"
    assert len(spec.parameters) == 2


def test_analyzer_analyze_class(analyzer):
    """Test analyzing a class."""
    code = """
class Calculator:
    '''A simple calculator.'''

    def add(self, a, b):
        return a + b
"""

    spec = analyzer.analyze_class(code)

    assert spec.name == "Calculator"
    assert spec.type == SpecType.CLASS


def test_analyzer_parse_docstring(analyzer):
    """Test parsing docstring."""
    docstring = """
    A test function.

    Example:
        result = test()
    """

    description, examples = analyzer._parse_docstring(docstring)

    assert "test function" in description.lower()
    assert len(examples) > 0


def test_analyzer_handle_invalid_code(analyzer):
    """Test handling invalid code."""
    code = "invalid python code !!!"

    spec = analyzer.analyze_function(code)

    # Should return minimal spec
    assert spec.name == "unknown"


# ============================================================================
# TestGenerator Tests
# ============================================================================

@pytest.fixture
def generator():
    """Create a test generator."""
    return TestGenerator()


def test_generator_creation(generator):
    """Test creating a generator."""
    assert generator is not None


def test_generator_generate_tests(generator):
    """Test generating tests."""
    spec = Specification(
        name="test_function",
        type=SpecType.FUNCTION,
        description="A test function",
        parameters=[
            Parameter(name="value", type_hint="int"),
        ],
    )

    tests = generator.generate_tests(spec)

    assert len(tests) > 0


def test_generator_generate_basic_test(generator):
    """Test generating basic test."""
    spec = Specification(
        name="add",
        type=SpecType.FUNCTION,
        description="Add two numbers",
        parameters=[
            Parameter(name="a", type_hint="int"),
            Parameter(name="b", type_hint="int"),
        ],
    )

    test = generator._generate_basic_test(spec)

    assert test.name == "test_add_basic"
    assert test.type == TestType.UNIT


def test_generator_generate_edge_case_tests(generator):
    """Test generating edge case tests."""
    spec = Specification(
        name="process",
        type=SpecType.FUNCTION,
        description="Process data",
        parameters=[
            Parameter(name="data", type_hint="str"),
        ],
    )

    tests = generator._generate_edge_case_tests(spec)

    assert len(tests) > 0
    assert any(t.type == TestType.EDGE_CASE for t in tests)


def test_generator_generate_property_tests(generator):
    """Test generating property tests."""
    spec = Specification(
        name="normalize",
        type=SpecType.FUNCTION,
        description="Normalize value",
        parameters=[
            Parameter(name="value", type_hint="float"),
        ],
    )

    tests = generator._generate_property_tests(spec)

    assert len(tests) > 0
    assert any(t.type == TestType.PROPERTY for t in tests)


def test_generator_generate_sample_value(generator):
    """Test generating sample values."""
    param_int = Parameter(name="x", type_hint="int")
    param_str = Parameter(name="s", type_hint="str")
    param_bool = Parameter(name="b", type_hint="bool")

    assert generator._generate_sample_value(param_int) == "42"
    assert generator._generate_sample_value(param_str) == "'test'"
    assert generator._generate_sample_value(param_bool) == "True"


# ============================================================================
# DocumentationGenerator Tests
# ============================================================================

@pytest.fixture
def doc_generator():
    """Create a documentation generator."""
    return DocumentationGenerator()


def test_doc_generator_creation(doc_generator):
    """Test creating a documentation generator."""
    assert doc_generator is not None


def test_doc_generator_generate_documentation(doc_generator):
    """Test generating documentation."""
    specs = [
        Specification(
            name="add",
            type=SpecType.FUNCTION,
            description="Add two numbers",
        ),
    ]

    docs = doc_generator.generate_documentation(specs)

    assert docs.title == "API Documentation"
    assert len(docs.api_reference) > 0


def test_doc_generator_generate_functions_section(doc_generator):
    """Test generating functions section."""
    functions = [
        Specification(
            name="add",
            type=SpecType.FUNCTION,
            description="Add two numbers",
            parameters=[
                Parameter(name="a", type_hint="int"),
                Parameter(name="b", type_hint="int"),
            ],
        ),
    ]

    section = doc_generator._generate_functions_section(functions)

    assert "add" in section
    assert "Parameters" in section


def test_doc_generator_generate_classes_section(doc_generator):
    """Test generating classes section."""
    classes = [
        Specification(
            name="Calculator",
            type=SpecType.CLASS,
            description="A calculator class",
        ),
    ]

    section = doc_generator._generate_classes_section(classes)

    assert "Calculator" in section


def test_doc_generator_generate_api_entry(doc_generator):
    """Test generating API entry."""
    spec = Specification(
        name="multiply",
        type=SpecType.FUNCTION,
        description="Multiply numbers",
        parameters=[
            Parameter(name="x"),
            Parameter(name="y"),
        ],
    )

    entry = doc_generator._generate_api_entry(spec)

    assert "multiply" in entry
    assert "x" in entry
    assert "y" in entry


# ============================================================================
# AutoSpecKit Tests
# ============================================================================

@pytest.fixture
def kit():
    """Create an auto-spec kit."""
    return AutoSpecKit()


def test_kit_creation(kit):
    """Test creating a kit."""
    assert kit.analyzer is not None
    assert kit.test_generator is not None
    assert kit.doc_generator is not None


def test_kit_generate_spec(kit):
    """Test generating specification."""
    code = """
def subtract(a: int, b: int) -> int:
    return a - b
"""

    spec = kit.generate_spec(code)

    assert spec.name == "subtract"
    assert spec.type == SpecType.FUNCTION


def test_kit_generate_tests(kit):
    """Test generating tests."""
    spec = Specification(
        name="divide",
        type=SpecType.FUNCTION,
        description="Divide numbers",
        parameters=[
            Parameter(name="a", type_hint="float"),
            Parameter(name="b", type_hint="float"),
        ],
    )

    tests = kit.generate_tests(spec)

    assert len(tests) > 0


def test_kit_generate_documentation(kit):
    """Test generating documentation."""
    specs = [
        Specification(
            name="power",
            type=SpecType.FUNCTION,
            description="Raise to power",
        ),
    ]

    docs = kit.generate_documentation(specs)

    assert docs.title == "API Documentation"


def test_kit_generate_all(kit):
    """Test generating everything."""
    code = """
def square(x: int) -> int:
    '''Square a number.'''
    return x * x
"""

    spec, tests, docs = kit.generate_all(code)

    assert spec.name == "square"
    assert len(tests) > 0
    assert docs.title == "API Documentation"


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow(kit):
    """Test complete workflow."""
    code = """
def factorial(n: int) -> int:
    '''Calculate factorial.

    Args:
        n: Input number

    Returns:
        Factorial of n

    Example:
        factorial(5) == 120
    '''
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""

    # Generate spec
    spec = kit.generate_spec(code)
    assert spec.name == "factorial"

    # Generate tests
    tests = kit.generate_tests(spec)
    assert len(tests) > 0

    # Generate docs
    docs = kit.generate_documentation([spec])
    assert "factorial" in docs.api_reference[0]


def test_class_workflow(kit):
    """Test workflow with class."""
    code = """
class Stack:
    '''A simple stack implementation.'''

    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)
"""

    spec = kit.generate_spec(code, SpecType.CLASS)

    assert spec.name == "Stack"
    assert spec.type == SpecType.CLASS


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_code(kit):
    """Test with empty code."""
    spec = kit.generate_spec("")

    assert spec.name == "unknown"


def test_complex_function(kit):
    """Test with complex function."""
    code = """
def complex_function(
    a: int,
    b: str = "default",
    *args,
    **kwargs
) -> dict:
    '''A complex function.'''
    return {}
"""

    spec = kit.generate_spec(code)

    assert spec.name == "complex_function"


def test_no_parameters(kit):
    """Test function with no parameters."""
    code = """
def get_constant() -> int:
    return 42
"""

    spec = kit.generate_spec(code)

    assert spec.name == "get_constant"
    assert len(spec.parameters) == 0


# ============================================================================
# Performance Tests
# ============================================================================

def test_analyzer_performance(analyzer):
    """Test analyzer performance."""
    import time

    code = """
def test_function(a: int, b: int) -> int:
    return a + b
"""

    start = time.time()
    for _ in range(100):
        analyzer.analyze_function(code)
    duration = time.time() - start

    # Should be fast
    assert duration < 1.0


def test_generator_performance(generator):
    """Test generator performance."""
    import time

    spec = Specification(
        name="test",
        type=SpecType.FUNCTION,
        description="Test",
        parameters=[Parameter(name="x")],
    )

    start = time.time()
    for _ in range(100):
        generator.generate_tests(spec)
    duration = time.time() - start

    # Should be fast
    assert duration < 1.0


def test_kit_performance(kit):
    """Test kit performance."""
    import time

    code = """
def test(x: int) -> int:
    return x * 2
"""

    start = time.time()
    for _ in range(50):
        kit.generate_all(code)
    duration = time.time() - start

    # Should be reasonably fast
    assert duration < 2.0
