from lyra_decomposer import HierarchicalDecomposer
class TestHierarchicalDecomposer:
    def test_decompose(self):
        d = HierarchicalDecomposer()
        g = d.decompose("Research. Implement. Test. Deploy.")
        assert len(g.subgoals) >= 3
    def test_dependency_order(self):
        d = HierarchicalDecomposer()
        g = d.decompose("Plan. Execute. Verify.")
        ordered = d.dependency_order(g)
        assert len(ordered) == len(g.subgoals)
