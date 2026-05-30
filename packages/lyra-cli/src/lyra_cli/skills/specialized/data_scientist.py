"""
Data Scientist Skill - Data science project planning and analysis.

Given a data science problem, produces:
- Data exploration plan
- Feature engineering strategy
- Model selection recommendations
- Validation strategy
- Deployment pipeline

Outputs structured data science plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProblemType(StrEnum):
    """Types of data science problems."""

    SUPERVISED_CLASSIFICATION = "supervised_classification"
    SUPERVISED_REGRESSION = "supervised_regression"
    UNSUPERVISED_CLUSTERING = "unsupervised_clustering"
    DIMENSIONALITY_REDUCTION = "dimensionality_reduction"
    ANOMALY_DETECTION = "anomaly_detection"
    TIME_SERIES_FORECASTING = "time_series_forecasting"
    RECOMMENDATION = "recommendation"


class DataQualityIssue(StrEnum):
    """Common data quality issues."""

    MISSING_VALUES = "missing_values"
    OUTLIERS = "outliers"
    DUPLICATES = "duplicates"
    IMBALANCED_CLASSES = "imbalanced_classes"
    HIGH_CARDINALITY = "high_cardinality"
    DATA_LEAKAGE = "data_leakage"


@dataclass(frozen=True)
class ExplorationStep:
    """A data exploration step."""

    step_name: str
    description: str
    tools: tuple[str, ...]
    expected_insights: tuple[str, ...]


@dataclass(frozen=True)
class FeatureEngineering:
    """Feature engineering strategy."""

    techniques: tuple[str, ...]
    feature_selection_method: str
    dimensionality_target: str
    validation_approach: str


@dataclass(frozen=True)
class ModelRecommendation:
    """A model recommendation."""

    model_name: str
    rationale: str
    pros: tuple[str, ...]
    cons: tuple[str, ...]
    hyperparameters_to_tune: tuple[str, ...]


@dataclass(frozen=True)
class ValidationStrategy:
    """Model validation strategy."""

    split_strategy: str
    cross_validation: str
    metrics: tuple[str, ...]
    baseline_models: tuple[str, ...]


@dataclass(frozen=True)
class DeploymentPipeline:
    """Deployment pipeline design."""

    serving_method: str
    monitoring_metrics: tuple[str, ...]
    retraining_trigger: str
    rollback_strategy: str


@dataclass(frozen=True)
class DataSciencePlan:
    """Complete data science project plan."""

    project_name: str
    problem_type: ProblemType
    exploration_plan: tuple[ExplorationStep, ...]
    data_quality_checks: tuple[DataQualityIssue, ...]
    feature_engineering: FeatureEngineering
    model_recommendations: tuple[ModelRecommendation, ...]
    validation_strategy: ValidationStrategy
    deployment_pipeline: DeploymentPipeline
    timeline: tuple[tuple[str, str], ...]
    success_criteria: tuple[str, ...]


class DataScientist:
    """Data science planning skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run data science planning.

        Args:
            input_data: Dictionary with keys:
                - problem_description: Description of the data science problem
                - project_name: Optional project name (default "DS Project")
                - problem_type: Optional problem type (default "supervised_classification")

        Returns:
            Dictionary with data science plan data.
        """
        description = input_data.get("problem_description", "")
        if not description:
            return {"error": "No problem description provided"}

        project_name = input_data.get("project_name", "DS Project")
        type_str = input_data.get("problem_type", "supervised_classification").lower()

        try:
            problem_type = ProblemType(type_str)
        except ValueError:
            problem_type = ProblemType.SUPERVISED_CLASSIFICATION

        desc_lower = description.lower()

        exploration = self._plan_exploration(problem_type)
        quality_checks = self._identify_quality_checks(desc_lower)
        feature_eng = self._plan_feature_engineering(problem_type)
        models = self._recommend_models(problem_type)
        validation = self._design_validation(problem_type)
        deployment = self._design_deployment(problem_type)
        timeline = self._build_timeline()
        success = self._define_success_criteria(problem_type)

        return DataSciencePlan(
            project_name=project_name,
            problem_type=problem_type,
            exploration_plan=tuple(exploration),
            data_quality_checks=tuple(quality_checks),
            feature_engineering=feature_eng,
            model_recommendations=tuple(models),
            validation_strategy=validation,
            deployment_pipeline=deployment,
            timeline=tuple(timeline),
            success_criteria=tuple(success),
        ).__dict__ | {
            "exploration_plan": [e.__dict__ for e in exploration],
            "feature_engineering": feature_eng.__dict__,
            "model_recommendations": [m.__dict__ for m in models],
            "validation_strategy": validation.__dict__,
            "deployment_pipeline": deployment.__dict__,
        }

    @staticmethod
    def _plan_exploration(problem_type: ProblemType) -> list[ExplorationStep]:
        return [
            ExplorationStep(
                step_name="Data Profiling",
                description="Generate statistical summary and data types",
                tools=("pandas.describe()", "pandas.info()", "ydata-profiling"),
                expected_insights=(
                    "Data shape and size",
                    "Column types and distributions",
                    "Missing value patterns",
                ),
            ),
            ExplorationStep(
                step_name="Univariate Analysis",
                description="Analyze each feature independently",
                tools=("matplotlib", "seaborn", "plotly"),
                expected_insights=(
                    "Distribution shapes (normal, skewed, bimodal)",
                    "Outlier detection",
                    "Cardinality of categorical features",
                ),
            ),
            ExplorationStep(
                step_name="Bivariate Analysis",
                description="Analyze relationships between features and target",
                tools=("seaborn.pairplot", "correlation matrix", "chi-square tests"),
                expected_insights=(
                    "Feature-target correlations",
                    "Multicollinearity detection",
                    "Feature importance hints",
                ),
            ),
        ]

    @staticmethod
    def _identify_quality_checks(description: str) -> list[DataQualityIssue]:
        checks = [
            DataQualityIssue.MISSING_VALUES,
            DataQualityIssue.OUTLIERS,
            DataQualityIssue.DUPLICATES,
        ]

        if "imbalanced" in description or "rare" in description:
            checks.append(DataQualityIssue.IMBALANCED_CLASSES)

        if "categorical" in description or "high cardinality" in description:
            checks.append(DataQualityIssue.HIGH_CARDINALITY)

        checks.append(DataQualityIssue.DATA_LEAKAGE)

        return checks

    @staticmethod
    def _plan_feature_engineering(problem_type: ProblemType) -> FeatureEngineering:
        if problem_type == ProblemType.TIME_SERIES_FORECASTING:
            techniques = (
                "Lag features (t-1, t-7, t-30)",
                "Rolling statistics (mean, std, min, max)",
                "Date/time features (day of week, month, season)",
            )
        else:
            techniques = (
                "One-hot encoding for categorical features",
                "Scaling/normalization for numerical features",
                "Polynomial features for non-linear relationships",
            )

        return FeatureEngineering(
            techniques=techniques,
            feature_selection_method="Recursive Feature Elimination (RFE)",
            dimensionality_target="Top 80% of cumulative feature importance",
            validation_approach="Cross-validated feature selection",
        )

    @staticmethod
    def _recommend_models(problem_type: ProblemType) -> list[ModelRecommendation]:
        if problem_type == ProblemType.SUPERVISED_CLASSIFICATION:
            return [
                ModelRecommendation(
                    model_name="Gradient Boosting (XGBoost/LightGBM)",
                    rationale="Strong performance on tabular data",
                    pros=("Handles mixed data types", "Built-in feature importance"),
                    cons=("Can overfit on small datasets",),
                    hyperparameters_to_tune=("learning_rate", "max_depth", "n_estimators"),
                ),
                ModelRecommendation(
                    model_name="Random Forest",
                    rationale="Robust baseline with good interpretability",
                    pros=("Less prone to overfitting", "Handles non-linear relationships"),
                    cons=("Can be memory-intensive",),
                    hyperparameters_to_tune=("n_estimators", "max_depth"),
                ),
            ]
        else:
            return [
                ModelRecommendation(
                    model_name="Domain-Specific Model",
                    rationale="Select based on problem type",
                    pros=("TBD",),
                    cons=("TBD",),
                    hyperparameters_to_tune=("TBD",),
                ),
            ]

    @staticmethod
    def _design_validation(problem_type: ProblemType) -> ValidationStrategy:
        if problem_type == ProblemType.TIME_SERIES_FORECASTING:
            split = "Time-based split (train on past, validate on future)"
            cv = "Time series cross-validation (expanding window)"
            metrics = ("RMSE", "MAE", "MAPE")
        else:
            split = "Stratified train/validation/test split (70/15/15)"
            cv = "5-fold stratified cross-validation"
            metrics = ("Accuracy", "F1 Score", "Precision", "Recall")

        return ValidationStrategy(
            split_strategy=split,
            cross_validation=cv,
            metrics=metrics,
            baseline_models=("Random baseline", "Simple heuristic"),
        )

    @staticmethod
    def _design_deployment(problem_type: ProblemType) -> DeploymentPipeline:
        return DeploymentPipeline(
            serving_method="REST API (Flask/FastAPI) or batch prediction",
            monitoring_metrics=(
                "Prediction latency (p50, p95, p99)",
                "Model performance (online metrics)",
                "Data drift detection",
            ),
            retraining_trigger="Performance degradation > 5% OR monthly schedule",
            rollback_strategy="Blue-green deployment with automated rollback",
        )

    @staticmethod
    def _build_timeline() -> list[tuple[str, str]]:
        return [
            ("Week 1", "Data exploration and quality assessment"),
            ("Week 2", "Feature engineering and selection"),
            ("Week 3-4", "Model training and hyperparameter tuning"),
            ("Week 5", "Model validation and error analysis"),
            ("Week 6", "Deployment pipeline setup"),
        ]

    @staticmethod
    def _define_success_criteria(problem_type: ProblemType) -> list[str]:
        if problem_type == ProblemType.SUPERVISED_CLASSIFICATION:
            return [
                "Model accuracy > 85% on test set",
                "F1 score > 0.80 for all classes",
                "Inference latency < 100ms (p95)",
            ]
        else:
            return [
                "Primary metric exceeds baseline by 15%+",
                "Model passes validation on holdout set",
            ]
