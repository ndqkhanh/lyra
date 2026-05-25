"""OTEL Tracer exception hierarchy."""

from __future__ import annotations


class OtelTracerError(Exception):
    """Base exception for all otel-tracer-related errors."""


class SpanError(OtelTracerError):
    """Raised when span operations fail."""


class TokenTrackerError(OtelTracerError):
    """Raised when token tracking operations fail."""


class HallucinationDetectionError(OtelTracerError):
    """Raised when hallucination detection operations fail."""


class CostAttributionError(OtelTracerError):
    """Raised when cost attribution operations fail."""


class LatencyMonitorError(OtelTracerError):
    """Raised when latency monitoring operations fail."""


class DriftIntegrationError(OtelTracerError):
    """Raised when drift integration operations fail."""


class ExportError(OtelTracerError):
    """Raised when metric export operations fail."""
