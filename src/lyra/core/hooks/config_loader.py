"""
YAMLHookConfig — load hook configuration from YAML files.

Supports defining hooks declaratively in YAML and registering them
with a HookEngine.  Includes a HotReload utility that watches for
file changes and reloads hooks without restarting the engine.

Additional handler types:

    - HTTPHook: Make an HTTP request when the hook fires.
    - LogHook: Write structured logs when the hook fires.
    - ScriptHook: Execute an external script when the hook fires.
    - MetricsHook: Emit metrics (counter, gauge, histogram).
    - RateLimitHook: Rate-limit operations by key.
    - CacheHook: Cache results to reduce repeated computation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from lyra.hooks import (
    HookAction,
    HookContext,
    HookEngine,
    HookResult,
    HookType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_CONFIG_GLOB: str = "hooks.*.yml"
DEFAULT_POLL_INTERVAL: float = 5.0


# =============================================================================
# YAMLHookConfig
# =============================================================================


@dataclass
class YAMLHookDefinition:
    """A single hook definition parsed from YAML.

    Attributes:
        name: Hook name (used as hook_id).
        type: Hook type string (e.g., "pre_tool_use").
        handler_type: Handler implementation type.
        priority: Execution priority (higher = earlier).
        description: Human-readable description.
        tool_filter: Optional tool name pattern (fnmatch).
        file_pattern: Optional file path pattern (fnmatch).
        enabled: Whether the hook is enabled by default.
        config: Handler-specific configuration dict.
    """

    name: str
    type: str
    handler_type: str = "inline"
    priority: int = 500
    description: str = ""
    tool_filter: str = ""
    file_pattern: str = ""
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


class YAMLHookConfig:
    """Load hook configuration from YAML files.

    Supports loading hook definitions from one or more YAML files
    and registering them with a HookEngine.  Each definition specifies
    the hook type, handler implementation, priority, and optional
    filters.

    Attributes:
        engine: The HookEngine to register hooks with.
        config_path: Path or glob pattern for YAML config files.
    """

    def __init__(
        self,
        engine: HookEngine,
        config_path: str = DEFAULT_CONFIG_GLOB,
    ) -> None:
        self.engine = engine
        self.config_path = config_path
        self._loaded_defs: dict[str, YAMLHookDefinition] = {}
        self._registered_ids: list[str] = []

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> int:
        """Load hook definitions from YAML config files.

        Searches for files matching the config_path glob, parses each,
        and registers hooks with the engine.

        Returns:
            Number of hooks registered.

        Raises:
            FileNotFoundError: If no config files match the glob.
            ValueError: If YAML parsing fails.
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAMLHookConfig. "
                "Install it with: pip install pyyaml"
            )

        matching: list[Path] = []
        try:
            matching = list(Path(".").glob(self.config_path))
        except (NotImplementedError, OSError):
            pass
        if not matching:
            # Try resolving from project root
            try:
                matching = list(Path(self.config_path).parent.glob(self.config_path.split("/")[-1]))
            except (NotImplementedError, OSError):
                pass
        if not matching:
            # Try as a plain file path
            p = Path(self.config_path)
            if p.exists() and p.is_file():
                matching = [p]
        if not matching:
            logger.warning("YAMLHookConfig: no files matching '%s'", self.config_path)
            return 0

        total = 0
        for filepath in matching:
            try:
                raw = filepath.read_text(encoding="utf-8")
                data = yaml.safe_load(raw)
                if data is None:
                    continue
                count = self._load_file(data, str(filepath))
                total += count
                logger.info("YAMLHookConfig: loaded %d hooks from %s", count, filepath)
            except Exception as e:
                logger.warning("YAMLHookConfig: failed to load %s: %s", filepath, e)

        return total

    def load_dict(self, data: dict[str, Any], source: str = "<inline>") -> int:
        """Load hook definitions from an in-memory dict.

        Args:
            data: Dict with a "hooks" key containing a list of hook defs.
            source: Source label for logging.

        Returns:
            Number of hooks registered.
        """
        return self._load_file(data, source)

    def _load_file(self, data: dict[str, Any], source: str) -> int:
        """Parse a YAML dict and register hooks."""
        hooks_data = data.get("hooks", data)
        if isinstance(hooks_data, dict):
            hooks_data = [hooks_data]

        count = 0
        for item in hooks_data:
            if not isinstance(item, dict):
                continue

            definition = YAMLHookDefinition(
                name=item.get("name", f"hook_{uuid.uuid4().hex[:8]}"),
                type=item.get("type", "pre_tool_use"),
                handler_type=item.get("handler_type", "inline"),
                priority=item.get("priority", 500),
                description=item.get("description", ""),
                tool_filter=item.get("tool_filter", ""),
                file_pattern=item.get("file_pattern", ""),
                enabled=item.get("enabled", True),
                config=item.get("config", {}),
            )

            self._loaded_defs[definition.name] = definition
            self._register_definition(definition, source)
            count += 1

        return count

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def _register_definition(self, definition: YAMLHookDefinition, source: str) -> str:
        """Register a single YAML hook definition with the engine."""
        hook_type = self._resolve_type(definition.type)
        handler = self._build_handler(definition)
        description = definition.description or f"YAML hook: {definition.name}"

        hook_id = self.engine.register(
            hook_type=hook_type,
            handler=handler,
            priority=definition.priority,
            hook_id=f"yaml.{definition.name}",
            description=description,
            tool_filter=definition.tool_filter or None,
            file_pattern=definition.file_pattern or None,
        )

        # Enable/disable
        if not definition.enabled:
            self.engine.registry.disable(hook_id)

        self._registered_ids.append(hook_id)
        return hook_id

    @staticmethod
    def _resolve_type(type_str: str) -> HookType:
        """Resolve a hook type string to a HookType enum."""
        type_map = {
            "pre_tool_use": HookType.PRE_TOOL_USE,
            "post_tool_use": HookType.POST_TOOL_USE,
            "pre_model_call": HookType.PRE_MODEL_CALL,
            "post_model_call": HookType.POST_MODEL_CALL,
            "session_start": HookType.SESSION_START,
            "session_end": HookType.SESSION_END,
            # Legacy
            "stop": HookType.STOP,
        }
        mapped = type_map.get(type_str)
        if mapped is None:
            logger.warning("YAMLHookConfig: unknown hook type '%s', using pre_tool_use", type_str)
            return HookType.PRE_TOOL_USE
        return mapped

    def _build_handler(self, definition: YAMLHookDefinition) -> Callable:
        """Build a handler callable from a YAML hook definition."""
        handler_type = definition.handler_type
        config = definition.config

        if handler_type == "inline":
            return self._build_inline_handler(config)
        elif handler_type == "http":
            return HTTPHook(config)
        elif handler_type == "log":
            return LogHook(config)
        elif handler_type == "script":
            return ScriptHook(config)
        elif handler_type == "metrics":
            return MetricsHook(config)
        elif handler_type == "rate_limit":
            return RateLimitHook(config)
        elif handler_type == "cache":
            return CacheHook(config)
        else:
            logger.warning("YAMLHookConfig: unknown handler type '%s', using inline", handler_type)
            return self._build_inline_handler(config)

    @staticmethod
    def _build_inline_handler(config: dict[str, Any]) -> Callable:
        """Build a handler from inline configuration.

        The inline handler evaluates a simple condition and returns
        ALLOW or BLOCK based on the config.
        """
        block_if = config.get("block_if", "")
        allow_if = config.get("allow_if", "")
        log_message = config.get("log", "")

        def handler(context: HookContext) -> HookResult:
            if log_message:
                logger.info("YAMLHook[inline]: %s", log_message)

            if block_if:
                # Check if condition matches any part of the context
                ctx_str = str(context)
                if block_if.lower() in ctx_str.lower():
                    return HookResult.block(
                        reason=f"Inline block: {block_if}",
                        hook_name="YAMLHook(inline)",
                    )

            if allow_if:
                ctx_str = str(context)
                if allow_if.lower() in ctx_str.lower():
                    return HookResult.allow(hook_name="YAMLHook(inline)")

            return HookResult.allow(hook_name="YAMLHook(inline)")

        return handler

    # ------------------------------------------------------------------
    # Unload
    # ------------------------------------------------------------------

    def unload_all(self) -> int:
        """Unregister all YAML-defined hooks.

        Returns:
            Number of unregistered hooks.
        """
        count = 0
        for hid in self._registered_ids:
            if self.engine.registry.unregister(hid):
                count += 1
        self._registered_ids.clear()
        self._loaded_defs.clear()
        return count

    def get_loaded_definitions(self) -> list[YAMLHookDefinition]:
        """Return all currently loaded hook definitions."""
        return list(self._loaded_defs.values())

    def get_statistics(self) -> dict[str, Any]:
        """Return config loader statistics."""
        return {
            "loaded_definitions": len(self._loaded_defs),
            "registered_hooks": len(self._registered_ids),
            "config_path": self.config_path,
        }


