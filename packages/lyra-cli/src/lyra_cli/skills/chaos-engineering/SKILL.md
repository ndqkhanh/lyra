---
name: chaos-engineering
description: Experiment design, fault injection, blast radius control, and reliability testing practices
origin: Plan 13
tags: [chaos, resilience, fault-injection, reliability]
triggers: [chaos, resilience, fault, failure, reliability, blast radius]
---

# Chaos Engineering

## Experiment Design Methodology

1. **Steady State** — Define normal behavior via metrics (latency P99 < 200ms, error rate < 0.1%)
2. **Hypothesis** — "If `<fault>` is injected, the system will maintain `<steady-state>`"
3. **Blast Radius** — Start with one host, one region, or one user segment
4. **Abort Conditions** — Hard thresholds that auto-stop the experiment (e.g., error rate > 5%)

## Fault Injection Types

| Type | Example | Tool |
|------|---------|------|
| Latency | Network delay (+100ms) | Toxiproxy, tc |
| Error | HTTP 503 from dependency | Chaos Mesh, Litmus |
| Resource Exhaustion | CPU/memory pressure | stress-ng, chaosblade |
| Dependency Failure | Kill a microservice process | Gremlin, custom scripts |
| Network Partition | Block traffic between pods | iptables, service mesh |

## Blast Radius Control

- Start with **lowest isolation** (single pod, canary user, read-only endpoint)
- Use feature flags or traffic shadowing for safe experiments
- Set automated rollback triggers in the experiment definition
- Run during low-traffic windows for new scenarios

## Steady-State Verification Metrics

- Request latency (P50, P95, P99)
- Error rate (4xx/5xx per minute)
- Throughput (requests/sec)
- Resource utilization (CPU, memory, disk, network)

## GameDay Planning Template

```
## GameDay: <scenario>
- **Duration**: <start> - <end>
- **Scope**: <services/regions affected>
- **Team**: <participants + observers>

### Schedule
1. Pre-brief: scenario walkthrough, roles assignment
2. Experiment execution
3. Post-mortem: what went well, what didn't
4. Action item tracking
```

## Rollback and Abort Procedures

- **Manual abort**: Kill switch in dashboard or CLI
- **Auto-abort**: Metric thresholds that trigger immediate cleanup
- **Cleanup script**: Restore all altered configs, restart affected services
- Validate cleanup success by re-running steady-state checks

## Chaos Maturity Model

| Level | State | Practice |
|-------|-------|----------|
| L0 | Ad-hoc | Manual experiments, no documentation |
| L1 | Repeatable | Scripted experiments, basic runbooks |
| L2 | Automated | Scheduled experiments, CI integration |
| L3 | Proactive | Continuous verification, auto-remediation |
| L4 | Resilient-by-design | Chaos in dev/CI gates, proactive hardening |
