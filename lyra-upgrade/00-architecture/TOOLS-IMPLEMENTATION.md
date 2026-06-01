# Tools System Implementation Roadmap

**Date:** 2026-05-29  
**Status:** Planning  
**Duration:** 12 weeks (3 phases)  
**Based on:** US-007 (Tools Analysis), TOOLS-SYSTEM.md (Architecture)

---

## Executive Summary

This roadmap outlines a 12-week implementation plan for Lyra's comprehensive tools system, organized into three phases: Foundation, Extensibility, and Advanced Features. Each phase delivers working functionality while building toward the complete vision.

**Key Milestones:**
- **Week 4:** Core tools system with permissions and basic hooks
- **Week 8:** Full MCP integration and plugin support
- **Week 12:** Advanced features including channels and agent teams

---

## Phase 1: Foundation (Weeks 1-4)

### Week 1: Tool Registry Core

**Objectives:**
- Implement tool registration and discovery
- Create tool schema and validation
- Build basic tool execution engine

**Deliverables:**

1. **Tool Schema** (`lyra_core/tools/schema.py`)
   ```python
   - ToolDefinition dataclass
   - ToolParameter dataclass
   - ToolCategory enum
   - Validation functions
   ```

2. **Tool Registry** (`lyra_core/tools/registry.py`)
   ```python
   - ToolRegistry class
   - register() method
   - get() method
   - list_by_category() method
   - search() method
   ```

3. **Basic Tools** (`lyra_core/tools/builtin/`)
   ```python
   - Read tool (file reading)
   - Glob tool (file finding)
   - Grep tool (content search)
   ```

4. **Tests** (`tests/tools/`)
   ```python
   - test_registry.py
   - test_schema.py
   - test_builtin_tools.py
   ```

**Success Criteria:**
- [ ] Tool registration works
- [ ] Tool discovery by name/category
- [ ] Basic tools execute successfully
- [ ] 90%+ test coverage

---

### Week 2: Permission System Core

**Objectives:**
- Implement permission rule engine
- Add pattern matching for file paths and commands
- Create permission modes

**Deliverables:**

1. **Permission Schema** (`lyra_core/permissions/schema.py`)
   ```python
   - PermissionRule dataclass
   - PermissionMode enum
   - PermissionDecision enum
   - Pattern matching utilities
   ```

2. **Permission System** (`lyra_core/permissions/system.py`)
   ```python
   - PermissionSystem class
   - add_rule() method
   - check_permission() method
   - Pattern matching (gitignore-style)
   - Wildcard matching for commands
   - Decision caching
   ```

3. **Permission Modes** (`lyra_core/permissions/modes.py`)
   ```python
   - Default mode
   - AcceptEdits mode
   - Plan mode (read-only)
   - DontAsk mode
   ```

4. **Tests** (`tests/permissions/`)
   ```python
   - test_system.py
   - test_patterns.py
   - test_modes.py
   - test_caching.py
   ```

**Success Criteria:**
- [ ] Rule matching works correctly
- [ ] Pattern matching handles all cases
- [ ] Mode switching works
- [ ] Decision caching improves performance
- [ ] 90%+ test coverage

---

### Week 3: Hook System Foundation

**Objectives:**
- Implement hook registration and execution
- Add command and HTTP hook types
- Create lifecycle event system

**Deliverables:**

1. **Hook Schema** (`lyra_core/hooks/schema.py`)
   ```python
   - HookDefinition dataclass
   - HookType enum
   - HookEvent enum
   - HookContext dataclass
   - HookResult dataclass
   ```

2. **Hook System** (`lyra_core/hooks/system.py`)
   ```python
   - HookSystem class
   - register() method
   - execute() method
   - Event dispatching
   - Timeout handling
   ```

3. **Hook Types** (`lyra_core/hooks/types/`)
   ```python
   - CommandHook (shell execution)
   - HTTPHook (POST requests)
   - Hook result parsing
   ```

4. **Core Events** (`lyra_core/hooks/events.py`)
   ```python
   - SessionStart
   - PreToolUse
   - PostToolUse
   - Stop
   ```

5. **Tests** (`tests/hooks/`)
   ```python
   - test_system.py
   - test_command_hook.py
   - test_http_hook.py
   - test_events.py
   ```

**Success Criteria:**
- [ ] Hook registration works
- [ ] Command hooks execute
- [ ] HTTP hooks POST correctly
- [ ] Event lifecycle works
- [ ] Timeout enforcement
- [ ] 90%+ test coverage

