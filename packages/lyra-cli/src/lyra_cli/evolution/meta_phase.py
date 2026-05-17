"""Meta-editing phase for two-phase loop."""
from lyra_cli.evolution.context import EvolutionContext
from lyra_cli.evolution.meta_agent import MetaAgent
from lyra_cli.evolution.actions import EditAction


def meta_editing_phase(
    meta_agent: MetaAgent,
    context: EvolutionContext,
) -> EditAction:
    """Meta-agent observes context and proposes edit."""
    # Phase 1: Observe
    obs = meta_agent.observe(context)

    # Phase 2: Plan edit
    action = meta_agent.plan_edit(obs)

    # Phase 3: Apply edit
    meta_agent.apply_edit(action)

    return action
