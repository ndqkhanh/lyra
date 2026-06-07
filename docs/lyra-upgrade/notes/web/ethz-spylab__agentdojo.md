# ethz-spylab/agentdojo -- Deep-Read

## 1. Headline Feature & Mechanism (how the code really works)

**AgentDojo** is a dynamic, versioned benchmark for evaluating **prompt injection attacks and defenses** in LLM-based agents that use tool-calling. Unlike static benchmarks that test a single prompt response, AgentDojo runs a full agent execution loop -- the agent receives a user task (e.g., "send the agenda to the team"), can call tools to complete it, and an attack simultaneously tries to hijack the agent via injected text embedded in the tool-output environment.

The core loop works as follows:

1. **Environment injection**: The attack places adversarial text (the "injection") into the agent's environment data (e.g., an email body, a calendar event description, a filename) using Python `str.format()` template substitution against `environment.yaml` and `injection_vectors.yaml`.
2. **Agent execution**: The pipeline (system message -> user query -> LLM -> tool execution loop) runs the agent against the injected environment. The tool execution loop iterates: LLM generates tool calls -> runtime executes them -> results feed back to the LLM, looping until no more tool calls are made (max 15 iterations).
3. **Dual scoring**: Every run produces two booleans:
   - **Utility**: did the agent complete the *user's* legitimate task? (measured by `BaseUserTask.utility()`, often via environment diffing with `DeepDiff`).
   - **Security**: did the agent also execute the *attacker's* injection goal? (measured by `BaseInjectionTask.security()`, checking for traces of the injection in the post-execution environment).
4. **Result aggregation**: Across all (user_task x injection_task) pairs, the benchmark reports average utility, utility-under-attack, and targeted attack success rate (ASR = 1 - avg security).

## 2. Architecture & Core Modules (entry points, data flow, patterns)

```
entry point:
  src/agentdojo/scripts/benchmark.py  (CLI via click)

data flow:
  benchmark.py
    -> AgentPipeline.from_config(PipelineConfig)
    -> benchmark_suite_with_injections()
      -> for each user_task x injection_task:
           attack.attack(user_task, injection_task)  -> returns injected dict[str,str]
           suite.run_task_with_pipeline(pipeline, user_task, injection_task, injections)
             -> suite.load_and_inject_default_environment(injections)  # template substitution
             -> pipeline.query(prompt, runtime, environment)
               -> [SystemMessage, InitQuery, LLM, ToolsExecutionLoop]
                  -> ToolsExecutionLoop: [ToolsExecutor, LLM] up to 15 iters
             -> _check_user_task_utility() AND _check_injection_task_security()
```

### Core Modules

| Module | File(s) | Responsibility |
|---|---|---|
| **Agent Pipeline** | `agent_pipeline/agent_pipeline.py` | `AgentPipeline` -- chains `BasePipelineElement` instances in order |
| **Base Pipeline Element** | `agent_pipeline/base_pipeline_element.py` | Abstract `query()` interface: `(query, runtime, env, messages, extra_args) -> tuple` |
| **Basic Elements** | `agent_pipeline/basic_elements.py` | `SystemMessage` and `InitQuery` -- prepend system/user messages to the message list |
| **LLM Adapters** | `agent_pipeline/llms/` | 7 LLM backends: OpenAI, Anthropic, Cohere, Google, Local, vLLM, PromptingLLM -- wrap provider APIs into pipeline elements |
| **Tool Execution** | `agent_pipeline/tool_execution.py` | `ToolsExecutor` runs function calls from assistant messages; `ToolsExecutionLoop` drives the tool-use loop |
| **PI Detector** | `agent_pipeline/pi_detector.py` | `TransformersBasedPIDetector` using `protectai/deberta-v3-base-prompt-injection-v2` as a defense middleware |
| **Functions Runtime** | `functions_runtime.py` | `FunctionsRuntime` with tool registration, Pydantic argument validation, nested function call support, and a `Depends` dependency injection system |
| **Task Suite** | `task_suite/task_suite.py` | `TaskSuite` manages versioned user/injection tasks, environment loading/injection, and orchestration of pipeline execution |
| **Base Tasks** | `base_tasks.py` | `BaseUserTask` (abstract: PROMPT, ground_truth, utility) and `BaseInjectionTask` (abstract: GOAL, ground_truth, security) |
| **Attacks** | `attacks/base_attacks.py`, `baseline_attacks.py`, `important_instructions_attacks.py`, `dos_attacks.py` | Pluggable attack classes with a registry pattern; `BaseAttack.attack()` returns dict of injection values; baselines include direct, ignore_previous, system_message, injecagent, important_instructions, tool_knowledge, and 4 DOS variants |
| **Benchmark** | `benchmark.py` | Orchestrator: loops over task pairs, handles logging, error recovery (context length exceeded, server errors), result persistence |
| **Task Combinators** | `task_suite/task_combinators.py` | `TaskCombinator` creates combined tasks from two subtasks for multi-step evaluations |
| **Types** | `types.py` | Re-implemented OpenAI-compatible chat message types (TextContentBlock, ThinkingContentBlock, etc.) with custom typed dicts |

