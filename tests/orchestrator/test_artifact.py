"""Tests for the artifact module."""

import json
import tempfile
from pathlib import Path

import pytest

from lyra.orchestrator.artifact import (
    Artifact,
    CompressionLevel,
    compress_artifact,
    decompress_artifact,
)


class TestArtifact:
    """Tests for the Artifact dataclass."""

    def test_create_artifact(self) -> None:
        """Test creating an artifact with default values."""
        artifact = Artifact(task_id="t1", content="test content")
        assert artifact.task_id == "t1"
        assert artifact.content == "test content"
        assert artifact.summary == ""
        assert artifact.confidence == 1.0
        assert artifact.sources == []
        assert artifact.worker_id == ""

    def test_create_artifact_with_all_fields(self) -> None:
        """Test creating an artifact with all fields."""
        artifact = Artifact(
            task_id="t1",
            content="detailed content",
            summary="brief summary",
            confidence=0.85,
            sources=["https://example.com"],
            worker_id="w1",
            metadata={"key": "value"},
        )
        assert artifact.confidence == 0.85
        assert artifact.sources == ["https://example.com"]
        assert artifact.metadata == {"key": "value"}

    def test_confidence_validation(self) -> None:
        """Test confidence bounds validation."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            Artifact(task_id="t1", content="x", confidence=-0.1)

        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            Artifact(task_id="t1", content="x", confidence=1.5)

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        artifact = Artifact(
            task_id="t1", content="c", summary="s", confidence=0.9,
        )
        data = artifact.to_dict()
        assert data["task_id"] == "t1"
        assert data["content"] == "c"
        assert data["summary"] == "s"
        assert data["confidence"] == 0.9
        assert "created_at" in data

    def test_dict_roundtrip(self) -> None:
        """Test dictionary serialization roundtrip."""
        original = Artifact(
            task_id="t1", content="content", summary="summary",
            confidence=0.75, sources=["src1"],
        )
        data = original.to_dict()
        restored = Artifact.from_dict(data)
        assert restored.task_id == original.task_id
        assert restored.content == original.content
        assert restored.confidence == original.confidence
        assert restored.sources == original.sources

    def test_json_roundtrip(self) -> None:
        """Test JSON serialization roundtrip."""
        original = Artifact(
            task_id="t1", content="content", summary="summary",
            confidence=0.8, sources=["src1"],
        )
        payload = original.to_json()
        restored = Artifact.from_json(payload)
        assert restored.task_id == original.task_id
        assert restored.content == original.content
        assert restored.confidence == original.confidence

    def test_to_markdown_includes_fields(self) -> None:
        """Test markdown rendering includes key fields."""
        artifact = Artifact(
            task_id="t1", content="body", summary="sum",
            confidence=0.9, sources=["https://example.com"],
            worker_id="w1",
        )
        md = artifact.to_markdown()
        assert "t1" in md
        assert "body" in md
        assert "sum" in md
        assert "0.90" in md
        assert "w1" in md
        assert "example.com" in md

    def test_markdown_without_sources(self) -> None:
        """Test markdown rendering without sources section."""
        artifact = Artifact(task_id="t1", content="body", summary="sum")
        md = artifact.to_markdown()
        assert "Sources" not in md

    def test_write_json(self) -> None:
        """Test writing artifact to JSON file."""
        artifact = Artifact(task_id="t1", content="test")
        with tempfile.TemporaryDirectory() as tmp:
            path = artifact.write_json(Path(tmp) / "artifact.json")
            assert path.exists()
            loaded = json.loads(path.read_text())
            assert loaded["task_id"] == "t1"

    def test_write_markdown(self) -> None:
        """Test writing artifact to markdown file."""
        artifact = Artifact(task_id="t1", content="test content")
        with tempfile.TemporaryDirectory() as tmp:
            path = artifact.write_markdown(Path(tmp) / "artifact.md")
            assert path.exists()
            text = path.read_text()
            assert "t1" in text
            assert "test content" in text


class TestCompression:
    """Tests for artifact compression/decompression."""

    def test_compress_none(self) -> None:
        """Test NONE compression returns plain JSON."""
        artifact = Artifact(task_id="t1", content="hello")
        compressed = compress_artifact(artifact, CompressionLevel.NONE)
        data = json.loads(compressed)
        assert data["task_id"] == "t1"

    def test_compress_light_truncates_content(self) -> None:
        """Test LIGHT compression truncates content."""
        long_content = "A" * 500
        artifact = Artifact(task_id="t1", content=long_content)
        compressed = compress_artifact(artifact, CompressionLevel.LIGHT)
        data = json.loads(compressed)
        assert len(data["content"]) < len(long_content)
        assert data["content"].endswith("...")
        assert data["metadata"]["compression"] == "light"

    def test_compress_full_roundtrip(self) -> None:
        """Test FULL compression roundtrip."""
        artifact = Artifact(
            task_id="t1", content="hello world",
            summary="test summary", confidence=0.95,
            sources=["https://example.com"],
        )
        compressed = compress_artifact(artifact, CompressionLevel.FULL)
        assert isinstance(compressed, str)
        assert not compressed.startswith("{")  # not plain JSON

        restored = decompress_artifact(compressed)
        assert restored.task_id == artifact.task_id
        assert restored.content == artifact.content
        assert restored.confidence == artifact.confidence
        assert restored.sources == artifact.sources

    def test_decompress_fallback_json(self) -> None:
        """Test decompress falls back to plain JSON."""
        artifact = Artifact(task_id="t1", content="plain")
        payload = artifact.to_json()
        restored = decompress_artifact(payload)
        assert restored.task_id == "t1"

    def test_decompress_invalid_raises(self) -> None:
        """Test decompress raises on invalid payload."""
        with pytest.raises(ValueError, match="Cannot decompress"):
            decompress_artifact("not-a-valid-payload")
