# modelcontextprotocol/modelcontextprotocol -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**Headline Feature**: The Model Context Protocol (MCP) specification -- an open standard defining how LLM-based applications (hosts) interact with external tools, data sources, and prompts via a uniform, transport-agnostic JSON-RPC 2.0 protocol. This is the canonical specification repository, not an SDK implementation.

**How it really works**: The protocol is defined in TypeScript as the source of truth (`schema/<version>/schema.ts`) and mechanically transcribed into JSON Schema (`schema.json`), JSON examples, and Mintlify-MDX documentation. The TypeScript definitions encode every wire message shape -- requests, notifications, responses, error codes, capability declarations, content types -- through union types and interfaces. A generate-schema script (`scripts/generate-schemas.ts`) using TypeScript-JSON-Schema and TypeDoc emits the JSON Schema and human-readable docs from the TS source, and a validation script (`scripts/validate-examples.ts`) checks that example JSON files conform to their declared schema. The entire protocol evolves through Standards Enhancement Proposals (SEPs) living in `seps/`, each a markdown document with a formal template (`seps/TEMPLATE.md`). There is zero runtime code in this repo; its function is normative specification production and curation.

**Wire-level mechanism**: All MCP messages are JSON-RPC 2.0 envelopes. The latest released version (`2025-11-25`) uses an `initialize` handshake for capability/version negotiation; the draft version (`LATEST_PROTOCOL_VERSION = "2026-07-28"`) eliminates the `initialize` handshake entirely and carries capabilities per-request via a structured `_meta` field (`RequestMetaObject`), making the protocol stateless and sessionless. Features like Tools, Resources, and Prompts are listable, callable, and paginated via opaque cursor tokens. The draft introduces `CacheableResult` (with `ttlMs` + `cacheScope`) on list/read results for client-side caching, a `subscriptions/listen` mechanism to replace per-resource subscribe/unsubscribe, and the Multi Round-Trip Request (MRTR) pattern where servers embed required client inputs (elicitation, sampling) inside the response itself rather than opening a separate SSE stream, enabling stateless load-balanced deployments.

## 2. Architecture & Core Modules (entry points, data flow, patterns)

**Repository structure** (not application architecture -- this is a spec):

| Path | Role |
|------|------|
| `schema/<version>/schema.ts` | Canonical type definitions (entry point for all generated artifacts) |
| `schema/<version>/schema.json` | Generated JSON Schema (for code-gen in non-TS stacks) |
| `schema/<version>/examples/<TypeName>/` | Validated example JSON files, linked via `@includeCode` JSDoc |
| `schema/draft/schema.ts` | In-progress next-version definitions |
| `scripts/generate-schemas.ts` | TypeScript-to-JSON-Schema + MDX generation |
| `scripts/validate-examples.ts` | Validates examples against their declared type |
| `scripts/render-seps.ts` | Renders SEP markdown into docs site |
| `seps/` | ~40 Standards Enhancement Proposals, each a self-contained design doc |
| `docs/specification/<version>/` | Generated specification pages (Mintlify MDX) |
| `docs/docs/` | Tutorials, guides, best-practices |
| `tools/sep-automation/` | Vitest-based TypeScript project for SEP automation workflows |
| `plugins/mcp-spec/skills/` | Claude agent skills: `draft-sep`, `search-mcp-github` |

**Data flow**: TypeScript interfaces in `schema.ts` are the single source of truth. The npm script `generate:schema` runs `tsx scripts/generate-schemas.ts` (emits JSON Schema + MDX) in parallel with a Typedoc pass (emits structured schema reference pages). The `check:schema` pipeline validates the TS compiles (`tsc --noEmit`), the generated JSON matches, all examples validate, and the rendered MDX matches. This CI-enforced pipeline ensures the specification is always internally consistent.

