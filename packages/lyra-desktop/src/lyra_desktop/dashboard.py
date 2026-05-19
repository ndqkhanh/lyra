"""
Dashboard - Real-time monitoring dashboard backend.

Features:
- System metrics
- Scan statistics
- Real-time updates
- Alert management
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SystemMetrics:
    """System metrics."""

    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_rx: float
    network_tx: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ScanStatistics:
    """Scan statistics."""

    total_scans: int
    active_scans: int
    completed_scans: int
    failed_scans: int
    total_findings: int
    critical_findings: int
    high_findings: int


class Dashboard:
    """
    Real-time monitoring dashboard.

    Features:
    - System metrics tracking
    - Scan statistics
    - Alert management
    """

    def __init__(self):
        """Initialize dashboard."""
        self.metrics_history: List[SystemMetrics] = []
        self.scan_stats = ScanStatistics(
            total_scans=0,
            active_scans=0,
            completed_scans=0,
            failed_scans=0,
            total_findings=0,
            critical_findings=0,
            high_findings=0,
        )

    def get_system_metrics(self) -> SystemMetrics:
        """
        Get current system metrics.

        Returns:
            System metrics
        """
        # Placeholder implementation
        # Real implementation would use psutil
        metrics = SystemMetrics(
            cpu_usage=25.5,
            memory_usage=60.2,
            disk_usage=45.8,
            network_rx=1024.0,
            network_tx=512.0,
        )

        self.metrics_history.append(metrics)

        # Keep last 100 metrics
        if len(self.metrics_history) > 100:
            self.metrics_history.pop(0)

        return metrics

    def get_scan_statistics(self) -> Dict[str, Any]:
        """
        Get scan statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_scans": self.scan_stats.total_scans,
            "active_scans": self.scan_stats.active_scans,
            "completed_scans": self.scan_stats.completed_scans,
            "failed_scans": self.scan_stats.failed_scans,
            "total_findings": self.scan_stats.total_findings,
            "critical_findings": self.scan_stats.critical_findings,
            "high_findings": self.scan_stats.high_findings,
            "success_rate": (
                self.scan_stats.completed_scans / self.scan_stats.total_scans * 100
                if self.scan_stats.total_scans > 0
                else 0
            ),
        }

    def update_scan_stats(
        self,
        status: str,
        findings: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Update scan statistics.

        Args:
            status: Scan status (started, completed, failed)
            findings: Scan findings
        """
        if status == "started":
            self.scan_stats.total_scans += 1
            self.scan_stats.active_scans += 1
        elif status == "completed":
            self.scan_stats.active_scans -= 1
            self.scan_stats.completed_scans += 1

            if findings:
                self.scan_stats.total_findings += len(findings)
                for finding in findings:
                    severity = finding.get("severity", "").upper()
                    if severity == "CRITICAL":
                        self.scan_stats.critical_findings += 1
                    elif severity == "HIGH":
                        self.scan_stats.high_findings += 1

        elif status == "failed":
            self.scan_stats.active_scans -= 1
            self.scan_stats.failed_scans += 1

    def get_metrics_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get metrics history.

        Args:
            limit: Maximum number of metrics to return

        Returns:
            Metrics history
        """
        recent_metrics = self.metrics_history[-limit:]

        return [
            {
                "cpu_usage": m.cpu_usage,
                "memory_usage": m.memory_usage,
                "disk_usage": m.disk_usage,
                "network_rx": m.network_rx,
                "network_tx": m.network_tx,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in recent_metrics
        ]

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get dashboard summary.

        Returns:
            Dashboard summary
        """
        current_metrics = self.get_system_metrics()
        scan_stats = self.get_scan_statistics()

        return {
            "system": {
                "cpu": current_metrics.cpu_usage,
                "memory": current_metrics.memory_usage,
                "disk": current_metrics.disk_usage,
            },
            "scans": scan_stats,
            "timestamp": datetime.now().isoformat(),
        }
