# MontrealAI/skillos -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline:** SkillOS is a reference implementation and public proof environment for self-improving AI-agent systems. It implements a closed loop that converts completed work into reusable, verified skills that compound across a network.

**The mechanism is a deterministic pipeline:**

```
work -> trace -> lesson -> candidate skill -> verification -> release -> routing upgrade -> better future work
```

Concretely, the code enacts this through six service classes:
1. **AgentRuntime** runs a job by selecting a skill (via keyword matching on the goal string), rendering output from a template, scoring it against hardcoded heuristics, and recording a trace.
2. **LearningEngine** scans traces for patterns in `human_edits` fields and produces "lessons" (e.g., "users repeatedly move the next step to the opening -- put it there by default").
3. **SkillTrainer** takes a lesson and appends a `## Learned Behavior` section to the skill's markdown, producing a candidate version.
4. **TestLab** A/B tests the candidate against the baseline on a held-out case set using deterministic scoring and safety-checks the candidate markdown for dangerous phrases.
5. **ReleaseCenter** approves/releases a candidate version (with rollback support) if tests pass.
6. **SkillOSStorage** persists everything in SQLite.

**Critical detail:** The entire system is deterministic. There is no LLM integration. The "agent" is a template renderer, the "learning" is hardcoded rule extraction from `human_edits` strings, and the "A/B test" compares pre-programmed scores. This is by design -- it enables zero-cost, zero-API-key, perfectly reproducible GitHub Actions proofs.

## 2. Architecture & Core Modules

**Language:** Python 3.10+, JavaScript/CSS for the frontend.

**Package structure** (13 files in `skillos/`):

| Module | Lines | Role |
|--------|-------|------|
| `cli.py` | 246 | CLI entry point (argparse); 11 subcommands: init, demo, job, learn, train, approve, serve, status, dashboard, verify, wealth-proof, reset |
| `models.py` | 90 | 6 dataclasses: Agent, Job, Trace, Lesson, SkillVersion, Release |
| `storage.py` | 289 | SQLite persistence; 7 tables (agents, skills, skill_versions, jobs, traces, lessons, releases); JSON columns for nested data |
| `runtime.py` | 92 | AgentRuntime -- keyword-based skill routing, template-based output rendering, deterministic scoring |
| `learning.py` | 53 | LearningEngine -- discovers lessons from trace + human_edits pattern matching |
| `trainer.py` | 41 | SkillTrainer -- creates candidate skill versions by appending learned-behavior sections |
| `evals.py` | 74 | TestLab -- A/B tests candidate vs baseline with deterministic scores; safety checks |
| `releases.py` | 54 | ReleaseCenter -- approval/rollback with canary rollout support |
| `permissions.py` | 22 | PermissionCenter -- allow/block list tool checking |
| `seed.py` | 131 | Demo data seeder (3 agents, 3 skills) |
| `api.py` | 138 | HTTP API (8 endpoints) using stdlib http.server |
| `wealth_proof.py` | 477 | Flagship wealth-accumulation proof generator |
| `__init__.py` | 3 | Package version |

**Data Flow:**

```
CLI (cli.py) -> AgentRuntime.run_job() -> SkillOSStorage.create_trace()
            -> LearningEngine.discover_lessons() -> SkillTrainer.create_candidate_from_lesson()
            -> TestLab.evaluate_skill() -> ReleaseCenter.approve_release()
```

**Architecture Pattern:** Monolithic Python reference implementation. Layered service classes over a single SQLite store. Zero external dependencies (stdlib only). HTTP server is Python's built-in `http.server.ThreadingHTTPServer`.

**Configuration:** `pyproject.toml` declares zero dependencies beyond `setuptools>=68`. The `[project.scripts]` entry registers `skillos = skillos.cli:main`.

## 3. Performance / Benchmarks

All benchmarks are **deterministically generated** from `wealth_proof.py`, not from real LLM evaluations. The "wealth proof" runs on a sales follow-up email workflow with 5 training jobs and 4 holdout cases.

**Reported metrics** (from `QA_VERIFICATION.md` and `wealth_proof.py`):

| Metric | Initial Agent | After SkillOS (v6) | Delta |
|--------|:-:|:-:|:-:|
| Quality score | 0.50 | 0.96 | +0.46 (+92%) |
| Minutes per job | 6.75 | 2.55 | -4.20 (-62%) |
| Cost per job (USD) | $8.48 | $3.23 | -$5.25 (-62%) |
| Accepted rate | 36% | 96% | +60pp |

**Monotonic checks** (all pass by construction):
- Cost decreases after every release
- Speed (minutes/job) decreases after every release
- Quality score increases after every release
- Accepted rate increases after every release

**Projected annual impact** (model assumptions): $117,700 savings vs human baseline at 10,000 jobs/year.

**Benchmark methodology:** The proof uses `HOLDOUT_CASES` (4 prospects never seen during training) for validation. Quality scoring is rule-based (5 rules with additive quality weights). Human baseline assumes 12 min/job at $75/hr fully loaded.

## 4. Trade-offs

**Wins:**

- **Perfect reproducibility.** Deterministic agents and SQLite persistence mean every proof run produces identical results. Zero flakiness.
- **Zero operational cost.** No API keys, no LLM calls, no cloud services. Runs entirely in GitHub Actions free tier.
- **Comprehensive proof portfolio.** 17+ autonomous proofs covering capability liquidity, cross-domain transfer, fork resistance, governance twin, assurance case graph, SLA reliability mesh, etc.
- **Public transparency.** Full proof chain published to GitHub Pages with JSON receipts, markdown reports, badges, and visual proof cards accessible to non-technical viewers.
- **Monotonic gates.** The proof checks that every release monotonically improves cost, speed, and quality -- not just net improvement.
- **Safety and permission model.** Built-in allow/block tool lists, test lab safety checks (e.g., "no unauthorized send", "no payment initiation"), and release rollback.

