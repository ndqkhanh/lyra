"""Latent space decoder — reconstructs text from compressed latent vectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from .exceptions import DecodingError
from .latent_encoder import LatentEncoder, LatentVector

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class DecodingConfig:
    fidelity_threshold: float = 0.5
    max_tokens: int = 50
    preserve_key_terms: bool = True


@dataclass(frozen=True)
class DecodedMessage:
    text: str
    confidence: float
    semantic_fidelity: float
    key_terms: tuple[str, ...]


def compute_fidelity(original: str | list[str], decoded: str | list[str]) -> float:
    """Compute semantic fidelity between original and decoded text.

    Uses Jaccard similarity on token sets.
    """
    if isinstance(original, str):
        orig_tokens = set(original.lower().split())
    else:
        orig_tokens = set(t.lower() for t in original)

    if isinstance(decoded, str):
        dec_tokens = set(decoded.lower().split())
    else:
        dec_tokens = set(t.lower() for t in decoded)

    if not orig_tokens and not dec_tokens:
        return 1.0
    if not orig_tokens or not dec_tokens:
        return 0.0

    intersection = orig_tokens & dec_tokens
    union = orig_tokens | dec_tokens
    return len(intersection) / len(union)


class LatentDecoder:
    """Reconstructs text from latent vector representations."""

    def __init__(self, encoder: LatentEncoder) -> None:
        self.encoder = encoder

    def _reconstruct_vector(
        self, vector: LatentVector, target_dim: int
    ) -> np.ndarray:
        """Reconstruct original-space vector from latent representation."""
        if self.encoder._pca_components is not None:
            k = vector.compressed_length
            components = self.encoder._pca_components[:k]
            mean = self.encoder._pca_mean
            if mean is not None:
                return (components.T @ vector.vector + mean).astype(np.float64)
            return (components.T @ vector.vector).astype(np.float64)

        if self.encoder._random_matrix is not None:
            mat = self.encoder._random_matrix
            k = min(vector.compressed_length, mat.shape[0])
            pseudo_inv = np.linalg.pinv(mat[:k])
            return (pseudo_inv @ vector.vector[:k]).astype(np.float64)

        vocab_size = target_dim or len(self.encoder.vocabulary)
        result = np.zeros(vocab_size, dtype=np.float64)
        for i, val in enumerate(vector.vector):
            if i < vocab_size:
                result[i] = val
        return result

    def _recover_terms_from_vector(
        self, reconstructed: np.ndarray, top_n: int = 10
    ) -> list[str]:
        vocab = self.encoder.vocabulary
        if not vocab:
            return []

        index_to_word = {v: k for k, v in vocab.items()}
        top_indices = np.argsort(reconstructed)[-top_n:][::-1]
        terms: list[str] = []
        for idx in top_indices:
            word = index_to_word.get(int(idx))
            if word is not None and reconstructed[int(idx)] > 0:
                terms.append(word)
        return terms

    def _generate_text(self, key_terms: list[str], max_tokens: int) -> str:
        if not key_terms:
            return ""
        text = " ".join(key_terms[:max_tokens])
        return text

    def decode(
        self, vector: LatentVector, config: DecodingConfig | None = None
    ) -> DecodedMessage:
        cfg = config or DecodingConfig()
        if vector.vector.size == 0:
            raise DecodingError("Cannot decode an empty latent vector")

        try:
            reconstructed = self._reconstruct_vector(vector, len(self.encoder.vocabulary))
            key_terms = self._recover_terms_from_vector(reconstructed)

            if cfg.preserve_key_terms and key_terms:
                text = self._generate_text(key_terms, cfg.max_tokens)
            else:
                text = ""

            decoded_terms = self.encoder._tokenize(text) if text else []
            key_term_overlap = set(key_terms) & (
                set(decoded_terms) if decoded_terms else set(key_terms)
            )
            if key_terms:
                fidelity = len(key_term_overlap) / len(set(key_terms))
            else:
                fidelity = 0.0

            if text:
                conf = min(1.0, max(0.0, fidelity * 0.8 + 0.2))
            else:
                conf = fidelity * 0.5

            decoded = DecodedMessage(
                text=text,
                confidence=conf,
                semantic_fidelity=fidelity,
                key_terms=tuple(key_terms),
            )

            if fidelity < cfg.fidelity_threshold and decoded.key_terms:
                decoded = DecodedMessage(
                    text=" ".join(key_terms[:5]),
                    confidence=conf * 0.6,
                    semantic_fidelity=fidelity,
                    key_terms=tuple(key_terms),
                )

            return decoded

        except Exception as exc:
            raise DecodingError(f"Failed to decode latent vector: {exc}") from exc

    def batch_decode(
        self, vectors: Sequence[LatentVector], config: DecodingConfig | None = None
    ) -> list[DecodedMessage]:
        return [self.decode(v, config) for v in vectors]

    def recover_key_terms(self, vector: LatentVector) -> list[str]:
        try:
            reconstructed = self._reconstruct_vector(vector, len(self.encoder.vocabulary))
            return self._recover_terms_from_vector(reconstructed)
        except Exception as exc:
            raise DecodingError(
                f"Failed to recover key terms: {exc}"
            ) from exc
