---
id: reliability-patterns
name: Reliability Patterns
description: Apply reliability patterns: circuit breakers, retries, timeouts, bulkheads, health checks.
keywords:
  - reliability
  - circuit breaker
  - retry
  - timeout
  - resilience
  - fault tolerance
---

1. Identify single points of failure in the system architecture.
2. For each external dependency: add timeouts (always), retries with backoff (where idempotent), circuit breakers (for 5xx errors).
3. Implement health checks: liveness (is the process alive?), readiness (can it serve traffic?).
4. Add graceful degradation: what features can be disabled when a dependency is down?
5. Implement observability: metrics (RED: Rate, Errors, Duration), structured logging, distributed tracing.
6. Test failure modes: chaos engineering — deliberately break dependencies and verify the system handles it gracefully.
7. Document reliability SLOs: what uptime/latency do we promise, how is it measured, what happens when we miss?