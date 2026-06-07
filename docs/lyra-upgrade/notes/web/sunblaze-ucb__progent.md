# sunblaze-ucb/progent -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**Progent** is a privilege-control framework for LLM-based agents that enforces least-privilege on tool calls via dynamically generated, monotonic security policies. The headline feature is **runtime privilege confinement with monotonic safety**: an LLM generates JSON Schema-based restrictions on tool arguments at query time, an SMT solver (Z3) validates that policy updates are narrowing (permitted automatically) versus expansion (requires user approval), and a middleware proxy intercepts every tool call to check against the active policy before execution.

The mechanism operates as a transparent **MCP (Model Context Protocol) proxy** sitting between the agent and its tool backend. The flow:

1. **Policy Generation**: When a user query arrives, the system prompts an LLM (configurable: GPT-4o, Claude, Gemini, local models) with a prompt listing available tools and their JSON Schemas. The LLM outputs a per-tool, per-argument restriction set as JSON Schema constraints (enum, pattern, minLength, etc.).
2. **Policy Enrichment**: Read-only tools (e.g., `get_balance`, `read_channel_messages`) are pre-allowed automatically. The system maintains a priority-sorted policy list per tool.
3. **Dynamic Policy Updates**: After each tool call, the system may ask the LLM whether the result can narrow or expand the policy. If narrowing: auto-applied. If expanding: requires `SECAGENT_ONLY_ALLOW_NARROW` flag validation via Z3 SMT solver (`security_policy_subset_check` in `policy_analysis.py`).
4. **Enforcement**: A middleware layer on the MCP server intercepts `on_call_tool`, validates `kwargs` against the policy's JSON Schema using `jsonschema.validate()`, and raises `ValidationError` on violations.

The key innovation is not the LLM-based policy generation itself but the **monotonic confinement via SMT subset-checking**: Z3 is used to prove that a proposed new policy is a subset of the existing one (no expansion), making auto-approval safe.

## 2. Architecture & Core Modules (entry points, data flow, patterns)

### Repository Structure

```
sunblaze-ucb__progent/
  pyproject.toml          # Root package: "secagent" v0.1.0
  secagent/                # Core library (the actual Progent code)
    __init__.py            # Re-exports: Tool, check_tool_call, generate_security_policy, etc.
    progent_proxy.py       # Main entry point -- MCP proxy server with FastAPI REST layer
    tool.py                # Policy data structures, API calls to LLMs, policy generation/update logic
    policy_analysis.py     # Z3-based SMT: overlap detection, subset checking
    policy_type_check.py   # JSON Schema type-keyword validation (doesn't mix type-specific keys)
    role_analyzer.py       # Z3 model for role-based access control (RBAC) -- adapted from k8s RBAC linter
    mcp_proxy.py           # Simple MCP-only proxy (no REST) for demonstration
    utils.py               # JSON extraction from LLM text output
  agentdojo/               # Fork of ETHZ AgentDojo benchmark (tool-calling tasks)
    src/agentdojo/
      scripts/benchmark.py
      agent_pipeline/      # Agent execution pipeline
      attacks/             # Prompt injection attacks
      default_suites/      # Banking, Slack, Travel, Workspace task suites (v1, v1.1, v1.2, v1.1.1, v1.1.2)
    run.sh
  agentdojo-mcp/           # MCP server variant of AgentDojo
    mcp_server.py          # REST + MCP server that initializes tasks, runs agents
    mcp_server.py lines 33-76: init_task, finish_task endpoints
  asb/                     # Fork of Agent Security Bench (ICLR 2025)
    main_attacker.py       # Attack execution: scheduler, agent factory, result evaluation
  real-world-agents/       # Agent runners for OpenAI SDK, LangChain, AutoGen, OpenHands
    run.py                 # Suite orchestrator calling agent scripts
    openai-agent-sdk.py
    langchain-agent.py
    autogen-multi-agent.py
    openhands-agent.py
```

### Entry Points

- **Primary**: `secagent/progent_proxy.py` -- `if __name__ == "__main__":` starts two servers on separate threads:
  - `REST API` (port 9100): proxies LLM API calls (e.g., to OpenAI). Extracts user queries from messages, triggers security policy generation.
  - `MCP Proxy` (port 9101): intercepts tool listings (`on_list_tools`) and tool calls (`on_call_tool`). Applies middleware: `ListingFilterMiddleware` (captures tool schemas, classifies by agent domain) and `ToolCallFilterMiddleware` (validates each call).

