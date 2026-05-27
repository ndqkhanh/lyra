---
id: flatten-nesting
name: Flatten Nesting
description: Reduce deep nesting in loops and callbacks using early exits and extraction.
keywords:
  - flatten
  - nesting
  - nested
  - callback hell
  - pyramid of doom
  - deep nesting
---

1. Find the most deeply nested block (arrowhead anti-pattern).
2. Apply: early continue/break in loops, early return in functions, extract inner loops.
3. For async code: use async/await instead of .then() chains.
4. For list operations: use map/filter/reduce instead of for-loops with accumulators.
5. Target maximum 3 levels of nesting after refactoring.
