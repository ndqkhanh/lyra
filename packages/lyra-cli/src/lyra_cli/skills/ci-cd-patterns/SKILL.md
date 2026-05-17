---
name: ci-cd-patterns
description: CI/CD pipeline patterns and best practices
origin: ECC
tags: [ci-cd, devops, automation]
triggers: [ci-cd, pipeline, deployment]
---

# CI/CD Patterns

## Pipeline Stages

1. **Build**: Compile, install dependencies
2. **Test**: Run test suite
3. **Lint**: Code quality checks
4. **Security**: Vulnerability scanning
5. **Deploy**: Deploy to environment

## Best Practices

- Fail fast (run quick tests first)
- Parallel execution where possible
- Cache dependencies
- Use artifacts between stages
- Automated rollback on failure

## Example GitHub Actions

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: pytest
      - name: Check coverage
        run: pytest --cov
```

## Deployment Strategies

- **Blue-Green**: Zero downtime
- **Canary**: Gradual rollout
- **Rolling**: Sequential updates
