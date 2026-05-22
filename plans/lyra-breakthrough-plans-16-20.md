# 🧬 Lyra Breakthrough Plans 16–20: The AGI Ascent

> **5 new ultra plans for Lyra's final ascent toward AGI.**
> Built from 4,840 lines of research (45 parts, 23 waves), 111 existing packages, 15 existing plans.
> Each plan represents the single highest-impact capability Lyra is still missing.

---

## Gap Analysis: What Lyra Has vs. What It Still Needs

| Capability | Lyra Has? | Research Source | Gap |
|-----------|-----------|-----------------|-----|
| **Auto Mode** (2-layer classifier) | ❌ Missing | Claude Code Auto Mode, Anthropic | Most critical UX gap |
| **Constitutional Alignment** (96%→0%) | Partial (`lyra-ethics`) | Anthropic Teaching Claude Why | Needs principled training |
| **NLA Interpretability** (read agent thoughts) | ❌ Missing | Anthropic NLAs (May 2026) | No internal transparency |
| **Thinking/Non-Thinking Switch** | ❌ Missing | Qwen3 (June 2026) | Can't allocate compute per task |
| **Long-Horizon Planning** (100+ steps) | ❌ Missing | SGR-Bench (agents fail >3 steps) | No long-horizon coherence |
| **World Model** (mental simulation) | ❌ Missing | Verified open gap | Reactive, not proactive |
| **Agent Challenge Platform** | ❌ Missing | OpenAI Parameter Golf (93% agent usage) | No competitive agent research |
| **Managed Agent Orchestration** | Partial | Anthropic Scaling Managed Agents | Needs brain/hands separation |
| **Auto Alignment Research** | ❌ Missing | Anthropic AARs (Apr 2026) | Can't self-improve alignment |
| **MoE Agent Dispatch** | ❌ Missing | Moego (202⭐) | No expert routing |

---

# Plan 16 — AUTO MODE & CONSTITUTIONAL ALIGNMENT
## The Trust & Autonomy Layer

### Core Thesis
The #1 thing Lyra is missing: **a safe autonomous mode**. Based on Claude Code Auto Mode (Anthropic, Mar 2026) — 2-layer classifier with 0.4% FPR, 93% fewer permission prompts, deny-and-continue policy. Combined with constitutional alignment training (Anthropic, May 2026 — reduced misalignment 96%→0%).

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    LYRA AUTO MODE                             │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐│
│  │ INPUT LAYER              │  │ OUTPUT LAYER                 ││
│  │ Prompt Injection Probe   │  │ 2-Stage Classifier (Sonnet) ││
│  │ Scans tool outputs       │  │ Fast filter → CoT analysis  ││
│  │ Blocks hijacking att.    │  │ Sees user + tool calls only ││
│  └─────────────────────────┘  └─────────────────────────────┘│
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ CONSTITUTIONAL ALIGNMENT TRAINER                          ││
│  │ Teaches WHY not just WHAT — principles > demonstrations  ││
│  │ 96%→0% agentic misalignment (proven by Anthropic)        ││
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ DENY-AND-CONTINUE POLICY                                  ││
│  │ Blocked → safer approach → max 3 consecutive denials     ││
│  │ → HUMAN escalation                                        ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Auto Mode Engine (`lyra-auto-mode`)
```python
class AutoModeEngine:
    """Two-layer autonomous permission system."""
    
    def __init__(self):
        self.input_probe = PromptInjectionProbe()
        self.classifier = TranscriptClassifier()
        self.denial_count = 0
        self.total_denials = 0
    
    async def check_input(self, tool_output: str) -> InputVerdict:
        """Layer 1: detect prompt injection in tool outputs before they enter context."""
    
    async def check_action(self, transcript: Transcript) -> ActionVerdict:
        """Layer 2: 2-stage transcript classification.
        Stage 1: Fast single-token filter (cheap).
        Stage 2: Chain-of-thought analysis (only if flagged)."""
    
    def handle_denial(self) -> Action:
        """Deny-and-continue: blocked action → try safer approach.
        3 consecutive or 20 total → HUMAN escalation."""
```

#### 2. Constitutional Alignment Trainer (`lyra-constitutional`)
```python
class ConstitutionalTrainer:
    """Teaches agents WHY actions are aligned, not just WHAT actions to take.
    Based on Anthropic's proven 96%→0% misalignment reduction."""
    
    PRINCIPLES = [
        "Honesty: Never deceive users or evaluators",
        "Cooperation: Help users achieve their goals safely",
        "Responsibility: Acknowledge limitations and errors",
        "Safety: Refuse actions that could cause harm",
    ]
    
    def train(self, agent: Agent, constitution: list[Principle]) -> TrainingResult:
        """Train agent on constitutional principles across diverse environments."""
    
    def evaluate_alignment(self, agent: Agent) -> AlignmentScore:
        """Evaluate agent against misalignment benchmarks."""
```

