---
name: system-design
description: System architecture design patterns, trade-off analysis, and decision frameworks
origin: Plan 13
tags: [system-design, architecture, tradeoffs, c4-model]
triggers: [architecture, system design, design pattern, trade-off, scalability]
---

# System Design

## Architecture Decision Records (ADR)

- **Title**: Short statement of the decision
- **Status**: Proposed, Accepted, Deprecated, Superseded
- **Context**: What forces are at play? Why is this decision needed?
- **Decision**: What did we decide? Be specific — "Use PostgreSQL" not "RDBMS".
- **Consequences**: What trade-offs does this introduce? Both gains and costs.

## Trade-off Analysis Framework

1. **List options** (at least 2-3 viable candidates)
2. **Score each** on: complexity, scalability, operational cost, team familiarity
3. **Identify must-haves vs nice-to-haves** — a perfect solution to a non-problem is waste
4. **Document the rejected alternatives** and why they lost — prevents re-litigation

## C4 Model Levels

| Level | Diagram | Audience |
|-------|---------|----------|
| L1 Context | System boundary, users, external systems | Everyone |
| L2 Container | Services, databases, message queues | Tech leads |
| L3 Component | Internal modules of one container | Dev team |
| L4 Code | Class/interface details (optional) | Individual devs |

## Scalability Dimensions

- **Load**: Requests per second, concurrent connections
- **Data**: Storage volume, growth rate, retention policy
- **Traffic**: Peak-to-average ratio, geographic distribution
- **Cost**: Linear vs sub-linear scaling under each dimension

## CAP Theorem Guide

- **CP** (Consistency + Partition Tolerance): Banking, inventory, locks
- **AP** (Availability + Partition Tolerance): Feeds, logs, analytics
- **CA** (Consistency + Availability): Single-node systems only (never real-world)

## Microservices vs Monolith Decision Tree

Monolith first unless: team > 10 engineers, independent deploy cadence needed, or polyglot tech stack required. Extract bounded contexts gradually — never decompose before understanding the domain.
