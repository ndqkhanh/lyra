# Reliability & Observability: Checkpointing, Circuit Breakers, and OTel Tracing
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/16-reliability.md) | [Code](../../src/lyra/reliability/)

## Abstract
Lyra's reliability module provides three layers of protection: (1) checkpointing for resumability across crashes, (2) circuit breakers that stop cascading failures (MAX_CONSECUTIVE failures threshold), and (3) OpenTelemetry-compatible tracing for observability. Combined with the verification module's error probe (semantic failure attribution in multi-agent systems), Lyra can diagnose which agent caused a failure and why.

## Method
`src/lyra/reliability/checkpoint.py`: save/restore agent state. `circuit_breaker.py`: failure count tracking with automatic trip. `retry.py`: tenacity-based retry with exponential backoff. All hooks instrumented for tracing via OTel spans.

## Conclusion
Implemented: checkpointing, circuit breakers, retry, OTel tracing. Future: automated root-cause analysis from traces.
