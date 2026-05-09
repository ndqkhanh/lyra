---
id: review
name: Review
description: Critique an agent's change before ship; catch obvious quality and safety issues.
---

Scan for:
- Removed or weakened assertions in tests.
- `assert True`, `pass`, or commented-out test bodies.
- Unrelated file touches beyond the plan.
- New deps that weren't in the plan.
- Secret-shaped strings in edited files.

Report findings by severity; do not auto-fix.
