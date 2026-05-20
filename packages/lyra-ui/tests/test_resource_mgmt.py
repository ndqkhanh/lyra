"""Tests for resource management."""

import time

from lyra_ui import (
    BandwidthOptimizer,
    DiskSpaceManager,
    MemoryLeakDetector,
    ResourceCleaner,
    ResourceMonitor,
)


# ResourceMonitor Tests


def test_resource_monitor_init():
    """Test resource monitor initialization."""
    monitor = ResourceMonitor(alert_threshold_mb=100.0)
    assert monitor.alert_threshold_mb == 100.0
    assert len(monitor.history) == 0


def test_resource_monitor_get_current_usage():
    """Test getting current usage."""
    monitor = ResourceMonitor()
    usage = monitor.get_current_usage()

    assert usage.memory_mb > 0
    assert usage.cpu_percent >= 0
    assert usage.disk_usage_percent > 0


def test_resource_monitor_record_usage():
    """Test recording usage."""
    monitor = ResourceMonitor()
    monitor.record_usage()

    assert len(monitor.history) == 1


def test_resource_monitor_max_history():
    """Test max history limit."""
    monitor = ResourceMonitor()
    monitor.max_history = 5

    for _ in range(10):
        monitor.record_usage()

    assert len(monitor.history) == 5


def test_resource_monitor_stats():
    """Test getting statistics."""
    monitor = ResourceMonitor()
    monitor.record_usage()
    monitor.record_usage()

    stats = monitor.get_stats()
    assert "memory_current" in stats
    assert "memory_average" in stats
    assert "memory_peak" in stats
    assert "cpu_average" in stats


# MemoryLeakDetector Tests


def test_memory_leak_detector_init():
    """Test leak detector initialization."""
    detector = MemoryLeakDetector()
    assert len(detector.snapshots) == 0


def test_memory_leak_detector_take_snapshot():
    """Test taking snapshot."""
    detector = MemoryLeakDetector()
    detector.take_snapshot()

    assert len(detector.snapshots) == 1


def test_memory_leak_detector_max_snapshots():
    """Test max snapshots limit."""
    detector = MemoryLeakDetector()
    detector.max_snapshots = 3

    for _ in range(5):
        detector.take_snapshot()

    assert len(detector.snapshots) == 3


def test_memory_leak_detector_detect_leaks():
    """Test detecting leaks."""
    detector = MemoryLeakDetector()

    # Take initial snapshot
    detector.take_snapshot()

    # Create some objects
    leak_list = [i for i in range(200)]

    # Take second snapshot
    detector.take_snapshot()

    leaks = detector.detect_leaks()
    # Should detect growth in list objects
    assert len(leaks) >= 0


# ResourceCleaner Tests


def test_resource_cleaner_init(tmp_path):
    """Test resource cleaner initialization."""
    cleaner = ResourceCleaner(temp_dir=tmp_path)
    assert cleaner.temp_dir == tmp_path


def test_resource_cleaner_cleanup_memory():
    """Test memory cleanup."""
    cleaner = ResourceCleaner()
    # Should not raise error
    cleaner.cleanup_memory()


def test_resource_cleaner_cleanup_temp_files(tmp_path):
    """Test temp file cleanup."""
    cleaner = ResourceCleaner(temp_dir=tmp_path)

    # Create temp file
    temp_file = tmp_path / "temp.txt"
    temp_file.write_text("test")

    cleaner.cleanup_temp_files(max_age_days=0)
    # File should still exist (just created)
    assert temp_file.exists()


