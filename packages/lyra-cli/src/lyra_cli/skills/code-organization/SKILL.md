---
name: code-organization
description: Code organization and file structure patterns
origin: ECC
tags: [organization, structure, architecture]
triggers: [organization, structure, layout]
---

# Code Organization

## Principles

- **High Cohesion**: Related code together
- **Low Coupling**: Minimal dependencies
- **Clear Boundaries**: Defined interfaces
- **Consistent Structure**: Predictable layout

## File Organization

### By Feature (Recommended)
```
src/
├── users/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   └── tests.py
├── orders/
│   ├── models.py
│   ├── views.py
│   └── tests.py
```

### By Type (Alternative)
```
src/
├── models/
├── views/
├── serializers/
└── tests/
```

## File Size Guidelines

- Functions: <50 lines
- Files: <800 lines
- Extract when exceeding limits

## Best Practices

- One class per file (when large)
- Group related functionality
- Clear naming conventions
- Consistent structure across project