### Key Design Patterns

1. **Pipeline Composition**: Every component implements `BasePipelineElement.query()`. Pipelines are chains: `[SystemMessage, InitQuery, LLM, ToolsExecutionLoop]`. This mirrors Lyra's own middleware/pipe architecture and makes it trivial to insert defenses anywhere in the call chain.

2. **Attack/Defense Separation via Registry**: Attacks register themselves via `@register_attack` decorator. Defenses are selected by name and configured at pipeline build time. This makes it possible to evaluate all combinatoric pairs of (model x attack x defense).

3. **Versioned Task Suites**: `TaskSuite._user_tasks` and `_injection_tasks` store `dict[BenchmarkVersion, BaseTask]`, enabling backward-compatible task evolution. `get_version_compatible_items()` resolves the right task version at runtime.

4. **Environment Differencing for Verification**: Utility/security checks are done by comparing `pre_environment` vs `post_environment` using `deepdiff.DeepDiff` with path exclusions (to ignore ephemeral fields like inbox/received drafts). This avoids fragile output-parsing and enables precise state-based verification.

## 3. Performance/Benchmarks (real numbers from the repo)

Data from the published results table (`docs/results-table.html`), benchmark version v1.2.2 across 4 suites (workspace, travel, banking, slack):

### Utility (no attack) -- Top models
| Model | Utility | Utility Under Attack | Targeted ASR |
|---|---|---|---|
| claude-3-7-sonnet-20250219 | **88.66%** | 77.27% | 7.31% |
| claude-3-5-sonnet-20241022 | **79.38%** | 72.50% | 1.11% |
| claude-3-5-sonnet-20240620 | **79.38%** | 51.19% | 33.86% |
| gpt-4o-2024-05-13 | **69.07%** | 50.08% | 47.69% |
| claude-3-opus-20240229 | **68.04%** | 52.46% | 11.29% |
| gpt-4o-mini-2024-07-18 | **68.04%** | 49.92% | 27.19% |
| gemini-2.0-flash-001 | **43.30%** | 39.75% | 20.83% |
| command-r-plus | **24.74%** | 25.12% | 4.45% |

Key observations from the data:
- claude-3-7-sonnet is the best overall: highest utility (88.66%) and near-best security (7.31% ASR).
- claude-3-5-sonnet-20241022 has the **lowest ASR in the entire table** at 1.11%, meaning it almost never falls for important_instructions attacks while maintaining competitive utility.
- The "utility under attack" column shows that attacks meaningfully degrade task performance: even for the best model, utility drops 11 percentage points when attacked.
- ASR varies wildly: claude-3-5-sonnet-20241022 (1.11%) vs gpt-4-0125-preview (56.28%) -- the same attack (important_instructions) has 50x different effectiveness across models.

