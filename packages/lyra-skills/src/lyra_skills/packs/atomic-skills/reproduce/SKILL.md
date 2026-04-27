---
id: reproduce
name: Reproduce
description: Turn a vague bug report into a minimal, deterministic repro script or test.
---

1. Extract the observable wrongness from the bug report.
2. Write the smallest script or test that exhibits it.
3. Pin inputs (seed, timestamp, fixture) so the repro is deterministic.
4. Record the exact command + exit code that shows failure.
