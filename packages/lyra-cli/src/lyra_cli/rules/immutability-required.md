---
name: immutability-required
description: Always create new objects, never mutate existing ones
category: CodingStandards
severity: high
enabled: true
---

# Immutability Required

Always create new objects instead of mutating existing ones.

## Rule

WRONG: `modify(original, field, value)` → changes original in-place
CORRECT: `update(original, field, value)` → returns new copy with change

## Rationale

Immutable data prevents hidden side effects, makes debugging easier, and enables safe concurrency.

## Examples

```python
# Wrong
def update_user(user, name):
    user.name = name  # Mutates original
    return user

# Correct
def update_user(user, name):
    return User(**{**user.__dict__, 'name': name})  # Returns new copy
```
