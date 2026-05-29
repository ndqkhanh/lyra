"""Observation capture - Records user interactions for learning"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Observation:
    """A single observation from user interaction"""

    timestamp: datetime
    session_id: str
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: dict[str, Any] | None
    user_prompt: str | None
    agent_response: str | None
    project_id: str | None


class ObservationCapture:
    """Captures observations from hooks for learning"""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path.home() / ".lyra" / "learning" / "observations"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, observation: Observation):
        """Capture an observation"""
        # Determine file path
        if observation.project_id:
            obs_file = self.data_dir / observation.project_id / "observations.jsonl"
            obs_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            obs_file = self.data_dir / "global" / "observations.jsonl"
            obs_file.parent.mkdir(parents=True, exist_ok=True)

        # Append observation
        with open(obs_file, "a") as f:
            obs_dict = {
                "timestamp": observation.timestamp.isoformat(),
                "session_id": observation.session_id,
                "tool_name": observation.tool_name,
                "tool_input": observation.tool_input,
                "tool_output": observation.tool_output,
                "user_prompt": observation.user_prompt,
                "agent_response": observation.agent_response,
                "project_id": observation.project_id,
            }
            f.write(json.dumps(obs_dict) + "\n")

    def get_observations(self, project_id: str | None = None, limit: int = 100) -> list:
        """Get recent observations"""
        if project_id:
            obs_file = self.data_dir / project_id / "observations.jsonl"
        else:
            obs_file = self.data_dir / "global" / "observations.jsonl"

        if not obs_file.exists():
            return []

        observations = []
        with open(obs_file) as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    obs_dict = json.loads(line)
                    observations.append(obs_dict)
                except json.JSONDecodeError:
                    continue

        return observations

    def capture_from_hook(
        self, hook_context: dict[str, Any], session_id: str, project_id: str | None = None
    ):
        """Capture observation from hook context"""
        observation = Observation(
            timestamp=datetime.now(),
            session_id=session_id,
            tool_name=hook_context.get("tool_name"),
            tool_input=hook_context.get("tool_input", {}),
            tool_output=hook_context.get("tool_output"),
            user_prompt=hook_context.get("user_prompt"),
            agent_response=hook_context.get("agent_response"),
            project_id=project_id,
        )
        self.capture(observation)


# Global observation capture
_observation_capture: ObservationCapture | None = None


def get_observation_capture() -> ObservationCapture:
    """Get or create global observation capture"""
    global _observation_capture
    if _observation_capture is None:
        _observation_capture = ObservationCapture()
    return _observation_capture
