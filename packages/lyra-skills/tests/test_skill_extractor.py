"""Red tests for Hermes-style skill extraction from successful trajectories."""
from __future__ import annotations

from lyra_skills.extractor import (
    ExtractorInput,
    ExtractorOutput,
    extract_candidate,
)


def test_extractor_proposes_skill_on_successful_trajectory() -> None:
    result = extract_candidate(
        ExtractorInput(
            task="Add a user registration form with validation",
            outcome_verdict="pass",
            tool_calls=[
                {"name": "Read", "args": {"path": "src/auth.py"}},
                {"name": "Write", "args": {"path": "tests/test_auth.py", "content": "..."}},
                {"name": "Edit", "args": {"path": "src/auth.py", "diff": "..."}},
                {"name": "Bash", "args": {"cmd": "pytest -q"}},
            ],
            skills_used=["edit", "test_gen"],
        )
    )
    assert isinstance(result, ExtractorOutput)
    assert result.promote is True
    assert result.manifest is not None
    assert result.manifest.id
    assert "test" in result.manifest.body.lower() or "edit" in result.manifest.body.lower()


def test_extractor_rejects_failed_trajectory() -> None:
    result = extract_candidate(
        ExtractorInput(
            task="t",
            outcome_verdict="fail",
            tool_calls=[{"name": "Read", "args": {}}],
            skills_used=[],
        )
    )
    assert result.promote is False
    assert "fail" in (result.reason or "").lower()


def test_extractor_rejects_too_short_trajectory() -> None:
    """A trajectory with fewer than 3 tool calls is too small to generalise."""
    result = extract_candidate(
        ExtractorInput(
            task="t",
            outcome_verdict="pass",
            tool_calls=[{"name": "Read", "args": {}}],
            skills_used=[],
        )
    )
    assert result.promote is False


def test_extractor_requires_user_review_flag() -> None:
    """Promote is a proposal; shipping code must gate on user_review."""
    result = extract_candidate(
        ExtractorInput(
            task="Add export-to-csv feature",
            outcome_verdict="pass",
            tool_calls=[
                {"name": "Read", "args": {}},
                {"name": "Write", "args": {}},
                {"name": "Edit", "args": {}},
                {"name": "Bash", "args": {}},
            ],
            skills_used=["edit"],
        )
    )
    assert result.requires_user_review is True
