# P1: Multi-Agent Orchestrator-Worker (Breakthrough #2)

> Plan: §4.13, §4.15 | Depends on: S5, S6, S9 | Breakthrough #2

## Scope
LeadResearcher (Opus) spawns parallel subagents (Sonnet) with isolated context windows, compressed artifact output, effort-scaling heuristics. +90.2% performance gain.

## Key Design
1. **Orchestrator**: decompose query → spawn subagents → collect artifacts → synthesize
2. **Subagent pool**: configurable max concurrency, isolated context per agent
3. **Artifact protocol**: file-system-based output (JSON/markdown), compressed before return
4. **Effort scaling**: 1 agent (simple), 2-4 (comparison), 10+ (complex research)