**Architecture pattern** (protocol level):
- **Message framing**: JSON-RPC 2.0 with typed union messages (`JSONRPCRequest | JSONRPCNotification | JSONRPCResponse`)
- **Capability negotiation**: Per-request via `_meta.io.modelcontextprotocol/clientCapabilities` in draft; via `initialize` handshake in 2025-11-25
- **Transport abstraction**: The spec is transport-agnostic; normative transports are stdio and Streamable HTTP; legacy HTTP+SSE is deprecated
- **Server primitives**: Tools (callable functions), Resources (readable data), Prompts (templated text), Completion (argument autocomplete)
- **Server-initiated requests**: Sampling (server asks client to call LLM -- deprecated), Elicitation (server asks client for user input), Roots (server asks for filesystem scope -- deprecated)
- **Task augmentation** (2025-11-25 only): A `TaskAugmentedRequestParams` system allowing call-now/fetch-later for tools, via `tasks/` methods
- **MRTR** (draft only): Server returns `InputRequiredResult` with embedded requests + `requestState` instead of opening SSE back-channel
- **Extensions framework** (SEP-2133): Optional capabilities via `{vendor-prefix}/{extension-name}` identifiers in `ServerCapabilities.extensions` / `ClientCapabilities.extensions`

## 3. Performance/Benchmarks (real numbers from the repo)

This repository does not contain any benchmarks. It is a specification-only repository. There is no runtime, no client, no server implementation to measure. The SEPs reference design goals relating to performance (e.g., SEP-2322 MRTR reducing operational complexity and eliminating SSE connection overhead for horizontal scaling; SEP-2549 introducing TTL caching to reduce redundant `resources/list` / `tools/list` fetches; SEP-2567 removing sessions so list endpoints become cacheable across conversation boundaries), but no empirical numbers are provided.

**Qualitative performance design targets (from SEPs)**:
- MRTR eliminates need for stateful SSE connections, enabling standard HTTP load balancers (L7 routing) for MCP server farms
- Cacheable list results (SEP-2549) allow HTTP caching proxies to serve `tools/list` and `resources/list` without hitting the origin server
- Sessionless design (SEP-2567) means zero session-rehydration overhead on server restart or scale-out
- HTTP header mirroring (`Mcp-Method`, `Mcp-Name` in SEP-2243) allows load balancers to route on HTTP headers alone, avoiding JSON body parsing

## 4. Trade-offs (wins vs loses -- from issues, design decisions, complexity)

**Wins**:
1. **Transport-agnostic core**: Any transport can carry JSON-RPC messages -- stdio, HTTP, WebSocket, message queues. The protocol layer does not mandate a transport.
2. **Extensible by design**: The `extensions` capability map (SEP-2133) and `_meta` key-name reservation system let anyone add protocol features without forking. Official extensions live in `ext-*` repos with their own maintainers.
3. **Stateless (draft)**: Removing sessions and per-connection state dramatically simplifies server deployment. A tool server can be stateless behind a standard HTTP load balancer.
4. **Cache-aware design (draft)**: `CacheableResult` with `ttlMs` and `cacheScope` is a first-class protocol concern, enabling HTTP-style caching semantics at the MCP message level.
5. **MRTR replaces SSE complexity (draft)**: Servers no longer need long-lived SSE connections to request intermediate input from the client. The input requests are bundled into the response body.
6. **Versioned per-date, not semver**: Date-based versioning (`2025-11-25`, `2026-07-28`) makes it obvious which specification generation a message conforms to, and the draft pipeline is clear.

