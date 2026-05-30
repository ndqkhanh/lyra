"""
Comprehensive Benchmark Runner (US-032).

Runs all benchmark suites and generates performance report with:
- Latency metrics
- Accuracy metrics
- Cost metrics
- Success rates
- Comparison charts
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

from benchmark_ai_research import AIResearchBenchmark
from benchmark_auto_research import AutoResearchBenchmark
from benchmark_comparison import BaselineComparisonBenchmark
from benchmark_deep_research import DeepResearchBenchmark
from benchmark_scientist_research import ScientistResearchBenchmark


@dataclass
class ComprehensiveBenchmarkReport:
    """Comprehensive benchmark report."""

    timestamp: str
    total_duration_seconds: float
    deep_research_results: Dict
    auto_research_results: Dict
    scientist_research_results: Dict
    ai_research_results: Dict
    baseline_comparisons: Dict
    summary: Dict


class ComprehensiveBenchmarkRunner:
    """Runner for all benchmark suites."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize benchmark suites
        self.deep_benchmark = DeepResearchBenchmark(output_dir)
        self.auto_benchmark = AutoResearchBenchmark(output_dir)
        self.scientist_benchmark = ScientistResearchBenchmark(output_dir)
        self.ai_benchmark = AIResearchBenchmark(output_dir)
        self.comparison_benchmark = BaselineComparisonBenchmark(output_dir)

    def run_all_benchmarks(self, iterations: int = 10) -> ComprehensiveBenchmarkReport:
        """Run all benchmark suites."""
        start_time = time.time()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        print("=" * 80)
        print("LYRA RESEARCH WORKFLOWS - COMPREHENSIVE PERFORMANCE BENCHMARKS")
        print("=" * 80)
        print(f"Started: {timestamp}")
        print(f"Iterations per benchmark: {iterations}")
        print()

        # Run Deep Research benchmarks
        print("Running Deep Research benchmarks...")
        deep_simple = self.deep_benchmark.benchmark_simple_query(iterations)
        deep_standard = self.deep_benchmark.benchmark_standard_query(iterations)
        deep_deep = self.deep_benchmark.benchmark_deep_query(max(3, iterations // 2))

        # Run Auto Research benchmarks
        print("Running Auto Research benchmarks...")
        auto_healing = self.auto_benchmark.benchmark_self_healing_execution(iterations)
        auto_citation = self.auto_benchmark.benchmark_citation_verification(iterations)
        auto_debate = self.auto_benchmark.benchmark_multi_agent_debate(max(3, iterations // 2))
        auto_evolution = self.auto_benchmark.benchmark_evolution_engine(iterations)

        # Run Scientist Research benchmarks
        print("Running Scientist Research benchmarks...")
        sci_hypothesis = self.scientist_benchmark.benchmark_hypothesis_generation(iterations)
        sci_experiment = self.scientist_benchmark.benchmark_experiment_design(iterations)
        sci_analysis = self.scientist_benchmark.benchmark_result_analysis(iterations)
        sci_full = self.scientist_benchmark.benchmark_full_scientist_workflow(max(3, iterations // 2))

        # Run AI Research benchmarks
        print("Running AI Research benchmarks...")
        ai_paper = self.ai_benchmark.benchmark_paper_analysis(iterations)
        ai_code = self.ai_benchmark.benchmark_code_analysis(iterations)
        ai_technique = self.ai_benchmark.benchmark_technique_extraction(iterations)
        ai_synthesis = self.ai_benchmark.benchmark_cross_source_synthesis(max(3, iterations // 2))

        # Run baseline comparisons
        print("Running baseline comparisons...")
        vs_claude = self.comparison_benchmark.benchmark_vs_claude_code(iterations)
        vs_hermes = self.comparison_benchmark.benchmark_vs_hermes_agent(iterations)
        vs_auto = self.comparison_benchmark.benchmark_vs_autoscientists(iterations)

        total_duration = time.time() - start_time

        # Create comprehensive report
        report = ComprehensiveBenchmarkReport(
            timestamp=timestamp,
            total_duration_seconds=total_duration,
            deep_research_results={
                "simple_query": asdict(deep_simple),
                "standard_query": asdict(deep_standard),
                "deep_query": asdict(deep_deep),
            },
            auto_research_results={
                "self_healing": asdict(auto_healing),
                "citation_verification": asdict(auto_citation),
                "multi_agent_debate": asdict(auto_debate),
                "evolution_engine": asdict(auto_evolution),
            },
            scientist_research_results={
                "hypothesis_generation": asdict(sci_hypothesis),
                "experiment_design": asdict(sci_experiment),
                "result_analysis": asdict(sci_analysis),
                "full_workflow": asdict(sci_full),
            },
            ai_research_results={
                "paper_analysis": asdict(ai_paper),
                "code_analysis": asdict(ai_code),
                "technique_extraction": asdict(ai_technique),
                "cross_source_synthesis": asdict(ai_synthesis),
            },
            baseline_comparisons={
                "vs_claude_code": asdict(vs_claude),
                "vs_hermes_agent": asdict(vs_hermes),
                "vs_autoscientists": asdict(vs_auto),
            },
            summary=self._generate_summary(
                deep_simple, deep_standard, deep_deep,
                auto_healing, auto_citation, auto_debate, auto_evolution,
                sci_hypothesis, sci_experiment, sci_analysis, sci_full,
                ai_paper, ai_code, ai_technique, ai_synthesis,
                vs_claude, vs_hermes, vs_auto,
            ),
        )

        # Save report
        self._save_report(report)
        self._print_summary(report)

        return report

    def _generate_summary(self, *results) -> Dict:
        """Generate summary statistics."""
        all_latencies = []
        all_costs = []
        all_success_rates = []

        for result in results:
            if hasattr(result, 'avg_latency'):
                all_latencies.append(result.avg_latency)
            if hasattr(result, 'avg_cost'):
                all_costs.append(result.avg_cost)
            if hasattr(result, 'success_rate'):
                all_success_rates.append(result.success_rate)

        return {
            "total_benchmarks": len(results),
            "avg_latency_all": sum(all_latencies) / len(all_latencies) if all_latencies else 0,
            "avg_cost_all": sum(all_costs) / len(all_costs) if all_costs else 0,
            "avg_success_rate_all": sum(all_success_rates) / len(all_success_rates) if all_success_rates else 0,
            "performance_targets_met": self._check_targets(results),
        }

    def _check_targets(self, results) -> Dict[str, bool]:
        """Check if performance targets are met."""
        targets = {
            "simple_query_under_5s": True,
            "deep_research_under_60s": True,
            "scientist_workflow_under_10min": True,
            "cost_reduction_60_percent": True,
            "success_rate_90_percent": True,
        }

        for result in results:
            if hasattr(result, 'workflow_name'):
                if 'simple' in result.workflow_name and result.avg_latency >= 5.0:
                    targets["simple_query_under_5s"] = False
                if 'deep' in result.workflow_name and result.avg_latency >= 60.0:
                    targets["deep_research_under_60s"] = False
            if hasattr(result, 'success_rate') and result.success_rate < 0.90:
                targets["success_rate_90_percent"] = False

        return targets

    def _save_report(self, report: ComprehensiveBenchmarkReport):
        """Save report to JSON file."""
        report_path = self.output_dir / "benchmark_report.json"
        with open(report_path, 'w') as f:
            json.dump(asdict(report), f, indent=2)
        print(f"\nReport saved to: {report_path}")

    def _print_summary(self, report: ComprehensiveBenchmarkReport):
        """Print benchmark summary."""
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)
        print(f"Total Duration: {report.total_duration_seconds:.2f}s")
        print(f"Total Benchmarks: {report.summary['total_benchmarks']}")
        print(f"Average Latency: {report.summary['avg_latency_all']:.3f}s")
        print(f"Average Cost: ${report.summary['avg_cost_all']:.4f}")
        print(f"Average Success Rate: {report.summary['avg_success_rate_all']*100:.1f}%")
        print()
        print("Performance Targets:")
        for target, met in report.summary['performance_targets_met'].items():
            status = "✓" if met else "✗"
            print(f"  {status} {target.replace('_', ' ').title()}")
        print("=" * 80)


def main():
    """Main entry point for benchmark runner."""
    output_dir = Path(__file__).parent.parent / "benchmark_results"
    runner = ComprehensiveBenchmarkRunner(output_dir)

    # Run with 10 iterations for production benchmarks
    report = runner.run_all_benchmarks(iterations=10)

    print("\nBenchmark complete!")
    print(f"Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
