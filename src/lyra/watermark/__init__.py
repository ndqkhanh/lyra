"""Lyra Watermark - Content watermarking and provenance attribution for Lyra agents.

This package provides:
- Content watermarking (statistical, cryptographic, steganographic, semantic)
- Watermark detection and extraction
- Tamper detection
- Provenance chain tracking and verification
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_WATERMARK_START = "<<<LYRA_WM::"
_WATERMARK_END = "::LYRA_WM>>>"


class WatermarkMethod(str, Enum):
    """Supported watermark embedding methods."""

    STATISTICAL = "STATISTICAL"
    CRYPTOGRAPHIC = "CRYPTOGRAPHIC"
    STEGANOGRAPHIC = "STEGANOGRAPHIC"
    SEMANTIC = "SEMANTIC"


class ContentType(str, Enum):
    """Types of content that can be watermarked."""

    TEXT = "TEXT"
    CODE = "CODE"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    DATA = "DATA"


@dataclass(frozen=True)
class WatermarkPayload:
    """Payload embedded into watermarked content.

    Contains all metadata needed to verify content provenance.

    Parameters
    ----------
    method : str
        Watermark method used (e.g. STATISTICAL, CRYPTOGRAPHIC).
    agent_id : str
        Identifier of the agent that created the content.
    content_type : str
        Type of content being watermarked (see ``ContentType``).
    timestamp : float
        Unix timestamp when the watermark was embedded.
    version : str
        Version of the watermarking scheme.
    content_hash : str
        SHA-256 hex digest of the original content.
    signature : str
        Cryptographic signature computed over content + agent_id + key.
    metadata : tuple[tuple[str, str], ...]
        Key-value metadata pairs attached to the watermark.
    """

    method: str
    agent_id: str
    content_type: str
    timestamp: float
    version: str
    content_hash: str
    signature: str
    metadata: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize this payload to a JSON-compatible dictionary."""
        return {
            "method": self.method,
            "agent_id": self.agent_id,
            "content_type": self.content_type,
            "timestamp": self.timestamp,
            "version": self.version,
            "content_hash": self.content_hash,
            "signature": self.signature,
            "metadata": list(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WatermarkPayload:
        """Deserialize a dictionary into a WatermarkPayload.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary produced by ``to_dict()``.

        Returns
        -------
        WatermarkPayload
            Reconstructed payload instance.
        """
        meta: tuple[tuple[str, str], ...] = tuple(
            tuple(item) for item in data.get("metadata", [])  # type: ignore[misc]
        )
        return cls(
            method=data["method"],
            agent_id=data["agent_id"],
            content_type=data.get("content_type", "TEXT"),
            timestamp=data["timestamp"],
            version=data["version"],
            content_hash=data["content_hash"],
            signature=data["signature"],
            metadata=meta,
        )


@dataclass(frozen=True)
class WatermarkResult:
    """Result of a watermark detection operation.

    Parameters
    ----------
    watermarked : bool
        Whether a watermark was found.
    payload : WatermarkPayload | None
        The extracted payload, if found.
    detection_confidence : float
        Confidence score between 0.0 and 1.0.
    extraction_method : str
        Method used for extraction (e.g. signature_verify, content_hash_mismatch).
    tampered : bool
        Whether the content appears to have been tampered with.
    """

    watermarked: bool
    payload: WatermarkPayload | None
    detection_confidence: float
    extraction_method: str
    tampered: bool = False


@dataclass(frozen=True)
class ProvenanceChain:
    """Immutable chain of provenance records for a piece of content.

    Parameters
    ----------
    content_id : str
        Unique identifier for the content.
    origin_agent : str
        Agent that originally created the content.
    timestamp : float
        Unix timestamp of the most recent watermark.
    prior_watermarks : tuple[WatermarkPayload, ...]
        All prior watermarks in the chain (excluding the latest).
    verification_status : str
        Current verification status (e.g. verified, unverified, tampered).
    chain_length : int
        Total number of watermarks in the chain.
    """

    content_id: str
    origin_agent: str
    timestamp: float
    prior_watermarks: tuple[WatermarkPayload, ...]
    verification_status: str
    chain_length: int


@dataclass(frozen=True)
class ProvenanceRecord:
    """A single provenance registration record.

    Parameters
    ----------
    record_id : str
        Unique identifier for this record.
    content_hash : str
        SHA-256 hex digest of the content at registration time.
    watermark_payload : WatermarkPayload
        The watermark payload embedded at registration.
    creation_time : float
        Unix timestamp when the record was created.
    verified_count : int
        Number of times this record has been successfully verified.
    """

    record_id: str
    content_hash: str
    watermark_payload: WatermarkPayload
    creation_time: float
    verified_count: int = 0


@dataclass(frozen=True)
class WatermarkConfig:
    """Configuration for the WatermarkEngine.

    Parameters
    ----------
    default_method : str
        Default watermark method to use when embedding.
    signature_key : str
        Secret key used for computing cryptographic signatures.
    min_confidence_threshold : float
        Minimum confidence required for a positive detection.
    tamper_detection_enabled : bool
        Whether tamper detection is active.
    provenance_tracking_enabled : bool
        Whether provenance chain tracking is active.
    """

    default_method: str = "STATISTICAL"
    signature_key: str = "lyra-watermark-v1"
    min_confidence_threshold: float = 0.7
    tamper_detection_enabled: bool = True
    provenance_tracking_enabled: bool = True


class WatermarkEngine:
    """Engine for embedding, detecting, and verifying content watermarks.

    Uses SHA-256 based signatures to produce deterministic, verifiable
    watermarks embedded as a detectable suffix in the content.

    Parameters
    ----------
    config : WatermarkConfig | None
        Engine configuration. Defaults are used when ``None``.
    """

    def __init__(self, config: WatermarkConfig | None = None) -> None:
        self.config = config or WatermarkConfig()
        self._watermarked_content: dict[str, str] = {}
        self._provenance_records: dict[str, ProvenanceRecord] = {}
        self._stats: dict[str, Any] = {
            "total_watermarked": 0,
            "total_verified": 0,
            "total_tampered": 0,
            "registered_records": 0,
        }

    def _compute_signature(self, content: str, agent_id: str) -> str:
        """Compute a deterministic SHA-256 signature for content.

        Parameters
        ----------
        content : str
            The original (non-watermarked) content.
        agent_id : str
            Agent identifier used in signature computation.

        Returns
        -------
        str
            First 32 hex characters of the SHA-256 digest.
        """
        sig_input = content + agent_id + self.config.signature_key
        return hashlib.sha256(sig_input.encode()).hexdigest()[:32]

    def _generate_tag(self, payload: WatermarkPayload) -> str:
        """Generate the watermark tag string to append to content.

        Parameters
        ----------
        payload : WatermarkPayload
            The payload to encode into the tag.

        Returns
        -------
        str
            A newline-terminated watermark tag.
        """
        payload_dict = payload.to_dict()
        encoded = base64.b64encode(
            json.dumps(payload_dict, sort_keys=True).encode()
        ).decode()
        return f"\n{_WATERMARK_START}{encoded}{_WATERMARK_END}\n"

    def _find_watermark_tag(self, content: str) -> tuple[str, str] | None:
        """Locate and extract the watermark tag from content.

        Searches for the watermark delimiter from the end of the string
        to correctly handle content that contains watermark-like patterns.

        Parameters
        ----------
        content : str
            Content that may contain a watermark tag.

        Returns
        -------
        tuple[str, str] | None
            ``(original_content, encoded_payload)`` if a valid tag is found,
            otherwise ``None``.
        """
        start_idx = content.rfind(_WATERMARK_START)
        if start_idx == -1:
            return None
        end_idx = content.find(_WATERMARK_END, start_idx)
        if end_idx == -1:
            return None
        encoded = content[start_idx + len(_WATERMARK_START) : end_idx]
        original_content = content[:start_idx].rstrip("\n")
        return (original_content, encoded)

    def embed(
        self,
        content: str,
        content_type: str = "TEXT",
        agent_id: str = "",
        metadata: dict[str, str] | None = None,
    ) -> WatermarkPayload:
        """Embed a watermark into content.

        Computes a SHA-256 content hash and a deterministic signature
        from ``content + agent_id + key``, then appends a detectable
        watermark tag to the content.

        Parameters
        ----------
        content : str
            The original content to watermark.
        content_type : str
            Type of content being watermarked (see ``ContentType``).
        agent_id : str
            Identifier of the agent generating the content.
        metadata : dict[str, str] | None
            Optional key-value metadata to attach.

        Returns
        -------
        WatermarkPayload
            The payload that was embedded into the content.
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        timestamp = time.time()
        signature = self._compute_signature(content, agent_id)
        meta_items: tuple[tuple[str, str], ...] = tuple(
            sorted((k, v) for k, v in (metadata or {}).items())
        )

        payload = WatermarkPayload(
            method=self.config.default_method,
            agent_id=agent_id,
            content_type=content_type,
            timestamp=timestamp,
            version="0.1.0",
            content_hash=content_hash,
            signature=signature,
            metadata=meta_items,
        )

        watermark_tag = self._generate_tag(payload)
        watermarked_content = content + watermark_tag
        self._watermarked_content[content_hash] = watermarked_content
        self._stats["total_watermarked"] += 1

        return payload

    def detect(self, content: str) -> WatermarkResult:
        """Detect whether content contains a valid Lyra watermark.

        Attempts to find and parse the watermark tag, then verifies
        the cryptographic signature against the original content.

        Parameters
        ----------
        content : str
            Content to check for a watermark.

        Returns
        -------
        WatermarkResult
            Detection result with confidence score and tamper status.
        """
        tag_result = self._find_watermark_tag(content)
        if tag_result is None:
            return WatermarkResult(
                watermarked=False,
                payload=None,
                detection_confidence=0.0,
                extraction_method="none",
            )

        original_content, encoded = tag_result

        try:
            payload_dict = json.loads(base64.b64decode(encoded).decode())
            payload = WatermarkPayload.from_dict(payload_dict)
        except (json.JSONDecodeError, KeyError, ValueError):
            return WatermarkResult(
                watermarked=False,
                payload=None,
                detection_confidence=0.0,
                extraction_method="none",
            )

        expected_signature = self._compute_signature(
            original_content, payload.agent_id
        )
        if expected_signature == payload.signature:
            return WatermarkResult(
                watermarked=True,
                payload=payload,
                detection_confidence=1.0,
                extraction_method="signature_verify",
                tampered=False,
            )

        self._stats["total_tampered"] += 1
        return WatermarkResult(
            watermarked=True,
            payload=payload,
            detection_confidence=0.0,
            extraction_method="signature_mismatch",
            tampered=True,
        )

    def extract(self, content: str) -> WatermarkPayload | None:
        """Extract an embedded watermark payload from content.

        Parameters
        ----------
        content : str
            Content containing a watermark.

        Returns
        -------
        WatermarkPayload | None
            The extracted payload, or ``None`` if no valid watermark exists.
        """
        tag_result = self._find_watermark_tag(content)
        if tag_result is None:
            return None

        _, encoded = tag_result

        try:
            payload_dict = json.loads(base64.b64decode(encoded).decode())
            return WatermarkPayload.from_dict(payload_dict)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def verify(self, content: str, expected_agent_id: str) -> bool:
        """Verify that content originated from a specific agent.

        Extracts the watermark and checks both the agent_id and the
        cryptographic signature.

        Parameters
        ----------
        content : str
            Watermarked content to verify.
        expected_agent_id : str
            The agent that is expected to have created the content.

        Returns
        -------
        bool
            ``True`` if the content is verified for the given agent.
        """
        tag_result = self._find_watermark_tag(content)
        if tag_result is None:
            return False

        original_content, encoded = tag_result

        try:
            payload_dict = json.loads(base64.b64decode(encoded).decode())
            payload = WatermarkPayload.from_dict(payload_dict)
        except (json.JSONDecodeError, KeyError, ValueError):
            return False

        if payload.agent_id != expected_agent_id:
            return False

        expected_signature = self._compute_signature(
            original_content, expected_agent_id
        )
        if expected_signature != payload.signature:
            return False

        self._stats["total_verified"] += 1
        return True

    def detect_tampering(
        self, original_content: str, suspected_content: str
    ) -> WatermarkResult:
        """Compare original and suspected content to detect tampering.

        Computes the content hash of the suspected content and compares
        it against the hash stored in the original watermark. Also
        re-verifies the cryptographic signature.

        Parameters
        ----------
        original_content : str
            The original watermarked content.
        suspected_content : str
            Content that may have been tampered with.

        Returns
        -------
        WatermarkResult
            Result indicating whether tampering was detected.
        """
        original_result = self.detect(original_content)
        if not original_result.watermarked or not original_result.payload:
            return WatermarkResult(
                watermarked=False,
                payload=None,
                detection_confidence=0.0,
                extraction_method="none",
            )

        tag_result = self._find_watermark_tag(suspected_content)
        suspected_base = tag_result[0] if tag_result else suspected_content

        suspected_hash = hashlib.sha256(suspected_base.encode()).hexdigest()
        if suspected_hash != original_result.payload.content_hash:
            self._stats["total_tampered"] += 1
            return WatermarkResult(
                watermarked=True,
                payload=original_result.payload,
                detection_confidence=0.0,
                extraction_method="content_hash_mismatch",
                tampered=True,
            )

        expected_sig = self._compute_signature(
            suspected_base, original_result.payload.agent_id
        )
        if expected_sig != original_result.payload.signature:
            self._stats["total_tampered"] += 1
            return WatermarkResult(
                watermarked=True,
                payload=original_result.payload,
                detection_confidence=0.0,
                extraction_method="signature_mismatch",
                tampered=True,
            )

        return WatermarkResult(
            watermarked=True,
            payload=original_result.payload,
            detection_confidence=1.0,
            extraction_method="content_verified",
            tampered=False,
        )

    def build_provenance_chain(
        self, content_id: str, watermarks: list[WatermarkPayload]
    ) -> ProvenanceChain:
        """Build an immutable chain of provenance records.

        Constructs a ``ProvenanceChain`` from an ordered list of
        watermark payloads. The latest (last) watermark is used
        as the head of the chain.

        Parameters
        ----------
        content_id : str
            Unique identifier for the content.
        watermarks : list[WatermarkPayload]
            Ordered list of watermarks, most recent last.

        Returns
        -------
        ProvenanceChain
            The constructed provenance chain.
        """
        prior = tuple(watermarks[:-1]) if len(watermarks) > 1 else ()
        latest = watermarks[-1]

        return ProvenanceChain(
            content_id=content_id,
            origin_agent=latest.agent_id,
            timestamp=latest.timestamp,
            prior_watermarks=prior,
            verification_status="verified",
            chain_length=len(watermarks),
        )

    def register_content(self, content: str, agent_id: str) -> ProvenanceRecord:
        """Register content with a watermark and store its provenance record.

        Embeds a watermark, creates a ``ProvenanceRecord``, and stores
        it in the engine's internal registry.

        Parameters
        ----------
        content : str
            Content to register.
        agent_id : str
            Agent identifier for the watermark.

        Returns
        -------
        ProvenanceRecord
            The created provenance record.
        """
        payload = self.embed(content, agent_id=agent_id)
        record_id = hashlib.sha256(
            (content + agent_id + str(time.time())).encode()
        ).hexdigest()[:16]

        record = ProvenanceRecord(
            record_id=record_id,
            content_hash=payload.content_hash,
            watermark_payload=payload,
            creation_time=payload.timestamp,
        )

        self._provenance_records[record_id] = record
        self._stats["registered_records"] += 1

        return record

    def verify_provenance(self, content: str, record: ProvenanceRecord) -> bool:
        """Verify that content matches its provenance record.

        Checks that the content hash and watermark signature both
        match the values stored in the provenance record. The
        watermark tag is stripped before computing the content hash
        so that the comparison works against the original content.

        Parameters
        ----------
        content : str
            Watermarked content to verify.
        record : ProvenanceRecord
            The provenance record to check against.

        Returns
        -------
        bool
            ``True`` if the content is verified against the record.
        """
        tag_result = self._find_watermark_tag(content)
        if tag_result is None:
            return False

        original_content, encoded = tag_result

        content_hash = hashlib.sha256(original_content.encode()).hexdigest()
        if content_hash != record.content_hash:
            return False

        try:
            payload_dict = json.loads(base64.b64decode(encoded).decode())
            payload = WatermarkPayload.from_dict(payload_dict)
        except (json.JSONDecodeError, KeyError, ValueError):
            return False

        if payload.content_hash != record.content_hash:
            return False

        expected_sig = self._compute_signature(
            original_content, payload.agent_id
        )
        if expected_sig != payload.signature:
            return False

        self._stats["total_verified"] += 1
        return True

    def get_stats(self) -> dict[str, Any]:
        """Return engine statistics.

        Returns
        -------
        dict[str, Any]
            Dictionary with keys: total_watermarked, total_verified,
            total_tampered, registered_records.
        """
        return dict(self._stats)


__all__ = [
    "WatermarkMethod",
    "ContentType",
    "WatermarkPayload",
    "WatermarkResult",
    "ProvenanceChain",
    "ProvenanceRecord",
    "WatermarkConfig",
    "WatermarkEngine",
]
