---
name: preserve-state
description: Preserve critical state before compaction
type: PreCompact
script: preserve_state.py
enabled: true
---

# Preserve State Hook

Preserves critical state before compaction.

## State Preservation

- Mark important messages
- Preserve task list
- Save active modes
- Protect user directives

## Usage

This hook runs automatically before context compaction.
