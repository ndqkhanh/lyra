"""Tests for lyra-watermark package."""

import time
from typing import Any

import pytest

from lyra_watermark import (
    ContentType,
    ProvenanceChain,
    ProvenanceRecord,
    WatermarkConfig,
    WatermarkEngine,
    WatermarkMethod,
    WatermarkPayload,
    WatermarkResult,
)


# ---------------------------------------------------------------------------
# Data class instantiation
# ---------------------------------------------------------------------------


def test_watermark_method_enum() -> None:
    """Verify WatermarkMethod enum values."""
    assert WatermarkMethod.STATISTICAL.value == "STATISTICAL"
    assert WatermarkMethod.CRYPTOGRAPHIC.value == "CRYPTOGRAPHIC"
    assert WatermarkMethod.STEGANOGRAPHIC.value == "STEGANOGRAPHIC"
    assert WatermarkMethod.SEMANTIC.value == "SEMANTIC"


def test_content_type_enum() -> None:
    """Verify ContentType enum values."""
    assert ContentType.TEXT.value == "TEXT"
    assert ContentType.CODE.value == "CODE"
    assert ContentType.IMAGE.value == "IMAGE"
    assert ContentType.AUDIO.value == "AUDIO"
    assert ContentType.DATA.value == "DATA"


def test_watermark_payload_instantiation() -> None:
    """Test WatermarkPayload creation."""
    payload = WatermarkPayload(
        method="STATISTICAL",
        agent_id="agent-001",
        timestamp=1000.0,
        version="0.1.0",
        content_hash="abc123",
        signature="def456",
        metadata=(("key1", "val1"),),
    )
    assert payload.method == "STATISTICAL"
    assert payload.agent_id == "agent-001"
    assert payload.timestamp == 1000.0
    assert payload.content_hash == "abc123"
    assert payload.signature == "def456"
    assert payload.metadata == (("key1", "val1"),)


def test_watermark_payload_to_dict_roundtrip() -> None:
    """Test WatermarkPayload serialization round-trip."""
    payload = WatermarkPayload(
        method="CRYPTOGRAPHIC",
        agent_id="agent-002",
        timestamp=2000.0,
        version="0.1.0",
        content_hash="xyz789",
        signature="sig123",
        metadata=(("a", "1"), ("b", "2")),
    )
    data = payload.to_dict()
    restored = WatermarkPayload.from_dict(data)
    assert restored == payload


def test_watermark_result_instantiation() -> None:
    """Test WatermarkResult creation."""
    payload = WatermarkPayload(
        method="STATISTICAL",
        agent_id="agent-001",
        timestamp=1000.0,
        version="0.1.0",
        content_hash="abc",
        signature="def",
        metadata=(),
    )
    result = WatermarkResult(
        watermarked=True,
        payload=payload,
        detection_confidence=1.0,
        extraction_method="signature_verify",
        tampered=False,
    )
    assert result.watermarked is True
    assert result.payload is not None
    assert result.payload.method == "STATISTICAL"
    assert result.detection_confidence == 1.0
    assert result.tampered is False


def test_provenance_chain_instantiation() -> None:
    """Test ProvenanceChain creation."""
    payload = WatermarkPayload(
        method="STATISTICAL",
        agent_id="agent-001",
        timestamp=1000.0,
        version="0.1.0",
        content_hash="abc",
        signature="def",
        metadata=(),
    )
    chain = ProvenanceChain(
        content_id="content-001",
        origin_agent="agent-001",
        timestamp=1000.0,
        prior_watermarks=(),
        verification_status="verified",
        chain_length=1,
    )
    assert chain.content_id == "content-001"
    assert chain.origin_agent == "agent-001"
    assert chain.chain_length == 1


def test_provenance_record_instantiation() -> None:
    """Test ProvenanceRecord creation."""
    payload = WatermarkPayload(
        method="STATISTICAL",
        agent_id="agent-001",
        timestamp=1000.0,
        version="0.1.0",
        content_hash="abc",
        signature="def",
        metadata=(),
    )
    record = ProvenanceRecord(
        record_id="rec-001",
        content_hash="abc",
        watermark_payload=payload,
        creation_time=1000.0,
    )
    assert record.record_id == "rec-001"
    assert record.verified_count == 0


