---
id: health-check
name: Health Check
description: Implement liveness, readiness, and dependency health checks for services.
keywords:
  - health check
  - health
  - liveness
  - readiness
  - probe
  - monitoring
  - uptime
---

1. Add /health/live (process is running) and /health/ready (can serve traffic) endpoints.
2. In readiness: check connectivity to databases, message queues, and critical APIs.
3. Keep health checks fast (<1s); cache dependency checks with a short TTL.
4. Configure orchestrator probes (K8s, ECS, Nomad) to use these endpoints.
5. Expose health check metrics to the monitoring system.
