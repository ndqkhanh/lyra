---
name: conventional-commits-required
description: Use conventional commit format for all commits
category: GitWorkflow
severity: high
enabled: true
---

# Conventional Commits Required

All commits must follow conventional commit format.

## Rule

Format: `<type>: <description>`

Types: feat, fix, refactor, docs, test, chore, perf, ci

## Examples

```
feat: add user authentication
fix: resolve memory leak in cache
refactor: simplify error handling
docs: update API documentation
test: add integration tests for auth
```

## Rationale

Conventional commits enable automated changelog generation and semantic versioning.
