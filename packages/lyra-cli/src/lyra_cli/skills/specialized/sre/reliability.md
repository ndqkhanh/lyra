---
name: "sre-engineer"
description: Site Reliability Engineering expertise covering monitoring, incident response, capacity planning, SLOs/SLIs, and production operations. Use when setting up observability, responding to incidents, or improving system reliability.
tags: ["sre", "reliability", "monitoring", "incident-response", "observability"]
triggers: ["sre", "reliability", "monitoring", "incident", "observability", "slo", "sli"]
model: "sonnet"
tools: ["Read", "Write", "Edit", "Bash", "Grep"]
---

# SRE Engineer

Site Reliability Engineering for production systems.

## Core Competencies

### 1. Observability
- **Metrics**: Prometheus, Datadog, CloudWatch
- **Logs**: ELK Stack, Loki, Splunk
- **Traces**: Jaeger, Tempo, Zipkin
- **Dashboards**: Grafana, Kibana
- **Alerting**: PagerDuty, Opsgenie, Slack

### 2. Incident Management
- On-call rotation and escalation
- Incident response procedures
- Postmortem analysis (blameless)
- Root cause analysis (5 Whys, Fishbone)
- Incident communication

### 3. Service Level Objectives
- SLI (Service Level Indicator) definition
- SLO (Service Level Objective) targets
- Error budgets
- SLA (Service Level Agreement) compliance
- Burn rate alerts

### 4. Capacity Planning
- Traffic forecasting
- Resource utilization analysis
- Scaling strategies
- Cost optimization
- Performance testing

### 5. Automation
- Runbook automation
- Self-healing systems
- Chaos engineering
- Infrastructure as Code
- CI/CD pipeline reliability

## The Four Golden Signals

### 1. Latency
Time to serve a request
```
Metrics:
- p50, p95, p99 response time
- Request duration histogram

Alert:
- p99 latency > 1s for 5 minutes
```

### 2. Traffic
Demand on the system
```
Metrics:
- Requests per second
- Concurrent connections
- Bandwidth usage

Alert:
- Traffic spike > 2x baseline
```

### 3. Errors
Rate of failed requests
```
Metrics:
- Error rate (%)
- 4xx and 5xx responses
- Failed health checks

Alert:
- Error rate > 1% for 5 minutes
```

### 4. Saturation
How "full" the service is
```
Metrics:
- CPU utilization
- Memory usage
- Disk I/O
- Connection pool usage

Alert:
- CPU > 80% for 10 minutes
- Memory > 90%
```

## SLO Framework

### Define SLIs
```
Availability SLI:
  successful_requests / total_requests

Latency SLI:
  requests_under_300ms / total_requests

Throughput SLI:
  requests_processed / requests_received
```

### Set SLO Targets
```
Availability: 99.9% (43.2 minutes downtime/month)
Latency: 95% of requests < 300ms
Throughput: 99% of requests processed within 1 hour
```

### Calculate Error Budget
```
SLO: 99.9% availability
Error budget: 0.1% = 43.2 minutes/month

If error budget exhausted:
- Freeze feature releases
- Focus on reliability improvements
- Conduct incident reviews
```

### Burn Rate Alerts
```
Fast burn (1 hour):
  Error rate consuming 5% of monthly budget per hour
  → Page on-call immediately

Slow burn (24 hours):
  Error rate consuming 2% of monthly budget per day
  → Create ticket for investigation
```

## Incident Response

### Severity Levels
```
SEV-1 (Critical):
  - Complete service outage
  - Data loss or corruption
  - Security breach
  Response: Immediate, all hands on deck

SEV-2 (High):
  - Partial service degradation
  - Performance issues affecting users
  - Non-critical feature broken
  Response: Within 30 minutes

SEV-3 (Medium):
  - Minor issues, workaround available
  - Internal tools affected
  Response: Within 4 hours

SEV-4 (Low):
  - Cosmetic issues
  - Documentation errors
  Response: Next business day
```

### Incident Response Process
```
1. Detect: Alert fires or user report
2. Triage: Assess severity, assign incident commander
3. Investigate: Check logs, metrics, traces
4. Mitigate: Rollback, scale up, or hotfix
5. Resolve: Verify fix, close incident
6. Postmortem: Document timeline, root cause, action items
```

### Incident Roles
```
Incident Commander:
  - Coordinate response
  - Make decisions
  - Communicate status

Technical Lead:
  - Investigate root cause
  - Implement fixes
  - Verify resolution

Communications Lead:
  - Update status page
  - Notify stakeholders
  - Post incident updates
```

## Monitoring Setup

### Prometheus Metrics
```yaml
# Application metrics
http_requests_total{method="GET", status="200"}
http_request_duration_seconds{quantile="0.99"}
database_connections_active
cache_hit_rate

# System metrics
node_cpu_seconds_total
node_memory_MemAvailable_bytes
node_disk_io_time_seconds_total
node_network_receive_bytes_total
```

### Grafana Dashboard
```
Row 1: Overview
  - Request rate (RPS)
  - Error rate (%)
  - p99 latency (ms)
  - Availability (%)

Row 2: Resources
  - CPU usage (%)
  - Memory usage (%)
  - Disk I/O (MB/s)
  - Network I/O (MB/s)

Row 3: Application
  - Active connections
  - Database query time
  - Cache hit rate
  - Queue depth
```

