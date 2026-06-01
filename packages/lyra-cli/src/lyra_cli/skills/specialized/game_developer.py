"""Game Developer Skill — game development patterns and optimization validation.

Analyzes game code for:
- Game loop and frame timing
- Physics and collision detection
- Asset management and loading
- Memory pooling and object reuse
- Input handling and responsiveness
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class GameSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GameCategory(StrEnum):
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    MEMORY = "memory"
    PHYSICS = "physics"
    ASSETS = "assets"


@dataclass(frozen=True)
class GameIssue:
    category: GameCategory
    severity: GameSeverity
    message: str
    suggestion: str
    line: int


class GameDeveloperSkill:
    """Analyzes game code for performance and architecture patterns."""

    def __init__(self) -> None:
        self._issues: list[GameIssue] = []

    def run(self, input_data: dict) -> dict:
        """Run game code analysis.

        Args:
            input_data: Dictionary with keys:
                - source: Source code string to analyze
                - engine: Game engine (unity, unreal, godot, custom)
                - target_fps: Target frame rate (default 60)

        Returns:
            Dictionary with analysis report data.
        """
        source = input_data.get("source", "")
        engine = input_data.get("engine", "custom")
        target_fps = input_data.get("target_fps", 60)

        self._issues.clear()

        self._check_game_loop(source, target_fps)
        self._check_memory_management(source, engine)
        self._check_physics(source)
        self._check_asset_management(source)
        self._check_input_handling(source)
        self._check_performance_patterns(source, engine)

        score = self._compute_score()

        return {
            "engine": engine,
            "target_fps": target_fps,
            "issues": [i.__dict__ for i in self._issues],
            "score": score,
            "total_issues": len(self._issues),
        }

    def _check_game_loop(self, source: str, target_fps: int) -> None:
        """Check game loop implementation."""
        has_update = "Update(" in source or "update(" in source or "_process(" in source
        has_fixed_update = "FixedUpdate(" in source or "fixed_update(" in source

        if not has_update:
            self._issues.append(
                GameIssue(
                    category=GameCategory.ARCHITECTURE,
                    severity=GameSeverity.CRITICAL,
                    message="No game loop update method detected",
                    suggestion="Implement Update() or equivalent game loop method",
                    line=0,
                )
            )

        # Check for frame-rate dependent code
        if "Time.deltaTime" not in source and "delta" not in source.lower() and has_update:
            self._issues.append(
                GameIssue(
                    category=GameCategory.PERFORMANCE,
                    severity=GameSeverity.HIGH,
                    message="No delta time usage detected - frame-rate dependent movement",
                    suggestion="Multiply movement by deltaTime for frame-rate independence",
                    line=0,
                )
            )

        # Check for physics in Update instead of FixedUpdate
        if has_update and not has_fixed_update and "Rigidbody" in source:
            self._issues.append(
                GameIssue(
                    category=GameCategory.PHYSICS,
                    severity=GameSeverity.HIGH,
                    message="Physics code in Update() instead of FixedUpdate()",
                    suggestion="Move physics calculations to FixedUpdate() for stability",
                    line=0,
                )
            )

    def _check_memory_management(self, source: str, engine: str) -> None:
        """Check memory management patterns."""
        # Check for object pooling
        has_instantiate = "Instantiate(" in source or "new " in source
        has_destroy = "Destroy(" in source or "delete " in source
        has_pool = "pool" in source.lower() or "ObjectPool" in source

        if has_instantiate and has_destroy and not has_pool:
            count = source.count("Instantiate(") + source.count("new ")
            if count > 5:
                self._issues.append(
                    GameIssue(
                        category=GameCategory.MEMORY,
                        severity=GameSeverity.HIGH,
                        message=f"Frequent object creation/destruction ({count} instances) without pooling",
                        suggestion="Implement object pooling for frequently spawned objects",
                        line=0,
                    )
                )

        # Check for string concatenation in Update
        if re.search(r'(Update|update|_process).*\+.*"', source):
            self._issues.append(
                GameIssue(
                    category=GameCategory.MEMORY,
                    severity=GameSeverity.MEDIUM,
                    message="String concatenation in game loop causes GC pressure",
                    suggestion="Use StringBuilder or cache strings outside the loop",
                    line=0,
                )
            )

        # Check for GetComponent in Update
        if "Update(" in source and "GetComponent" in source:
            self._issues.append(
                GameIssue(
                    category=GameCategory.PERFORMANCE,
                    severity=GameSeverity.HIGH,
                    message="GetComponent() called in Update() - expensive operation",
                    suggestion="Cache component references in Start() or Awake()",
                    line=0,
                )
            )

    def _check_physics(self, source: str) -> None:
        """Check physics implementation."""
        # Check for raycasts in Update
        if "Update(" in source and "Raycast" in source:
            count = source.count("Raycast")
            if count > 3:
                self._issues.append(
                    GameIssue(
                        category=GameCategory.PHYSICS,
                        severity=GameSeverity.MEDIUM,
                        message=f"Multiple raycasts ({count}) in Update() - performance impact",
                        suggestion="Limit raycasts or use physics layers to reduce checks",
                        line=0,
                    )
                )

        # Check for collision detection optimization
        has_collision = "OnCollision" in source or "OnTrigger" in source
        has_layers = "layer" in source.lower() or "LayerMask" in source

        if has_collision and not has_layers:
            self._issues.append(
                GameIssue(
                    category=GameCategory.PHYSICS,
                    severity=GameSeverity.MEDIUM,
                    message="Collision detection without layer filtering",
                    suggestion="Use physics layers to reduce unnecessary collision checks",
                    line=0,
                )
            )

    def _check_asset_management(self, source: str) -> None:
        """Check asset loading and management."""
        # Check for synchronous loading
        has_load = "Resources.Load" in source or "load(" in source.lower()
        has_async_load = "LoadAsync" in source or "async" in source.lower()

        if has_load and not has_async_load:
            self._issues.append(
                GameIssue(
                    category=GameCategory.ASSETS,
                    severity=GameSeverity.HIGH,
                    message="Synchronous asset loading can cause frame drops",
                    suggestion="Use async loading (LoadAsync, Addressables) for large assets",
                    line=0,
                )
            )

        # Check for texture/mesh optimization
        if "Texture" in source and "compression" not in source.lower():
            self._issues.append(
                GameIssue(
                    category=GameCategory.ASSETS,
                    severity=GameSeverity.MEDIUM,
                    message="No texture compression settings detected",
                    suggestion="Enable texture compression for target platforms",
                    line=0,
                )
            )

        # Check for asset unloading
        if has_load and "Unload" not in source and "Resources.UnloadUnusedAssets" not in source:
            self._issues.append(
                GameIssue(
                    category=GameCategory.MEMORY,
                    severity=GameSeverity.MEDIUM,
                    message="Assets loaded but never unloaded",
                    suggestion="Unload unused assets to free memory",
                    line=0,
                )
            )

    def _check_input_handling(self, source: str) -> None:
        """Check input handling patterns."""
        # Check for input in Update
        has_input = "Input.Get" in source or "input" in source.lower()
        has_input_system = "InputSystem" in source or "InputAction" in source

        if has_input and not has_input_system and "Update(" in source:
            self._issues.append(
                GameIssue(
                    category=GameCategory.ARCHITECTURE,
                    severity=GameSeverity.LOW,
                    message="Using legacy Input system",
                    suggestion="Consider migrating to new Input System for better flexibility",
                    line=0,
                )
            )

        # Check for input buffering
        if has_input and "buffer" not in source.lower() and "queue" not in source.lower():
            self._issues.append(
                GameIssue(
                    category=GameCategory.ARCHITECTURE,
                    severity=GameSeverity.LOW,
                    message="No input buffering detected",
                    suggestion="Implement input buffering for responsive controls",
                    line=0,
                )
            )

    def _check_performance_patterns(self, source: str, engine: str) -> None:
        """Check general performance patterns."""
        # Check for Find operations
        if "Find(" in source or "FindObjectOfType" in source:
            count = source.count("Find(") + source.count("FindObjectOfType")
            if count > 2:
                self._issues.append(
                    GameIssue(
                        category=GameCategory.PERFORMANCE,
                        severity=GameSeverity.HIGH,
                        message=f"Frequent use of Find operations ({count} calls) - very expensive",
                        suggestion="Cache references or use singleton pattern instead of Find",
                        line=0,
                    )
                )

        # Check for camera.main in Update
        if "Update(" in source and "Camera.main" in source:
            self._issues.append(
                GameIssue(
                    category=GameCategory.PERFORMANCE,
                    severity=GameSeverity.MEDIUM,
                    message="Camera.main accessed in Update() - uses FindGameObjectWithTag",
                    suggestion="Cache Camera.main reference in Start()",
                    line=0,
                )
            )

        # Check for SendMessage
        if "SendMessage" in source or "BroadcastMessage" in source:
            self._issues.append(
                GameIssue(
                    category=GameCategory.PERFORMANCE,
                    severity=GameSeverity.HIGH,
                    message="SendMessage/BroadcastMessage is slow - uses reflection",
                    suggestion="Use direct method calls, events, or UnityEvents instead",
                    line=0,
                )
            )

        # Check for LINQ in Update
        if "Update(" in source and re.search(r"\.(Where|Select|First|Any)\(", source):
            self._issues.append(
                GameIssue(
                    category=GameCategory.PERFORMANCE,
                    severity=GameSeverity.MEDIUM,
                    message="LINQ operations in Update() cause GC allocations",
                    suggestion="Use for loops or cache LINQ results outside Update()",
                    line=0,
                )
            )

    def _compute_score(self) -> int:
        """Compute overall game code quality score (0-100)."""
        return max(
            0,
            100
            - len([i for i in self._issues if i.severity == GameSeverity.CRITICAL]) * 25
            - len([i for i in self._issues if i.severity == GameSeverity.HIGH]) * 15
            - len([i for i in self._issues if i.severity == GameSeverity.MEDIUM]) * 8
            - len([i for i in self._issues if i.severity == GameSeverity.LOW]) * 3,
        )
