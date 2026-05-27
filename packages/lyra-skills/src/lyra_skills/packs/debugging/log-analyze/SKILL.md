---
id: log-analyze
name: Log Analyze
description: Parse and correlate logs across services to reconstruct a failure timeline.
keywords:
  - log
  - logs
  - logging
  - analyze logs
  - correlate
  - timeline
---

1. Collect logs from all relevant services for the time window of the incident.
2. Extract timestamps and request/trace IDs; sort into a unified timeline.
3. Identify the first anomalous event (error, timeout, unexpected state change).
4. Trace the causal chain forward from the anomaly.
5. Summarise: trigger → propagation → user impact.
