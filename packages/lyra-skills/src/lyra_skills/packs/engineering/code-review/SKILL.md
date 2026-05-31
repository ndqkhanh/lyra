---
id: code-review
name: Code Review
description: Systematic code review covering correctness, security, performance, and maintainability.
keywords:
  - code review
  - review
  - audit
  - pull request
  - PR review
---

1. Read the diff or changed files to understand the scope of changes.
2. Check for security issues first: hardcoded secrets, SQL injection, XSS, path traversal.
3. Verify correctness: does this change actually solve the stated problem? Are edge cases handled?
4. Assess performance: N+1 queries, unbounded loops, missing pagination, memory leaks.
5. Review maintainability: clear naming, small functions (<50 lines), single responsibility.
6. Check test coverage: every new behavior has a test, edge cases are covered, tests actually exercise the feature.
7. Produce a structured review with severity (CRITICAL/HIGH/MEDIUM/LOW) and concrete fix suggestions.
