# THUDM/AgentBench -- Deep-Read

**Repo**: https://github.com/THUDM/AgentBench
**Local path**: /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/THUDM__AgentBench
**License**: Apache 2.0
**Language**: Python
**Paper**: arXiv 2308.03688 (NeurIPS 2023)

---

## 1. Headline Feature & Mechanism

AgentBench is the first comprehensive benchmark designed to evaluate LLMs as autonomous agents across a diverse spectrum of 8 distinct environments. It was the first benchmark to systematically test frontier LLMs (GPT-4, Claude, Llama 2, etc.) on multi-turn, interactive agent tasks -- not just static Q&A.

**The 8 tasks are:**

| Task | Abbr. | Nature | Metric |
|------|-------|--------|--------|
| Operating System | OS | Bash commands in real Docker containers | Accuracy |
| Database | DB | Execute SQL against MySQL | Category accuracy |
| Knowledge Graph | KG | SPARQL queries over Freebase | Answer F1 |
| Digital Card Game | DCG | Turn-based strategy (Aquawar) | Win rate |
| Lateral Thinking Puzzles | LTP | Yes/no deduction game | Game progress |
| House-Holding (ALFWorld) | HH | Text-based embodied home tasks | Success rate |
| Web Shopping (WebShop) | WS | Simulated e-commerce | Reward |
| Web Browsing (Mind2Web) | WB | Real website interaction | Step SR |

**How the code really works -- the evaluation loop:**

The evaluation has three decoupled layers that communicate over HTTP:

1. **Task Server** (Dockerized): Each task runs in its own Docker container. A Task Controller accepts connections from Task Workers and routes sample requests. When a sample starts, the worker creates an environment (e.g., boots a MySQL database or a bash shell), presents the initial prompt to the agent, and waits.

2. **Agent Client**: A thin wrapper over an LLM API (OpenAI, Claude, or local via FastChat). The core interface is a single method: `inference(history: List[dict]) -> str`. The agent receives the conversation history and returns the next action text.

3. **Assigner** (`src/assigner.py`): The orchestration engine. It reads a YAML config describing which agents to run on which tasks with what concurrency limits. It then:
   - Builds a bipartite graph: source -> agents -> tasks -> sink
   - Edge capacities = remaining samples and concurrency limits
   - Runs a **max-flow algorithm** (Edmonds-Karp via BFS) to find the optimal assignment at each allocation cycle
   - Spawns worker threads that run the interaction loop:
     ```
     TaskClient.run_sample(index, agent):
       result = controller.start_sample(index)
       while result.status == RUNNING:
         agent_response = agent.inference(result.history)
         result = controller.interact(session_id, agent_response)
       return result
     ```
   - Records every sample result as JSONL and computes overall metrics upon completion

The repo's primary branch now uses a **Function Calling (FC)** prompt format and containers via Docker Compose, integrated with the AgentRL framework. The older v0.1 and v0.2 branches used a different interaction format.

---

## 2. Architecture & Core Modules

### Top-level structure:

```
AgentBench/
  configs/            YAML-driven configuration system
    agents/           LLM provider configs (OpenAI, Claude, FastChat)
    assignments/      Eval run configs (what agent x task, concurrency)
    tasks/            Task environment configs (tools, docker, data paths)
  src/
    assigner.py       *** CORE: Max-flow scheduler + evaluation loop
    analysis.py       *** CORE: Result aggregation, leaderboard CSV generation
    configs.py        YAML/JSON config loader with import/merge/overwrite
    client/
      agent.py         Abstract base class: AgentClient.inference(history)
      task.py          TaskClient.run_sample() -- the agent-task interaction loop
      agents/
        http_agent.py     HTTPAgent -- wraps any REST API (OpenAI, etc.)
        claude_agent.py   ClaudeAgent -- uses anthropic Python SDK
        fastchat_client.py FastChatClient -- local model serving
        test_agent.py     EchoAgent for testing
    server/
      tasks/            One subdirectory per task environment
        os_interaction/  Docker-based bash environment
        dbbench/         MySQL/SQLite interaction
        knowledgegraph/  SPARQL over Freebase
        alfworld/        Text-based home simulator
        webshop/         Online shopping simulation
    typings/          Pydantic models (configs, outputs, status enums, requests)
    utils/
      max_flow.py       Graph + Edmonds-Karp max-flow implementation
      rules.py          Composable rule engine (And/Or/Not/Contain)
      others.py         JSON encoder, color printer, serializer
  data/              Task-specific data files (problems, scripts, configs)
  extra/
    docker-compose.yml  FC version -- one-service-per-task orchestration
  scripts/
    validate_lite_configs.py
```

### Data flow:

