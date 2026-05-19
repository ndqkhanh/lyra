"""
Adaptive task decomposition for research coordination.

Adjusts task graph based on intermediate results.
"""
from __future__ import annotations

from typing import Any, Dict, List

from lyra_research.coordination import Task, TaskGraph


class AdaptiveTaskGraph(TaskGraph):
    """
    Task graph with adaptive decomposition.

    Adjusts task graph based on intermediate results:
    - Adds more discovery tasks if insufficient sources
    - Adds falsification tasks if contradictions detected
    - Adjusts analysis depth based on source quality
    """

    def __init__(self) -> None:
        super().__init__()
        self.adaptation_history: List[Dict[str, Any]] = []

    def adapt_graph(self, results: List[Any]) -> List[Task]:
        """
        Adjust task graph based on intermediate results.

        Args:
            results: List of intermediate results (sources, analyses, etc.)

        Returns:
            List of new tasks to add
        """
        new_tasks: List[Task] = []

        # Check if discovery found insufficient sources
        if self._insufficient_sources(results):
            discovery_tasks = self._create_additional_discovery_tasks()
            new_tasks.extend(discovery_tasks)
            self.adaptation_history.append({
                "reason": "insufficient_sources",
                "tasks_added": len(discovery_tasks),
            })

        # Check if contradictions detected
        if self._contradictions_detected(results):
            falsification_tasks = self._create_falsification_tasks(results)
            new_tasks.extend(falsification_tasks)
            self.adaptation_history.append({
                "reason": "contradictions_detected",
                "tasks_added": len(falsification_tasks),
            })

        # Check if low-quality sources need deeper analysis
        if self._needs_deeper_analysis(results):
            analysis_tasks = self._create_deeper_analysis_tasks(results)
            new_tasks.extend(analysis_tasks)
            self.adaptation_history.append({
                "reason": "low_quality_sources",
                "tasks_added": len(analysis_tasks),
            })

        return new_tasks

    def _insufficient_sources(self, results: List[Any]) -> bool:
        """
        Check if discovery found insufficient sources.

        Args:
            results: List of results

        Returns:
            True if insufficient sources (<10 total)
        """
        source_count = 0

        for result in results:
            if isinstance(result, dict):
                # Check for sources in dict
                if "sources" in result:
                    source_count += len(result["sources"])
                elif "source_count" in result:
                    source_count += result["source_count"]

        return source_count < 10

    def _contradictions_detected(self, results: List[Any]) -> bool:
        """
        Check if contradictions were detected.

        Args:
            results: List of results

        Returns:
            True if contradictions found
        """
        for result in results:
            if isinstance(result, dict):
                if "contradictions" in result and result["contradictions"]:
                    return True
                if "contradiction_count" in result and result["contradiction_count"] > 0:
                    return True

        return False

    def _needs_deeper_analysis(self, results: List[Any]) -> bool:
        """
        Check if sources need deeper analysis.

        Args:
            results: List of results

        Returns:
            True if low-quality sources detected
        """
        for result in results:
            if isinstance(result, dict):
                if "quality_score" in result and result["quality_score"] < 0.6:
                    return True
                if "confidence" in result and result["confidence"] < 0.7:
                    return True

        return False

    def _create_additional_discovery_tasks(self) -> List[Task]:
        """
        Create additional discovery tasks.

        Returns:
            List of new discovery tasks
        """
        tasks = []

        # Add 2 more discovery tasks with different sources
        for i in range(2):
            task = Task(
                agent_type="discovery",
                timeout_seconds=300,
                max_retries=2,
            )
            tasks.append(task)

        return tasks

    def _create_falsification_tasks(self, results: List[Any]) -> List[Task]:
        """
        Create falsification tasks for contradictions.

        Args:
            results: List of results with contradictions

        Returns:
            List of falsification tasks
        """
        tasks = []

        # Extract contradictions
        contradiction_count = 0
        for result in results:
            if isinstance(result, dict):
                if "contradictions" in result:
                    contradiction_count += len(result["contradictions"])
                elif "contradiction_count" in result:
                    contradiction_count += result["contradiction_count"]

        # Create 1 falsification task per 2 contradictions
        task_count = max(1, contradiction_count // 2)

        for i in range(task_count):
            task = Task(
                agent_type="falsification",
                timeout_seconds=600,
                max_retries=1,
            )
            tasks.append(task)

        return tasks

    def _create_deeper_analysis_tasks(self, results: List[Any]) -> List[Task]:
        """
        Create deeper analysis tasks for low-quality sources.

        Args:
            results: List of results

        Returns:
            List of analysis tasks
        """
        tasks = []

        # Add 2 more analysis tasks
        for i in range(2):
            task = Task(
                agent_type="analysis",
                timeout_seconds=600,
                max_retries=2,
            )
            tasks.append(task)

        return tasks

    def get_adaptation_history(self) -> List[Dict[str, Any]]:
        """
        Get history of adaptations.

        Returns:
            List of adaptation events
        """
        return self.adaptation_history.copy()