def test_watermark_config_defaults() -> None:
    """Test WatermarkConfig default values."""
    config = WatermarkConfig()
    assert config.default_method == "STATISTICAL"
    assert config.signature_key == "lyra-watermark-v1"
    assert config.min_confidence_threshold == 0.7
    assert config.tamper_detection_enabled is True
    assert config.provenance_tracking_enabled is True


def test_watermark_config_custom() -> None:
    """Test WatermarkConfig with custom values."""
    config = WatermarkConfig(
        default_method="CRYPTOGRAPHIC",
        signature_key="custom-key",
        min_confidence_threshold=0.9,
        tamper_detection_enabled=False,
        provenance_tracking_enabled=False,
    )
    assert config.default_method == "CRYPTOGRAPHIC"
    assert config.signature_key == "custom-key"


def test_all_data_classes_can_be_instantiated() -> None:
    """Verify all data classes can be created with minimal args."""
    payload = WatermarkPayload(
        method="TEST",
        agent_id="",
        timestamp=0.0,
        version="0.0.0",
        content_hash="",
        signature="",
        metadata=(),
    )
    _ = WatermarkResult(
        watermarked=False,
        payload=payload,
        detection_confidence=0.0,
        extraction_method="none",
    )
    _ = ProvenanceChain(
        content_id="",
        origin_agent="",
        timestamp=0.0,
        prior_watermarks=(),
        verification_status="",
        chain_length=0,
    )
    _ = ProvenanceRecord(
        record_id="",
        content_hash="",
        watermark_payload=payload,
        creation_time=0.0,
    )
    _ = WatermarkConfig()


# ---------------------------------------------------------------------------
# WatermarkEngine tests
# ---------------------------------------------------------------------------


def test_engine_init() -> None:
    """Test WatermarkEngine initialization with defaults."""
    engine = WatermarkEngine()
    assert engine.config.default_method == "STATISTICAL"
    assert engine.config.signature_key == "lyra-watermark-v1"


def test_engine_init_with_config() -> None:
    """Test WatermarkEngine initialization with custom config."""
    config = WatermarkConfig(default_method="CRYPTOGRAPHIC")
    engine = WatermarkEngine(config=config)
    assert engine.config.default_method == "CRYPTOGRAPHIC"


def test_embed_creates_valid_payload() -> None:
    """Test embed creates a WatermarkPayload with correct fields."""
    engine = WatermarkEngine()
    content = "Hello, Lyra! This is a test message."
    payload = engine.embed(content, agent_id="agent-001")

    assert isinstance(payload, WatermarkPayload)
    assert payload.agent_id == "agent-001"
    assert payload.method == "STATISTICAL"
    assert payload.version == "0.1.0"
    assert len(payload.content_hash) == 64  # SHA-256 hex digest
    assert len(payload.signature) == 32  # First 32 hex chars
    assert isinstance(payload.timestamp, float)
    assert payload.timestamp > 0
    assert payload.metadata == ()


def test_embed_with_metadata() -> None:
    """Test embed with metadata dict."""
    engine = WatermarkEngine()
    content = "Metadata test content."
    metadata = {"source": "test", "priority": "high"}
    payload = engine.embed(content, agent_id="agent-002", metadata=metadata)

    assert len(payload.metadata) == 2
    meta_dict = dict(payload.metadata)
    assert meta_dict["source"] == "test"
    assert meta_dict["priority"] == "high"


def test_embed_with_content_type() -> None:
    """Test embed with a content type string."""
    engine = WatermarkEngine()
    content = "def foo(): pass"
    payload = engine.embed(content, content_type="CODE", agent_id="agent-003")

    assert payload.method == "STATISTICAL"
    # The content_type is accepted but we don't store it in the payload
    # (the watermark method is in the payload)


