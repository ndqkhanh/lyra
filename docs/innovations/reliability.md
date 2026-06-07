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

## Use Cases

**Scenario 1: Production deployment with automatic rollback.** An engineering team uses Lyra to automate deployments to staging and production. During a deployment, the health check endpoint returns 503 errors after the new container starts. The circuit breaker detects MAX_CONSECUTIVE failures, snaps open, and triggers a rollback to the previous known-good deployment. The team gets an alert with an OTel trace showing exactly which step failed and how long each retry took. No on-call engineer had to SSH into a box.

**Scenario 2: Flaky API dependency handling.** Lyra is running a daily report that pulls data from a third-party analytics API. That API occasionally returns 429 rate-limit errors and 502 gateway timeouts. Without the reliability layer, a single timeout would crash the whole report. With retry (tenacity with exponential backoff), Lyra waits 1s, 2s, then 4s before giving up. If the API stays broken for 10 minutes, the circuit breaker trips and Lyra runs the report with cached data instead, annotating the output: "Analytics API was unavailable — used cached data from 1 hour ago."

**Scenario 3: Debugging multi-agent failures with tracing.** A senior engineer notices that a complex multi-agent pipeline — context builder, researcher, writer, verifier — sometimes produces reports with gaps. They open the OTel trace for a failed run and see that the context builder agent's web_search call timed out, the researcher agent received incomplete context, and the writer agent silently produced a thin report. Instead of guessing, the engineer sees the exact failure chain in one view: "Context builder failed → researcher never got proper sources → writer output was weak." They fix the context builder's timeout settings and verify the next run passes.

## Conclusion
Implemented: checkpointing, circuit breakers, retry, OTel tracing. Future: automated root-cause analysis from traces.
