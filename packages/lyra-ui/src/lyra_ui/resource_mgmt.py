"""
Resource Management - Memory and resource monitoring.

Features:
- Memory usage monitoring
- Memory leak detection
- Automatic garbage collection
- Resource cleanup
- Disk space management
- Network bandwidth optimization
"""

import gc
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ResourceUsage:
    """Resource usage snapshot."""

    timestamp: datetime
    memory_mb: float
    cpu_percent: float
    disk_usage_percent: float
    open_files: int


class ResourceMonitor:
    """
    Resource monitor.

    Features:
    - Track resource usage
    - Detect anomalies
    - Generate alerts
    - Historical data
    """

    def __init__(self, alert_threshold_mb: float = 200.0):
        """
        Initialize resource monitor.

        Args:
            alert_threshold_mb: Memory alert threshold in MB
        """
        self.alert_threshold_mb = alert_threshold_mb
        self.history: list[ResourceUsage] = []
        self.max_history = 1000

    def get_current_usage(self) -> ResourceUsage:
        """
        Get current resource usage.

        Returns:
            Resource usage snapshot
        """
        import psutil

        process = psutil.Process(os.getpid())

        # Memory usage
        memory_mb = process.memory_info().rss / 1024 / 1024

        # CPU usage
        cpu_percent = process.cpu_percent(interval=0.1)

        # Disk usage
        disk = shutil.disk_usage("/")
        disk_usage_percent = (disk.used / disk.total) * 100

        # Open files
        try:
            open_files = len(process.open_files())
        except Exception:
            open_files = 0

        return ResourceUsage(
            timestamp=datetime.now(),
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            disk_usage_percent=disk_usage_percent,
            open_files=open_files,
        )

    def record_usage(self):
        """Record current usage."""
        usage = self.get_current_usage()
        self.history.append(usage)

        # Keep only recent history
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def is_over_threshold(self) -> bool:
        """
        Check if over memory threshold.

        Returns:
            True if over threshold
        """
        if not self.history:
            return False
        return self.history[-1].memory_mb > self.alert_threshold_mb

    def get_stats(self) -> dict[str, float]:
        """
        Get resource statistics.

        Returns:
            Statistics dictionary
        """
        if not self.history:
            return {
                "memory_current": 0.0,
                "memory_average": 0.0,
                "memory_peak": 0.0,
                "cpu_average": 0.0,
                "disk_usage": 0.0,
            }

        memory_values = [h.memory_mb for h in self.history]
        cpu_values = [h.cpu_percent for h in self.history]

        return {
            "memory_current": self.history[-1].memory_mb,
            "memory_average": sum(memory_values) / len(memory_values),
            "memory_peak": max(memory_values),
            "cpu_average": sum(cpu_values) / len(cpu_values),
            "disk_usage": self.history[-1].disk_usage_percent,
        }


class MemoryLeakDetector:
    """
    Memory leak detector.

    Features:
    - Track object counts
    - Detect growing objects
    - Generate reports
    """

    def __init__(self):
        """Initialize leak detector."""
        self.snapshots: list[dict[str, int]] = []
        self.max_snapshots = 10

    def take_snapshot(self):
        """Take memory snapshot."""
        # Count objects by type
        counts: dict[str, int] = {}
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            counts[obj_type] = counts.get(obj_type, 0) + 1

        self.snapshots.append(counts)

        # Keep only recent snapshots
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots.pop(0)

    def detect_leaks(self) -> list[tuple[str, int]]:
        """
        Detect potential memory leaks.

        Returns:
            List of (type_name, growth) tuples
        """
        if len(self.snapshots) < 2:
            return []

        # Compare first and last snapshot
        first = self.snapshots[0]
        last = self.snapshots[-1]

        leaks = []
        for obj_type, count in last.items():
            if obj_type in first:
                growth = count - first[obj_type]
                # Consider it a leak if grown by more than 100 objects
                if growth > 100:
                    leaks.append((obj_type, growth))

        # Sort by growth
        leaks.sort(key=lambda x: x[1], reverse=True)
        return leaks


