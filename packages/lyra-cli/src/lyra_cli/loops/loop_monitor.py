"""Loop monitor - Monitor loop execution"""

from typing import Dict, Optional
from datetime import datetime


class LoopMonitor:
    """Monitors loop execution and health"""

    def __init__(self):
        self.metrics: Dict[str, Dict] = {}

    def record_iteration(self, loop_id: str, iteration: int, success: bool, duration: float):
        """Record iteration metrics"""
        if loop_id not in self.metrics:
            self.metrics[loop_id] = {
                "iterations": [],
                "total_iterations": 0,
                "successful_iterations": 0,
                "failed_iterations": 0,
                "total_duration": 0.0,
            }

        self.metrics[loop_id]["iterations"].append({
            "iteration": iteration,
            "success": success,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })

        self.metrics[loop_id]["total_iterations"] += 1
        if success:
            self.metrics[loop_id]["successful_iterations"] += 1
        else:
            self.metrics[loop_id]["failed_iterations"] += 1
        self.metrics[loop_id]["total_duration"] += duration

    def get_metrics(self, loop_id: str) -> Dict:
        """Get metrics for a loop"""
        return self.metrics.get(loop_id, {})

    def get_success_rate(self, loop_id: str) -> float:
        """Get success rate for a loop"""
        metrics = self.metrics.get(loop_id)
        if not metrics or metrics["total_iterations"] == 0:
            return 0.0

        return metrics["successful_iterations"] / metrics["total_iterations"]

    def get_average_duration(self, loop_id: str) -> float:
        """Get average iteration duration"""
        metrics = self.metrics.get(loop_id)
        if not metrics or metrics["total_iterations"] == 0:
            return 0.0

        return metrics["total_duration"] / metrics["total_iterations"]


# Global monitor
_monitor: Optional[LoopMonitor] = None


def get_monitor() -> LoopMonitor:
    """Get or create global monitor"""
    global _monitor
    if _monitor is None:
        _monitor = LoopMonitor()
    return _monitor
