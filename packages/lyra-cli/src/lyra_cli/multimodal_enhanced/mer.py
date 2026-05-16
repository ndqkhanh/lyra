"""
Multimodal Execution Record (MER) - Enhanced AER with multimodal evidence.

Extends Agent Execution Record with frame-by-frame provenance tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from lyra_cli.observability.aer import AgentAction, AgentDecision
from lyra_cli.multimodal_enhanced.hop_trace import MultimodalFrame, RegionEvidence


@dataclass
class MultimodalAgentAction(AgentAction):
    """Agent action with multimodal evidence."""

    frames: List[MultimodalFrame] = field(default_factory=list)
    regions: List[RegionEvidence] = field(default_factory=list)


@dataclass
class MultimodalExecutionRecord:
    """Enhanced execution record with multimodal evidence."""

    record_id: str
    agent_id: str
    session_id: str
    task_description: str
    start_time: str
    end_time: Optional[str] = None
    actions: List[MultimodalAgentAction] = field(default_factory=list)
    decisions: List[AgentDecision] = field(default_factory=list)
    frames: List[MultimodalFrame] = field(default_factory=list)
    final_status: str = "in_progress"
    final_output: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultimodalAERSystem:
    """
    Multimodal Agent Execution Record System.

    Features:
    - Frame-by-frame provenance
    - Region-level evidence tracking
    - Multimodal action recording
    - Complete audit trail with visual evidence
    """

    def __init__(self):
        self.records: Dict[str, MultimodalExecutionRecord] = {}
        self.active_records: Dict[str, str] = {}

        # Statistics
        self.stats = {
            "total_records": 0,
            "total_actions": 0,
            "total_frames": 0,
            "total_regions": 0,
        }

    def start_execution(
        self,
        agent_id: str,
        session_id: str,
        task_description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start recording multimodal execution."""
        record_id = f"mer_{len(self.records):06d}"

        record = MultimodalExecutionRecord(
            record_id=record_id,
            agent_id=agent_id,
            session_id=session_id,
            task_description=task_description,
            start_time=datetime.now().isoformat(),
            metadata=metadata or {},
        )

        self.records[record_id] = record
        self.active_records[agent_id] = record_id
        self.stats["total_records"] += 1

        return record_id

    def record_action_with_frames(
        self,
        agent_id: str,
        action_type: str,
        description: str,
        frames: Optional[List[MultimodalFrame]] = None,
        regions: Optional[List[RegionEvidence]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        reasoning: Optional[str] = None,
        success: bool = True
    ) -> str:
        """Record action with multimodal evidence."""
        if agent_id not in self.active_records:
            return ""

        record_id = self.active_records[agent_id]
        record = self.records[record_id]

        # Import ActionType from aer module
        from lyra_cli.observability.aer import ActionType

        action = MultimodalAgentAction(
            action_id=f"{record_id}_action_{len(record.actions):04d}",
            action_type=ActionType.TOOL_CALL,  # Default type
            timestamp=datetime.now().isoformat(),
            agent_id=agent_id,
            description=description,
            inputs=inputs or {},
            outputs=outputs or {},
            reasoning=reasoning,
            success=success,
            frames=frames or [],
            regions=regions or [],
        )

        record.actions.append(action)
        self.stats["total_actions"] += 1

        if frames:
            record.frames.extend(frames)
            self.stats["total_frames"] += len(frames)

        if regions:
            self.stats["total_regions"] += len(regions)

        return action.action_id

    def add_frame_to_record(
        self,
        agent_id: str,
        frame: MultimodalFrame
    ):
        """Add a frame to the current record."""
        if agent_id not in self.active_records:
            return

        record_id = self.active_records[agent_id]
        record = self.records[record_id]

        record.frames.append(frame)
        self.stats["total_frames"] += 1

    def end_execution(
        self,
        agent_id: str,
        status: str,
        final_output: Optional[Any] = None
    ):
        """End multimodal execution recording."""
        if agent_id not in self.active_records:
            return

        record_id = self.active_records[agent_id]
        record = self.records[record_id]

        record.end_time = datetime.now().isoformat()
        record.final_status = status
        record.final_output = final_output

        del self.active_records[agent_id]

    def get_record(self, record_id: str) -> Optional[MultimodalExecutionRecord]:
        """Get a record by ID."""
        return self.records.get(record_id)

    def export_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Export record with full multimodal provenance."""
        record = self.get_record(record_id)
        if not record:
            return None

        return {
            "record_id": record.record_id,
            "agent_id": record.agent_id,
            "session_id": record.session_id,
            "task_description": record.task_description,
            "start_time": record.start_time,
            "end_time": record.end_time,
            "final_status": record.final_status,
            "action_count": len(record.actions),
            "frame_count": len(record.frames),
            "actions": [
                {
                    "action_id": action.action_id,
                    "description": action.description,
                    "timestamp": action.timestamp,
                    "success": action.success,
                    "frame_count": len(action.frames),
                    "region_count": len(action.regions),
                }
                for action in record.actions
            ],
            "frames": [
                {
                    "frame_id": frame.frame_id,
                    "timestamp": frame.timestamp,
                    "has_screenshot": frame.screenshot is not None,
                    "has_dom": frame.dom_snapshot is not None,
                    "region_count": len(frame.regions),
                }
                for frame in record.frames
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get MER statistics."""
        return {
            **self.stats,
            "num_records": len(self.records),
            "active_records": len(self.active_records),
        }
