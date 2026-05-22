"""Mode Switch — thinking/non-thinking compute allocation per task (Qwen3-inspired)."""
from __future__ import annotations; import logging; from enum import Enum; from dataclasses import dataclass; from typing import Any, Optional
logger = logging.getLogger(__name__); __all__ = ["ComputeMode", "ModeSwitchEngine"]

class ComputeMode: NON_THINKING = "non_thinking"; THINKING = "thinking"; DEEP_THINKING = "deep_thinking"; ENSEMBLE = "ensemble"

class ModeSwitchEngine:
    def __init__(self): self._switches = 0; self.current_mode = ComputeMode.NON_THINKING
    def select_mode(self, complexity: float) -> str:
        self._switches += 1
        if complexity < 0.2: self.current_mode = ComputeMode.NON_THINKING
        elif complexity < 0.5: self.current_mode = ComputeMode.THINKING
        elif complexity < 0.8: self.current_mode = ComputeMode.DEEP_THINKING
        else: self.current_mode = ComputeMode.ENSEMBLE
        return self.current_mode
    @property
    def stats(self) -> dict: return {"switches": self._switches, "mode": self.current_mode}
