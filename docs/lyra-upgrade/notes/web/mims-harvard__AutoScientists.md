# mims-harvard/AutoScientists -- Deep-Read

## 1. Headline Feature & Mechanism

**Self-organizing agent teams for decentralized long-running scientific experimentation.**

Unlike prior agent systems (e.g., OpenHands, LangGraph) that follow a single research trajectory or coordinate through a central planner, AutoScientists agents self-organize into hypothesis-based teams, critique each other's proposals before spending experimental compute, and share successes and failures through a shared message-board workspace so the entire system avoids redundant exploration while sustaining parallel search.

The mechanism works as follows:

- **Orchestrator as pure coordinator**: A single orchestrator process (guided by `runbook.md`) launches Claude Code subagents, monitors health, and propagates champions. It NEVER runs experiments itself.
- **Peer-review-before-compute**: Every experiment starts as a `[PROPOSAL]` post. At least one non-author must comment before the experiment enters a team queue. No GPU time is spent on unreviewed ideas.
- **Hypothesis-based team formation**: Agents form teams around falsifiable hypotheses (not fixed search-space axes). Teams age and are refuted or adapted via meta-improvement cycles.
- **Champion propagation with multi-seed noise gating**: Before a new-best configuration is promoted, a multi-seed noise floor check confirms the improvement is not a lucky draw. Second-seed re-runs are required for borderline deltas.
- **Self-regulating discussion triggers**: Analysts detect stagnation (0 KEEPs in 3+ rotations OR single-axis exhaustion) and autonomously post `[DISCUSSION-TRIGGER]` threads to initiate team restructuring without orchestrator intervention.

## 2. Architecture & Core Modules

### Entry Points

| File | Role |
|------|------|
| `launch.py` | Experiment scaffolding -- clones repos, creates agent directories, registers on ClawInstitute API, populates workspaces, posts kickoff discussion |
| `runbook.md` | Orchestrator program -- the control flow the orchestrator executes (bootstrap, discuss, form teams, execute loop, meta-improve) |
| `requirements.txt` | Minimal: `requests>=2.31`, `pyyaml>=6.0` |

### System Directory (the actual "code" is markdown + API calls)

| Path | Purpose |
|------|---------|
| `system/templates/HEARTBEAT.md` | Per-agent lifecycle -- 6-part state machine (Mode Selector, Boot, Discussion Branch, No-Team Exit, Normal Cycle, Resume-and-Post). Every agent reads this every invocation. |
| `system/templates/ROLE-GPU.md` | GPU agent protocol: claim from queue, copy champion code, apply diff, train, record, post result, propagate champion, run multi-seed gate |
| `system/templates/ROLE-ANALYST.md` | Analyst protocol: stagnation detection, team reform, noise-floor calibration, baseline coverage audit, propose experiments (2 per cycle, 1 must be bold), queue management |
| `system/templates/ROLE-MONITOR.md` | Monitor protocol: bootstrap infrastructure, facilitate team formation, health monitoring |
| `system/templates/ROLE-TEAM.md` | Team coordination: file discovery protocol, hypothesis tracking, strategy docs |
| `system/reference/SKILL.md` | Overview of the multi-agent focus area concept |
| `system/reference/PHASES.md` | 4-phase lifecycle: Bootstrap, Discuss/Form Teams, Execute, Adapt |
| `system/reference/AGENT-SETUP.md` | Agent directory structure, credentials, AGENT.md format, boot sequence |
| `system/reference/API-REFERENCE.md` | Full ClawInstitute REST API reference |
| `system/reference/LOGGING.md` | Structured logging format (`experiments.jsonl`, `sessions.jsonl`, raw logs) |
| `system/reference/META-IMPROVEMENT.md` | Meta-improvement protocol -- every 3 cycles the orchestrator diagnoses team performance and edits role templates |
| `system/external-repo-setup/SKILL.md` | Protocol for cloning external GitHub repos, installing deps, downloading pretrained weights, patching for modern dep compatibility |

### Task Directories (benchmark definitions)

| Path | Task Type |
|------|-----------|
| `task-autoresearch/` | Open-ended nanoGPT val_bpb optimization (wraps karpathy/autoresearch) |
| `task-biomlbench/` | 24 biomedical ML benchmarks (drug discovery, protein engineering, single-cell omics, biomedical imaging) |
| `task-protein-gym/` | ProteinGym Spike fitness prediction, evolving a Kermut GP baseline |

Each task ships a `TASK.md` (problem definition with YAML frontmatter) and a `LAUNCH.md` (task-profile filling the 13 hooks `runbook.md` references).

### Data Flow

```
1. launch.py creates experiment directory, clones repos, boots ClawInstitute workspace
2. orchestrator reads runbook.md + task-profile.md
3. All agents run discussion (post [DISCUSSION] threads)
4. Monitor or alphabetically-last analyst writes teams/roster.md
5. Execution loop:
   a. Analysts post [PROPOSAL] -> discuss -> add to team queue
   b. GPU agents claim from queue -> copy champion code -> apply diff -> train -> record result
   c. If KEEP: multi-seed gate -> propagate champion/train.py -> update champion.md
   d. Orchestrator checks health, handles stagnation, runs meta-improvement every 3 cycles
6. Exit on stagnation (optimization) or wall-clock deadline (biomlbench)
```

### External Dependencies

- **ClawInstitute** (npm: `clawinstitute`): Local message-board/server for agent coordination (workshops, workspaces, posts, files with YAML frontmatter, versioning, notifications)
- **Claude Code CLI** (`claude`): Each agent runs as a Claude Code subagent
- Python: `requests`, `pyyaml`

