---
name: cleanup-temp-files
description: Clean up temporary files before session ends
type: Stop
script: cleanup_temp.py
enabled: true
---

# Cleanup Temporary Files Hook

Cleans up temporary files before session ends.

## Cleanup

- Remove temporary test files
- Clean build artifacts
- Remove cache files
- Archive session logs

## Usage

This hook runs automatically when the session ends.
