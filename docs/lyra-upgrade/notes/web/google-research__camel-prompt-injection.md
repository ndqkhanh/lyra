# google-research/camel-prompt-injection -- Deep-Read

Paper: [CaMeL: Defeating Prompt Injections by Design](https://arxiv.org/abs/2503.18813)

## 1. Headline Feature & Mechanism

CaMeL is a **defense architecture against prompt injection attacks** on LLM agents. Instead of bolting a prompt-level defense on top of a standard tool-calling loop, CaMeL changes the fundamental architecture: the LLM generates Python code, and a **custom AST-walking interpreter** executes it. The LLM never calls tools directly -- it calls them indirectly through a sandboxed interpreter that enforces **data-flow taint tracking** and **per-tool security policies**.

The mechanism has four layers:

1. **Code Generation**: The LLM receives a system prompt that describes available tools as Python function stubs, along with allowed built-in types, methods, classes, and strict coding rules (no imports, no while loops, no try/except, no function definitions). The LLM generates a markdown code block.

2. **Custom Interpreter** (`interpreter/interpreter.py`): A Python AST-walking interpreter that handles a **subset** of Python (no while/break/continue/try/except/with/async/lambda/yield/import). ~2700 lines implementing `camel_eval()` as a large match/case on AST node types. Every value is wrapped in a `CaMeLValue` that carries `Capabilities` metadata tracking the data's `sources_set` and `readers_set`.

3. **Data-Flow Taint Tracking** (`capabilities/`): Every value computed in the interpreter carries a `Capabilities` object with:
   - `sources_set` -- where the data came from (`SourceEnum.User`, `SourceEnum.CaMeL`, `Tool("send_email", {...})`, etc.)
   - `readers_set` -- who can read this data (either `Public()` or a `frozenset` of email addresses/entities)
   
   These propagate through **dependencies** -- when a new value is computed from old values, it inherits combined source/reader metadata. The `is_trusted()` function checks whether all sources in the chain are trusted (User, CaMeL, Assistant, TrustedToolSource).

4. **Security Policies** (`security_policy.py`, `pipeline_elements/security_policies/`): Before every tool call, `eval_args.security_policy_engine.check_policy()` is invoked. Each suite (workspace, banking, travel, slack) has its own `SecurityPolicyEngine` subclass defining:
   - **No-side-effect tools** allowed without checks (read-only queries like `search_emails`, `get_balance`)
   - **Side-effect tool policies** that check argument trust: `send_email` checks that recipients/body/subject/attachments have readers covering all recipients; `send_money` checks trust of recipient and readability of amount/subject; `delete_email` requires the email_id to come from the user (untrusted), etc.

A secondary mechanism is the **Quarantined LLM** (`quarantined_llm.py`): a separate LLM invocation (same or different model) for parsing unstructured data into structured schemas. It is called as a tool `query_ai_assistant()` and uses `pydantic-ai` to enforce structured output. If it cannot extract the information, it raises `NotEnoughInformationError`.

## 2. Architecture & Core Modules

```
src/camel/
  __init__.py                     -- empty
  models.py                       -- Model registry + make_tools_pipeline() entry point
  system_prompt_generator.py      -- Generates the system prompt exposing tools as Python stubs
  security_policy.py              -- Base SecurityPolicy/SecurityPolicyEngine protocol
  quarantined_llm.py              -- Separate LLM for structured data extraction
  conditional_cache.py            -- LRU cache for metadata propagation
  chat_turn.py                    -- Chat turn types
  custom_yaml.py                  -- YAML customizations
  count_tokens.py                 -- Token counting for benchmarks
  
  capabilities/
    __init__.py                   -- Re-exports
    capabilities.py               -- Capabilities frozen dataclass (sources_set, readers_set)
    readers.py                    -- Public dataclass + Readers type alias
    sources.py                    -- SourceEnum (CaMeL, User, Assistant, TrustedToolSource) + Tool source
    utils.py                      -- is_trusted(), is_public(), get_all_readers(), can_readers_read_value()
  
  interpreter/
    __init__.py
    interpreter.py                -- ~2700-line custom AST interpreter (camel_eval)
    library.py                    -- Supported built-in functions/classes/methods
    namespace.py                  -- Namespace (variable store) dataclass
    op_protocols.py               -- Protocol classes for operator overloading
    result.py                     -- Result/Ok/Error pattern
    value.py                      -- CaMeLValue hierarchy (CaMeLStr, CaMeLInt, CaMeLList, CaMeLDict, etc.)
  
  pipeline_elements/
    __init__.py
    privileged_llm.py             -- PrivilegedLLM pipeline element (main orchestration)
    agentdojo_function.py         -- AgentDojoFunction wrapper + metadata annotation
    anthropic_tool_filter.py      -- Anthropic-specific tool filter defense
    old_google_llm.py             -- Legacy Google LLM adapter
    replay_privileged_llm.py      -- Replay mode for policy evaluation
    security_policies/
      agentdojo_security_policies.py  -- Base AgentDojoSecurityPolicyEngine + make_trusted_fields_policy
      workspace.py                    -- Workspace security policies (email, calendar, drive)
      banking.py                      -- Banking security policies (send_money, update_password)
      slack.py                        -- Slack security policies
      travel.py                       -- Travel security policies

main.py                           -- CLI entry point (cyclopts) calling make_tools_pipeline
count_tokens.py                   -- Per-task token usage analysis
print_conversation.py             -- Rich-formatted conversation viewer
run_code.py                       -- Scratch script for ad-hoc experimentation
analysis.ipynb                    -- Full benchmark analysis with LaTeX tables and plots
```

**Data flow**:
1. `main.py` calls `make_tools_pipeline(model, ...)` which constructs an `AgentPipeline` with `PrivilegedLLM`
2. `PrivilegedLLM.query()` receives the user query, builds a namespace with builtins + tool functions, and loops (max 10 attempts) calling `_generate_and_interpret_code()`
3. Each iteration: LLM generates code -> `parse_and_interpret_code()` -> AST-parsed -> `camel_eval()` walks the AST -> every operation propagates Capabilities metadata -> tool calls are intercepted via `AgentDojoFunction.call()` which runs the actual tool + annotates output metadata -> security policy checks happen before each tool invocation
4. On error: exception is caught, formatted with line highlighting, and fed back to the LLM for re-generation

**Architecture pattern**: Pipeline-of-responsibility. The `PrivilegedLLM` is a single `BasePipelineElement` in the AgentDojo pipeline. Three modes:
- **Native**: Standard tool-calling API (baseline)
- **CaMeL (no policies)**: Code generation + interpreter, but `ADNoSecurityPolicyEngine` allowing everything
- **CaMeL**: Code generation + interpreter + per-suite security policies

**Dependencies** (from `pyproject.toml`):
- `agentdojo>=0.1.34` -- the benchmark framework
- `openai>=1.78.1`, `anthropic>=0.51.0`, `google-genai>=1.15.0`, `vertexai>=1.71.1` -- model providers
- `pydantic>=2.11.4`, `pydantic-ai>=0.2.4` -- structured data handling
- `cyclopts>=3.16.1` -- CLI argument parsing
- `tiktoken>=0.9.0` -- token counting
- `jsonref>=1.1.0`, `openapi-pydantic>=0.5.1` -- OpenAPI schema handling

## 3. Performance/Benchmarks

Evaluated on **AgentDojo v1.2** (4 suites: workspace, banking, travel, slack; 20-23 tasks each, 5-30 injection tasks each). Tested models: Gemini 2.5 Flash/Pro, Claude 4 Sonnet, o3 High, o4 Mini High.

**Key results (from analysis.ipynb LaTeX tables)**:

| Model | Undefended ASR | CaMeL ASR | CaMeL + Policies ASR | Undefended N-attacks | CaMeL N-attacks |
|---|---|---|---|---|---|
| Claude 4 Sonnet | ~80% | 13 / 144 | **11 / 144** | 75 | 11 |
| Claude 4 Sonnet* | ~78% | 10 / 144 | **11 / 144** | 75 | 11 |
| Gemini 2.5 Flash | ~40% | 1 / 144 | **1 / 144** | 297 | 1 |
| Gemini 2.5 Pro | ~58% | 0 / 144 | **0 / 144** | 163 | 0 |
| o3 High | ~79% | 1 / 144 | **0 / 144** | 11 | 0 |
| o4 Mini High | ~82% | 1 / 144 | **1 / 144** | 2 | 1 |

**ASR (Attack Success Rate)**: Undefended models range from ~40% (Gemini 2.5 Flash) to ~80% (o4 Mini High). CaMeL + policies reduces ASR to near-zero for most models.

**Utility cost** (drop in task completion rate, no injection):
- Claude 4 Sonnet: -12.4% (86.6% to 74.2%)
- Claude 4 Sonnet*: -13.4% (83.5% to 70.1%)
- Gemini 2.5 Flash: -20.6% (55.7% to 35.1%)
- Gemini 2.5 Pro: -32.0% (73.2% to 41.2%)
- o3 High: -7.2% (84.5% to 77.3%)
- o4 Mini High: -3.1% (79.4% to 76.3%)

Utility drops are uneven across suites. Travel suite is hardest hit (Gemini 2.5 Pro goes from 60% to 0%).

**Comparison to other defenses** (on Claude 3.5 Sonnet):
- Undefended: 44 successful attacks
- Prompt Sandwiching: 24 successful attacks
- Spotlighting: 5 successful attacks
- Tool Filter: 8 successful attacks
- **CaMeL (no policies): 1 successful attack**
- **CaMeL: 0 successful attacks**

CaMeL's code-interpreter approach alone (without per-suite security policies) is already dramatically more effective than the best prompt-level defense (Spotlighting, 5 attacks).

**False-positive rate** (policy triggers on benign tasks): ~27-34% in normal mode, ~45-53% in strict mode -- the security policies sometimes trigger on legitimate user tasks, reducing utility.

## 4. Trade-offs

**Wins**:
- Near-zero attack success rate across all tested models (0-1 successful attacks out of ~144 injection tasks)
- Defense works regardless of model capability -- stronger models are actually easier to defend because they follow code generation rules better
- Architectural, not prompt-level -- no fragile prompt engineering
- Generalizes across model providers (OpenAI, Anthropic, Google)
- The code-interpreter approach alone (without per-tool policies) already defeats most attacks by eliminating the tool-calling API surface
- Token overhead is modest -- median input token increase of ~2x, median output tokens comparable or lower

**Loses**:
- **Utility cost**: 3-32% drop in task completion rates. The custom interpreter is a restricted Python subset -- no while loops, no try/except, no function definitions, no lambdas, no imports, no break/continue
- **Complexity**: ~6000 lines of Python for the custom interpreter + capabilities system. "Likely contains bugs" per the README
- **Model compliance dependency**: The defense relies on the LLM following code generation rules. A model that refuses to generate Python code or generates it in non-standard formats would break the defense
- **Policy false positives**: ~27-34% of successful task completions trigger security policies unnecessarily, causing failures
- **Speed**: Custom interpreter is slower than native API tool-calling. The code adds overhead for AST walking, metadata propagation, and security policy evaluation
- **Not maintained**: Explicitly labeled as a research artifact, not a Google product, not for production use
- **Limited Python subset**: Many useful patterns (try/except for error handling, function definitions for reuse, while loops, context managers) are explicitly forbidden
- **Travel suite weakness**: Some models (Gemini 2.5 Pro, Flash) drop to 0% utility on the travel suite with CaMeL, suggesting poor support for the travel tool patterns

## 5. Design Rationale

The core insight is that **standard tool-calling APIs are inherently vulnerable to prompt injection**. The model receives user text (potentially containing injected instructions) and the tool definitions in the same message, and it decides which tools to call. Any defense that operates at the prompt level (spotlighting, sandwiching, filtering) can be bypassed by a sufficiently clever injection.

CaMeL's approach: **change the abstraction layer**. Instead of the model deciding which tools to call directly, it writes Python code. The code is executed by a custom interpreter that:

1. **Understands the data flow** -- every value carries its provenance (where it came from, who can read it)
2. **Enforces information flow control** -- a value constructed from untrusted data + user data is tainted, and the policies check tool arguments for taint
3. **Is restrictive by default** -- the Python subset eliminates dangerous patterns (while loops that never terminate, imports of malicious modules, eval/exec)
4. **Has a separate pathway for AI-assisted parsing** -- the quarantined LLM is a separate, structured-output-only model that cannot call tools

The `Capabilities` system is the intellectual core. It is a **decentralized information flow control** mechanism similar to Myers and Liskov's JFlow/Decentralized Label Model. Every `CaMeLValue` carries a label describing:
- `sources_set`: who originated this data (the user, a tool, the CaMeL interpreter itself)
- `readers_set`: who is authorized to read this data

Labels propagate through all operations (arithmetic, string concatenation, list construction, etc.). The `is_trusted()` function checks that all sources are in the trusted set -- if any source is untrusted (e.g., data returned from a tool reading an email crafted by an attacker), the value is considered tainted.

Security policies then use this taint information: "send an email only if the body and subject can be read by all recipients" prevents an attacker-injected email body from being sent.

## 6. Transfer to Lyra

**One idea**: Adopt **data-flow taint tracking on tool arguments** for Lyra's tool-calling pipeline.

Lyra currently has no mechanism to track whether a tool argument contains data from an untrusted source (e.g., a user-provided document) versus data from a trusted source (e.g., a confirmed user intent). By wrapping every tool call argument in a capability-bearing wrapper and propagating source/reader metadata through data dependencies, Lyra could add a **policy layer** that blocks dangerous tool calls when arguments are tainted.

**Workstream route**: Section 4.x -- this fits under Section 4 (Architecture), as a cross-cutting safety mechanism. Specifically:
- **Section 4.3 (Tool Integration / Plugin Safety)**: Add a `SecurityPolicyEngine` abstraction at the tool invocation layer. Each plugin/tool registers policies that verify argument trustworthiness before execution.
- **Section 4.2 (Memory/Context Safety)**: Extend the data-flow tracking to memory retrieval -- when injecting context from external sources (documents, web), track which portions are untrusted and which are from the primary user.

**Impact**: 8/10 -- Highly impactful. Prompt injection is the #1 security vulnerability for LLM agents, and Lyra is exposed through file-reading, web-searching, and third-party plugin tool calls. A data-flow taint approach would catch injections at the architectural level rather than relying on prompt vigilance.

**Effort**: 8/10 -- High effort. Requires:
1. A capability-bearing value wrapper throughout the tool-calling path (similar to CaMeL's `CaMeLValue`)
2. A custom interpreter or a post-hoc taint analysis on tool arguments
3. Per-tool security policy definitions
4. Careful handling of string operations where taint can leak (format strings, concatenation)
5. A quarantined LLM pattern for safe structured data extraction

**Tier**: Tier 1 -- Architectural safety improvement. This is not a quick fix; it requires rethinking the tool execution pipeline. However, it's the single most impactful change for Lyra's security posture.

**License**: Apache 2.0 -- fully compatible with open-source reuse.

**Key file**: The security policy module at `src/camel/security_policy.py` (~100 lines) is the cleanest abstraction to port. The `Capabilities` dataclass in `src/camel/capabilities/capabilities.py` (~40 lines) defines the core label model.
