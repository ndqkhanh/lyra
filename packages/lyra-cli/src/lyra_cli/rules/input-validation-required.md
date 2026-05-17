---
name: input-validation-required
description: Always validate input at system boundaries
category: Security
severity: critical
enabled: true
---

# Input Validation Required

Validate all input at system boundaries (user input, API requests, file content).

## Rule

- Validate all user input before processing
- Use schema-based validation where available
- Fail fast with clear error messages
- Never trust external data

## Rationale

Unvalidated input is the root cause of many security vulnerabilities (SQL injection, XSS, path traversal).

## Examples

```python
# Wrong
def get_user(user_id):
    return db.query(f"SELECT * FROM users WHERE id = {user_id}")

# Correct
def get_user(user_id: int):
    if not isinstance(user_id, int) or user_id < 1:
        raise ValueError("Invalid user_id")
    return db.query("SELECT * FROM users WHERE id = ?", (user_id,))
```
