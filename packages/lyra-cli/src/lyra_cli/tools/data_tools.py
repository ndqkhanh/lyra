"""Data processing tools for JSON, CSV, XML, and structured data."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from enum import StrEnum


class DataFormat(StrEnum):
    JSON = "json"
    JSONL = "jsonl"
    CSV = "csv"
    YAML = "yaml"
    XML = "xml"
    TOML = "toml"


@dataclass(frozen=True)
class DataTransformResult:
    input_format: DataFormat
    output_format: DataFormat
    output: str
    row_count: int
    error: str = ""


@dataclass(frozen=True)
class DataSchema:
    fields: tuple[str, ...]
    types: dict[str, str]
    nullable_fields: tuple[str, ...]
    row_count: int


class DataTool:
    """Parse, transform, and validate structured data formats.

    Usage::

        tool = DataTool()
        result = tool.transform(csv_data, DataFormat.CSV, DataFormat.JSON)
        schema = tool.infer_schema(json_data)
    """

    def transform(
        self, data: str, from_fmt: DataFormat, to_fmt: DataFormat
    ) -> DataTransformResult:
        try:
            if from_fmt == DataFormat.JSON and to_fmt == DataFormat.CSV:
                return self._json_to_csv(data)
            if from_fmt == DataFormat.JSON and to_fmt == DataFormat.JSONL:
                return self._json_to_jsonl(data)
            if from_fmt == DataFormat.CSV and to_fmt == DataFormat.JSON:
                return self._csv_to_json(data)
            return DataTransformResult(
                input_format=from_fmt,
                output_format=to_fmt,
                output="",
                row_count=0,
                error=f"Unsupported transform: {from_fmt} → {to_fmt}",
            )
        except Exception as exc:
            return DataTransformResult(
                input_format=from_fmt,
                output_format=to_fmt,
                output="",
                row_count=0,
                error=str(exc),
            )

    @staticmethod
    def infer_schema(json_data: str) -> DataSchema:
        rows = json.loads(json_data)
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list) or not rows:
            return DataSchema(fields=(), types={}, nullable_fields=(), row_count=0)

        fields: list[str] = []
        types: dict[str, str] = {}
        nullable: set[str] = set()

        for row in rows:
            if not isinstance(row, dict):
                continue
            for key, value in row.items():
                if key not in fields:
                    fields.append(key)
                if value is None:
                    nullable.add(key)
                else:
                    types[key] = type(value).__name__

        return DataSchema(
            fields=tuple(fields),
            types=types,
            nullable_fields=tuple(sorted(nullable)),
            row_count=len(rows),
        )

    @staticmethod
    def _json_to_csv(data: str) -> DataTransformResult:
        rows = json.loads(data)
        if isinstance(rows, dict):
            rows = [rows]
        if not rows:
            return DataTransformResult(DataFormat.JSON, DataFormat.CSV, "", 0)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return DataTransformResult(
            input_format=DataFormat.JSON,
            output_format=DataFormat.CSV,
            output=output.getvalue(),
            row_count=len(rows),
        )

    @staticmethod
    def _json_to_jsonl(data: str) -> DataTransformResult:
        rows = json.loads(data)
        if isinstance(rows, dict):
            rows = [rows]
        output = "\n".join(json.dumps(r) for r in rows)
        return DataTransformResult(
            input_format=DataFormat.JSON,
            output_format=DataFormat.JSONL,
            output=output,
            row_count=len(rows),
        )

    @staticmethod
    def _csv_to_json(data: str) -> DataTransformResult:
        reader = csv.DictReader(io.StringIO(data))
        rows = list(reader)
        output = json.dumps(rows, indent=2)
        return DataTransformResult(
            input_format=DataFormat.CSV,
            output_format=DataFormat.JSON,
            output=output,
            row_count=len(rows),
        )
