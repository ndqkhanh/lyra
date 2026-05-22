from lyra_supply_chain import SupplyChainAgent
class TestSupplyChain:
    def test_reorder(self):
        s = SupplyChainAgent(); s.add_item("WIDGET-001", 5, 10, 7)
        assert "WIDGET-001" in s.check_reorder()
    def test_place_order(self):
        s = SupplyChainAgent(); s.add_item("BOLT-001", 3, 10, 5)
        assert s.place_order("BOLT-001", 20)
