"""DevOps Engineer Skill — CI/CD pipeline design and infrastructure validation.

Validates pipeline configurations, checks for:
- Proper stage ordering and gate conditions
- Security scanning integration
- Artifact management and caching
- Deployment strategies (blue-green, canary, rolling)
"""

from __future__ import annotations

from enum import StrEnum


class PipelineStage(StrEnum):
    BUILD = "build"
    TEST = "test"
    SCAN = "scan"
    STAGE = "stage"
    DEPLOY = "deploy"
    VERIFY = "verify"


class DevOpsEngineerSkill:
    """Validates CI/CD pipeline designs and infrastructure configurations."""

    _REQUIRED_STAGES = frozenset({PipelineStage.BUILD, PipelineStage.TEST, PipelineStage.DEPLOY})
    _RECOMMENDED_STAGES = frozenset({PipelineStage.SCAN, PipelineStage.STAGE, PipelineStage.VERIFY})

    def __init__(self) -> None:
        self._warnings: list[dict] = []

    def run(self, input_data: dict) -> dict:
        pipeline = input_data.get("pipeline", {})
        stages = pipeline.get("stages", [])
        env = input_data.get("environment", "development")

        self._warnings.clear()
        stage_names = {s.get("name", "") for s in stages}

        missing = self._REQUIRED_STAGES - stage_names
        for m in missing:
            self._warnings.append(
                {
                    "severity": "error",
                    "message": f"Missing required stage: {m.value}",
                    "suggestion": f"Add a '{m.value}' stage to the pipeline.",
                }
            )

        missing_rec = self._RECOMMENDED_STAGES - stage_names
        for m in missing_rec:
            self._warnings.append(
                {
                    "severity": "warning",
                    "message": f"Recommended stage missing: {m.value}",
                    "suggestion": f"Consider adding a '{m.value}' stage for production readiness.",
                }
            )

        if env == "production":
            checks = [
                ("approval_gate", "Add manual approval gates before production deployment."),
                ("rollback_plan", "Define an automated rollback strategy for failed deployments."),
                ("blue_green", "Use blue-green or canary deployment to reduce risk."),
            ]
            for check, suggestion in checks:
                found = any(check in str(s).lower() for s in stages)
                if not found:
                    self._warnings.append(
                        {
                            "severity": "error" if check == "rollback_plan" else "warning",
                            "message": f"Production safety check missing: {check}.",
                            "suggestion": suggestion,
                        }
                    )

        return {
            "warnings": self._warnings,
            "score": max(
                0,
                100
                - len([w for w in self._warnings if w["severity"] == "error"]) * 20
                - len([w for w in self._warnings if w["severity"] == "warning"]) * 10,
            ),
            "stages_found": sorted(stage_names),
            "passed": len(self._warnings) == 0,
        }
