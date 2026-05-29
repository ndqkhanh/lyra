"""Recursive latent link module — core RecursiveMAS aggregation logic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import numpy as np

from lyra_recursive_link.exceptions import LinkError
from lyra_recursive_link.latent_encoder import LatentVector, compute_compression_ratio, similarity


class AggregationMethod(Enum):
    MEAN = auto()
    MAX = auto()
    ATTENTION = auto()
    WEIGHTED_SUM = auto()


@dataclass(frozen=True)
class LinkConfig:
    depth: int = 1
    width: int = 4
    aggregation_method: AggregationMethod = AggregationMethod.MEAN
    residual_connection: bool = True
    attention_temperature: float = 1.0


@dataclass(frozen=True)
class LinkMetrics:
    compression_achieved: float
    semantic_loss: float
    hop_count: int
    num_messages: int


class RecursiveLink:
    """Core RecursiveMAS module for recursive latent aggregation."""

    def __init__(self, default_config: LinkConfig | None = None) -> None:
        self.default_config = default_config or LinkConfig()

    def forward(
        self,
        messages: list[LatentVector],
        config: LinkConfig | None = None,
    ) -> LatentVector:
        cfg = config or self.default_config
        if not messages:
            raise LinkError("Cannot aggregate empty message list")
        if len(messages) == 1:
            return messages[0]

        self._validate_dimensions(messages)

        if cfg.aggregation_method == AggregationMethod.MEAN:
            aggregated = self._mean_aggregate(messages)
        elif cfg.aggregation_method == AggregationMethod.MAX:
            aggregated = self._max_aggregate(messages)
        elif cfg.aggregation_method == AggregationMethod.ATTENTION:
            aggregated = self._attention_aggregate(messages, cfg)
        elif cfg.aggregation_method == AggregationMethod.WEIGHTED_SUM:
            aggregated = self._weighted_sum(messages)
        else:
            raise LinkError(f"Unknown aggregation method: {cfg.aggregation_method}")

        if cfg.residual_connection:
            return self.residual_link(messages[-1], aggregated)

        last = messages[-1]
        from lyra_recursive_link.latent_encoder import compute_compression_ratio

        cr = compute_compression_ratio(last.original_length, len(aggregated))
        return LatentVector(
            vector=aggregated,
            original_length=last.original_length,
            compressed_length=len(aggregated),
            compression_ratio=cr,
            semantic_hash=last.semantic_hash,
        )

    def __call__(
        self,
        messages: list[LatentVector],
        config: LinkConfig | None = None,
    ) -> LatentVector:
        return self.forward(messages, config)

    def _validate_dimensions(self, messages: list[LatentVector]) -> None:
        dim = len(messages[0].vector)
        for m in messages:
            if len(m.vector) != dim:
                raise LinkError(
                    f"All messages must have same latent dimension (got {len(m.vector)}, expected {dim})"
                )

    def _mean_aggregate(self, messages: list[LatentVector]) -> np.ndarray:
        vectors = np.array([m.vector for m in messages])
        return np.mean(vectors, axis=0).astype(np.float64)

    def _max_aggregate(self, messages: list[LatentVector]) -> np.ndarray:
        vectors = np.array([m.vector for m in messages])
        return np.max(vectors, axis=0).astype(np.float64)

    def _attention_aggregate(
        self, messages: list[LatentVector], cfg: LinkConfig
    ) -> np.ndarray:
        vectors = np.array([m.vector for m in messages])
        query = vectors[-1:]
        keys = vectors[:-1] if len(vectors) > 1 else vectors
        if keys.shape[0] == 0:
            keys = vectors
            query = vectors[:1]

        scores = np.dot(keys, query.T).flatten()
        temperature = max(0.001, cfg.attention_temperature)
        weights = np.exp(scores / temperature)
        weights = weights / (np.sum(weights) + 1e-10)
        weighted_sum = np.sum(
            keys * weights.reshape(-1, 1), axis=0
        ).astype(np.float64)
        return weighted_sum

    def _weighted_sum(self, messages: list[LatentVector]) -> np.ndarray:
        vectors = np.array([m.vector for m in messages])
        n = len(messages)
        weights = np.array(
            [1.0 / (i + 1) for i in range(n)], dtype=np.float64
        )
        weights = weights / np.sum(weights)
        return np.sum(vectors * weights.reshape(-1, 1), axis=0).astype(np.float64)

    def residual_link(
        self, original: LatentVector, aggregated: np.ndarray | LatentVector
    ) -> LatentVector:
        agg_vec = aggregated.vector if isinstance(aggregated, LatentVector) else aggregated
        residual = (original.vector + agg_vec) / 2.0
        cr = compute_compression_ratio(
            original.original_length, len(residual)
        )
        return LatentVector(
            vector=residual.astype(np.float64),
            original_length=original.original_length,
            compressed_length=len(residual),
            compression_ratio=cr,
            semantic_hash=original.semantic_hash,
        )

    def multi_hop(
        self,
        agents_latents: list[list[LatentVector]],
        hops: int = 2,
        config: LinkConfig | None = None,
    ) -> list[LatentVector]:
        cfg = config or self.default_config
        if not agents_latents:
            raise LinkError("Cannot perform multi-hop on empty agents list")
        if hops < 1:
            raise LinkError("hops must be at least 1")

        current = agents_latents
        for _ in range(hops):
            next_round: list[LatentVector] = []
            for i, latents in enumerate(current):
                neighbor_idx = (i + 1) % len(current)
                combined = latents + current[neighbor_idx]
                aggregated = self.forward(combined, cfg)
                next_round.append(aggregated)
            current = [[lv] for lv in next_round]

        return [lv[0] for lv in current]

    def compute_metrics(
        self,
        original_messages: list[LatentVector],
        aggregated: LatentVector,
        hop_count: int,
    ) -> LinkMetrics:
        if not original_messages:
            return LinkMetrics(
                compression_achieved=0.0,
                semantic_loss=0.0,
                hop_count=hop_count,
                num_messages=0,
            )

        avg_compression = np.mean([m.compression_ratio for m in original_messages]).item()

        total_loss = 0.0
        for msg in original_messages:
            try:
                sim = similarity(msg, aggregated)
                total_loss += 1.0 - sim
            except ValueError:
                total_loss += 0.0
        avg_loss = total_loss / len(original_messages)

        return LinkMetrics(
            compression_achieved=avg_compression,
            semantic_loss=avg_loss,
            hop_count=hop_count,
            num_messages=len(original_messages),
        )
