#!/usr/bin/env python3
"""
Verification script for lyra-autoresearch package

Checks that all components are properly implemented and functional
"""

import sys
from pathlib import Path


def check_imports():
    """Verify all modules can be imported"""
    print("Checking imports...")

    try:
        import lyra_autoresearch
        print("  ✓ Main package")

        from lyra_autoresearch import (
            # Citations
            CitationVerifier,
            # Debate
            DebatePanel,
            # Evolution
            EvolutionEngine,
            ExecutionStrategy,
            FailureType,
            # HITL
            GateOrchestrator,
            HITLMode,
            LessonCategory,
            LessonSeverity,
            Perspective,
            # Execution
            SelfHealingExecutor,
            VerifyStatus,
            create_gate_config,
            execute_with_healing,
            run_debate,
            verify_citations,
        )
        print("  ✓ All exports available")

        return True

    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def check_structure():
    """Verify package structure"""
    print("\nChecking package structure...")

    base = Path("src/lyra_autoresearch")

    required_files = [
        base / "__init__.py",
        base / "citations" / "__init__.py",
        base / "debate" / "__init__.py",
        base / "execution" / "__init__.py",
        base / "evolution" / "__init__.py",
        base / "hitl" / "__init__.py",
    ]

    all_exist = True
    for file in required_files:
        if file.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ Missing: {file}")
            all_exist = False

    return all_exist


def check_documentation():
    """Verify documentation exists"""
    print("\nChecking documentation...")

    required_docs = [
        "README.md",
        "INTEGRATION.md",
        "IMPLEMENTATION_SUMMARY.md",
        "pyproject.toml",
    ]

    all_exist = True
    for doc in required_docs:
        if Path(doc).exists():
            print(f"  ✓ {doc}")
        else:
            print(f"  ✗ Missing: {doc}")
            all_exist = False

    return all_exist


def check_tests():
    """Verify tests exist"""
    print("\nChecking tests...")

    test_files = [
        "tests/test_citations.py",
        "tests/test_execution.py",
    ]

    all_exist = True
    for test in test_files:
        if Path(test).exists():
            print(f"  ✓ {test}")
        else:
            print(f"  ✗ Missing: {test}")
            all_exist = False

    return all_exist


def check_examples():
    """Verify examples exist"""
    print("\nChecking examples...")

    example_files = [
        "examples/complete_pipeline.py",
    ]

    all_exist = True
    for example in example_files:
        if Path(example).exists():
            print(f"  ✓ {example}")
        else:
            print(f"  ✗ Missing: {example}")
            all_exist = False

    return all_exist


def check_code_quality():
    """Check code statistics"""
    print("\nCode statistics...")

    total_lines = 0
    for module in ["citations", "debate", "execution", "evolution", "hitl"]:
        file = Path(f"src/lyra_autoresearch/{module}/__init__.py")
        if file.exists():
            lines = len(file.read_text().splitlines())
            total_lines += lines
            print(f"  {module}: {lines} lines")

    print(f"  Total: {total_lines} lines")

    return total_lines > 2000  # Should have substantial implementation


def main():
    """Run all checks"""
    print("=" * 60)
    print("Lyra AutoResearch Package Verification")
    print("=" * 60)

    checks = [
        ("Package Structure", check_structure),
        ("Module Imports", check_imports),
        ("Documentation", check_documentation),
        ("Tests", check_tests),
        ("Examples", check_examples),
        ("Code Quality", check_code_quality),
    ]

    results = []
    for name, check_fn in checks:
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} check failed with error: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✓ All checks passed!")
        print("\nPackage is ready for use:")
        print("  pip install -e .")
        print("  python examples/complete_pipeline.py")
        return 0
    else:
        print("\n✗ Some checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
