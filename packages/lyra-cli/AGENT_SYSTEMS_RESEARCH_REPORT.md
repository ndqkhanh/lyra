# Agent Systems Research Report
## arXiv Papers & Anthropic Engineering Analysis

**Research Date:** May 16, 2026  
**Focus:** Practical techniques for Lyra CLI agent system

---

## Executive Summary

This report analyzes 9 recent papers and 1 engineering post on AI agent systems, extracting actionable techniques for building robust, scalable agent architectures. Key themes include:

1. **Context efficiency** as a first-class design constraint
2. **Direct corpus interaction** outperforming semantic retrieval
3. **Self-evolving systems** that improve through experience
4. **Memory-based learning** without model fine-tuning
5. **Atomic skill decomposition** for better generalization

---

## Paper 1: Beyond Semantic Similarity (arXiv:2605.05242)

**Authors:** Zhuofeng Li, Haoxiang Zhang, Cong Wei, et al. (18 authors)

### Key Contribution

**Direct Corpus Interaction (DCI)** - Agents search raw corpora using terminal tools (grep, file reads, shell commands) instead of embedding models or vector indexes.

### Core Insight

Traditional retrieval compresses corpus access into "a single top-k retrieval step before reasoning" which bottlenecks agentic tasks requiring:
- Exact lexical constraints
- Sparse clue conjunctions
- Local context checks
- Multi-step hypothesis refinement
- Intermediate entity discovery
- Plan revision after observing partial evidence

### Technical Approach

**DCI Characteristics:**
- No offline indexing required
- No embedding models or vector indexes
- Uses general-purpose terminal tools directly on raw text
- Adapts naturally to evolving local corpora
- Provides higher-resolution interface for corpus interaction

### Results

DCI "substantially outperforms strong sparse, dense, and reranking baselines" on BRIGHT and BEIR datasets, achieving strong accuracy on BrowseComp-Plus and multi-hop QA.

### Lyra CLI Implications

- **Prioritize terminal-native search tools** (grep, ripgrep, ast-grep) over semantic embeddings
- **Enable multi-step exploration** rather than single retrieval passes
- **Support hypothesis refinement** through iterative corpus interaction
- **Avoid premature indexing** - let agents explore raw files directly

---

## Paper 2: Agent-World (arXiv:2604.18292)

**Authors:** Guanting Dong, Junting Lu, Junjie Huang, Wanjun Zhong, et al. (19 authors)  
**Status:** Work in progress (April 2026)

### Key Contribution

**Self-evolving training system** with autonomous environment-task discovery and continuous multi-environment RL.

### Novel Techniques

1. **Agentic Environment-Task Discovery:** Autonomously explores databases and tool ecosystems from thousands of real-world themes, synthesizing verifiable tasks with controllable difficulty

2. **Continuous Self-Evolving Agent Training:** Combines multi-environment RL with dynamic task synthesis that identifies capability gaps and drives targeted learning

3. **Co-evolution Framework:** Simultaneous evolution of agent policies and training environments

### Architectural Patterns

- Multi-environment reinforcement learning setup
- Integration with Model Context Protocol (MCP) for unified tool interfaces
- Continuous learning loop between environment discovery and agent training

### Evaluation

- Tested across 23 agent benchmarks
- Agent-World-8B and 14B models outperform proprietary baselines
- Scaling analysis examines environment diversity and self-evolution rounds

### Lyra CLI Implications

- **MCP integration** for standardized tool interfaces
- **Dynamic task synthesis** to identify capability gaps
- **Multi-environment testing** across diverse real-world scenarios
- **Continuous learning loops** for agent improvement

---

## Paper 3: AutoTTS (arXiv:2605.08083)

**Authors:** Tong Zheng, Haolin Liu, Chengsong Huang, et al. (13 authors)  
**Date:** May 2026

### Key Contribution

**AutoTTS** - Environment-driven framework for discovering test-time scaling strategies automatically rather than manual heuristic design.

### Novel Techniques

**Environment Construction:**
- Formulates "width-depth TTS as controller synthesis over pre-collected reasoning trajectories and probe signals"
- Controllers decide when to "branch, continue, probe, prune, or stop"
- Enables cheap evaluation "without repeated LLM calls"

**Two Key Innovations:**
1. **Beta parameterization** - makes search space tractable
2. **Fine-grained execution trace feedback** - helps agents "diagnose why a TTS program fails"

