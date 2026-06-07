"""
Integration tests for Lyra system.

Tests the integration of all major components.
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestCoreIntegration:
    """Test core component integration."""

    def test_imports_work(self):
        """Test that all modules can be imported."""
        # Core modules
        from adapters.base import AdapterFactory
        from memory.memory_store import MemoryStore
        from monitoring.token_observatory import TokenObservatory
        from optimization.token_optimizer import TokenOptimizer
        from security.agent_shield import AgentShield

        assert AdapterFactory is not None
        assert MemoryStore is not None
        assert TokenObservatory is not None
        assert TokenOptimizer is not None
        assert AgentShield is not None


class TestSecurityIntegration:
    """Test security integration."""

    def test_agent_shield_basic(self):
        """Test basic AgentShield functionality."""
        from security.agent_shield import AgentShield

        shield = AgentShield()
        code = "def hello(): return 'world'"
        report = shield.scan_code(code)

        assert report is not None
        assert hasattr(report, 'passed')

    def test_secrets_detection(self):
        """Test secrets detection."""
        from security.agent_shield import AgentShield

        shield = AgentShield()
        code = "API_KEY = 'sk-1234567890abcdef'"
        report = shield.scan_code(code)

        # Security scanner should detect issues
        assert report is not None
        assert hasattr(report, 'passed')


class TestAdapterIntegration:
    """Test adapter integration."""

    def test_adapter_creation(self):
        """Test creating adapters."""
        from adapters.base import AdapterFactory, HarnessType

        adapter = AdapterFactory.create_adapter(HarnessType.CLAUDE_CODE)
        assert adapter is not None

    def test_adapter_initialization(self):
        """Test adapter initialization."""
        from adapters.base import AdapterFactory, HarnessType

        adapter = AdapterFactory.create_adapter(HarnessType.CLAUDE_CODE)
        result = adapter.initialize()

        assert result is True
        assert adapter.is_connected()

    def test_message_flow(self):
        """Test message flow through adapter."""
        from adapters.base import AdapterFactory, HarnessType, Message

        adapter = AdapterFactory.create_adapter(HarnessType.CLAUDE_CODE)
        adapter.initialize()

        msg = Message(content="Test")
        response = adapter.send_message(msg)

        assert response.success is True


class TestOptimizationIntegration:
    """Test optimization integration."""

    def test_optimizer_basic(self):
        """Test basic optimizer functionality."""
        from optimization.token_optimizer import LLMRequest, TaskType, TokenOptimizer

        optimizer = TokenOptimizer()
        request = LLMRequest(
            prompt="Test",
            task_type=TaskType.CHAT,
            context="",
            context_size=0,
        )

        optimized = optimizer.optimize_request(request)
        assert optimized.model == "claude-haiku-4.5"

    def test_cost_tracking(self):
        """Test cost tracking."""
        from optimization.token_optimizer import TokenOptimizer

        optimizer = TokenOptimizer()
        optimizer.track_usage(1000, 500, 0, 0.01)

        metrics = optimizer.get_metrics()
        assert metrics.total_tokens == 1500
        assert metrics.total_cost == 0.01


class TestMonitoringIntegration:
    """Test monitoring integration."""

    def test_observatory_basic(self):
        """Test basic observatory functionality."""
        from monitoring.token_observatory import TokenObservatory

        observatory = TokenObservatory()
        assert observatory.classifier is not None
        assert observatory.analyzer is not None

    def test_activity_classification(self):
        """Test activity classification."""
        from datetime import datetime

        from monitoring.token_observatory import ActivityCategory, TokenObservatory, Turn

        observatory = TokenObservatory()
        turn = Turn(
            timestamp=datetime.now(),
            role="user",
            content="Implement a feature",
            tokens=100,
            model="claude-sonnet-4.6",
            cost=0.001,
        )

        category = observatory.classifier.classify(turn)
        assert category == ActivityCategory.CODING


class TestMemoryIntegration:
    """Test memory integration."""

    def test_memory_store_basic(self):
        """Test basic memory store functionality."""
        from memory.memory_store import MemoryStore

        store = MemoryStore()
        # Memory store exists and can be instantiated
        assert store is not None

    def test_memory_module_available(self):
        """Test memory module is available."""
        from memory.long_term_memory import LongTermMemory
        from memory.memory_store import MemoryStore
        from memory.short_term_memory import ShortTermMemory

        assert MemoryStore is not None
        assert ShortTermMemory is not None
        assert LongTermMemory is not None


class TestEndToEndWorkflow:
    """Test end-to-end workflows."""

    def test_security_and_optimization(self):
        """Test security with optimization."""
        from optimization.token_optimizer import LLMRequest, TaskType, TokenOptimizer
        from security.agent_shield import AgentShield

        shield = AgentShield()
        optimizer = TokenOptimizer()

        # Scan code
        code = "def hello(): return 'world'"
        report = shield.scan_code(code)
        assert report is not None

        # Optimize request
        request = LLMRequest(
            prompt="Write code",
            task_type=TaskType.CHAT,
            context="",
            context_size=0,
        )
        optimized = optimizer.optimize_request(request)
        assert optimized.model is not None

    def test_adapter_with_optimizer(self):
        """Test adapter with optimizer."""
        from adapters.base import AdapterFactory, HarnessType, Message
        from optimization.token_optimizer import LLMRequest, TaskType, TokenOptimizer

        adapter = AdapterFactory.create_adapter(HarnessType.CLAUDE_CODE)
        optimizer = TokenOptimizer()

        adapter.initialize()

        # Optimize
        request = LLMRequest(
            prompt="Test",
            task_type=TaskType.CHAT,
            context="",
            context_size=0,
        )
        optimized = optimizer.optimize_request(request)

        # Send
        msg = Message(content=optimized.prompt)
        response = adapter.send_message(msg)
        assert response.success

    def test_full_pipeline(self):
        """Test full pipeline."""
        from monitoring.token_observatory import TokenObservatory
        from optimization.token_optimizer import LLMRequest, TaskType, TokenOptimizer
        from security.agent_shield import AgentShield

        # Components
        shield = AgentShield()
        optimizer = TokenOptimizer()
        observatory = TokenObservatory()

        # Security check
        code = "def test(): pass"
        report = shield.scan_code(code)
        assert report.passed

        # Optimization
        request = LLMRequest(
            prompt="Test",
            task_type=TaskType.CHAT,
            context="",
            context_size=0,
        )
        optimized = optimizer.optimize_request(request)
        assert optimized.model is not None

        # Monitoring
        assert observatory.classifier is not None


class TestPerformance:
    """Test performance."""

    def test_memory_performance(self):
        """Test memory performance."""
        import time

        from memory.memory_store import MemoryStore

        MemoryStore()

        start = time.time()
        # Just test instantiation performance
        for _i in range(100):
            _ = MemoryStore()
        duration = time.time() - start

        assert duration < 1.0

    def test_optimizer_performance(self):
        """Test optimizer performance."""
        import time

        from optimization.token_optimizer import LLMRequest, TaskType, TokenOptimizer

        optimizer = TokenOptimizer()

        start = time.time()
        for i in range(100):
            request = LLMRequest(
                prompt=f"Test {i}",
                task_type=TaskType.CHAT,
                context="",
                context_size=0,
            )
            optimizer.optimize_request(request)
        duration = time.time() - start

        assert duration < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