# =============================================================================
# HotReload
# =============================================================================


class HotReload:
    """Hot-reload hooks without restarting the engine.

    Watches hook config files for changes (by content hash) and
    reloads the configuration when changes are detected.

    Attributes:
        config_loader: The YAMLHookConfig to reload from.
        poll_interval: Seconds between polls.
        auto_reload: If True, reload on every poll cycle when changes detected.
    """

    def __init__(
        self,
        config_loader: YAMLHookConfig,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        auto_reload: bool = True,
    ) -> None:
        self.config_loader = config_loader
        self.poll_interval = poll_interval
        self.auto_reload = auto_reload

        self._last_poll: float = 0.0
        self._file_hashes: dict[str, str] = {}
        self._reload_count: int = 0

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def poll(self) -> bool:
        """Poll for configuration changes.

        Checks all matching config files for content hash changes.
        If changes are detected and auto_reload is True, reloads
        automatically.

        Returns:
            True if changes were detected (and reloaded if auto_reload).
        """
        now = time.time()
        if now - self._last_poll < self.poll_interval:
            return False

        self._last_poll = now
        config_path = self.config_loader.config_path

        matching = list(Path(".").glob(config_path))
        if not matching:
            try:
                matching = list(Path(config_path).parent.glob(config_path.split("/")[-1]))
            except (NotImplementedError, OSError):
                pass
        if not matching:
            p = Path(config_path)
            if p.exists() and p.is_file():
                matching = [p]

        changed = False
        for filepath in matching:
            try:
                content = filepath.read_bytes()
                hash_val = hashlib.md5(content, usedforsecurity=False).hexdigest()
                old_hash = self._file_hashes.get(str(filepath))

                if old_hash is None:
                    self._file_hashes[str(filepath)] = hash_val
                elif old_hash != hash_val:
                    logger.info("HotReload: detected change in %s", filepath)
                    self._file_hashes[str(filepath)] = hash_val
                    changed = True
            except OSError:
                continue

        if changed and self.auto_reload:
            self.reload()

        return changed

    def reload(self) -> int:
        """Force a full reload of all hook configurations.

        Unloads existing YAML-defined hooks and reloads from config files.

        Returns:
            Number of hooks registered in the reload.
        """
        self.config_loader.unload_all()
        count = self.config_loader.load()
        self._reload_count += 1
        logger.info("HotReload: reloaded %d hooks (reload #%d)", count, self._reload_count)
        return count

    def force_poll(self) -> bool:
        """Force an immediate poll, bypassing the interval."""
        saved = self._last_poll
        self._last_poll = 0.0
        result = self.poll()
        if not result:
            self._last_poll = saved
        return result

    def get_statistics(self) -> dict[str, Any]:
        """Return hot-reload statistics."""
        return {
            "poll_interval": self.poll_interval,
            "auto_reload": self.auto_reload,
            "reload_count": self._reload_count,
            "watched_files": len(self._file_hashes),
            "last_poll": self._last_poll,
        }


