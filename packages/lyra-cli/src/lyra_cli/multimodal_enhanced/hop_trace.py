"""
Multimodal Hop Trace Schema - Phase A Enhancement.

Synchronizes screenshot/DOM/video with region-level evidence provenance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple


@dataclass
class RegionEvidence:
    """Evidence from a specific region in a frame."""

    region_id: str
    bounding_box: Dict[str, int]  # x, y, width, height
    evidence_type: str  # text, ui_element, object, action
    content: str
    confidence: float
    timestamp: str


@dataclass
class MultimodalFrame:
    """A synchronized frame across modalities."""

    frame_id: str
    timestamp: str
    screenshot: Optional[str] = None  # Base64 or path
    dom_snapshot: Optional[Dict[str, Any]] = None
    terminal_output: Optional[str] = None
    code_context: Optional[Dict[str, Any]] = None
    regions: List[RegionEvidence] = field(default_factory=list)


@dataclass
class HopTrace:
    """A single hop in reasoning with multimodal evidence."""

    hop_id: str
    hop_number: int
    reasoning_step: str
    frames: List[MultimodalFrame] = field(default_factory=list)
    input_query: str = ""
    output_answer: str = ""
    confidence: float = 0.0
    provenance: List[str] = field(default_factory=list)


@dataclass
class MultimodalHopTraceChain:
    """Complete chain of reasoning hops with multimodal evidence."""

    chain_id: str
    task_description: str
    hops: List[HopTrace] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    final_answer: Optional[str] = None


class MultimodalHopTracer:
    """
    Multimodal hop trace system for evidence provenance.

    Features:
    - Screenshot/DOM/video synchronization
    - Region-level evidence tracking
    - Hop-by-hop reasoning traces
    - Frame-by-frame provenance
    """

    def __init__(self):
        self.chains: Dict[str, MultimodalHopTraceChain] = {}
        self.frames: Dict[str, MultimodalFrame] = {}

        # Statistics
        self.stats = {
            "total_chains": 0,
            "total_hops": 0,
            "total_frames": 0,
            "total_regions": 0,
        }

    def start_chain(self, task_description: str) -> str:
        """Start a new hop trace chain."""
        chain_id = f"chain_{len(self.chains):06d}"

        chain = MultimodalHopTraceChain(
            chain_id=chain_id,
            task_description=task_description,
        )

        self.chains[chain_id] = chain
        self.stats["total_chains"] += 1

        return chain_id

    def add_hop(
        self,
        chain_id: str,
        reasoning_step: str,
        input_query: str = "",
        output_answer: str = "",
        confidence: float = 0.0
    ) -> str:
        """Add a reasoning hop to the chain."""
        if chain_id not in self.chains:
            return ""

        chain = self.chains[chain_id]

        hop = HopTrace(
            hop_id=f"{chain_id}_hop_{len(chain.hops):03d}",
            hop_number=len(chain.hops) + 1,
            reasoning_step=reasoning_step,
            input_query=input_query,
            output_answer=output_answer,
            confidence=confidence,
        )

        chain.hops.append(hop)
        self.stats["total_hops"] += 1

        return hop.hop_id

    def add_frame(
        self,
        chain_id: str,
        hop_id: str,
        screenshot: Optional[str] = None,
        dom_snapshot: Optional[Dict[str, Any]] = None,
        terminal_output: Optional[str] = None,
        code_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a multimodal frame to a hop."""
        if chain_id not in self.chains:
            return ""

        chain = self.chains[chain_id]

        # Find the hop
        hop = None
        for h in chain.hops:
            if h.hop_id == hop_id:
                hop = h
                break

        if not hop:
            return ""

        frame = MultimodalFrame(
            frame_id=f"{hop_id}_frame_{len(hop.frames):03d}",
            timestamp=datetime.now().isoformat(),
            screenshot=screenshot,
            dom_snapshot=dom_snapshot,
            terminal_output=terminal_output,
            code_context=code_context,
        )

        hop.frames.append(frame)
        self.frames[frame.frame_id] = frame
        self.stats["total_frames"] += 1

        return frame.frame_id

    def add_region_evidence(
        self,
        frame_id: str,
        bounding_box: Dict[str, int],
        evidence_type: str,
        content: str,
        confidence: float
    ) -> str:
        """Add region-level evidence to a frame."""
        if frame_id not in self.frames:
            return ""

        frame = self.frames[frame_id]

        region = RegionEvidence(
            region_id=f"{frame_id}_region_{len(frame.regions):03d}",
            bounding_box=bounding_box,
            evidence_type=evidence_type,
            content=content,
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
        )

        frame.regions.append(region)
        self.stats["total_regions"] += 1

        return region.region_id

    def complete_chain(
        self,
        chain_id: str,
        final_answer: Optional[str] = None
    ):
        """Complete a hop trace chain."""
        if chain_id not in self.chains:
            return

        chain = self.chains[chain_id]
        chain.completed_at = datetime.now().isoformat()
        chain.final_answer = final_answer

    def get_chain(self, chain_id: str) -> Optional[MultimodalHopTraceChain]:
        """Get a chain by ID."""
        return self.chains.get(chain_id)

    def export_chain(self, chain_id: str) -> Optional[Dict[str, Any]]:
        """Export chain with full provenance."""
        chain = self.get_chain(chain_id)
        if not chain:
            return None

        return {
            "chain_id": chain.chain_id,
            "task_description": chain.task_description,
            "created_at": chain.created_at,
            "completed_at": chain.completed_at,
            "final_answer": chain.final_answer,
            "hop_count": len(chain.hops),
            "hops": [
                {
                    "hop_id": hop.hop_id,
                    "hop_number": hop.hop_number,
                    "reasoning_step": hop.reasoning_step,
                    "input_query": hop.input_query,
                    "output_answer": hop.output_answer,
                    "confidence": hop.confidence,
                    "frame_count": len(hop.frames),
                    "frames": [
                        {
                            "frame_id": frame.frame_id,
                            "timestamp": frame.timestamp,
                            "has_screenshot": frame.screenshot is not None,
                            "has_dom": frame.dom_snapshot is not None,
                            "has_terminal": frame.terminal_output is not None,
                            "has_code": frame.code_context is not None,
                            "region_count": len(frame.regions),
                            "regions": [
                                {
                                    "region_id": region.region_id,
                                    "bounding_box": region.bounding_box,
                                    "evidence_type": region.evidence_type,
                                    "content": region.content,
                                    "confidence": region.confidence,
                                }
                                for region in frame.regions
                            ],
                        }
                        for frame in hop.frames
                    ],
                }
                for hop in chain.hops
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get tracer statistics."""
        return {
            **self.stats,
            "num_chains": len(self.chains),
            "num_frames": len(self.frames),
        }
