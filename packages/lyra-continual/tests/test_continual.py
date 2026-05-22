"""Tests for lyra-continual."""
from lyra_continual import ContinualLearner, AgentExperience, ExperienceReplay


class TestExperienceReplay:
    def test_store_and_sample(self):
        r = ExperienceReplay(capacity=100)
        for i in range(10):
            r.store(AgentExperience(task_id=f"task_{i%3}", state={}, action="test", result="ok"))
        samples = r.sample(batch_size=5, strategy="balanced")
        assert len(samples) <= 5
        assert r.stats["total_experiences"] == 10

    def test_balanced_sampling(self):
        r = ExperienceReplay(capacity=100)
        for i in range(30):
            r.store(AgentExperience(task_id=f"task_{i%2}", state={}, action="a", result="r"))
        samples = r.sample(batch_size=10, strategy="balanced")
        assert len(samples) <= 10


class TestContinualLearner:
    def test_learn_task(self):
        cl = ContinualLearner()
        result = cl.learn_task("task_1", [
            AgentExperience(task_id="task_1", state={}, action="a", result="r", reward=1.0)
            for _ in range(5)
        ])
        assert result["task"] == "task_1"
        assert result["total_experiences"] == 5
        assert cl.task_count == 1

    def test_multiple_tasks(self):
        cl = ContinualLearner()
        for t in range(3):
            cl.learn_task(f"task_{t}", [
                AgentExperience(task_id=f"task_{t}", state={}, action="a", result="r")
                for _ in range(5)
            ])
        assert cl.task_count == 3