---

### Week 4: Integration & Tool Execution

**Objectives:**
- Integrate registry, permissions, and hooks
- Build complete tool execution flow
- Add more built-in tools

**Deliverables:**

1. **Tool Executor** (`lyra_core/tools/executor.py`)
   ```python
   - ToolExecutor class
   - execute() method with full lifecycle:
     * Parameter validation
     * PreToolUse hooks
     * Permission checking
     * Tool execution
     * PostToolUse hooks
     * Error handling
   ```

2. **Additional Built-in Tools** (`lyra_core/tools/builtin/`)
   ```python
   - Edit tool (file editing)
   - Write tool (file creation)
   - Bash tool (shell execution)
   - TaskCreate/TaskList/TaskUpdate
   ```

3. **CLI Integration** (`lyra_cli/tools.py`)
   ```python
   - Tool command handlers
   - Permission prompts
   - Status display
   ```

4. **Integration Tests** (`tests/integration/`)
   ```python
   - test_tool_execution_flow.py
   - test_permission_integration.py
   - test_hook_integration.py
   ```

**Success Criteria:**
- [ ] Full execution flow works
- [ ] Hooks integrate correctly
- [ ] Permissions enforce properly
- [ ] 10+ built-in tools working
- [ ] CLI integration complete
- [ ] 85%+ test coverage

**Phase 1 Demo:**
- Show tool execution with permission prompts
- Demonstrate hook-based auto-formatting
- Display permission modes in action

---

## Phase 2: Extensibility (Weeks 5-8)

### Week 5: MCP Foundation

**Objectives:**
- Implement MCP server manager
- Add stdio transport
- Create tool discovery

**Deliverables:**

1. **MCP Schema** (`lyra_core/mcp/schema.py`)
   ```python
   - MCPServerConfig dataclass
   - MCPTransport enum
   - MCPTool dataclass
   - MCPResource dataclass
   ```

2. **MCP Server Manager** (`lyra_core/mcp/manager.py`)
   ```python
   - MCPServerManager class
   - add_server() method
   - connect() method (stdio)
   - disconnect() method
   - Auto-reconnection logic
   ```

3. **MCP Client** (`lyra_core/mcp/client.py`)
   ```python
   - MCPClient class
   - list_tools() method
   - call_tool() method
   - list_resources() method
   - read_resource() method
   ```

4. **Tests** (`tests/mcp/`)
   ```python
   - test_manager.py
   - test_client.py
   - test_stdio_transport.py
   - Mock MCP server for testing
   ```

**Success Criteria:**
- [ ] MCP server connection works
- [ ] Tool discovery works
- [ ] Tool execution works
- [ ] stdio transport stable
- [ ] 90%+ test coverage

---

### Week 6: MCP HTTP & Authentication

**Objectives:**
- Add HTTP and SSE transports
- Implement OAuth 2.0 authentication
- Add resource support

**Deliverables:**

1. **HTTP Transport** (`lyra_core/mcp/transports/http.py`)
   ```python
   - HTTPTransport class
   - Connection management
   - Request/response handling
   - Reconnection logic
   ```

2. **SSE Transport** (`lyra_core/mcp/transports/sse.py`)
   ```python
   - SSETransport class
   - Event stream handling
   - Reconnection logic
   ```

3. **OAuth Support** (`lyra_core/mcp/auth.py`)
   ```python
   - OAuthAuthenticator class
   - Authorization flow
   - Token refresh
   - Credential storage
   ```

4. **Resource Support** (`lyra_core/mcp/resources.py`)
   ```python
   - Resource listing
   - Resource reading
   - @ mention integration
   ```

5. **Tests** (`tests/mcp/`)
   ```python
   - test_http_transport.py
   - test_sse_transport.py
   - test_oauth.py
   - test_resources.py
   ```

**Success Criteria:**
- [ ] HTTP transport works
- [ ] SSE transport works
- [ ] OAuth flow completes
- [ ] Resources accessible
- [ ] 90%+ test coverage

---

### Week 7: Plugin System

**Objectives:**
- Implement plugin manager
- Add plugin manifest parsing
- Create component loading

**Deliverables:**

1. **Plugin Schema** (`lyra_core/plugins/schema.py`)
   ```python
   - PluginManifest dataclass
   - PluginComponent enum
   - Dependency resolution
   ```

