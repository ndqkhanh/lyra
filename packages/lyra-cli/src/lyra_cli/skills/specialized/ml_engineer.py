"""Machine Learning Engineer Skill — ML pipeline design and model lifecycle management.

Validates ML pipelines for:
- Data leakage prevention
- Train/test split integrity
- Feature engineering best practices
- Model evaluation and monitoring
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MLRiskLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class MLFinding:
    stage: str
    risk: MLRiskLevel
    description: str
    recommendation: str


class MLEngineerSkill:
    """Validates ML pipeline designs for common pitfalls."""

    def run(self, input_data: dict) -> dict:
        pipeline = input_data.get("pipeline", {})
        stages = pipeline.get("stages", [])
        findings: list[MLFinding] = []

        stage_names = {s.get("name", "").lower() for s in stages}

        if "data_split" not in stage_names and "train_test_split" not in stage_names:
            findings.append(MLFinding("data_prep", MLRiskLevel.HIGH,
                "No train/test split stage defined — risk of data leakage.",
                "Add explicit train/test/validation split before model training."))

        if "feature_engineering" not in stage_names:
            findings.append(MLFinding("features", MLRiskLevel.MEDIUM,
                "No explicit feature engineering stage.",
                "Add feature selection, scaling, and encoding stages."))

        if "evaluation" not in stage_names and "validate" not in stage_names:
            findings.append(MLFinding("evaluation", MLRiskLevel.HIGH,
                "No model evaluation stage — can't assess model quality.",
                "Add evaluation with appropriate metrics (accuracy, F1, RMSE, etc.)."))

        if "monitoring" not in stage_names:
            findings.append(MLFinding("production", MLRiskLevel.MEDIUM,
                "No model monitoring stage — can't detect drift or degradation.",
                "Add monitoring for prediction drift, feature drift, and latency."))

        if "retraining" not in stage_names:
            findings.append(MLFinding("production", MLRiskLevel.LOW,
                "No automated retraining pipeline defined.",
                "Add scheduled or trigger-based retraining pipeline."))

        score = max(0, 100
            - len([f for f in findings if f.risk == MLRiskLevel.HIGH]) * 20
            - len([f for f in findings if f.risk == MLRiskLevel.MEDIUM]) * 10
            - len([f for f in findings if f.risk == MLRiskLevel.LOW]) * 5)

        return {
            "findings": [f.__dict__ for f in findings],
            "score": score,
            "total_findings": len(findings),
            "passed": len([f for f in findings if f.risk == MLRiskLevel.HIGH]) == 0,
        }