### Alert Rules
```yaml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}%"

      - alert: HighLatency
        expr: histogram_quantile(0.99, http_request_duration_seconds) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "p99 latency is {{ $value }}s"

      - alert: HighCPU
        expr: rate(node_cpu_seconds_total{mode="idle"}[5m]) < 0.2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value }}%"
```

## Capacity Planning

### Traffic Forecasting
```
Historical data:
  - Daily/weekly/monthly patterns
  - Seasonal trends
  - Growth rate

Forecasting methods:
  - Linear regression
  - Time series analysis (ARIMA)
  - Machine learning (Prophet)

Example:
  Current: 10K RPS
  Growth: 20% per quarter
  Q1: 12K RPS
  Q2: 14.4K RPS
  Q3: 17.3K RPS
  Q4: 20.7K RPS
```

### Resource Planning
```
Current capacity:
  - 10 servers @ 1K RPS each = 10K RPS total
  - CPU: 60% average, 80% peak
  - Memory: 70% average, 85% peak

Target capacity (Q4):
  - 20.7K RPS needed
  - Add 11 servers (21 total)
  - Maintain 20% headroom for spikes
```

### Cost Optimization
```
Strategies:
  - Right-size instances (avoid over-provisioning)
  - Use spot instances for batch jobs
  - Auto-scaling based on demand
  - Reserved instances for baseline
  - Compress and archive old logs
  - Optimize database queries
```

## Chaos Engineering

### Principles
1. Define steady state (normal behavior)
2. Hypothesize steady state continues
3. Introduce real-world failures
4. Disprove hypothesis by finding differences

### Experiments
```
Network failures:
  - Introduce latency (100ms, 500ms, 1s)
  - Drop packets (1%, 5%, 10%)
  - Partition network (split brain)

Resource exhaustion:
  - CPU spike (stress test)
  - Memory leak simulation
  - Disk full scenario

Service failures:
  - Kill random instances
  - Shutdown dependencies
  - Corrupt data
```

### Tools
- **Chaos Monkey**: Randomly terminates instances
- **Litmus**: Kubernetes chaos engineering
- **Gremlin**: Chaos engineering platform
- **Pumba**: Docker chaos testing

## Runbook Automation

### Manual Runbook
```markdown
## Restart API Service

1. Check current status:
   kubectl get pods -l app=api

2. Identify unhealthy pods:
   kubectl describe pod <pod-name>

3. Restart deployment:
   kubectl rollout restart deployment/api

4. Verify:
   kubectl rollout status deployment/api
   
5. Check logs:
   kubectl logs -f deployment/api
```

### Automated Runbook
```bash
#!/bin/bash
# auto-restart-api.sh

set -e

echo "Checking API health..."
if ! curl -f http://api/health; then
  echo "API unhealthy, restarting..."
  kubectl rollout restart deployment/api
  kubectl rollout status deployment/api --timeout=5m
  echo "API restarted successfully"
else
  echo "API is healthy"
fi
```

## Postmortem Template

```markdown
# Incident Postmortem: [Title]

**Date**: 2024-01-15
**Duration**: 2 hours 15 minutes
**Severity**: SEV-1
**Impact**: 100% of users unable to access service

## Timeline (UTC)
- 14:00: Alert fired for high error rate
- 14:05: On-call engineer acknowledged
- 14:10: Incident commander assigned
- 14:15: Root cause identified (database connection pool exhausted)
- 14:30: Mitigation applied (increased pool size)
- 14:45: Service partially restored
- 16:15: Full service restored

## Root Cause
Database connection pool size (10) was insufficient for traffic spike (3x normal). Connections were held open by long-running queries, causing new requests to timeout.

## Impact
- 100% of API requests failed for 45 minutes
- 50% of requests failed for additional 90 minutes
- Estimated 10,000 users affected
- $50,000 revenue impact

## What Went Well
- Alert fired within 1 minute of issue
- Incident response team assembled quickly
- Mitigation applied within 30 minutes

## What Went Wrong
- No monitoring for connection pool usage
- No auto-scaling for database connections
- Long-running queries not identified earlier

## Action Items
1. [P0] Add connection pool monitoring (Owner: Alice, Due: 2024-01-20)
2. [P0] Implement connection pool auto-scaling (Owner: Bob, Due: 2024-01-25)
3. [P1] Identify and optimize slow queries (Owner: Charlie, Due: 2024-02-01)
4. [P2] Add load testing for 3x traffic (Owner: Dave, Due: 2024-02-15)
```

## Quick Commands

```bash
# Prometheus queries
rate(http_requests_total[5m])
histogram_quantile(0.99, http_request_duration_seconds_bucket)
up{job="api"} == 0

# Kubernetes debugging
kubectl get pods
kubectl describe pod <pod-name>
kubectl logs -f <pod-name>
kubectl exec -it <pod-name> -- sh

# Performance profiling
top
htop
iostat
netstat -an

# Log analysis
tail -f /var/log/app.log
grep ERROR /var/log/app.log | wc -l
awk '{print $1}' access.log | sort | uniq -c | sort -rn
```

## When to Escalate

- Multi-region outage → Activate disaster recovery plan
- Security incident → Engage security team immediately
- Data corruption → Engage database team, consider restore from backup
- Vendor outage → Contact vendor support, implement workaround
- Capacity exhausted → Emergency scaling, traffic shedding
