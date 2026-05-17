"""Edit actions for meta-agent."""
from dataclasses import dataclass
from enum import Enum


class EditType(Enum):
    """Type of edit action."""
    PROCEDURE = "procedure"  # Edit Python code
    AGENT_CONTEXT = "agent_context"  # Edit agent context files


@dataclass
class EditAction:
    """Proposed edit from meta-agent."""
    edit_type: EditType
    target_path: str
    content: str
    rationale: str
