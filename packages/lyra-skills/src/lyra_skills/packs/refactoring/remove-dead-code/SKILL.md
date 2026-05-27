---
id: remove-dead-code
name: Remove Dead Code
description: Find and safely remove unreachable code, unused imports, and dead variables.
keywords:
  - dead code
  - unused
  - unreachable
  - remove code
  - clean up
  - delete code
---

1. Use the linter/IDE to find: unused imports, unused variables, unreachable branches.
2. For each finding, verify it's truly dead (not used by reflection, eval, or external consumers).
3. Remove the dead code; do not comment it out.
4. If the code had tests, remove those tests too.
5. Run the test suite; git history preserves the old code if needed.
