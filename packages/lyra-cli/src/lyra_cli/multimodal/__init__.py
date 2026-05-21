"""
Multimodal module for Lyra - Multimodal & Computer-Use Support.

Implements:
- Multimodal evidence chain for images/video/screenshots
- Computer-use context engineering
- Screenshot analysis with OCR and UI detection
- Memory integration with compression (10MB → 2KB)
"""

from lyra_cli.multimodal.evidence_chain import (
    MediaType,
    MediaMetadata,
    MediaEvidence,
    EvidenceChain,
    MultimodalEvidenceChain,
)

from lyra_cli.multimodal.computer_use import (
    ActionType,
    UIElement,
    UIAction,
    ComputerUseSession,
    ComputerUseContext,
)

from lyra_cli.multimodal.screenshot_analysis import (
    OCRResult,
    DetectedObject,
    ScreenshotAnalysis,
    ScreenshotAnalyzer,
)

from lyra_cli.multimodal.memory_integration import (
    CompressionLevel,
    MultimodalReference,
    MultimodalMemoryIntegrator,
)

__all__ = [
    # Evidence Chain
    "MediaType",
    "MediaMetadata",
    "MediaEvidence",
    "EvidenceChain",
    "MultimodalEvidenceChain",
    # Computer Use
    "ActionType",
    "UIElement",
    "UIAction",
    "ComputerUseSession",
    "ComputerUseContext",
    # Screenshot Analysis
    "OCRResult",
    "DetectedObject",
    "ScreenshotAnalysis",
    "ScreenshotAnalyzer",
    # Memory Integration
    "CompressionLevel",
    "MultimodalReference",
    "MultimodalMemoryIntegrator",
]