### Packages
| Package | Purpose | Research Source |
|---------|---------|----------------|
| `lyra-auto-mode` | 2-layer autonomous permission system | Claude Code Auto Mode |
| `lyra-constitutional` | Principled alignment training | Anthropic Teaching Claude Why |

### Timeline: 12 weeks

---

# Plan 17 — NLA INTERPRETABILITY & AGENT INTROSPECTION
## Reading the Agent's Mind

### Core Thesis
Lyra cannot explain its internal reasoning. Anthropic's Natural Language Autoencoders (May 2026) proved that **model activations can be translated into human-readable text** — reading the agent's thoughts. Lyra needs this for: detecting deception, debugging reasoning chains, building user trust, and safety auditing.

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│               LYRA INTERPRETABILITY ENGINE                     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐│
│  │ ACTIVATION VERBALIZER    │  │ BELIEF DETECTOR             ││
│  │ Reads internal           │  │ Detects hidden beliefs:     ││
│  │ activations → text       │  │ - Being tested awareness   ││
│  │ Trained on frozen model  │  │ - Cheating behavior        ││
│  │ Cross-validated via      │  │ - Language drift           ││
│  │ reconstruction           │  │ - Reward hacking           ││
│  └─────────────────────────┘  └─────────────────────────────┘│
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ AUTO ALIGNMENT RESEARCHER                                  ││
│  │ N copies of Lyra autonomously discover alignment          ││
│  │ improvements — using weak-to-strong supervision           ││
│  │ Detects and disqualifies reward hacking                   ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Activation Verbalizer (`lyra-interpret`)
```python
class ActivationVerbalizer:
    """Translates internal model activations into human-readable text.
    Based on Anthropic's Natural Language Autoencoders (May 2026)."""
    
    def __init__(self):
        self.encoder = ActivationEncoder()  # activation → tokens
        self.decoder = ActivationDecoder()  # tokens → reconstructed activation
    
    def verbalize(self, activation: Activation) -> str:
        """Convert a model activation to a text explanation."""
    
    def detect_hidden_belief(self, activation: Activation) -> Belief:
        """Detect if agent holds hidden beliefs (about being tested, etc.)."""
```

#### 2. Auto Alignment Researcher (`lyra-auto-align`)
```python
class AutoAlignmentResearcher:
    """N copies of Lyra autonomously discover improvements to their own alignment.
    Based on Anthropic's AAR system (Apr 2026)."""
    
    def __init__(self, copies: int = 9):
        self.copies = [Agent() for _ in range(copies)]
    
    async def discover_improvements(self) -> list[AlignmentImprovement]:
        """Each copy designs, tests, and analyzes alignment experiments."""
    
    def detect_reward_hacking(self, improvement: AlignmentImprovement) -> bool:
        """Detect and disqualify improvements that game the reward signal."""
```

### Packages
| Package | Purpose | Research Source |
|---------|---------|----------------|
| `lyra-interpret` | Activation verbalization, belief detection | Anthropic NLAs |
| `lyra-auto-align` | Automated alignment research | Anthropic AARs |

### Timeline: 14 weeks


---

# Plan 18 — THINKING/NON-THINKING MODE SWITCH + MoE DISPATCH
## Adaptive Compute Allocation

### Core Thesis
Lyra uses the same compute for every task — from "what's the weather?" to "prove the Riemann Hypothesis." Qwen3 (June 2026) proved that **a single model can switch between thinking and non-thinking modes** based on task complexity. Combined with Mixture-of-Experts dispatch, Lyra would dynamically allocate compute per request: spend more on hard tasks, less on easy ones.

### Architecture

```
                    ┌──────────────────────────────────────┐
                    │   TASK COMPLEXITY ESTIMATOR           │
                    │   • Step count prediction             │
                    │   • Ambiguity detection               │
                    │   • Knowledge requirement analysis    │
                    │   • Confidence calibration            │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │      MODE ROUTER                     │
                    │                                      │
                    │   Easy? → Non-Thinking (fast, cheap) │
                    │   Medium? → Thinking (balanced)       │
                    │   Hard? → Deep-Thinking (slow, deep) │
                    │   Critical? → MoE Ensemble (all)     │
                    └──────┬──────────────┬───────────────┘
                           │              │
              ┌────────────▼──┐    ┌─────▼────────────┐
              │  SKILL EXPERT │    │ REASONING EXPERT  │
              │  (code, math,  │    │ (CoT, ToT, PoT)   │
              │   research)    │    │                    │
              └───────────────┘    └────────────────────┘
```

