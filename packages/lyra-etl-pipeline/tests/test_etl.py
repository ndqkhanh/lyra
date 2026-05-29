"""Tests for lyra-etl-pipeline."""
import asyncio

from lyra_etl_pipeline import ETLPipeline


class TestETLPipeline:
    def test_run(self):
        pipe = ETLPipeline()
        ds = asyncio.run(pipe.run("data.csv", {"id": "int", "name": "str"}))
        assert ds.name == "dataset_1"
        assert "id" in ds.schema.fields

    def test_multiple_pipelines(self):
        pipe = ETLPipeline()
        asyncio.run(pipe.run("a.csv", {"x": "str"}))
        asyncio.run(pipe.run("b.csv", {"y": "int"}))
        assert pipe.stats["pipelines_run"] == 2

    def test_stats(self):
        pipe = ETLPipeline()
        assert pipe.stats["pipelines_run"] == 0
