---
name: test-isolation-required
description: Tests must be isolated and independent
category: Testing
severity: high
enabled: true
---

# Test Isolation Required

Each test must be independent and not rely on other tests.

## Rule

- Tests can run in any order
- No shared state between tests
- Use fixtures for setup/teardown
- Mock external dependencies

## Rationale

Isolated tests are reliable and easier to debug when they fail.

## Examples

```python
# Wrong - tests depend on order
def test_create_user():
    global user_id
    user_id = create_user("test")

def test_get_user():
    user = get_user(user_id)  # Depends on previous test

# Correct - tests are isolated
@pytest.fixture
def user():
    return create_user("test")

def test_create_user(user):
    assert user.name == "test"

def test_get_user(user):
    fetched = get_user(user.id)
    assert fetched.name == "test"
```
