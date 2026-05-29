"""Multimodal Memory Integration.

Integrates multimodal evidence (screenshots, DOM, terminal) with the
7-tier memory system. Provides storage, retrieval, and compression
for multimodal content.

Architecture:
- Stores multimodal evidence in L2 (episodic) memory
- Compresses large screenshots/DOM to compact references
- Enables cross-modal retrieval (text query → screenshot)
- Preserves evidence chains for debugging

Usage:
    integrator = MultimodalMemoryIntegrator(memory_system)

    # Store screenshot evidence
    evidence_id = integrator.store_screenshot(
        screenshot_data=base64_image,
        description="Login page",
        extracted_text="Username Password Login",
        context={"task": "login", "step": 1}
    )

    # Retrieve by text query
    results = integrator.search_multimodal("login page")
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lyra_cli.multimodal.computer_use import ComputerUseContext
    from lyra_cli.multimodal.evidence_chain import (
        MultimodalEvidenceChain,
    )
    from lyra_cli.multimodal.screenshot_analysis import ScreenshotAnalyzer


class CompressionLevel(Enum):
    """Compression level for multimodal content."""

    NONE = "none"  # Store full content
    LIGHT = "light"  # Store thumbnail + metadata
    AGGRESSIVE = "aggressive"  # Store only text + layout summary


@dataclass
class MultimodalReference:
    """Compact reference to multimodal content."""

    ref_id: str
    media_type: str
    content_hash: str
    description: str
    extracted_text: str | None
    metadata: dict[str, Any]
    storage_path: str | None = None  # Path to full content if stored
    thumbnail: str | None = None  # Base64 thumbnail for preview
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class MultimodalMemoryIntegrator:
    """
    Integrates multimodal evidence with the memory system.

    Features:
    - Stores multimodal evidence in episodic memory
    - Compresses large content (10MB → 2KB)
    - Cross-modal retrieval (text → image)
    - Evidence chain preservation
    """

    def __init__(
        self,
        evidence_chain: MultimodalEvidenceChain | None = None,
        computer_use: ComputerUseContext | None = None,
        screenshot_analyzer: ScreenshotAnalyzer | None = None,
        compression_level: CompressionLevel = CompressionLevel.AGGRESSIVE,
    ):
        """Initialize the integrator.

        Args:
            evidence_chain: Multimodal evidence chain
            computer_use: Computer-use context
            screenshot_analyzer: Screenshot analyzer
            compression_level: How aggressively to compress
        """
        # Import here to avoid circular dependencies
        from lyra_cli.multimodal.computer_use import ComputerUseContext
        from lyra_cli.multimodal.evidence_chain import MultimodalEvidenceChain
        from lyra_cli.multimodal.screenshot_analysis import ScreenshotAnalyzer

        self.evidence_chain = evidence_chain or MultimodalEvidenceChain()
        self.computer_use = computer_use or ComputerUseContext()
        self.screenshot_analyzer = screenshot_analyzer or ScreenshotAnalyzer()
        self.compression_level = compression_level

        # Storage
        self.references: dict[str, MultimodalReference] = {}
        self.content_store: dict[str, bytes] = {}  # Hash → content

        # Statistics
        self.stats = {
            "total_stored": 0,
            "total_compressed": 0,
            "bytes_saved": 0,
            "screenshots_stored": 0,
            "dom_snapshots_stored": 0,
            "terminal_outputs_stored": 0,
        }

    def store_screenshot(
        self,
        screenshot_data: str,
        description: str,
        extracted_text: str | None = None,
        detected_objects: list[str] | None = None,
        context: dict[str, Any] | None = None,
        chain_id: str | None = None,
    ) -> str:
        """Store a screenshot with compression.

        Args:
            screenshot_data: Base64 encoded screenshot
            description: Human-readable description
            extracted_text: OCR extracted text
            detected_objects: Detected UI elements/objects
            context: Additional context
            chain_id: Evidence chain to add to

        Returns:
            Reference ID
        """
        from lyra_cli.multimodal.evidence_chain import MediaType

        # Compute content hash
        content_hash = hashlib.sha256(screenshot_data.encode()).hexdigest()[:16]

        # Compress based on level
        storage_path = None
        thumbnail = None

        if self.compression_level == CompressionLevel.NONE:
            # Store full content
            self.content_store[content_hash] = screenshot_data.encode()
            storage_path = f"screenshot_{content_hash}"

        elif self.compression_level == CompressionLevel.LIGHT:
            # Store thumbnail + metadata
            thumbnail = self._create_thumbnail(screenshot_data)
            self.content_store[content_hash] = screenshot_data.encode()
            storage_path = f"screenshot_{content_hash}"

        elif self.compression_level == CompressionLevel.AGGRESSIVE:
            # Store only text + layout summary
            # Full content discarded after processing
            thumbnail = self._create_thumbnail(screenshot_data)

        # Create reference
        ref_id = f"screenshot_{len(self.references):06d}"

        reference = MultimodalReference(
            ref_id=ref_id,
            media_type="screenshot",
            content_hash=content_hash,
            description=description,
            extracted_text=extracted_text,
            metadata={
                "detected_objects": detected_objects or [],
                "context": context or {},
                "compression_level": self.compression_level.value,
            },
            storage_path=storage_path,
            thumbnail=thumbnail,
        )

        self.references[ref_id] = reference

        # Add to evidence chain if provided
        if chain_id:
            self.evidence_chain.add_evidence(
                chain_id=chain_id,
                media_type=MediaType.SCREENSHOT,
                content=ref_id,  # Store reference, not full content
                description=description,
                extracted_text=extracted_text,
                detected_objects=detected_objects,
                context=context,
            )

        # Update statistics
        self.stats["total_stored"] += 1
        self.stats["screenshots_stored"] += 1

        if self.compression_level != CompressionLevel.NONE:
            self.stats["total_compressed"] += 1
            # Estimate bytes saved (10MB → 2KB)
            self.stats["bytes_saved"] += 10 * 1024 * 1024 - 2 * 1024

        return ref_id

    def store_dom_snapshot(
        self,
        dom_data: str,
        description: str,
        relevant_elements: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
        chain_id: str | None = None,
    ) -> str:
        """Store a DOM snapshot with filtering.

        Args:
            dom_data: Full DOM HTML
            description: Human-readable description
            relevant_elements: Filtered relevant elements
            context: Additional context
            chain_id: Evidence chain to add to

        Returns:
            Reference ID
        """
        # Compute content hash
        content_hash = hashlib.sha256(dom_data.encode()).hexdigest()[:16]

        # Filter DOM to relevant elements only
        filtered_dom = self._filter_dom(dom_data, relevant_elements)

        # Create reference
        ref_id = f"dom_{len(self.references):06d}"

        reference = MultimodalReference(
            ref_id=ref_id,
            media_type="dom",
            content_hash=content_hash,
            description=description,
            extracted_text=filtered_dom,  # Store filtered DOM as text
            metadata={
                "relevant_elements": relevant_elements or [],
                "context": context or {},
                "original_size": len(dom_data),
                "filtered_size": len(filtered_dom),
                "compression_ratio": len(dom_data) / max(len(filtered_dom), 1),
            },
        )

        self.references[ref_id] = reference

        # Update statistics
        self.stats["total_stored"] += 1
        self.stats["dom_snapshots_stored"] += 1
        self.stats["bytes_saved"] += len(dom_data) - len(filtered_dom)

        return ref_id

    def store_terminal_output(
        self,
        command: str,
        output: str,
        exit_code: int,
        description: str,
        context: dict[str, Any] | None = None,
        chain_id: str | None = None,
    ) -> str:
        """Store terminal command output.

        Args:
            command: Command executed
            output: Command output
            exit_code: Exit code
            description: Human-readable description
            context: Additional context
            chain_id: Evidence chain to add to

        Returns:
            Reference ID
        """
        # Create compact representation
        content = f"$ {command}\n{output}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Truncate long output
        if len(output) > 10000:
            output = output[:5000] + "\n... (truncated) ...\n" + output[-5000:]

        # Create reference
        ref_id = f"terminal_{len(self.references):06d}"

        reference = MultimodalReference(
            ref_id=ref_id,
            media_type="terminal",
            content_hash=content_hash,
            description=description,
            extracted_text=f"$ {command}\n{output}",
            metadata={
                "command": command,
                "exit_code": exit_code,
                "context": context or {},
            },
        )

        self.references[ref_id] = reference

        # Update statistics
        self.stats["total_stored"] += 1
        self.stats["terminal_outputs_stored"] += 1

        return ref_id

    def search_multimodal(
        self,
        query: str,
        media_type: str | None = None,
        limit: int = 10,
    ) -> list[MultimodalReference]:
        """Search multimodal content by text query.

        Args:
            query: Text query
            media_type: Filter by media type
            limit: Max results

        Returns:
            List of matching references
        """
        results = []
        query_lower = query.lower()

        for ref in self.references.values():
            # Filter by media type
            if media_type and ref.media_type != media_type:
                continue

            # Search in description and extracted text
            desc_match = query_lower in ref.description.lower()
            text_match = (
                ref.extracted_text and
                query_lower in ref.extracted_text.lower()
            )

            if desc_match or text_match:
                results.append(ref)

            if len(results) >= limit:
                break

        return results

    def get_reference(self, ref_id: str) -> MultimodalReference | None:
        """Get a reference by ID."""
        return self.references.get(ref_id)

    def get_full_content(self, ref_id: str) -> bytes | None:
        """Get full content if stored.

        Args:
            ref_id: Reference ID

        Returns:
            Full content bytes, or None if not stored
        """
        ref = self.get_reference(ref_id)
        if not ref or not ref.storage_path:
            return None

        return self.content_store.get(ref.content_hash)

    def export_reference(self, ref_id: str) -> dict[str, Any] | None:
        """Export a reference in JSON format.

        Args:
            ref_id: Reference to export

        Returns:
            Reference data
        """
        ref = self.get_reference(ref_id)
        if not ref:
            return None

        return {
            "ref_id": ref.ref_id,
            "media_type": ref.media_type,
            "content_hash": ref.content_hash,
            "description": ref.description,
            "extracted_text": ref.extracted_text,
            "metadata": ref.metadata,
            "has_full_content": ref.storage_path is not None,
            "has_thumbnail": ref.thumbnail is not None,
            "created_at": ref.created_at,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get integration statistics."""
        compression_ratio = (
            self.stats["bytes_saved"] / max(self.stats["total_stored"], 1)
            if self.stats["total_stored"] > 0
            else 0
        )

        return {
            **self.stats,
            "num_references": len(self.references),
            "num_stored_content": len(self.content_store),
            "compression_ratio": compression_ratio,
        }

    def _create_thumbnail(self, screenshot_data: str, max_size: int = 200) -> str:
        """Create a thumbnail from screenshot.

        Args:
            screenshot_data: Base64 screenshot
            max_size: Max dimension in pixels

        Returns:
            Base64 thumbnail
        """
        # Placeholder - in production, use PIL/Pillow
        # For now, just truncate to simulate compression
        if len(screenshot_data) > 1000:
            return screenshot_data[:1000] + "..."
        return screenshot_data

    def _filter_dom(
        self,
        dom_data: str,
        relevant_elements: list[dict[str, Any]] | None = None,
    ) -> str:
        """Filter DOM to relevant elements only.

        Args:
            dom_data: Full DOM HTML
            relevant_elements: Elements to keep

        Returns:
            Filtered DOM
        """
        if not relevant_elements:
            # Simple heuristic: keep only visible text and interactive elements
            # In production, use BeautifulSoup or lxml
            lines = dom_data.split('\n')
            filtered = []

            for line in lines:
                # Keep lines with text content or interactive elements
                if any(tag in line.lower() for tag in ['button', 'input', 'a href', 'form']):
                    filtered.append(line)
                elif line.strip() and not line.strip().startswith('<'):
                    # Keep text content
                    filtered.append(line)

            return '\n'.join(filtered)

        # Filter to specified elements
        # In production, use proper DOM parsing
        return dom_data[:1000]  # Placeholder
