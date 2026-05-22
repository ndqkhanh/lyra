"""Tests for lyra-economy."""
from lyra_economy import AgentEconomy, TokenWallet


class TestTokenWallet:
    def test_initial_balance(self):
        w = TokenWallet("agent_1", 100.0)
        assert w.balance == 100.0

    def test_spend_sufficient(self):
        w = TokenWallet("agent_1", 100.0)
        assert w.spend(50.0, "test")
        assert w.balance == 50.0

    def test_spend_insufficient(self):
        w = TokenWallet("agent_1", 10.0)
        assert not w.spend(50.0, "test")
        assert w.balance == 10.0

    def test_earn(self):
        w = TokenWallet("agent_1", 100.0)
        w.earn(50.0, "payment")
        assert w.balance == 150.0


class TestAgentEconomy:
    def test_register_agent(self):
        eco = AgentEconomy()
        w = eco.register_agent("agent_1", 100.0)
        assert w.balance == 100.0
        assert eco.stats["registered_agents"] == 1

    def test_list_service(self):
        eco = AgentEconomy()
        eco.register_agent("agent_1", 100.0)
        listing = eco.list_service("agent_1", "code_review", "Review Python code", 10.0)
        assert listing is not None
        assert listing.price == 10.0

    def test_search_services(self):
        eco = AgentEconomy()
        eco.register_agent("agent_1")
        eco.list_service("agent_1", "code_review", "Review Python code", 10.0)
        eco.list_service("agent_1", "testing", "Run test suites", 15.0)
        results = eco.search_services("code")
        assert len(results) == 1

    def test_buy_service(self):
        eco = AgentEconomy()
        eco.register_agent("seller", 100.0)
        eco.register_agent("buyer", 50.0)
        listing = eco.list_service("seller", "code_review", "Review code", 10.0)
        result = eco.buy_service(listing.id, "buyer")
        assert result.success
        assert eco.wallets["buyer"].balance == 40.0
        assert eco.wallets["seller"].balance == 110.0

    def test_buy_insufficient_funds(self):
        eco = AgentEconomy()
        eco.register_agent("seller", 100.0)
        eco.register_agent("buyer", 5.0)
        listing = eco.list_service("seller", "code_review", "Review code", 10.0)
        result = eco.buy_service(listing.id, "buyer")
        assert not result.success