### Architecture Pattern

Separates concerns:
- **Environment layer:** Tractable control space with cheap, frequent feedback
- **Controller layer:** Synthesizes strategies over pre-collected trajectories
- **Feedback mechanism:** Execution traces for iterative improvement

### Results

- Improved "accuracy-cost tradeoff over strong manually designed baselines"
- Discovered strategies generalize to held-out benchmarks and model scales
- Discovery cost: "$39.9 and 160 minutes"

### Lyra CLI Implications

- **Pre-collect reasoning trajectories** to avoid repeated expensive LLM calls
- **Implement probe signals** to guide branching decisions
- **Use execution traces** for iterative strategy improvement
- **Automate test-time compute allocation** rather than manual tuning

---

## Paper 4: Active Context Compression (arXiv:2601.07190)

**Author:** Nikhil Verma

### Key Contribution

**Focus Agent Architecture** - Agent-centric system where the agent autonomously decides when to compress context, inspired by slime mold exploration strategies.

### Technical Approach

**Autonomous Memory Management:**
- Agent actively consolidates key learnings into persistent "Knowledge" block
- Prunes raw interaction history on its own initiative
- Self-directed compressions when prompted

**Scaffold Design:**
- Optimized setup using persistent bash + string-replacement editor
- Matches industry best practices

### Evaluation Results

- **Dataset:** 5 context-intensive instances from SWE-bench Lite
- **Model:** Claude Haiku 4.5
- **Token Reduction:** 22.7% overall (14.9M → 11.5M tokens)
- **Accuracy:** Maintained identical performance (60% for both)
- **Compression Frequency:** 6.0 autonomous compressions per task
- **Peak Savings:** Up to 57% token reduction on individual instances

### Lyra CLI Implications

- **Agent-driven compression** rather than passive external summarization
- **Persistent knowledge blocks** for consolidated learnings
- **Aggressive compression prompting** to encourage self-regulation
- **Cost-aware agentic systems** without sacrificing performance

---

## Paper 5: OPENDEV (arXiv:2603.05344)

**Author:** Nghi D. Q. Bui  
**Date:** March 2026

### Key Contribution

**OPENDEV** - Open-source Rust-based CLI coding agent designed for terminal-native development.

### Novel Techniques

1. **Lazy Tool Discovery:** Dynamic tool loading rather than upfront registration
2. **Dual-Agent Architecture:** Separates planning responsibilities from execution tasks
3. **Adaptive Context Compaction:** Automatically reduces historical context to maintain reasoning quality
4. **Event-Driven System Reminders:** Counteracts "instruction fade-out" through automated prompts
5. **Automated Memory System:** Accumulates project-specific knowledge across sessions

### Architectural Patterns

- **Terminal-native design:** Operates directly in CLI environment
- **Compound AI system:** Multiple specialized models for different workloads
- **Explicit reasoning phases:** Enforced separation between planning and action
- **Context efficiency prioritization:** Core design principle throughout

### Implementation Details

- **Language:** Rust (for performance and safety)
- **Deployment:** Command-line interface
- **Focus:** Long-horizon autonomous development tasks

### Lyra CLI Implications

- **Rust implementation** for performance and safety
- **Lazy tool loading** to reduce upfront overhead
- **Dual-agent separation** of planning from execution
- **Event-driven reminders** to prevent instruction fade-out
- **Cross-session memory** for project-specific knowledge

---

## Paper 6: Darwin Gödel Machine (arXiv:2505.22954)

**Authors:** Jenny Zhang, Shengran Hu, Cong Lu, Robert Lange, Jeff Clune

### Key Contribution

**Self-improving AI system** that iteratively modifies its own code and validates changes empirically using coding benchmarks.

### Results

- SWE-bench performance: 20.0% → 50.0%
- Polyglot benchmark: 14.2% → 30.7%
- Outperforms baselines without self-improvement or open-ended exploration

### Novel Techniques

**Open-Ended Archive Evolution:**
- Maintains archive of generated coding agents
- Samples existing agent and creates "new, interesting, version"
- Forms growing tree enabling "parallel exploration of many different paths"

**Self-Modification Approach:**
- Agent modifies its own code, including "its ability to modify its own codebase"
- Empirical validation replaces formal proofs
- Inspired by Darwinian evolution and open-endedness research

