# Tools & Plugins System: Complete 118+ Tool Catalog

**Version:** 2.0.0
**Date:** 2026-05-30
**Status:** Implementation Design - Ready
**Based on:** Hermes-agent (73 tools), Claude Code (45 tools), MCP protocol, Phase 3 Research

---

## Executive Summary

The Tools & Plugins System implements all 118+ tools from Hermes-agent and Claude Code, unified under a consistent interface with MCP protocol support, tool composition (chaining + parallel execution), progressive disclosure, and plugin sandboxing.

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Tool Count | ~30 | 118+ | 4× expansion |
| Invocation Latency | ~100ms | <50ms | 2× faster |
| MCP Support | None | Full protocol | New capability |

---

## I. Complete Tool Catalog (118+ tools)

### File Operations (18)
`read, write, edit, glob, grep, tree, ls, cat, head, tail, find, cp, mv, rm, mkdir, touch, chmod, stat`

### Git Operations (16)
`git_status, git_diff, git_add, git_commit, git_push, git_pull, git_branch, git_checkout, git_merge, git_rebase, git_log, git_stash, git_reset, git_tag, git_remote, git_blame`

### Search (12)
`grep_search, find_files, semantic_search, code_search, web_search, web_fetch, arxiv_search, github_search, doc_search, symbol_search, regex_search, ripgrep`

### Analysis (20)
`lsp_diagnostics, lsp_hover, lsp_references, lsp_definition, lsp_document_symbols, lsp_workspace_symbols, type_check, lint, format, complexity_analyze, dependency_analyze, test_coverage, security_scan, performance_profile, dead_code_detect, api_usage_check, breaking_change_detect, code_quality_score, duplication_detect, todo_scan`

### Generation (15)
`code_generate, test_generate, doc_generate, commit_generate, pr_generate, release_notes, changelog, diagram_generate, config_generate, migration_generate, benchmark_generate, mock_generate, schema_generate, api_client_generate, scaffold`

### Execution (12)
`bash_exec, python_exec, node_exec, sql_exec, docker_exec, build_run, test_run, deploy_run, benchmark_run, script_run, command_palette, task_run`

### Communication (10)
`notify, alert, report, email_send, slack_send, webhook_call, api_call, graphql_query, grpc_call, message_queue`

### Knowledge (15)
`memory_store, memory_retrieve, context_load, context_save, note_create, note_search, wiki_read, wiki_write, learn_fact, recall_fact, knowledge_graph_query, embedding_search, semantic_index, document_parse, data_extract`

---

## II. Core Components

### 2.1 Standard Tool Interface

```python
class Tool(ABC):
    def __init__(self, definition: ToolDef):
        self.defn = definition

    @abstractmethod
    async def execute(self, params: dict, ctx: ToolContext) -> ToolResult: ...

    async def _execute_with_retry(self, params: dict, ctx: ToolContext) -> ToolResult:
        last_error = None
        for attempt in range(self.defn.retry_count + 1):
            try:
                return await asyncio.wait_for(
                    self.execute(params, ctx),
                    timeout=self.defn.timeout_ms / 1000
                )
            except asyncio.TimeoutError:
                last_error = ToolTimeoutError(self.defn.name)
            except Exception as e:
                last_error = e
                if attempt < self.defn.retry_count:
                    await asyncio.sleep(2 ** attempt)
        raise last_error
```

### 2.2 Tool Composer

```python
class ToolComposer:
    async def compose(self, pipeline: ToolPipeline, ctx: ToolContext) -> PipelineResult:
        results: dict[str, ToolResult] = {}
        levels = self._topological_sort(pipeline.dag)
        for level in levels:
            parallel_results = await asyncio.gather(*[
                self._execute_node(node, results, ctx) for node in level
            ])
            for node, result in zip(level, parallel_results):
                results[node.id] = result
                if result.error and node.critical:
                    return PipelineResult(success=False, partial_results=results)
        return PipelineResult(success=True, results=results)

    async def chain(self, tools: list[tuple[str, dict]], ctx: ToolContext) -> list[ToolResult]:
        results, pipe_context = [], {}
        for tool_name, params in tools:
            resolved = self._resolve_refs(params, pipe_context)
            result = await self._execute_tool(tool_name, resolved, ctx)
            results.append(result)
            pipe_context[tool_name] = result
            pipe_context['last'] = result
            if result.error:
                break
        return results
```

### 2.3 MCP Integration

```python
class MCPManager:
    def __init__(self):
        self.servers: dict[str, MCPServer] = {}
        self.discovery = MCPServerDiscovery()

    async def discover_servers(self) -> list[MCPServerInfo]:
        return await self.discovery.scan([
            DiscoveryMethod.CONFIG_FILE, DiscoveryMethod.ENV_VAR,
            DiscoveryMethod.LOCAL_REGISTRY, DiscoveryMethod.NETWORK_SCAN
        ])

    async def connect(self, server_id: str) -> MCPServer:
        info = await self.discovery.resolve(server_id)
        server = MCPServer(id=server_id, info=info,
            transport=await MCPTransport().connect(info.endpoint),
            capabilities=await self._fetch_capabilities(info))
        self.servers[server_id] = server
        return server
```

### 2.4 Plugin Sandbox

```python
class PluginManager:
    def __init__(self, plugins_dir: str):
        self.plugins_dir = Path(plugins_dir)
        self.loaded: dict[str, Plugin] = {}
        self.sandbox = PluginSandbox()

    async def load(self, plugin_id: str) -> Plugin:
        info = await self._find_plugin(plugin_id)
        for dep_id in info.dependencies:
            if dep_id not in self.loaded:
                await self.load(dep_id)
        self.sandbox.validate_permissions(info)
        plugin = await self.sandbox.load(
            info.path / info.entry_point,
            allowed_imports=info.allowed_imports,
            allowed_paths=info.allowed_paths,
            memory_limit_mb=info.get('memory_limit_mb', 256)
        )
        await plugin.initialize()
        self.loaded[plugin_id] = plugin
        return plugin
```

---

## III. Implementation Phases

| Phase | Weeks | Scope | Tests |
|-------|-------|-------|-------|
| 1: Core Tools | 1-4 | File ops (18), Git ops (16), standard interface | 60 |
| 2: Search & Analysis | 5-8 | Search (12), Analysis (20), Generation (15) | 70 |
| 3: MCP & Composition | 9-10 | MCP protocol, tool chaining, Execution/Comm/Knowledge (37) | 70 |
| 4: Plugins | 11-12 | Discovery, sandbox, permissions, progressive disclosure | 60 |

---

## IV. Testing Plan

| Test Type | Count | Coverage |
|-----------|-------|----------|
| Unit tests (all tools) | 160 | 90%+ |
| Tool composition tests | 20 | 90% |
| MCP integration tests | 20 | 90% |
| Plugin system tests | 20 | 90% |
| Integration tests | 25 | N/A |
| E2E tests | 15 | N/A |
| **Total** | **260** | **90%+** |

## V. Success Metrics

- [ ] 118+ tools implemented and tested
- [ ] <50ms tool invocation latency (p95)
- [ ] MCP protocol fully supported
- [ ] Tool composition (chain + parallel) working
- [ ] Plugin sandbox prevents unauthorized access
- [ ] 260+ tests, 90%+ coverage
