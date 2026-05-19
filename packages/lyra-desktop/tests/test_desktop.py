"""Tests for desktop application backend."""

import pytest
from fastapi.testclient import TestClient

from lyra_desktop import APIServer, Dashboard


def test_api_server_init():
    """Test API server initialization."""
    server = APIServer()
    assert server.host == "127.0.0.1"
    assert server.port == 8000


def test_api_server_root():
    """Test root endpoint."""
    server = APIServer()
    client = TestClient(server.get_app())

    response = client.get("/")
    assert response.status_code == 200
    assert "Lyra Desktop API" in response.json()["message"]


def test_api_server_health():
    """Test health check endpoint."""
    server = APIServer()
    client = TestClient(server.get_app())

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_api_server_start_scan():
    """Test start scan endpoint."""
    server = APIServer()
    client = TestClient(server.get_app())

    response = client.post(
        "/api/scan",
        json={"target": "192.168.1.100", "scan_type": "full"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "started"


def test_api_server_get_scan_status():
    """Test get scan status endpoint."""
    server = APIServer()
    client = TestClient(server.get_app())

    response = client.get("/api/scan/test_scan_id")
    assert response.status_code == 200
    assert "status" in response.json()


def test_api_server_list_scans():
    """Test list scans endpoint."""
    server = APIServer()
    client = TestClient(server.get_app())

    response = client.get("/api/scans")
    assert response.status_code == 200
    assert "scans" in response.json()


def test_dashboard_init():
    """Test dashboard initialization."""
    dashboard = Dashboard()
    assert len(dashboard.metrics_history) == 0


def test_dashboard_system_metrics():
    """Test system metrics."""
    dashboard = Dashboard()

    metrics = dashboard.get_system_metrics()

    assert metrics.cpu_usage > 0
    assert metrics.memory_usage > 0
    assert len(dashboard.metrics_history) == 1


def test_dashboard_scan_statistics():
    """Test scan statistics."""
    dashboard = Dashboard()

    stats = dashboard.get_scan_statistics()

    assert stats["total_scans"] == 0
    assert stats["active_scans"] == 0


def test_dashboard_update_scan_stats():
    """Test updating scan statistics."""
    dashboard = Dashboard()

    # Start scan
    dashboard.update_scan_stats("started")
    assert dashboard.scan_stats.total_scans == 1
    assert dashboard.scan_stats.active_scans == 1

    # Complete scan
    findings = [
        {"severity": "CRITICAL"},
        {"severity": "HIGH"},
    ]
    dashboard.update_scan_stats("completed", findings)

    assert dashboard.scan_stats.active_scans == 0
    assert dashboard.scan_stats.completed_scans == 1
    assert dashboard.scan_stats.critical_findings == 1


def test_dashboard_metrics_history():
    """Test metrics history."""
    dashboard = Dashboard()

    # Generate some metrics
    for _ in range(5):
        dashboard.get_system_metrics()

    history = dashboard.get_metrics_history(limit=3)
    assert len(history) == 3


def test_dashboard_summary():
    """Test dashboard summary."""
    dashboard = Dashboard()

    summary = dashboard.get_dashboard_summary()

    assert "system" in summary
    assert "scans" in summary
    assert "timestamp" in summary
