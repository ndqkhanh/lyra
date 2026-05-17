---
name: tdd-workflow-required
description: Test-driven development workflow is mandatory
category: Testing
severity: high
enabled: true
---

# TDD Workflow Required

Follow test-driven development workflow for all new features.

## Rule

MANDATORY workflow:
1. Write test first (RED)
2. Run test - it should FAIL
3. Write minimal implementation (GREEN)
4. Run test - it should PASS
5. Refactor (IMPROVE)
6. Verify coverage (80%+)

## Rationale

TDD ensures testable code and catches edge cases early.

## Examples

```python
# Step 1: Write test first
def test_calculate_total():
    assert calculate_total([10, 20, 30]) == 60

# Step 2: Run test - FAILS (function doesn't exist)
# Step 3: Write implementation
def calculate_total(items):
    return sum(items)

# Step 4: Run test - PASSES
# Step 5: Refactor if needed
# Step 6: Verify coverage
```
