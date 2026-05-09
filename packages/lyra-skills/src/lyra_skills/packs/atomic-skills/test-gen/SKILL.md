---
id: test-gen
name: Test Gen
description: Produce a failing test that captures the user's acceptance criterion.
---

1. Rewrite the user ask as a single assertion.
2. Pick the narrowest test location (unit > integration > e2e).
3. Write one test that fails for the right reason (AssertionError, not ImportError).
4. Run it; attach the RED proof to the session trace.
