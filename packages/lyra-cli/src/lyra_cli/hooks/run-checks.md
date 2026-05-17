---
name: run-checks
description: Run quality checks after tool execution
type: PostToolUse
script: run_checks.py
enabled: true
---

# Run Checks Hook

Runs quality checks after tool execution.

## Checks

- Lint code for errors
- Check type annotations
- Verify imports are valid
- Run quick tests

## Usage

This hook runs automatically after Write and Edit tool executions.
