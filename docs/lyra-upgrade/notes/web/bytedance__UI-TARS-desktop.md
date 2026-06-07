# bytedance/UI-TARS-desktop -- Deep-Read

## 1. Headline Feature & Mechanism

**Two products in one monorepo.** The repo ships both **UI-TARS Desktop** (v0.2.4) -- an Electron application that controls your computer with natural language via a Vision-Language Model -- and **Agent TARS** (v0.3.0) -- a newer, general-purpose multimodal AI agent stack with CLI, Web UI, hybrid browser control, and MCP tool integration.

**Core mechanism -- the screenshot-inference-execute loop:**

1. **Screenshot**: An `Operator` captures the current screen (full desktop via `nut-js`/Electron `desktopCapturer`, or browser viewport via Playwright).
2. **Model inference**: The screenshot is sent (as base64 image) to a VLM via an OpenAI-compatible API (Supports UI-TARS-1.5, Seed-1.5-VL/1.6, Doubao-1.5-UI-TARS, or any OpenAI-compatible VLM). The model returns text like `click(start_box='[0.131,0.25,0.131,0.25]')`.
3. **Action parsing**: The `actionParser()` function (in `packages/ui-tars/action-parser/src/actionParser.ts`) uses regex to extract action type, coordinates, and arguments from the model text output. Coordinates are normalized as fractions of the screenshot dimensions and then denormalized to screen pixels.
4. **Action execution**: The operator executes the parsed action -- mouse click/drag, keyboard type/hotkey, scroll, navigate, wait, or terminal actions like `finished()` or `call_user()`.
5. **Loop**: The agent repeats steps 1-4 up to `maxLoopCount` (default 25) times, or until `finished()` is predicted or an error state is reached.

**Agent TARS extends this** with a browser-native approach: it uses a multi-agent architecture (Planner, Navigator, Validator agents via LangChain), extracts DOM structure for clickable-element highlighting, supports hybrid GUI+DOM grounding, and integrates external tools via MCP servers. It has its own `Event Stream` protocol for context engineering and agent UI rendering.

## 2. Architecture & Core Modules

**Monorepo structure** (pnpm workspaces + Turborepo):

```
apps/ui-tars/                         -- Electron desktop app (ui-tars-desktop)
  src/main/main.ts                    -- Electron main process entry
  src/main/agent/operator.ts          -- NutJSElectronOperator (Electron-native screenshot)
  src/main/services/runAgent.ts       -- Orchestrates GUIAgent creation per operator type
  src/main/agent/prompts.ts           -- System prompts by model version
  src/renderer/                       -- React UI (zustand state mgmt + Tailwind CSS)
  package.json                        -- ui-tars-desktop v0.2.4
packages/ui-tars/
  sdk/src/index.ts                    -- Exports GUIAgent class
  sdk/src/GUIAgent.ts                 -- Core agent loop (screenshot -> model -> execute)
  sdk/src/Model.ts                    -- UITarsModel (OpenAI-compatible VLM client)
  sdk/src/core.ts                     -- Exports Operator, Model, UITarsModel, types
  sdk/src/utils.ts                    -- parseBoxToScreenCoords, convertToOpenAIMessages, etc.
  sdk/src/types.ts                    -- Operator/Model abstract classes, GUIAgentConfig
  sdk/src/base/index.ts               -- BaseGUIAgent, BaseModel, BaseOperator abstracts
  sdk/src/constants.ts                -- System prompts, action space definitions
  cli/src/index.ts                    -- CLI entry (npx @ui-tars/cli start)
  cli/src/cli/commands.ts             -- Commander-based CLI
  cli/src/cli/start.ts                -- CLI agent creation flow
  action-parser/src/actionParser.ts   -- Regex-based parser for VLM action text output
  operators/nut-js/src/index.ts        -- NutJSOperator (cross-platform computer control)
  operators/browser-operator/src/      -- BrowserOperator (Playwright-based browser agent)
  shared/                             -- Shared types, constants, model version enums
packages/agent-infra/                  -- Agent TARS infrastructure
  browser-use/src/                     -- Browser-use agent (multi-agent: planner, navigator, validator)
    agent/executor.ts                  -- Executor loop with planning/navigation/validation
    agent/agents/base.ts               -- BaseAgent with structured output + LangChain
    agent/agents/navigator.ts          -- DOM + visual navigation agent
    agent/agents/planner.ts            -- Task planning agent
    agent/agents/validator.ts          -- Output validation agent
  browser/src/                         -- Local/Remote browser abstraction
  mcp-client/                          -- MCP client for Electron (same-process approach)
  mcp-servers/                         -- MCP servers (browser, commands, filesystem, search)
multimodal/                            -- Older separate versioned packages (agent-tars, tarko, omni-tars)
```

