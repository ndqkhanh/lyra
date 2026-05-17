---
name: comprehensive-error-handling
description: Always handle errors comprehensively
category: CodingStandards
severity: high
enabled: true
---

# Comprehensive Error Handling

Handle errors explicitly at every level with clear messages.

## Rule

- Handle errors explicitly at every level
- Provide user-friendly error messages in UI-facing code
- Log detailed error context on the server side
- Never silently swallow errors

## Rationale

Proper error handling prevents silent failures and makes debugging easier.

## Examples

```python
# Wrong
try:
    result = risky_operation()
except:
    pass  # Silent failure

# Correct
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise UserFacingError("Unable to complete operation") from e
```
