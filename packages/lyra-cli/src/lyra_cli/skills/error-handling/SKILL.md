---
name: error-handling
description: Error handling patterns and best practices
origin: ECC
tags: [error-handling, exceptions, patterns]
triggers: [error, exception, handling]
---

# Error Handling

## Principles

- **Fail Fast**: Detect errors early
- **Be Specific**: Use specific exception types
- **Provide Context**: Include helpful error messages
- **Log Appropriately**: Log errors with context
- **Don't Swallow**: Never silently ignore errors

## Patterns

### Try-Except-Finally
```python
try:
    risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    handle_error(e)
finally:
    cleanup()
```

### Custom Exceptions
```python
class ValidationError(Exception):
    pass

raise ValidationError("Invalid email format")
```

### Error Responses
```python
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input",
        "details": {...}
    }
}
```

## Best Practices

- Catch specific exceptions
- Provide user-friendly messages
- Log detailed technical info
- Include error codes
- Document error scenarios
