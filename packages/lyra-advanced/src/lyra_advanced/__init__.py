"""
Lyra Advanced - Advanced capabilities.

This package provides:
- Exploit development automation
- Malware analysis
"""

from lyra_advanced.exploit_dev import (
    Exploit,
    ExploitDevelopment,
    ExploitReliability,
    ExploitType,
    Vulnerability,
)
from lyra_advanced.malware_analysis import (
    AnalysisResult,
    AnalysisType,
    MalwareAnalysis,
    MalwareSample,
    MalwareType,
)

__version__ = "0.1.0"

__all__ = [
    # Exploit Development
    "ExploitDevelopment",
    "Exploit",
    "Vulnerability",
    "ExploitType",
    "ExploitReliability",
    # Malware Analysis
    "MalwareAnalysis",
    "MalwareSample",
    "AnalysisResult",
    "MalwareType",
    "AnalysisType",
]
