from lyra_gateway import LLMGateway
class TestLLMGateway:
    def test_register_and_route(self):
        g = LLMGateway(); g.register_provider("openai", 0.01); g.register_provider("anthropic", 0.015)
        p = g.route("test task", "low"); assert p is not None
    def test_budget(self):
        g = LLMGateway(); g.register_provider("openai", 0.01); g.route("task"); g.route("task")
        assert g.check_budget()
    def test_fallback(self):
        g = LLMGateway(); g.register_provider("openai", 0.01); g.providers["openai"].is_available = False
        g.register_provider("anthropic", 0.015); g.config.fallback_providers = ["anthropic"]
        f = g.fallback("openai"); assert f.name == "anthropic"