# =============================================================================
# Additional Handler Types
# =============================================================================


class HTTPHook:
    """Make an HTTP request when the hook fires.

    Config:
        url: Target URL.
        method: HTTP method (default: POST).
        headers: Optional dict of headers.
        timeout: Request timeout in seconds.
        include_context: If True, include HookContext as JSON body.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.url = config.get("url", "")
        self.method = config.get("method", "POST").upper()
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout", 5.0)
        self.include_context = config.get("include_context", False)

    def __call__(self, context: HookContext) -> HookResult:
        if not self.url:
            return HookResult.allow(hook_name="HTTPHook")

        try:
            import urllib.request
            import urllib.error

            data = None
            if self.include_context:
                payload = {
                    "hook_type": context.hook_type.value,
                    "tool_name": context.tool_name,
                    "session_id": context.session_id,
                    "agent_id": context.agent_id,
                    "timestamp": str(context.timestamp),
                }
                data = json.dumps(payload).encode("utf-8")

            req = urllib.request.Request(
                self.url,
                data=data,
                headers=self.headers,
                method=self.method,
            )
            urllib.request.urlopen(req, timeout=self.timeout)

        except Exception as e:
            logger.warning("HTTPHook: request failed: %s", e)

        return HookResult.allow(hook_name="HTTPHook")


class LogHook:
    """Write structured logs when the hook fires.

    Config:
        level: Log level (debug, info, warning, error).
        message: Log message template.
        include_context: If True, include context summary in log.
        format: Output format (text, json).
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.level = config.get("level", "info").lower()
        self.message = config.get("message", "Hook fired")
        self.include_context = config.get("include_context", True)
        self.format = config.get("format", "text")

    def __call__(self, context: HookContext) -> HookResult:
        level_map = {
            "debug": logger.debug,
            "info": logger.info,
            "warning": logger.warning,
            "error": logger.error,
        }
        log_fn = level_map.get(self.level, logger.info)

        if self.format == "json":
            record = {
                "message": self.message,
                "hook_type": context.hook_type.value,
                "tool_name": context.tool_name,
                "session_id": context.session_id,
                "agent_id": context.agent_id,
            }
            log_fn(json.dumps(record))
        else:
            ctx_info = ""
            if self.include_context:
                ctx_info = f" [type={context.hook_type.value}, tool={context.tool_name}]"
            log_fn("%s%s", self.message, ctx_info)

        return HookResult.allow(hook_name="LogHook")


