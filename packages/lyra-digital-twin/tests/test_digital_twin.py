from lyra_digital_twin import DigitalTwin
class TestDigitalTwin:
    def test_add_entity(self):
        t = DigitalTwin(); e = t.add_entity("factory", {"temp": 72}); assert e.name == "factory"
    def test_tick(self):
        t = DigitalTwin(); t.add_entity("warehouse", {"stock": 100}); r = t.tick()
        assert r["entities"] == 1
