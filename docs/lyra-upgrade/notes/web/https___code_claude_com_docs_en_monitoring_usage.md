# Monitoring (Claude Code Official Docs, Anthropic)

Source: https://code.claude.com/docs/en/monitoring-usage
Fetched: 2026-06-07

## Key Technical Claims

1. Claude Code exports full OpenTelemetry telemetry across three signal types: metrics (time series), events/logs, and traces (beta). This makes all agent activity observable in any standards-compliant backend (Prometheus, Datadog, Honeycomb, Jaeger, etc.).

2. The telemetry system is **opt-in and explicitly configured** -- no data flows to Anthropic by default from the OTel pipeline; it goes only to the operator's configured endpoint. Separate operational telemetry is a different system.

3. Admin can enforce telemetry settings across an organization via managed settings files distributed through MDM, and those settings cannot be overridden by individual users.

4. **Full audit trail**: every tool call, permission decision, MCP server connection, plugin install, and auth event carries user identity attributes (`user.email`, `user.account_uuid`, `organization.id`, `session.id`). This maps every agent action back to a specific developer.

5. Distributed tracing with W3C `traceparent` propagation enables end-to-end trace linking: Claude Code -> Anthropic API -> any subprocess that reads `TRACEPARENT`. In Agent SDK sessions, an embedding process can also pass its own `TRACEPARENT` in so Claude Code's spans appear as children of the caller's distributed trace.

6. Subagent and tool spans nest hierarchically under the parent interaction span, letting operators see the full tree: user prompt -> LLM request(s) -> tool calls -> subagent API calls.

7. **Privacy safeguards baked in**: user prompt content, tool input details, tool output content, and raw API bodies are all disabled by default and require explicit opt-in via separate env vars.

## Architecture/Mechanism Details

**Three signal paths:**
- **Metrics** (OTEL_METRICS_EXPORTER): Counter-based time series for cost, tokens, sessions, commits, PRs, LOC, active time. 7 metrics total, each with standard + context-specific attributes.
- **Events/Logs** (OTEL_LOGS_EXPORTER): Structured events with rich attributes for user prompts, tool results, API requests/errors/refusals, permission decisions, auth, MCP connections, plugin installs, hook executions, skill activations, compaction, and survey feedback. ~20 distinct event types.
- **Traces** (OTEL_TRACES_EXPORTER, beta): Distributed spans linking user prompts to API requests and tool executions. W3C trace context propagation to subprocesses and the Anthropic API.

**Span hierarchy:**
```
claude_code.interaction
  +-- claude_code.llm_request
  +-- claude_code.hook
  +-- claude_code.tool
       +-- claude_code.tool.blocked_on_user
       +-- claude_code.tool.execution
       +-- (Agent tool subagent spans)
```

**Configuration patterns:**
- Environment variable driven (CLAUDE_CODE_ENABLE_TELEMETRY, OTEL_* vars)
- Managed settings JSON can enforce across fleet via MDM
- Dynamic headers script for enterprise token refresh (29 min default debounce)
- mTLS authentication for both gRPC and HTTP protocols
- Metrics cardinality control: optional inclusion of session ID, user UUID, entrypoint, resource attributes
- Multi-team support via `OTEL_RESOURCE_ATTRIBUTES` (custom labels on every metric/event)

**Privacy gates (all default-off):**
- `OTEL_LOG_USER_PROMPTS` - raw prompt text
- `OTEL_LOG_TOOL_DETAILS` - bash commands, MCP names, skill names, tool params
- `OTEL_LOG_TOOL_CONTENT` - tool input/output bodies (60 KB truncation)
- `OTEL_LOG_RAW_API_BODIES` - full Messages API request/response JSON (inline or file mode)

**Backend recommendations:**
- Metrics: Prometheus / ClickHouse / Honeycomb / Datadog
- Events: Elasticsearch / Loki / ClickHouse
- Traces: Jaeger / Zipkin / Grafana Tempo

## Numbers & Benchmarks

- **Default metric export interval**: 60,000 ms (60 seconds)
- **Default logs export interval**: 5,000 ms (5 seconds)
- **Default traces export interval**: 5,000 ms (5 seconds)
- **Dynamic headers debounce**: 1,740,000 ms (29 minutes)
- **Tool content truncation**: 60 KB per attribute
- **Tool input truncation**: 512 chars per value, ~4 KB total payload bound
- **API body truncation** (inline): 60 KB
- **API retry default**: 10 (`CLAUDE_CODE_MAX_RETRIES`)
- **7 core metrics**: session.count, lines_of_code.count, pull_request.count, commit.count, cost.usage, token.usage, code_edit_tool.decision, active_time.total
- **~20 event types**: user_prompt, tool_result, api_request, api_error, api_refusal, api_request_body, api_response_body, tool_decision, permission_mode_changed, auth, mcp_server_connection, internal_error, plugin_installed, plugin_loaded, skill_activated, at_mention, api_retries_exhausted, hook_registered, hook_execution_start, hook_execution_complete, hook_plugin_metrics, compaction, feedback_survey

## Transfer to Lyra

### One Idea: OpenTelemetry Span Hierarchy for Multi-Agent Systems

The single most transferable idea is Claude Code's **hierarchical span tree with W3C trace context propagation** across the full agent execution stack. Claude Code creates a root `claude_code.interaction` span per user prompt, then nests `llm_request`, `tool`, and subagent spans beneath it. Subagent API calls and tool executions appear as children of the parent tool span, producing a complete request waterfall.

For Lyra, this means instrumenting every component in the pipeline with OpenTelemetry:

```
lyra.interaction
  +-- lyra.router (which sub-agent was selected)
  |    +-- lyra.llm_request (router LLM call)
  +-- lyra.planner
  |    +-- lyra.llm_request (planner LLM call)
  +-- lyra.executor
  |    +-- lyra.tool
  |         +-- lyra.tool.execution
  |         +-- lyra.llm_request (executor RAG call)
  +-- lyra.memory.read
  +-- lyra.memory.write
  +-- lyra.hook
```

Each span carries attributes like `agent_type`, `tool_name`, `model`, `token_usage`, `duration_ms`, and `success`. W3C `traceparent` propagation lets Lyra's own API integrate with the broader observability stack.

The existing Lyra workstream **§4 Observability & Monitoring** is the natural route:
- **§4.1** (or a new subsection §4.4) should specify that every subsystem exports OTel metrics and spans, not just logs
- **§4.2 Cost Attribution** can borrow directly from Claude Code's model: attribute cost by `agent.name`, `skill.name`, `plugin.name` dimensions
- **§4.3 Audit Trail** maps exactly to Lyra's need for per-session audit logs showing which agent did what, to which file, at whose request
