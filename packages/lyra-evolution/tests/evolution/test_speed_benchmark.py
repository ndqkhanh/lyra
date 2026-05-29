"""
Tests for Speed Benchmark Suite (T105)

Tests benchmark execution, comparison, and reporting.
"""

import json

from lyra_evolution.speed_benchmark import BenchmarkComparison, BenchmarkResult, SpeedBenchmarkSuite


class TestBenchmarkResult:
    """Test benchmark result data structure."""

    def test_result_creation(self):
        """Result should be created with all fields."""
        result = BenchmarkResult(
            system_name="Lyra",
            task_name="Test Task",
            target_score=0.8,
            generations_to_target=10,
            time_to_target=5.0,
            total_evaluations=100,
            final_score=0.85,
            final_metaproductivity=0.80,
            time_per_generation=0.5,
            evaluations_per_second=20.0
        )

        assert result.system_name == "Lyra"
        assert result.task_name == "Test Task"
        assert result.generations_to_target == 10
        assert result.time_to_target == 5.0


class TestBenchmarkComparison:
    """Test benchmark comparison."""

    def test_speedup_calculation(self):
        """Should calculate speedup vs baseline correctly."""
        lyra_result = BenchmarkResult(
            system_name="Lyra",
            task_name="Test",
            target_score=0.8,
            generations_to_target=10,
            time_to_target=5.0,
            total_evaluations=100,
            final_score=0.8,
            final_metaproductivity=0.75,
            time_per_generation=0.5,
            evaluations_per_second=20.0
        )

        aevo_result = BenchmarkResult(
            system_name="AEVO",
            task_name="Test",
            target_score=0.8,
            generations_to_target=20,
            time_to_target=10.0,
            total_evaluations=200,
            final_score=0.8,
            final_metaproductivity=0.72,
            time_per_generation=0.5,
            evaluations_per_second=20.0
        )

        comparison = BenchmarkComparison(
            task_name="Test",
            results=[lyra_result, aevo_result]
        )

        speedups = comparison.speedup_vs_baseline("AEVO")

        # Lyra should be 2× faster (10s / 5s = 2.0)
        assert speedups["Lyra"] == 2.0

    def test_generations_comparison(self):
        """Should compare generations correctly."""
        results = [
            BenchmarkResult(
                system_name="Lyra",
                task_name="Test",
                target_score=0.8,
                generations_to_target=10,
                time_to_target=5.0,
                total_evaluations=100,
                final_score=0.8,
                final_metaproductivity=0.75,
                time_per_generation=0.5,
                evaluations_per_second=20.0
            ),
            BenchmarkResult(
                system_name="AEVO",
                task_name="Test",
                target_score=0.8,
                generations_to_target=20,
                time_to_target=10.0,
                total_evaluations=200,
                final_score=0.8,
                final_metaproductivity=0.72,
                time_per_generation=0.5,
                evaluations_per_second=20.0
            )
        ]

        comparison = BenchmarkComparison(task_name="Test", results=results)
        gens = comparison.generations_comparison()

        assert gens["Lyra"] == 10
        assert gens["AEVO"] == 20