### Defense effectiveness (gpt-4o-2024-05-13, important_instructions attack)
| Defense | Utility | Utility Under Attack | ASR |
|---|---|---|---|
| None | 69.07% | 50.08% | 47.69% |
| tool_filter | 72.16% | 56.28% | 6.84% |
| repeat_user_prompt | 84.54% | 67.25% | 27.82% |
| transformers_pi_detector | 41.24% | 21.14% | 7.95% |
| spotlighting_with_delimiting | 72.16% | 55.64% | 41.65% |

- **tool_filter** cuts ASR from 47.69% to 6.84% (an 86% reduction) while actually improving utility slightly -- because it removes irrelevant tools, reducing the attack surface and making the model focus.
- **repeat_user_prompt** has the highest utility (84.54%) but only modestly reduces ASR.
- **transformers_pi_detector** nearly eliminates successful attacks (7.95% ASR) but at massive utility cost (41.24%, down from 69.07%).
- **spotlighting_with_delimiting** barely works (41.65% ASR, down from 47.69%) -- the model ignores the delimiters.

## 4. Trade-offs (wins vs loses from issues, design decisions, complexity)

### Wins

1. **Dual-metric scoring (utility + security)** is the defining contribution. Most prior benchmarks measure only one or the other. This reveals the fundamental tension: improving security often hurts utility.

2. **Dynamic environment injection** captures realistic attack vectors. Injections appear in the data the agent reads (emails, filenames, calendar entries), not in the prompt itself. This is the most realistic threat model for tool-using agents.

3. **Version-controlled task evolution** (v1 -> v1.1 -> v1.1.1 -> v1.2 -> v1.2.1 -> v1.2.2) allows the benchmark to grow without breaking backward compatibility. New tasks and refinements coexist with old versions.

4. **Pluggable architecture** makes it easy to add new models (7+ providers), attacks (12 registered), and defenses (4 bundled). The registry pattern for attacks is clean and minimal.

5. **Rich published results** with full runtime traces viewable in the Invariant Explorer, enabling qualitative analysis of attack trajectories, not just aggregate scores.

### Loses / Limitations

1. **Synthetic environments limit ecological validity**. The banking, workspace, slack, and travel suites use simplified mock clients, not real APIs. Real-world prompt injection in production agents may differ significantly.

2. **No multi-step injection chaining**. Each run evaluates exactly one user task paired with one injection task. Real attacks might inject into one tool output that triggers a second injection in the next tool call.

3. **No tool-output provenance tracking**. The agent sees flat text for tool results. There is no mechanism to mark tool outputs as "from tool" vs "from user" to enable origin-based defenses.

4. **The "ground truth pipeline" only checks task solvability, not task diversity**. All tasks must be solvable by deterministic tool call sequences. This excludes tasks requiring open-ended reasoning, negotiation, or creative work.

5. **Defense coverage is limited to 4 defenses**, and tool_filter only works with OpenAI models (hardcoded in `agent_pipeline.py` line 224: `if not isinstance(llm, OpenAILLM): raise ValueError`).

6. **Utility drop under attack is treated as a bug, not a feature**. When an attack degrades utility (e.g., the agent gets confused and fails its original task), the benchmark counts this as a negative. But a confused agent that stops working is arguably more secure than one that blindly follows injection instructions while completing the original task.

7. **No adaptive attacks**. All attacks are static templates. There is no attacker that changes strategy based on observed model behavior.

## 5. Design Rationale (why this approach)

**Why a dynamic environment rather than static prompts?** The ETH SPY Lab team explicitly chose injection-through-tool-outputs because it is the most realistic attack surface for deployed agents. An agent reading a user's email or a shared document encounters attacker-controlled text as part of normal operation. Static prompt-injection benchmarks test a single-turn scenario that does not reflect how agents actually interact with data.