2. **Plugin Manager** (`lyra_core/plugins/manager.py`)
   ```python
   - PluginManager class
   - install() method
   - enable() method
   - disable() method
   - Component loading
   ```

3. **Plugin Loader** (`lyra_core/plugins/loader.py`)
   ```python
   - load_skills() method
   - load_agents() method
   - load_hooks() method
   - load_mcp_servers() method
   - load_tools() method
   ```

4. **Marketplace Client** (`lyra_core/plugins/marketplace.py`)
   ```python
   - MarketplaceClient class
   - search() method
   - download() method
   - Version management
   ```

5. **Tests** (`tests/plugins/`)
   ```python
   - test_manager.py
   - test_loader.py
   - test_marketplace.py
   - Sample test plugins
   ```

**Success Criteria:**
- [ ] Plugin installation works
- [ ] Component loading works
- [ ] Dependencies resolve
- [ ] Marketplace integration
- [ ] 90%+ test coverage

---

### Week 8: Tool Search & Optimization

**Objectives:**
- Implement deferred tool loading
- Add tool search functionality
- Optimize context usage

**Deliverables:**

1. **Tool Search** (`lyra_core/tools/search.py`)
   ```python
   - ToolSearch class
   - Deferred tool loading
   - Search by description
   - Relevance scoring
   ```

2. **Context Optimizer** (`lyra_core/tools/optimizer.py`)
   ```python
   - ContextOptimizer class
   - Tool deferral logic
   - Threshold-based loading
   - alwaysLoad support
   ```

3. **MCP Tool Search** (`lyra_core/mcp/tool_search.py`)
   ```python
   - MCP tool deferral
   - On-demand loading
   - Server instructions parsing
   ```

4. **Performance Tuning** (`lyra_core/tools/performance.py`)
   ```python
   - Caching improvements
   - Parallel execution
   - Resource pooling
   ```

5. **Tests** (`tests/tools/`)
   ```python
   - test_search.py
   - test_optimizer.py
   - test_performance.py
   - Benchmark suite
   ```

**Success Criteria:**
- [ ] Tool search works
- [ ] Deferred loading reduces context
- [ ] Performance benchmarks met
- [ ] 90%+ test coverage

**Phase 2 Demo:**
- Show MCP server integration
- Demonstrate plugin installation
- Display tool search in action
- Show context optimization

---

## Phase 3: Advanced Features (Weeks 9-12)

### Week 9: Channel System

**Objectives:**
- Implement channel architecture
- Add notification system
- Create reply tools

**Deliverables:**

1. **Channel Schema** (`lyra_core/channels/schema.py`)
   ```python
   - ChannelConfig dataclass
   - ChannelNotification dataclass
   - ChannelCapability enum
   ```

2. **Channel Manager** (`lyra_core/channels/manager.py`)
   ```python
   - ChannelManager class
   - register_channel() method
   - handle_notification() method
   - Permission relay support
   ```

3. **Built-in Channels** (`lyra_core/channels/builtin/`)
   ```python
   - WebhookChannel (HTTP receiver)
   - FileWatcherChannel (file changes)
   ```

4. **Reply Tools** (`lyra_core/channels/reply.py`)
   ```python
   - ReplyTool class
   - Two-way communication
   - Message routing
   ```

5. **Tests** (`tests/channels/`)
   ```python
   - test_manager.py
   - test_webhook.py
   - test_file_watcher.py
   - test_reply.py
   ```

**Success Criteria:**
- [ ] Channel registration works
- [ ] Notifications deliver
- [ ] Reply tools work
- [ ] Permission relay works
- [ ] 90%+ test coverage

---

### Week 10: Subagent System

**Objectives:**
- Implement subagent spawning
- Add tool restriction
- Create result aggregation

**Deliverables:**

1. **Subagent Schema** (`lyra_core/agents/schema.py`)
   ```python
   - SubagentDefinition dataclass
   - SubagentConfig dataclass
   - IsolationMode enum
   ```

2. **Subagent Manager** (`lyra_core/agents/manager.py`)
   ```python
   - SubagentManager class
   - spawn() method
   - Tool restriction logic
   - Result collection
   ```

3. **Subagent Executor** (`lyra_core/agents/executor.py`)
   ```python
   - SubagentExecutor class
   - Foreground execution
   - Background execution
   - Max turns enforcement
   ```

