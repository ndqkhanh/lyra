---
id: trace-error
name: Trace Error
description: Follow a stack trace back to the root cause and produce a minimal reproduction.
keywords:
  - trace
  - error
  - stack trace
  - exception
  - crash
  - traceback
  - backtrace
---

1. Read the full stack trace; note the innermost frame that originates from project code (not third-party).
2. Open the file at that frame; understand what state could trigger the error.
3. Write a minimal reproduction script or test that triggers the same error.
4. If the error is a regression, bisect to find the breaking commit.
5. Suggest a fix with rationale; keep the diff minimal.
