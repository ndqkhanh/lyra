---
title: Architecture
description: A guided tour of how the Lyra kernel is laid out, the eleven design commitments it enforces, and the trade-offs accepted to make those commitments real.
---

# Architecture <span class="lyra-badge advanced">advanced</span>

This is the deep-dive layer. Concepts pages explained the seven main
ideas; this layer explains **how they fit together** as a system, what
trade-offs were accepted, and what the alternatives were.

## What's in this layer

| Page | What you'll learn |
|---|---|
| [System topology](topology.md) | Daemon, processes, on-disk layout, how a session physically runs |
| [Eleven commitments](commitments.md) | The architectural choices Lyra is willing to be wrong about — and the failures each prevents |
| [Harness plugins](harness-plugins.md) | `single-agent` / `three-agent` / `dag-teams` strategy pattern |
| [Trade-offs](../architecture-tradeoff.md) | The alternatives we considered and rejected, with reasons |
| [Full architecture spec](../architecture.md) | The original ~320-line architecture doc — exhaustive, with target metrics |
| [System design](../system-design.md) | The operational spec — Pydantic models, file layouts, daemon API |

## The component stack at a glance

```mermaid
graph TB
    User([User · Typer CLI · Python API · web viewer])
    GW[Gateway<br/>session lifecycle · event bus · plugin chooser]
    HP[Harness Plugins<br/>single-agent · three-agent · dag-teams]
    AL[Agent Loop]
    SUB[Subagent Orchestrator]
    DAG[DAG Scheduler]
    MR[Model Router<br/>fast / smart slot]
    Tools[Tool Layer<br/>read · write · bash · MCP · plugins]
    PB[Permission Bridge<br/>+ hooks + risk + injection guard]
    CE[Context Engine<br/>5-layer + cache breakpoints]
    MS[Memory Store<br/>3-tier · SQLite FTS5 + Chroma]
    SE[Skill Engine<br/>loader · router · extractor · curator]
    Ver[Verifier<br/>2-phase · cross-channel evidence]
    Safety[Safety Monitor<br/>cheap model · every N steps]
    Obs[Observability<br/>OTel + JSONL + HIR]

    User --> GW
    GW --> HP
    HP --> AL
    HP --> SUB
    HP --> DAG
    AL --> MR
    SUB --> MR
    AL --> Tools
    Tools --> PB
    PB --> CE
    CE --> MS
    AL --> SE
    AL --> Ver
    AL --> Safety
    AL --> Obs

    classDef ring fill:#1e1b4b,stroke:#7c3aed,color:#f1f5f9
    class GW,HP,AL,SUB,DAG,MR,Tools,PB,CE,MS,SE,Ver,Safety,Obs ring
```

Read top-down. Every box on this diagram has its own page or block
spec — the [reference index](../reference/blocks-index.md) maps them
all.

## Reading order

1. Start with [System topology](topology.md) to see *where* code lives
   and *how* a session runs as a process.
2. Then [Eleven commitments](commitments.md) — the most opinionated
   page on this site.
3. Then [Harness plugins](harness-plugins.md) for the strategy pattern
   that picks the topology per task.
4. Skim [Trade-offs](../architecture-tradeoff.md) when you want to
   know "why not X?"
5. Use the [Full spec](../architecture.md) and [System
   design](../system-design.md) as references — they're long, but
   exhaustive.

[System topology →](topology.md){ .md-button .md-button--primary }
