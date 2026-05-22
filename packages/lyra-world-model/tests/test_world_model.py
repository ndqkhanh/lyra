from lyra_world_model import WorldModel, State, Action
class TestWorldModel:
    def test_predict(self):
        w = WorldModel(); s = State(variables={"x": 100})
        r = w.predict(s, Action("increment", {"by": 1}))
        assert r.step == 1
    def test_simulate(self):
        w = WorldModel(); s = State(variables={"count": 0})
        sim = w.simulate_plan(s, [Action("add", {}), Action("add", {})])
        assert len(sim.states) == 3