**Data Flow** (for UI-TARS Desktop -- the simpler case):

```
User Instruction
  -> GUIAgent.run(instruction)
    -> Loop:
      -> operator.screenshot() -> base64 image + scaleFactor
      -> Jimp preprocess (resize, compress)
      -> model.invoke(screenshot + conversation history) -> text prediction
      -> actionParser.parse(text) -> PredictionParsed[] (action_type + action_inputs)
      -> operator.execute(parsedPrediction) -> mouse/keyboard/browser action
      -> callback onData({ data }) emits delta conversation
    -> End when: finished() / call_user() / maxLoopCount / error
```

**Design patterns used:**
- **Plugin/Strategy Pattern**: The `Operator` abstract class (defined in `sdk/src/types.ts`) is implemented by `NutJSOperator`, `BrowserOperator`, `AdbOperator`, etc. The agent is operator-agnostic.
- **Observer/Event-Driven**: `onData`/`onError` callbacks stream state as delta events. The Event Stream concept is core to Agent TARS.
- **Abstract Base Classes**: `BaseGUIAgent<TConfig, TParams, TOutput>`, `BaseModel`, `BaseOperator` form a type-safe generic hierarchy.
- **Dependency Injection**: Context (`logger`, `factors`, `signal`) is injected into operators via `setContext()`/`useContext()`.
- **Retry Wrapper**: `async-retry` wraps screenshot, model invoke, and action execution with configurable retries.

## 3. Performance/Benchmarks

The repo includes three benchmark suites, none of which measure end-to-end agent performance (since that depends on VLM quality):

1. **MCP Transport Benchmark** (`packages/agent-infra/mcp-benchmark/benchmarks/browser_server.bench.ts`):
   - Compares 7 transport strategies: StdioTransport, SSETransport, StreamableHTTPTransport, InMemoryTransport, supergateway, mcp-proxy (Python), mcp-proxy (TypeScript), mcp-http-server
   - Measures tool listing latency per transport (using vitest bench)

2. **Content Extraction Benchmark** (`multimodal/benchmark/content-extraction/src/benchmark-runner.ts`):
   - Evaluates different content extraction strategies from web pages
   - Metrics: execution time (ms), extracted length, token count, memory usage (MB), compression ratios

3. **Action Parser Benchmark** (`packages/ui-tars/action-parser/test/index.bench.ts`):
   - Microbenchmark for the action parser regex engine

**No published end-to-end agent benchmarks** (accuracy rates, task completion rates, etc.) exist in this repo -- those are in the UI-TARS research paper (arXiv 2501.12326).

## 4. Trade-offs

| Dimension | Win | Loss |
|-----------|-----|------|
| **Platform reach** | Cross-platform via Electron (Mac/Win/Linux); Android via ADB operator | Single-monitor only as of v0.2.4; macOS requires Accessibility + Screen Recording permissions |
| **Model flexibility** | Works with any OpenAI-compatible VLM (local, HuggingFace, or cloud) | Quality is entirely dependent on VLM's ability to output accurate bounding box coordinates; coordinate drift directly causes task failure |
| **Action parsing** | Human-readable text format enables model understanding; regex is simple and debuggable | Regex-based parsing is fragile against malformed or novel model output; ARP format is a custom protocol, not a standard |
| **Architecture** | Clean Operator abstraction makes it trivial to add new execution targets (desktop, browser, mobile, game) | The `GUIAgent.run()` is a single synchronous loop -- no parallel execution, no sub-tasks, no branching |
| **Browser agent** | Two approaches: visual-only (UI-TARS) and hybrid visual+DOM (Agent TARS browser-use) | Visual-only approach doesn't scale to complex multi-page apps; DOM approach requires Playwright compatibility |
| **MCP integration** | Agent TARS kernel is MCP-native; any MCP server is a plugin | Increases complexity; the kernel itself depends on external server processes |
| **Deployment** | CLI available via `npx`; Desktop via Homebrew/installer | VLM model must be self-deployed (HuggingFace endpoint or VolcEngine); free remote operator discontinued Aug 2025 |
| **State management** | Delta event streaming keeps bandwidth low; full history reconstructable from events | Consumers must assemble the full conversation from deltas; no built-in persistence layer |
| **Community** | Well-documented; RFCs; multiple install channels; active changelog | Updates to Agent TARS outpacing UI-TARS Desktop; two co-evolving product lines may confuse users |

