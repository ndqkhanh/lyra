---
name: context-window-management
description: Manage context window efficiently
category: Performance
severity: medium
enabled: true
---

# Context Window Management

Avoid last 20% of context window for complex operations.

## Rule

Avoid last 20% of context window for:
- Large-scale refactoring
- Feature implementation spanning multiple files
- Debugging complex interactions

Lower context sensitivity tasks:
- Single-file edits
- Independent utility creation
- Documentation updates
- Simple bug fixes

## Rationale

Working near context limits can degrade model performance and increase costs.