**Why pipeline composition rather than monolithic agents?** The `BasePipelineElement` abstraction allows defenses, LLM calls, and tool execution to be reordered and composed freely. This design mirrors production agent frameworks (LangChain, Anthropic's tool-use loop) and enables fair comparison: the same pipeline structure can run on any supported model with any defense.

**Why environment diffing for verification?** Using `deepdiff.DeepDiff` on the pre/post environment avoids fragile output parsing. It catches side-effect attacks (e.g., "delete a file") that would never appear in the agent's text output. It also enables precise state-based verification: a task is "solved" when the post-environment has exactly the expected differences from the pre-environment.

**Why versioned task suites?** The benchmark is designed as a community resource that evolves. Early adopters reported bugs in task verification (e.g., Workspace injection tasks 4 and 5 had imprecise checks -- fixed in v0.1.15), and versioning prevents old results from becoming invalid when tasks are updated.

**Why separate attack/defense registration?** To enable combinatorial evaluation. With 13 models x 12 attacks x 4 defenses, the full cartesian product is 624 configurations. The registry pattern makes it possible to add new attacks or defenses in a single file (with one decorator) and have them instantly available across all pipelines.

## 6. Transfer to Lyra (one idea + Section 4.x route + Impact/Effort/Tier + LICENSE)

### Transferable Idea: Dual-metric benchmarking harness (utility + security)

Lyra should adopt AgentDojo's dual-metric scoring for its own evaluation pipeline. Currently, Lyra's test suite measures task completion (does the tool call produce the right output?) but does not systematically measure security (did an injection subvert the agent?). Lyra could build a mini "dojo" that:

1. Defines a set of canonical user tasks (e.g., "read a file and summarize it", "send a message to user X").
2. Defines injection vectors for each task (e.g., a malicious line in a file being read, an injected instruction in a received message).
3. Runs each (task, injection) pair and records both utility (did the agent do what the user asked?) and security (did the agent also execute the injection goal?).

### Workstream Route

This maps to **Section 4 of the Lyra architecture** (Safety and Alignment). Specifically:

- **Section 4.2: Input/Output Guardrails** -- The `tool_filter` defense (an LLM pre-filters available tools based on the user query) is directly applicable as a Lyra guardrail step. It reduced ASR by 86% for gpt-4o while actually improving utility.
- **Section 4.3: Prompt Injection Detection** -- The `TransformersBasedPIDetector` using `deberta-v3-base-prompt-injection-v2` can be integrated as a Lyra middleware pipe that scans tool outputs for injected instructions before they reach the LLM.
- **Section 4.5: Benchmarking & Evaluation** -- The dual-metric evaluation methodology itself belongs here: Lyra should measure security alongside utility in its CI pipeline.

The most practical near-term integration is the **dual-metric CI benchmark**. Lyra already has a test harness; extending it to measure "utility under attack" and "injection resistance" for each release would give a quantitative safety regression signal.

### Impact, Effort, Tier

- **Impact: 8/10** -- Adds a quantitative security dimension to Lyra's evaluation that currently does not exist. Enables safety regression testing and defense effectiveness comparisons. However, the synthetic tasks would need to be maintained and kept relevant as Lyra's capabilities grow.
- **Effort: 4/10** -- The core benchmarking infrastructure already exists in AgentDojo's open-source code (MIT license). The main work is (a) adapting the pipeline composition model to Lyra's existing architecture, (b) writing Lyra-specific user/injection tasks, and (c) integrating with Lyra's CI. Estimated 1-2 weeks for a senior engineer.
- **Tier: High** -- This is a fundamental safety evaluation capability, not a nice-to-have. As Lyra becomes capable of more autonomous actions, the ability to measure and track injection resistance becomes critical.

### LICENSE

**MIT License** -- Full permissive license. No restrictions on use, modification, or redistribution. AgentDojo can be used as a dependency, forked, or adapted without any license restrictions. Attribution is requested (CITATION.bib) but not required by the license terms.