**Known limitations from documentation and issues:**
- "UI-TARS-desktop is currently only available for single monitor setup. Multi-monitor configuration may cause failure for some tasks." (from docs/quick-start.md)
- Remote Operator service discontinued on August 20, 2025
- Action parser uses `console.error` inside parsing code (production-unfriendly)
- Max 25-loop default means complex multi-step tasks may terminate prematurely
- No built-in caching for repeated VLM queries; every screenshot triggers a full inference
- The `multimodal/` directory contains what appears to be an older, separate version of packages, creating duplication with `packages/`

## 5. Design Rationale

1. **Visual grounding over structural access**: By using pure pixel-based understanding (screenshots + coordinate actions), UI-TARS works on *any* GUI -- desktop apps, web browsers, mobile screens, games, terminals. This is the core philosophical choice: universal access through vision rather than platform-specific structural APIs (DOM, Accessibility Tree, etc.).

2. **Separation of model + agent + operator**: The three-tier architecture (VLM model -> GUIAgent loop -> Operator execution) allows independent evolution. A better VLM improves accuracy without changing the loop. A new operator adds a target platform without changing the model interface. This is clean, extensible, and testable.

3. **MCP as universal tool protocol**: Agent TARS commits to the Model Context Protocol as its tool interface rather than building a custom one. This means any MCP server (browser, filesystem, search, commands, etc.) is immediately available as an agent tool, and the kernel doesn't need to know about individual tools.

4. **Delta event streaming for context engineering**: Rather than passing full conversation state, the agent emits only new turns as delta events. This enables the Agent UI to render incrementally, supports streaming, and keeps bandwidth proportional to conversation length. The Agent TARS event stream is protocol-driven, enabling "context engineering" where different renderers can be composed for different tool outputs.

5. **OpenAI-compatible API as lingua franca**: By using the OpenAI SDK interface, the system works with any VLM provider (local, HuggingFace, VolcEngine, Anthropic) without provider-specific code. The `useResponsesApi` flag adds optional support for OpenAI's Responses API with incremental message passing.

## 6. Transfer to Lyra

**Transferable idea**: The **Operator abstraction pattern** from `@ui-tars/sdk`.

Lyra should define an `Operator` interface (mirroring `sdk/src/types.ts`):

```typescript
interface Operator {
  screenshot(): Promise<ScreenshotOutput>;   // capture current environment state
  execute(action: ParsedAction): Promise<ExecuteOutput>;  // perform action
}
```

This gives Lyra:
- **Environment-agnostic execution**: The same core agent can run on desktop, browser, mobile, or headless CI by swapping the operator implementation.
- **Type-safe action space**: Each operator declares its supported `ACTION_SPACES`, making the action space self-documenting and verifiable.
- **Simple test/fixture operators**: A mock operator can be used for testing (return fake screenshots, verify executed actions), enabling Lyra's agent logic to be tested without real environments.

**Workstream route**: This maps cleanly to **section 4.2 (Agent-Tool Interface)** in Lyra's architecture -- the boundary between Lyra's reasoning engine and the real world. The Operator interface is the contract at that boundary.

**Impact | Effort | Tier**: 4 | 2 | P1

- Impact 4: Enables cross-environment execution (local, CI, cloud, mobile)
- Effort 2: The interface is tiny (~200 lines of TypeScript types and abstract classes), already proven in production
- Tier P1: Foundational enabler that unblocks multiple downstream workstreams

**License**: Apache 2.0 -- fully compatible with Lyra's licensing; code can be adapted or directly referenced.

**Key files to reference**:
- `/packages/ui-tars/sdk/src/types.ts` -- Operator and Model abstract class definitions
- `/packages/ui-tars/sdk/src/GUIAgent.ts` -- Core agent loop
- `/packages/ui-tars/action-parser/src/actionParser.ts` -- Action parsing from model output
- `/packages/ui-tars/operators/nut-js/src/index.ts` -- Reference operator implementation
- `/packages/ui-tars/operators/browser-operator/src/browser-operator.ts` -- Browser operator
