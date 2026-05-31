---
id: incident-response
name: Incident Response
description: Structured incident response: detect, triage, mitigate, resolve, postmortem.
keywords:
  - incident
  - outage
  - SRE
  - postmortem
  - oncall
  - alert
---

1. Detect: confirm the incident is real. Check dashboards, logs, alerts. Determine scope.
2. Triage: severity (SEV1 = user-facing outage, SEV2 = degraded, SEV3 = internal). Notify stakeholders.
3. Mitigate: stop the bleeding first — rollback, failover, scale up, circuit-break. Don't debug in production.
4. Resolve: identify root cause, implement fix, verify recovery, monitor for 15+ minutes.
5. Postmortem: what happened (timeline), why (root cause), how we fixed it, how we prevent recurrence.
6. Action items: specific, assigned, time-bound improvements from the postmortem.