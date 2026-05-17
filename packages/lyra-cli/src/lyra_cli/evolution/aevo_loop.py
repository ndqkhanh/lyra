"""AEVO two-phase evolution loop."""
from typing import Callable
from lyra_cli.evolution.context import EvolutionContext
from lyra_cli.evolution.meta_agent import MetaAgent
from lyra_cli.evolution.segment import EvolutionSegment
from lyra_cli.evolution.meta_phase import meta_editing_phase
from lyra_cli.evolution.cost_meter import BudgetCap


def aevo_loop(
    meta_agent: MetaAgent,
    segment_runner: EvolutionSegment,
    evolver: Callable,
    max_rounds: int,
    segment_size: int,
    budget_cap: BudgetCap | None = None,
) -> EvolutionContext:
    """Run AEVO two-phase loop: meta-editing → evolution segment."""
    context = EvolutionContext()

    for r in range(max_rounds):
        # Phase 1: Meta-editing
        if r > 0:  # Skip first round (no context yet)
            edit = meta_editing_phase(meta_agent, context)
            context.append_edit({
                "round": r,
                "edit_type": edit.edit_type.value,
                "target": edit.target_path,
                "rationale": edit.rationale,
            })

        # Phase 2: Evolution segment
        candidates = segment_runner.run_segment(evolver, segment_size, budget_cap)

        # Update context
        for candidate, score in candidates:
            context.append_candidate(candidate, score)

        # Check budget
        if budget_cap and not segment_runner.cost_meter.check_budget(budget_cap):
            break

    return context
