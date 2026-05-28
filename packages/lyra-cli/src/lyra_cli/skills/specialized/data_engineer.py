"""
Data Engineer Skill - Data engineering design and analysis.

Given data requirements, produces:
- ETL pipeline design
- Data model (star/snowflake schema)
- Data quality checks
- Pipeline monitoring suggestions
- Technology recommendations

Outputs structured data engineering plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DataSourceType(StrEnum):
    """Types of data sources."""

    DATABASE = "database"
    API = "api"
    FILE = "file"
    STREAM = "stream"
    QUEUE = "queue"
    OBJECT_STORE = "object_store"


class ProcessingMode(StrEnum):
    """Data processing modes."""

    BATCH = "batch"
    STREAMING = "streaming"
    MICRO_BATCH = "micro_batch"
    LAMBDA = "lambda_architecture"  # batch + streaming


class SchemaType(StrEnum):
    """Data modeling schema types."""

    STAR = "star_schema"
    SNOWFLAKE = "snowflake_schema"
    VAULT = "data_vault"
    ONE_BIG_TABLE = "one_big_table"


@dataclass(frozen=True)
class DataSource:
    """A data source in the pipeline."""

    name: str
    type: DataSourceType
    format: str
    volume_estimate: str
    latency_requirement: str
    connection_method: str


@dataclass(frozen=True)
class ETLStep:
    """A single step in the ETL pipeline."""

    step_number: int
    name: str
    description: str
    technology: str
    expected_duration: str
    error_handling: str


@dataclass(frozen=True)
class ETLPipeline:
    """Complete ETL pipeline design."""

    name: str
    mode: ProcessingMode
    sources: tuple[DataSource, ...]
    steps: tuple[ETLStep, ...]
    orchestration_tool: str
    total_estimated_duration: str


@dataclass(frozen=True)
class SchemaTable:
    """A table in the data model."""

    name: str
    type: str
    columns: tuple[tuple[str, str, str], ...]  # (name, type, description)
    primary_key: str
    foreign_keys: tuple[tuple[str, str], ...]  # (column, references)


@dataclass(frozen=True)
class DataModel:
    """Complete data model."""

    schema_type: SchemaType
    fact_tables: tuple[SchemaTable, ...]
    dimension_tables: tuple[SchemaTable, ...]
    ascii_diagram: str


@dataclass(frozen=True)
class DataQualityCheck:
    """A data quality check configuration."""

    check_name: str
    description: str
    severity: str
    frequency: str
    action_on_failure: str
    sql_template: str


@dataclass(frozen=True)
class PipelineMonitor:
    """A pipeline monitoring metric."""

    metric_name: str
    description: str
    alert_threshold: str
    dashboard_location: str
    retention_period: str


@dataclass(frozen=True)
class DataEngineeringPlan:
    """Complete data engineering plan."""

    project_name: str
    pipeline: ETLPipeline
    data_model: DataModel
    quality_checks: tuple[DataQualityCheck, ...]
    monitors: tuple[PipelineMonitor, ...]
    technology_recommendations: tuple[dict[str, str], ...]
    considerations: tuple[str, ...]


class DataEngineer:
    """Data engineering skill producing structured pipeline designs."""

    def run(self, input_data: dict) -> dict:
        """Run data engineering analysis.

        Args:
            input_data: Dictionary with keys:
                - requirements: Data requirements description
                - project_name: Optional project name (default "Data Pipeline")

        Returns:
            Dictionary with data engineering plan data.
        """
        requirements = input_data.get("requirements", "")
        if not requirements:
            return {"error": "No requirements provided"}

        project = input_data.get("project_name", "Data Pipeline")
        reqs_lower = requirements.lower()

        pipeline = self._design_pipeline(reqs_lower, project)
        data_model = self._design_data_model(reqs_lower, project)
        quality_checks = self._design_quality_checks(reqs_lower)
        monitors = self._design_monitors(reqs_lower)
        tech_recommendations = self._recommend_technology(reqs_lower)
        considerations = self._list_considerations(reqs_lower)

        return DataEngineeringPlan(
            project_name=project,
            pipeline=pipeline,
            data_model=data_model,
            quality_checks=tuple(quality_checks),
            monitors=tuple(monitors),
            technology_recommendations=tuple(tech_recommendations),
            considerations=tuple(considerations),
        ).__dict__ | {
            "pipeline": self._serialize_pipeline(pipeline),
            "data_model": self._serialize_data_model(data_model),
            "quality_checks": [q.__dict__ for q in quality_checks],
            "monitors": [m.__dict__ for m in monitors],
        }

    @staticmethod
    def _serialize_pipeline(pipeline: ETLPipeline) -> dict:
        return {
            "name": pipeline.name,
            "mode": pipeline.mode.value,
            "sources": [s.__dict__ for s in pipeline.sources],
            "steps": [s.__dict__ for s in pipeline.steps],
            "orchestration_tool": pipeline.orchestration_tool,
            "total_estimated_duration": pipeline.total_estimated_duration,
        }

    @staticmethod
    def _serialize_data_model(model: DataModel) -> dict:
        return {
            "schema_type": model.schema_type.value,
            "fact_tables": [t.__dict__ for t in model.fact_tables],
            "dimension_tables": [t.__dict__ for t in model.dimension_tables],
            "ascii_diagram": model.ascii_diagram,
        }

    @staticmethod
    def _design_pipeline(requirements: str, project: str) -> ETLPipeline:
        is_streaming = any(
            kw in requirements for kw in ["stream", "real-time", "realtime", "kafka"]
        )
        mode = ProcessingMode.STREAMING if is_streaming else ProcessingMode.BATCH

        sources: list[DataSource] = [
            DataSource(
                name=f"{project}-source-1",
                type=DataSourceType.DATABASE,
                format="PostgreSQL / MySQL",
                volume_estimate="100 GB - 1 TB initial, ~10 GB/day growth",
                latency_requirement="Daily batch" if not is_streaming else "< 5 seconds",
                connection_method="JDBC / CDC connector",
            ),
            DataSource(
                name=f"{project}-source-2",
                type=DataSourceType.API,
                format="JSON / REST",
                volume_estimate="~1M requests/day",
                latency_requirement="Hourly sync" if not is_streaming else "< 1 minute",
                connection_method="REST API client with rate limiting",
            ),
        ]

        steps: list[ETLStep] = [
            ETLStep(
                step_number=1,
                name="Extract",
                description="Extract raw data from all sources",
                technology="Apache Spark / Airbyte / Fivetran",
                expected_duration="30 min - 2 hours" if not is_streaming else "Continuous",
                error_handling="Retry with exponential backoff (3 attempts)",
            ),
            ETLStep(
                step_number=2,
                name="Validate",
                description="Schema validation and format checking",
                technology="Great Expectations / Deequ",
                expected_duration="10 min" if not is_streaming else "Per event",
                error_handling="Quarantine invalid records to dead letter queue",
            ),
            ETLStep(
                step_number=3,
                name="Transform",
                description="Clean, normalize, and enrich data",
                technology="dbt / Spark SQL / Pandas",
                expected_duration="1-3 hours" if not is_streaming else "< 1 min per micro-batch",
                error_handling="Partial success: good records proceed, bad records quarantined",
            ),
            ETLStep(
                step_number=4,
                name="Load",
                description="Load transformed data into target store",
                technology="COPY command / JDBC batch insert / Kafka sink",
                expected_duration="30 min - 1 hour" if not is_streaming else "Continuous",
                error_handling="Idempotent upsert; retry on conflict",
            ),
        ]

        return ETLPipeline(
            name=f"{project}-pipeline",
            mode=mode,
            sources=tuple(sources),
            steps=tuple(steps),
            orchestration_tool="Apache Airflow" if not is_streaming else "Apache Flink / Kafka Streams",
            total_estimated_duration="2-6 hours (full batch)" if not is_streaming else "< 5 min end-to-end latency",
        )

    @staticmethod
    def _design_data_model(requirements: str, project: str) -> DataModel:
        is_snowflake = "normalized" in requirements or "3nf" in requirements
        schema_type = SchemaType.SNOWFLAKE if is_snowflake else SchemaType.STAR

        fact_table = SchemaTable(
            name=f"fact_{project.lower().replace('-', '_')}_events",
            type="fact",
            columns=(
                ("event_id", "UUID", "Unique event identifier"),
                ("dim_date_id", "INT", "Foreign key to date dimension"),
                ("dim_user_id", "INT", "Foreign key to user dimension"),
                ("metric_value", "DECIMAL(18,2)", "The measured metric"),
                ("event_timestamp", "TIMESTAMP", "When event occurred"),
                ("created_at", "TIMESTAMP", "Record creation timestamp"),
            ),
            primary_key="event_id",
            foreign_keys=(
                ("dim_date_id", "dim_date.date_id"),
                ("dim_user_id", "dim_user.user_id"),
            ),
        )

        dimension_tables: list[SchemaTable] = [
            SchemaTable(
                name="dim_date",
                type="dimension",
                columns=(
                    ("date_id", "INT", "Date surrogate key (YYYYMMDD)"),
                    ("full_date", "DATE", "Calendar date"),
                    ("year", "INT", "Year"),
                    ("quarter", "INT", "Quarter (1-4)"),
                    ("month", "INT", "Month (1-12)"),
                    ("is_weekend", "BOOLEAN", "Weekend flag"),
                ),
                primary_key="date_id",
                foreign_keys=(),
            ),
            SchemaTable(
                name="dim_user",
                type="dimension",
                columns=(
                    ("user_id", "INT", "User surrogate key"),
                    ("external_id", "VARCHAR(100)", "Source system user ID"),
                    ("user_name", "VARCHAR(255)", "Display name"),
                    ("user_email", "VARCHAR(255)", "Email address"),
                    ("user_tier", "VARCHAR(50)", "Free / Premium / Enterprise"),
                    ("created_date", "DATE", "Account creation date"),
                ),
                primary_key="user_id",
                foreign_keys=(),
            ),
            SchemaTable(
                name="dim_metric",
                type="dimension",
                columns=(
                    ("metric_id", "INT", "Metric surrogate key"),
                    ("metric_name", "VARCHAR(100)", "Metric display name"),
                    ("metric_unit", "VARCHAR(50)", "Unit of measurement"),
                    ("metric_category", "VARCHAR(50)", "Category grouping"),
                ),
                primary_key="metric_id",
                foreign_keys=(),
            ),
        ]

        # Build ASCII diagram
        lines: list[str] = [
            f"  {fact_table.name:50s}",
            "  " + "+" + "-" * 48 + "+",
            "  | PK: event_id                    |",
            "  | FK: dim_date_id --> dim_date    |",
            "  | FK: dim_user_id --> dim_user    |",
            "  +" + "-" * 48 + "+",
            "         |              |",
            "         v              v",
            f"  {dimension_tables[0].name:30s}    {dimension_tables[1].name:30s}",
            "  (date)                    (user)",
        ]
        ascii_diagram = "\n".join(lines)

        return DataModel(
            schema_type=schema_type,
            fact_tables=(fact_table,),
            dimension_tables=tuple(dimension_tables),
            ascii_diagram=ascii_diagram,
        )

    @staticmethod
    def _design_quality_checks(requirements: str) -> list[DataQualityCheck]:
        return [
            DataQualityCheck(
                check_name="Completeness",
                description="Ensure no required fields are NULL",
                severity="CRITICAL",
                frequency="Every batch / stream event",
                action_on_failure="Reject record, alert data engineering team",
                sql_template="SELECT COUNT(*) FROM {table} WHERE {column} IS NULL",
            ),
            DataQualityCheck(
                check_name="Uniqueness",
                description="Primary key uniqueness validation",
                severity="CRITICAL",
                frequency="Every batch",
                action_on_failure="Flag duplicates, alert DQ team",
                sql_template="SELECT {pk}, COUNT(*) FROM {table} GROUP BY {pk} HAVING COUNT(*) > 1",
            ),
            DataQualityCheck(
                check_name="Freshness",
                description="Data arrival within expected latency window",
                severity="HIGH",
                frequency="Every 15 minutes",
                action_on_failure="Alert pipeline team, page on-call",
                sql_template="SELECT MAX(created_at) FROM {table}",
            ),
            DataQualityCheck(
                check_name="Referential Integrity",
                description="Foreign key relationships are valid",
                severity="HIGH",
                frequency="Every batch",
                action_on_failure="Quarantine orphaned records",
                sql_template="SELECT COUNT(*) FROM {fact_table} f LEFT JOIN {dim_table} d ON f.{fk}=d.{pk} WHERE d.{pk} IS NULL",
            ),
            DataQualityCheck(
                check_name="Volume Anomaly",
                description="Row count within expected range",
                severity="MEDIUM",
                frequency="Every batch",
                action_on_failure="Notify team for investigation",
                sql_template="SELECT COUNT(*) FROM {table}",
            ),
            DataQualityCheck(
                check_name="Value Range",
                description="Numeric values within expected bounds",
                severity="MEDIUM",
                frequency="Every batch",
                action_on_failure="Flag out-of-range records, alert team",
                sql_template="SELECT {column}, COUNT(*) FROM {table} WHERE {column} < {min} OR {column} > {max}",
            ),
        ]

    @staticmethod
    def _design_monitors(requirements: str) -> list[PipelineMonitor]:
        return [
            PipelineMonitor(
                metric_name="pipeline_lag",
                description="Time between event generation and availability in target",
                alert_threshold="> 30 min for batch, > 5 min for streaming",
                dashboard_location="Grafana / DataDog / CloudWatch",
                retention_period="90 days",
            ),
            PipelineMonitor(
                metric_name="record_volume",
                description="Number of records processed per pipeline run",
                alert_threshold="Volume drop > 50% or spike > 200%",
                dashboard_location="Airflow / Flink dashboard",
                retention_period="30 days",
            ),
            PipelineMonitor(
                metric_name="error_rate",
                description="Percentage of records that fail processing",
                alert_threshold="> 1% error rate",
                dashboard_location="AlertManager / PagerDuty",
                retention_period="90 days",
            ),
            PipelineMonitor(
                metric_name="data_freshness",
                description="Max age of data in target tables",
                alert_threshold="> SLA defined for each table",
                dashboard_location="DataDog / Grafana",
                retention_period="30 days",
            ),
            PipelineMonitor(
                metric_name="storage_usage",
                description="Storage consumed by data warehouse",
                alert_threshold="> 80% of provisioned capacity",
                dashboard_location="Cloud provider console",
                retention_period="30 days",
            ),
        ]

    @staticmethod
    def _recommend_technology(requirements: str) -> list[dict[str, str]]:
        return [
            {"layer": "Orchestration", "recommended": "Apache Airflow",
             "alternatives": "Prefect / Dagster / AWS Step Functions"},
            {"layer": "Processing (Batch)", "recommended": "Apache Spark / dbt",
             "alternatives": "Pandas / DuckDB / AWS Glue"},
            {"layer": "Processing (Stream)", "recommended": "Apache Flink / Kafka Streams",
             "alternatives": "Spark Streaming / AWS Kinesis Analytics"},
            {"layer": "Storage (Warehouse)", "recommended": "Snowflake / BigQuery / Redshift",
             "alternatives": "ClickHouse / DuckDB / PostgreSQL"},
            {"layer": "Storage (Lake)", "recommended": "AWS S3 / GCP Cloud Storage / ADLS",
             "alternatives": "MinIO (self-hosted) / HDFS"},
            {"layer": "Data Quality", "recommended": "Great Expectations",
             "alternatives": "dbt tests / Deequ / Soda"},
            {"layer": "Monitoring", "recommended": "Grafana + Prometheus",
             "alternatives": "DataDog / Databand / Monte Carlo"},
            {"layer": "Schema Registry", "recommended": "Confluent Schema Registry",
             "alternatives": "JSON Schema / Protobuf / Avro"},
        ]

    @staticmethod
    def _list_considerations(requirements: str) -> list[str]:
        return [
            "Implement idempotent writes to handle retries safely",
            "Use incremental processing instead of full refresh where possible",
            "Partition data by date for efficient query pruning",
            "Compress data in transit and at rest to reduce costs",
            "Implement data cataloging (dbt docs / DataHub) for discoverability",
            "Plan for data retention policies (hot/warm/cold tiers)",
            "Ensure PII data is masked/anonymized before loading to warehouse",
        ]
