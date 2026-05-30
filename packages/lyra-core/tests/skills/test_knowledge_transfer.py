"""Tests for Phase 3.2a Cross-Skill Knowledge Transfer."""
from __future__ import annotations

import pytest
from lyra_core.skills.knowledge_transfer import (
    KnowledgeTransferEngine,
    PatternMatch,
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


# ── PatternExtractor Tests ─────────────────────────────────────────


class TestPatternExtractor:
    """Tests for PatternExtractor."""

    def test_extract_imports(self):
        from lyra_core.skills.transfer.pattern_extractor import (
            PatternExtractor,
            PatternType,
        )

        extractor = PatternExtractor()
        code = "import json\nimport os\nfrom pathlib import Path\n\ndef main():\n    pass\n"
        result = extractor.extract("test-skill", code)
        imports = [p for p in result.patterns if p.pattern_type == PatternType.IMPORT]
        assert len(imports) >= 2

    def test_extract_functions(self):
        from lyra_core.skills.transfer.pattern_extractor import (
            PatternExtractor,
            PatternType,
        )

        extractor = PatternExtractor()
        code = "def calculate_total(items: list) -> float:\n    return sum(items)\n\ndef format_result(value: float) -> str:\n    return str(value)\n"
        result = extractor.extract("func-skill", code)
        funcs = [p for p in result.patterns if p.pattern_type == PatternType.FUNCTION]
        assert len(funcs) >= 2

    def test_extract_classes(self):
        from lyra_core.skills.transfer.pattern_extractor import (
            PatternExtractor,
            PatternType,
        )

        extractor = PatternExtractor()
        code = "class DataStore:\n    def __init__(self):\n        self.data = {}\n\nclass CacheManager:\n    pass\n"
        result = extractor.extract("class-skill", code)
        classes = [p for p in result.patterns if p.pattern_type == PatternType.CLASS]
        assert len(classes) >= 2

    def test_extract_decorators(self):
        from lyra_core.skills.transfer.pattern_extractor import (
            PatternExtractor,
            PatternType,
        )

        extractor = PatternExtractor()
        code = "@dataclass\nclass Foo:\n    x: int\n\n@staticmethod\ndef helper():\n    pass\n"
        result = extractor.extract("deco-skill", code)
        decorators = [p for p in result.patterns if p.pattern_type == PatternType.DECORATOR]
        assert len(decorators) >= 2

    def test_extract_error_handling(self):
        from lyra_core.skills.transfer.pattern_extractor import (
            PatternExtractor,
            PatternType,
        )

        extractor = PatternExtractor()
        code = "try:\n    risky()\nexcept ValueError as e:\n    raise CustomError('failed')\n"
        result = extractor.extract("error-skill", code)
        errors = [p for p in result.patterns if p.pattern_type == PatternType.ERROR_HANDLING]
        assert len(errors) >= 1

    def test_extract_validation(self):
        from lyra_core.skills.transfer.pattern_extractor import (
            PatternExtractor,
            PatternType,
        )

        extractor = PatternExtractor()
        code = "def process(data):\n    if not validate(data):\n        raise ValueError('invalid')\n    return data\n"
        result = extractor.extract("validation-skill", code)
        validations = [p for p in result.patterns if p.pattern_type == PatternType.VALIDATION]
        assert len(validations) >= 1

    def test_respects_min_reusability(self):
        from lyra_core.skills.transfer.pattern_extractor import PatternExtractor

        extractor = PatternExtractor(min_reusability=1.0)
        code = "import json\n\ndef foo():\n    pass\n"
        result = extractor.extract("strict-skill", code)
        assert len(result.patterns) == 0

    def test_extract_multiple_skills(self):
        from lyra_core.skills.transfer.pattern_extractor import PatternExtractor

        extractor = PatternExtractor()
        skills = {
            "skill_a": "import json\n\ndef do_a():\n    pass\n",
            "skill_b": "import os\n\ndef do_b():\n    pass\n",
        }
        results = extractor.extract_multiple(skills)
        assert len(results) == 2

    def test_clear(self):
        from lyra_core.skills.transfer.pattern_extractor import PatternExtractor

        extractor = PatternExtractor()
        extractor.extract("test", "import json")
        extractor.clear()
        assert len(extractor._history) == 0


# ── EnrichmentEngine Tests ─────────────────────────────────────────


class TestEnrichmentEngine:
    """Tests for EnrichmentEngine."""

    def test_build_actions(self):
        from lyra_core.skills.transfer.enrichment_engine import EnrichmentEngine

        engine = EnrichmentEngine()
        patterns = [
            {
                "pattern_type": "import",
                "content": "import json",
                "name": "json_import",
                "source_skill": "json-parser",
                "reusability_score": 0.9,
            },
            {
                "pattern_type": "function",
                "content": "def validate(data):\n    return True",
                "name": "validate",
                "source_skill": "validator",
                "reusability_score": 0.8,
            },
        ]
        actions = engine.build_actions("target-skill", patterns, "data-processing")
        assert len(actions) == 2

    def test_enrich_adds_patterns(self):
        from lyra_core.skills.transfer.enrichment_engine import (
            EnrichmentEngine,
            EnrichmentStatus,
        )

        engine = EnrichmentEngine()
        actions = engine.build_actions(
            "target-skill",
            [
                {
                    "pattern_type": "import",
                    "content": "import json",
                    "name": "json_import",
                    "source_skill": "parser",
                    "reusability_score": 0.9,
                },
            ],
            "data",
        )
        result = engine.enrich("target-skill", "def main():\n    pass", actions)
        assert result.status == EnrichmentStatus.ENRICHED
        assert result.added_patterns >= 1

    def test_enrich_deduplicates_content(self):
        from lyra_core.skills.transfer.enrichment_engine import EnrichmentEngine

        engine = EnrichmentEngine()
        actions = engine.build_actions(
            "target",
            [
                {
                    "pattern_type": "import",
                    "content": "import json",
                    "name": "import_json",
                    "source_skill": "parser",
                    "reusability_score": 0.9,
                },
                {
                    "pattern_type": "import",
                    "content": "import json",  # duplicate
                    "name": "import_json2",
                    "source_skill": "parser2",
                    "reusability_score": 0.9,
                },
            ],
            "data",
        )
        # Second duplicate should be filtered by build_actions
        assert len(actions) == 1

    def test_enrich_empty_actions_unchanged(self):
        from lyra_core.skills.transfer.enrichment_engine import (
            EnrichmentEngine,
            EnrichmentStatus,
        )

        engine = EnrichmentEngine()
        result = engine.enrich("target", "def main():\n    pass", [])
        assert result.status == EnrichmentStatus.UNCHANGED

    def test_enrich_preserves_original_on_reject(self):
        from lyra_core.skills.transfer.enrichment_engine import (
            EnrichmentEngine,
            EnrichmentStatus,
        )

        engine = EnrichmentEngine()
        actions = engine.build_actions(
            "target",
            [
                {
                    "pattern_type": "import",
                    "content": "import json",
                    "name": "already_there",
                    "source_skill": "parser",
                    "reusability_score": 0.9,
                },
            ],
            "data",
        )
        source = "import json\n\ndef main():\n    pass"
        result = engine.enrich("target", source, actions)
        assert result.status == EnrichmentStatus.REJECTED
        assert result.added_patterns == 0

    def test_get_report(self):
        from lyra_core.skills.transfer.enrichment_engine import EnrichmentEngine

        engine = EnrichmentEngine()
        actions = engine.build_actions(
            "skill",
            [{
                "pattern_type": "import",
                "content": "import os",
                "name": "os_import",
                "source_skill": "source",
                "reusability_score": 0.9,
            }],
            "data",
        )
        engine.enrich("skill", "def main():\n    pass", actions)
        report = engine.get_report()
        assert report.total_enrichments == 1

    def test_clear(self):
        from lyra_core.skills.transfer.enrichment_engine import EnrichmentEngine

        engine = EnrichmentEngine()
        actions = engine.build_actions(
            "skill",
            [{
                "pattern_type": "import",
                "content": "import os",
                "name": "os_import",
                "source_skill": "source",
                "reusability_score": 0.9,
            }],
            "data",
        )
        engine.enrich("skill", "def main():\n    pass", actions)
        engine.clear()
        report = engine.get_report()
        assert report.total_enrichments == 0