```
                  +-------------+
                  |  Assigner   | (src/assigner.py)
                  |  (max-flow  |
                  |   scheduler)|
                  +------+------+
                         |
          +--------------+--------------+
          |                             |
    +-----v------+               +------v-----+
    | AgentClient |               | TaskClient |
    | (LLM API)   |               | (HTTP to   |
    |             |               | Controller)|
    +-----+------+               +------+-----+
          |                             |
    +-----v------+               +------v-----+
    | Agent API  |               | Task       |
    | (OpenAI /  |               | Controller |
    |  Claude /  |               | (FastAPI)  |
    |  FastChat) |               +------+-----+
    +------------+                      |
                                  +-----v------+
                                  | TaskWorker  |
                                  | (Docker     |
                                  |  container) |
                                  +-------------+
```

### Key architectural patterns:

- **Config-driven object creation**: `InstanceFactory` (Pydantic model in `src/typings/general.py`) uses `__import__` and `getattr` to dynamically instantiate classes from dotted module paths specified in YAML. No registration needed.
- **Config inheritance**: The `ConfigLoader` supports `import`, `default`, and `overwrite` directives in YAML, enabling layered config composition.
- **Thread-based concurrency**: Worker threads (not async in v0.2; the FC version uses asyncio via AgentRL) with thread-safe locking (`self.assignment_lock`).
- **Resume capability**: The Assigner checks the output directory for existing `runs.jsonl` files on startup and skips already-completed samples.
- **Docker isolation**: Each task environment runs in its own Docker container; the `os_interaction` task even creates containers dynamically per sample via Docker-in-Docker.
- **Function calling protocol**: The FC version defines tool schemas in YAML configs (e.g., `bash_action`, `execute_sql`, `commit_final_answer`) which are injected into the LLM prompt.

---

## 3. Performance / Benchmarks

The paper reports results for 25 LLMs across the 8 tasks. Key findings:

- **GPT-4** was the top performer across most tasks, but still showed large gaps vs. practical usability.
- **Claude models** (claude-v1.3, claude-instant) performed competitively on OS, DB, and KG tasks but weaker on game-based tasks.
- **Open-source models** (Llama 2, Vicuna, ChatGLM, etc.) trailed significantly, especially on multi-step reasoning tasks like OS and DB.
- **Task difficulty ranking** (approximate, from overall scores):
  - Easiest: LTP (lateral thinking puzzles), WS (webshop)
  - Medium: HH (ALFWorld), KG
  - Hardest: OS, DB, DCG, WB (Mind2Web)
- **Resource consumption** (from README):
  - WebShop: ~15GB RAM per worker, ~3min startup
  - Mind2Web: ~1GB RAM, ~5min startup
  - All others: <500MB RAM, 5-20s startup
- **Known instability**: KG Freebase external SPARQL service is unreliable. ALFWorld memory/disk leaks over time.

The README references a live leaderboard (Google Sheets) for up-to-date scores. The FC version adds its own leaderboard image (`assets/fc_leaderboard.png`).

---

## 4. Trade-offs (Wins vs Losses)

### Wins:

1. **Comprehensive coverage**: 8 diverse task types covering OS, DB, web, games, knowledge retrieval, embodied reasoning -- far broader than any single-task LLM benchmark.
2. **Clean decoupling**: Three-layer architecture (agent, task, assigner) means you can swap any component independently.
3. **Config-driven**: Adding a new task or agent requires only a YAML config and implementing the `Task` interface -- no framework modifications.
4. **Reproducible Docker environments**: Containers ensure tasks produce identical conditions across evaluation runs.
5. **Max-flow scheduling**: Optimal use of limited concurrent resources, with automatic resume on failure.
6. **Function Calling standardization (FC version)**: Defines a universal tool-use protocol that works across OpenAI, Claude, and other function-calling models.

### Losses / Known Issues:

1. **Heavy Docker dependency**: All tasks require Docker, which is a significant barrier for casual use. The KG task additionally requires a multi-GB Freebase database setup.
2. **Resource bloat**: WebShop at ~15GB RAM is prohibitive for many testers. The ACKnowledgment in README says "make sure your machine has sufficient resources."
3. **Python/package pinning**: `numpy~=1.23.5`, `FastAPI~=0.101.1`, `aiohttp~=3.8.4` -- all dated. Requires Python 3.9 for clean install. This is acknowledged in README.
4. **Memory leaks**: "the current implementation of alfworld leaks memory and disk space until the task worker is restarted" (direct quote from README WARNING).
5. **Dual version complexity**: The main branch now uses AgentRL and Function Calling (FC), but older v0.1/v0.2 exist as separate branches. Users must pick the right version.
6. **Threading vs async mismatch**: The v0.2 Assigner uses threading (GIL-bound), while the FC version uses asyncio via AgentRL. Not all tasks support both modes.
7. **No unit tests**: The repo has no `tests/` directory. The only validation script is `scripts/validate_lite_configs.py`.
8. **External service dependency**: KG task relies on a public SPARQL endpoint that is "not stable" per the README.
9. **OS port conflicts**: Mac users need to free port 5000 for the task controller.

