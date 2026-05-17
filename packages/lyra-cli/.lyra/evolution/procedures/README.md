# Evolution Procedures

This directory contains Python procedures that can be edited by the meta-agent in **Procedure Mode**.

## Purpose

Procedure mode enables the meta-agent to edit the evolution code itself, allowing it to:
- Modify mutation strategies
- Adjust selection algorithms
- Update evaluation logic
- Refine candidate generation

## Structure

Each procedure is a Python file (`.py`) that implements a specific evolution function.

Example:
```python
# mutator.py
def mutate_candidate(candidate, strategy):
    """Mutate a candidate using the given strategy."""
    # Meta-agent can rewrite this function
    pass
```

## Meta-Agent Edits

The meta-agent can:
- Read existing procedures
- Propose new implementations
- Validate syntax before applying
- Log all edits to `archive/meta_edits/`

## Safety

- All edits are syntax-checked before application
- Edit history is preserved in the archive
- Procedures run in the harness-controlled environment
