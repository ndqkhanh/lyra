> ⚠️ **DEPRECATED** — This plan has been superseded by the fresh research in [docs/lyra-upgrade/plans/](../lyra-upgrade/plans/). See [docs/lyra-upgrade/MASTER-PLAN.md](../lyra-upgrade/MASTER-PLAN.md) for the current roadmap. This file is kept for historical reference.

# Plans and Design Documents

This directory contains planning documents, design specifications, and implementation roadmaps for Lyra.

## Overview

Planning documents capture design decisions, implementation strategies, and future roadmap items before they are implemented.

## Planning Documents by Category

### System Design Plans

| Document | Description |
|----------|-------------|
| *No current plans* | Future system design plans will be added here |

### Block Design Plans

| Block | Design Documents |
|-------|------------------|
| Agent Loop | [blocks/agent-loop/system-design.md](../blocks/agent-loop/system-design.md) |
| Hooks & TDD Gate | [blocks/hooks-tdd/system-design.md](../blocks/hooks-tdd/system-design.md) |
| MCP Adapter | [blocks/mcp-adapter/system-design.md](../blocks/mcp-adapter/system-design.md) |
| Memory (Three-Tier) | [blocks/memory/system-design.md](../blocks/memory/system-design.md) |
| Safety Monitor | [blocks/safety-monitor/system-design.md](../blocks/safety-monitor/system-design.md) |

### System-Level Plans

| System | Design Documents |
|--------|------------------|
| Fleet Supervisor | [systems/fleet-supervisor/system-design.md](../systems/fleet-supervisor/system-design.md) |
| Skills System | [systems/skills-system/system-design.md](../systems/skills-system/system-design.md) |

## Implementation Guides

Detailed implementation plans and guides:

### Block Implementation Guides

| Block | Implementation Guide |
|-------|---------------------|
| Agent Loop | [blocks/agent-loop/implementation-guide.md](../blocks/agent-loop/implementation-guide.md) |
| Hooks & TDD Gate | [blocks/hooks-tdd/implementation-guide.md](../blocks/hooks-tdd/implementation-guide.md) |
| MCP Adapter | [blocks/mcp-adapter/implementation-guide.md](../blocks/mcp-adapter/implementation-guide.md) |
| Memory (Three-Tier) | [blocks/memory/implementation-guide.md](../blocks/memory/implementation-guide.md) |
| Safety Monitor | [blocks/safety-monitor/implementation-guide.md](../blocks/safety-monitor/implementation-guide.md) |

### System Implementation Guides

| System | Implementation Guide |
|--------|---------------------|
| Fleet Supervisor | [systems/fleet-supervisor/implementation.md](../systems/fleet-supervisor/implementation.md) |
| Skills System | [systems/skills-system/implementation.md](../systems/skills-system/implementation.md) |

## Roadmap and Future Plans

### Planned Features

Future planning documents will be organized here as new features are designed.

### Research Integration

Plans for integrating research findings:

- See [research/](../research/) for papers and analysis
- See [research/repos/](../research/repos/) for external repository analysis

## Document Structure

Planning documents follow these conventions:

### Design Documents
1. **Problem Statement** — What problem does this solve?
2. **Requirements** — Functional and non-functional requirements
3. **Design Overview** — High-level approach
4. **Detailed Design** — Component interfaces, data flows, algorithms
5. **Trade-offs** — Alternative approaches and rationale
6. **Success Metrics** — How to measure success

### Implementation Guides
1. **Setup** — Prerequisites and environment setup
2. **Step-by-Step** — Detailed implementation steps
3. **Code Examples** — Sample implementations
4. **Integration** — How to integrate with existing components
5. **Testing** — Test strategy and validation
6. **Troubleshooting** — Common issues and solutions

## Related Documentation

- [Architecture](../architecture/) — Architectural documentation
- [Blocks](../blocks/) — Block-level documentation
- [Systems](../systems/) — System-level documentation
- [Research](../research/) — Research papers and analysis
- [Developer Guide](../DEVELOPER_GUIDE.md) — Developer workflows