- **Agent-dojo MCP**: `agentdojo-mcp/mcp_server.py` -- a standalone server that initializes tasks, runs agents, and evaluates utility/security.

### Data Flow

```
User Query
    |
    v
[REST API Proxy] -- extracts user input, calls generate_security_policy()
    |
    v
[LLM API] -- generates JSON Schema restrictions per tool             
    |
    v
[Policy Store] -- priority-sorted tuples: (priority, effect, restrictions, fallback)
    |
    v
[Agent] -- calls tool via MCP
    |
    v
[ToolCallFilterMiddleware] -- check_tool_call() validates kwargs against policy
    |                           - No policy for tool -> disallowed
    |                           - Matching allow rule -> passes
    |                           - Matching forbid rule -> blocks (message/terminate/prompt user)
    v
[Tool Execution] -- actual tool runs (if allowed)
    |
    v
[generate_update_security_policy] -- LLM decides if result can narrow the policy
    |                                   - Z3 subset check validates narrowing
    v
[Updated Policy]
```

### Patterns

- **Middleware Chain**: Both MCP proxy servers use FastMCP's middleware pattern. `ListingFilterMiddleware` and `ToolCallFilterMiddleware` are added to the server object.
- **Priority-Ordered Policy**: Each tool has a list of `(priority, effect, conditions, fallback)` tuples, sorted by priority descending. Higher priority takes precedence.
- **SMT-Based Formal Verification**: Z3 SMT solver (`z3-solver` dependency) is used for:
  - **Overlap detection**: Do two restriction schemas overlap (can produce same value)?
  - **Subset checking**: Is a proposed update strictly narrower than the current policy?
- **Adapter Pattern**: Framework-specific adapters for LangChain (`SecAgentLangchainMiddleware`) and OpenAI Agents SDK (`openai_agent_wrapper`, `openai_tool_wrapper`).

## 3. Performance/Benchmarks (real numbers from the repo)

The paper (arXiv 2504.11703) evaluates on **AgentDojo** and **ASB** benchmarks. Key results reported in the paper:

- **Significantly reduces attack success rates** across all AgentDojo suites (banking, slack, travel, workspace) while maintaining high utility.
- **The paper's results page**: AgentDojo results are tracked at `agentdojo.spylab.ai/results/` (not in the repo as static files).
- The ASB benchmark covers 10 diverse agent scenarios (academic, counseling, investment, legal, etc.) with attacks including DPI, OPI, memory poisoning, and PoT backdoor.
- Exact numerical tables are in the paper PDF, not in the codebase.
- **Token overhead**: The policy LLM call adds latency and token cost per query and per tool call update decision. The code tracks `total_completion_tokens` and `total_prompt_tokens` (commented out in `tool.py` lines 182-185, 253-255).

## 4. Trade-offs (wins vs loses -- from issues, design decisions, complexity)

### Wins
- **Monotonic safety guarantee**: No expansion of agent privileges without explicit approval or a narrowing proof from Z3. This is a strong formal property.
- **Autonomous but bounded**: Agent can act autonomously within a dynamically shrinking action space.
- **Multi-framework**: Works with OpenAI SDK, LangChain, AutoGen, OpenHands, and any MCP-compatible agent.
- **Model-agnostic policy LLM**: Supports GPT-4o, GPT-4.1, o3, Claude, Gemini, Llama, Qwen -- can use cheap models for policy generation.
- **Domain-aware pre-allowed tools**: Read-only tools are auto-allowed by suite (banking, slack, travel, workspace), reducing friction.

### Losses (limitations observed from code)

