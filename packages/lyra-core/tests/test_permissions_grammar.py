"""Tests for ``lyra_core.permissions.grammar`` — Claude-Code-style rules."""
from __future__ import annotations

import pytest

from lyra_core.permissions.grammar import (
    Policy,
    Rule,
    RuleParseError,
    Verdict,
    parse_rule,
    policy_from_mapping,
)


# ---------------------------------------------------------------------------
# parse_rule
# ---------------------------------------------------------------------------


class TestParseRule:
    def test_bare_tool_rule_has_no_specifier(self) -> None:
        rule = parse_rule("Read")
        assert rule.tool == "Read"
        assert rule.specifier is None
        assert rule.is_bare

    def test_specifier_is_extracted(self) -> None:
        rule = parse_rule("Bash(git push *)")
        assert rule.tool == "Bash"
        assert rule.specifier == "git push *"
        assert not rule.is_bare

    def test_strips_outer_whitespace(self) -> None:
        rule = parse_rule("  Read( ./src/** )  ")
        assert rule.tool == "Read"
        assert rule.specifier == "./src/**"

    def test_empty_specifier_means_bare(self) -> None:
        rule = parse_rule("Bash()")
        assert rule.is_bare

    def test_empty_string_raises(self) -> None:
        with pytest.raises(RuleParseError):
            parse_rule("")

    def test_invalid_chars_raise(self) -> None:
        with pytest.raises(RuleParseError):
            parse_rule("Bash{git push}")

    def test_source_preserved(self) -> None:
        # Source text is retained verbatim (sans outer whitespace) so
        # the REPL can show "rule that fired: Bash(git push *)" exactly
        # as the user wrote it in settings.
        rule = parse_rule("  Bash(git push *)  ")
        assert rule.source == "Bash(git push *)"


# ---------------------------------------------------------------------------
# Policy.decide — Bash matcher (with VAR=val stripping)
# ---------------------------------------------------------------------------


class TestBashMatcher:
    def test_simple_command_matches(self) -> None:
        policy = Policy.from_strings(allow=["Bash(git push *)"])
        result = policy.decide("Bash", {"command": "git push origin main"})
        assert result.verdict is Verdict.ALLOW

    def test_var_assignment_is_stripped(self) -> None:
        # ``FOO=bar git push`` should still match ``Bash(git push *)``.
        policy = Policy.from_strings(allow=["Bash(git push *)"])
        result = policy.decide("Bash", {"command": "FOO=bar git push origin main"})
        assert result.verdict is Verdict.ALLOW

    def test_multiple_var_assignments_stripped(self) -> None:
        policy = Policy.from_strings(allow=["Bash(npm test*)"])
        result = policy.decide(
            "Bash", {"command": "FOO=1 BAR=2 npm test -- --watch"}
        )
        assert result.verdict is Verdict.ALLOW

    def test_compound_command_does_not_strip_after_amp(self) -> None:
        # We only strip VAR=val from the *start*; ``X=1 && cmd`` matches
        # cmd-side rules, but ``cmd && X=1 git push`` does NOT —
        # otherwise users could bypass deny-rules by chaining.
        policy = Policy.from_strings(deny=["Bash(rm -rf *)"])
        result = policy.decide(
            "Bash", {"command": "echo ok && rm -rf /"}
        )
        # Glob pattern won't match "echo ok && rm -rf /" wholesale,
        # so this falls through to default (ASK for non-read-only).
        assert result.verdict is not Verdict.DENY


# ---------------------------------------------------------------------------
# Policy.decide — path matcher with ** support
# ---------------------------------------------------------------------------


class TestPathMatcher:
    def test_double_star_matches_any_depth(self) -> None:
        policy = Policy.from_strings(deny=["Read(./.env*)"])
        result = policy.decide("Read", {"path": "./.env.production"})
        assert result.verdict is Verdict.DENY

    def test_src_glob_matches_nested(self) -> None:
        policy = Policy.from_strings(ask=["Edit(./src/**)"])
        result = policy.decide("Edit", {"path": "./src/components/Button.tsx"})
        assert result.verdict is Verdict.ASK

    def test_pattern_field_used_for_glob_grep(self) -> None:
        # Grep / Glob use ``pattern`` not ``path``; the matcher should
        # pick up either field.
        policy = Policy.from_strings(allow=["Grep(*.py)"])
        result = policy.decide("Grep", {"pattern": "foo.py"})
        assert result.verdict is Verdict.ALLOW

    def test_no_path_arg_does_not_match_specifier(self) -> None:
        policy = Policy.from_strings(deny=["Edit(./.env*)"])
        # Edit invocation with no path field — specifier doesn't match,
        # falls through to default (ASK for write tools).
        result = policy.decide("Edit", {})
        assert result.verdict is Verdict.ASK