def test_detect_finds_embedded_watermark() -> None:
    """Test detect finds a watermark that was just embedded."""
    engine = WatermarkEngine()
    content = "Detectable content."
    payload = engine.embed(content, agent_id="agent-001")

    # Retrieve the watermarked content from the engine internals to detect
    watermarked = engine._watermarked_content[payload.content_hash]
    result = engine.detect(watermarked)

    assert result.watermarked is True
    assert result.payload is not None
    assert result.payload.content_hash == payload.content_hash
    assert result.detection_confidence == 1.0
    assert result.tampered is False


def test_detect_non_watermarked_content() -> None:
    """Test detect returns negative for plain content."""
    engine = WatermarkEngine()
    result = engine.detect("This is just plain content with no watermark.")

    assert result.watermarked is False
    assert result.payload is None
    assert result.detection_confidence == 0.0


def test_extract_recovers_embedded_payload() -> None:
    """Test extract recovers the payload from watermarked content."""
    engine = WatermarkEngine()
    content = "Extractable content."
    original_payload = engine.embed(content, agent_id="agent-010")

    watermarked = engine._watermarked_content[original_payload.content_hash]
    extracted = engine.extract(watermarked)

    assert extracted is not None
    assert extracted.content_hash == original_payload.content_hash
    assert extracted.agent_id == "agent-010"
    assert extracted.signature == original_payload.signature
    assert extracted.timestamp == original_payload.timestamp


def test_extract_non_watermarked_content() -> None:
    """Test extract returns None for plain content."""
    engine = WatermarkEngine()
    result = engine.extract("Plain content without watermark.")
    assert result is None


def test_verify_correct_agent() -> None:
    """Test verify returns True for the correct agent."""
    engine = WatermarkEngine()
    content = "Verify this content."
    payload = engine.embed(content, agent_id="agent-verify-1")
    watermarked = engine._watermarked_content[payload.content_hash]

    assert engine.verify(watermarked, expected_agent_id="agent-verify-1") is True


def test_verify_wrong_agent() -> None:
    """Test verify returns False for the wrong agent."""
    engine = WatermarkEngine()
    content = "Wrong agent test."
    payload = engine.embed(content, agent_id="agent-real")
    watermarked = engine._watermarked_content[payload.content_hash]

    assert engine.verify(watermarked, expected_agent_id="agent-impostor") is False


def test_verify_non_watermarked_content() -> None:
    """Test verify returns False for non-watermarked content."""
    engine = WatermarkEngine()
    assert engine.verify("No watermark here.", expected_agent_id="any-agent") is False


def test_detect_tampering_detects_modifications() -> None:
    """Test detect_tampering finds modifications in content."""
    engine = WatermarkEngine()
    original = "This is the original content."
    payload = engine.embed(original, agent_id="agent-001")
    watermarked = engine._watermarked_content[payload.content_hash]

    suspected = watermarked.replace("original", "modified")
    result = engine.detect_tampering(watermarked, suspected)

    assert result.tampered is True
    assert result.detection_confidence == 0.0


def test_detect_tampering_no_change() -> None:
    """Test detect_tampering passes when content is unchanged."""
    engine = WatermarkEngine()
    content = "Unchanged content for tamper test."
    payload = engine.embed(content, agent_id="agent-001")
    watermarked = engine._watermarked_content[payload.content_hash]

    result = engine.detect_tampering(watermarked, watermarked)

    assert result.tampered is False
    assert result.detection_confidence == 1.0


def test_build_provenance_chain() -> None:
    """Test building a provenance chain from multiple watermarks."""
    engine = WatermarkEngine()

    payloads = []
    for i in range(3):
        content = f"Chain link {i}"
        payload = engine.embed(content, agent_id=f"agent-{i}")
        payloads.append(payload)

    chain = engine.build_provenance_chain(content_id="chain-001", watermarks=payloads)

    assert isinstance(chain, ProvenanceChain)
    assert chain.content_id == "chain-001"
    assert chain.origin_agent == "agent-2"  # Most recent
    assert chain.chain_length == 3
    assert len(chain.prior_watermarks) == 2


