# memodb-io/Acontext -- Deep-Read

## 1. Headline Feature & Mechanism

**Agent Skills as a Memory Layer.** Acontext automatically captures learnings from AI agent runs and stores them as editable Markdown skill files. The core loop: session messages -- task detection -- LLM-based distillation -- skill agent writes/updates Markdown files.

The mechanism is a two-phase pipeline running asynchronously via RabbitMQ:

- **Phase 1 -- Distillation** (fast, single LLM call). Raw messages for a completed task are packed together, and an LLM analyzes them. For successful tasks it extracts approach, key_decisions, generalizable_pattern (or factual content for knowledge-gathering). For failures it extracts failure_point, flawed_reasoning, prevention_principle. Trivial tasks are skipped. This produces a `SkillLearnDistilled` payload.

- **Phase 2 -- Skill Agent** (multi-turn LLM agent with tool use, holds a Redis lock). A specialized LLM agent receives the distilled context plus the current skill inventory. It uses tools: `get_skill`, `get_skill_file`, `create_skill`, `create_skill_file`, `str_replace_skill_file`, `mv_skill_file`, `delete_skill_file`. The agent decides whether to update an existing skill or create a new one, enforcing domain-level naming (never narrow single-purpose skills). The lock serializes concurrent learning for the same learning space; excess contexts are queued in Redis and drained when the current agent finishes.

The result: skills are real Markdown files with YAML front matter. The SKILL.md defines the schema. Data files contain entries in structured formats (SOP entries with Principle/When-to-Apply/Steps, Warning entries with Symptom/Root-Cause/Correct-Approach/Prevention, fact entries).

## 2. Architecture & Core Modules

Acontext is a **polyglot, event-driven three-tier system**:

```
Client Layer (Python SDK + TypeScript SDK + CLI)
        |
        v  REST (JSON API)
Go API Layer (Gin + GORM/PostgreSQL + Redis + RabbitMQ)
        |
        v  RabbitMQ (async message queue)
Python Core Layer (FastAPI + SQLAlchemy/PostgreSQL+pgvector + Redis + S3)
        |
        v
Infrastructure: PostgreSQL, Redis, RabbitMQ, S3
```

**Go API** (`src/server/api/go/cmd/server/main.go`):
- Entry point. Builds dependency injection container via `samber/do`.
- Gin router with handlers for: sessions, disks, artifacts, tasks, agent skills, users, sandboxes, learning spaces, session events, projects, materials.
- Exposes REST API at `/api/v1` with Swagger docs.
- Has Redis-buffered asset reference writer for S3.
- OpenTelemetry tracing wired into GORM and Redis.
- Tokenizer (tiktoken-go) for context-window accounting.

**Python Core** (`src/server/core/api.py`):
- FastAPI app with `/health`, session router, sandbox router.
- Lifespan: setup() initializes DB, Redis, S3, MQ, sandbox, then starts MQ consumer.
- DI via explicit init functions, no framework.
- Consumer-driven: `process_skill_distillation` and `process_skill_agent` registered via decorators on RabbitMQ exchanges.

**Key sub-modules in Core**:

| Module | Path | Purpose |
|---|---|---|
| `di.py` | `acontext_core/di.py` | Bootstrap: init DB, Redis, S3, MQ, sandbox |
| `service/skill_learner.py` | `acontext_core/service/skill_learner.py` | MQ consumers: distillation entry + skill agent entry |
| `service/controller/skill_learner.py` | `acontext_core/service/controller/skill_learner.py` | Orchestrates: fetch task/messages, call LLM, then call skill agent |
| `llm/prompt/skill_distillation.py` | `acontext_core/llm/prompt/skill_distillation.py` | System prompts for distillation LLM (success, failure, factual modes) |
| `llm/prompt/skill_learner.py` | `acontext_core/llm/prompt/skill_learner.py` | System prompt for the skill-writing agent (tool use, entry formats, rules) |
| `llm/agent/skill_learner.py` | `acontext_core/llm/agent/skill_learner.py` | Skill agent loop: LLM call -> tool execution -> context injection |
| `llm/tool/skill_learner_lib/` | Various | Individual skill editor tools (create_skill, create_skill_file, get_skill, get_skill_file, str_replace, mv, delete) |
| `schema/orm/` | `acontext_core/schema/orm/` | SQLAlchemy dataclass ORM models (session, task, message, skill, learning space, disk, etc.) |
| `infra/` | `acontext_core/infra/` | DB client, Redis, S3, async MQ, sandbox backends (E2B, Novita, Cloudflare, AWS AgentCore) |

**Client SDKs**:
- Python (`acontext` on PyPI): httpx-based, sync + async clients. Resources: sessions, disks, sandboxes, learning spaces, skills, users, project.
- TypeScript (`@acontext/acontext` on npm): zod-based, compile-to-JS.
- CLI (`acontext-cli`): Go-based CLI for self-hosting (`acontext server up`), template creation.

**SDK Language**: Python 3.10+, TypeScript, Go (CLI)
**Core Language**: Python 3.11+ (FastAPI)
**API Language**: Go 1.22 (Gin, GORM)

## 3. Performance/Benchmarks

The repo contains **no explicit benchmark files or published performance numbers**. The CI pipeline runs unit/integration/e2e tests but no latency or throughput benchmarks. Design choices relevant to performance:

