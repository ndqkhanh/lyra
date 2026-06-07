# S7: Reliability Core (Retry, Circuit Breaker, Checkpoint)

> Plan: §4.16 | Depends on: S1, S2

## Scope
Retry with exponential backoff, circuit breaker pattern, checkpoint-based recovery.

## Key Design
1. RetryPolicy: max_retries, base_delay, max_delay, exponential backoff with jitter
2. CircuitBreaker: CLOSED→OPEN after N failures, HALF_OPEN after timeout, CLOSED after success
3. CheckpointManager: save/resume agent state at each step boundary
