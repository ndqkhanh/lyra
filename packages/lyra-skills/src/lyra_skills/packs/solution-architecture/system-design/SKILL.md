---
id: system-design
name: System Design
description: Design scalable systems: requirements → architecture → trade-offs → implementation plan.
keywords:
  - system design
  - architecture
  - scalability
  - trade-offs
  - design doc
---

1. Clarify requirements: functional (what must it do?), non-functional (latency, throughput, availability, consistency).
2. Estimate scale: requests/second, storage, bandwidth. Numbers drive architecture decisions.
3. Design the high-level architecture: services, databases, caches, queues, load balancers. Draw the diagram.
4. Deep-dive each component: data model, API design, scaling strategy, failure modes.
5. Identify trade-offs: consistency vs availability, latency vs throughput, simplicity vs flexibility. Make them explicit.
6. Plan for evolution: v1 (MVP), v2 (scale), v3 (features). What changes at each stage?
7. Document assumptions, risks, and alternatives considered. Why this design and not the obvious alternative?
