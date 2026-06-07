"""
Headroom Bridge — MCP-integrated context compression for Lyra.

Integrates headroom (chopratejas/headroom, Apache 2.0) into Lyra's
context pipeline via MCP tools. headroom achieves 60-95% token reduction
with zero accuracy loss across agent workloads (code search, SRE
debugging, issue triage, codebase exploration).

Uses headroom's CCR (Compress-Cache-Retrieve) protocol:
1. Compress: replace heavy content with ``<<ccr:hash>>`` markers
2. Cache: store originals in SQLite/Redis keyed by BLAKE3 hash
3. Retrieve: agent calls ``headroom_retrieve`` MCP tool on demand

References
----------
- headroom: https://github.com/chopratejas/headroom (Apache 2.0)
- headroom deep-dive: notes/web/chopratejas__headroom.md
- Lyra §4.3 Context Engineering Plan: plans/4.3-context-engineering.md
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CompressionMode(str, Enum):
    """Headroom delivery modes."""

    PROXY = "proxy"       # Local HTTP proxy (zero code change)
    LIBRARY = "library"   # Inline compress(messages) API
    MCP = "mcp"           # MCP tools (headroom_compress, headroom_retrieve)
    WRAP = "wrap"         # One-command agent wrapper


@dataclass
class CompressionStats:
    """Statistics from a headroom compression pass.

    Attributes:
        original_tokens: Estimated tokens before compression.
        compressed_tokens: Estimated tokens after compression.
        reduction_pct: Percentage reduction.
        cache_hits: Number of CCR cache hits.
        compressor_used: Which compressor was applied.
    """

    original_tokens: int
    compressed_tokens: int
    reduction_pct: float
    cache_hits: int = 0
    compressor_used: str = "unknown"

    @property
    def tokens_saved(self) -> int:
        return self.original_tokens - self.compressed_tokens


@dataclass
class HeadroomBridge:
    """Bridge between Lyra's context pipeline and headroom compression.

    Usage::

        bridge = HeadroomBridge(mode=CompressionMode.MCP)
        stats = bridge.compress_messages([
            {"role": "user", "content": large_tool_output},
            {"role": "assistant", "content": "..."},
        ])
        print(f"Saved {stats.tokens_saved} tokens ({stats.reduction_pct:.0f}%)")
    """

    mode: CompressionMode = CompressionMode.MCP
    proxy_port: int = 8787
    _ccr_cache: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compress_messages(
        self,
        messages: list[dict[str, str]],
        aggressive: bool = False,
    ) -> CompressionStats:
        """Compress a list of chat messages using headroom.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts.
            aggressive: If True, use maximum compression (may lose nuance).

        Returns:
            CompressionStats with before/after token counts.
        """
        original_tokens = self._estimate_tokens(messages)

        if self.mode == CompressionMode.LIBRARY:
            compressed = self._compress_library(messages, aggressive)
        elif self.mode == CompressionMode.MCP:
            compressed = self._compress_mcp(messages, aggressive)
        elif self.mode == CompressionMode.PROXY:
            compressed = self._compress_proxy(messages, aggressive)
        else:
            compressed = messages  # WRAP mode not applicable inline

        compressed_tokens = self._estimate_tokens(compressed)
        reduction = (
            (original_tokens - compressed_tokens) / original_tokens * 100
            if original_tokens > 0
            else 0.0
        )

        return CompressionStats(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            reduction_pct=round(reduction, 1),
            compressor_used=f"headroom-{self.mode.value}",
        )

    def retrieve(self, ccr_hash: str) -> Optional[str]:
        """Retrieve original content for a CCR hash marker.

        Args:
            ccr_hash: The hash from a ``<<ccr:hash>>`` marker.

        Returns:
            Original content, or None if not in cache.
        """
        # Check local cache first
        if ccr_hash in self._ccr_cache:
            return self._ccr_cache[ccr_hash]

        # Try headroom's cache via MCP
        if self.mode == CompressionMode.MCP:
            try:
                result = subprocess.run(
                    ["headroom", "retrieve", ccr_hash],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return None

    def preload_cache(self, key: str, content: str) -> None:
        """Preload the CCR cache with known content.

        Useful for frequently-referenced documents (system prompts,
        skill files, etc.) that should be compressed to hash markers
        but instantly retrievable.
        """
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
        self._ccr_cache[hash_val] = content

    def install_mcp_tools(self) -> list[dict[str, Any]]:
        """Return MCP tool definitions for headroom integration.

        These can be registered with Lyra's MCP gateway so agents
        can call headroom_compress and headroom_retrieve directly.
        """
        return [
            {
                "name": "headroom_compress",
                "description": (
                    "Compress context by 60-95% using headroom. "
                    "Replaces heavy content with CCR markers. "
                    "Use before sending large tool outputs to the model."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Content to compress",
                        },
                        "aggressive": {
                            "type": "boolean",
                            "description": "Use maximum compression",
                            "default": False,
                        },
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "headroom_retrieve",
                "description": (
                    "Retrieve original content for a CCR hash marker. "
                    "Call when you need to read the full content behind "
                    "a <<ccr:hash>> marker."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "ccr_hash": {
                            "type": "string",
                            "description": "The hash from a <<ccr:hash>> marker",
                        },
                    },
                    "required": ["ccr_hash"],
                },
            },
            {
                "name": "headroom_stats",
                "description": "Get compression statistics for the current session.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def should_compress(self, content: str) -> bool:
        """Heuristic: should this content be compressed?

        Compression is most valuable for:
        - Large tool outputs (>1000 chars)
        - JSON/structured data (repetitive schema)
        - Log files (repetitive lines)
        - Code search results (many similar snippets)

        Compression is NOT valuable for:
        - Short messages (<200 chars)
        - Single unique facts
        - User instructions
        """
        if len(content) < 200:
            return False
        if len(content) > 1000:
            return True
        # Heuristic: JSON-like or repetitive content
        if content.count("{") > 10 or content.count("\n") > 20:
            return True
        return False

    # ------------------------------------------------------------------
    # Internal compression backends
    # ------------------------------------------------------------------

    def _compress_library(
        self, messages: list[dict[str, str]], aggressive: bool
    ) -> list[dict[str, str]]:
        """Use headroom's Python library API (requires `pip install headroom`)."""
        try:
            import headroom  # type: ignore[import-untyped]

            raw = json.dumps(messages)
            compressed_str = headroom.compress(raw, aggressive=aggressive)
            return json.loads(compressed_str)
        except ImportError:
            # Fallback: basic dedup + truncation
            return self._fallback_compress(messages, aggressive)

    def _compress_mcp(
        self, messages: list[dict[str, str]], aggressive: bool
    ) -> list[dict[str, str]]:
        """Use headroom via subprocess/MCP call."""
        try:
            raw = json.dumps(messages)
            args = ["headroom", "compress"]
            if aggressive:
                args.append("--aggressive")
            result = subprocess.run(
                args,
                input=raw,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

        return self._fallback_compress(messages, aggressive)

    def _compress_proxy(
        self, messages: list[dict[str, str]], aggressive: bool
    ) -> list[dict[str, str]]:
        """Use headroom via local HTTP proxy."""
        import urllib.request

        try:
            data = json.dumps({
                "messages": messages,
                "aggressive": aggressive,
            }).encode()
            req = urllib.request.Request(
                f"http://localhost:{self.proxy_port}/compress",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception:
            return self._fallback_compress(messages, aggressive)

    @staticmethod
    def _fallback_compress(
        messages: list[dict[str, str]], aggressive: bool
    ) -> list[dict[str, str]]:
        """Basic fallback compression when headroom is unavailable.

        Truncates large content and deduplicates repeated patterns.
        """
        max_len = 500 if aggressive else 2000
        compressed = []
        seen = set()

        for msg in messages:
            content = msg.get("content", "")
            if len(content) > max_len:
                # Keep first and last portion for context
                half = max_len // 2
                content = content[:half] + f"\n... [{len(content) - max_len} chars truncated] ...\n" + content[-half:]

            # Dedup identical messages
            content_hash = hashlib.md5(content.encode()).hexdigest()
            if content_hash in seen:
                content = f"[Duplicate of previous message — {len(content)} chars]"
            else:
                seen.add(content_hash)

            compressed.append({**msg, "content": content})

        return compressed

    @staticmethod
    def _estimate_tokens(messages: list[dict[str, str]]) -> int:
        """Rough token estimation: 1 token ≈ 4 characters."""
        total = sum(len(m.get("content", "")) for m in messages)
        return total // 4
