---
name: testing-patterns
description: Testing strategies and patterns for comprehensive coverage
origin: ECC
tags: [testing, patterns, unit-test, integration-test]
triggers: [testing, test-patterns]
---

# Testing Patterns

## Test Types

### Unit Tests
- Test individual functions in isolation
- Fast (<100ms)
- No external dependencies
- 80%+ coverage required

### Integration Tests
- Test component interactions
- Database, API calls
- Slower but realistic

### E2E Tests
- Test critical user flows
- Browser automation
- Slowest but most realistic

## Patterns

### Arrange-Act-Assert
```python
def test_user_creation():
    # Arrange
    email = "test@example.com"
    
    # Act
    user = create_user(email)
    
    # Assert
    assert user.email == email
```

### Test Fixtures
```python
@pytest.fixture
def sample_user():
    return User(email="test@example.com")
```

### Mocking
```python
@patch('requests.post')
def test_api_call(mock_post):
    mock_post.return_value.status_code = 200
    result = call_api()
    assert result.success
```
