"""Tests for lyra-spatial."""
from lyra_spatial import SpatialAgent, BoundingBox
class TestSpatialAgent:
    def test_distance(self):
        s = SpatialAgent()
        s.register_object("a", BoundingBox(0,0,0,1,1,1))
        s.register_object("b", BoundingBox(5,5,5,6,6,6))
        d = s.distance("a", "b")
        assert d is not None and d > 0
    def test_move(self):
        s = SpatialAgent(); s.move_to(10, 20, 30)
        assert s.position.x == 10
