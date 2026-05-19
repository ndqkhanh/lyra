"""
Lyra Desktop - Desktop application backend.

This package provides:
- FastAPI server
- WebSocket support
- Real-time dashboard
"""

from lyra_desktop.api_server import APIServer, ScanRequest, ScanResult
from lyra_desktop.dashboard import Dashboard, ScanStatistics, SystemMetrics

__version__ = "0.1.0"

__all__ = [
    # API Server
    "APIServer",
    "ScanRequest",
    "ScanResult",
    # Dashboard
    "Dashboard",
    "SystemMetrics",
    "ScanStatistics",
]