- **Distillation is non-blocking** -- runs asynchronously via MQ after task completion, agent never waits.
- **Skill agent has a configurable timeout** (`skill_learn_agent_consumer_timeout`) and max iterations (default 5), with lock renewal during long runs.
- **Redis lock serializes per learning space** -- prevents concurrent skill edits on the same space.
- **Configurable LLM model** -- defaults to `gpt-4.1` for the server, but client SDKs support any OpenAI/Anthropic-compatible model.
- **Core dependencies** include pgvector (for possible semantic search), but current retrieval design is tool-based (progressive disclosure), not embedding-based.

## 4. Trade-offs

| Choice | Win | Lose |
|---|---|---|
| **Skills as plain Markdown files** | Git-able, grep-able, mountable, inspectable. No vendor lock-in. | No vector search, must parse files. Larger context for agent to read. |
| **LLM-based distillation** | High-quality, contextualized learning. Can distinguish procedures from facts from failures. | Costly per-task (extra LLM call + agent loop). Latency: learning happens async minutes later. |
| **Progressive disclosure retrieval** | Agent in the loop. Uses reasoning to pick relevant skills. | No retrieval guarantees. Skills could be missed if agent does not use correct tools. |
| **Two-phase pipeline (distill then agent)** | Separation of concerns. Quick distillation rejects trivial content before expensive agent loop. | Higher infra complexity (two MQ exchanges, Redis lock, Redis pending queue). |
| **Full polyglot stack** | Each service uses the best tool (Go for API performance, Python for AI work). | Higher ops burden: Docker Compose needs PostgreSQL, Redis, RabbitMQ, S3 (or minio). |
| **Redis lock + pending queue** | Concurrent-safe skill updates. | One learning space can have only one active agent run. Queueing adds lag. |
| **Self-hosted or cloud** | Developer choice. Cloud version handles infra. | Self-hosted setup requires significant infrastructure (Docker, several services). |
| **Encrypted context storage** | User KEK support for encrypting data in S3. | Key management overhead. Hard-fail on invalid KEK. Only in commercial version. |

## 5. Design Rationale

The core philosophy is **"Skill is All You Need"** (from the README and AGENTS.md). The team explicitly rejected opaque memory architectures:

- **Against vector embeddings**: "No embeddings, no API lock-in." Memory should be human-readable and cross-framework. You can grep it, mount it in a sandbox, or `cat` it.
- **Against black-box persistence**: "Agent memory is getting increasingly complicated -- hard to understand, hard to debug, and hard for users to inspect or correct." Skills-as-files makes memory transparent.
- **Progressive disclosure over search**: The agent decides what it needs via tool use, not a vector top-k. This puts reasoning in the loop rather than hoping embeddings capture relevance.
- **Skill = Memory, Memory = Skill**: Whether a skill was downloaded from Clawhub or auto-generated, it follows the same format. No distinction between "installed knowledge" and "learned experience."
- **You design the structure**: The SKILL.md schema is user-defined. This means the memory system adapts to the domain, not the other way around.
- **The Skill Agent is prompted to prefer fewer, richer skills** -- "Never create narrow, single-purpose skills." Forces generalization and consolidation.

The MQ-driven architecture decouples API from Core. The Go API handles CRUD and authentication; the Python Core handles AI workload. This is a deliberate split for scaling AI workers independently from the API.

## 6. Transfer to Lyra

**The single most transferable idea is the automatic distillation + skill-writing agent pipeline as a memory layer for Lyra's agents.**

Lyra currently has no automatic mechanism to capture learnings from agent runs and persist them as structured, reusable knowledge. The Acontext pattern maps directly to Lyra's architecture:

- Lyra's session/run data feeds into a distillation step (single LLM call) that produces structured learnings.
- A skill agent (the same Lyra agent system) receives distilled learnings and writes to skill files.
- Skills are organized under "learning spaces" (analogous to Lyra projects).
- The Redis lock + pending queue pattern serializes writes safely.
- Skills as Markdown files means they are immediately usable in Lyra's prompt construction without any embedding pipeline.

**Concrete route:**

Route through **Section 4.x (Memory & Learning)** -- specifically the `04-memory` and `02-memory` workstreams already established in the Lyra plans. The Acontext mechanism directly addresses the gap identified in the memory architecture debate: "how do agents learn from past runs without opaque embeddings."

**Alternative route**: Section 3.x (Agent Runtime) -- the distillation pipeline integrates with Lyra's task completion hooks.

**Impact/Effort/Tier**: High impact (8), Medium effort (5), Tier 1. Automatic learning from runs is a force multiplier. Effort is moderate because the architecture already exists in the codebase to reference -- it is a matter of adapting the pipeline, not inventing it. The LLM calls are already part of any Lyra run; distillation reuses them.

**LICENSE compatibility**: Apache 2.0. Fully compatible with Lyra's licensing (MIT or Apache). Can reference and adapt freely.

**Key files to read for implementation**:
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/memodb-io__Acontext/src/server/core/acontext_core/service/skill_learner.py` -- the consumer-based pipeline
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/memodb-io__Acontext/src/server/core/acontext_core/service/controller/skill_learner.py` -- the orchestration logic
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/memodb-io__Acontext/src/server/core/acontext_core/llm/prompt/skill_distillation.py` -- the distillation prompts
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/memodb-io__Acontext/src/server/core/acontext_core/llm/prompt/skill_learner.py` -- the skill agent prompts
- `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/memodb-io__Acontext/src/server/core/acontext_core/llm/agent/skill_learner.py` -- the agent loop