### Emergent Capabilities

The system automatically developed:
- Better code editing tools
- Long-context window management
- Peer-review mechanisms

### Safety Measures

Experiments conducted with "sandboxing, human oversight"

### Lyra CLI Implications

- **Archive-based evolution** for maintaining agent variants
- **Empirical validation** over formal proofs
- **Self-modification capabilities** with safety sandboxing
- **Emergent tool development** through evolutionary pressure

**Repository:** github.com/jennyzzt/dgm

---

## Paper 7: Dive into Claude Code (arXiv:2604.05013)

**Authors:** Jiacheng Liu, Xiaohan Zhao, Xinyi Shang, Zhiqiang Shen

### Key Contribution

Comprehensive architectural analysis of Claude Code's TypeScript source code, mapping five human values to thirteen design principles and implementation choices.

### Core Architecture

**Central Loop:** "a simple while-loop that calls the model, runs tools, and repeats"

**Five Supporting Systems:**

1. **Permission System:** Seven modes with ML-based classifier for safety
2. **Context Management:** Five-layer compaction pipeline
3. **Extensibility:** Four mechanisms (MCP, plugins, skills, hooks)
4. **Delegation:** Subagent mechanism with worktree isolation
5. **Storage:** Append-oriented session storage

### Five Motivating Values

1. Human decision authority
2. Safety and security
3. Reliable execution
4. Capability amplification
5. Contextual adaptability

### Novel Techniques

- **ML-based permission classifier** for action safety evaluation
- **Worktree isolation** for subagent delegation
- **Five-layer compaction** for context window management
- **Multi-channel extensibility** through MCP/plugins/skills/hooks

### Claude Code vs OpenClaw Differences

- Safety: Per-action classification → Perimeter-level access control
- Runtime: Single CLI loop → Embedded gateway runtime
- Context: Window extensions → Gateway-wide capability registration

### Lyra CLI Implications

- **Simple core loop** with sophisticated supporting systems
- **ML-based safety classification** for autonomous operation
- **Multi-layer compaction** for context efficiency
- **Four extensibility channels** for different use cases
- **Worktree isolation** for safe subagent delegation

**Repository:** github.com/VILA-Lab/Dive-into-Claude-Code

---

## Paper 8: Memento (arXiv:2604.14228)

**Authors:** Huichi Zhou, Yihang Chen, Siyuan Guo, et al.

### Key Contribution

**Memory-based online reinforcement learning** for LLM agents that avoids fine-tuning the base model.

### Technical Approach

**Memory-augmented Markov Decision Process (M-MDP):**
- Formalizes agent learning with episodic memory storage
- Neural case-selection policy guides action decisions
- Memory can be differentiable or non-parametric

**Learning Mechanism:**
- Policy updates via "memory rewriting mechanism" based on environmental feedback
- Policy improvement through efficient memory retrieval
- No gradient updates to the underlying LLM

### Architecture Components

1. **Episodic Memory:** Stores past experiences
2. **Case-Selection Policy:** Neural network that decides which memories to use
3. **Memory Reading/Retrieval:** Accesses relevant past cases for current decisions
4. **Memory Rewriting:** Updates stored experiences based on outcomes

### Evaluation Results

**GAIA Benchmark:**
- 87.88% Pass@3 on validation (top-1 performance)
- 79.40% on test set

**DeepResearcher Dataset:**
- 66.6% F1 score
- 80.4% PM (Precision-Match)
- Case-based memory adds 4.7% to 9.6% absolute improvement on out-of-distribution tasks

### Practical Advantages

- Low computational cost compared to fine-tuning
- Continuous real-time learning capability
- Scalable for generalist agents
- Effective for "open-ended skill acquisition and deep research scenarios"

### Lyra CLI Implications

- **Episodic memory storage** for past experiences
- **Case-based retrieval** for decision-making
- **Memory rewriting** based on outcomes
- **No model fine-tuning required** for continuous learning

---

## Paper 9: Scaling Coding Agents via Atomic Skills (arXiv:2508.16153)

**Status:** ⚠️ **WITHDRAWN** (data errors discovered post-submission)

**Authors:** Yingwei Ma, Yue Liu, Xinlong Yang, et al.

### Core Concept

Training coding agents on **atomic skills** rather than composite tasks to improve generalization.

### Five Atomic Skills Identified

