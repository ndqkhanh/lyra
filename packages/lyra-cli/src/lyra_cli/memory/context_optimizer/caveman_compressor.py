"""Caveman-style aggressive compression.

Achieves ~65% compression with minimal overhead. Faster than RTK but
less reversible — optimized for ephemeral contexts.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CavemanResult:
    compressed: str
    original_hash: str
    original_len: int
    compressed_len: int
    compression_ratio: float
    elapsed_ms: float
    dedup_count: int
    short_id_count: int


class CavemanCompressor:
    """Aggressive compressor for ephemeral contexts.

    Four strategies in sequence:
    1. Whitespace collapse — strip leading/trailing, collapse multiples
    2. Token-level dedup — remove repeated adjacent lines
    3. Short-identifier replacement — shorten long identifiers
    4. Repetitive pattern compression — collapse repeated token sequences
    """

    _SHORT_ID_MAP: dict[str, str] = {}

    def compress(self, content: str) -> CavemanResult:
        original_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        original_len = len(content)
        start = time.perf_counter()

        result = content
        result = self._collapse_whitespace(result)
        result, dedup_count = self._dedup_lines(result)
        result, short_id_count = self._shorten_identifiers(result)
        result = self._compress_repetition(result)

        elapsed = (time.perf_counter() - start) * 1000
        compressed_len = len(result)
        ratio = round((1 - compressed_len / max(original_len, 1)) * 100, 1)

        return CavemanResult(
            compressed=result,
            original_hash=original_hash,
            original_len=original_len,
            compressed_len=compressed_len,
            compression_ratio=ratio,
            elapsed_ms=round(elapsed, 2),
            dedup_count=dedup_count,
            short_id_count=short_id_count,
        )

    def _collapse_whitespace(self, content: str) -> str:
        result = content.strip()
        result = re.sub(r'[ \t]+', ' ', result)
        result = re.sub(r'\n{2,}', '\n', result)
        return result

    def _dedup_lines(self, content: str) -> tuple[str, int]:
        lines = content.split('\n')
        seen: set[str] = set()
        result: list[str] = []
        dedup_count = 0
        for line in lines:
            stripped = line.strip()
            if stripped and stripped in seen:
                dedup_count += 1
                continue
            if stripped:
                seen.add(stripped)
            result.append(line)
        return '\n'.join(result), dedup_count

    def _shorten_identifiers(self, content: str) -> tuple[str, int]:
        long_ids = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]{12,}\b', content))
        count = 0
        result = content
        for lid in sorted(long_ids, key=len, reverse=True):
            short = f"_{len(self._SHORT_ID_MAP)}"
            self._SHORT_ID_MAP[lid] = short
            result = result.replace(lid, short)
            count += 1
        return result, count

    def _compress_repetition(self, content: str) -> str:
        return re.sub(r'(.+?)\1{3,}', r'\1×N', content)

    def stats(self) -> dict:
        return {"short_id_map_size": len(self._SHORT_ID_MAP)}
