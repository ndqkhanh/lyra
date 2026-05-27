---
id: bisect
name: Bisect
description: Binary-search through git history to find the commit that introduced a bug.
keywords:
  - bisect
  - git bisect
  - regression
  - find commit
  - breaking change
---

1. Identify a known-good commit and the known-bad commit (usually HEAD).
2. Run `git bisect start <bad> <good>`.
3. At each step, run the reproduction test and mark `git bisect good` or `git bisect bad`.
4. When bisect completes, inspect the identified commit.
5. Document the breaking change and notify the author if applicable.
