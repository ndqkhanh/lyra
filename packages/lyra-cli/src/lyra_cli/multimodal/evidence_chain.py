"""
Multimodal Evidence Chain for Images, Video, and Screenshots.

Processes multimodal inputs with context preservation and evidence tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import base64


class MediaType(Enum):
    """Type of media."""

    IMAGE = "image"
    VIDEO = "video"
    SCREENSHOT = "screenshot"
    AUDIO = "audio"


@dataclass
class MediaMetadata:
    """Metadata for media content."""

    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    fps: Optional[int] = None


@dataclass
class MediaEvidence:
    """Evidence extracted from media."""

    evidence_id: str
    media_type: MediaType
    timestamp: str
    content: str  # Base64 encoded or file path
    description: str
    extracted_text: Optional[str] = None
    detected_objects: List[str] = field(default_factory=list)
    metadata: Optional[MediaMetadata] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceChain:
    """A chain of related evidence."""

    chain_id: str
    task_description: str
    evidence_items: List[MediaEvidence] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


class MultimodalEvidenceChain:
    """
    Multimodal evidence chain for processing images, video, and screenshots.

    Features:
    - Processes multiple media types
    - Preserves context across evidence
    - Tracks evidence relationships
    - Supports evidence replay
    """

    def __init__(self):
        self.chains: Dict[str, EvidenceChain] = {}
        self.evidence_index: Dict[str, MediaEvidence] = {}

        # Statistics
        self.stats = {
            "total_chains": 0,
            "total_evidence": 0,
            "images_processed": 0,
            "videos_processed": 0,
            "screenshots_processed": 0,
        }

    def start_chain(self, task_description: str) -> str:
        """
        Start a new evidence chain.

        Args:
            task_description: Description of the task

        Returns:
            Chain ID
        """
        chain_id = f"chain_{len(self.chains):06d}"

        chain = EvidenceChain(
            chain_id=chain_id,
            task_description=task_description,
        )

        self.chains[chain_id] = chain
        self.stats["total_chains"] += 1

        return chain_id

    def add_evidence(
        self,
        chain_id: str,
        media_type: MediaType,
        content: str,
        description: str,
        extracted_text: Optional[str] = None,
        detected_objects: Optional[List[str]] = None,
        metadata: Optional[MediaMetadata] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add evidence to a chain.

        Args:
            chain_id: Chain to add evidence to
            media_type: Type of media
            content: Media content (base64 or path)
            description: Evidence description
            extracted_text: Text extracted from media
            detected_objects: Objects detected in media
            metadata: Media metadata
            context: Additional context

        Returns:
            Evidence ID
        """
        if chain_id not in self.chains:
            return ""

        chain = self.chains[chain_id]

        evidence = MediaEvidence(
            evidence_id=f"{chain_id}_evidence_{len(chain.evidence_items):04d}",
            media_type=media_type,
            timestamp=datetime.now().isoformat(),
            content=content,
            description=description,
            extracted_text=extracted_text,
            detected_objects=detected_objects or [],
            metadata=metadata,
            context=context or {},
        )

        chain.evidence_items.append(evidence)
        self.evidence_index[evidence.evidence_id] = evidence

        # Update statistics
        self.stats["total_evidence"] += 1
        if media_type == MediaType.IMAGE:
            self.stats["images_processed"] += 1
        elif media_type == MediaType.VIDEO:
            self.stats["videos_processed"] += 1
        elif media_type == MediaType.SCREENSHOT:
            self.stats["screenshots_processed"] += 1

        return evidence.evidence_id

    def complete_chain(self, chain_id: str):
        """
        Mark a chain as complete.

        Args:
            chain_id: Chain to complete
        """
        if chain_id not in self.chains:
            return

        chain = self.chains[chain_id]
        chain.completed_at = datetime.now().isoformat()

    def get_chain(self, chain_id: str) -> Optional[EvidenceChain]:
        """Get a chain by ID."""
        return self.chains.get(chain_id)

    def get_evidence(self, evidence_id: str) -> Optional[MediaEvidence]:
        """Get evidence by ID."""
        return self.evidence_index.get(evidence_id)

    def search_evidence(
        self,
        media_type: Optional[MediaType] = None,
        text_query: Optional[str] = None
    ) -> List[MediaEvidence]:
        """
        Search for evidence.

        Args:
            media_type: Filter by media type
            text_query: Search in descriptions and extracted text

        Returns:
            List of matching evidence
        """
        results = []

        for evidence in self.evidence_index.values():
            # Filter by media type
            if media_type and evidence.media_type != media_type:
                continue

            # Filter by text query
            if text_query:
                text_lower = text_query.lower()
                desc_match = text_lower in evidence.description.lower()
                text_match = (
                    evidence.extracted_text and
                    text_lower in evidence.extracted_text.lower()
                )

                if not (desc_match or text_match):
                    continue

            results.append(evidence)

        return results

    def export_chain(self, chain_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a chain in JSON format.

        Args:
            chain_id: Chain to export

        Returns:
            Chain data
        """
        chain = self.get_chain(chain_id)
        if not chain:
            return None

        return {
            "chain_id": chain.chain_id,
            "task_description": chain.task_description,
            "created_at": chain.created_at,
            "completed_at": chain.completed_at,
            "evidence_count": len(chain.evidence_items),
            "evidence": [
                {
                    "evidence_id": evidence.evidence_id,
                    "media_type": evidence.media_type.value,
                    "timestamp": evidence.timestamp,
                    "description": evidence.description,
                    "extracted_text": evidence.extracted_text,
                    "detected_objects": evidence.detected_objects,
                    "metadata": {
                        "width": evidence.metadata.width,
                        "height": evidence.metadata.height,
                        "format": evidence.metadata.format,
                        "size_bytes": evidence.metadata.size_bytes,
                    } if evidence.metadata else None,
                    "context": evidence.context,
                }
                for evidence in chain.evidence_items
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get evidence chain statistics."""
        return {
            **self.stats,
            "num_chains": len(self.chains),
            "num_evidence": len(self.evidence_index),
        }
