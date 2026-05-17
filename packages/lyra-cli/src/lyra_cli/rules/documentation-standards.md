---
name: documentation-standards
description: Maintain clear and up-to-date documentation
category: Documentation
severity: medium
enabled: true
---

# Documentation Standards

Maintain clear and up-to-date documentation for all code.

## Rule

- Document public APIs and interfaces
- Keep README files current
- Update docs when code changes
- Include usage examples
- Document non-obvious behavior

## Rationale

Good documentation reduces onboarding time and prevents misuse.

## Examples

```python
def calculate_total(items: List[float], tax_rate: float = 0.1) -> float:
    """Calculate total with tax.
    
    Args:
        items: List of item prices
        tax_rate: Tax rate as decimal (default 0.1 = 10%)
        
    Returns:
        Total price including tax
        
    Example:
        >>> calculate_total([10.0, 20.0], 0.15)
        34.5
    """
    subtotal = sum(items)
    return subtotal * (1 + tax_rate)
```
