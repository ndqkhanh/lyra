# Lyra — Reference Papers

Local mirror of the arxiv papers that inform [`docs/novel-ideas.md`](../docs/novel-ideas.md).
Pulled on 2026-04-24 from arxiv (PDFs only). 22 papers, ~145 MB total.

## Wave 1 — original eight selling points (§3 of `novel-ideas.md`)

| File | arxiv ID | Title | Authors / Org | Year |
|---|---|---|---|---|
| `meta-tts-agentic-coding.pdf` | [2604.16529](https://arxiv.org/abs/2604.16529) | Scaling Test-Time Compute for Agentic Coding | Kim, Yang, Niu, Zhang, Zhu, Helenowski, Silva, Chen, Iyer, Zaheer, Fried, Hajishirzi, Arora, Synnaeve, Salakhutdinov, Goyal — Meta Superintelligence Labs / UW / NYU / Google DeepMind / CMU / Princeton | 2026 |
| `ngc-neural-garbage-collection.pdf` | [2604.18002](https://arxiv.org/abs/2604.18002) | Neural Garbage Collection: Learning to Forget while Learning to Reason | Li, Hamid, Fox, Goodman — Stanford | 2026 |
| `skill-rag.pdf` | [2604.15771](https://arxiv.org/abs/2604.15771) | Skill-RAG — Hidden-State Probing + 4-skill Recovery Router | Univ. of Michigan / Univ. of Pennsylvania | 2026 |
| `knowrl.pdf` | [2506.19807](https://arxiv.org/abs/2506.19807) | KnowRL: Exploring Knowledgeable Reinforcement Learning for Factuality | Zhejiang University | 2025 |
| `reasoningbank-mattS.pdf` | [2509.25140](https://arxiv.org/abs/2509.25140) | ReasoningBank — Scaling Agent Self-Evolving with Reasoning Memory + MaTTS | Google Research | 2025 |
| `poisonedrag.pdf` | [2402.07867](https://arxiv.org/abs/2402.07867) | PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of LLMs | (USENIX Security 2025) | 2024 |
| `semaclaw-midea-airc.pdf` | [2604.11548](https://arxiv.org/abs/2604.11548) | SemaClaw: A Step Towards General-Purpose Personal AI Agents through Harness Engineering | Midea AIRC | 2026 |

## Wave 2 — performance edges (§9 of `novel-ideas.md`)

| File | arxiv ID | Title | Authors / Org | Year |
|---|---|---|---|---|
| `swe-search-mcts.pdf` | [2410.20285](https://arxiv.org/abs/2410.20285) | SWE-Search: Enhancing Software Agents with Monte Carlo Tree Search and Iterative Refinement (ICLR 2025) | Antoniades et al. | 2024 / 2025 |
| `alphaevolve.pdf` | [2506.13131](https://arxiv.org/abs/2506.13131) | AlphaEvolve: A coding agent for scientific and algorithmic discovery | Novikov et al. — Google DeepMind | 2025 |
| `frugalgpt.pdf` | [2305.05176](https://arxiv.org/abs/2305.05176) | FrugalGPT: How to Use LLMs While Reducing Cost and Improving Performance | Chen, Zaharia, Zou — Stanford | 2023 |
| `routellm.pdf` | [2406.18665](https://arxiv.org/abs/2406.18665) | RouteLLM: Learning to Route LLMs with Preference Data | Ong et al. — UC Berkeley / LMSYS | 2024 |
| `confidence-driven-llm-router.pdf` | [2502.11021](https://arxiv.org/abs/2502.11021) | Confidence-Driven LLM Router | (2025 follow-up to RouteLLM) | 2025 |
| `voyager.pdf` | [2305.16291](https://arxiv.org/abs/2305.16291) | Voyager: An Open-Ended Embodied Agent with Large Language Models (TMLR 2024) | Wang et al. — NVIDIA / Caltech / UT Austin | 2023 / 2024 |
| `reflexion.pdf` | [2303.11366](https://arxiv.org/abs/2303.11366) | Reflexion: Language Agents with Verbal Reinforcement Learning (NeurIPS 2023) | Shinn et al. — Northeastern / MIT | 2023 |
| `metagpt.pdf` | [2308.00352](https://arxiv.org/abs/2308.00352) | MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework | Hong et al. | 2023 / 2024 |
| `chatdev.pdf` | [2307.07924](https://arxiv.org/abs/2307.07924) | ChatDev: Communicative Agents for Software Development | Qian et al. — Tsinghua / OpenBMB | 2023 / 2024 |
| `dspy.pdf` | [2310.03714](https://arxiv.org/abs/2310.03714) | DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines (ICLR 2024) | Khattab et al. — Stanford | 2023 / 2024 |
| `eagle3-spec-decoding.pdf` | [2503.01840](https://arxiv.org/abs/2503.01840) | EAGLE-3: Scaling up Inference Acceleration of LLMs via Training-Time Test | Li et al. | 2025 |
| `osworld.pdf` | [2404.07972](https://arxiv.org/abs/2404.07972) | OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments (NeurIPS 2024) | Xie et al. | 2024 |
| `gdpval.pdf` | [2510.04374](https://arxiv.org/abs/2510.04374) | GDPval: Evaluating AI Model Performance on Real-World Economically Valuable Tasks | OpenAI | 2025 |
| `qwen-process-reward-lessons.pdf` | [2501.07301](https://arxiv.org/abs/2501.07301) | The Lessons of Developing Process Reward Models in Mathematical Reasoning | Qwen team | 2025 |

## Wave 3 — Diversity-Collapse Hardening (§10A of `novel-ideas.md`)

| File | arxiv ID | Title | Authors / Org | Year |
|---|---|---|---|---|
| `diversity-collapse-mas.pdf` | [2604.18005](https://arxiv.org/abs/2604.18005) | Diversity Collapse in Multi-Agent LLM Systems: Structural Coupling and Collective Failure in Open-Ended Idea Generation (**ACL 2026 Findings**) | Chen, Tong, Yang, He, Zhang, Zou, Wang, He — NUS / CUHK-Shenzhen | 2026 |

> Companion analysis: [`../docs/research/diversity-collapse-analysis.md`](../docs/research/diversity-collapse-analysis.md). Code: <https://github.com/Xtra-Computing/MAS_Diversity>.

## Other primary sources (link-only)

### Wave 1
- **Harness Engineering talk** — Ryan Leopo (OpenAI), 2026 — "Code is Free / scarce resources are Human Time, Attention, Context Window".
- **CubeSandbox** — [`TencentCloud/CubeSandbox`](https://github.com/TencentCloud/CubeSandbox), Apache-2.0, Rust 52 % / Go 26 % / C 18 %. RustVMM + KVM microVM, sub-60 ms cold start, <5 MB RAM/instance, eBPF-based egress (CubeVS), E2B SDK drop-in. Released April 2026.
- **Phantom** — [`ghostwright/phantom`](https://github.com/ghostwright/phantom), Apache-2.0, ~1.3 k stars. Persistent autonomous AI co-worker on a dedicated VM with self-evolution loop and 17+ MCP tools.
- **Moraine** — [`eric-tramel/moraine`](https://github.com/eric-tramel/moraine). "Unified realtime agent trace database & search MCP." Cross-harness traceability surface.
- **GBrain v0.12** — Self-wiring knowledge graph announced by Garry Tan (April 2026). Stated deltas: +5 % precision, +11 % recall, +28 % graph search, −53 % noise.
- **SemaClaw codebase** — [`midea-ai/SemaClaw`](https://github.com/midea-ai/SemaClaw), TypeScript reference implementation paired with the paper above.

### Wave 2
- **SWE-Search reference impl** — [`aorwall/moatless-tree-search`](https://github.com/aorwall/moatless-tree-search), Apache-2.0. Streamlit demo + video.
- **SWE-RL** — [`facebookresearch/swe-rl`](https://github.com/facebookresearch/swe-rl), NeurIPS 2025. RL-on-software-evolution with rule-based rewards (search/replace + unidiff similarity). Stretch §11.3.
- **SWE-Lancer benchmark** — [`openai/SWELancer-Benchmark`](https://github.com/openai/SWELancer-Benchmark). $1 M of real Upwork tasks; Diamond split ($500 K) is open-source with a unified Docker image.
- **τ-bench / τ³-bench** — [`sierra-research/tau2-bench`](https://github.com/sierra-research/tau2-bench). Airline / retail / telecom / banking / voice. Even GPT-4 < 50 % pass-1, ~25 % pass-8.
- **Terminal-Bench 2.0** — [t-bench.com](https://t-bench.com/) and [`harbor-framework/terminal-bench-2`](https://github.com/harbor-framework/terminal-bench-2). 89 hard CLI tasks. Used by all frontier labs.
- **Voyager codebase** — [`MineDojo/Voyager`](https://github.com/MineDojo/Voyager). Open-source automatic curriculum + skill library + iterative prompting.
- **DSPy** — [`stanfordnlp/dspy`](https://github.com/stanfordnlp/dspy). Stanford compiler for LM pipelines. Stretch §11.2.
- **MetaGPT** — [`geekan/MetaGPT`](https://github.com/geekan/MetaGPT). Reference framework for the SOP-driven Org Mode (§9.3).
- **ChatDev** — [`OpenBMB/ChatDev`](https://github.com/OpenBMB/ChatDev). Reference framework for the role-driven Org Mode (§9.3).
- **PRM800K** — [`openai/prm800k`](https://github.com/openai/prm800k). 800 k step-level correctness labels.
- **Anthropic Skills** — [`anthropics/skills`](https://github.com/anthropics/skills) and [`skills-mcp/skills-mcp`](https://github.com/skills-mcp/skills-mcp). MCP-portable skill registry pattern.
- **DeepSeek-R1** — [`deepseek-ai/DeepSeek-R1`](https://github.com/deepseek-ai/DeepSeek-R1). MIT-licensed RL-trained reasoning model used as a default "thinking" profile.
- **EAGLE-3 weights** — `yuhuili/EAGLE3-LLaMA3.3-Instruct-70B` (HF). Validated draft head for Llama 3.3 70B.

### Industry signals (April 2026)
- **OpenAI GPT-5.5** — 82.7 % on Terminal-Bench 2.0, 84.9 % on GDPval ([release coverage](https://www.marktechpost.com/2026/04/23/openai-releases-gpt-5-5-a-fully-retrained-agentic-model-that-scores-82-7-on-terminal-bench-2-0-and-84-9-on-gdpval/)).
- **Z.AI GLM-5.1** — 754 B open-weight, SOTA on SWE-bench Pro, **8-hour autonomous execution** ([release coverage](https://www.marktechpost.com/2026/04/08/z-ai-introduces-glm-5-1-an-open-weight-754b-agentic-model-that-achieves-sota-on-swe-bench-pro-and-sustains-8-hour-autonomous-execution/)).
- **OSS coding-agent stars (April 2026)** — Cline ~58 k, Aider ~39 k, OpenHands ~65 k. Self-host is mainstream.

## Reproducing the download

```bash
mkdir -p projects/lyra/papers && cd projects/lyra/papers
ids=(
  # Wave 1
  "2604.16529:meta-tts-agentic-coding"
  "2604.18002:ngc-neural-garbage-collection"
  "2604.15771:skill-rag"
  "2506.19807:knowrl"
  "2509.25140:reasoningbank-mattS"
  "2402.07867:poisonedrag"
  "2604.11548:semaclaw-midea-airc"
  # Wave 2
  "2410.20285:swe-search-mcts"
  "2506.13131:alphaevolve"
  "2305.05176:frugalgpt"
  "2406.18665:routellm"
  "2502.11021:confidence-driven-llm-router"
  "2305.16291:voyager"
  "2303.11366:reflexion"
  "2308.00352:metagpt"
  "2307.07924:chatdev"
  "2310.03714:dspy"
  "2503.01840:eagle3-spec-decoding"
  "2404.07972:osworld"
  "2510.04374:gdpval"
  "2501.07301:qwen-process-reward-lessons"
  # Wave 3
  "2604.18005:diversity-collapse-mas"
)
for pair in "${ids[@]}"; do
  id="${pair%%:*}"; name="${pair##*:}"
  curl -fsSL "https://arxiv.org/pdf/${id}" -o "${name}.pdf"
done
```

## How to use these

Read in this order if you want the full design narrative:

**Wave 1 (capabilities):**

1. **SemaClaw** — the harness-engineering frame (validates Lyra's bet).
2. **Meta TTS for Agentic Coding** — the test-time-scaling story.
3. **ReasoningBank + MaTTS** — the memory side of the same coin.
4. **Skill-RAG** — failure-aware retrieval routing.
5. **NGC** — what to forget while reasoning.
6. **KnowRL** — factuality reward for reasoning steps.
7. **PoisonedRAG** — the attack surface every harness has to defend.

**Wave 2 (performance edges):**

8.  **SWE-Search** — intra-attempt MCTS, +23 % SWE-bench across 5 models.
9.  **FrugalGPT → RouteLLM → Confidence-Driven Router** — three-step evolution of the cascade-routing idea.
10. **MetaGPT** then **ChatDev** — assembly-line and waterfall multi-agent SDLC for the Org Mode.
11. **Voyager** — automatic curriculum + skill library; the missing planner on top of Skill-Creator v2.
12. **PRM800K → Math-Shepherd → Qwen2.5-Math-PRM lessons** — process-reward models grow up.
13. **OSWorld** — what a real computer-use benchmark looks like (12 % best agent vs 72 % human — wide-open headroom).
14. **GDPval** — the OpenAI economic-value benchmark; the new bar.
15. **EAGLE-3** — speculative decoding; the silent ×6 speedup for self-host profiles.

**Wave 3 (cross-cutting hardening):**

16. **Diversity Collapse in Multi-Agent LLM Systems** — ACL 2026 Findings; the failure mode every multi-agent harness has to defend, and the structural prescription (NGT + Subgroups + Vertical persona mix) Lyra adopts as a default. Companion analysis: [`../docs/research/diversity-collapse-analysis.md`](../docs/research/diversity-collapse-analysis.md).

**Stretch / context:**

17. **Reflexion** — the verbal-RL ancestor of ReasoningBank.
18. **DSPy** — programmatic LM-pipeline compilation (§11.2 stretch).
19. **AlphaEvolve** — DeepMind's evolutionary coding agent; long-tail inspiration for sample-and-rank-with-verifier.

Each paper is cited inline in `docs/novel-ideas.md` with the specific section that adopts it.
