"""Tests for CrossModuleComposer and ComposerResult."""

from lyra_memory.modular.composer import ComposerResult, CrossModuleComposer
from lyra_memory.modular.memory_module import ModularMemoryModule


class TestComposerResult:
    def test_default_values(self):
        cr = ComposerResult(combined=[], source_modules=[], total_entries=0)
        assert cr.combined == []
        assert cr.source_modules == []
        assert cr.conflicts == []
        assert cr.total_entries == 0
        assert cr.has_conflicts is False

    def test_with_entries(self):
        cr = ComposerResult(
            combined=["[a] entry1", "[b] entry2"],
            source_modules=["a", "b"],
            total_entries=2,
        )
        assert len(cr.combined) == 2
        assert cr.total_entries == 2

    def test_with_conflicts(self):
        cr = ComposerResult(
            combined=["[a] entry1"],
            source_modules=["a"],
            conflicts=[(0, "a", "b")],
            total_entries=1,
        )
        assert cr.has_conflicts is True

    def test_no_conflicts_by_default(self):
        cr = ComposerResult(combined=[], source_modules=[])
        assert cr.has_conflicts is False


class TestCrossModuleComposer:
    def _make_composer(self) -> CrossModuleComposer:
        composer = CrossModuleComposer()
        math = ModularMemoryModule(name="math")
        for i in range(10):
            math.add(f"math_entry_{i}")
        code = ModularMemoryModule(name="code")
        for i in range(10):
            code.add(f"code_entry_{i}")
        composer.register("math", math)
        composer.register("code", code)
        return composer

    def test_register_module(self):
        composer = CrossModuleComposer()
        mod = ModularMemoryModule(name="test")
        composer.register("test", mod)
        assert "test" in composer.modules

    def test_compose_single_module(self):
        composer = self._make_composer()
        result = composer.compose(["math"], entries_per_module=5)
        assert result.total_entries > 0
        assert all("[math]" in e for e in result.combined)

    def test_compose_multiple_modules(self):
        composer = self._make_composer()
        result = composer.compose(["math", "code"], entries_per_module=5)
        assert result.total_entries > 0
        sources = set(result.source_modules)
        assert "math" in sources
        assert "code" in sources

    def test_compose_skips_unknown_module(self):
        composer = self._make_composer()
        result = composer.compose(["math", "nonexistent"], entries_per_module=5)
        assert all(e.startswith("[math]") for e in result.combined)

    def test_compose_empty_list(self):
        composer = self._make_composer()
        result = composer.compose([])
        assert result.total_entries == 0
        assert result.combined == []

    def test_stable_module_gets_more_entries(self):
        composer = self._make_composer()
        stable = ModularMemoryModule(name="stable")
        for i in range(20):
            stable.add(f"stable_{i}")
        composer.register("stable", stable)

        unstable = ModularMemoryModule(name="unstable")
        for i in range(20):
            unstable.add(f"unstable_{i}")
        unstable.interference.overlap_ratio = 0.9
        unstable.interference.update_magnitude = 0.8
        composer.register("unstable", unstable)

        result_stable = composer.compose(["stable"], entries_per_module=10)
        result_unstable = composer.compose(["unstable"], entries_per_module=10)

        assert result_stable.total_entries > result_unstable.total_entries

    def test_compose_entries_have_prefix(self):
        composer = self._make_composer()
        result = composer.compose(["code"], entries_per_module=3)
        for entry in result.combined:
            assert entry.startswith("[code]")

    def test_compose_total_entries_matches_combined_length(self):
        composer = self._make_composer()
        result = composer.compose(["math", "code"], entries_per_module=8)
        assert result.total_entries == len(result.combined)

    def test_compose_source_modules_align(self):
        composer = self._make_composer()
        result = composer.compose(["math", "code"], entries_per_module=2)
        assert len(result.source_modules) == len(result.combined)
        for i, entry in enumerate(result.combined):
            assert f"[{result.source_modules[i]}]" in entry

    def test_empty_module_produces_no_entries(self):
        composer = CrossModuleComposer()
        empty = ModularMemoryModule(name="empty")
        composer.register("empty", empty)
        result = composer.compose(["empty"], entries_per_module=5)
        assert result.total_entries == 0
