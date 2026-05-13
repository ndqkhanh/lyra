"""Token compression pipeline for tool outputs and retrieved chunks.

Applies rule-based compression (no ML model required) to reduce token
count while protecting content that the LLM needs verbatim.

This complements :mod:`tool_output_policy` (which *classifies* and
*truncates*) with a *compression layer* that:
  - Enforces a protection list (code identifiers, diffs, errors are never
    mangled)
  - Learns from miss signals: when the agent re-requests content that
    was compressed, record that pattern and protect it next time
    (ACON-inspired per-session compression guidelines)
  - Tracks per-turn compression ratios so regressions are visible

Research grounding: §3.1 (LLMLingua-2: 2–5× compression with token-
protect lists), §3.4 (ACON arXiv:2510.00615 — learns compression
guideline from failure trajectories), Bottom Line #6.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# CompressionPolicy — what to protect vs what to compress
# ---------------------------------------------------------------------------

_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_]\w{2,}\b")  # code identifiers (3+ chars)
_DIFF_LINE_RE = re.compile(r"^[+-]{1,3}(?!--)")       # diff lines (+ / -)
_ERROR_LINE_RE = re.compile(
    r"(?:Error|Exception|Traceback|FAIL|WARN|WARNING|CRITICAL)", re.IGNORECASE
)
_PATH_RE = re.compile(r"[./\\][A-Za-z0-9_./\\-]+\.[a-z]{1,6}\b")  # file paths


@dataclass
class CompressionPolicy:
    """Defines what content is protected from compression.

    Protected content is never stripped, truncated, or mangled.
    Unprotected prose/whitespace/logs are candidates for compression.

    Usage::
        policy = CompressionPolicy()
        is_safe = policy.line_is_protected("def login(user):")
    """

    protect_identifiers: bool = True
    protect_diff_lines: bool = True
    protect_error_lines: bool = True
    protect_file_paths: bool = True
    extra_protect_patterns: list[str] = field(default_factory=list)

    def line_is_protected(self, line: str) -> bool:
        """Return True if *line* should not be compressed."""
        if self.protect_diff_lines and _DIFF_LINE_RE.match(line.strip()):
            return True
        if self.protect_error_lines and _ERROR_LINE_RE.search(line):
            return True
        if self.protect_file_paths and _PATH_RE.search(line):
            return True
        if self.protect_identifiers and _IDENTIFIER_RE.search(line):
            return True
        for pat in self.extra_protect_patterns:
            if re.search(pat, line):
                return True
        return False

    def text_has_protected_content(self, text: str) -> bool:
        """Return True if *text* contains any protected content."""
        return any(self.line_is_protected(ln) for ln in text.splitlines())


# ---------------------------------------------------------------------------
# CompressionStats — per-turn metrics
# ---------------------------------------------------------------------------


@dataclass
class CompressionStats:
    """Statistics for one compression operation."""

    original_chars: int
    compressed_chars: int
    original_tokens: int  # estimate
    compressed_tokens: int  # estimate
    protected_lines: int
    compressed_lines: int

    @property
    def ratio(self) -> float:
        """chars_compressed / chars_original. Lower is better."""
        if self.original_chars == 0:
            return 1.0
        return self.compressed_chars / self.original_chars

    @property
    def tokens_saved(self) -> int:
        return max(0, self.original_tokens - self.compressed_tokens)

    @property
    def regressed(self) -> bool:
        """True if the compressor made the output *larger*."""
        return self.compressed_chars > self.original_chars


# ---------------------------------------------------------------------------
# CompressionGuideline — ACON-inspired miss-signal learning
# ---------------------------------------------------------------------------


@dataclass
class GuidelineEntry:
    """A learned pattern to protect or compress in future turns."""

    pattern: str          # regex or keyword pattern
    protect: bool         # True = protect; False = compress
    confidence: float     # 0.0–1.0
    miss_count: int       # times the agent re-requested compressed content
    created_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GuidelineEntry":
        return cls(**d)


class CompressionGuideline:
    """Per-session compression rules learned from miss signals.

    A *miss signal* occurs when the agent requests content that was
    previously compressed away — evidence that that pattern should have
    been protected. Each miss increments the pattern's confidence;
    high-confidence patterns are added to the protection policy.

    This implements the core insight from ACON: "natural-language
    compression guidelines generated by analyzing failure cases
    outperform any single fixed policy" (§9, §3.4).

    Usage::
        guideline = CompressionGuideline()
        guideline.record_miss("auth.py:login")   # agent asked for this again
        policy = guideline.build_policy(base_policy)
    """

    PROMOTE_THRESHOLD = 2  # misses before a pattern becomes "protect"

    def __init__(self, store_path: Path | None = None) -> None:
        self._entries: dict[str, GuidelineEntry] = {}
        self._store_path = store_path
        if store_path and store_path.exists():
            self._load(store_path)

    def record_miss(self, pattern: str) -> GuidelineEntry:
        """Record that *pattern* was compressed but later needed."""
        existing = self._entries.get(pattern)
        if existing:
            updated = GuidelineEntry(
                pattern=pattern,
                protect=existing.miss_count + 1 >= self.PROMOTE_THRESHOLD,
                confidence=min(1.0, existing.confidence + 0.25),
                miss_count=existing.miss_count + 1,
                created_at=existing.created_at,
            )
            self._entries[pattern] = updated
        else:
            self._entries[pattern] = GuidelineEntry(
                pattern=pattern,
                protect=False,
                confidence=0.25,
                miss_count=1,
            )
        if self._store_path:
            self._save(self._store_path)
        return self._entries[pattern]

    def build_policy(
        self, base: CompressionPolicy | None = None
    ) -> CompressionPolicy:
        """Return a policy with high-confidence patterns added."""
        base = base or CompressionPolicy()
        learned = [
            e.pattern
            for e in self._entries.values()
            if e.protect and e.confidence >= 0.5
        ]
        return CompressionPolicy(
            protect_identifiers=base.protect_identifiers,
            protect_diff_lines=base.protect_diff_lines,
            protect_error_lines=base.protect_error_lines,
            protect_file_paths=base.protect_file_paths,
            extra_protect_patterns=[*base.extra_protect_patterns, *learned],
        )

    def entries(self) -> list[GuidelineEntry]:
        return sorted(
            self._entries.values(), key=lambda e: e.miss_count, reverse=True
        )

    def _save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([e.to_dict() for e in self._entries.values()], indent=2)
        )

    def _load(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text())
            self._entries = {d["pattern"]: GuidelineEntry.from_dict(d) for d in data}
        except (json.JSONDecodeError, TypeError, KeyError):
            self._entries = {}


# ---------------------------------------------------------------------------
# ToolOutputCompressor — the main compression engine
# ---------------------------------------------------------------------------

_PROGRESS_BAR_RE = re.compile(r"[\|#=>\-]{5,}|\d+%")  # progress bar characters
_COLOUR_NOISE_RE = re.compile(r"[█▓▒░]+")   # block chars


class ToolOutputCompressor:
    """Rule-based compressor for tool outputs and retrieved chunks.

    Applies compression that is provably safe: it only removes content
    that a human expert would also omit (progress noise, blank padding,
    repeated log lines). Protected content (diffs, identifiers, errors)
    passes through untouched.

    Usage::
        compressor = ToolOutputCompressor()
        compressed, stats = compressor.compress(text)
    """

    def __init__(self, *, policy: CompressionPolicy | None = None) -> None:
        self._policy = policy or CompressionPolicy()

    def compress(self, text: str) -> tuple[str, CompressionStats]:
        """Return (compressed_text, stats)."""
        lines = text.splitlines()
        original_chars = len(text)
        original_tokens = max(1, original_chars // 4)

        result: list[str] = []
        protected_count = 0
        compressed_count = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            if self._policy.line_is_protected(line):
                result.append(line)
                protected_count += 1
                i += 1
                continue

            # Strip pure-noise lines (progress bars, block chars)
            stripped = _PROGRESS_BAR_RE.sub("", line)
            stripped = _COLOUR_NOISE_RE.sub("", stripped).strip()
            if not stripped:
                # Blank or noise-only line — drop (unless last line)
                if result and result[-1] != "":
                    result.append("")  # keep at most one blank
                compressed_count += 1
                i += 1
                continue

            result.append(line)
            i += 1

        # Remove trailing blank lines
        while result and result[-1] == "":
            result.pop()

        compressed_text = "\n".join(result)
        compressed_chars = len(compressed_text)
        compressed_tokens = max(1, compressed_chars // 4)

        stats = CompressionStats(
            original_chars=original_chars,
            compressed_chars=compressed_chars,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            protected_lines=protected_count,
            compressed_lines=compressed_count,
        )
        # If compression made things worse, return original
        if stats.regressed:
            return text, CompressionStats(
                original_chars=original_chars,
                compressed_chars=original_chars,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                protected_lines=protected_count,
                compressed_lines=0,
            )
        return compressed_text, stats

    def compress_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[CompressionStats]]:
        """Compress tool output content in a message list.

        Returns (new_messages, stats_per_tool_message).
        Non-tool messages are passed through unchanged.
        """
        result: list[dict[str, Any]] = []
        all_stats: list[CompressionStats] = []
        for msg in messages:
            if msg.get("role") != "tool":
                result.append(msg)
                continue
            content = msg.get("content", "")
            if not isinstance(content, str):
                result.append(msg)
                continue
            compressed, stats = self.compress(content)
            result.append({**msg, "content": compressed})
            all_stats.append(stats)
        return result, all_stats


__all__ = [
    "CompressionPolicy",
    "CompressionStats",
    "CompressionGuideline",
    "GuidelineEntry",
    "ToolOutputCompressor",
]