## 3. Performance/Benchmarks

From the README and paper (arXiv 2605.28655):

- **BioML-Bench (24 tasks)**: 74.4% mean leaderboard percentile, +8.33% over the strongest prior AI agent (single-agent baseline). Covers biomedical imaging, protein engineering, single-cell omics, drug discovery.
- **nanoGPT training optimization**: 1.9x faster to a target validation metric. 7 accepted improvements vs. 0 for a single-agent baseline.
- **ProteinGym fitness prediction**: +12.5% on the ACE2-Spike binding assay; +6.5% averaged across all 217 assays.
- **Known from meta-improvement diagnostics**: Prior runs experienced duplicate proposal rates of 20-40%, agent activation failures (analysts writing elaborate local notes instead of posting to the API), stale champion propagation, and discussion rounds that generated analysis reports without changing any files.

## 4. Trade-offs

### Wins

- **Eliminates central planner bottleneck**: Teams self-organize; no single agent decides the research direction.
- **Discussion-before-queuing prevents GPU waste**: Peer review catches mechanism errors and duplicates before compute spend.
- **Multi-seed noise gating prevents champion corruption**: Borderline improvements require second-seed confirmation before promotion.
- **Meta-improvement closes the loop**: The system edits its own role templates based on diagnostic patterns (duplicates, low KEEP rate, slow propagation).
- **Biomlbench wall-clock deadline awareness**: Agents dynamically shift from exploration to submission-production as deadline approaches.

### Losses

- **Heavy Claude Code API cost**: 9 agents (6 GPU + 3 analysts) running continuously on sonnet/opus. The meta-improvement log documents agent rate limits and OOM kills as recurring failure modes.
- **Agent reliability is the dominant failure mode**: The HEARTBEAT.md and ROLE-ANALYST.md files contain extensive documented failure-mode history -- analysts writing local notes instead of posting, GPU agents detaching training subprocesses, stale queue claims. Each documented failure adds another instruction, increasing template size and agent cognitive load.
- **Template bloat**: ROLE-ANALYST.md is 1300+ lines. As meta-improvement adds more checks (Step 0.5 noise calibration, Step 0.7 backlog ledger, Step 3.4 bracket rule, Step 3.5 ledger walk, Step 1a noise-floor rule, Step 1b followup harvest, Step 1b2 inductive reasoning, etc.), agents have more to comply with and less time to experiment.
- **Hypothesis falsification is slow**: Teams are supposed to self-refute via Step 0.3, but the protocol requires 3 rotations with zero supported KEEPs before `[HYPOTHESIS-FALSIFIED]` fires. In practice, teams can burn many GPU-hours on a dead hypothesis.
- **No training framework integration**: AutoScientists is purely an agent orchestration framework. It does not provide training infrastructure, model registries, or experiment tracking beyond flat JSONL files.

## 5. Design Rationale

The design is driven by three empirical observations documented in the codebase from prior runs:

1. **"Analysts hallucinate API calls"**: Haiku-class analysts repeatedly wrote local memory files claiming work was done but never called `POST /posts`. The fix was the `<promise>` tag requirement, the Rule 2 restatement ("your cycle is not complete until your [PROPOSAL]s appear in the workshop feed"), and the 50-tool-call budget.

2. **"Shared mutable state corrupts baselines"**: The initial design used a symlinked `repo/` directory shared across runs, accumulating 1800+ lines of uncommitted changes between experiments. Every experiment was anchored to a non-upstream starting point. The fix: each run gets an isolated git clone with `--depth 1`.

3. **"Single-agent baselines plateau"**: A single agent working independently produces incremental improvements but cannot sustain parallel search across diverse hypotheses. The self-organizing team structure was the direct response.

The system treats agents as **stateless workers with discoverable context** -- every agent session starts by reading the current shared state (workspace files, roster, champion, queue) rather than depending on prior session memory. This is explicitly documented in `AGENT-SETUP.md`: "Agents have no memory between sessions. All state comes from shared workspaces."

## 6. Transfer to Lyra

### One Transferable Idea: Hypothesis-Based Self-Organizing Agent Teams with Peer-Review-Gated Compute

The core pattern -- agents self-organize into hypothesis-based teams, use discussion-before-queuing peer review, and propagate champions with noise-gated promotion -- is directly applicable to Lyra's long-running research workflows. Lyra's current architecture uses a central planner/orchestrator pattern; adopting AutoScientists' decentralized self-organization would allow Lyra to sustain parallel research directions and autonomously detect/respond to stagnation.

### Lyra Workstream Route

**4.3 (Multi-Agent Orchestration)** -> **4.4 (Agent Lifecycle Management)** -> **4.6 (Research Workflow Automation)**.

4.3 adopts the discussion-before-queuing peer review pattern and hypothesis-based team formation. 4.4 adopts the HEARTBEAT mode selector and stateless-worker lifecycle. 4.6 adopts meta-improvement loops and self-triggered discussion rounds.

### Impact: 5 / Effort: 4 / Tier: Tier 1

The impact is high because decentralized self-organization is one of the few demonstrated approaches to sustaining long-running parallel scientific search. The effort is rated 4 because adapting the HEARTBEAT state machine and peer review protocol into Lyra's existing agent framework is a significant refactoring but does not require new infrastructure. Tier 1 because this is a fundamental architectural pattern change.

### License

**No license file found in the repository.** The README links to an arXiv paper and a project page. USE CAUTION -- the absence of a license means default copyright applies; you may not have rights to copy, modify, or distribute the code without explicit permission from the authors.
