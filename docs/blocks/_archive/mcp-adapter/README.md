# MCP Adapter -- Learning Path

> **Phase:** 3 (Integration) | **Dependencies:** Permission Bridge, Hooks | **Used by:** Tool Registry, External Tool Integration

## Progressive Reading

| Level | Focus | Document | What You'll Learn |
|-------|-------|----------|-------------------|
| 1 Basic | What is it? | [architecture.md](architecture.md) | MCP gateway, client bridge, stdio transport, security scanning, progressive disclosure |
| 2 Intermediate | How & Why? | [system-design.md](system-design.md) | Design decisions, data flow, component interactions |
| 3 Advanced | Build It | [implementation-guide.md](implementation-guide.md) | Code patterns, APIs, integration steps |
| 4 Expert | Deep Dive | [deep-dive.md](deep-dive.md) | JSON-RPC protocol details, transport management, security analysis |
| 5 Decision | Trade-offs | [architecture-tradeoffs.md](architecture-tradeoffs.md) | Pros/cons, alternatives, when to use vs not |

## In 30 Seconds

The MCP adapter provides bidirectional connectivity with external Model Context Protocol servers across two packages (`lyra-mcp` and `lyra-core/mcp/`). It includes an enterprise gateway with rate limiting and policies, a security scanner with taint analysis, client bridging from MCP tools into Lyra's tool registry, stdio transport management, progressive tool disclosure to minimize context bloat, and server discovery via transport pools.

## Quick Reference

- **Use case**: Connecting Lyra to external MCP-compatible servers (filesystem, database, custom tools) with security scanning and progressive disclosure.
- **Key concept**: The gateway manages server registrations and rate limiting; the bridge converts MCP tools into Lyra-compatible tool specs; progressive disclosure tiers tools by visibility to reduce context size.
- **Dependencies**: Permission Bridge (04), Hooks (05).
- **Used by**: Tool Registry, External Tool Integration.
- **Phase**: 3 (Integration).

## Related

- Concept doc: [Tools and Hooks overview](../../concepts/tools-and-hooks.md)
- System doc: [Index](../../lyra-upgrade/plans/index.md)
- Upgrade plan: [MCP evolution](../../lyra-upgrade/plans/08-mcp.md)

## Reading Path by Role

| Role | Read These |
|------|-----------|
| New Lyra user | architecture.md |
| Skill author | architecture.md + system-design.md |
| Lyra contributor | architecture.md + system-design.md + implementation-guide.md |
| Core developer | All 5 docs |
| Architect / reviewer | system-design.md + architecture-tradeoffs.md |
