"""
Tests for Load Balancer.
"""

import pytest
from src.coordination import LoadBalancer
from src.agents import CodeAgent, ResearchAgent, TestAgent, ReviewAgent
from src.core.task import Task, TaskType


class TestLoadBalancer:
    """Test LoadBalancer class."""

    def test_load_balancer_creation(self):
        """Test load balancer creation."""
        balancer = LoadBalancer()
        
        assert balancer.max_tasks_per_agent == 5
        assert len(balancer.agent_loads) == 0

    def test_load_balancer_with_max_tasks(self):
        """Test load balancer with custom max tasks."""
        balancer = LoadBalancer(max_tasks_per_agent=10)
        
        assert balancer.max_tasks_per_agent == 10

    def test_get_agent_load(self):
        """Test getting agent load."""
        balancer = LoadBalancer()
        agent = CodeAgent()
        
        load = balancer.get_agent_load(agent)
        
        assert load.agent_id == "code_agent"
        assert load.current_tasks == 0
        assert load.load_percentage == 0.0

    def test_get_agent_load_with_task(self):
        """Test getting load for busy agent."""
        balancer = LoadBalancer()
        agent = CodeAgent()
        
        # Simulate agent with current task
        agent.current_task = Task(type=TaskType.CODE_GENERATION, description="Task")
        
        load = balancer.get_agent_load(agent)
        
        assert load.current_tasks == 1
        assert load.load_percentage == 20.0  # 1/5 * 100

    def test_get_least_loaded_agent(self):
        """Test getting least loaded agent."""
        balancer = LoadBalancer()
        
        agent1 = CodeAgent()
        agent2 = ResearchAgent()
        agent3 = TestAgent()
        
        # Make agent1 busy
        agent1.current_task = Task(type=TaskType.CODE_GENERATION, description="Task")
        
        agents = [agent1, agent2, agent3]
        least_loaded = balancer.get_least_loaded_agent(agents)
        
        assert least_loaded is not None
        assert least_loaded.agent_id in ["research_agent", "test_agent"]

    def test_get_least_loaded_no_agents(self):
        """Test getting least loaded with no agents."""
        balancer = LoadBalancer()
        
        least_loaded = balancer.get_least_loaded_agent([])
        
        assert least_loaded is None

    def test_get_least_loaded_all_busy(self):
        """Test getting least loaded when all at capacity."""
        balancer = LoadBalancer(max_tasks_per_agent=1)
        
        agent1 = CodeAgent()
        agent2 = ResearchAgent()
        
        # Make both busy
        agent1.current_task = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        agent2.current_task = Task(type=TaskType.RESEARCH, description="Task 2")
        
        least_loaded = balancer.get_least_loaded_agent([agent1, agent2])
        
        assert least_loaded is None

    def test_is_agent_available(self):
        """Test checking if agent is available."""
        balancer = LoadBalancer(max_tasks_per_agent=2)
        agent = CodeAgent()
        
        assert balancer.is_agent_available(agent) is True
        
        # Make agent busy
        agent.current_task = Task(type=TaskType.CODE_GENERATION, description="Task")
        
        assert balancer.is_agent_available(agent) is True
        
        # Simulate at capacity (would need to track multiple tasks in real impl)
        balancer.max_tasks_per_agent = 1
        assert balancer.is_agent_available(agent) is False

    def test_get_available_agents(self):
        """Test getting all available agents."""
        balancer = LoadBalancer(max_tasks_per_agent=1)
        
        agent1 = CodeAgent()
        agent2 = ResearchAgent()
        agent3 = TestAgent()
        
        # Make agent1 busy
        agent1.current_task = Task(type=TaskType.CODE_GENERATION, description="Task")
        
        agents = [agent1, agent2, agent3]
        available = balancer.get_available_agents(agents)
        
        assert len(available) == 2
        assert agent1 not in available

    def test_balance_load(self):
        """Test load balancing analysis."""
        balancer = LoadBalancer()
        
        agents = [CodeAgent(), ResearchAgent(), TestAgent()]
        
        result = balancer.balance_load(agents)
        
        assert "average_load" in result
        assert "max_load" in result
        assert "min_load" in result
        assert "imbalance" in result
        assert "suggestions" in result

    def test_balance_load_no_agents(self):
        """Test load balancing with no agents."""
        balancer = LoadBalancer()
        
        result = balancer.balance_load([])
        
        assert result == {"suggestions": []}

    def test_record_load_snapshot(self):
        """Test recording load snapshots."""
        balancer = LoadBalancer()
        
        agents = [CodeAgent(), ResearchAgent()]
        
        balancer.record_load_snapshot(agents)
        
        assert len(balancer.load_history) == 1

    def test_load_snapshot_limit(self):
        """Test load snapshot history limit."""
        balancer = LoadBalancer()
        
        agents = [CodeAgent()]
        
        for i in range(150):
            balancer.record_load_snapshot(agents)
        
        assert len(balancer.load_history) == 100

    def test_get_statistics(self):
        """Test getting load statistics."""
        balancer = LoadBalancer()
        
        agents = [CodeAgent(), ResearchAgent(), TestAgent()]
        
        # Get loads to populate cache
        for agent in agents:
            balancer.get_agent_load(agent)
        
        stats = balancer.get_statistics()
        
        assert stats["total_agents"] == 3
        assert stats["max_tasks_per_agent"] == 5
        assert "total_current_tasks" in stats
        assert "average_load_percentage" in stats
        assert "agents" in stats

    def test_get_statistics_empty(self):
        """Test statistics with no agents."""
        balancer = LoadBalancer()
        
        stats = balancer.get_statistics()
        
        assert stats["total_agents"] == 0

    def test_get_load_trends(self):
        """Test load trend analysis."""
        balancer = LoadBalancer()
        
        agents = [CodeAgent()]
        
        # Record multiple snapshots
        for i in range(15):
            balancer.record_load_snapshot(agents)
        
        trends = balancer.get_load_trends()
        
        assert "trend" in trends
        assert trends["trend"] in ["increasing", "decreasing", "stable"]

    def test_get_load_trends_insufficient_data(self):
        """Test trends with insufficient data."""
        balancer = LoadBalancer()
        
        trends = balancer.get_load_trends()
        
        assert trends["trend"] == "insufficient_data"
