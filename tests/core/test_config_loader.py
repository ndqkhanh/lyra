"""
Unit tests for YAMLHookConfig, HotReload, and all handler types.
Mocks file I/O, yaml, HookEngine, and external processes.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from lyra.hooks import HookAction, HookContext, HookEngine, HookType

# Module to test -- we import from it directly.
# We'll patch yaml / file / subprocess / sounddevice as needed.


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_engine() -> MagicMock:
    eng = MagicMock(spec=HookEngine)
    eng.register.return_value = "hook-registered-1"
    eng.registry = MagicMock()
    return eng


@pytest.fixture
def ctx() -> HookContext:
    return HookContext(
        hook_type=HookType.PRE_TOOL_USE,
        tool_name="bash",
        session_id="sess-1",
        agent_id="agent-1",
        tool_input={"cmd": "echo hi"},
    )


# To avoid triggering the dynamic yaml import in __init__, we import the module
# lazily inside each test and patch yaml at the module level.

def _import_cls():
    from lyra.core.hooks.config_loader import (
        YAMLHookConfig,
        YAMLHookDefinition,
        HotReload,
        HTTPHook,
        LogHook,
        ScriptHook,
        MetricsHook,
        RateLimitHook,
        CacheHook,
    )
    return (YAMLHookConfig, YAMLHookDefinition, HotReload,
            HTTPHook, LogHook, ScriptHook, MetricsHook, RateLimitHook, CacheHook)


# =============================================================================
# YAMLHookDefinition
# =============================================================================

class TestYAMLHookDefinition:
    def test_defaults(self) -> None:
        (YHC, YHD, *_) = _import_cls()
        d = YHD(name="test-hook", type="pre_tool_use")
        assert d.name == "test-hook"
        assert d.type == "pre_tool_use"
        assert d.handler_type == "inline"
        assert d.priority == 500
        assert d.enabled is True
        assert d.config == {}

    def test_custom_values(self) -> None:
        (YHC, YHD, *_) = _import_cls()
        d = YHD(
            name="custom", type="post_tool_use", handler_type="http",
            priority=100, description="desc", tool_filter="bash",
            file_pattern="*.py", enabled=False,
            config={"url": "http://example.com"},
        )
        assert d.tool_filter == "bash"
        assert d.file_pattern == "*.py"
        assert d.enabled is False
        assert d.config["url"] == "http://example.com"


# =============================================================================
# YAMLHookConfig
# =============================================================================

class TestYAMLHookConfigInit:
    def test_init(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine, config_path="hooks.*.yml")
        assert cfg.engine is mock_engine
        assert cfg.config_path == "hooks.*.yml"
        assert cfg._loaded_defs == {}
        assert cfg._registered_ids == []

    def test_get_statistics(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        stats = cfg.get_statistics()
        assert stats["loaded_definitions"] == 0
        assert stats["registered_hooks"] == 0
        assert "config_path" in stats


class TestYAMLHookConfigLoad:
    def test_load_no_files(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine, config_path="nonexistent.*.yml")
        with patch.object(Path, "glob", return_value=[]):
            with patch.object(Path, "exists", return_value=False):
                count = cfg.load()
        assert count == 0

    def test_load_single_file(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine, config_path="hooks.dev.yml")
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = "hooks:\n  - name: pre_hook\n    type: pre_tool_use\n"
        with patch.object(Path, "glob", return_value=[mock_path]):
            with patch("yaml.safe_load", return_value={"hooks": [{"name": "pre_hook", "type": "pre_tool_use"}]}):
                count = cfg.load()
        assert count == 1
        assert "pre_hook" in cfg._loaded_defs

    def test_load_none_data(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine, config_path="hooks.dev.yml")
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = "~\n"
        with patch.object(Path, "glob", return_value=[mock_path]):
            with patch("yaml.safe_load", return_value=None):
                count = cfg.load()
        assert count == 0

    def test_load_file_exception(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine, config_path="hooks.dev.yml")
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.side_effect = OSError("read error")
        with patch.object(Path, "glob", return_value=[mock_path]):
            count = cfg.load()
        assert count == 0

    def test_load_missing_yaml(self, mock_engine) -> None:
        """ImportError when yaml is not installed (simulated by patch)."""
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        with patch("builtins.__import__", side_effect=ImportError("no yaml")):
            with pytest.raises(ImportError, match="PyYAML is required"):
                cfg.load()

    def test_load_resolves_path_fallback(self, mock_engine) -> None:
        """Test the fallback logic when glob returns [] the first time."""
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine, config_path="sub/hooks.dev.yml")
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = "hooks:\n  - name: fb\n    type: post_tool_use\n"
        type(mock_path).parent = PropertyMock(return_value=Path("sub"))
        # First glob returns [] -> falls through to parent.glob, then plain path
        with patch.object(Path, "glob", side_effect=[
            [],
            [mock_path],
        ]):
            with patch("yaml.safe_load", return_value={"hooks": [{"name": "fb", "type": "post_tool_use"}]}):
                count = cfg.load()
        assert count == 1

    def test_load_plain_file_path(self, mock_engine, tmp_path) -> None:
        (YHC, *_) = _import_cls()
        config_file = tmp_path / "plain_hooks.yml"
        config_file.write_text("hooks:\n  - name: h1\n    type: pre_tool_use\n")
        cfg = YHC(mock_engine, config_path=str(config_file))
        with patch.object(Path, "glob", return_value=[]):
            count = cfg.load()
        assert count == 1


class TestYAMLHookConfigLoadDict:
    def test_load_dict(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        count = cfg.load_dict({"hooks": [{"name": "d1", "type": "pre_tool_use"}]})
        assert count == 1
        assert "d1" in cfg._loaded_defs

    def test_load_dict_hooks_as_dict(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        count = cfg.load_dict({"name": "d1", "type": "pre_tool_use"})
        assert count == 1

    def test_load_dict_skips_non_dict_items(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        count = cfg.load_dict({"hooks": ["not-a-dict", 42]})
        assert count == 0

    def test_load_dict_with_disabled(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        count = cfg.load_dict({"hooks": [{"name": "dis", "type": "pre_tool_use", "enabled": False}]})
        assert count == 1
        assert cfg._loaded_defs["dis"].enabled is False
        # engine.registry.disable should have been called
        assert mock_engine.registry.disable.called


class TestYAMLHookConfigUnload:
    def test_unload_all(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        mock_engine.registry.unregister.return_value = True
        cfg._registered_ids = ["a", "b"]
        cfg._loaded_defs = {"a": MagicMock(), "b": MagicMock()}
        count = cfg.unload_all()
        assert count == 2
        assert cfg._registered_ids == []
        assert cfg._loaded_defs == {}

    def test_unload_all_partial_failure(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        mock_engine.registry.unregister.side_effect = [True, False]
        cfg._registered_ids = ["a", "b"]
        count = cfg.unload_all()
        assert count == 1


class TestYAMLHookConfigGetLoadedDefs:
    def test_get_loaded_definitions(self, mock_engine) -> None:
        (YHC, YHD, *_) = _import_cls()
        cfg = YHC(mock_engine)
        d = YHD(name="x", type="pre_tool_use")
        cfg._loaded_defs["x"] = d
        defs = cfg.get_loaded_definitions()
        assert len(defs) == 1
        assert defs[0].name == "x"


class TestYAMLHookConfigResolveType:
    def test_known_types(self) -> None:
        (YHC, *_) = _import_cls()
        assert YHC._resolve_type("pre_tool_use") == HookType.PRE_TOOL_USE
        assert YHC._resolve_type("post_tool_use") == HookType.POST_TOOL_USE
        assert YHC._resolve_type("pre_model_call") == HookType.PRE_MODEL_CALL
        assert YHC._resolve_type("post_model_call") == HookType.POST_MODEL_CALL
        assert YHC._resolve_type("session_start") == HookType.SESSION_START
        assert YHC._resolve_type("session_end") == HookType.SESSION_END
        assert YHC._resolve_type("stop") == HookType.STOP

    def test_unknown_type_defaults(self) -> None:
        (YHC, *_) = _import_cls()
        result = YHC._resolve_type("bogus_type")
        assert result == HookType.PRE_TOOL_USE


class TestYAMLHookConfigBuildHandler:
    def test_build_inline(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        handler = cfg._build_handler(
            MagicMock(handler_type="inline", config={"block_if": "danger"})
        )
        assert callable(handler)

    def test_build_http(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        from lyra.core.hooks.config_loader import HTTPHook
        handler = cfg._build_handler(
            MagicMock(handler_type="http", config={"url": "http://example.com"})
        )
        assert isinstance(handler, HTTPHook)

    def test_build_log(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        from lyra.core.hooks.config_loader import LogHook
        handler = cfg._build_handler(
            MagicMock(handler_type="log", config={})
        )
        assert isinstance(handler, LogHook)

    def test_build_script(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        from lyra.core.hooks.config_loader import ScriptHook
        handler = cfg._build_handler(
            MagicMock(handler_type="script", config={})
        )
        assert isinstance(handler, ScriptHook)

    def test_build_metrics(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        from lyra.core.hooks.config_loader import MetricsHook
        handler = cfg._build_handler(
            MagicMock(handler_type="metrics", config={})
        )
        assert isinstance(handler, MetricsHook)

    def test_build_rate_limit(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        from lyra.core.hooks.config_loader import RateLimitHook
        handler = cfg._build_handler(
            MagicMock(handler_type="rate_limit", config={})
        )
        assert isinstance(handler, RateLimitHook)

    def test_build_cache(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        from lyra.core.hooks.config_loader import CacheHook
        handler = cfg._build_handler(
            MagicMock(handler_type="cache", config={})
        )
        assert isinstance(handler, CacheHook)

    def test_build_unknown_defaults_inline(self, mock_engine) -> None:
        (YHC, *_) = _import_cls()
        cfg = YHC(mock_engine)
        handler = cfg._build_handler(
            MagicMock(handler_type="alien_tech", config={})
        )
        assert callable(handler)


# =============================================================================
# Inline handler
# =============================================================================

class TestInlineHandler:
    def test_allow_by_default(self, mock_engine, ctx) -> None:
        (YHC, *_) = _import_cls()
        handler = YHC._build_inline_handler({})
        result = handler(ctx)
        assert result.action == HookAction.ALLOW

    def test_block_if_matches(self, mock_engine, ctx) -> None:
        (YHC, *_) = _import_cls()
        handler = YHC._build_inline_handler({"block_if": "echo hi"})
        result = handler(ctx)
        assert result.action == HookAction.BLOCK

    def test_block_if_no_match(self, mock_engine, ctx) -> None:
        (YHC, *_) = _import_cls()
        handler = YHC._build_inline_handler({"block_if": "NONEXISTENT"})
        result = handler(ctx)
        assert result.action == HookAction.ALLOW

    def test_allow_if_matches(self, mock_engine, ctx) -> None:
        (YHC, *_) = _import_cls()
        handler = YHC._build_inline_handler({"allow_if": "echo hi"})
        result = handler(ctx)
        assert result.action == HookAction.ALLOW

    def test_log_message(self, mock_engine, ctx) -> None:
        (YHC, *_) = _import_cls()
        handler = YHC._build_inline_handler({"log": "test log msg"})
        with patch("lyra.core.hooks.config_loader.logger") as mock_log:
            result = handler(ctx)
        mock_log.info.assert_called_with("YAMLHook[inline]: %s", "test log msg")
        assert result.action == HookAction.ALLOW


# =============================================================================
# HotReload
# =============================================================================

class TestHotReload:
    def test_init(self, mock_engine) -> None:
        (YHC, _, HR, *_) = _import_cls()
        cfg = YHC(mock_engine)
        hr = HR(cfg, poll_interval=0.1, auto_reload=True)
        assert hr.config_loader is cfg
        assert hr.poll_interval == 0.1
        assert hr.auto_reload is True
        assert hr._reload_count == 0

    def test_poll_skipped_before_interval(self, mock_engine) -> None:
        (YHC, _, HR, *_) = _import_cls()
        cfg = YHC(mock_engine)
        hr = HR(cfg, poll_interval=9999)
        hr._last_poll = time.time()
        result = hr.poll()
        assert result is False

    def test_poll_no_matching_files(self, mock_engine) -> None:
        (YHC, _, HR, *_) = _import_cls()
        cfg = YHC(mock_engine)
        hr = HR(cfg, poll_interval=0.001)
        hr._last_poll = 0
        with patch.object(Path, "glob", side_effect=[
            [],
            [],
        ]):
            with patch.object(Path, "exists", return_value=False):
                result = hr.poll()
        assert result is False

    def test_poll_first_seen_stores_hash(self, mock_engine) -> None:
        (YHC, _, HR, *_) = _import_cls()
        cfg = YHC(mock_engine)
        hr = HR(cfg, poll_interval=0.001)
        hr._last_poll = 0
        mock_path = MagicMock(spec=Path)
        mock_path.read_bytes.return_value = b"content"
        with patch.object(Path, "glob", return_value=[mock_path]):
            result = hr.poll()
        assert result is False  # first time, no change
        assert len(hr._file_hashes) == 1

    def test_poll_detects_change(self, mock_engine) -> None:
        (YHC, _, HR, *_) = _import_cls()
        cfg = YHC(mock_engine)
        hr = HR(cfg, poll_interval=0.001, auto_reload=False)
        hr._last_poll = 0
        mock_path = MagicMock(spec=Path)
        type(mock_path).__str__ = lambda s: "/fake/path.yml"
        mock_path.read_bytes.return_value = b"new-content"
        hr._file_hashes["/fake/path.yml"] = "oldhash"
        with patch.object(Path, "glob", return_value=[mock_path]):
            result = hr.poll()
        assert result is True
        assert hr._file_hashes["/fake/path.yml"] != "oldhash"

    def test_poll_with_auto_reload(self, mock_engine) -> None:
        (YHC, _, HR, *_) = _import_cls()
        cfg = YHC(mock_engine)
        cfg.load = MagicMock(return_value=3)
        cfg.unload_all = MagicMock(return_value=2)
        hr = HR(cfg, poll_interval=0.001, auto_reload=True)
        hr._last_poll = 0
        mock_path = MagicMock(spec=Path)
        type(mock_path).__str__ = lambda s: "/fake/path.yml"
        mock_path.read_bytes.return_value = b"new-content"
        hr._file_hashes["/fake/path.yml"] = "oldhash"
        with patch.object(Path, "glob", return_value=[mock_path]):
            result = hr.poll()
        assert result is True
        cfg.unload_all.assert_called_once()
        cfg.load.assert_called_once()

    def test_poll_oserror_skipped(self, mock_engine) -> None:
        (YHC, _, HR, *_) = _import_cls()
        cfg = YHC(mock_engine)
        hr = HR(cfg, poll_interval=0.001, auto_reload=False)
        hr._last_poll = 0
        mock_path = MagicMock(spec=Path)
        mock_path.read_bytes.side_effect = OSError("no access")
        with patch.object(Path, "glob", return_value=[mock_path]):
            result = hr.poll()
        assert result is False

    def test_reload(self, mock_engine) -> None:
        (YHC, _, HR, *_) = _import_cls()
        cfg = YHC(mock_engine)
        cfg.load = MagicMock(return_value=5)
        cfg.unload_all = MagicMock(return_value=3)
        hr = HR(cfg)
        count = hr.reload()
        assert count == 5
        assert hr._reload_count == 1
        cfg.unload_all.assert_called_once()
        cfg.load.assert_called_once()

    def test_force_poll(self, mock_engine) -> None:
        (YHC, _, HR, *_) = _import_cls()
        cfg = YHC(mock_engine)
        hr = HR(cfg, poll_interval=9999)
        hr._last_poll = time.time()
        # No matching files => no changes
        with patch.object(Path, "glob", side_effect=[
            [],
            [],
        ]):
            with patch.object(Path, "exists", return_value=False):
                result = hr.force_poll()
        assert result is False

    def test_force_poll_restores_on_no_change(self, mock_engine) -> None:
        (YHC, _, HR, *_) = _import_cls()
        cfg = YHC(mock_engine)
        hr = HR(cfg, poll_interval=9999)
        hr._last_poll = time.time()
        saved = hr._last_poll
        with patch.object(Path, "glob", side_effect=[[], []]):
            with patch.object(Path, "exists", return_value=False):
                hr.force_poll()
        # _last_poll should be restored to saved since there was no change
        assert hr._last_poll == saved

    def test_get_statistics(self, mock_engine) -> None:
        (YHC, _, HR, *_) = _import_cls()
        cfg = YHC(mock_engine)
        hr = HR(cfg, poll_interval=2.0, auto_reload=True)
        stats = hr.get_statistics()
        assert stats["poll_interval"] == 2.0
        assert stats["auto_reload"] is True
        assert stats["reload_count"] == 0
        assert stats["watched_files"] == 0


# =============================================================================
# HTTPHook
# =============================================================================

class TestHTTPHook:
    def test_empty_url_allows(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        HTTPHook = rest[0]
        hook = HTTPHook({})
        result = hook(ctx)
        assert result.action == HookAction.ALLOW

    def test_request_success(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        HTTPHook = rest[0]
        hook = HTTPHook({"url": "http://example.com/hook"})
        with patch("urllib.request.urlopen") as mock_open:
            result = hook(ctx)
        mock_open.assert_called_once()
        assert result.action == HookAction.ALLOW

    def test_request_failure_logged(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        HTTPHook = rest[0]
        hook = HTTPHook({"url": "http://example.com/hook"})
        with patch("urllib.request.urlopen", side_effect=OSError("connection failed")):
            result = hook(ctx)
        assert result.action == HookAction.ALLOW

    def test_include_context(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        HTTPHook = rest[0]
        hook = HTTPHook({"url": "http://ex.com", "include_context": True, "method": "PUT"})
        assert hook.method == "PUT"
        with patch("urllib.request.urlopen") as mock_open:
            hook(ctx)
        args, kwargs = mock_open.call_args
        req = args[0]
        assert req.method == "PUT"
        assert req.data is not None
        body = json.loads(req.data)
        assert body["hook_type"] == "pre_tool_use"


# =============================================================================
# LogHook
# =============================================================================

class TestLogHook:
    def test_default_level(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        LogHook = rest[1]
        hook = LogHook({})
        result = hook(ctx)
        assert result.action == HookAction.ALLOW

    def test_debug_level(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        LogHook = rest[1]
        hook = LogHook({"level": "debug"})
        with patch("lyra.core.hooks.config_loader.logger") as mock_log:
            hook(ctx)
        mock_log.debug.called

    def test_error_level(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        LogHook = rest[1]
        hook = LogHook({"level": "error"})
        with patch("lyra.core.hooks.config_loader.logger") as mock_log:
            hook(ctx)
        mock_log.error.called

    def test_json_format(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        LogHook = rest[1]
        hook = LogHook({"format": "json", "message": "hook fired"})
        with patch("lyra.core.hooks.config_loader.logger") as mock_log:
            hook(ctx)
        mock_log.info.assert_called_once()
        # First call should be a JSON string
        call_args = mock_log.info.call_args[0]
        assert isinstance(call_args[0], str)
        parsed = json.loads(call_args[0])
        assert parsed["message"] == "hook fired"

    def test_text_format_no_context(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        LogHook = rest[1]
        hook = LogHook({"format": "text", "include_context": False})
        with patch("lyra.core.hooks.config_loader.logger") as mock_log:
            hook(ctx)
        mock_log.info.assert_called_once()

    def test_unknown_level_defaults_info(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        LogHook = rest[1]
        hook = LogHook({"level": "critical"})
        result = hook(ctx)
        assert result.action == HookAction.ALLOW


# =============================================================================
# ScriptHook
# =============================================================================

class TestScriptHook:
    def test_empty_script_allows(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        ScriptHook = rest[2]
        hook = ScriptHook({})
        result = hook(ctx)
        assert result.action == HookAction.ALLOW

    def test_script_not_found(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        ScriptHook = rest[2]
        hook = ScriptHook({"script": "/nonexistent/script.sh"})
        with patch("os.path.isfile", return_value=False):
            result = hook(ctx)
        assert result.action == HookAction.ALLOW

    def test_script_executes_successfully(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        ScriptHook = rest[2]
        hook = ScriptHook({"script": "/bin/echo", "args": ["hello"]})
        with patch("os.path.isfile", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                result = hook(ctx)
        assert result.action == HookAction.ALLOW
        mock_run.assert_called_once()

    def test_script_nonzero_exit(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        ScriptHook = rest[2]
        hook = ScriptHook({"script": "/bin/false"})
        with patch("os.path.isfile", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="error")
                result = hook(ctx)
        assert result.action == HookAction.ALLOW

    def test_script_timeout(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        ScriptHook = rest[2]
        hook = ScriptHook({"script": "/bin/sleep", "timeout": 0.01})
        with patch("os.path.isfile", return_value=True):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 0.01)):
                result = hook(ctx)
        assert result.action == HookAction.ALLOW

    def test_script_exception(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        ScriptHook = rest[2]
        hook = ScriptHook({"script": "/bin/true"})
        with patch("os.path.isfile", return_value=True):
            with patch("subprocess.run", side_effect=OSError("fork failed")):
                result = hook(ctx)
        assert result.action == HookAction.ALLOW

    def test_pass_context_env(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        ScriptHook = rest[2]
        hook = ScriptHook({"script": "/bin/echo", "pass_context": True})
        with patch("os.path.isfile", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                hook(ctx)
        _, kwargs = mock_run.call_args
        env = kwargs["env"]
        assert env["LYRA_HOOK_TYPE"] == "pre_tool_use"
        assert env["LYRA_TOOL_NAME"] == "bash"
        assert env["LYRA_SESSION_ID"] == "sess-1"
        assert env["LYRA_AGENT_ID"] == "agent-1"


# =============================================================================
# MetricsHook
# =============================================================================

class TestMetricsHook:
    def test_counter_default(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        MetricsHook = rest[3]
        hook = MetricsHook({})
        result = hook(ctx)
        assert result.action == HookAction.ALLOW
        assert hook._counter == 1

    def test_gauge(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        MetricsHook = rest[3]
        hook = MetricsHook({"metric_type": "gauge", "value": 42})
        result = hook(ctx)
        assert result.action == HookAction.ALLOW
        assert hook._gauges["lyra.hook.fired"] == 42.0

    def test_histogram(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        MetricsHook = rest[3]
        hook = MetricsHook({"metric_type": "histogram", "value": 3.14})
        result = hook(ctx)
        assert result.action == HookAction.ALLOW
        assert hook._histogram == [3.14]

    def test_get_metrics_with_data(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        MetricsHook = rest[3]
        hook = MetricsHook({"metric_type": "histogram", "value": 10})
        hook(ctx)
        hook(ctx)
        m = hook.get_metrics()
        assert m["counter"] == 0  # only counter is from default type, but we overrode
        assert m["histogram_count"] == 2

    def test_resolve_value_context_attr(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        MetricsHook = rest[3]
        hook = MetricsHook({"metric_type": "gauge", "value": "agent_id"})
        val = hook._resolve_value(ctx)
        # context.agent_id = "agent-1", which cannot be parsed as float -> 0.0
        assert val == 0.0

    def test_resolve_value_string_not_on_context(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        MetricsHook = rest[3]
        hook = MetricsHook({"metric_type": "gauge", "value": "tool_input"})
        val = hook._resolve_value(ctx)
        # context.tool_input exists but is a dict, cannot be parsed as float -> 0.0
        assert val == 0.0


# =============================================================================
# RateLimitHook
# =============================================================================

class TestRateLimitHook:
    def test_allow_within_limit(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        RateLimitHook = rest[4]
        hook = RateLimitHook({"max_calls": 3, "window_seconds": 60})
        for _ in range(3):
            result = hook(ctx)
            assert result.action == HookAction.ALLOW

    def test_block_when_exceeded(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        RateLimitHook = rest[4]
        hook = RateLimitHook({"max_calls": 2, "window_seconds": 60})
        hook(ctx)  # 1
        hook(ctx)  # 2
        result = hook(ctx)  # 3 > 2
        assert result.action == HookAction.BLOCK
        assert "Rate limit exceeded" in result.reason

    def test_key_from_agent_id(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        RateLimitHook = rest[4]
        hook = RateLimitHook({"key": "agent_id"})
        key = hook._get_key(ctx)
        assert key == "agent-1"

    def test_key_from_session_id(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        RateLimitHook = rest[4]
        hook = RateLimitHook({"key": "session_id"})
        key = hook._get_key(ctx)
        assert key == "sess-1"

    def test_key_from_tool_name(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        RateLimitHook = rest[4]
        hook = RateLimitHook({"key": "tool_name"})
        key = hook._get_key(ctx)
        assert key == "bash"

    def test_key_default(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        RateLimitHook = rest[4]
        hook = RateLimitHook({"key": "unknown_field"})
        key = hook._get_key(ctx)
        assert key == "default"

    def test_get_statistics(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        RateLimitHook = rest[4]
        hook = RateLimitHook({})
        hook(ctx)
        stats = hook.get_statistics()
        assert stats["buckets"] == 1
        assert stats["max_calls_per_window"] == 10

    def test_prune_old_entries(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        RateLimitHook = rest[4]
        hook = RateLimitHook({"max_calls": 1, "window_seconds": 0.001})
        hook(ctx)  # 1
        import time
        time.sleep(0.005)
        result = hook(ctx)  # Old entry pruned, should allow
        assert result.action == HookAction.ALLOW


# =============================================================================
# CacheHook
# =============================================================================

class TestCacheHook:
    def test_empty_key_allows(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        CacheHook = rest[5]
        hook = CacheHook({"key": "tool_input"})
        # ctx.tool_input is {"cmd": "echo hi"}
        result = hook(ctx)
        assert result.action == HookAction.ALLOW

    def test_cache_hit(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        CacheHook = rest[5]
        hook = CacheHook({"key": "tool_input", "ttl_seconds": 300})
        key = hook._get_key(ctx)
        hook._cache[key] = (time.time(), {"cached": "value"})
        result = hook(ctx)
        assert result.action == HookAction.MODIFY
        assert result.modified_context is not None

    def test_cache_expired(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        CacheHook = rest[5]
        hook = CacheHook({"key": "tool_input", "ttl_seconds": 0.001})
        key = hook._get_key(ctx)
        hook._cache[key] = (0, {"old": "data"})  # expired
        import time
        time.sleep(0.005)
        result = hook(ctx)
        assert result.action == HookAction.ALLOW

    def test_store_and_invalidate(self) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        CacheHook = rest[5]
        hook = CacheHook({"max_size": 100})
        hook.store("mykey", "myvalue")
        assert len(hook._cache) == 1
        count = hook.invalidate("*")
        assert count == 1
        assert len(hook._cache) == 0

    def test_store_evicts_oldest(self) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        CacheHook = rest[5]
        hook = CacheHook({"max_size": 2})
        hook.store("a", 1)
        hook.store("b", 2)
        hook.store("c", 3)  # should evict "a"
        assert len(hook._cache) == 2
        assert "manual:a" not in hook._cache

    def test_invalidate_pattern(self) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        CacheHook = rest[5]
        hook = CacheHook({})
        hook.store("alpha", 1)
        hook.store("beta", 2)
        count = hook.invalidate("manual:alpha")
        assert count == 1
        assert "manual:alpha" not in hook._cache
        assert "manual:beta" in hook._cache

    def test_clear(self) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        CacheHook = rest[5]
        hook = CacheHook({})
        hook._cache["k"] = (time.time(), "v")
        hook.clear()
        assert len(hook._cache) == 0

    def test_get_statistics(self) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        CacheHook = rest[5]
        hook = CacheHook({"max_size": 500, "ttl_seconds": 60})
        stats = hook.get_statistics()
        assert stats["max_size"] == 500
        assert stats["ttl_seconds"] == 60

    def test_key_extraction(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        CacheHook = rest[5]
        # tool_input key
        hook = CacheHook({"key": "tool_input"})
        key = hook._get_key(ctx)
        assert "cmd" in key

        # tool_name key
        hook2 = CacheHook({"key": "tool_name"})
        key2 = hook2._get_key(ctx)
        assert key2 == "bash"

        # agent_id key
        hook3 = CacheHook({"key": "agent_id"})
        key3 = hook3._get_key(ctx)
        assert key3 == "agent-1"

        # unknown key
        hook4 = CacheHook({"key": "nonexistent"})
        key4 = hook4._get_key(ctx)
        assert key4 == ""

    def test_cache_hit_with_tool_name_key(self, ctx) -> None:
        (_YHC, _YHD, _HR, *rest) = _import_cls()
        CacheHook = rest[5]
        hook = CacheHook({"key": "tool_name"})
        hook._cache["bash"] = (time.time(), "cached_result")
        result = hook(ctx)
        assert result.action == HookAction.MODIFY