1. **LLM quality dependency on policy generation**: The entire security posture depends on the policy LLM correctly inferring restrictions from a user query. If the LLM misses constraints or generates over-permissive schemas, the agent is vulnerable.
2. **Latency**: Each tool call can trigger `decide_whether_to_update()` (another LLM call) + optional `generate_update_security_policy()` + Z3 solving. The timeout flag `SECAGENT_IGNORE_UPDATE_ERROR` suggests update failures are expected and tolerated silently.
3. **SMT solver limitations**: `role_analyzer.py` has explicit `NotImplementedError` for regex anchors (`^`, `$`, `\b`), word boundaries, and lookahead/lookbehind. The Z3 translation of Python regex is partial -- anchor-free patterns only. The `RegexReplaceFunctionConstraint` is explicitly `NotImplementedError` (line 596-597).
4. **Hardcoded suite configurations**: The tool classification by `agent_expert` (general/workspace/slack/banking/travel/web) in `progent_proxy.py` lines 136-206 is hand-crafted and fragile. Adding a new domain requires code changes.
5. **Static suite definitions**: Both AgentDojo and ASB suites have hardcoded task definitions. The `run.py` in `real-world-agents` defines all user/injection task IDs as string lists.
6. **No streaming support mentioned**: The proxy buffers entire request/response bodies (`await request.body()`, full response collection) before forwarding.
7. **Human-in-the-loop friction**: Fallback mode 2 (`fallback == 2`) prompts the user for every blocked-but-uncertain call via stdin. Non-interactive deployments need different handling.
8. **Evaluation edge case**: The README (agentdojo/README.md lines 18-19) notes a specific bug in injection task 5 (slack suite): even blocked tool calls create trace entries that are misclassified as successful attacks, requiring manual correction.

## 5. Design Rationale (why this approach)

- **Why a proxy instead of agent-side modifications?**: Proxying the MCP layer makes the defense agent-agnostic. Any MCP-compatible agent (OpenAI, LangChain, AutoGen, OpenHands) gets protected without code changes.
- **Why Z3 SMT?**: Overlap detection and subset checking on JSON Schema constraints require reasoning about infinite sets of possible values. Z3's string solver and regex support (`z3.InRe`, `z3.Concat`, `z3.Star`, etc.) provide sound formal guarantees that heuristic comparison cannot.
- **Why dynamic policy instead of static RBAC?**: The authors argue that security requirements evolve based on the user's task and execution state. A static policy would be either too permissive (no security) or too restrictive (breaks utility). Dynamic narrowing achieves both via the principle of least privilege.
- **Why monotonic confinement?**: The constraint that privileges can only shrink (never automatically expand) prevents the agent from escalating its own permissions, even if compromised via prompt injection. This is the paper's central security contribution.
- **Why permissive read-only defaults?**: Read-only tools (e.g., `get_balance`, `read_channel_messages`) are always allowed because they cannot modify state. This reduces false positives without compromising security.
- **Why both REST API and MCP proxy?**: The REST API intercepts the LLM API call (to extract the user query for policy generation), while the MCP proxy intercepts tool calls for enforcement. Two separate interception points for two different attack surfaces.

## 6. Transfer to Lyra (one idea + SS 4.x route + Impact/Effort/Tier + LICENSE)

### Transferable Idea

**Monotonic privilege confinement for Lyra's tool-calling agent via an SMT-validated narrowing policy**.

Lyra currently lacks runtime privilege control for its tools. By inserting an MCP middleware proxy (or equivalent langchain/tool-call middleware) that generates and enforces per-query JSON Schema restrictions, Lyra could enforce least-privilege on tool calls. The key insight to borrow: use an SMT solver (Z3) to formally verify that policy updates are narrowing, preventing any self-escalation via indirect prompt injection.

Specifically, for Lyra's `ExecCommand` / `Read` / `Write` / `WebFetch` / `Bash` tools, the system would:
1. Generate an initial policy from the user task description (allow editing files mentioned in the task only; allow executing npm/test commands only).
2. After each tool call result, attempt to narrow (but never expand) the policy.
3. Use an SMT solver to prove narrowing before auto-applying.

### Workstream Route

SS 4.1 (Safety & Guardrails) -- this is a defense against prompt injection and tool misuse. It slots into the safety infrastructure workstream already planned for Lyra.

### Impact / Effort / Tier

- **Impact**: 7 -- High. Provides formal safety guarantees for tool use, addressing a critical vulnerability in autonomous agent execution (indirect prompt injection via tool results).
- **Effort**: 6 -- Significant. Requires: (a) integrating Z3 or an equivalent SMT solver into the Python dependency tree, (b) implementing middleware in the tool execution layer, (c) designing prompt templates for policy generation/granularity per Lyra tool, (d) handling the policy update loop, (e) testing across all Lyra tool categories.
- **Tier**: P1 (Safety). This directly addresses the indirect prompt injection attack vector, which is arguably the highest-priority threat model for an agent that executes arbitrary commands and reads files.

### LICENSE

The repo is **MIT License** (all three subcomponents: agentdojo, agentdojo-mcp, asb). Compatible with Lyra's use.
