"""
Multimodal module for Lyra - Multimodal & Computer-Use Support.

Implements:
- Multimodal evidence chain for images/video/screenshots
- Computer-use context engineering
- Screenshot analysis with OCR and UI detection
- Memory integration with compression (10MB → 2KB)
"""

from lyra_cli.multimodal.computer_use import (
    ActionType,
    ComputerUseContext,
    ComputerUseSession,
    UIAction,
    UIElement,
)
from lyra_cli.multimodal.evidence_chain import (
    EvidenceChain,
    MediaEvidence,
    MediaMetadata,
    MediaType,
    MultimodalEvidenceChain,
)
from lyra_cli.multimodal.memory_integration import (
    CompressionLevel,
    MultimodalMemoryIntegrator,
    MultimodalReference,
)
from lyra_cli.multimodal.screenshot_analysis import (
    DetectedObject,
    OCRResult,
    ScreenshotAnalysis,
    ScreenshotAnalyzer,
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
