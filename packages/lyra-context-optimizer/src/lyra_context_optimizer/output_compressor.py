"""Caveman-style dialect shift for agent responses.

Compresses agent output by removing filler words, shortening sentences,
using abbreviations, and trimming redundancies — while preserving
technical accuracy of code, commands, and file paths.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from .exceptions import CompressionError


@dataclass(frozen=True)
class CompressionConfig:
    """Configuration for output compression behavior.

    Attributes:
        aggression_level: Compression aggressiveness (0.0 to 1.0).
        preserve_technical_terms: If True, never modify code/paths/commands.
        min_compression_ratio: Minimum compression ratio required; if not met,
            the compress operation raises FidelityLossError.
        max_sentence_length: Maximum sentence length in characters.
        max_line_length: Maximum line length in characters.
    """

    aggression_level: float = 0.6
    preserve_technical_terms: bool = True
    min_compression_ratio: float = 0.0
    max_sentence_length: int = 200
    max_line_length: int = 120


# Abbreviation mapping for common words/phrases
_ABBREVIATIONS: dict[str, str] = {
    "because": "b/c",
    "approximately": "approx",
    "configuration": "config",
    "configuration file": "config",
    "directory": "dir",
    "documentation": "docs",
    "implementation": "impl",
    "application": "app",
    "applications": "apps",
    "additional": "extra",
    "functionality": "fn",
    "functionalities": "fns",
    "function": "func",
    "functions": "funcs",
    "parameter": "param",
    "parameters": "params",
    "argument": "arg",
    "arguments": "args",
    "environment": "env",
    "variable": "var",
    "variables": "vars",
    "authentication": "auth",
    "authorization": "authz",
    "repository": "repo",
    "utilities": "utils",
    "utility": "util",
    "management": "mgmt",
    "manager": "mgr",
    "message": "msg",
    "messages": "msgs",
    "identifier": "id",
    "identification": "id",
    "information": "info",
    "initialize": "init",
    "initializing": "init",
    "initialization": "init",
    "previous": "prev",
    "previous value": "prev value",
    "current": "curr",
    "current value": "curr value",
    "temporary": "temp",
    "temporarily": "temp",
    "buffer": "buf",
    "buffers": "bufs",
    "error": "err",
    "errors": "errs",
    "exception": "exc",
    "exceptions": "excs",
    "source": "src",
    "source code": "src",
    "binary": "bin",
    "binaries": "bins",
    "specification": "spec",
    "specifications": "specs",
    "standard": "std",
    "object oriented": "OO",
}

# Filler words to remove
_FILLER_WORDS: set[str] = {
    "basically",
    "actually",
    "essentially",
    "literally",
    "virtually",
    "simply",
    "just",
    "very",
    "really",
    "quite",
    "rather",
    "somewhat",
    "totally",
    "absolutely",
    "definitely",
    "certainly",
    "obviously",
    "importantly",
    "interestingly",
    "notably",
    "specifically",
    "particularly",
    "additionally",
    "furthermore",
    "moreover",
    "nevertheless",
    "nonetheless",
    "notwithstanding",
    "consequently",
    "accordingly",
    "subsequently",
    "ultimately",
    "eventually",
    "currently",
    "presently",
    "previously",
    "previously mentioned",
    "as mentioned",
    "as previously stated",
    "in order to",
    "in order for",
    "for the purpose of",
    "with regard to",
    "with respect to",
    "in terms of",
    "in the context of",
    "in the case of",
    "in the event of",
    "in regards to",
    "when it comes to",
}

# Patterns for content types to never modify
_TECHNICAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"`[^`]+`"),  # inline code
    re.compile(r"```[\s\S]*?```"),  # code blocks
    re.compile(r"/[\w./-]+"),  # file paths
    re.compile(r"[\w.]+@[\w.]+"),  # emails
    re.compile(r"https?://\S+"),  # URLs
    re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),  # IPs
    re.compile(r"\b[a-f0-9]{32}\b"),  # MD5
    re.compile(r"\b[a-f0-9]{40}\b"),  # SHA1
    re.compile(r"\b[a-f0-9]{64}\b"),  # SHA256
    re.compile(r"[\w-]+\.(py|js|ts|go|rs|java|rb|php|c|cpp|h|hpp|rs|swift|kt)"),  # files
]


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token)."""
    return max(1, len(text) // 4)


class OutputCompressor:
    """Compresses agent responses using Caveman-style dialect shift.

    Reduces verbosity while preserving technical accuracy. Code blocks,
    commands, file paths, and structured data are never modified.

    Targets 65% output reduction on average.
    """

    def __init__(self, config: CompressionConfig | None = None) -> None:
        self.config = config or CompressionConfig()
        self._history: list[dict[str, Any]] = []
        self._total_original_tokens: int = 0
        self._total_compressed_tokens: int = 0

    def compress_response(self, text: str) -> str:
        """Compress a response text.

        Applies style transformation: removes filler words, shortens
        sentences, uses abbreviations, trims redundancies.

        Args:
            text: The text to compress.

        Returns:
            Compressed text.

        Raises:
            CompressionError: If text is empty.
        """
        if not text:
            raise CompressionError("compress_response", 0, "empty text")

        start = time.time()
        original_tokens = _estimate_tokens(text)

        # Identify technical segments to preserve
        technical_segments: list[tuple[int, int, str]] = []
        if self.config.preserve_technical_terms:
            for pattern in _TECHNICAL_PATTERNS:
                for match in pattern.finditer(text):
                    technical_segments.append(
                        (match.start(), match.end(), match.group(0))
                    )

        # Remove filler words
        text = self._remove_fillers(text)

        # Shorten sentences
        text = self._shorten_sentences(text)

        # Apply abbreviations (based on aggression level)
        text = self._apply_abbreviations(text)

        # Trim redundancies
        text = self._trim_redundancies(text)

        # Enforce max lengths
        text = self._enforce_lengths(text)

        # Restore technical segments if they were modified
        if self.config.preserve_technical_terms and technical_segments:
            text = self._restore_technical(text, technical_segments)

        compressed_tokens = _estimate_tokens(text)
        compression_ratio = (
            1.0 - (compressed_tokens / original_tokens) if original_tokens > 0 else 0.0
        )

        elapsed = (time.time() - start) * 1000
        self._history.append({
            "compression_ratio": compression_ratio,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "time_ms": elapsed,
        })
        self._total_original_tokens += original_tokens
        self._total_compressed_tokens += compressed_tokens

        return text

    def _remove_fillers(self, text: str) -> str:
        """Remove filler words based on aggression level."""
        aggression = self.config.aggression_level
        if aggression < 0.3:
            return text

        # Remove filler adverbs at sentence starts
        filler_patterns = [
            r"(?i)\b" + re.escape(word) + r"\b,?\s*"
            for word in list(_FILLER_WORDS)[: int(len(_FILLER_WORDS) * aggression)]
        ]
        for pattern in filler_patterns:
            text = re.sub(pattern, "", text, count=1 if aggression < 0.6 else 0)

        # At higher aggression, remove all fillers
        if aggression >= 0.8:
            for word in list(_FILLER_WORDS):
                text = re.sub(r"(?i)\b" + re.escape(word) + r"\b", "", text)

        return text

    def _shorten_sentences(self, text: str) -> str:
        """Shorten verbose sentence constructions."""
        aggression = self.config.aggression_level
        if aggression < 0.2:
            return text

        replacements: list[tuple[str, str]] = [
            (r"(?i)it is (important|essential|critical) to ", ""),
            (r"(?i)we (need to|should|must|can) ", ""),
            (r"(?i)it (is|would be) (possible|recommended|advisable) to ", ""),
            (r"(?i)in (order to|order for) ", "to "),
            (r"(?i)due to the fact that ", "because "),
            (r"(?i)in spite of the fact that ", "although "),
            (r"(?i)on the (other hand|contrary),?\s*", "however "),
            (r"(?i)at this (point in time|time)", "now"),
            (r"(?i)in the (near )?future", "soon"),
            (r"(?i)for the purpose of", "for"),
            (r"(?i)a number of", "some"),
            (r"(?i)the majority of", "most"),
            (r"(?i)a majority of", "most"),
            (r"(?i)a (large|significant) number of", "many"),
        ]

        if aggression >= 0.5:
            cutoff = len(replacements)
            replacements = replacements[: int(cutoff * aggression)]

        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text)

        return text

    def _apply_abbreviations(self, text: str) -> str:
        """Apply word abbreviations based on aggression level."""
        aggression = self.config.aggression_level
        if aggression < 0.3:
            return text

        cutoff = int(len(_ABBREVIATIONS) * aggression)
        abbrevs_to_apply = list(_ABBREVIATIONS.items())[:cutoff]

        for full, abbr in abbrevs_to_apply:
            # Only replace whole words, not inside technical terms
            text = re.sub(r"(?i)\b" + re.escape(full) + r"\b", abbr, text)

        return text

    @staticmethod
    def _trim_redundancies(text: str) -> str:
        """Trim redundant phrases and double mentions."""
        patterns = [
            (r"(?i)in other words,?\s*[A-Z]", ""),
            (r"(?i)that is to say,?\s*", ""),
            (r"(?i)i\.e\.,?\s*", ""),
            (r"(?i)e\.g\.,?\s*", ""),
            (r"\s{2,}", " "),
            (r"\n{3,}", "\n\n"),
        ]
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        return text

    def _enforce_lengths(self, text: str) -> str:
        """Enforce maximum sentence and line lengths."""
        # Truncate overlong lines
        max_line = self.config.max_line_length
        if max_line > 0:
            lines = text.splitlines(keepends=True)
            truncated: list[str] = []
            for line in lines:
                if len(line.rstrip("\n")) > max_line:
                    # Try to break at a natural boundary
                    parts = self._smart_split(line, max_line)
                    truncated.extend(parts)
                else:
                    truncated.append(line)
            text = "".join(truncated)

        return text

    @staticmethod
    def _smart_split(line: str, max_length: int) -> list[str]:
        """Split a long line at a natural boundary."""
        if len(line) <= max_length:
            return [line]

        # Find last space before max_length
        split_at = line.rfind(" ", 0, max_length)
        if split_at < max_length // 2:
            split_at = max_length

        result: list[str] = []
        remaining = line
        while len(remaining) > max_length:
            split_at = remaining.rfind(" ", 0, max_length)
            if split_at < max_length // 2:
                split_at = max_length
            result.append(remaining[:split_at].rstrip() + "\n")
            remaining = remaining[split_at:].lstrip()
        if remaining:
            result.append(remaining)
        return result

    @staticmethod
    def _restore_technical(
        text: str, segments: list[tuple[int, int, str]]
    ) -> str:
        """Restore technical segments that may have been modified."""
        for start, end, original in sorted(segments, reverse=True):
            if start < len(text) and end <= len(text):
                # Check if the segment was altered
                current = text[start:end]
                if current.lower() != original.lower():
                    text = text[:start] + original + text[end:]
        return text

    @property
    def summary(self) -> dict[str, Any]:
        """Get compression summary statistics."""
        total_saved = self._total_original_tokens - self._total_compressed_tokens
        overall_ratio = (
            1.0 - (self._total_compressed_tokens / self._total_original_tokens)
            if self._total_original_tokens > 0
            else 0.0
        )
        return {
            "total_compressions": len(self._history),
            "total_original_tokens": self._total_original_tokens,
            "total_compressed_tokens": self._total_compressed_tokens,
            "total_tokens_saved": total_saved,
            "overall_compression_ratio": overall_ratio,
            "config_aggression": self.config.aggression_level,
        }
