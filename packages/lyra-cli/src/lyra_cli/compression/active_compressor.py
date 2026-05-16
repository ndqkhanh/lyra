"""
Active Context Compression - Focus-style agent-driven compression.

Implements explicit focus regions with persistent Knowledge blocks.
Achieves 70%+ compression while preserving causal state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json


@dataclass
class FocusRegion:
    """A region of exploration that can be compressed."""

    region_id: str
    start_step: int
    end_step: int
    phase: str  # "exploration" or "exploitation"
    observations: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    compressed: bool = False
    knowledge_extracted: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class KnowledgeBlock:
    """Persistent knowledge extracted from compressed regions."""

    knowledge_id: str
    content: str
    source_regions: List[str] = field(default_factory=list)
    confidence: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: Optional[str] = None
    usage_count: int = 0


class ActiveCompressor:
    """
    Active context compression with agent-driven decisions.

    Features:
    - Explicit focus regions (exploration vs exploitation)
    - Persistent Knowledge blocks
    - Sawtooth context pattern (compress then grow)
    - Preserves verified causal state
    """

    def __init__(self, data_dir: str = "./data/compression"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.focus_regions: List[FocusRegion] = []
        self.knowledge_blocks: Dict[str, KnowledgeBlock] = {}
        self.current_step = 0

        # Statistics
        self.total_observations = 0
        self.total_compressed = 0
        self.compression_events = 0

        self._load_state()

    def _load_state(self):
        """Load compression state from disk."""
        state_file = self.data_dir / "compression_state.json"
        if state_file.exists():
            with open(state_file, "r") as f:
                data = json.load(f)
                self.focus_regions = [
                    FocusRegion(**r) for r in data.get("focus_regions", [])
                ]
                self.knowledge_blocks = {
                    kid: KnowledgeBlock(**kdata)
                    for kid, kdata in data.get("knowledge_blocks", {}).items()
                }
                self.current_step = data.get("current_step", 0)
                self.total_observations = data.get("total_observations", 0)
                self.total_compressed = data.get("total_compressed", 0)
                self.compression_events = data.get("compression_events", 0)

    def _save_state(self):
        """Save compression state to disk."""
        data = {
            "focus_regions": [
                {
                    "region_id": r.region_id,
                    "start_step": r.start_step,
                    "end_step": r.end_step,
                    "phase": r.phase,
                    "observations": r.observations,
                    "actions": r.actions,
                    "compressed": r.compressed,
                    "knowledge_extracted": r.knowledge_extracted,
                    "created_at": r.created_at,
                }
                for r in self.focus_regions
            ],
            "knowledge_blocks": {
                kid: {
                    "knowledge_id": k.knowledge_id,
                    "content": k.content,
                    "source_regions": k.source_regions,
                    "confidence": k.confidence,
                    "created_at": k.created_at,
                    "last_used": k.last_used,
                    "usage_count": k.usage_count,
                }
                for kid, k in self.knowledge_blocks.items()
            },
            "current_step": self.current_step,
            "total_observations": self.total_observations,
            "total_compressed": self.total_compressed,
            "compression_events": self.compression_events,
        }

        with open(self.data_dir / "compression_state.json", "w") as f:
            json.dump(data, f, indent=2)

    def add_observation(
        self,
        observation: str,
        action: Optional[str] = None,
        phase: str = "exploration"
    ):
        """Add observation to current focus region."""
        self.current_step += 1
        self.total_observations += 1

        # Get or create current region
        if not self.focus_regions or self.focus_regions[-1].compressed:
            region = FocusRegion(
                region_id=f"region_{len(self.focus_regions):04d}",
                start_step=self.current_step,
                end_step=self.current_step,
                phase=phase,
            )
            self.focus_regions.append(region)
        else:
            region = self.focus_regions[-1]
            region.end_step = self.current_step

        region.observations.append(observation)
        if action:
            region.actions.append(action)

        self._save_state()

    def should_compress(self) -> bool:
        """
        Decide if current region should be compressed.

        Compress when:
        - Region is in exploration phase and has many observations
        - Transitioning from exploration to exploitation
        - Context is approaching limits
        """
        if not self.focus_regions:
            return False

        current_region = self.focus_regions[-1]

        # Don't compress if already compressed
        if current_region.compressed:
            return False

        # Compress exploration regions with many observations
        if current_region.phase == "exploration":
            if len(current_region.observations) >= 20:
                return True

        # Compress if context is large
        total_obs = sum(len(r.observations) for r in self.focus_regions if not r.compressed)
        if total_obs >= 50:
            return True

        return False

    def compress_region(self, region_id: str, knowledge: str) -> str:
        """
        Compress a focus region by extracting knowledge.

        Args:
            region_id: Region to compress
            knowledge: Extracted knowledge summary

        Returns:
            Knowledge block ID
        """
        # Find region
        region = None
        for r in self.focus_regions:
            if r.region_id == region_id:
                region = r
                break

        if not region:
            raise ValueError(f"Region {region_id} not found")

        # Mark as compressed
        region.compressed = True
        region.knowledge_extracted = knowledge

        # Create knowledge block
        kb_id = f"kb_{len(self.knowledge_blocks):04d}"
        kb = KnowledgeBlock(
            knowledge_id=kb_id,
            content=knowledge,
            source_regions=[region_id],
        )

        self.knowledge_blocks[kb_id] = kb

        # Update statistics
        self.total_compressed += len(region.observations)
        self.compression_events += 1

        self._save_state()

        return kb_id

    def get_active_context(self) -> Dict[str, Any]:
        """
        Get current active context (uncompressed + knowledge blocks).

        Returns:
            Dict with observations and knowledge
        """
        # Uncompressed observations
        active_observations = []
        for region in self.focus_regions:
            if not region.compressed:
                active_observations.extend(region.observations)

        # All knowledge blocks
        knowledge = [kb.content for kb in self.knowledge_blocks.values()]

        return {
            "observations": active_observations,
            "knowledge": knowledge,
            "total_tokens_estimate": (
                len(" ".join(active_observations).split()) +
                len(" ".join(knowledge).split())
            ),
        }

    def get_compression_ratio(self) -> float:
        """Calculate current compression ratio."""
        if self.total_observations == 0:
            return 0.0

        active_context = self.get_active_context()
        active_obs_count = len(active_context["observations"])

        # Compression ratio = (total - active) / total
        return (self.total_observations - active_obs_count) / self.total_observations

    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics."""
        return {
            "total_observations": self.total_observations,
            "total_compressed": self.total_compressed,
            "compression_events": self.compression_events,
            "compression_ratio": self.get_compression_ratio(),
            "num_regions": len(self.focus_regions),
            "num_knowledge_blocks": len(self.knowledge_blocks),
            "current_step": self.current_step,
        }

    def use_knowledge(self, knowledge_id: str):
        """Record that a knowledge block was used."""
        if knowledge_id in self.knowledge_blocks:
            kb = self.knowledge_blocks[knowledge_id]
            kb.usage_count += 1
            kb.last_used = datetime.now().isoformat()
            self._save_state()