class ScriptHook:
    """Execute an external script when the hook fires.

    Config:
        script: Path to the script to execute.
        args: Additional CLI arguments.
        timeout: Script execution timeout in seconds.
        pass_context: If True, pass context as environment variables.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.script = config.get("script", "")
        self.args = config.get("args", [])
        self.timeout = config.get("timeout", 10.0)
        self.pass_context = config.get("pass_context", False)

    def __call__(self, context: HookContext) -> HookResult:
        if not self.script:
            return HookResult.allow(hook_name="ScriptHook")

        if not os.path.isfile(self.script):
            logger.warning("ScriptHook: script not found: %s", self.script)
            return HookResult.allow(hook_name="ScriptHook")

        try:
            env = dict(os.environ)
            if self.pass_context:
                env["LYRA_HOOK_TYPE"] = context.hook_type.value
                env["LYRA_TOOL_NAME"] = context.tool_name or ""
                env["LYRA_SESSION_ID"] = context.session_id or ""
                env["LYRA_AGENT_ID"] = context.agent_id or ""

            cmd = [self.script] + list(self.args)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )
            if result.returncode != 0:
                logger.warning(
                    "ScriptHook: script %s exited with %d: %s",
                    self.script, result.returncode, result.stderr[:200],
                )
        except subprocess.TimeoutExpired:
            logger.warning("ScriptHook: script %s timed out after %.1fs", self.script, self.timeout)
        except Exception as e:
            logger.warning("ScriptHook: script %s failed: %s", self.script, e)

        return HookResult.allow(hook_name="ScriptHook")


class MetricsHook:
    """Emit metrics (counter, gauge, histogram) when the hook fires.

    Config:
        metric_name: Name of the metric.
        metric_type: Type (counter, gauge, histogram).
        value: Value to record (or extract from context via key).
        tags: Dict of tags to attach.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.metric_name = config.get("metric_name", "lyra.hook.fired")
        self.metric_type = config.get("metric_type", "counter")
        self.value = config.get("value", 1)
        self.tags = config.get("tags", {})

        self._counter: int = 0
        self._gauges: dict[str, float] = {}
        self._histogram: list[float] = []

    def __call__(self, context: HookContext) -> HookResult:
        tag_str = ",".join(f"{k}={v}" for k, v in self.tags.items())

        if self.metric_type == "counter":
            self._counter += 1
            logger.debug("MetricsHook: %s counter=%d [%s]", self.metric_name, self._counter, tag_str)

        elif self.metric_type == "gauge":
            val = self._resolve_value(context)
            self._gauges[self.metric_name] = val
            logger.debug("MetricsHook: %s gauge=%.2f [%s]", self.metric_name, val, tag_str)

        elif self.metric_type == "histogram":
            val = self._resolve_value(context)
            self._histogram.append(val)
            logger.debug("MetricsHook: %s histogram=%.2f [%s]", self.metric_name, val, tag_str)

        return HookResult.allow(hook_name="MetricsHook")

    def _resolve_value(self, context: HookContext) -> float:
        """Extract a numeric value from context or use default."""
        if isinstance(self.value, (int, float)):
            return float(self.value)
        if isinstance(self.value, str) and hasattr(context, self.value):
            attr_val = getattr(context, self.value, 0)
            try:
                return float(attr_val) if attr_val else 0.0
            except (TypeError, ValueError):
                return 0.0
        return 1.0

    def get_metrics(self) -> dict[str, Any]:
        """Return collected metrics."""
        result: dict[str, Any] = {
            "counter": self._counter,
        }
        if self._gauges:
            result["gauges"] = dict(self._gauges)
        if self._histogram:
            result["histogram_count"] = len(self._histogram)
            if self._histogram:
                result["histogram_avg"] = sum(self._histogram) / len(self._histogram)
        return result


