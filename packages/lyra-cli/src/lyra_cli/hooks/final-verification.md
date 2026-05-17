---
name: final-verification
description: Run final verification before session ends
type: Stop
script: final_verification.py
enabled: true
---

# Final Verification Hook

Runs final verification checks before session ends.

## Verification

- Check all tests pass
- Verify no uncommitted changes
- Check code quality metrics
- Validate documentation is updated

## Usage

This hook runs automatically when the session ends.
