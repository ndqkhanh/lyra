"""
BGE-M3 Embedder Integration for Lyra

Wrapper for BGE-M3 (BAAI General Embedding Model v3) - a 568M parameter
dense embedding model supporting 100+ languages with 8192 token context.

Used for HippoRAG 2 dense embedding fusion.
"""

from typing import List, Union, Optional
import numpy as np


class BGE_M3_Embedder:
    """
    BGE-M3 embedder wrapper for Lyra memory system.

    Supports:
    - Dense embeddings (768-dim)
    - Sparse embeddings (lexical matching)
    - Multi-vector embeddings (ColBERT-style)
    - 8192 token context window
    - 100+ languages
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cpu",
        use_fp16: bool = False
    ):
        """
        Initialize BGE-M3 embedder.

        Args:
            model_name: HuggingFace model name
            device: Device to run on ('cpu', 'cuda', 'mps')
            use_fp16: Use FP16 for faster inference (requires GPU)
        """
        self.model_name = model_name
        self.device = device
        self.use_fp16 = use_fp16
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        """Lazy load model on first use."""
        if self._model is not None:
            return

        try:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=self.use_fp16,
                device=self.device
            )
        except ImportError:
            raise ImportError(
                "FlagEmbedding not installed. Install with: "
                "pip install FlagEmbedding"
            )

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        max_length: int = 8192,
        return_dense: bool = True,
        return_sparse: bool = False,
        return_colbert: bool = False
    ) -> Union[np.ndarray, dict]:
        """
        Encode texts to embeddings.

        Args:
            texts: Single text or list of texts
            batch_size: Batch size for encoding
            max_length: Maximum sequence length
            return_dense: Return dense embeddings (768-dim)
            return_sparse: Return sparse embeddings (lexical)
            return_colbert: Return ColBERT multi-vector embeddings

        Returns:
            Dense embeddings (np.ndarray) or dict with multiple types
        """
        self._load_model()

        # Convert single text to list
        if isinstance(texts, str):
            texts = [texts]
            single_input = True
        else:
            single_input = False

        # Encode
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            max_length=max_length,
            return_dense=return_dense,
            return_sparse=return_sparse,
            return_colbert_vecs=return_colbert
        )

        # Return format
        if return_dense and not return_sparse and not return_colbert:
            # Return only dense embeddings
            result = embeddings['dense_vecs']
            if single_input:
                return result[0]
            return result
        else:
            # Return dict with multiple types
            if single_input:
                return {k: v[0] if isinstance(v, np.ndarray) else v for k, v in embeddings.items()}
            return embeddings

    def encode_queries(
        self,
        queries: Union[str, List[str]],
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Encode queries (optimized for retrieval).

        Args:
            queries: Query text(s)
            batch_size: Batch size

        Returns:
            Dense query embeddings
        """
        return self.encode(
            queries,
            batch_size=batch_size,
            return_dense=True,
            return_sparse=False,
            return_colbert=False
        )

    def encode_corpus(
        self,
        documents: List[str],
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Encode corpus documents (optimized for indexing).

        Args:
            documents: List of documents
            batch_size: Batch size

        Returns:
            Dense document embeddings
        """
        return self.encode(
            documents,
            batch_size=batch_size,
            return_dense=True,
            return_sparse=False,
            return_colbert=False
        )

    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        doc_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and documents.

        Args:
            query_embedding: Query embedding (768-dim)
            doc_embeddings: Document embeddings (N x 768)

        Returns:
            Similarity scores (N,)
        """
        # Normalize
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)

        # Cosine similarity
        similarities = np.dot(doc_norms, query_norm)

        return similarities


# Fallback: Sentence-Transformers embedder
class SentenceTransformerEmbedder:
    """
    Fallback embedder using sentence-transformers.

    Use when BGE-M3 is not available or for lighter-weight embedding.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu"
    ):
        """
        Initialize sentence-transformers embedder.

        Args:
            model_name: Model name
            device: Device to run on
        """
        self.model_name = model_name
        self.device = device
        self._model = None

    def _load_model(self):
        """Lazy load model."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=self.device)
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. Install with: "
                "pip install sentence-transformers"
            )

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32
    ) -> np.ndarray:
        """Encode texts to embeddings."""
        self._load_model()

        if isinstance(texts, str):
            texts = [texts]
            single_input = True
        else:
            single_input = False

        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True
        )

        if single_input:
            return embeddings[0]
        return embeddings

    def encode_queries(self, queries: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """Encode queries."""
        return self.encode(queries, batch_size)

    def encode_corpus(self, documents: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode corpus."""
        return self.encode(documents, batch_size)

    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        doc_embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity."""
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
        return np.dot(doc_norms, query_norm)


# Factory function
def get_embedder(
    model_type: str = "bge-m3",
    device: str = "cpu",
    **kwargs
) -> Union[BGE_M3_Embedder, SentenceTransformerEmbedder]:
    """
    Get embedder instance.

    Args:
        model_type: 'bge-m3' or 'sentence-transformers'
        device: Device to run on
        **kwargs: Additional arguments

    Returns:
        Embedder instance
    """
    if model_type == "bge-m3":
        return BGE_M3_Embedder(device=device, **kwargs)
    elif model_type == "sentence-transformers":
        return SentenceTransformerEmbedder(device=device, **kwargs)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


# Usage example
"""
from lyra_core.memory.embedders import get_embedder

# Initialize embedder
embedder = get_embedder("bge-m3", device="cpu")

# Encode query
query_emb = embedder.encode_queries("How do I implement authentication?")

# Encode documents
docs = ["Use JWT tokens", "Use OAuth 2.0", "Use session cookies"]
doc_embs = embedder.encode_corpus(docs)

# Compute similarities
similarities = embedder.compute_similarity(query_emb, doc_embs)
print(similarities)  # [0.85, 0.78, 0.65]
"""
