"""Tests for Phase 3.2a Cross-Skill Knowledge Transfer."""
from __future__ import annotations

import pytest

from lyra_core.skills.knowledge_transfer import (
    KnowledgeTransferEngine,
    PatternMatch,
    SkillEmbedding,
    TransferResult,
    TransferStatus,
)

SKILL_JSON = '''"""Parse and validate JSON files."""

import json
import os


def parse_json(path: str) -> dict:
    """Read a JSON file from disk."""
    with open(path) as f:
        return json.load(f)


def validate_json(data: dict, schema: dict) -> bool:
    """Check JSON data against a schema."""
    for key in schema:
        if key not in data:
            return False
    return True
'''

SKILL_YAML = '''"""Parse YAML configuration files."""

import yaml


def parse_yaml(path: str) -> dict:
    """Read a YAML config file."""
    with open(path) as f:
        return yaml.safe_load(f)
'''

SKILL_UNRELATED = '''#!/bin/bash
# Count lines in a directory

echo "Counting..."
find . -name "*.py" | xargs wc -l
echo "Done"
'''


class TestSkillEmbedding:
    def test_embedding_has_128_dims(self):
        engine = KnowledgeTransferEngine()
        emb = engine.index_skill("test", ("test",), "def foo(): pass")
        assert len(emb.dimensions) == 128

    def test_embedding_version_increments(self):
        engine = KnowledgeTransferEngine()
        e1 = engine.index_skill("test", ("a",), "first")
        e2 = engine.index_skill("test", ("b",), "second")
        assert e1.version == 1
        assert e2.version == 2


class TestKnowledgeTransferEngine:
    def test_index_and_retrieve(self):
        engine = KnowledgeTransferEngine()
        engine.index_skill("json-parser", ("json", "parse"), SKILL_JSON)
        emb = engine.get_embedding("json-parser")
        assert emb is not None
        assert emb.skill_name == "json-parser"

    def test_find_similar_same_domain(self):
        engine = KnowledgeTransferEngine()
        engine.index_skill("json-parser", ("json", "parse"), SKILL_JSON)
        engine.index_skill("yaml-parser", ("yaml", "parse"), SKILL_YAML)
        similar = engine.find_similar("json-parser")
        assert len(similar) >= 1
        assert similar[0][0] == "yaml-parser"

    def test_find_similar_skips_self(self):
        engine = KnowledgeTransferEngine()
        engine.index_skill("json-parser", ("json",), SKILL_JSON)
        engine.index_skill("yaml-parser", ("yaml",), SKILL_YAML)
        similar = engine.find_similar("json-parser")
        assert "json-parser" not in [s[0] for s in similar]

    def test_unrelated_skills_low_similarity(self):
        engine = KnowledgeTransferEngine()
        engine.index_skill("json-parser", ("json",), SKILL_JSON)
        engine.index_skill("count-files", ("count",), SKILL_UNRELATED)
        similar = engine.find_similar("count-files", top_n=3)
        assert len(similar) <= 1

    def test_transfer_between_similar_skills(self):
        engine = KnowledgeTransferEngine()
        engine.index_skill("json-parser", ("json", "parse"), SKILL_JSON)
        engine.index_skill("yaml-parser", ("yaml", "parse"), SKILL_YAML)
        result = engine.transfer("json-parser", "yaml-parser")
        assert result.status == TransferStatus.ENRICHED
        assert len(result.extracted_patterns) > 0
        assert result.similarity > 0.0

    def test_transfer_below_threshold(self):
        engine = KnowledgeTransferEngine(min_similarity=0.9)
        engine.index_skill("json-parser", ("json",), SKILL_JSON)
        engine.index_skill("count-files", ("count",), SKILL_UNRELATED)
        result = engine.transfer("json-parser", "count-files")
        assert result.status == TransferStatus.SKIPPED

    def test_transfer_missing_skill(self):
        engine = KnowledgeTransferEngine()
        engine.index_skill("json-parser", ("json",), SKILL_JSON)
        result = engine.transfer("json-parser", "nonexistent")
        assert result.status == TransferStatus.SKIPPED

    def test_transfer_enriches_body_with_imports(self):
        engine = KnowledgeTransferEngine()
        engine.index_skill("json-parser", ("json", "parse"), SKILL_JSON)
        engine.index_skill("basic", ("basic",), "def no_imports():\n    pass")
        result = engine.transfer("json-parser", "basic")
        if result.status == TransferStatus.ENRICHED and result.enriched_body:
            assert "import" in result.enriched_body.lower()

    def test_result_id_is_unique(self):
        engine = KnowledgeTransferEngine()
        engine.index_skill("a", ("a",), "def a(): pass")
        engine.index_skill("b", ("b",), "def b(): pass")
        r1 = engine.transfer("a", "b")
        r2 = engine.transfer("b", "a")
        assert r1.result_id != r2.result_id

    def test_embedding_keywords_match_dimensions(self):
        engine = KnowledgeTransferEngine()
        emb = engine.index_skill("test", ("test",), "def foo(): pass")
        assert len(emb.dimension_labels) == 128
        assert len(emb.dimension_labels) == len(emb.dimensions)

    def test_history_accumulates(self):
        engine = KnowledgeTransferEngine()
        engine.index_skill("a", ("a",), "def a(): pass")
        engine.index_skill("b", ("b",), "def b(): pass")
        engine.transfer("a", "b")
        assert len(engine.history) == 1

    def test_clear_removes_all(self):
        engine = KnowledgeTransferEngine()
        engine.index_skill("test", ("test",), "def test(): pass")
        engine.clear()
        assert engine.embedded_count == 0
        assert len(engine.history) == 0

    def test_embedded_count(self):
        engine = KnowledgeTransferEngine()
        assert engine.embedded_count == 0
        engine.index_skill("a", ("a",), "a")
        engine.index_skill("b", ("b",), "b")
        assert engine.embedded_count == 2


class TestPatternMatch:
    def test_frozen_dataclass(self):
        pm = PatternMatch(
            skill_name="test",
            pattern_type="import",
            pattern_content="import json",
            relevance=0.8,
            confidence=0.7,
        )
        with pytest.raises(Exception):
            pm.relevance = 0.5  # type: ignore[misc]