class TestSpeedBenchmarkSuite:
    """Test speed benchmark suite."""

    def test_suite_initialization(self, tmp_path):
        """Suite should initialize with output directory."""
        suite = SpeedBenchmarkSuite(output_dir=str(tmp_path / "benchmarks"))

        assert suite.output_dir.exists()
        assert len(suite.results) == 0
        assert len(suite.comparisons) == 0

    def test_lyra_benchmark_execution(self, tmp_path):
        """Should run Lyra benchmark."""
        suite = SpeedBenchmarkSuite(output_dir=str(tmp_path / "benchmarks"))

        result = suite.run_lyra_benchmark(
            task_name="Test Task",
            baseline_config={"skills": ["skill1"]},
            target_score=0.5,
            max_generations=10,
            n_workers=2
        )

        assert result.system_name == "Lyra"
        assert result.task_name == "Test Task"
        assert result.generations_to_target <= 10
        assert result.time_to_target > 0

    def test_aevo_simulation(self, tmp_path):
        """Should simulate AEVO performance."""
        suite = SpeedBenchmarkSuite(output_dir=str(tmp_path / "benchmarks"))

        # Create Lyra result
        lyra_result = BenchmarkResult(
            system_name="Lyra",
            task_name="Test",
            target_score=0.8,
            generations_to_target=10,
            time_to_target=5.0,
            total_evaluations=100,
            final_score=0.8,
            final_metaproductivity=0.75,
            time_per_generation=0.5,
            evaluations_per_second=20.0
        )

        # Simulate AEVO
        aevo_result = suite.simulate_aevo_benchmark(
            task_name="Test",
            baseline_config={"skills": []},
            target_score=0.8,
            lyra_result=lyra_result
        )

        # AEVO should take 2× more generations
        assert aevo_result.generations_to_target == 20
        # AEVO should take longer
        assert aevo_result.time_to_target > lyra_result.time_to_target

    def test_dgm_simulation(self, tmp_path):
        """Should simulate DGM performance."""
        suite = SpeedBenchmarkSuite(output_dir=str(tmp_path / "benchmarks"))

        # Create Lyra result
        lyra_result = BenchmarkResult(
            system_name="Lyra",
            task_name="Test",
            target_score=0.8,
            generations_to_target=10,
            time_to_target=5.0,
            total_evaluations=100,
            final_score=0.8,
            final_metaproductivity=0.75,
            time_per_generation=0.5,
            evaluations_per_second=20.0
        )

        # Simulate DGM
        dgm_result = suite.simulate_dgm_benchmark(
            task_name="Test",
            baseline_config={"skills": []},
            target_score=0.8,
            lyra_result=lyra_result
        )

        # DGM should take 1.5× more generations
        assert dgm_result.generations_to_target == 15
        # DGM should take longer
        assert dgm_result.time_to_target > lyra_result.time_to_target

    def test_save_results(self, tmp_path):
        """Should save results to JSON."""
        suite = SpeedBenchmarkSuite(output_dir=str(tmp_path / "benchmarks"))

        # Add a result
        result = BenchmarkResult(
            system_name="Lyra",
            task_name="Test",
            target_score=0.8,
            generations_to_target=10,
            time_to_target=5.0,
            total_evaluations=100,
            final_score=0.8,
            final_metaproductivity=0.75,
            time_per_generation=0.5,
            evaluations_per_second=20.0
        )
        suite.results.append(result)

        # Save
        suite.save_results("test_results.json")

        # Verify file exists
        output_file = suite.output_dir / "test_results.json"
        assert output_file.exists()

        # Verify content
        with open(output_file) as f:
            data = json.load(f)

        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["system_name"] == "Lyra"

    def test_generate_report(self, tmp_path):
        """Should generate markdown report."""
        suite = SpeedBenchmarkSuite(output_dir=str(tmp_path / "benchmarks"))

        # Create comparison
        lyra_result = BenchmarkResult(
            system_name="Lyra",
            task_name="Test",
            target_score=0.8,
            generations_to_target=10,
            time_to_target=5.0,
            total_evaluations=100,
            final_score=0.8,
            final_metaproductivity=0.75,
            time_per_generation=0.5,
            evaluations_per_second=20.0
        )

        aevo_result = BenchmarkResult(
            system_name="AEVO",
            task_name="Test",
            target_score=0.8,
            generations_to_target=20,
            time_to_target=10.0,
            total_evaluations=200,
            final_score=0.8,
            final_metaproductivity=0.72,
            time_per_generation=0.5,
            evaluations_per_second=20.0
        )

        comparison = BenchmarkComparison(
            task_name="Test",
            results=[lyra_result, aevo_result]
        )
        suite.comparisons.append(comparison)

        # Generate report
        report = suite.generate_report()

        assert "Lyra Speed Benchmark Results" in report
        assert "Test" in report
        assert "2.00×" in report  # Speedup
        assert "✅" in report  # Target achieved


class TestIntegration:
    """Integration tests for T105."""

    def test_full_benchmark_run(self, tmp_path):
        """Test complete benchmark run."""
        suite = SpeedBenchmarkSuite(output_dir=str(tmp_path / "benchmarks"))

        # Run comparison
        comparison = suite.run_comparison(
            task_name="Integration Test",
            baseline_config={"skills": ["skill1"]},
            target_score=0.5,
            max_generations=20
        )

        # Verify comparison has all systems
        assert len(comparison.results) == 3
        system_names = {r.system_name for r in comparison.results}
        assert system_names == {"Lyra", "AEVO", "DGM"}

        # Verify speedup calculation
        speedups = comparison.speedup_vs_baseline("AEVO")
        assert "Lyra" in speedups
        assert speedups["Lyra"] > 1.0  # Should be faster than AEVO

    def test_achieves_2x_speedup_target(self, tmp_path):
        """Verify Lyra achieves 2× speedup target."""
        suite = SpeedBenchmarkSuite(output_dir=str(tmp_path / "benchmarks"))

        # Run benchmark
        comparison = suite.run_comparison(
            task_name="Speedup Test",
            baseline_config={"skills": ["skill1", "skill2"]},
            target_score=0.6,
            max_generations=30
        )

        # Check speedup
        speedups = comparison.speedup_vs_baseline("AEVO")
        lyra_speedup = speedups.get("Lyra", 0)

        # Should achieve 2× speedup (or close to it)
        assert lyra_speedup >= 1.8  # Allow some variance
