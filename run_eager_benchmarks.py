#!/usr/bin/env python3
"""Run eager tools performance benchmarks."""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-cli/src"))

from lyra_cli.eager_tools.benchmarks import run_benchmarks


async def main():
    """Run benchmarks and display results."""
    print("=" * 70)
    print("Eager Tools Performance Benchmarks")
    print("=" * 70)
    print()

    print("Running benchmarks...")
    results = await run_benchmarks()

    print()
    print("Results:")
    print("-" * 70)
    print(f"{'Workload':<20} {'Sequential':<12} {'Eager':<12} {'Speedup':<10} {'Tools':<8}")
    print("-" * 70)

    total_speedup = 0
    for result in results:
        print(
            f"{result.workload:<20} "
            f"{result.sequential_ms:>10.1f}ms "
            f"{result.eager_ms:>10.1f}ms "
            f"{result.speedup:>8.2f}x "
            f"{result.tools_executed:>6}"
        )
        total_speedup += result.speedup

    avg_speedup = total_speedup / len(results) if results else 0

    print("-" * 70)
    print(f"Average Speedup: {avg_speedup:.2f}x")
    print()

    # Check if target met
    target_min = 1.2
    target_max = 1.5

    if avg_speedup >= target_min:
        print(f"✅ SUCCESS: Average speedup {avg_speedup:.2f}x meets target ({target_min}x-{target_max}x)")
        return 0
    else:
        print(f"⚠️  WARNING: Average speedup {avg_speedup:.2f}x below target ({target_min}x-{target_max}x)")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
