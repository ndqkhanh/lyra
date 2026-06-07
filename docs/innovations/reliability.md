# Reliability & Observability: Checkpointing, Circuit Breakers, and OTel Tracing
> **Status:** ✅ Implemented | [Plan](../lyra-upgrade/plans/16-reliability.md) | [Code](../../src/lyra/reliability/)

## Abstract
Lyra's reliability module provides three layers of protection: (1) checkpointing for resumability across crashes, (2) circuit breakers that stop cascading failures (MAX_CONSECUTIVE failures threshold), and (3) OpenTelemetry-compatible tracing for observability. Combined with the verification module's error probe (semantic failure attribution in multi-agent systems), Lyra can diagnose which agent caused a failure and why.

## Method
`src/lyra/reliability/checkpoint.py`: save/restore agent state. `circuit_breaker.py`: failure count tracking with automatic trip. `retry.py`: tenacity-based retry with exponential backoff. All hooks instrumented for tracing via OTel spans.

## Working Flow

Lyra's reliability layer sits between every tool call and the agent, watching for trouble. Think of it as three safety nets stacked on top of each other: the retry mechanism catches transient hiccups, the circuit breaker catches systemic failures, and checkpointing saves your progress so a crash doesn't mean starting over. Every step is logged to OpenTelemetry traces so you can replay what happened.

**Example:** An external API keeps failing.

1. Lyra calls `web_search("latest Python 3.13 features")`. The HTTP request times out.
2. The retry module (`src/lyra/reliability/retry.py`) waits 1 second, retries. Fails again. Waits 2 seconds, retries. Fails a third time.
3. The circuit breaker (`src/lyra/reliability/circuit_breaker.py`) sees MAX_CONSECUTIVE failures tripped. It snaps to OPEN state — now ALL outbound web calls are instantly rejected without trying, giving the API time to recover.
4. A checkpoint (`src/lyra/reliability/checkpoint.py`) was saved before the tool call. Lyra rolls back to that checkpoint and tells you: "web_search is temporarily unavailable, here is what I had before the failures."
5. You review the OTel trace and see exactly which three requests failed, with timing and error details.

## Conclusion
Implemented: checkpointing, circuit breakers, retry, OTel tracing. Future: automated root-cause analysis from traces.
