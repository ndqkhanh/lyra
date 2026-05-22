"""World Model — mental simulation of environment dynamics before action."""
from __future__ import annotations; import logging; from dataclasses import dataclass, field; from typing import Any, Optional
logger = logging.getLogger(__name__); __all__ = ["State", "Action", "Simulation", "WorldModel"]
@dataclass
class State: variables: dict; step: int = 0
@dataclass
class Action: name: str; params: dict
@dataclass
class Simulation: states: list[State]; total_cost: float = 0.0

class WorldModel:
    def __init__(self): self._simulations = 0
    def predict(self, state: State, action: Action) -> State:
        new_vars = dict(state.variables)
        for k, v in new_vars.items():
            if isinstance(v, (int, float)): new_vars[k] = v * (1.0 + 0.01 * (hash(action.name) % 10 - 5))
        return State(variables=new_vars, step=state.step + 1)
    def simulate_plan(self, initial: State, actions: list[Action]) -> Simulation:
        self._simulations += 1; states = [initial]
        for a in actions: states.append(self.predict(states[-1], a))
        return Simulation(states=states, total_cost=len(actions) * 0.05)
    def what_if(self, state: State, action_a: Action, action_b: Action) -> tuple[State, State]:
        return (self.predict(state, action_a), self.predict(state, action_b))
    @property
    def stats(self) -> dict: return {"simulations": self._simulations}