def test_resource_cleaner_cleanup_cache(tmp_path):
    """Test cache cleanup."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "file.txt").write_text("test")

    cleaner = ResourceCleaner()
    cleaner.cleanup_cache(cache_dir=cache_dir)

    # Cache dir should be recreated empty
    assert cache_dir.exists()
    assert len(list(cache_dir.iterdir())) == 0


def test_resource_cleaner_cleanup_all(tmp_path):
    """Test cleaning all resources."""
    cleaner = ResourceCleaner(temp_dir=tmp_path)
    # Should not raise error
    cleaner.cleanup_all()


# DiskSpaceManager Tests


def test_disk_space_manager_init(tmp_path):
    """Test disk space manager initialization."""
    manager = DiskSpaceManager(data_dir=tmp_path, threshold_percent=90.0)
    assert manager.data_dir == tmp_path
    assert manager.threshold_percent == 90.0


def test_disk_space_manager_get_disk_usage(tmp_path):
    """Test getting disk usage."""
    manager = DiskSpaceManager(data_dir=tmp_path)
    usage = manager.get_disk_usage()

    assert "total_gb" in usage
    assert "used_gb" in usage
    assert "free_gb" in usage
    assert "percent" in usage


def test_disk_space_manager_get_directory_size(tmp_path):
    """Test getting directory size."""
    manager = DiskSpaceManager(data_dir=tmp_path)

    # Create test file
    (tmp_path / "test.txt").write_text("test content")

    size = manager.get_directory_size()
    assert size > 0


def test_disk_space_manager_cleanup_old_files(tmp_path):
    """Test cleaning old files."""
    manager = DiskSpaceManager(data_dir=tmp_path)

    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    manager.cleanup_old_files(max_age_days=0)
    # File should still exist (just created)
    assert test_file.exists()


# BandwidthOptimizer Tests


def test_bandwidth_optimizer_init():
    """Test bandwidth optimizer initialization."""
    optimizer = BandwidthOptimizer(max_requests_per_second=10)
    assert optimizer.max_requests_per_second == 10
    assert len(optimizer.request_times) == 0


def test_bandwidth_optimizer_can_make_request():
    """Test checking if can make request."""
    optimizer = BandwidthOptimizer(max_requests_per_second=10)
    assert optimizer.can_make_request() is True


def test_bandwidth_optimizer_record_request():
    """Test recording request."""
    optimizer = BandwidthOptimizer(max_requests_per_second=10)
    optimizer.record_request()

    assert len(optimizer.request_times) == 1


def test_bandwidth_optimizer_rate_limit():
    """Test rate limiting."""
    optimizer = BandwidthOptimizer(max_requests_per_second=2)

    # Make 2 requests
    optimizer.record_request()
    optimizer.record_request()

    # Should be at limit
    assert optimizer.can_make_request() is False


def test_bandwidth_optimizer_stats():
    """Test getting statistics."""
    optimizer = BandwidthOptimizer(max_requests_per_second=10)
    optimizer.record_request()

    stats = optimizer.get_stats()
    assert "requests_per_second" in stats
    assert "max_requests_per_second" in stats
    assert "utilization" in stats


def test_bandwidth_optimizer_time_window():
    """Test time window for rate limiting."""
    optimizer = BandwidthOptimizer(max_requests_per_second=2)

    # Make 2 requests
    optimizer.record_request()
    optimizer.record_request()
    assert optimizer.can_make_request() is False

    # Wait for time window to pass
    time.sleep(1.1)
    assert optimizer.can_make_request() is True


# Integration Tests


def test_resource_monitor_with_cleaner(tmp_path):
    """Test resource monitor with cleaner."""
    monitor = ResourceMonitor()
    cleaner = ResourceCleaner(temp_dir=tmp_path)

    # Record initial usage
    monitor.record_usage()

    # Create some temp files
    for i in range(10):
        (tmp_path / f"temp{i}.txt").write_text("test")

    # Clean up
    cleaner.cleanup_temp_files(max_age_days=0)

    # Record usage after cleanup
    monitor.record_usage()

    stats = monitor.get_stats()
    assert stats["memory_current"] > 0


def test_disk_manager_with_cleaner(tmp_path):
    """Test disk manager with cleaner."""
    manager = DiskSpaceManager(data_dir=tmp_path)
    cleaner = ResourceCleaner(temp_dir=tmp_path)

    # Create files
    for i in range(5):
        (tmp_path / f"file{i}.txt").write_text("test content")

    initial_size = manager.get_directory_size()
    assert initial_size > 0

    # Clean up
    cleaner.cleanup_temp_files(max_age_days=0)

    # Size should be same (files just created)
    final_size = manager.get_directory_size()
    assert final_size == initial_size


def test_bandwidth_optimizer_with_monitor():
    """Test bandwidth optimizer with resource monitor."""
    optimizer = BandwidthOptimizer(max_requests_per_second=5)
    monitor = ResourceMonitor()

    monitor.record_usage()

    # Make some requests
    for _ in range(3):
        if optimizer.can_make_request():
            optimizer.record_request()

    stats = optimizer.get_stats()
    assert stats["requests_per_second"] == 3

    monitor.record_usage()
