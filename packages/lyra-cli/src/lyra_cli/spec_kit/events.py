"""AgentEvent extensions for Auto-Spec-Kit."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal


@dataclass
class SpecDetectorRan:
    """Emitted when detector classifies a prompt."""
    kind: Literal["spec_detector_ran"] = "spec_detector_ran"
    verdict: dict | None = None


@dataclass
class SpecPhaseChanged:
    """Emitted when spec-kit phase transitions."""
    kind: Literal["spec_phase_changed"] = "spec_phase_changed"
    old_phase: str = ""
    new_phase: str = ""


@dataclass
class SpecDraftChunk:
    """Emitted when streaming draft content."""
    kind: Literal["spec_draft_chunk"] = "spec_draft_chunk"
    artifact: Literal["spec", "plan", "tasks", "constitution"] = "spec"
    chunk: str = ""


@dataclass
class SpecApprovalRequested:
    """Emitted when draft is ready for approval."""
    kind: Literal["spec_approval_requested"] = "spec_approval_requested"
    artifact: str = ""
    full_text: str = ""


@dataclass
class SpecApprovalResolved:
    """Emitted when user approves/rejects/edits."""
    kind: Literal["spec_approval_resolved"] = "spec_approval_resolved"
    artifact: str = ""
    approved: bool = False
    edits: str | None = None


@dataclass
class SpecFilesWritten:
    """Emitted when files are written to disk."""
    kind: Literal["spec_files_written"] = "spec_files_written"
    feature_id: str = ""
    paths: list[str] | None = None
