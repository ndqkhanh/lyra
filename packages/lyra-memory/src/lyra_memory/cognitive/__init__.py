"""
Neuroscience-Grounded Cognitive Architecture.

Grounds every memory design decision in cognitive neuroscience:
  ValenceVector      — 5-component emotional/cognitive weight per memory
  System12Router     — Dual-process: fast intuitive (S1) vs slow deliberative (S2)
  ThalamicGateway    — 6-channel salience filter before memory storage
  CBTBeliefHierarchy — 3-tier belief system with cathartic updates

Source: Human-Like Lifelong Memory (QufkvHbQs7), ICLR 2026 MemAgent Workshop.
"""

from lyra_memory.cognitive.beliefs import Belief, CBTBeliefHierarchy
from lyra_memory.cognitive.router import System12MemoryRouter
from lyra_memory.cognitive.thalamic import ThalamicGateway
from lyra_memory.cognitive.valence import ValenceEstimator, ValenceVector

__all__ = [
    "Belief",
    "CBTBeliefHierarchy",
    "System12MemoryRouter",
    "ThalamicGateway",
    "ValenceEstimator",
    "ValenceVector",
]
