---
name: refactoring-patterns
description: Code refactoring techniques and patterns
origin: ECC
tags: [refactoring, clean-code, patterns]
triggers: [refactor, cleanup, improve]
---

# Refactoring Patterns

## When to Refactor

- Code smells detected
- Before adding new features
- After bug fixes
- During code reviews
- When tests are green

## Common Refactorings

### Extract Function
```python
# Before
def process():
    # 50 lines of code
    
# After
def process():
    validate_input()
    transform_data()
    save_result()
```

### Extract Variable
```python
# Before
if user.age > 18 and user.verified and user.active:

# After
is_eligible = user.age > 18 and user.verified and user.active
if is_eligible:
```

### Remove Duplication
```python
# Before
def calc_a(): return x * 2 + 5
def calc_b(): return y * 2 + 5

# After
def calc(val): return val * 2 + 5
```

## Code Smells

- Long functions (>50 lines)
- Large files (>800 lines)
- Deep nesting (>4 levels)
- Duplicate code
- Magic numbers
- God objects