# ---------------------------------------------------------------------------
# Policy.decide — precedence (deny → ask → allow)
# ---------------------------------------------------------------------------


class TestPrecedence:
    def test_deny_beats_allow(self) -> None:
        policy = Policy.from_strings(
            deny=["Bash(rm *)"],
            allow=["Bash(rm *)"],
        )
        result = policy.decide("Bash", {"command": "rm foo.txt"})
        assert result.verdict is Verdict.DENY

    def test_ask_beats_allow(self) -> None:
        policy = Policy.from_strings(
            ask=["Edit(./src/**)"],
            allow=["Edit(./src/**)"],
        )
        result = policy.decide("Edit", {"path": "./src/foo.py"})
        assert result.verdict is Verdict.ASK

    def test_first_match_wins_within_a_list(self) -> None:
        policy = Policy.from_strings(
            allow=["Bash(git status)", "Bash(git *)"],
        )
        result = policy.decide("Bash", {"command": "git status"})
        assert result.verdict is Verdict.ALLOW
        # Source text identifies *which* rule fired — useful for
        # operator-facing "rule X fired" toasts.
        assert result.rule.source == "Bash(git status)"


# ---------------------------------------------------------------------------
# Default verdicts when no user rules match
# ---------------------------------------------------------------------------


class TestDefaultVerdict:
    def test_read_only_tools_default_allow(self) -> None:
        policy = Policy()  # empty
        for tool in ("Read", "Glob", "Grep", "LSP"):
            assert policy.decide(tool, {}).verdict is Verdict.ALLOW

    def test_write_exec_tools_default_ask(self) -> None:
        policy = Policy()
        for tool in ("Edit", "Write", "Bash", "WebFetch"):
            assert policy.decide(tool, {}).verdict is Verdict.ASK

    def test_default_rule_source_is_synthetic(self) -> None:
        match = Policy().decide("Read", {})
        assert match.rule.source == "<default>"


# ---------------------------------------------------------------------------
# policy_from_mapping (settings.json shape)
# ---------------------------------------------------------------------------


class TestPolicyFromMapping:
    def test_full_shape(self) -> None:
        policy = policy_from_mapping(
            {
                "permissions": {
                    "allow": ["Read", "Bash(git status)"],
                    "ask":   ["Edit(./src/**)"],
                    "deny":  ["Bash(rm -rf *)", "Read(./.env*)"],
                }
            }
        )
        assert len(policy.allow) == 2
        assert len(policy.ask) == 1
        assert len(policy.deny) == 2

    def test_missing_keys_treated_as_empty(self) -> None:
        # Partial settings files are common; load shouldn't require
        # the user to declare empty arrays for the lists they don't use.
        policy = policy_from_mapping({"permissions": {"deny": ["Bash(rm *)"]}})
        assert policy.allow == ()
        assert policy.ask == ()
        assert len(policy.deny) == 1

    def test_unwrapped_block_also_accepted(self) -> None:
        # When the caller already drilled into ``settings["permissions"]``
        # we shouldn't force them to re-wrap.
        policy = policy_from_mapping({"allow": ["Read"]})
        assert len(policy.allow) == 1

    def test_non_list_value_raises(self) -> None:
        with pytest.raises(RuleParseError):
            policy_from_mapping({"permissions": {"allow": "Read"}})

    def test_empty_strings_are_skipped(self) -> None:
        policy = policy_from_mapping(
            {"permissions": {"allow": ["Read", "", "  "]}}
        )
        assert len(policy.allow) == 1


# ---------------------------------------------------------------------------
# Policy.is_empty
# ---------------------------------------------------------------------------


def test_is_empty_distinguishes_default_from_user_loaded() -> None:
    assert Policy().is_empty()
    assert not Policy(allow=(Rule("Read", None, "Read"),)).is_empty()