1. Code localization
2. Code editing
3. Unit-test generation
4. Issue reproduction
5. Code review

These skills are "basis vectors for complex software engineering tasks" that are "more generalizable and composable."

### Key Technique

**Joint Reinforcement Learning over atomic skills** - Training where "atomic skills are consistently improved without negative interference or trade-offs."

### Claimed Results (Invalid)

- 18.7% average performance improvement
- Improvements in atomic skills generalized to unseen composite tasks

### Lyra CLI Implications

Despite withdrawal, the **conceptual framework** remains valuable:
- **Decompose complex tasks** into atomic skills
- **Train/optimize skills independently** to avoid interference
- **Compose atomic skills** for complex software engineering tasks
- **Measure skill mastery** separately from task completion

---

## Engineering Post: Anthropic Context Engineering

**Source:** anthropic.com/engineering/effective-context-engineering-for-ai-agents

### Core Principle

"Find the _smallest possible_ set of high-signal tokens that maximize the likelihood of some desired outcome"

### Key Challenges

**Context Rot:** As token count increases, model recall accuracy decreases. LLMs have finite "attention budget" - transformer architecture creates n² pairwise relationships for n tokens, stretching attention thin at scale.

**Attention Scarcity:** Models trained on shorter sequences have less experience with long-range dependencies. Position encoding interpolation helps but degrades precision.

### System Prompt Design

Find the "Goldilocks zone" between:
- **Too rigid:** Hardcoded if-else logic creates brittleness
- **Too vague:** High-level guidance without concrete signals

**Best Practices:**
- Use XML tags or Markdown headers for structure
- Start minimal, add instructions based on failure modes
- Provide diverse canonical examples, not exhaustive edge cases

### Tool Design

- Self-contained with minimal functional overlap
- Return token-efficient information
- Clear, unambiguous parameters
- "If a human engineer can't definitively say which tool should be used in a given situation, an AI agent can't be expected to do better"

### Context Retrieval Strategies

**Just-in-time approach:** Maintain lightweight identifiers (file paths, queries, links) and load data dynamically via tools rather than pre-loading everything.

**Benefits:**
- Progressive disclosure through exploration
- Metadata provides behavioral signals (folder hierarchies, naming conventions, timestamps)
- Maintains focused working memory

**Trade-off:** Runtime exploration is slower than pre-computed retrieval. Hybrid strategies work best.

### Long-Horizon Techniques

**Compaction:** Summarize conversation history when approaching context limits. Tool result clearing is "safest lightest touch" form.

**Structured note-taking:** Agent writes persistent notes outside context window (NOTES.md, to-do lists) that get pulled back when needed. Enables multi-hour coherence.

**Sub-agent architectures:** Specialized agents handle focused tasks with clean contexts, return condensed summaries (1,000-2,000 tokens) to main coordinator agent. Effective for complex research requiring parallel exploration.

### Implementation Guidance

- Test minimal prompts with best available model first
- Tune compaction prompts on complex traces - maximize recall, then improve precision
- Choose technique based on task: compaction for conversational flow, note-taking for iterative development, multi-agent for complex analysis
- "Do the simplest thing that works" as capabilities rapidly improve

---

## Cross-Paper Synthesis

### Common Themes

#### 1. Context Efficiency as First-Class Constraint

**Papers:** OPENDEV, Active Context Compression, Dive into Claude Code, Anthropic Engineering

**Consensus:** Context window management is not an afterthought but a core architectural concern.

**Techniques:**
- Adaptive compaction (OPENDEV, Active Context Compression)
- Five-layer compaction pipeline (Claude Code)
- Agent-driven compression decisions (Active Context Compression)
- Just-in-time retrieval over pre-loading (Anthropic)
- Tool result clearing (Anthropic)

**Lyra Implementation:**
- Multi-layer compaction strategy
- Agent autonomy in compression decisions
- Lazy loading of context
- Persistent knowledge blocks outside context window

#### 2. Terminal-Native Tool Use Over Semantic Retrieval

**Papers:** Beyond Semantic Similarity, OPENDEV, Anthropic Engineering

**Consensus:** Direct corpus interaction with terminal tools outperforms semantic embeddings for agentic tasks.

**Techniques:**
- grep, ripgrep, ast-grep for code search
- Multi-step exploration over single retrieval
- Hypothesis refinement through iteration
- No offline indexing required

