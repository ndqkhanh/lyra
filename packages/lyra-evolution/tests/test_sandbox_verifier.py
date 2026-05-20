"""Tests for SandboxVerifier."""
from __future__ import annotations

import pytest

from lyra_evolution.sandbox_verifier import SafetyRule, SandboxVerifier
from lyra_evolution.voyager import SkillCandidate


def test_safety_rule_allows_safe_code() -> None:
    safe_code = """
def add(a, b):
    return a + b

result = add(2, 3)
print(result)
"""
    safe, reason = SafetyRule.check(safe_code)
    assert safe is True
    assert "passed" in reason.lower()


def test_safety_rule_blocks_forbidden_import() -> None:
    unsafe_code = """
import os
os.system('ls')
"""
    safe, reason = SafetyRule.check(unsafe_code)
    assert safe is False
    assert "os" in reason


def test_safety_rule_blocks_subprocess_import() -> None:
    unsafe_code = """
import subprocess
subprocess.run(['ls'])
"""
    safe, reason = SafetyRule.check(unsafe_code)
    assert safe is False
    assert "subprocess" in reason


def test_safety_rule_blocks_eval() -> None:
    unsafe_code = """
code = "print('hello')"
eval(code)
"""
    safe, reason = SafetyRule.check(unsafe_code)
    assert safe is False
    assert "eval" in reason


def test_safety_rule_blocks_exec() -> None:
    unsafe_code = """
exec("import os")
"""
    safe, reason = SafetyRule.check(unsafe_code)
    assert safe is False
    assert "exec" in reason


def test_safety_rule_blocks_open() -> None:
    unsafe_code = """
with open('/etc/passwd', 'r') as f:
    data = f.read()
"""
    safe, reason = SafetyRule.check(unsafe_code)
    assert safe is False
    assert "open" in reason


def test_safety_rule_detects_syntax_error() -> None:
    invalid_code = """
def broken(
    print("missing closing paren")
"""
    safe, reason = SafetyRule.check(invalid_code)
    assert safe is False
    assert "syntax" in reason.lower()


def test_sandbox_verifier_accepts_safe_skill() -> None:
    verifier = SandboxVerifier(timeout_seconds=2)
    candidate = SkillCandidate(
        name="add_numbers",
        code="""
def add(a, b):
    return a + b

result = add(2, 3)
print(f"Result: {result}")
""",
        description="Adds two numbers",
    )
    passed, feedback = verifier.verify(candidate)
    assert passed is True
    assert "passed" in feedback.lower()


def test_sandbox_verifier_rejects_unsafe_import() -> None:
    verifier = SandboxVerifier(timeout_seconds=2)
    candidate = SkillCandidate(
        name="unsafe_skill",
        code="""
import os
os.system('echo "hacked"')
""",
        description="Unsafe skill",
    )
    passed, feedback = verifier.verify(candidate)
    assert passed is False
    assert "safety" in feedback.lower() or "forbidden" in feedback.lower()


def test_sandbox_verifier_rejects_timeout() -> None:
    verifier = SandboxVerifier(timeout_seconds=1)
    candidate = SkillCandidate(
        name="infinite_loop",
        code="""
while True:
    pass
""",
        description="Infinite loop",
    )
    passed, feedback = verifier.verify(candidate)
    assert passed is False
    assert "timeout" in feedback.lower()


def test_sandbox_verifier_rejects_runtime_error() -> None:
    verifier = SandboxVerifier(timeout_seconds=2)
    candidate = SkillCandidate(
        name="error_skill",
        code="""
def divide(a, b):
    return a / b

result = divide(10, 0)
""",
        description="Division by zero",
    )
    passed, feedback = verifier.verify(candidate)
    assert passed is False
    assert "failed" in feedback.lower() or "error" in feedback.lower()


def test_sandbox_verifier_rejects_large_output() -> None:
    verifier = SandboxVerifier(timeout_seconds=2, max_output_bytes=100)
    candidate = SkillCandidate(
        name="large_output",
        code="""
for i in range(1000):
    print(f"Line {i}: " + "x" * 100)
""",
        description="Generates large output",
    )
    passed, feedback = verifier.verify(candidate)
    assert passed is False
    assert "output too large" in feedback.lower() or "bytes" in feedback.lower()


def test_voyager_accumulator_integration() -> None:
    from lyra_evolution.voyager import SkillLibrary, VoyagerAccumulator

    library = SkillLibrary()
    verifier = SandboxVerifier(timeout_seconds=2)
    accumulator = VoyagerAccumulator(library, verifier)

    # Submit safe skill
    safe_skill = SkillCandidate(
        name="multiply",
        code="""
def multiply(a, b):
    return a * b

print(multiply(3, 4))
""",
        description="Multiplies two numbers",
    )
    passed, feedback = accumulator.submit(safe_skill)
    assert passed is True
    assert library.size == 1
    assert accumulator.accepted == 1
    assert accumulator.rejected == 0

    # Submit unsafe skill
    unsafe_skill = SkillCandidate(
        name="unsafe",
        code="import os; os.system('ls')",
        description="Unsafe",
    )
    passed, feedback = accumulator.submit(unsafe_skill)
    assert passed is False
    assert library.size == 1  # Still only 1 skill
    assert accumulator.accepted == 1
    assert accumulator.rejected == 1
    assert accumulator.acceptance_rate == 0.5
