"""Lyra unified API.

Phase 4, Week 1: System Integration - Unified API

Provides a single entry point for all Lyra capabilities with:
- Consistent error handling
- Unified response format
- Capability discovery
- Health checks
"""
from lyra_core.api.core import LyraAPI
from lyra_core.api.errors import APIError
from lyra_core.api.response import APIResponse

__all__ = ["LyraAPI", "APIError", "APIResponse"]