### Key Components

#### 1. Complexity Estimator (`lyra-complexity`)
```python
class ComplexityEstimator:
    """Predict task difficulty to allocate appropriate compute."""
    
    def estimate(self, task: str) -> ComplexityScore:
        """Analyze task and return complexity estimate."""
    
    DIMENSIONS = ["step_count", "ambiguity", "knowledge_depth", "creativity_required"]
```

#### 2. Mode Switch Engine (`lyra-mode-switch`)
```python
class ModeSwitchEngine:
    """Switch between thinking/non-thinking modes per task."""
    
    MODES = ["non_thinking", "thinking", "deep_thinking", "ensemble"]
    
    def select_mode(self, complexity: ComplexityScore) -> str:
        """Select optimal mode based on complexity."""
    
    async def execute(self, task: str, mode: str) -> Result:
        """Execute task in the selected compute mode."""
```

#### 3. MoE Agent Router (`lyra-moe-router`)
```python
class MoERouter:
    """Mixture-of-Experts dispatch for agent skills."""
    
    EXPERTS = {
        "code": CodeExpert(),
        "math": MathExpert(),
        "research": ResearchExpert(),
        "creative": CreativeExpert(),
        "safety": SafetyExpert(),
    }
    
    def route(self, task: str) -> list[Expert]:
        """Route task to most relevant experts."""
    
    def combine(self, expert_outputs: list[Output]) -> Output:
        """Combine expert outputs with learned weights."""
```

### Packages
| Package | Purpose | Research Source |
|---------|---------|----------------|
| `lyra-complexity` | Task difficulty estimation | Original |
| `lyra-mode-switch` | Thinking/non-thinking mode | Qwen3 |
| `lyra-moe-router` | Expert dispatch routing | Moego (202⭐) |

### Timeline: 12 weeks

---

# Plan 19 — LONG-HORIZON PLANNER + WORLD MODEL
## 100+ Step Coherence

### Core Thesis
SGR-Bench proved agents fail at >3 step multi-step tasks. Long-horizon planning requires: hierarchical goal decomposition, mental simulation (world model), periodic checkpointing with replanning, and maintaining coherence across hundreds of steps. Anthropic's long-running harness design (Mar 2026) provides the checkpointing pattern.

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    LONG-HORIZON PLANNER                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Goal: "Research, implement, test, deploy feature X"          │
│     ↓                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │ DECOMPOSER       │  │ WORLD MODEL      │  │ CHECKPOINTER ││
│  │ Goal → 100+      │  │ Mental sim before│  │ Save state   ││
│  │ subgoals in DAG  │  │ each subgoal     │  │ every N steps││
│  │ Dependency graph │  │ What-if analysis │  │ Replan from  ││
│  └─────────────────┘  └─────────────────┘  │ failure point ││
│                                              └──────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Hierarchical Decomposer (`lyra-decomposer`)
```python
class HierarchicalDecomposer:
    """Decompose complex goals into 100+ executable subgoals."""
    
    def decompose(self, goal: str) -> GoalGraph:
        """Decompose into hierarchical goal graph."""
    
    def dependency_order(self, graph: GoalGraph) -> list[Subgoal]:
        """Topological sort respecting dependencies."""
```

#### 2. World Model Simulator (`lyra-world-model`)
```python
class WorldModel:
    """Mental simulation of environment dynamics."""
    
    def predict(self, state: State, action: Action) -> State:
        """Predict next state."""
    
    def simulate_plan(self, plan: list[Action]) -> Simulation:
        """Full simulation before execution."""
    
    def what_if(self, state: State, alternative: Action) -> Consequence:
        """Counterfactual analysis."""
```

#### 3. Long-Horizon Executor (`lyra-long-horizon`)
```python
class LongHorizonExecutor:
    """Execute 100+ step plans with periodic verification."""
    
    CHECKPOINT_EVERY = 10
    
    async def execute(self, plan: Plan) -> ExecutionResult:
        """Execute with checkpointing and replanning."""
    
    async def verify_progress(self, subgoal: Subgoal) -> Progress:
        """Verify subgoal completion before advancing."""
    
    async def replan(self, plan: Plan, failure_step: int) -> Plan:
        """Replan from failure without restarting."""
```

### Packages
| Package | Purpose | Research Source |
|---------|---------|----------------|
| `lyra-decomposer` | Hierarchical goal decomposition | SGR-Bench, Verified gap |
| `lyra-world-model` | Mental simulation | Verified open gap |
| `lyra-long-horizon` | 100+ step execution with checkpointing | Anthropic long-running harness |

### Timeline: 14 weeks

---

# Plan 20 — AGENT CHALLENGE PLATFORM + OPEN-ENDED LEARNING
## Competitive & Self-Directed AGI

