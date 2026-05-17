---
name: minimum-test-coverage
description: Minimum 80% test coverage required
category: Testing
severity: critical
enabled: true
---

# Minimum Test Coverage: 80%

All code must have at least 80% test coverage.

## Rule

Test Types (ALL required):
1. **Unit Tests** - Individual functions, utilities, components
2. **Integration Tests** - API endpoints, database operations
3. **E2E Tests** - Critical user flows

## Rationale

High test coverage catches bugs early and enables confident refactoring.

## Verification

```bash
pytest --cov=src --cov-report=term-missing
# Coverage must be >= 80%
```
