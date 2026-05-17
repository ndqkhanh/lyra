---
name: check-environment
description: Check development environment when session starts
type: SessionStart
script: check_environment.py
enabled: true
---

# Check Environment Hook

Checks development environment when session starts.

## Environment Checks

- Verify required tools are installed
- Check Python version
- Validate dependencies
- Check git status

## Usage

This hook runs automatically when a new session starts.
