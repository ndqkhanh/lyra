---
name: incident-response
description: Incident severity levels, runbook execution, root cause analysis, and postmortem practices
origin: Plan 13
tags: [incident, SRE, runbook, postmortem, root-cause]
triggers: [incident, outage, runbook, postmortem, root cause, on-call]
---

# Incident Response

## Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| SEV1 | Critical outage, all hands | Immediate | Production down, data loss |
| SEV2 | Major feature impaired | 30 min | Partial outage, degraded perf |
| SEV3 | Minor issue, workaround exists | 4 hr | Non-critical bug |
| SEV4 | Low priority, cosmetic | Next business day | UI typo, docs |
| SEV5 | Informational, no impact | Best effort | User inquiry |

## Runbook Template

```
## [Incident Title]
- **Detected**: <timestamp>
- **Severity**: SEV<1-5>
- **On-call**: <engineer>

### Checklist
1. [ ] Acknowledge alert
2. [ ] Declare severity in #incidents channel
3. [ ] Identify affected service/component
4. [ ] Apply mitigation (rollback, scale, feature flag)
5. [ ] Verify recovery via metrics
6. [ ] Create postmortem ticket
```

## Root Cause Analysis

**5 Whys**: Ask "why" iteratively until the systemic cause emerges.

```
Problem: DB connection pool exhausted
Why? -> Connection leaks from unclosed transactions
Why? -> No context manager on query path
Why? -> Missing SDK wrapper pattern
Why? -> No code review enforced for DB layer
```

**Fishbone (Ishikawa)** categories: People, Process, Technology, Data, Environment, External.

## Postmortem Structure

1. **Summary**: One-liner of what happened and impact
2. **Timeline**: UTC timestamps, key events, actions taken
3. **Root Cause**: Technical and systemic causes
4. **Resolution**: What fixed the issue
5. **Action Items**: Blameless, specific, owner-assigned

## Blameless Culture

- Assume good intent; systems fail, not people
- Focus on process improvements, not individual mistakes
- Action items address detection, prevention, and process gaps

## Communication Templates

**Initial Alert**: "We are investigating an issue affecting `<service>` since `<time>`. `<symptoms>`."

**Status Update**: "Mitigation in progress. `<what>` is being `<action>`. ETA `<time>`."

**Resolution**: "Incident resolved. Impact: `<metrics>`. Postmortem tracking in `<ticket>`."

## Timeline Reconstruction

Gather logs, metrics, deploy events, and alert timestamps.
Map the sequence on a shared timeline to identify the trigger, detection gap, and mitigation lag.