---

## 5. Design Rationale

The design decisions documented in `docs/Introduction_en.md` and the code itself reveal clear reasoning:

1. **Decoupling was essential because of resource heterogeneity**: "The varied system resource and environment requirements of different tasks [make] a unified design challenging." (Introduction_en.md) WebShop at 15GB and LTP at <500MB cannot share the same deployment model.

2. **Max-flow scheduling over simpler alternatives**: The Assigner treats the evaluation as a bipartite graph flow problem rather than a simple FIFO queue. This ensures optimal utilization of concurrent agent API keys and task worker capacity simultaneously -- neither resource sits idle while the other is saturated.

3. **Docker over native execution**: Containers provide both isolation (no cross-task interference) and reproducibility (identical OS, tools, and data across runs). The OS task, for example, boots real Ubuntu containers and executes actual bash commands.

4. **YAML over code configuration**: The `ConfigLoader` with import/merge/overwrite semantics was built to support compositional configs without Python imports. A new task can be defined purely in YAML.

5. **Function Calling as the interaction protocol**: The FC version standardizes how agents communicate with environments. Instead of prompting the model to output raw text in a specific format, tool schemas are registered with the LLM via its native function-calling API, which is more reliable and parseable.

6. **Thread-based workers over async (v0.2)**: The original design used threading because individual task evaluation is I/O bound (waiting for HTTP responses from LLM APIs and task controllers). Threading avoids the complexity of async orchestration. The FC version later adopted asyncio via AgentRL.

---

## 6. Transfer to Lyra

### The single most transferable idea: **Max-flow concurrent task scheduling**

The `Assigner` class in `src/assigner.py` implements a clean, general-purpose scheduling algorithm that could directly improve Lyra's ability to run multiple LLM agents across multiple evaluation/benchmark tasks concurrently. The key mechanism:

- Build a bipartite graph: SRC -> agents -> tasks -> DST
- Edge capacities from agent concurrency limits (API rate limits, GPU memory)
- Edge capacities from task worker capacity (Docker slots, database connections)
- Run max-flow to find the optimal allocation
- Spawn worker threads for each assigned (agent, task, sample_index) triple

This solves a real problem in Lyra: when running multi-agent evaluations, naive round-robin or FIFO scheduling leaves resources idle. The max-flow approach guarantees optimal utilization.

### Workstream route:

This maps to **Section 4.2 (Agent orchestration and routing)** in the Lyra architecture document. The `Assigner` is fundamentally an orchestration router -- given N agents and M tasks, it decides which agent should work on which task at each point in time, respecting capacity constraints.

It could also apply to **Section 4.4 (Evaluation and benchmarking infrastructure)**, where Lyra needs to coordinate benchmark runs across different LLM backends with varying rate limits.

### Impact / Effort / Tier:

- **Impact**: 7/10. This would significantly improve Lyra's concurrent evaluation throughput. Without intelligent scheduling, Lyra will bottleneck on whichever resource (API rate limit or task capacity) is saturated first.
- **Effort**: 4/10. The max-flow algorithm itself is ~400 lines of Python (Edmonds-Karp). Lyra would need to wrap it with its own task definitions and agent abstractions, but the core scheduling logic is ready to port.
- **Tier**: Gold. This is a peer-reviewed, battle-tested algorithm (NeurIPS 2023) used to run thousands of agent-task evaluations across 25+ LLMs.

### LICENSE note:

Apache 2.0 -- fully permissive for both open-source and proprietary use. No copyleft restrictions. Attribution required.

### File references for porting:

- `/repos/THUDM__AgentBench/src/assigner.py` -- The full Assigner class with max-flow scheduling. Lines 41-405.
- `/repos/THUDM__AgentBench/src/utils/max_flow.py` -- Graph and Edmonds-Karp max-flow implementation. Lines 1-98.
- `/repos/THUDM__AgentBench/src/typings/config.py` -- AssignmentConfig and concurrency model. Lines 31-160.
- `/repos/THUDM__AgentBench/src/typings/general.py` -- InstanceFactory for dynamic YAML-driven object creation. Lines 10-35.
- `/repos/THUDM__AgentBench/configs/assignments/default.yaml` -- Example concurrency and assignment config.