4. **Built-in Subagents** (`lyra_core/agents/builtin/`)
   ```python
   - Explore agent
   - Plan agent
   - Review agent
   ```

5. **Tests** (`tests/agents/`)
   ```python
   - test_manager.py
   - test_executor.py
   - test_builtin_agents.py
   ```

**Success Criteria:**
- [ ] Subagent spawning works
- [ ] Tool restriction works
- [ ] Results aggregate correctly
- [ ] Built-in agents work
- [ ] 90%+ test coverage

---

### Week 11: Agent Teams (Experimental)

**Objectives:**
- Implement agent team coordination
- Add shared task list
- Create inter-agent messaging

**Deliverables:**

1. **Team Schema** (`lyra_core/teams/schema.py`)
   ```python
   - TeamConfig dataclass
   - TeammateDefinition dataclass
   - TeamMessage dataclass
   ```

2. **Team Manager** (`lyra_core/teams/manager.py`)
   ```python
   - TeamManager class
   - create_team() method
   - spawn_teammate() method
   - disband_team() method
   ```

3. **Task List** (`lyra_core/teams/tasks.py`)
   ```python
   - SharedTaskList class
   - Task claiming (with locking)
   - Dependency tracking
   - Status updates
   ```

4. **Messaging** (`lyra_core/teams/messaging.py`)
   ```python
   - Mailbox class
   - send_message() method
   - receive_message() method
   - Broadcast support
   ```

5. **Tests** (`tests/teams/`)
   ```python
   - test_manager.py
   - test_tasks.py
   - test_messaging.py
   - Integration tests
   ```

**Success Criteria:**
- [ ] Team creation works
- [ ] Task claiming works
- [ ] Messaging works
- [ ] Coordination works
- [ ] 85%+ test coverage

---

### Week 12: Context Management & Polish

**Objectives:**
- Implement checkpointing
- Add context compaction
- Polish and documentation

**Deliverables:**

1. **Checkpointing** (`lyra_core/context/checkpointing.py`)
   ```python
   - CheckpointManager class
   - create_checkpoint() method
   - restore() method
   - Rewind menu support
   ```

2. **Context Compaction** (`lyra_core/context/compaction.py`)
   ```python
   - ContextCompactor class
   - auto_compact() method
   - Summarization
   - Trigger thresholds
   ```

3. **Goal System** (`lyra_core/goals/system.py`)
   ```python
   - GoalManager class
   - set_goal() method
   - evaluate() method
   - Auto-continuation
   ```

4. **Documentation** (`docs/`)
   ```markdown
   - Tool reference
   - Permission guide
   - Hook guide
   - MCP guide
   - Plugin guide
   - API reference
   ```

5. **Polish** (Various)
   ```python
   - Error message improvements
   - Performance optimization
   - Bug fixes
   - UI refinements
   ```

**Success Criteria:**
- [ ] Checkpointing works
- [ ] Compaction works
- [ ] Goal system works
- [ ] Documentation complete
- [ ] All tests passing
- [ ] Performance benchmarks met

**Phase 3 Demo:**
- Show channel-driven workflows
- Demonstrate agent teams
- Display context management
- Complete feature showcase

---

## Testing Strategy

### Unit Tests (Throughout)

**Coverage Target:** 90%+

**Test Categories:**
- Schema validation
- Core logic
- Edge cases
- Error handling
- Performance

**Tools:**
- pytest
- pytest-cov
- pytest-asyncio
- pytest-mock

### Integration Tests (Each Phase)

**Coverage Target:** 85%+

**Test Scenarios:**
- Component interaction
- End-to-end flows
- Error propagation
- State management

**Tools:**
- pytest
- Docker (for MCP servers)
- Mock servers

### Performance Tests (Week 8, 12)

**Benchmarks:**
- Tool execution latency (<100ms)
- Permission check overhead (<10ms)
- Hook execution time (<50ms)
- MCP call latency (<200ms)
- Plugin load time (<500ms)

**Tools:**
- pytest-benchmark
- memory_profiler
- py-spy

### End-to-End Tests (Week 12)

**Scenarios:**
- Complete workflows
- Multi-tool operations
- Plugin integration
- Error recovery
- Performance under load

---

## Documentation Plan

### Week 4: Foundation Docs
- Tool system overview
- Permission guide basics
- Hook guide basics
- Getting started

