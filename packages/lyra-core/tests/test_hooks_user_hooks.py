"""Tests for ``lyra_core.hooks.user_hooks`` — the subprocess hook runner."""
from __future__ import annotations

import shutil

import pytest

from lyra_core.hooks.user_hooks import (
    HookSpec,
    SUPPORTED_EVENTS,
    parse_hooks_config,
    run_hooks,
)


def _has_shell() -> bool:
    """Skip subprocess-flavoured tests when the runner has no /bin/sh."""
    return shutil.which("/bin/sh") is not None


# ---------------------------------------------------------------------------
# parse_hooks_config
# ---------------------------------------------------------------------------


class TestParseHooksConfig:
    def test_full_shape(self) -> None:
        specs, enabled = parse_hooks_config(
            {
                "enable_hooks": True,
                "hooks": {
                    "PreToolUse": [
                        {"matcher": "Bash(rm *)", "command": "echo blocked"}
                    ],
                    "PostToolUse": [
                        {"matcher": "Edit(./src/**)", "command": "echo formatted"}
                    ],
                },
            }
        )
        assert enabled is True
        assert len(specs) == 2
        assert {s.event for s in specs} == {"PreToolUse", "PostToolUse"}

    def test_disabled_master_switch(self) -> None:
        specs, enabled = parse_hooks_config(
            {
                "hooks": {
                    "PreToolUse": [
                        {"matcher": "*", "command": "true"}
                    ]
                }
            }
        )
        # Specs still parse so doctor/status can warn "you have hooks
        # configured but they're disabled" — runtime gating is
        # separate from parsing.
        assert enabled is False
        assert len(specs) == 1

    def test_unknown_event_skipped_with_warning(self) -> None:
        specs, _ = parse_hooks_config(
            {
                "hooks": {
                    "PreToolUse": [{"matcher": "*", "command": "true"}],
                    "TotallyMadeUpEvent": [{"matcher": "*", "command": "true"}],
                }
            }
        )
        assert len(specs) == 1
        assert specs[0].event == "PreToolUse"

    def test_missing_command_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_hooks_config(
                {"hooks": {"PreToolUse": [{"matcher": "*"}]}}
            )

    def test_non_list_event_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_hooks_config(
                {"hooks": {"PreToolUse": "not a list"}}
            )

    def test_default_matcher_is_wildcard(self) -> None:
        specs, _ = parse_hooks_config(
            {"hooks": {"PreToolUse": [{"command": "true"}]}}
        )
        assert specs[0].matcher == "*"


# ---------------------------------------------------------------------------
# run_hooks — disabled master switch
# ---------------------------------------------------------------------------


def test_disabled_master_switch_short_circuits() -> None:
    """Even matching hooks shouldn't fire when ``enabled=False``."""
    specs = [HookSpec(event="PreToolUse", matcher="*", command="false")]
    outcome = run_hooks(
        specs,
        event="PreToolUse",
        tool_name="Bash",
        args={"command": "rm -rf /"},
        enabled=False,
    )
    assert outcome.block is False
    assert outcome.fired == []


# ---------------------------------------------------------------------------
# run_hooks — block / allow / mutate paths (real subprocesses)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_shell(), reason="no /bin/sh")
class TestRunHooksSubprocess:
    def test_continue_true_allows(self) -> None:
        specs = [
            HookSpec(
                event="PreToolUse",
                matcher="*",
                command='echo \'{"continue": true}\'',
            )
        ]
        outcome = run_hooks(
            specs,
            event="PreToolUse",
            tool_name="Bash",
            args={"command": "ls"},
        )
        assert outcome.block is False
        assert outcome.fired == ["*"]

    def test_continue_false_blocks(self) -> None:
        specs = [
            HookSpec(
                event="PreToolUse",
                matcher="Bash(rm *)",
                command='echo \'{"continue": false, "reason": "no rm"}\'',
            )
        ]
        outcome = run_hooks(
            specs,
            event="PreToolUse",
            tool_name="Bash",
            args={"command": "rm -rf /tmp/x"},
        )
        assert outcome.block is True
        assert outcome.reason == "no rm"

    def test_args_rewrite_applies(self) -> None:
        specs = [
            HookSpec(
                event="PreToolUse",
                matcher="*",
                command=(
                    'echo \'{"continue": true, "args": '
                    '{"command": "ls -la"}}\''
                ),
            )
        ]
        outcome = run_hooks(
            specs,
            event="PreToolUse",
            tool_name="Bash",
            args={"command": "ls"},
        )
        assert outcome.block is False
        assert outcome.mutated_args == {"command": "ls -la"}

    def test_broken_hook_fails_open(self) -> None:
        # Non-zero exit ⇒ allow, log the failure, don't block.
        specs = [
            HookSpec(
                event="PreToolUse",
                matcher="*",
                command="exit 1",
            )
        ]
        outcome = run_hooks(
            specs,
            event="PreToolUse",
            tool_name="Bash",
            args={"command": "ls"},
        )
        assert outcome.block is False

    def test_non_json_output_fails_open(self) -> None:
        specs = [
            HookSpec(
                event="PreToolUse",
                matcher="*",
                command="echo not json",
            )
        ]
        outcome = run_hooks(
            specs,
            event="PreToolUse",
            tool_name="Bash",
            args={"command": "ls"},
        )
        assert outcome.block is False

    def test_specifier_skips_non_matching_invocations(self) -> None:
        # ``Bash(rm *)`` shouldn't fire for ``ls`` — the hook command
        # has ``exit 1`` so if it DOES fire we'd see the broken-hook
        # path; outcome.fired==[] proves the matcher gated correctly.
        specs = [
            HookSpec(
                event="PreToolUse",
                matcher="Bash(rm *)",
                command="exit 1",
            )
        ]
        outcome = run_hooks(
            specs,
            event="PreToolUse",
            tool_name="Bash",
            args={"command": "ls"},
        )
        assert outcome.block is False
        assert outcome.fired == []

    def test_event_filter(self) -> None:
        # A PreToolUse hook shouldn't fire on PostToolUse dispatch.
        specs = [
            HookSpec(
                event="PreToolUse",
                matcher="*",
                command='echo \'{"continue": false}\'',
            )
        ]
        outcome = run_hooks(
            specs,
            event="PostToolUse",
            tool_name="Bash",
            args={"command": "ls"},
        )
        assert outcome.block is False
        assert outcome.fired == []

    def test_first_blocking_hook_short_circuits(self) -> None:
        # When two hooks match, the first ``continue=false`` should
        # win and the second hook should not run. We prove this by
        # giving the second hook a shell command that would set a
        # canary file — if it ran we'd find the file.
        canary = "/tmp/lyra-hook-canary-xxxxxx"
        specs = [
            HookSpec(
                event="PreToolUse",
                matcher="*",
                command='echo \'{"continue": false, "reason": "stop"}\'',
            ),
            HookSpec(
                event="PreToolUse",
                matcher="*",
                command=f"touch {canary} && echo '{{\"continue\": true}}'",
            ),
        ]
        outcome = run_hooks(
            specs,
            event="PreToolUse",
            tool_name="Bash",
            args={"command": "ls"},
        )
        assert outcome.block is True
        # Second hook shouldn't have run; canary should NOT exist.
        import os as _os
        assert not _os.path.exists(canary)


# ---------------------------------------------------------------------------
# Module surface
# ---------------------------------------------------------------------------


def test_supported_events_includes_core_set() -> None:
    # Sanity-check the public registry — protects against an event
    # being silently removed during refactors.
    for event in (
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "Stop",
    ):
        assert event in SUPPORTED_EVENTS
