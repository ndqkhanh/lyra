"""
Computer-Use Context Engineering for Screenshot Analysis.

Provides context engineering for computer-use scenarios with UI interaction tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class ActionType(Enum):
    """Type of UI action."""

    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    HOVER = "hover"
    DRAG = "drag"
    SCREENSHOT = "screenshot"


@dataclass
class UIElement:
    """A UI element detected in a screenshot."""

    element_id: str
    element_type: str  # button, input, link, etc.
    text: Optional[str]
    position: Dict[str, int]  # x, y, width, height
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UIAction:
    """A UI action performed."""

    action_id: str
    action_type: ActionType
    timestamp: str
    target_element: Optional[UIElement]
    input_value: Optional[str] = None
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class ComputerUseSession:
    """A computer-use session with tracked actions."""

    session_id: str
    task_description: str
    start_time: str
    end_time: Optional[str] = None
    actions: List[UIAction] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    final_status: str = "in_progress"


class ComputerUseContext:
    """
    Computer-use context engineering for screenshot analysis.

    Features:
    - UI element detection and tracking
    - Action sequence recording
    - Screenshot analysis
    - Context preservation across actions
    """

    def __init__(self):
        self.sessions: Dict[str, ComputerUseSession] = {}
        self.ui_elements: Dict[str, UIElement] = {}

        # Statistics
        self.stats = {
            "total_sessions": 0,
            "total_actions": 0,
            "total_screenshots": 0,
            "successful_actions": 0,
            "failed_actions": 0,
        }

    def start_session(self, task_description: str) -> str:
        """
        Start a new computer-use session.

        Args:
            task_description: Description of the task

        Returns:
            Session ID
        """
        session_id = f"session_{len(self.sessions):06d}"

        session = ComputerUseSession(
            session_id=session_id,
            task_description=task_description,
            start_time=datetime.now().isoformat(),
        )

        self.sessions[session_id] = session
        self.stats["total_sessions"] += 1

        return session_id

    def detect_ui_elements(
        self,
        screenshot: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[UIElement]:
        """
        Detect UI elements in a screenshot.

        Args:
            screenshot: Screenshot content (base64 or path)
            context: Additional context

        Returns:
            List of detected UI elements
        """
        # Placeholder for actual UI detection
        # In production, this would use computer vision or accessibility APIs
        elements = []

        # Simulate detecting some common UI elements
        element_types = ["button", "input", "link", "text"]

        for i, elem_type in enumerate(element_types):
            element = UIElement(
                element_id=f"elem_{len(self.ui_elements):06d}",
                element_type=elem_type,
                text=f"Sample {elem_type}",
                position={"x": 100 * i, "y": 100, "width": 80, "height": 30},
            )
            elements.append(element)
            self.ui_elements[element.element_id] = element

        return elements

    def record_action(
        self,
        session_id: str,
        action_type: ActionType,
        target_element: Optional[UIElement] = None,
        input_value: Optional[str] = None,
        screenshot_before: Optional[str] = None,
        screenshot_after: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> str:
        """
        Record a UI action.

        Args:
            session_id: Session ID
            action_type: Type of action
            target_element: Target UI element
            input_value: Input value (for type actions)
            screenshot_before: Screenshot before action
            screenshot_after: Screenshot after action
            success: Whether action succeeded
            error: Error message if failed

        Returns:
            Action ID
        """
        if session_id not in self.sessions:
            return ""

        session = self.sessions[session_id]

        action = UIAction(
            action_id=f"{session_id}_action_{len(session.actions):04d}",
            action_type=action_type,
            timestamp=datetime.now().isoformat(),
            target_element=target_element,
            input_value=input_value,
            screenshot_before=screenshot_before,
            screenshot_after=screenshot_after,
            success=success,
            error=error,
        )

        session.actions.append(action)

        # Update statistics
        self.stats["total_actions"] += 1
        if success:
            self.stats["successful_actions"] += 1
        else:
            self.stats["failed_actions"] += 1

        # Track screenshots
        if screenshot_before:
            session.screenshots.append(screenshot_before)
            self.stats["total_screenshots"] += 1

        if screenshot_after:
            session.screenshots.append(screenshot_after)
            self.stats["total_screenshots"] += 1

        return action.action_id

    def end_session(self, session_id: str, status: str = "success"):
        """
        End a computer-use session.

        Args:
            session_id: Session to end
            status: Final status
        """
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]
        session.end_time = datetime.now().isoformat()
        session.final_status = status

    def get_session(self, session_id: str) -> Optional[ComputerUseSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    def get_action_sequence(self, session_id: str) -> List[UIAction]:
        """
        Get the action sequence for a session.

        Args:
            session_id: Session ID

        Returns:
            List of actions in order
        """
        session = self.get_session(session_id)
        if not session:
            return []

        return session.actions

    def export_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a session in JSON format.

        Args:
            session_id: Session to export

        Returns:
            Session data
        """
        session = self.get_session(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "task_description": session.task_description,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "final_status": session.final_status,
            "action_count": len(session.actions),
            "screenshot_count": len(session.screenshots),
            "actions": [
                {
                    "action_id": action.action_id,
                    "action_type": action.action_type.value,
                    "timestamp": action.timestamp,
                    "target_element": {
                        "element_id": action.target_element.element_id,
                        "element_type": action.target_element.element_type,
                        "text": action.target_element.text,
                        "position": action.target_element.position,
                    } if action.target_element else None,
                    "input_value": action.input_value,
                    "success": action.success,
                    "error": action.error,
                }
                for action in session.actions
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get computer-use statistics."""
        success_rate = (
            self.stats["successful_actions"] / self.stats["total_actions"]
            if self.stats["total_actions"] > 0
            else 0.0
        )

        return {
            **self.stats,
            "success_rate": success_rate,
            "num_sessions": len(self.sessions),
        }
