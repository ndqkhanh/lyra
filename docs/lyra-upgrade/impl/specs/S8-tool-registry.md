# S8: Tool Registry + Execution Sandbox

> Plan: §4.6 (06-tools.md) | Depends on: S1 (Provider), S2 (Hooks)

## Scope

Build the tool registration and execution system: tool definition, schema validation, sandboxed execution, and MCP-ready protocol.

## Key Design
1. **ToolDef**: name, description, JSON Schema parameters, handler, sandbox requirements
2. **ToolRegistry**: register, lookup, list by capability, validate inputs against schema
3. **ToolExecutor**: sandboxed subprocess execution, timeout, output capture
4. **ToolResult**: success/failure, output, error, execution_time_ms

## Sandbox Rules
- File tools: scoped to workspace directory only
- Bash tools: denylist for destructive commands (rm -rf, sudo, curl|sh)
- Network tools: allowed domains whitelist
- All tools: 30s timeout default, configurable per-tool
