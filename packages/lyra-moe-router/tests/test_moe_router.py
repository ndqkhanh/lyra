
from lyra_moe_router import MoERouter
class TestMoERouter:
    def test_register_and_route(self):
        r = MoERouter(); r.register("code_expert", "code"); r.register("math_expert", "math")
        result = r.route("write some code")
        assert len(result) >= 1