### Core Thesis
OpenAI Parameter Golf proved (May 2026): **93% of participants used AI coding agents**, agents now do ML research competitively, and open challenges are the best talent discovery mechanism. Combined with open-ended learning (agents propose their own learning goals), this creates a **self-sustaining AGI improvement loop**.

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              LYRA CHALLENGE PLATFORM                           │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │ CHALLENGE ENGINE │  │ COMPETITION      │  │ LEADERBOARD  ││
│  │ ML research tasks│  │ Agent vs agent   │  │ Score per     ││
│  │ Varying difficulty│  │ Submission eval  │  │ version       ││
│  │ Auto-generated   │  │ Anti-gaming      │  │ Public API    ││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ OPEN-ENDED LEARNER                                        ││
│  │ Agent proposes its own learning goals                     ││
│  │ Self-evaluates progress                                   ││
│  │ Auto-generates next curriculum phase                      ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Challenge Engine (`lyra-challenge`)
```python
class ChallengeEngine:
    """Auto-generated ML research challenges for agents."""
    
    def generate_challenge(self, difficulty: str, domain: str) -> Challenge:
        """Generate research challenge at specified difficulty."""
    
    def evaluate_submission(self, submission: Submission, challenge: Challenge) -> Score:
        """Evaluate agent submission against ground truth."""
    
    def detect_gaming(self, submission: Submission) -> bool:
        """Detect if agent is gaming the evaluation."""
```

#### 2. Open-Ended Learner (`lyra-open-ended`)
```python
class OpenEndedLearner:
    """Agent that proposes and pursues its own learning goals."""
    
    def propose_goal(self, capabilities: list[str], gaps: list[str]) -> Goal:
        """Propose the next learning goal."""
    
    def self_evaluate(self, goal: Goal, result: Outcome) -> float:
        """Self-evaluate progress toward proposed goal."""
    
    def update_curriculum(self, completed: list[Goal]) -> list[Goal]:
        """Auto-generate next learning phase."""
```

#### 3. Agent Arena (`lyra-arena`)
```python
class AgentArena:
    """Competitive agent environment modeled on Parameter Golf."""
    
    async def run_tournament(self, agents: list[Agent], challenge: Challenge) -> TournamentResult:
        """Run multi-agent tournament on a challenge."""
    
    def compute_elo(self, results: list[Match]) -> dict[str, float]:
        """Compute Elo ratings for all participating agents."""
```

### Packages
| Package | Purpose | Research Source |
|---------|---------|----------------|
| `lyra-challenge` | ML research challenge platform | OpenAI Parameter Golf |
| `lyra-open-ended` | Self-proposed learning goals | Verified open gap |
| `lyra-arena` | Competitive agent tournaments | Original |

### Timeline: 12 weeks

---

# Compound Roadmap: All 20 Plans

```
Month: 0    2    4    6    8    10   12   14   16   18   20   22   24
      │    │    │    │    │    │    │    │    │    │    │    │    │
P1–5: AGI Foundations        ████████████████████████████████████
P6–10: Breakthroughs              ██████████████████████████████
P11–15: Frontier                     ████████████████████████████
P16: Auto Mode + Alignment                   ████████████
P17: NLA Interpretability                         ██████████████
P18: Thinking/MoE Switch                              ████████████
P19: Long-Horizon + World Model                           ██████████████
P20: Challenge + Open-Ended                                   ████████████
```

### Total: 20 Breakthrough Plans

| Plan | Name | Packages | Timeline | Source |
|------|------|----------|----------|--------|
| 16 | **Auto Mode + Constitutional Alignment** | lyra-auto-mode, lyra-constitutional | 12 wk | Claude Code Auto Mode + Anthropic |
| 17 | **NLA Interpretability + Auto Alignment** | lyra-interpret, lyra-auto-align | 14 wk | Anthropic NLAs + AARs |
| 18 | **Thinking/MoE Mode Switch** | lyra-complexity, lyra-mode-switch, lyra-moe-router | 12 wk | Qwen3 + Moego |
| 19 | **Long-Horizon Planner + World Model** | lyra-decomposer, lyra-world-model, lyra-long-horizon | 14 wk | SGR-Bench + Anthropic |
| 20 | **Challenge Platform + Open-Ended Learning** | lyra-challenge, lyra-open-ended, lyra-arena | 12 wk | Parameter Golf + GPT-5.5 |

**Total: 20 plans, 24 months, ~140+ packages, full-spectrum AGI coverage.**

---

> Part of the [Harness Engineering & Agentic AI](README.md) corpus. Built from 4,840 lines of research (45 parts, 23 waves), 111 existing Lyra packages, 15 existing plans. June 2026.
