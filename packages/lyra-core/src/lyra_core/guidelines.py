"""
Karpathy Behavioral Guidelines for Lyra

Based on research from andrej-karpathy-skills (125K+ stars)
Implements 4 core behavioral principles to reduce LLM coding mistakes.
"""

KARPATHY_GUIDELINES = """
# Behavioral Guidelines for Code Generation

## 1. Think Before Coding
**Problem**: LLMs make wrong assumptions and run with them without checking.

**Guidelines**:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- Surface inconsistencies and hidden confusion.

**Test**: Did you ask clarifying questions before implementing?

## 2. Simplicity First
**Problem**: LLMs overcomplicate solutions with unnecessary abstractions.

**Guidelines**:
- No features beyond what was asked.
- No abstractions for single-use code.
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Ask yourself: Would a senior engineer say this is overcomplicated?

**Test**: Can you remove code without breaking the requirement?

## 3. Surgical Changes
**Problem**: LLMs touch unrelated code, causing orthogonal changes.

**Guidelines**:
- Only touch what's needed for the user's request.
- No style fixes, no comment updates, no "while we're here" changes.
- Every changed line should trace directly to the user's request.

**Test**: Every changed line traces to user request?

## 4. Goal-Driven Execution
**Problem**: LLMs lack clear success criteria and verification.

**Guidelines**:
- Transform requests into verifiable goals with observable success criteria.
- Write tests that prove completion.
- Verify before claiming done.

**Examples**:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

**Test**: Can you prove the task is complete?

---

**Tradeoff**: These guidelines bias toward caution over speed.
For trivial tasks, use judgment.
"""


def inject_guidelines(system_prompt: str) -> str:
    """
    Inject Karpathy behavioral guidelines into system prompt.

    Args:
        system_prompt: Base system prompt

    Returns:
        Enhanced system prompt with behavioral guidelines
    """
    return f"{system_prompt}\n\n{KARPATHY_GUIDELINES}"


def get_principle_checklist() -> dict:
    """
    Get checklist for each principle.

    Returns:
        Dictionary mapping principle to checklist items
    """
    return {
        "think_before_coding": [
            "Stated assumptions explicitly",
            "Asked clarifying questions",
            "Presented multiple interpretations if ambiguous",
            "Surfaced inconsistencies"
        ],
        "simplicity_first": [
            "No features beyond request",
            "No unnecessary abstractions",
            "No adjacent code improvements",
            "No refactoring of working code"
        ],
        "surgical_changes": [
            "Only touched necessary code",
            "No style fixes",
            "No comment updates",
            "Every line traces to request"
        ],
        "goal_driven": [
            "Defined verifiable success criteria",
            "Wrote tests proving completion",
            "Verified before claiming done"
        ]
    }


def validate_against_principles(
    changes: list[str],
    user_request: str
) -> dict:
    """
    Validate code changes against Karpathy principles.

    Args:
        changes: List of changed lines
        user_request: Original user request

    Returns:
        Validation results with pass/fail for each principle
    """
    results = {
        "surgical_changes": {
            "passed": True,
            "issues": []
        },
        "simplicity_first": {
            "passed": True,
            "issues": []
        }
    }

    # Check for surgical changes
    # (In real implementation, would analyze git diff)
    if len(changes) > 100:
        results["surgical_changes"]["passed"] = False
        results["surgical_changes"]["issues"].append(
            f"Large changeset ({len(changes)} lines) - may include unrelated changes"
        )

    return results


# Export for use in interactive session
__all__ = [
    "KARPATHY_GUIDELINES",
    "inject_guidelines",
    "get_principle_checklist",
    "validate_against_principles"
]
