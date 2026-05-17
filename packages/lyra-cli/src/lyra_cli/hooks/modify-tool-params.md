---
name: modify-tool-params
description: Modify tool parameters before execution
type: PreToolUse
script: modify_params.py
enabled: true
---

# Modify Tool Parameters Hook

Modifies tool parameters before execution for optimization.

## Modifications

- Normalize file paths
- Add default parameters
- Convert relative to absolute paths
- Apply user preferences

## Usage

This hook runs automatically before any tool execution.
