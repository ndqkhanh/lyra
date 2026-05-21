"""
Lyra ECC Integration Package

This package provides ECC (Enhanced Claude Code) compatibility layer for Lyra.
It integrates ECC's 232 skills, 60 agents, hooks system, and rules engine.
"""

__version__ = "4.0.0"
__author__ = "Lyra Team"

from .compatibility import ECCCompatibilityLayer
from .importer import ECCImporter

__all__ = [
    "ECCCompatibilityLayer",
    "ECCImporter",
]
