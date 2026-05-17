---
name: validate-tool-params
description: Validate tool parameters before execution
type: PreToolUse
script: validate_params.py
enabled: true
---

# Validate Tool Parameters Hook

Validates tool parameters before execution to prevent errors.

## Validation Rules

- Check required parameters are present
- Validate parameter types
- Check file paths exist
- Validate ranges and constraints

## Usage

This hook runs automatically before any tool execution.
