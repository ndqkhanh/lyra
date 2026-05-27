---
id: extract-method
name: Extract Method
description: Extract a cohesive block of code into a well-named function.
keywords:
  - extract
  - extract method
  - refactor function
  - split function
  - decompose
---

1. Identify a block within a large function that performs one clear task.
2. Verify the block has minimal dependencies on surrounding state.
3. Create a new function with a descriptive name; pass needed state as parameters.
4. Replace the original block with a call to the new function.
5. Run tests to verify no behaviour change.
