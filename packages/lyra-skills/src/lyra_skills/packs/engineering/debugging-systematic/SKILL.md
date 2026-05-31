---
id: debugging-systematic
name: Systematic Debugging
description: Isolate bugs methodically: reproduce, bisect, hypothesize, fix, verify.
keywords:
  - debug
  - debugging
  - bug
  - fix
  - troubleshoot
  - bisect
---

1. Reproduce the bug reliably — create a minimal reproduction case.
2. Gather evidence: logs, stack traces, error messages, relevant configuration, recent changes.
3. Form a hypothesis about the root cause — be specific, not "something is wrong with X".
4. Test the hypothesis: if your hypothesis is correct, what else would be true? Check those predictions.
5. If hypothesis is wrong, form a new one — don't guess randomly; each failed hypothesis narrows the search space.
6. Fix the root cause, not the symptom. Add a regression test.
7. Consider: could the same bug class exist elsewhere in the codebase? Search and fix preventively.
