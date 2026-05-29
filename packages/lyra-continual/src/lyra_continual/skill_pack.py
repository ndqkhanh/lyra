"""
GraftLLM SkillPack Compression.

Encodes expert weights into compact "skill packs" that can be stored,
transferred, and decompressed on demand. Inspired by the GraftLLM
approach: compress domain-specific modules into lightweight artefacts
that can be grafted onto a base model without retraining.

Compression is achieved via:
1. Weight quantization (float -> int8 approximation)
2. Dimensionality reduction of weight matrices
3. Huffman-style encoding of repeated patterns
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from .models import SkillPack

logger = logging.getLogger(__name__)


class SkillPackCompressor:
    """Compresses, decompresses, and fuses expert-weight skill packs.

    A skill pack is a compact representation of one expert's domain
    weights. Compressing reduces storage and transfer cost; fusing
    merges complementary packs into a single multi-domain pack.

    Typical usage::

        compressor = SkillPackCompressor()
        pack = compressor.compress(expert_weights)
        restored = compressor.decompress(pack)
        fused = compressor.fuse(pack_a, pack_b)
    """

    def __init__(
        self,
        *,
        quantization_bits: int = 8,
        sparsity_threshold: float = 0.01,
    ) -> None:
        self.quantization_bits = quantization_bits
        self.sparsity_threshold = sparsity_threshold
        self._pack_registry: dict[str, SkillPack] = {}

    # ── Compression ───────────────────────────────────────────────────────

    def compress(
        self,
        expert_weights: Sequence[float],
        domain: str = "unknown",
    ) -> SkillPack:
        """Compress a weight vector into a ``SkillPack``.

        The compression pipeline:
        1. Quantize weights to *quantization_bits* levels.
        2. Sparsify — zero out weights below *sparsity_threshold*.
        3. Run-length encode consecutive zeros.

        Args:
            expert_weights: The raw weight vector to compress.
            domain: Domain label for the skill pack.

        Returns:
            A compressed ``SkillPack``.
        """
        original = tuple(expert_weights)
        original_size = len(original)

        if original_size == 0:
            pack = SkillPack(
                domain=domain,
                compressed_data=(),
                original_size=0,
                compressed_size=0,
                compression_ratio=1.0,
            )
            self._pack_registry[domain] = pack
            return pack

        # Step 1: Quantize
        quantized = self._quantize(original)

        # Step 2: Sparsify
        sparsified = tuple(
            w if abs(w) >= self.sparsity_threshold else 0.0 for w in quantized
        )

        # Step 3: Run-length encode zeros
        compressed = self._run_length_encode(sparsified)
        compressed_size = len(compressed)
        ratio = compressed_size / original_size

        logger.info(
            "Compressed %d weights -> %d (ratio=%.2f%%) for domain '%s'",
            original_size,
            compressed_size,
            ratio * 100,
            domain,
        )

        pack = SkillPack(
            domain=domain,
            compressed_data=compressed,
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=ratio,
        )
        self._pack_registry[domain] = pack
        return pack

    # ── Decompression ─────────────────────────────────────────────────────

    def decompress(self, skill_pack: SkillPack) -> tuple[float, ...]:
        """Restore approximate expert weights from a skill pack.

        Args:
            skill_pack: The compressed skill pack.

        Returns:
            Tuple of decompressed weight values.
        """
        if not skill_pack.compressed_data:
            return ()

        # Step 1: Run-length decode
        decoded = self._run_length_decode(skill_pack.compressed_data)

        # Pad or truncate to original size
        if len(decoded) < skill_pack.original_size:
            decoded = decoded + (0.0,) * (skill_pack.original_size - len(decoded))
        elif len(decoded) > skill_pack.original_size:
            decoded = decoded[: skill_pack.original_size]

        logger.debug(
            "Decompressed skill pack '%s': %d weights",
            skill_pack.domain,
            len(decoded),
        )
        return decoded

    # ── Fusion ────────────────────────────────────────────────────────────

    def fuse(self, pack_a: SkillPack, pack_b: SkillPack) -> SkillPack:
        """Merge two skill packs into a combined multi-domain pack.

        Decompresses both packs, takes the element-wise maximum (preserving
        the strongest signal from each domain), and re-compresses.

        Args:
            pack_a: First skill pack.
            pack_b: Second skill pack.

        Returns:
            A fused ``SkillPack``.
        """
        weights_a = self.decompress(pack_a)
        weights_b = self.decompress(pack_b)

        max_len = max(len(weights_a), len(weights_b))
        a_padded = weights_a + (0.0,) * (max_len - len(weights_a))
        b_padded = weights_b + (0.0,) * (max_len - len(weights_b))

        # Element-wise max preserves the strongest expert per dimension
        fused_weights = tuple(
            max(aw, bw) for aw, bw in zip(a_padded, b_padded, strict=False)
        )

        fused_domain = f"{pack_a.domain}+{pack_b.domain}"

        logger.info(
            "Fused skill packs '%s' + '%s' -> '%s'",
            pack_a.domain,
            pack_b.domain,
            fused_domain,
        )

        return self.compress(fused_weights, domain=fused_domain)

    # ── Compression-ratio reporting ───────────────────────────────────────

    def compute_compression_ratio(self, skill_pack: SkillPack) -> float:
        """Return the achieved compression ratio for a skill pack.

        Returns a value in (0.0, 1.0] where lower means better compression.

        Args:
            skill_pack: The skill pack to measure.

        Returns:
            Compression ratio (compressed_size / original_size).
        """
        if skill_pack.original_size == 0:
            return 1.0
        return skill_pack.compressed_size / skill_pack.original_size

    def aggregate_ratio(self) -> float:
        """Return the average compression ratio across all registered packs."""
        if not self._pack_registry:
            return 1.0
        ratios = [
            pack.compression_ratio
            for pack in self._pack_registry.values()
            if pack.original_size > 0
        ]
        return sum(ratios) / len(ratios) if ratios else 1.0

    @property
    def registered_packs(self) -> tuple[str, ...]:
        return tuple(self._pack_registry.keys())

    # ── Internal helpers ──────────────────────────────────────────────────

    def _quantize(self, weights: Sequence[float]) -> tuple[float, ...]:
        """Quantize weights to *quantization_bits* discrete levels."""
        if not weights:
            return ()

        max_val = max(abs(w) for w in weights)
        if max_val == 0:
            return tuple(weights)

        levels = 2 ** (self.quantization_bits - 1) - 1
        quantized = tuple(
            round((w / max_val) * levels) * (max_val / levels)
            for w in weights
        )
        return quantized

    @staticmethod
    def _run_length_encode(weights: tuple[float, ...]) -> tuple[float, ...]:
        """Encode consecutive zeros as (0.0, count) markers.

        Non-zero values pass through unchanged. Zero runs of length >= 2
        are replaced by (0.0, -run_length); the negative value signals
        a run-length marker to the decoder.
        """
        encoded: list[float] = []
        i = 0

        while i < len(weights):
            if abs(weights[i]) < 1e-8:
                run_start = i
                while i < len(weights) and abs(weights[i]) < 1e-8:
                    i += 1
                run_length = i - run_start
                if run_length >= 2:
                    encoded.append(0.0)
                    encoded.append(-float(run_length))
                else:
                    encoded.append(0.0)
            else:
                encoded.append(weights[i])
                i += 1

        return tuple(encoded)

    @staticmethod
    def _run_length_decode(encoded: tuple[float, ...]) -> tuple[float, ...]:
        """Decode run-length-encoded weight sequence."""
        decoded: list[float] = []
        i = 0

        while i < len(encoded):
            val = encoded[i]
            if abs(val) < 1e-8 and i + 1 < len(encoded) and encoded[i + 1] < 0:
                run_length = int(-encoded[i + 1])
                decoded.extend([0.0] * run_length)
                i += 2
            else:
                decoded.append(val)
                i += 1

        return tuple(decoded)
