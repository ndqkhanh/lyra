"""Tests for the LYRA_CONTEXT_PROFILE knob (Phase CE.1)."""
from __future__ import annotations

from typing import Any

import pytest

from lyra_core.context.profile import (
    MINIMAL,
    STANDARD,
    STRICT,
    ContextProfile,
    list_profiles,
    resolve_profile,
)


def test_default_is_standard_when_no_env_and_no_arg():
    assert resolve_profile(env={}) is STANDARD


def test_empty_env_var_is_treated_as_unset():
    assert resolve_profile(env={"LYRA_CONTEXT_PROFILE": ""}) is STANDARD


def test_explicit_arg_overrides_env():
    p = resolve_profile("minimal", env={"LYRA_CONTEXT_PROFILE": "strict"})
    assert p is MINIMAL


def test_env_is_used_when_arg_is_none():
    assert resolve_profile(env={"LYRA_CONTEXT_PROFILE": "strict"}) is STRICT


def test_lookup_is_case_and_whitespace_tolerant():
    assert resolve_profile("  Minimal  ") is MINIMAL
    assert resolve_profile("STRICT") is STRICT


def test_unknown_profile_name_raises_with_helpful_message():
    with pytest.raises(ValueError) as exc:
        resolve_profile("paranoid")
    msg = str(exc.value)
    assert "paranoid" in msg
    # Surface the valid options so the operator can self-correct.
    assert "minimal" in msg
    assert "standard" in msg
    assert "strict" in msg


@pytest.mark.parametrize("profile", [MINIMAL, STANDARD, STRICT])
def test_profile_invariants(profile: ContextProfile):
    """Each built-in profile must satisfy the value constraints."""
    assert 0.0 < profile.autocompact_pct <= 1.0
    assert profile.keep_last > 0
    assert profile.max_summary_tokens > 0
    assert profile.reduction_cap_kb > 0
    assert profile.mcp_descriptions in {"full", "trimmed", "off"}
    assert profile.session_start_context_bytes >= 0
    assert profile.reasoning_bank_k >= 0


def test_minimal_is_more_aggressive_than_standard():
    """Profiles must form a coherent gradient — minimal squeezes harder."""
    assert MINIMAL.autocompact_pct < STANDARD.autocompact_pct
    assert MINIMAL.keep_last < STANDARD.keep_last
    assert MINIMAL.max_summary_tokens < STANDARD.max_summary_tokens
    assert MINIMAL.reasoning_bank_k < STANDARD.reasoning_bank_k


def test_strict_recalls_more_than_standard():
    """Strict preserves more — bigger keep window, more lessons recalled."""
    assert STRICT.keep_last > STANDARD.keep_last
    assert STRICT.max_summary_tokens > STANDARD.max_summary_tokens
    assert STRICT.reasoning_bank_k > STANDARD.reasoning_bank_k


def test_frozen_dataclass_rejects_mutation():
    with pytest.raises(Exception):  # FrozenInstanceError ⊂ Exception
        STANDARD.autocompact_pct = 0.99  # type: ignore[misc]


def test_list_profiles_returns_three_in_canonical_order():
    profiles = list_profiles()
    assert [p.name for p in profiles] == ["minimal", "standard", "strict"]


@pytest.mark.parametrize(
    "field,value,err_fragment",
    [
        ("autocompact_pct", 0.0, "autocompact_pct"),
        ("autocompact_pct", 1.5, "autocompact_pct"),
        ("keep_last", 0, "keep_last"),
        ("max_summary_tokens", 0, "max_summary_tokens"),
        ("reduction_cap_kb", 0, "reduction_cap_kb"),
        ("mcp_descriptions", "verbose", "mcp_descriptions"),
        ("session_start_context_bytes", -1, "session_start_context_bytes"),
        ("reasoning_bank_k", -1, "reasoning_bank_k"),
    ],
)
def test_custom_profile_validates_each_field(
    field: str, value: object, err_fragment: str
):
    base: dict[str, Any] = dict(
        name="custom",
        autocompact_pct=0.7,
        keep_last=6,
        max_summary_tokens=600,
        reduction_cap_kb=3,
        mcp_descriptions="full",
        session_start_context_bytes=4000,
        reasoning_bank_k=3,
    )
    base[field] = value
    with pytest.raises(ValueError) as exc:
        ContextProfile(**base)
    assert err_fragment in str(exc.value)