**Losses / Limitations:**

- **No real LLM integration.** The roadmap (v2) explicitly lists "Plug in LLM provider" as TODO. The current agents are template renderers with hardcoded heuristics. This means the "self-improvement" is simulated, not real recursive self-improvement.
- **Massive scope gap.** The README discusses "civilization-scale capability network" and "Kardashev Type II," but the codebase is a 1,300-line SQLite demo. The marketing language dramatically overstates the current implementation's capability.
- **Template-based skills are simplistic.** Skills are markdown strings with instructions appended. There is no structured skill representation, no tool-calling graph, no conditional branching, no state management -- just text that the "agent" ignores (the AgentRuntime does not parse the markdown; it pattern-matches on skill_id).
- **No actual learning.** "Lesson discovery" is regex matching on `human_edits` strings. There is no model training, no gradient descent, no reinforcement learning. The "lesson" extracts one of five hardcoded patterns.
- **Limited scalability.** SQLite, stdlib HTTP server, no async, no connection pooling. Not suitable for production multi-agent systems.
- **Security is a mock.** `PermissionCenter` is 22 lines of Python with no authentication, no RBAC, no multi-tenancy. The `safety_checks` in `TestLab` checks for hardcoded dangerous phrases in markdown strings.
- **Test coverage is thin.** 4 test files, the main test (`test_wealth_proof.py`) tests the deterministic proof passes by construction. A circular proof.
- **GitHub Actions surface is large.** 60+ workflow files, many of which are versioned variants (command center v2/v3/v4/v5/v7/v17, agent evolution v2/v3, etc.), suggesting churn and unclear deprecation.

## 5. Design Rationale

The architectural choices reveal deliberate design philosophy:

1. **Zero dependencies** (`pyproject.toml` has no `dependencies` key). Rationale: the proof must run in GitHub Actions without pip install time, version conflicts, or network access. This is the single most important constraint.

2. **Deterministic agents.** Since there is no LLM, the "agent" is a template renderer. This is intentional: it makes every run byte-identical, enables monotonic-gate proofs, and removes the need for model version pinning or API reliability contracts.

3. **Skills as markdown.** Markdown is the simplest human-readable format. The system treats skills as opaque strings that happen to carry structured metadata (allowed_tools, blocked_tools, tests). By not parsing instruction text, the system avoids coupling to any skill representation format.

4. **Learning from human edits.** The key insight: human feedback on agent output is the richest signal for improvement. The lesson engine looks at what humans changed (`human_edits` field) to infer what should be different. This is a defensible design choice even for real agents.

5. **Monotonic checks as proof structure.** Instead of a single before/after comparison, SkillOS checks that every step in the sequence improves all metrics. This prevents cherry-picking and makes the proof harder to game.

6. **Pyramid of proofs.** Each proof layer (shadow pilot, capability liquidity, cross-domain transfer, etc.) tests a different aspect of the RSI claim. The portfolio approach acknowledges that no single proof can establish recursive self-improvement.

7. **Roadmap layering.** v1 = local reference impl (done), v2 = real agent integration (next), v3 = enterprise (multi-tenant, Postgres, auth), v4 = civilization-scale. This acknowledges the current implementation is a foundation, not the end state.

## 6. Transfer to Lyra

**Most transferable idea: The Lesson->Candidate->Verification->Release pipeline with monotonic gates.**

Lyra currently has a skill system but lacks a closed-loop mechanism for skills to improve from usage. The SkillOS pattern offers a concrete architecture:

- Persist traces from every agent invocation (inputs, outputs, human edits, quality score).
- Run a scheduled lesson extraction that finds patterns in traces where human edits cluster.
- Generate candidate skill improvements automatically.
- Run A/B tests (candidate vs baseline) across held-out test cases.
- Release only if the candidate passes monotonic gates (cost down, quality up, safety checks pass).
- Support rollback and canary rollout.

**Workstream Route:** This maps to **Section 4.2 (Learning and Skill Evolution)** in the Lyra plan. Specifically, subsection 4.2.3 "Closed-loop improvement from traces" or 4.2.4 "Skill quality gates". An alternative home is **Section 4.4 (Routing)**, where improved skills feed into routing decisions.

**Impact:** 6/10 -- high. This would give Lyra a compounding improvement mechanism that is self-reinforcing rather than relying on manual skill authoring.

**Effort:** 5/10 -- medium. Requires trace persistence, a lesson extraction engine, an A/B evaluation framework, and monotonic release gates. Most of the infrastructure (trace store, skill registry, eval harness) already exists or is planned in Lyra.

**Tier:** Instrumental. The mechanism is foundational for self-improvement but not itself a user-facing feature. It enables the virtuous cycle that makes the system get better over time.

**LICENSE: MIT** -- fully compatible with Lyra (permissive, no restrictions on use/modification/redistribution).

**Key files:**
- Core loop: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/MontrealAI__skillos/skillos/{runtime,learning,trainer,evals,releases,storage}.py`
- Reference proof: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/MontrealAI__skillos/skillos/wealth_proof.py`
- Data model: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/MontrealAI__skillos/skillos/models.py`
- Entry point: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/MontrealAI__skillos/skillos/cli.py`
- Tests: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/MontrealAI__skillos/tests/test_wealth_proof.py`
- Metadata: `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/lyra-upgrade/repos/MontrealAI__skillos/pyproject.toml`
