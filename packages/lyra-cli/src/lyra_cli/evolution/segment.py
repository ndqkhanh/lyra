"""Evolution segment runner."""
from typing import Callable
from lyra_cli.evolution.harness import EvolutionHarness
from lyra_cli.evolution.cost_meter import CostMeter, BudgetCap


class EvolutionSegment:
    """Run fixed evolver for N iterations."""

    def __init__(self, harness: EvolutionHarness, cost_meter: CostMeter):
        self.harness = harness
        self.cost_meter = cost_meter

    def run_segment(
        self,
        evolver: Callable,
        rounds: int,
        budget_cap: BudgetCap | None = None,
    ) -> list[tuple[dict, dict]]:
        """Run evolver with fixed Π_r for N rounds."""
        candidates = []

        for i in range(rounds):
            # Check budget before each round
            if budget_cap and not self.cost_meter.check_budget(budget_cap):
                break

            # Generate candidate
            candidate = evolver()
            candidate_id = candidate.get("id", f"c{i:03d}")

            # Evaluate via harness
            score = self.harness.evaluate(candidate_id)

            # Track cost (placeholder - real implementation would track actual tokens)
            self.cost_meter.add_tokens(1000, 0.001)

            candidates.append((candidate, score))

        return candidates