**Lyra Implementation:**
- Prioritize terminal-native search tools
- Enable multi-step corpus exploration
- Support iterative hypothesis refinement
- Avoid premature semantic indexing

#### 3. Self-Evolution and Continuous Learning

**Papers:** Agent-World, Darwin Gödel Machine, Memento, AutoTTS

**Consensus:** Agents should improve through experience without manual intervention.

**Techniques:**
- Archive-based evolution (Darwin Gödel Machine)
- Memory-based learning without fine-tuning (Memento)
- Automated strategy discovery (AutoTTS)
- Co-evolution of environments and policies (Agent-World)

**Lyra Implementation:**
- Episodic memory for past experiences
- Case-based retrieval for decisions
- Memory rewriting based on outcomes
- Archive of successful agent variants

#### 4. Separation of Planning from Execution

**Papers:** OPENDEV, Dive into Claude Code, AutoTTS

**Consensus:** Explicit separation improves reasoning quality and enables specialized optimization.

**Techniques:**
- Dual-agent architecture (OPENDEV)
- Controller synthesis over trajectories (AutoTTS)
- Subagent delegation with isolation (Claude Code)

**Lyra Implementation:**
- Separate planning and execution agents
- Worktree isolation for subagents
- Pre-collected trajectories for strategy synthesis

#### 5. Atomic Skill Decomposition

**Papers:** Scaling Coding Agents (withdrawn but conceptually valid), Memento

**Consensus:** Breaking complex tasks into atomic skills improves generalization.

**Atomic Skills for Coding Agents:**
1. Code localization
2. Code editing
3. Unit-test generation
4. Issue reproduction
5. Code review

**Lyra Implementation:**
- Identify atomic skills for research tasks
- Train/optimize skills independently
- Compose skills for complex workflows
- Measure skill mastery separately

#### 6. Safety Through Architecture

**Papers:** Dive into Claude Code, Darwin Gödel Machine, OPENDEV

**Consensus:** Safety is achieved through architectural patterns, not just prompting.

**Techniques:**
- ML-based permission classification (Claude Code)
- Worktree isolation (Claude Code)
- Sandboxing with human oversight (Darwin Gödel Machine)
- Strict safety controls (OPENDEV)

**Lyra Implementation:**
- Permission system with ML classification
- Filesystem isolation for risky operations
- Human-in-the-loop for critical decisions
- Audit trails for all actions

---

## Architectural Recommendations for Lyra CLI

### Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Lyra CLI Core Loop                       │
│  (Simple while-loop: call model → run tools → repeat)       │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Permission  │    │   Context    │    │ Extensibility│
│   System     │    │  Management  │    │   System     │
│              │    │              │    │              │
│ • ML-based   │    │ • 5-layer    │    │ • MCP        │
│   classifier │    │   compaction │    │ • Plugins    │
│ • 7 modes    │    │ • Agent-     │    │ • Skills     │
│              │    │   driven     │    │ • Hooks      │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Delegation  │    │   Storage    │    │    Memory    │
│   System     │    │   System     │    │   System     │
│              │    │              │    │              │
│ • Subagents  │    │ • Append-    │    │ • Episodic   │
│ • Worktree   │    │   oriented   │    │ • Case-based │
│   isolation  │    │ • Session    │    │ • Rewriting  │
│              │    │   storage    │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Implementation Priorities

#### Phase 1: Foundation (Immediate)

1. **Simple Core Loop**
   - Model call → tool execution → repeat
   - Minimal complexity in central orchestration

2. **Terminal-Native Tools**
   - Prioritize grep, ripgrep, ast-grep over semantic search
   - Enable multi-step corpus exploration
   - Support iterative hypothesis refinement

3. **Basic Context Management**
   - Tool result clearing (lightest touch)
   - Just-in-time loading over pre-loading
   - Lightweight identifiers (paths, queries)

#### Phase 2: Safety & Efficiency (Near-term)

4. **Permission System**
   - ML-based action classification
   - Seven permission modes
   - Audit trail for all actions

5. **Multi-Layer Compaction**
   - Agent-driven compression decisions
   - Persistent knowledge blocks
   - Adaptive historical pruning

6. **Dual-Agent Architecture**
   - Separate planning from execution
   - Worktree isolation for subagents
   - Clean context boundaries