**Loses / Costs**:
1. **Breaking changes in draft**: The 2026-07-28 draft is intentionally breaking -- it removes `initialize`, sessions, list-subscribe, logging/setLevel, and sampling. Any server implementing the 2025-11-25 spec must be substantially rewritten for 2026-07-28.
2. **Content blocks (arrays vs single)**: Earlier versions allowed a single `ContentBlock` where draft requires arrays. This breaks backward compatibility for tool call results and prompt messages.
3. **Response envelope change**: `JSONRPCResultResponse` now wraps `Result | InputRequiredResult` everywhere. Clients must handle two possible shapes for every server response.
4. **Deprecated feature burden**: Roots, Sampling, and Logging are deprecated but remain in the spec for 12+ months. Implementors must carry dead code during migration.
5. **No standardized discovery**: While `server/discover` exists in draft, there is no registry, no well-known endpoint pattern, and no authentication standard baked into the core protocol (auth lives in a separate `ext-auth` repo).
6. **Spec-first, not implementation-first**: The schema is abstract TypeScript. Every detail of wire format is in JSDoc comments, not enforced by code. Two SDK implementations could disagree on interpretation.

## 5. Design Rationale (why this approach)

**"Small core, extensions carry the weight"**: The MCP specification is deliberately minimal. Core primitives (Tools, Resources, Prompts) are kept small; everything else is an extension. SEP-2133 formalizes this: extensions can be official (`io.modelcontextprotocol/`), experimental, or external. This prevents spec bloat and allows the ecosystem to evolve faster than the core.

**"Sessions were a mistake"**: SEP-2567 argues that session semantics were never consistently defined across MCP clients (per-tool-call, per-app-launch, per-page-load), making the abstraction unreliable. The replacement -- explicit state handles returned as tool outputs -- is simpler and more aligned with RESTful design. This is a direct lesson from early deployment experience.

**"JSON-RPC 2.0 because it is universally understood"**: Rather than inventing a new wire format, MCP builds on JSON-RPC 2.0 which every language ecosystem can already handle. The additional structure is layered on top via strongly-typed `method` strings and interface inheritance.

**"Server-initiated requests need a stateless pattern"**: MRTR (SEP-2322) directly addresses the problem that SSE-based server-initiated requests prevent stateless, horizontally-scaled server deployments. By embedding the required client inputs (elicitation forms, sampling requests) inside the response to the original request, the protocol works through standard load balancers without affinity or sticky sessions.

**"Deprecate features with low adoption"**: SEP-2577 (deprecating Roots, Sampling, Logging) is pragmatic protocol hygiene. Despite being in the spec since 2024, these features have near-zero adoption in the ecosystem. Keeping them imposes mental and implementation overhead on every client and server implementor. The deprecation gives a 12-month migration window.

## 6. Transfer to Lyra (one idea + workstream route)

**Idea**: **Protocol-specified query caching with TTL + scope (CacheableResult)**. The MCP draft 2026-07-28 adds `ttlMs` and `cacheScope` to list and read results. Lyra agent orchestration could adopt the same pattern for its introspection endpoints (e.g., `/agents/list`, `/plugins/list`, `/workflows/list`): instead of forcing every agent handoff to re-fetch the same inventory, responses carry a cache hint. This is analogous to HTTP `Cache-Control: max-age=3600, private`, but embedded in the protocol message itself so the receiving agent (or its runtime) can cache proactively without a separate cache layer.

**Workstream route**: This maps to Lyra's **Section 4.3 (Agent Messaging/Protocol Layer)**. The agent communication protocol currently lacks cache metadata on list-type responses. Adding a `cache_hint` envelope to outbound messages -- with `ttl_ms` and `scope` (e.g., `"agent_session"`, `"orchestrator_wide"`, `"public"`) -- would reduce redundant introspection calls during multi-hop agent chains without requiring an external cache proxy.

**Impact**: 3 (Medium) -- reduces latency in agent handoff chains; prevents N+1 refetch patterns where the same agent/plugin list is queried at each orchestration hop.

**Effort**: 2 (Low) -- purely a protocol definition change to Lyra's message schema; no infrastructure dependency.

**Tier**: P2 (Enhancement) -- addresses an optimization, not a correctness issue.

**LICENSE**: Apache 2.0 / MIT transition (spec); CC-BY-4.0 (docs). Compatible with Lyra's license (MIT).
