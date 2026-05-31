"""
Lyra Safety Guardrails — 4-layer defense-in-depth architecture.

Layers (from plan §4.17, BREAKTHROUGH-ARCHITECTURE.md):
1. **Input Guard** (LlamaFirewall pattern): Prompt injection detection, PII scrubbing
2. **Control/Data Separation** (CaMeL pattern): Untrusted data never reaches control plane
3. **Runtime Rails** (NeMo pattern): Programmable runtime constraints via policy language
4. **Least-Privilege Tool Control** (Progent pattern): SMT-based minimum permission sets

Plus: "Agent May Misevolve" defenses — alignment decay detection, skill evolution
safety gates, and tool-creation audit trails.
"""

from __future__ import annotations

from .defense import DefensePipeline, DefenseResult, SafetyLayer
from .misevolve import MisevolveDefense, EvolutionSafetyGate

__all__ = [
    "DefensePipeline",
    "DefenseResult",
    "EvolutionSafetyGate",
    "MisevolveDefense",
    "SafetyLayer",
]
