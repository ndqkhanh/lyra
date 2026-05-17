---
name: testing-strategies
description: Testing strategies for different project types
origin: ECC
tags: [testing, strategy, coverage]
triggers: [test-strategy, testing-approach]
---

# Testing Strategies

## Test Pyramid

- **Unit Tests (70%)**: Fast, isolated, many
- **Integration Tests (20%)**: Component interactions
- **E2E Tests (10%)**: Critical user flows

## Coverage Strategy

- Minimum 80% coverage
- Focus on critical paths first
- Test edge cases
- Test error scenarios
- Don't chase 100% blindly

## Test Organization

```
tests/
├── unit/
│   ├── test_models.py
│   └── test_utils.py
├── integration/
│   ├── test_api.py
│   └── test_database.py
└── e2e/
    └── test_user_flows.py
```

## Best Practices

- Keep tests independent
- Use fixtures for setup
- Mock external dependencies
- Run tests in CI/CD
- Maintain test quality