class ResourceCleaner:
    """
    Resource cleaner.

    Features:
    - Automatic cleanup
    - Garbage collection
    - File cleanup
    - Cache cleanup
    """

    def __init__(self, temp_dir: Path | None = None):
        """
        Initialize resource cleaner.

        Args:
            temp_dir: Temporary directory to clean
        """
        self.temp_dir = temp_dir or Path.home() / ".lyra" / "temp"

    def cleanup_memory(self):
        """Force garbage collection."""
        gc.collect()

    def cleanup_temp_files(self, max_age_days: int = 7):
        """
        Clean up old temporary files.

        Args:
            max_age_days: Maximum file age in days
        """
        if not self.temp_dir.exists():
            return

        now = datetime.now()
        for file in self.temp_dir.rglob("*"):
            if not file.is_file():
                continue

            # Check file age
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            age_days = (now - mtime).days

            if age_days > max_age_days:
                try:
                    file.unlink()
                except Exception:
                    pass

    def cleanup_cache(self, cache_dir: Path | None = None):
        """
        Clean up cache directory.

        Args:
            cache_dir: Cache directory to clean
        """
        cache_dir = cache_dir or Path.home() / ".lyra" / "cache"

        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

    def cleanup_all(self):
        """Clean up all resources."""
        self.cleanup_memory()
        self.cleanup_temp_files()
        self.cleanup_cache()


class DiskSpaceManager:
    """
    Disk space manager.

    Features:
    - Monitor disk usage
    - Automatic cleanup
    - Space alerts
    """

    def __init__(self, data_dir: Path | None = None, threshold_percent: float = 90.0):
        """
        Initialize disk space manager.

        Args:
            data_dir: Data directory to manage
            threshold_percent: Alert threshold percentage
        """
        self.data_dir = data_dir or Path.home() / ".lyra"
        self.threshold_percent = threshold_percent

    def get_disk_usage(self) -> dict[str, float]:
        """
        Get disk usage statistics.

        Returns:
            Usage statistics
        """
        disk = shutil.disk_usage(self.data_dir)

        return {
            "total_gb": disk.total / (1024**3),
            "used_gb": disk.used / (1024**3),
            "free_gb": disk.free / (1024**3),
            "percent": (disk.used / disk.total) * 100,
        }

    def is_over_threshold(self) -> bool:
        """
        Check if over threshold.

        Returns:
            True if over threshold
        """
        usage = self.get_disk_usage()
        return usage["percent"] > self.threshold_percent

    def get_directory_size(self, path: Path | None = None) -> int:
        """
        Get directory size in bytes.

        Args:
            path: Directory path (uses data_dir if None)

        Returns:
            Size in bytes
        """
        path = path or self.data_dir

        if not path.exists():
            return 0

        total = 0
        for file in path.rglob("*"):
            if file.is_file():
                total += file.stat().st_size

        return total

    def cleanup_old_files(self, max_age_days: int = 30):
        """
        Clean up old files.

        Args:
            max_age_days: Maximum file age in days
        """
        if not self.data_dir.exists():
            return

        now = datetime.now()
        for file in self.data_dir.rglob("*"):
            if not file.is_file():
                continue

            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            age_days = (now - mtime).days

            if age_days > max_age_days:
                try:
                    file.unlink()
                except Exception:
                    pass


class BandwidthOptimizer:
    """
    Network bandwidth optimizer.

    Features:
    - Request throttling
    - Compression
    - Batch requests
    """

    def __init__(self, max_requests_per_second: int = 10):
        """
        Initialize bandwidth optimizer.

        Args:
            max_requests_per_second: Maximum requests per second
        """
        self.max_requests_per_second = max_requests_per_second
        self.request_times: list[float] = []

    def can_make_request(self) -> bool:
        """
        Check if can make request.

        Returns:
            True if within rate limit
        """
        import time

        now = time.time()

        # Remove old requests (older than 1 second)
        self.request_times = [t for t in self.request_times if now - t < 1.0]

        # Check rate limit
        return len(self.request_times) < self.max_requests_per_second

    def record_request(self):
        """Record request."""
        import time

        self.request_times.append(time.time())

    def get_stats(self) -> dict[str, float]:
        """
        Get bandwidth statistics.

        Returns:
            Statistics dictionary
        """
        import time

        now = time.time()
        recent = [t for t in self.request_times if now - t < 1.0]

        return {
            "requests_per_second": len(recent),
            "max_requests_per_second": self.max_requests_per_second,
            "utilization": len(recent) / self.max_requests_per_second,
        }
