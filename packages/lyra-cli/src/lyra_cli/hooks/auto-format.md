---
name: auto-format
description: Auto-format code after tool execution
type: PostToolUse
script: auto_format.py
enabled: true
---

# Auto-Format Hook

Automatically formats code after tool execution.

## Formatting

- Run language-specific formatters (black, prettier, gofmt)
- Fix import ordering
- Apply consistent style
- Remove trailing whitespace

## Usage

This hook runs automatically after Write and Edit tool executions.
