---
id: simplicity-first
name: Simplicity First
description: Prefer the simplest thing that could work; add complexity only when a test demands it.
---

If two designs solve the problem, ship the one with:
- Fewer branches.
- Fewer dependencies.
- Fewer special cases.

When tempted to add configurability "for later", don't — a new test will force the right abstraction.