#### Phase 3: Learning & Evolution (Medium-term)

7. **Episodic Memory System**
   - Store past experiences
   - Case-based retrieval
   - Memory rewriting based on outcomes

8. **Archive-Based Evolution**
   - Maintain successful agent variants
   - Empirical validation of changes
   - Parallel exploration of strategies

9. **Atomic Skill Framework**
   - Decompose research tasks into atomic skills
   - Independent skill optimization
   - Compositional task execution

#### Phase 4: Advanced Capabilities (Long-term)

10. **Self-Modification**
    - Agent modifies own code
    - Sandboxed validation
    - Human oversight for critical changes

11. **Automated Strategy Discovery**
    - Pre-collect reasoning trajectories
    - Controller synthesis over trajectories
    - Execution trace feedback

12. **Multi-Environment Training**
    - Dynamic task synthesis
    - Capability gap identification
    - Continuous learning loops

---

## Evaluation Metrics

### Context Efficiency

- **Token reduction:** Target 20-30% reduction without accuracy loss
- **Compression frequency:** Track autonomous compression decisions
- **Peak savings:** Measure maximum reduction on complex tasks

### Task Performance

- **Accuracy:** Maintain or improve on benchmarks
- **Generalization:** Performance on out-of-distribution tasks
- **Skill mastery:** Independent measurement of atomic skills

### System Reliability

- **Safety incidents:** Track permission violations
- **Context rot:** Monitor recall accuracy over long horizons
- **Tool success rate:** Measure terminal tool effectiveness

### Learning Capability

- **Improvement rate:** Track performance gains over time
- **Memory effectiveness:** Case-based retrieval accuracy
- **Strategy discovery:** Cost and time for new strategies

---

## Key Takeaways for Lyra CLI

### Do

1. **Prioritize context efficiency** from day one
2. **Use terminal-native tools** over semantic embeddings
3. **Separate planning from execution** with dual agents
4. **Enable agent-driven compression** decisions
5. **Implement episodic memory** for continuous learning
6. **Decompose tasks into atomic skills** for better generalization
7. **Use worktree isolation** for safe subagent delegation
8. **Build multi-layer compaction** pipeline
9. **Integrate MCP** for standardized tool interfaces
10. **Maintain archive of successful variants** for evolution

### Don't

1. **Don't pre-load everything** - use just-in-time retrieval
2. **Don't rely on single retrieval pass** - enable multi-step exploration
3. **Don't fine-tune base models** - use memory-based learning
4. **Don't hardcode strategies** - enable automated discovery
5. **Don't ignore safety** - build it into architecture
6. **Don't treat context as infinite** - manage it actively
7. **Don't optimize composite tasks** - focus on atomic skills
8. **Don't use passive summarization** - let agents drive compression
9. **Don't skip validation** - use empirical testing
10. **Don't build monolithic agents** - use specialized subagents

---

## References

1. Li, Z., et al. (2026). Beyond Semantic Similarity: Rethinking Retrieval for Agentic Search via Direct Corpus Interaction. arXiv:2605.05242

2. Dong, G., et al. (2026). Agent-World: Scaling Real-World Environment Synthesis for Evolving General Agent Intelligence. arXiv:2604.18292

3. Zheng, T., et al. (2026). LLMs Improving LLMs: Agentic Discovery for Test-Time Scaling. arXiv:2605.08083

4. Verma, N. (2026). Active Context Compression: Autonomous Memory Management in LLM Agents. arXiv:2601.07190

5. Bui, N. D. Q. (2026). Building Effective AI Coding Agents for the Terminal: Scaffolding, Harness, Context Engineering, and Lessons Learned. arXiv:2603.05344

6. Zhang, J., et al. (2025). Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents. arXiv:2505.22954

7. Liu, J., et al. (2026). Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems. arXiv:2604.05013

8. Zhou, H., et al. (2026). Memento: Fine-tuning LLM Agents without Fine-tuning LLMs. arXiv:2604.14228

9. Ma, Y., et al. (2026). Scaling Coding Agents via Atomic Skills. arXiv:2508.16153 [WITHDRAWN]

10. Anthropic. (2026). Effective Context Engineering for AI Agents. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

---

**Report compiled:** May 16, 2026  
**For:** Lyra CLI Development Team  
**Next steps:** Prioritize Phase 1 implementation based on architectural recommendations
