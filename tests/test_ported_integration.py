"""Port of lyra-ui tests/test_integration.py → tests TUI git_cmd + connect_status.

Original tested GitIntegration, GitHubIntegration, SlackIntegration.
Our TUI equivalents: git_cmd.py, connect_status.py, auth_cmd.py.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_git_branch():
    from lyra_cli.interactive.git_cmd import get_branch
    branch = get_branch()
    assert isinstance(branch, str)
    assert branch != ""


def test_git_dirty():
    from lyra_cli.interactive.git_cmd import get_dirty_count
    count = get_dirty_count()
    assert isinstance(count, int)


def test_git_status_badge():
    from lyra_cli.interactive.git_cmd import render_status_badge
    badge = render_status_badge()
    assert badge is not None
    assert len(badge) > 0


def test_git_commits_ahead():
    from lyra_cli.interactive.git_cmd import get_commits_ahead
    count = get_commits_ahead()
    assert isinstance(count, int)


def test_git_is_detached():
    from lyra_cli.interactive.git_cmd import is_detached
    detached = is_detached()
    assert isinstance(detached, bool)


def test_connect_providers():
    from lyra_cli.interactive.auth_cmd import AUTH_PROVIDERS
    assert len(AUTH_PROVIDERS) >= 5
    assert "github" in AUTH_PROVIDERS
    assert "openai" in AUTH_PROVIDERS
    assert "anthropic" in AUTH_PROVIDERS


def test_auth_list():
    from lyra_cli.interactive.auth_cmd import cmd_auth
    class FakeSession: pass
    result = cmd_auth(FakeSession(), "list")
    assert result is not None
    assert isinstance(result.output, str)
    assert "Providers" in result.output


def test_keys_list():
    from lyra_cli.interactive.keys_cmd import cmd_keys
    class FakeSession: pass
    result = cmd_keys(FakeSession(), "list")
    assert result is not None
    assert "Providers" in result.output


def test_keys_providers():
    from lyra_cli.interactive.keys_cmd import PROVIDERS
    assert len(PROVIDERS) >= 10
    assert "anthropic" in PROVIDERS
    assert "openai" in PROVIDERS
    assert "deepseek" in PROVIDERS


def test_keys_env():
    from lyra_cli.interactive.keys_cmd import cmd_keys
    class FakeSession: pass
    result = cmd_keys(FakeSession(), "env")
    assert result is not None


def test_connect_status_widget_import():
    pytest.importorskip("textual")
    from lyra_cli.tui_v2.widgets.connect_status import ConnectStatusWidget
    w = ConnectStatusWidget()
    assert w is not None
    assert w.expanded is False
