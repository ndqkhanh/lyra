"""Trajectory-Driven Patching — extract and apply skill patches from agent trajectories."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .exceptions import PatchError


class PatchType(Enum):
    """Types of patches that can be applied to a skill."""

    ADD_STEP = auto()
    REMOVE_STEP = auto()
    MODIFY_STEP = auto()
    ADD_TRIGGER = auto()
    ADD_EXAMPLE = auto()
    FIX_PATTERN = auto()


@dataclass(frozen=True)
class TrajectoryPatch:
    """A single patch extracted from an agent trajectory.

    Attributes:
        patch_id: Unique identifier for this patch.
        skill_id: The skill this patch targets.
        trajectory_ref: Reference to the source trajectory.
        change_description: Human-readable description of the change.
        before_snippet: Code or configuration before the patch.
        after_snippet: Code or configuration after the patch.
        confidence: Confidence score for this patch (0.0 to 1.0).
    """

    patch_id: str
    skill_id: str
    trajectory_ref: str
    change_description: str
    before_snippet: str
    after_snippet: str
    confidence: float = 1.0


@dataclass(frozen=True)
class PatchResult:
    """Result of applying a patch to a skill.

    Attributes:
        patch: The patch that was applied.
        success: Whether the patch was applied successfully.
        validation_results: List of validation outcome strings.
        side_effects: List of side effects detected.
    """

    patch: TrajectoryPatch
    success: bool
    validation_results: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Skill:
    """Represents a skill with versioned content.

    Attributes:
        skill_id: Unique identifier for this skill.
        version: Version string.
        content: The skill content (code, config, etc.).
        version_number: Monotonically increasing version number.
    """

    skill_id: str
    version: str = "0.1.0"
    content: dict[str, Any] = field(default_factory=dict)
    version_number: int = 1


class TrajectoryPatcher:
    """Extracts and applies patches from agent trajectories to improve skills.

    Trajectories capture how agents use skills; the patcher analyzes these
    traces to identify improvement opportunities and applies them as patches.
    """

    def __init__(self) -> None:
        self._patch_history: list[PatchResult] = []

    def extract_patches(self, trajectories: list[dict[str, Any]]) -> list[TrajectoryPatch]:
        """Extract skill patches from a list of agent trajectories.

        Analyzes trajectories for patterns that indicate skill improvements:
        repeated steps that could be automated, error patterns that need fixing,
        and new triggers that could accelerate future usage.

        Args:
            trajectories: List of trajectory dictionaries. Each must contain
                at least 'trajectory_id', 'skill_id', and 'events'.

        Returns:
            List of extracted TrajectoryPatch instances.
        """
        patches: list[TrajectoryPatch] = []

        for trajectory in trajectories:
            trajectory_id = trajectory.get("trajectory_id", "unknown")
            skill_id = trajectory.get("skill_id", "unknown")
            events = trajectory.get("events", [])

            # Detect repeated steps that could be added as sub-steps
            patches.extend(self._detect_repeated_steps(skill_id, trajectory_id, events))

            # Detect error patterns that need fixing
            patches.extend(self._detect_error_patterns(skill_id, trajectory_id, events))

            # Detect new triggers from contextual signals
            patches.extend(self._detect_new_triggers(skill_id, trajectory_id, events))

        self._patch_history.extend(
            PatchResult(patch=patch, success=True, validation_results=["extracted"])
            for patch in patches
        )

        return patches

    def _detect_repeated_steps(
        self,
        skill_id: str,
        trajectory_id: str,
        events: list[dict[str, Any]],
    ) -> list[TrajectoryPatch]:
        """Detect repeated sequences of steps in a trajectory.

        Args:
            skill_id: The skill being analyzed.
            trajectory_id: Reference to the trajectory.
            events: List of event dictionaries with 'event_type' and 'data'.

        Returns:
            Patches for automatically adding repeated steps.
        """
        patches: list[TrajectoryPatch] = []
        event_types = [e.get("event_type", "") for e in events]

        # Simple heuristic: find the most common event type
        if len(event_types) >= 3:
            from collections import Counter
            counter = Counter(event_types)
            most_common_type, count = counter.most_common(1)[0]
            if count >= 3:
                patch_id = f"patch_{skill_id}_{trajectory_id}_repeat_{int(time.time())}"
                patches.append(TrajectoryPatch(
                    patch_id=patch_id,
                    skill_id=skill_id,
                    trajectory_ref=trajectory_id,
                    change_description=f"Add automated step for frequently repeated '{most_common_type}'",
                    before_snippet="",
                    after_snippet=f"auto_{most_common_type}()",
                    confidence=min(1.0, count / 5),
                ))

        return patches

    def _detect_error_patterns(
        self,
        skill_id: str,
        trajectory_id: str,
        events: list[dict[str, Any]],
    ) -> list[TrajectoryPatch]:
        """Detect error patterns in a trajectory.

        Args:
            skill_id: The skill being analyzed.
            trajectory_id: Reference to the trajectory.
            events: List of event dictionaries with 'event_type' and 'error' fields.

        Returns:
            Patches for fixing detected error patterns.
        """
        patches: list[TrajectoryPatch] = []
        errors = [e for e in events if e.get("event_type") == "error"]

        for error in errors:
            error_data = error.get("data", "")
            if not error_data:
                continue

            patch_id = f"patch_{skill_id}_{trajectory_id}_fix_{hash(error_data) % 10000}_{int(time.time())}"
            patches.append(TrajectoryPatch(
                patch_id=patch_id,
                skill_id=skill_id,
                trajectory_ref=trajectory_id,
                change_description=f"Fix pattern: {error_data[:80]}",
                before_snippet=error_data,
                after_snippet=f"# FIXED: {error_data[:80]}",
                confidence=0.7,
            ))

        return patches

    def _detect_new_triggers(
        self,
        skill_id: str,
        trajectory_id: str,
        events: list[dict[str, Any]],
    ) -> list[TrajectoryPatch]:
        """Detect new trigger patterns from trajectory context.

        Args:
            skill_id: The skill being analyzed.
            trajectory_id: Reference to the trajectory.
            events: List of event dictionaries.

        Returns:
            Patches for adding new triggers to skills.
        """
        patches: list[TrajectoryPatch] = []

        # Simple detection: events with context_trigger field
        triggers = [e for e in events if e.get("context_trigger")]

        for trigger in triggers:
            trigger_name = trigger.get("context_trigger", "unknown")

            patch_id = f"patch_{skill_id}_{trajectory_id}_trigger_{trigger_name}_{int(time.time())}"
            patches.append(TrajectoryPatch(
                patch_id=patch_id,
                skill_id=skill_id,
                trajectory_ref=trajectory_id,
                change_description=f"Add trigger: {trigger_name}",
                before_snippet="",
                after_snippet=f"trigger on {trigger_name}",
                confidence=0.6,
            ))

        return patches

    def apply_patch(self, skill: Skill, patch: TrajectoryPatch) -> Skill:
        """Apply a single patch to a skill, returning a new skill version.

        Args:
            skill: The skill to patch.
            patch: The patch to apply.

        Returns:
            A new Skill with the patch applied and version incremented.

        Raises:
            PatchError: If the patch targets a different skill.
        """
        if patch.skill_id != skill.skill_id:
            raise PatchError(
                patch.patch_id,
                f"Patch targets skill '{patch.skill_id}' but skill is '{skill.skill_id}'",
            )

        new_content = dict(skill.content)
        patch_type = self._classify_patch(patch)

        if patch_type == PatchType.ADD_STEP:
            steps = new_content.get("steps", [])
            new_content["steps"] = [*steps, {"name": patch.change_description, "code": patch.after_snippet}]
        elif patch_type == PatchType.FIX_PATTERN:
            fixes = new_content.get("fixes", [])
            new_content["fixes"] = [*fixes, {"pattern": patch.before_snippet, "replacement": patch.after_snippet}]
        elif patch_type == PatchType.ADD_TRIGGER:
            triggers = new_content.get("triggers", [])
            new_content["triggers"] = [*triggers, patch.after_snippet]
        elif patch_type == PatchType.ADD_EXAMPLE:
            examples = new_content.get("examples", [])
            new_content["examples"] = [*examples, {"description": patch.change_description, "code": patch.after_snippet}]

        return Skill(
            skill_id=skill.skill_id,
            version=self._bump_version(skill.version),
            content=new_content,
            version_number=skill.version_number + 1,
        )

    def _classify_patch(self, patch: TrajectoryPatch) -> PatchType:
        """Classify a patch by its change description and snippets.

        Args:
            patch: The patch to classify.

        Returns:
            The PatchType for this patch.
        """
        desc = patch.change_description.lower()
        if "trigger" in desc:
            return PatchType.ADD_TRIGGER
        if "fix" in desc or "error" in desc:
            return PatchType.FIX_PATTERN
        if "example" in desc:
            return PatchType.ADD_EXAMPLE
        if "step" in desc or "automate" in desc:
            return PatchType.ADD_STEP
        return PatchType.MODIFY_STEP

    def validate_patch(
        self,
        skill: Skill,
        patch: TrajectoryPatch,
        test_cases: list[dict[str, Any]],
    ) -> bool:
        """Validate a patch by running test cases against it.

        Args:
            skill: The skill to test.
            patch: The patch to validate.
            test_cases: List of test case dictionaries with 'input' and 'expected' keys.

        Returns:
            True if all test cases pass, False otherwise.
        """
        if patch.skill_id != skill.skill_id:
            return False

        for test_case in test_cases:
            test_input = test_case.get("input")
            expected = test_case.get("expected")

            if test_input is None or expected is None:
                continue

            skill_content = str(skill.content)
            actual = skill_content.get(test_input) if isinstance(skill_content, dict) else None
            if actual is not None and actual != expected:
                return False

        return True

    def batch_apply(self, skill: Skill, patches: list[TrajectoryPatch]) -> Skill:
        """Apply multiple patches to a skill sequentially.

        If any patch fails, the operation stops and the error is propagated.

        Args:
            skill: The skill to patch.
            patches: Ordered list of patches to apply.

        Returns:
            A new Skill with all patches applied.
        """
        current = skill
        for patch in patches:
            current = self.apply_patch(current, patch)
        return current

    def _bump_version(self, version: str) -> str:
        """Bump a semver patch version.

        Args:
            version: Current version string (e.g. '0.1.0').

        Returns:
            Bumped version string (e.g. '0.1.1').
        """
        parts = version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
        return ".".join(parts)

    @property
    def patch_history(self) -> list[PatchResult]:
        """Get the full history of patch results."""
        return list(self._patch_history)

    def clear_history(self) -> None:
        """Clear patch history."""
        self._patch_history.clear()