class RateLimitHook:
    """Rate-limit operations by key.

    Config:
        key: Context field to use as rate-limit key (e.g., "agent_id").
        max_calls: Maximum calls per window.
        window_seconds: Time window in seconds.
        block_message: Message when rate limit is exceeded.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.key_field = config.get("key", "agent_id")
        self.max_calls = config.get("max_calls", 10)
        self.window_seconds = config.get("window_seconds", 60.0)
        self.block_message = config.get("block_message", "Rate limit exceeded")

        self._buckets: dict[str, list[float]] = defaultdict(list)

    def __call__(self, context: HookContext) -> HookResult:
        key = self._get_key(context)
        now = time.time()

        # Prune old entries
        bucket = self._buckets[key]
        bucket[:] = [t for t in bucket if now - t < self.window_seconds]

        if len(bucket) >= self.max_calls:
            logger.warning("RateLimitHook: rate limit exceeded for key '%s'", key)
            return HookResult.block(
                reason=f"{self.block_message} (key={key}, {len(bucket)}/{self.max_calls})",
                hook_name="RateLimitHook",
            )

        bucket.append(now)
        return HookResult.allow(hook_name="RateLimitHook")

    def _get_key(self, context: HookContext) -> str:
        """Extract the rate-limit key from context."""
        if self.key_field == "agent_id":
            return context.agent_id or "unknown"
        elif self.key_field == "session_id":
            return context.session_id or "unknown"
        elif self.key_field == "tool_name":
            return context.tool_name or "unknown"
        return "default"

    def get_statistics(self) -> dict[str, Any]:
        """Return rate-limit statistics."""
        return {
            "buckets": len(self._buckets),
            "max_calls_per_window": self.max_calls,
            "window_seconds": self.window_seconds,
            "active_keys": list(self._buckets.keys()),
        }


class CacheHook:
    """Cache results to reduce repeated computation.

    Config:
        key: Context field to use as cache key (e.g., "tool_input").
        ttl_seconds: Cache entry TTL.
        max_size: Maximum cache entries.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.key_field = config.get("key", "tool_input")
        self.ttl_seconds = config.get("ttl_seconds", 300.0)
        self.max_size = config.get("max_size", 1000)

        self._cache: dict[str, tuple[float, Any]] = {}

    def __call__(self, context: HookContext) -> HookResult:
        key = self._get_key(context)
        if not key:
            return HookResult.allow(hook_name="CacheHook")

        now = time.time()

        # Prune expired
        expired = [k for k, (ts, _) in self._cache.items() if now - ts > self.ttl_seconds]
        for k in expired:
            del self._cache[k]

        # Check cache
        if key in self._cache:
            logger.debug("CacheHook: cache hit for key '%s'", key[:60])
            cached_val = self._cache[key][1]
            # Return cached value as modified context
            return HookResult.modify(
                context=HookContext(
                    hook_type=context.hook_type,
                    tool_args=cached_val if isinstance(cached_val, dict) else {"cached": cached_val},
                    session_id=context.session_id,
                ),
                hook_name="CacheHook",
                reason="Cache hit",
            )

        # Cache miss: record for next time
        logger.debug("CacheHook: cache miss for key '%s'", key[:60])
        return HookResult.allow(hook_name="CacheHook")

    def store(self, key: str, value: Any) -> None:
        """Manually store a value in the cache.

        Args:
            key: Cache key.
            value: Value to cache.
        """
        full_key = f"manual:{key}"
        if len(self._cache) >= self.max_size:
            # Evict oldest
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][0])
            del self._cache[oldest]
        self._cache[full_key] = (time.time(), value)

    def _get_key(self, context: HookContext) -> str:
        """Extract the cache key from context."""
        if self.key_field == "tool_input":
            return json.dumps(context.tool_input, sort_keys=True) if context.tool_input else ""
        elif self.key_field == "tool_name":
            return context.tool_name or ""
        elif self.key_field == "agent_id":
            return context.agent_id or ""
        return ""

    def invalidate(self, pattern: str = "*") -> int:
        """Invalidate cache entries matching a pattern.

        Args:
            pattern: Key pattern (* = all).

        Returns:
            Number of invalidated entries.
        """
        import fnmatch

        if pattern == "*":
            count = len(self._cache)
            self._cache.clear()
            return count

        keys = [k for k in self._cache if fnmatch.fnmatch(k, pattern)]
        for k in keys:
            del self._cache[k]
        return len(keys)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def get_statistics(self) -> dict[str, Any]:
        """Return cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
        }
