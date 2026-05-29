"""Tests for EmbeddingDeadEndRegistry — Phase 21 Architecture Upgrade Module 3/4."""
import math

from lyra_core.collective import (
    DeadEndEntry,
    EmbeddingDeadEndRegistry,
    TFIDFVectorizer,
)


class TestTFIDFVectorizer:
    def test_tokenize_simple(self):
        tokens = TFIDFVectorizer._tokenize("Hello World")
        assert tokens == ["hello", "world"]

    def test_tokenize_with_punctuation(self):
        tokens = TFIDFVectorizer._tokenize("machine-learning, deep/reinforcement")
        assert "machine" in tokens
        assert "learning" in tokens
        assert "deep" in tokens
        assert "reinforcement" in tokens

    def test_tokenize_mixed_case(self):
        tokens = TFIDFVectorizer._tokenize("Neural Network Architecture")
        assert tokens == ["neural", "network", "architecture"]

    def test_tokenize_numbers(self):
        tokens = TFIDFVectorizer._tokenize("test 123 abc")
        assert "test" in tokens
        assert "123" in tokens
        assert "abc" in tokens

    def test_fit_builds_vocabulary(self):
        vec = TFIDFVectorizer()
        vec.fit(["the cat sat on the mat", "the dog sat on the log"])
        assert vec.vocab_size > 0
        assert "cat" in vec._vocabulary
        assert "dog" in vec._vocabulary

    def test_transform_produces_vectors(self):
        vec = TFIDFVectorizer()
        docs = ["neural network training", "convolutional neural network"]
        vectors = vec.fit_transform(docs)
        assert len(vectors) == 2
        assert all(isinstance(v, list) for v in vectors)
        assert all(isinstance(x, float) for v in vectors for x in v)

    def test_transform_one(self):
        vec = TFIDFVectorizer()
        vec.fit(["alpha beta gamma", "delta epsilon alpha"])
        v = vec.transform_one("alpha beta")
        assert len(v) == vec.vocab_size

    def test_fit_transform_returns_correct_count(self):
        vec = TFIDFVectorizer()
        vectors = vec.fit_transform(["doc one", "doc two", "doc three"])
        assert len(vectors) == 3

    def test_cosine_similarity_identical(self):
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        sim = TFIDFVectorizer.cosine_similarity(a, b)
        assert math.isclose(sim, 1.0, rel_tol=1e-6)

    def test_cosine_similarity_orthogonal(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        sim = TFIDFVectorizer.cosine_similarity(a, b)
        assert math.isclose(sim, 0.0, abs_tol=1e-6)

    def test_cosine_similarity_opposite(self):
        a = [1.0, 2.0, 3.0]
        b = [-1.0, -2.0, -3.0]
        sim = TFIDFVectorizer.cosine_similarity(a, b)
        assert math.isclose(sim, -1.0, rel_tol=1e-6)

    def test_cosine_similarity_empty_vectors(self):
        assert TFIDFVectorizer.cosine_similarity([], []) == 0.0

    def test_cosine_similarity_zero_vector(self):
        sim = TFIDFVectorizer.cosine_similarity([0.0, 0.0], [1.0, 2.0])
        assert sim == 0.0

    def test_similar_docs_high_similarity(self):
        vec = TFIDFVectorizer()
        docs = [
            "transformer attention mechanism for language modeling",
            "self-attention mechanism for transformer language models",
            "convolutional neural networks for image classification",
        ]
        vec.fit(docs)
        v1 = vec.transform_one(docs[0])
        v2 = vec.transform_one(docs[1])
        v3 = vec.transform_one(docs[2])

        sim_similar = TFIDFVectorizer.cosine_similarity(v1, v2)
        sim_different = TFIDFVectorizer.cosine_similarity(v1, v3)
        assert sim_similar > sim_different


class TestEmbeddingDeadEndRegistry:
    def test_register_entry(self):
        reg = EmbeddingDeadEndRegistry()
        entry = DeadEndEntry(
            id="de-1",
            hypothesis="Transformer models fail on small datasets",
            approach="Test transformers on datasets < 1000 samples",
            failure_reason="Insufficient data leads to overfitting",
            discovered_by="agent-1",
            tags=["transformer", "small-data"],
        )
        reg.register(entry)
        assert reg.entry_count == 1

    def test_is_known_dead_end_exact_match(self):
        reg = EmbeddingDeadEndRegistry(similarity_threshold=0.3)
        reg.register(DeadEndEntry(
            id="de-1",
            hypothesis="Using BERT for short text classification without fine-tuning",
            approach="Direct BERT embeddings + logistic regression",
            failure_reason="BERT embeddings too generic without task-specific tuning",
            discovered_by="agent-1",
            tags=["bert", "classification", "short-text"],
        ))

        is_dead, match = reg.is_known_dead_end(
            hypothesis="Using BERT for short text classification without fine-tuning",
        )
        assert is_dead
        assert match is not None
        assert match.id == "de-1"

    def test_is_known_dead_end_semantic_similar(self):
        reg = EmbeddingDeadEndRegistry(similarity_threshold=0.2)
        reg.register(DeadEndEntry(
            id="de-1",
            hypothesis="Reinforcement learning for robotic grasping fails without simulation",
            approach="Train RL policy from scratch on real robot",
            failure_reason="Too many real-world trials needed, damage risk",
            discovered_by="agent-2",
            tags=["rl", "robotics", "grasping"],
        ))
        reg.register(DeadEndEntry(
            id="de-2",
            hypothesis="ImageNet pre-training helps medical imaging classification",
            approach="Fine-tune ResNet on chest X-rays",
            failure_reason="Works well — not a dead end",
            discovered_by="agent-3",
            tags=["imagenet", "medical", "classification"],
        ))

        is_dead, match = reg.is_known_dead_end(
            hypothesis="Using reinforcement learning for robot grasping tasks in real world",
            threshold=0.2,
        )
        assert is_dead
        assert match is not None

    def test_is_known_dead_end_no_match(self):
        reg = EmbeddingDeadEndRegistry(similarity_threshold=0.7)
        reg.register(DeadEndEntry(
            id="de-1",
            hypothesis="Dead end about topic A",
            approach="Approach A",
            failure_reason="Failed",
            discovered_by="agent-1",
        ))

        is_dead, match = reg.is_known_dead_end(
            hypothesis="Completely different topic about quantum computing and cryptography",
            threshold=0.7,
        )
        assert not is_dead

    def test_query_similar(self):
        reg = EmbeddingDeadEndRegistry(similarity_threshold=0.7)
        reg.register(DeadEndEntry(
            id="de-1",
            hypothesis="GNN fail on heterophilic graphs",
            approach="Standard GCN on heterophilic graphs",
            failure_reason="GCN assumes homophily",
            discovered_by="agent-1",
            tags=["gnn", "graphs"],
        ))
        reg.register(DeadEndEntry(
            id="de-2",
            hypothesis="Transformer attention patterns for NLP",
            approach="Self-attention analysis on text",
            failure_reason="Works fine",
            discovered_by="agent-2",
            tags=["transformer", "nlp"],
        ))

        results = reg.query_similar("graph neural networks on heterophilic data", top_k=3)
        assert len(results) >= 1
        assert results[0].id == "de-1"

    def test_fallback_to_keyword_with_small_vocab(self):
        reg = EmbeddingDeadEndRegistry(similarity_threshold=0.3)
        reg.register(DeadEndEntry(
            id="de-1",
            hypothesis="test alpha",
            approach="test approach",
            failure_reason="nope",
            discovered_by="agent-1",
        ))
        reg._vectorizer = TFIDFVectorizer()

        is_dead, match = reg.is_known_dead_end("test alpha")
        assert is_dead

    def test_empty_registry(self):
        reg = EmbeddingDeadEndRegistry()
        is_dead, match = reg.is_known_dead_end("anything")
        assert not is_dead
        assert match is None
        assert reg.query_similar("anything") == []

    def test_multiple_entries_ranking(self):
        reg = EmbeddingDeadEndRegistry(similarity_threshold=0.1)
        reg.register(DeadEndEntry(
            id="de-relevant",
            hypothesis="Transformer attention analysis for NLP tasks",
            approach="Analyze attention heads in transformer models",
            failure_reason="Useful but computationally expensive",
            discovered_by="agent-1",
            tags=["transformer", "attention", "nlp"],
        ))
        reg.register(DeadEndEntry(
            id="de-unrelated",
            hypothesis="Convolutional neural networks for image segmentation",
            approach="U-Net architecture with ResNet backbone",
            failure_reason="Overfitting on small medical datasets",
            discovered_by="agent-2",
            tags=["cnn", "segmentation", "medical"],
        ))

        results = reg.query_similar("transformer attention mechanisms in NLP", top_k=2)
        assert results[0].id == "de-relevant"

    def test_inherits_keyword_registry_methods(self):
        reg = EmbeddingDeadEndRegistry()
        entry = DeadEndEntry(
            id="de-1",
            hypothesis="test",
            approach="test",
            failure_reason="test",
            discovered_by="agent-1",
        )
        reg.register(entry)
        assert reg.entry_count == 1

    def test_embedding_dim_grows_with_vocab(self):
        reg = EmbeddingDeadEndRegistry(similarity_threshold=0.1)
        initial = reg.embedding_dim
        reg.register(DeadEndEntry(
            id="de-1",
            hypothesis="unique terminology for testing vocabulary expansion",
            approach="novel method with distinctive keywords",
            failure_reason="does not work",
            discovered_by="agent-1",
            tags=["experimental"],
        ))
        assert reg.embedding_dim >= initial


class TestEmbeddingDeadEndRegistrySerialization:
    def test_to_dict_and_from_dict(self):
        reg = EmbeddingDeadEndRegistry(similarity_threshold=0.6)
        reg.register(DeadEndEntry(
            id="de-1",
            hypothesis="Test hypothesis",
            approach="Test approach",
            failure_reason="It failed",
            discovered_by="agent-1",
            tags=["test"],
        ))
        reg.register(DeadEndEntry(
            id="de-2",
            hypothesis="Another hypothesis",
            approach="Another approach",
            failure_reason="Also failed",
            discovered_by="agent-2",
            severity="severe",
        ))

        data = reg.to_dict()
        restored = EmbeddingDeadEndRegistry.from_dict(data)

        assert restored.entry_count == 2
        assert restored._similarity_threshold == 0.6

        is_dead, match = restored.is_known_dead_end(
            "Test hypothesis", "Test approach", threshold=0.3
        )
        assert is_dead
        assert match is not None
        assert match.id == "de-1"

    def test_from_dict_empty(self):
        reg = EmbeddingDeadEndRegistry.from_dict({})
        assert reg.entry_count == 0
        assert reg._similarity_threshold == 0.7


class TestEmbeddingDeadEndRegistryIntegration:
    def test_with_collective_state_pattern(self):
        """Verify EmbeddingDeadEndRegistry can replace DeadEndRegistry."""
        from lyra_core.collective import (
            CollectiveState,
            DeadEndEntry,
            Hypothesis,
        )

        state = CollectiveState()
        state.dead_ends = EmbeddingDeadEndRegistry(similarity_threshold=0.3)

        state.dead_ends.register(DeadEndEntry(
            id="de-integration",
            hypothesis="Gradient boosting fails on high-dimensional sparse data",
            approach="XGBoost on one-hot encoded categorical features",
            failure_reason="Memory explosion with thousands of sparse features",
            discovered_by="agent-42",
            tags=["gbm", "sparse", "high-dim"],
        ))

        hyp = Hypothesis(
            id="hyp-1",
            statement="Gradient boosting for high-dimensional sparse features",
            proposed_by="scientist-1",
            test_criteria="Measure memory usage and accuracy on 10K features",
        )

        result = state.propose_hypothesis(hyp, champion_id="scientist-1")
        assert result is None
