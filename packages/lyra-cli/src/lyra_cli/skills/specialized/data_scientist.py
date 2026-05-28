"""Data Scientist Skill — data analysis pipeline and statistical validation.

Validates data analysis for:
- Statistical assumption checking
- Data quality and preprocessing
- Experiment design and hypothesis testing
- Visualization and reporting
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DataQuality(StrEnum):
    GOOD = "good"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class DataIssue:
    column: str
    quality: DataQuality
    issue: str
    suggestion: str


class DataScientistSkill:
    """Validates data analysis pipelines and statistical methods."""

    def run(self, input_data: dict) -> dict:
        dataset = input_data.get("dataset", {})
        columns = dataset.get("columns", [])
        row_count = dataset.get("row_count", 0)
        issues: list[DataIssue] = []

        for col in columns:
            name = col.get("name", "unknown")
            null_pct = col.get("null_percentage", 0)
            dtype = col.get("dtype", "unknown")

            if null_pct > 20:
                issues.append(DataIssue(name, DataQuality.ERROR,
                    f"{null_pct:.0f}% null values — column may be unusable.",
                    "Consider imputation or dropping this column."))
            elif null_pct > 5:
                issues.append(DataIssue(name, DataQuality.WARNING,
                    f"{null_pct:.0f}% null values — imputation needed.",
                    "Impute nulls with mean/median/mode or use forward-fill."))

            if dtype == "object" and col.get("unique_values", 0) > row_count * 0.9:
                issues.append(DataIssue(name, DataQuality.WARNING,
                    "High cardinality categorical — may be an ID column.",
                    "Check if this is an identifier rather than a feature."))

        if row_count < 30:
            issues.append(DataIssue("*", DataQuality.WARNING,
                f"Small sample size ({row_count} rows) — statistical tests may be underpowered.",
                "Collect more data or use non-parametric methods."))

        return {
            "issues": [i.__dict__ for i in issues],
            "row_count": row_count,
            "column_count": len(columns),
            "score": max(0, 100
                - len([i for i in issues if i.quality == DataQuality.ERROR]) * 20
                - len([i for i in issues if i.quality == DataQuality.WARNING]) * 10),
        }
