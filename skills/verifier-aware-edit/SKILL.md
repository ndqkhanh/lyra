---
name: 'verifier-aware-edit'
description: 'When the cross-channel verifier rejects, fold the diagnostic into the next attempt.'
version: '0.1.0'
triggers: ['verifier-reject', 'critique']
tags: ['discipline', 'evolution']
---

# Goal
Treat verifier rejections as actionable diagnostics, not as opaque
failures.

# Constraints & Style
- Read the rejection's structured fields (`channel`, `expected`, `actual`).
- Fold the missing constraint into the next attempt as an explicit
  bullet under `# Constraints & Style`.
- Do not silently retry the same edit; the next attempt must visibly
  reflect the diagnostic.
- After 3 rejections in a row, escalate via `BL-LYRA-SKILL-COST`.

# Workflow
1. Detect verifier-reject event.
2. Parse the diagnostic into a constraint sentence.
3. Append the constraint to the active skill's prompt body.
4. Re-attempt the edit; verify; loop.