### Week 8: Extensibility Docs
- MCP integration guide
- Plugin development guide
- Advanced permissions
- Advanced hooks

### Week 12: Complete Docs
- Full API reference
- Architecture guide
- Best practices
- Troubleshooting
- Migration guide

---

## Risk Management

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| MCP protocol changes | High | Follow spec closely, version compatibility |
| Performance issues | Medium | Early benchmarking, optimization sprints |
| Complex permission patterns | Medium | Comprehensive test suite, user testing |
| Hook execution safety | High | Sandboxing, timeouts, resource limits |
| Plugin conflicts | Medium | Dependency resolution, isolation |

### Schedule Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scope creep | High | Strict phase boundaries, MVP focus |
| Integration delays | Medium | Early integration tests, continuous integration |
| Testing bottlenecks | Medium | Parallel test development, automation |
| Documentation lag | Low | Continuous documentation, templates |

---

## Success Metrics

### Phase 1 (Week 4)
- [ ] 10+ built-in tools working
- [ ] Permission system functional
- [ ] Basic hooks operational
- [ ] 90%+ test coverage
- [ ] Demo successful

### Phase 2 (Week 8)
- [ ] MCP integration complete
- [ ] Plugin system working
- [ ] Tool search functional
- [ ] 5+ MCP servers tested
- [ ] 3+ plugins available
- [ ] 90%+ test coverage
- [ ] Demo successful

### Phase 3 (Week 12)
- [ ] All features complete
- [ ] Channel system working
- [ ] Agent teams functional
- [ ] Context management complete
- [ ] Documentation complete
- [ ] 90%+ test coverage
- [ ] Performance benchmarks met
- [ ] Final demo successful

---

## Resource Requirements

### Team
- 2 Senior Engineers (full-time)
- 1 QA Engineer (full-time)
- 1 Technical Writer (part-time, weeks 4, 8, 12)

### Infrastructure
- CI/CD pipeline
- Test environments
- Docker for MCP testing
- Documentation hosting

### Tools
- Python 3.10+
- pytest ecosystem
- Docker
- Git
- Documentation tools (Sphinx/MkDocs)

---

## Deployment Strategy

### Week 4: Internal Alpha
- Core team testing
- Bug fixes
- Performance tuning

### Week 8: Beta Release
- Limited user group (10-20 users)
- Feedback collection
- Documentation refinement
- Bug fixes

### Week 12: General Availability
- Full rollout
- Migration support
- Training materials
- Support channels

---

## Post-Implementation

### Maintenance (Ongoing)
- Bug fixes
- Security updates
- Performance optimization
- Documentation updates

### Future Enhancements (Post-Week 12)
- Additional built-in tools
- More MCP servers
- Plugin marketplace
- Advanced agent features
- UI/UX improvements

---

## Appendix A: Tool Priority List

### Phase 1 (Must Have)
1. Read
2. Write
3. Edit
4. Glob
5. Grep
6. Bash
7. TaskCreate/List/Update
8. Skill

### Phase 2 (Should Have)
9. LSP
10. WebSearch
11. WebFetch
12. Agent (subagents)
13. NotebookEdit
14. Monitor

### Phase 3 (Nice to Have)
15. PowerShell
16. SendMessage
17. TeamCreate/Delete
18. CronCreate/List/Delete
19. PushNotification
20. RemoteTrigger

---

## Appendix B: MCP Server Examples

### Week 5-6 Testing
1. **filesystem** - File operations
2. **sqlite** - Database access
3. **github** - GitHub API
4. **slack** - Slack integration

### Week 8 Integration
5. **postgres** - PostgreSQL
6. **redis** - Redis cache
7. **aws** - AWS services
8. **google** - Google APIs

---

## Appendix C: Plugin Examples

### Week 7 Development
1. **code-intelligence** - LSP integration
2. **git-tools** - Git operations
3. **docker-tools** - Docker management

### Week 8 Testing
4. **security-scanner** - Security checks
5. **formatter** - Code formatting
6. **linter** - Code linting

---

## References

- US-007: Claude Code Tools Inventory
- TOOLS-SYSTEM.md: Architecture Proposal
- Claude Code Documentation: https://code.claude.com/docs
- MCP Specification: https://modelcontextprotocol.io

**Document Status:** Planning  
**Next Steps:** Team review, resource allocation, kickoff  
**Estimated Effort:** 12 weeks, 2 senior engineers + 1 QA + 1 tech writer
