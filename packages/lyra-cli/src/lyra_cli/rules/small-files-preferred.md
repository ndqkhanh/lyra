---
name: small-files-preferred
description: Many small files preferred over few large files
category: CodingStandards
severity: medium
enabled: true
---

# Small Files Preferred

Organize code into many small, focused files rather than few large files.

## Rule

- 200-400 lines typical
- 800 lines maximum
- High cohesion, low coupling
- Organize by feature/domain, not by type

## Rationale

Small files are easier to understand, test, and maintain. They encourage better separation of concerns.

## Examples

```
# Wrong
src/
  utils.py (2000 lines)

# Correct
src/
  utils/
    string_utils.py (200 lines)
    date_utils.py (150 lines)
    validation_utils.py (300 lines)
```