def test_build_provenance_chain_single() -> None:
    """Test building a provenance chain with a single watermark."""
    engine = WatermarkEngine()
    payload = engine.embed("Single content", agent_id="agent-solo")
    chain = engine.build_provenance_chain(content_id="solo", watermarks=[payload])

    assert chain.chain_length == 1
    assert chain.prior_watermarks == ()


def test_register_content_and_verify_provenance() -> None:
    """Test register_content and verify_provenance round-trip."""
    engine = WatermarkEngine()
    content = "Registered content for provenance."
    record = engine.register_content(content, agent_id="agent-provenance")

    assert isinstance(record, ProvenanceRecord)
    assert record.content_hash is not None
    assert record.verified_count == 0
    assert record.watermark_payload.agent_id == "agent-provenance"

    # Verify the provenance record
    watermarked = engine._watermarked_content[record.content_hash]
    assert engine.verify_provenance(watermarked, record) is True


def test_verify_provenance_wrong_content() -> None:
    """Test verify_provenance fails with modified content."""
    engine = WatermarkEngine()
    content = "Original provenance content."
    record = engine.register_content(content, agent_id="agent-p")

    # Verify with different content
    assert engine.verify_provenance("Tampered content.", record) is False


def test_provenance_record_is_frozen() -> None:
    """Test that ProvenanceRecord instances are immutable."""
    engine = WatermarkEngine()
    content = "Frozen record test."
    payload = engine.embed(content, agent_id="agent-frozen")
    record = ProvenanceRecord(
        record_id="test-frozen",
        content_hash=payload.content_hash,
        watermark_payload=payload,
        creation_time=payload.timestamp,
    )
    with pytest.raises(AttributeError):
        record.record_id = "changed"  # type: ignore[misc]


def test_get_stats() -> None:
    """Test engine statistics after various operations."""
    engine = WatermarkEngine()

    stats = engine.get_stats()
    assert stats["total_watermarked"] == 0
    assert stats["total_verified"] == 0
    assert stats["total_tampered"] == 0
    assert stats["registered_records"] == 0

    # Embed content
    content = "Stats test content."
    payload = engine.embed(content, agent_id="agent-stats")
    stats = engine.get_stats()
    assert stats["total_watermarked"] == 1

    # Verify
    watermarked = engine._watermarked_content[payload.content_hash]
    engine.verify(watermarked, expected_agent_id="agent-stats")
    stats = engine.get_stats()
    assert stats["total_verified"] == 1

    # Register
    engine.register_content("Another registration.", agent_id="agent-reg")
    stats = engine.get_stats()
    assert stats["registered_records"] == 1

    # Tamper - modify the content body before the watermark tag
    tampered_content = watermarked.replace("Stats test", "Hacked test")
    engine.detect_tampering(watermarked, tampered_content)
    stats = engine.get_stats()
    assert stats["total_tampered"] == 1


def test_roundtrip_invariant() -> None:
    """Test that embed then detect gives a consistent result."""
    engine = WatermarkEngine()
    content = "Round-trip invariant test content."
    payload = engine.embed(content, agent_id="agent-rt")

    watermarked = engine._watermarked_content[payload.content_hash]
    result = engine.detect(watermarked)

    assert result.watermarked is True
    assert result.payload is not None
    assert result.payload.content_hash == payload.content_hash
    assert result.payload.agent_id == "agent-rt"

    # Verify the content hash is SHA-256 of the original content
    expected_hash = __import__("hashlib").sha256(content.encode()).hexdigest()
    assert payload.content_hash == expected_hash


def test_extract_after_detect_is_consistent() -> None:
    """Test that extract returns the same payload as detect."""
    engine = WatermarkEngine()
    content = "Consistency check content."
    engine.embed(content, agent_id="agent-consistency")

    watermarked = list(engine._watermarked_content.values())[0]
    detect_result = engine.detect(watermarked)
    extracted = engine.extract(watermarked)

    assert extracted is not None
    assert detect_result.payload is not None
    assert extracted.content_hash == detect_result.payload.content_hash
    assert extracted.signature == detect_result.payload.signature
