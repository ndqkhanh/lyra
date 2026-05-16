"""
Agent Execution Record (AER) - Full transparency into agent operations.

Records all agent decisions, actions, and reasoning for complete observability.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class ActionType(Enum):
    """Type of agent action."""

    TOOL_CALL = "tool_call"
    DECISION = "decision"
    REASONING = "reasoning"
    OBSERVATION = "observation"
    PLANNING = "planning"


@dataclass
class AgentAction:
    """A single agent action."""

    action_id: str
    action_type: ActionType
    timestamp: str
    agent_id: str
    description: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    reasoning: Optional[str] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class AgentDecision:
    """A decision made by an agent."""

    decision_id: str
    timestamp: str
    agent_id: str
    question: str
    options: List[str]
    selected_option: str
    reasoning: str
    confidence: float  # 0.0 to 1.0


@dataclass
class AgentExecutionRecord:
    """Complete execution record for an agent session."""

    record_id: str
    agent_id: str
    session_id: str
    task_description: str
    start_time: str
    end_time: Optional[str] = None
    actions: List[AgentAction] = field(default_factory=list)
    decisions: List[AgentDecision] = field(default_factory=list)
    final_status: str = "in_progress"  # in_progress, success, failure
    final_output: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AERSystem:
    """
    Agent Execution Record (AER) System.

    Features:
    - Records all agent actions and decisions
    - Captures reasoning and context
    - Provides complete audit trail
    - Enables replay and analysis
    """

    def __init__(self):
        self.records: Dict[str, AgentExecutionRecord] = {}
        self.active_records: Dict[str, str] = {}  # agent_id -> record_id

        # Statistics
        self.stats = {
            "total_records": 0,
            "total_actions": 0,
            "total_decisions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
        }

    def start_execution(
        self,
        agent_id: str,
        session_id: str,
        task_description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start recording an agent execution.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            task_description: Description of the task
            metadata: Optional metadata

        Returns:
            Record ID
        """
        record_id = f"aer_{len(self.records):06d}"

        record = AgentExecutionRecord(
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

    def record_action(
        self,
        agent_id: str,
        action_type: ActionType,
        description: str,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        reasoning: Optional[str] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> str:
        """
        Record an agent action.

        Args:
            agent_id: Agent performing the action
            action_type: Type of action
            description: Action description
            inputs: Action inputs
            outputs: Action outputs
            reasoning: Reasoning behind the action
            duration_ms: Action duration
            success: Whether action succeeded
            error: Error message if failed

        Returns:
            Action ID
        """
        if agent_id not in self.active_records:
            return ""

        record_id = self.active_records[agent_id]
        record = self.records[record_id]

        action = AgentAction(
            action_id=f"{record_id}_action_{len(record.actions):04d}",
            action_type=action_type,
            timestamp=datetime.now().isoformat(),
            agent_id=agent_id,
            description=description,
            inputs=inputs or {},
            outputs=outputs or {},
            reasoning=reasoning,
            duration_ms=duration_ms,
            success=success,
            error=error,
        )

        record.actions.append(action)
        self.stats["total_actions"] += 1

        return action.action_id

    def record_decision(
        self,
        agent_id: str,
        question: str,
        options: List[str],
        selected_option: str,
        reasoning: str,
        confidence: float
    ) -> str:
        """
        Record an agent decision.

        Args:
            agent_id: Agent making the decision
            question: Decision question
            options: Available options
            selected_option: Selected option
            reasoning: Decision reasoning
            confidence: Confidence level (0.0-1.0)

        Returns:
            Decision ID
        """
        if agent_id not in self.active_records:
            return ""

        record_id = self.active_records[agent_id]
        record = self.records[record_id]

        decision = AgentDecision(
            decision_id=f"{record_id}_decision_{len(record.decisions):04d}",
            timestamp=datetime.now().isoformat(),
            agent_id=agent_id,
            question=question,
            options=options,
            selected_option=selected_option,
            reasoning=reasoning,
            confidence=confidence,
        )

        record.decisions.append(decision)
        self.stats["total_decisions"] += 1

        return decision.decision_id

    def end_execution(
        self,
        agent_id: str,
        status: str,
        final_output: Optional[Any] = None
    ):
        """
        End an agent execution recording.

        Args:
            agent_id: Agent identifier
            status: Final status (success, failure)
            final_output: Final output
        """
        if agent_id not in self.active_records:
            return

        record_id = self.active_records[agent_id]
        record = self.records[record_id]

        record.end_time = datetime.now().isoformat()
        record.final_status = status
        record.final_output = final_output

        # Update statistics
        if status == "success":
            self.stats["successful_executions"] += 1
        else:
            self.stats["failed_executions"] += 1

        # Remove from active records
        del self.active_records[agent_id]

    def get_record(self, record_id: str) -> Optional[AgentExecutionRecord]:
        """Get an execution record by ID."""
        return self.records.get(record_id)

    def get_agent_records(self, agent_id: str) -> List[AgentExecutionRecord]:
        """Get all records for a specific agent."""
        return [
            record for record in self.records.values()
            if record.agent_id == agent_id
        ]

    def export_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a record in JSON format.

        Args:
            record_id: Record to export

        Returns:
            Record data
        """
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
            "final_output": str(record.final_output) if record.final_output else None,
            "metadata": record.metadata,
            "actions": [
                {
                    "action_id": action.action_id,
                    "action_type": action.action_type.value,
                    "timestamp": action.timestamp,
                    "description": action.description,
                    "inputs": action.inputs,
                    "outputs": action.outputs,
                    "reasoning": action.reasoning,
                    "duration_ms": action.duration_ms,
                    "success": action.success,
                    "error": action.error,
                }
                for action in record.actions
            ],
            "decisions": [
                {
                    "decision_id": decision.decision_id,
                    "timestamp": decision.timestamp,
                    "question": decision.question,
                    "options": decision.options,
                    "selected_option": decision.selected_option,
                    "reasoning": decision.reasoning,
                    "confidence": decision.confidence,
                }
                for decision in record.decisions
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get AER system statistics."""
        success_rate = (
            self.stats["successful_executions"] /
            (self.stats["successful_executions"] + self.stats["failed_executions"])
            if (self.stats["successful_executions"] + self.stats["failed_executions"]) > 0
            else 0.0
        )

        return {
            **self.stats,
            "success_rate": success_rate,
            "num_records": len(self.records),
            "active_records": len(self.active_records),
        }
