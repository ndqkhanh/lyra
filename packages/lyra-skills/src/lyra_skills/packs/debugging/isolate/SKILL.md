---
id: isolate
name: Isolate
description: Narrow a bug to the smallest possible reproducing case by eliminating variables.
keywords:
  - isolate
  - narrow
  - minimal
  - reproduce
  - reproduction
  - isolate bug
---

1. Identify all inputs and state that could affect the buggy behaviour.
2. Remove or mock one variable at a time; re-run the repro after each change.
3. Stop when removing anything further makes the bug disappear.
4. Document the minimal failing case: inputs, expected output, actual output.
5. File the isolated repro as a test case.
