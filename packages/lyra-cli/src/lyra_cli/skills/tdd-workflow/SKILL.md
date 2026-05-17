---
name: tdd-workflow
description: Test-driven development workflow patterns and best practices
origin: ECC
tags: [testing, tdd, workflow, best-practices]
triggers: [tdd, test-driven, red-green-refactor]
---

# TDD Workflow

## Overview

Test-driven development (TDD) is a software development approach where tests are written before implementation code. This skill provides patterns and best practices for effective TDD workflows.

## When to Use

- Implementing new features
- Fixing bugs with unclear root causes
- Refactoring existing code
- When test coverage is below 80%
- Building critical business logic

## Core Principles

### RED-GREEN-REFACTOR Cycle

1. **RED**: Write a failing test that defines desired behavior
2. **GREEN**: Write minimal code to make the test pass
3. **REFACTOR**: Improve code while keeping tests green

### Test First, Always

- Write tests before implementation
- Tests define the API and behavior
- Implementation follows test requirements
- No production code without a failing test first

## Workflow Steps

### 1. Write Failing Test (RED)

```python
def test_user_registration():
    user = register_user("test@example.com", "password123")
    assert user.email == "test@example.com"
    assert user.is_active is True
```

### 2. Run Test - Verify Failure

```bash
pytest tests/test_user.py::test_user_registration
# Should fail with clear error message
```

### 3. Write Minimal Implementation (GREEN)

```python
def register_user(email: str, password: str) -> User:
    return User(email=email, is_active=True)
```

### 4. Run Test - Verify Pass

```bash
pytest tests/test_user.py::test_user_registration
# Should pass
```

### 5. Refactor (IMPROVE)

- Extract duplicates
- Improve naming
- Simplify logic
- Add error handling
- Keep tests green

### 6. Verify Coverage

```bash
pytest --cov=src tests/
# Should show 80%+ coverage
```

## Test Types

### Unit Tests

Test individual functions and methods in isolation.

```python
def test_calculate_total():
    items = [10, 20, 30]
    assert calculate_total(items) == 60
```

### Integration Tests

Test component interactions.

```python
def test_user_registration_flow():
    response = client.post("/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 201
    assert User.objects.filter(email="test@example.com").exists()
```

### E2E Tests

Test critical user flows end-to-end.

```python
def test_complete_checkout_flow(browser):
    browser.visit("/products")
    browser.click("Add to Cart")
    browser.visit("/checkout")
    browser.fill("card_number", "4242424242424242")
    browser.click("Complete Purchase")
    assert browser.is_text_present("Order Confirmed")
```

## Best Practices

### Test Naming

- Use descriptive names: `test_user_cannot_register_with_invalid_email`
- Follow pattern: `test_<what>_<condition>_<expected_result>`
- Be specific about what is being tested

### Test Organization

- One test file per module
- Group related tests in classes
- Use fixtures for common setup
- Keep tests independent

### Test Quality

- Each test should test one thing
- Tests should be fast (<100ms for unit tests)
- Tests should be deterministic (no flaky tests)
- Tests should be readable (clear arrange-act-assert)

### Coverage Goals

- Minimum 80% coverage required
- Focus on critical paths first
- Don't chase 100% coverage blindly
- Test behavior, not implementation

## Common Pitfalls

### Testing Implementation Details

❌ **Bad**: Testing internal methods
```python
def test_internal_helper():
    result = _internal_helper(data)
    assert result == expected
```

✅ **Good**: Testing public API
```python
def test_public_method():
    result = public_method(data)
    assert result == expected
```

### Mocking Too Much

❌ **Bad**: Mocking everything
```python
@patch('module.function1')
@patch('module.function2')
@patch('module.function3')
def test_something(mock3, mock2, mock1):
    # Test becomes brittle
```

✅ **Good**: Mock external dependencies only
```python
@patch('requests.post')
def test_api_call(mock_post):
    # Test actual logic, mock external API
```

### Not Running Tests Frequently

- Run tests after every change
- Use watch mode during development
- Run full suite before commits

## Tools

### Python

- **pytest**: Test framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities
- **hypothesis**: Property-based testing

### Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_user.py::test_registration

# Watch mode
pytest-watch

# Parallel execution
pytest -n auto
```

## Example: Complete TDD Session

```python
# 1. RED: Write failing test
def test_calculate_discount():
    price = 100
    discount_percent = 20
    result = calculate_discount(price, discount_percent)
    assert result == 80

# 2. Run test - fails (function doesn't exist)

# 3. GREEN: Minimal implementation
def calculate_discount(price: float, discount_percent: float) -> float:
    return price - (price * discount_percent / 100)

# 4. Run test - passes

# 5. REFACTOR: Add validation
def calculate_discount(price: float, discount_percent: float) -> float:
    if price < 0 or discount_percent < 0 or discount_percent > 100:
        raise ValueError("Invalid input")
    return price - (price * discount_percent / 100)

# 6. Add test for validation
def test_calculate_discount_invalid_input():
    with pytest.raises(ValueError):
        calculate_discount(-10, 20)

# 7. Run all tests - all pass

# 8. Check coverage
# pytest --cov=src tests/
# Coverage: 100%
```

## References

- Kent Beck: "Test-Driven Development by Example"
- Martin Fowler: "Refactoring"
- pytest documentation: https://docs.pytest.org
