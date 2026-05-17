---
name: backup-context
description: Backup context before compaction
type: PreCompact
script: backup_context.py
enabled: true
---

# Backup Context Hook

Backs up context before compaction.

## Backup

- Save current conversation state
- Backup project memory
- Archive important context
- Create recovery point

## Usage

This hook runs automatically before context compaction.
