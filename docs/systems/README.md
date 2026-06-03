# Lyra Systems

Lyra systems are high-level architectures built from composing multiple blocks. Each system follows a consistent five-file documentation structure.

## System Catalog

| # | System | Description | Documentation |
|---|--------|-------------|---------------|
| 01 | **Fleet Supervisor** | Multi-agent fleet coordination and lifecycle management | [📁 fleet-supervisor/](fleet-supervisor/) |
| 02 | **Skills System** | Dynamic skill loading, extraction, and execution | [📁 skills-system/](skills-system/) |

## Documentation Structure

All systems contain five detailed documents:

| File | Purpose |
|------|---------|
| **architecture.md** | System overview, components, and relationships |
| **system-design.md** | Design decisions, principles, and rationale |
| **implementation.md** | Implementation details, code patterns, and integration |
| **evaluation.md** | Performance analysis, benchmarks, and validation |
| **tradeoffs.md** | Trade-offs, alternatives, and design choices |

## System Details

### [Fleet Supervisor](fleet-supervisor/)

Multi-agent fleet coordination system managing agent lifecycle, resource allocation, and inter-agent communication.

**Composed from blocks:**
- Agent Loop (orchestration)
- DAG Teams (coordination)
- Context Engine (resource management)
- Safety Monitor (guardrails)

**Documentation:**
- [architecture.md](fleet-supervisor/architecture.md) — Component overview and interfaces
- [system-design.md](fleet-supervisor/system-design.md) — Design principles and patterns
- [implementation.md](fleet-supervisor/implementation.md) — Implementation guide and code
- [evaluation.md](fleet-supervisor/evaluation.md) — Performance and validation
- [tradeoffs.md](fleet-supervisor/tradeoffs.md) — Design decisions and alternatives

### [Skills System](skills-system/)

Dynamic skill loading, pattern extraction, and execution system enabling agents to learn and apply new capabilities.

**Composed from blocks:**
- Skill Engine & Extractor (core)
- MCP Adapter (external integration)
- Memory (Three-Tier) (skill storage)
- Hooks & TDD Gate (skill validation)

**Documentation:**
- [architecture.md](skills-system/architecture.md) — Component overview and interfaces
- [system-design.md](skills-system/system-design.md) — Design principles and patterns
- [implementation.md](skills-system/implementation.md) — Implementation guide and code
- [evaluation.md](skills-system/evaluation.md) — Performance and validation
- [tradeoffs.md](skills-system/tradeoffs.md) — Design decisions and alternatives

## Block Composition Patterns

Systems demonstrate how blocks compose into larger architectures:

### Runtime Layer
- **Agent Loop** + **Context Engine** + **Memory** → Agent execution runtime

### Safety Layer
- **Hooks & TDD Gate** + **Safety Monitor** + **Permission Bridge** → Safety enforcement

### Coordination Layer
- **DAG Teams** + **Fleet Supervisor** + **Subagent Worktree** → Multi-agent orchestration

### Integration Layer
- **MCP Adapter** + **Skill Engine** + **Verifier Cross-Channel** → External tool integration

### Observability Layer
- **Observability HIR** + **Memory** + **Context Engine** → Tracing and debugging

## Related Documentation

- [Blocks](../blocks/) — Foundational building blocks
- [Architecture Overview](../02-Architecture-and-Core-Concepts.md)
- [Implementation Guide](../03-API-Reference-and-Developer-Guide.md)
- [Research](../research/) — Research papers and analysis
