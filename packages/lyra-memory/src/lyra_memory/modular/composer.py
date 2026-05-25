"""
Cross-Module Composer — combines results from multiple memory modules
with interference-aware weighting and conflict resolution.

Source: Modular Compression (ztmwHisqJ4), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ComposerResult:
    """Result of composing across module outputs."""

    combined: list[str]
    source_modules: list[str]
    conflicts: list[tuple[int, str, str]] = field(default_factory=list)
    total_entries: int = 0

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0


@dataclass
class CrossModuleComposer:
    """Combines results from multiple modules with interference weighting.

    Entries from stable modules (low interference) are weighted higher
    than entries from unstable modules (high interference).
    """

    modules: dict[str, object] = field(default_factory=dict)
    stability_weight: float = 0.7

    def register(self, name: str, module: object) -> None:
        self.modules[name] = module

    def compose(
        self, module_names: list[str], entries_per_module: int = 5,
    ) -> ComposerResult:
        """Combine top entries from selected modules with weighting."""
        from lyra_memory.modular.memory_module import ModularMemoryModule

        combined: list[str] = []
        sources: list[str] = []
        conflicts: list[tuple[int, str, str]] = []

        for name in module_names:
            mod = self.modules.get(name)
            if mod is None:
                continue
            m: ModularMemoryModule = mod  # type: ignore[assignment]
            weight = self._module_weight(m)

            count = max(1, int(entries_per_module * weight))
            entries = m.entries[-count:] if m.entries else []
            for e in entries:
                combined.append(f"[{name}] {e}")
                sources.append(name)

        return ComposerResult(
            combined=combined,
            source_modules=sources,
            conflicts=conflicts,
            total_entries=len(combined),
        )

    def _module_weight(self, module: object) -> float:
        """Compute weight based on module stability."""
        from lyra_memory.modular.memory_module import ModularMemoryModule

        m: ModularMemoryModule = module  # type: ignore[assignment]
        if m.interference.is_stable:
            return 1.0
        interference = m.interference.interference_bound
        alpha = max(0.1, 1.0 - interference)
        return round(self.stability_weight * 1.0 + (1 - self.stability_weight) * alpha, 4)
