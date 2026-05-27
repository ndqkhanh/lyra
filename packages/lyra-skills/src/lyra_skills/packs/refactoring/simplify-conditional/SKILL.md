---
id: simplify-conditional
name: Simplify Conditional
description: Simplify complex boolean expressions and nested conditionals.
keywords:
  - simplify
  - conditional
  - if statement
  - boolean
  - guard clause
  - early return
---

1. Identify deeply nested conditionals (>3 levels) or complex boolean expressions.
2. Apply: guard clauses (early returns), De Morgan's laws, extract boolean variables.
3. Consider replacing complex conditionals with polymorphism or lookup tables.
4. Ensure the simplified logic is equivalent; write truth-table tests if needed.
5. Verify readability: can a new developer understand the control flow in one pass?
