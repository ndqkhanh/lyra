---
name: python-patterns
description: Python best practices, idioms, and design patterns
origin: ECC
tags: [python, patterns, best-practices, idioms]
triggers: [python, pythonic, pep8]
---

# Python Patterns

## Overview

Python-specific best practices, idiomatic patterns, and design patterns for writing clean, maintainable Python code.

## When to Use

- Writing new Python code
- Refactoring existing Python code
- Code reviews for Python projects
- Learning Python best practices

## PEP 8 Style Guide

### Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`
- **Dunder**: `__double_underscore__`

### Line Length

- Maximum 79 characters for code
- Maximum 72 characters for docstrings/comments

### Imports

```python
# Standard library
import os
import sys

# Third-party
import requests
import numpy as np

# Local
from myapp import models
from myapp.utils import helper
```

## Pythonic Idioms

### List Comprehensions

```python
# Good
squares = [x**2 for x in range(10)]

# Bad
squares = []
for x in range(10):
    squares.append(x**2)
```

### Context Managers

```python
# Good
with open('file.txt') as f:
    content = f.read()

# Bad
f = open('file.txt')
content = f.read()
f.close()
```

### EAFP vs LBYL

```python
# Good (EAFP - Easier to Ask Forgiveness than Permission)
try:
    value = my_dict[key]
except KeyError:
    value = default

# Bad (LBYL - Look Before You Leap)
if key in my_dict:
    value = my_dict[key]
else:
    value = default
```

### Generators

```python
# Good (memory efficient)
def read_large_file(file_path):
    with open(file_path) as f:
        for line in f:
            yield line.strip()

# Bad (loads entire file)
def read_large_file(file_path):
    with open(file_path) as f:
        return [line.strip() for line in f]
```

## Type Hints

```python
from typing import List, Dict, Optional

def process_items(items: List[str], config: Dict[str, int]) -> Optional[str]:
    """Process items with configuration."""
    if not items:
        return None
    return items[0]
```

## Common Anti-Patterns

### Mutable Default Arguments

```python
# Bad
def append_to(element, target=[]):
    target.append(element)
    return target

# Good
def append_to(element, target=None):
    if target is None:
        target = []
    target.append(element)
    return target
```

### Bare Except

```python
# Bad
try:
    risky_operation()
except:
    pass

# Good
try:
    risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
```

### Using `is` for Value Comparison

```python
# Bad
if x is True:
    pass

# Good
if x:
    pass

# Good (for None checks)
if x is None:
    pass
```

## Design Patterns

### Singleton

```python
class Singleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### Factory

```python
class ShapeFactory:
    @staticmethod
    def create_shape(shape_type: str):
        if shape_type == "circle":
            return Circle()
        elif shape_type == "square":
            return Square()
        raise ValueError(f"Unknown shape: {shape_type}")
```

### Decorator

```python
from functools import wraps

def retry(max_attempts=3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
        return wrapper
    return decorator
```
