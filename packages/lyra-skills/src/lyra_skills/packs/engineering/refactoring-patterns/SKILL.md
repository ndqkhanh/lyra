---
id: refactoring-patterns
name: Refactoring Patterns
description: Apply proven refactoring patterns: extract method, inline, replace conditional with polymorphism.
keywords:
  - refactor
  - refactoring
  - extract
  - clean code
  - simplify
---

1. Identify the code smell: long method, duplicate code, feature envy, shotgun surgery, divergent change.
2. Write/run existing tests to establish a safety net before refactoring.
3. Apply the smallest refactoring that addresses the smell: extract method, inline temp, replace conditional with polymorphism, introduce parameter object.
4. Re-run tests after each refactoring step — never batch multiple refactorings between test runs.
5. Verify the refactored code is simpler (fewer lines, fewer branches, clearer intent) while preserving all behavior.
6. Document the pattern applied for future readers.
