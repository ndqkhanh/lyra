# Alibaba-NLP/DeepResearch — Deep-Read

## 1. Headline Feature & Mechanism

**Tongyi DeepResearch** is an agentic large language model (30.5B total parameters, 3.3B activated per token) developed by Alibaba's Tongyi Lab, purpose-built for **long-horizon, deep information-seeking tasks**. It achieves SOTA across Humanity's Last Exam, BrowseComp, BrowseComp-ZH, WebWalkerQA, xbench-DeepSearch, FRAMES, and SimpleQA.

The core mechanism is a **ReAct agent loop**:

1. The model receives a question and a system prompt listing available tools (search, visit, google_scholar, PythonInterpreter, parse_file).
2. It produces `<think>` reasoning, then optionally emits `<tool_call>{"name": "...", "arguments": {...}}</tool_call>` with XML-delimited arguments.
3. The inference engine dispatches the tool call, appends `<tool_response>` observation, and feeds it back to the model.
4. When ready, the model emits `<answer>...</answer>` to conclude.

The model supports two inference modes:
- **ReAct (light)**: For rigorous evaluation of intrinsic abilities -- the open-sourced mode.
- **IterResearch (heavy)**: A test-time scaling strategy for maximum performance ceiling -- not yet fully open-sourced.

What makes this repo uniquely valuable is its **complete training pipeline disclosure**: a fully automated synthetic data generation pipeline for agentic pre-training, large-scale continual pre-training on agentic interaction data, and end-to-end on-policy RL via a customized GRPO (Group Relative Policy Optimization) framework with token-level policy gradients and leave-one-out advantage estimation.

## 2. Architecture & Core Modules

```
Alibaba-NLP__DeepResearch/
├── inference/                     # Core inference engine
│   ├── run_multi_react.py         # ENTRY POINT: Parallel ReAct inference
│   ├── react_agent.py             # MultiTurnReactAgent (agent loop)
│   ├── prompt.py                  # System prompt + tool definitions
│   ├── tool_search.py             # Web search via Serper.dev
│   ├── tool_visit.py              # Webpage reading via Jina.ai + LLM summarization
│   ├── tool_scholar.py            # Google Scholar via Serper.dev
│   ├── tool_python.py             # Sandboxed Python via SandboxFusion
│   ├── tool_file.py               # Multi-format file parser (PDF, DOCX, etc.)
│   ├── file_tools/                # Low-level file parsing (file_parser.py, video_agent.py)
│   ├── run_react_infer.sh         # 8-GPU VLLM deployment script
│   └── eval_data/                 # Example JSONL/JSON datasets
├── evaluation/                    # Benchmark evaluation
│   ├── evaluate_hle_official.py   # HLE evaluation (structured output judge)
│   ├── evaluate_deepsearch_official.py  # Multi-round evaluation (Pass@1, Pass@3)
│   └── prompt.py                  # Judge prompts (GAIA, BrowseComp, XBench)
├── WebAgent/                      # Sibling research family (18+ papers)
│   ├── WebDancer/                 # Search agent (NeurIPS 2025)
│   ├── WebSailor/                 # Complex reasoning web agent
│   ├── WebWatcher/                # Vision-language deep research agent
│   ├── WebShaper/                 # Data synthesis framework
│   ├── ParallelMuse/              # Parallel thinking for deep search
│   └── ...                        # 14+ more paper-code repositories
├── Agent/                         # Meta-agent research (AgentFounder, AgentScaler)
├── requirements.txt               # Python dependencies
├── LICENSE                        # Apache 2.0
└── README.md / FAQ.md             # Documentation
```

**Entry point**: `run_multi_react.py` uses `ThreadPoolExecutor(max_workers=20)` to run parallel ReAct loops. Each loop spins up a `MultiTurnReactAgent` that queries VLLM servers (ports 6001-6008, round-robin). Results streamed as JSONL files per rollout iteration.

**Data flow**: User question -> VLLM (tool-augmented generation) -> Tool response -> VLLM (next action) -> ... -> Final `<answer>`. The agent enforces a 150-minute timeout and 100 LLM-call limit. Token budget is 110K tokens for context; when exceeded, the model is forced to emit its best guess.

**Key dependencies**: `torch`, `transformers`, `vllm`, `qwen-agent`, `openai`, `sentencepiece`, `sandbox-fusion`, `tiktoken`, `litellm`, `fastapi`, `uvicorn`, `ray`, `apscheduler`, `dashscope` (Aliyun SDK). The model uses the Qwen-2.5 architecture family.

**Architecture pattern**: ReAct agent loop, with parallel inference orchestration, external API tools (Serper.dev for search, Jina.ai for page reading), and LLM-based summarization for page content extraction. Evaluation uses judge LLMs (o3-mini, GPT-4o, Gemini-2.0-flash) with structured output to grade correctness.

## 3. Performance/Benchmarks

From the repo's benchmark chart and paper:

| Benchmark | Tongyi-DeepResearch-30B-A3B | Notes |
|---|---|---|
| **Humanity's Last Exam (HLE)** | SOTA at time of release | Multi-step web research questions |
| **BrowseComp** | SOTA | English web competition |
| **BrowseComp-ZH** | SOTA | Chinese web competition |
| **WebWalkerQA** | SOTA | Web traversal benchmark |
| **xbench-DeepSearch** | SOTA | Deep search benchmark |
| **FRAMES** | SOTA | Factual retrieval |
| **SimpleQA** | SOTA | Simple question answering |

The model uses **3 rollout iterations** for evaluation, reporting Pass@3 and Best Pass@1 metrics. The evaluation judges answers using LLM-as-a-judge with structured output (Pydantic models for answer extraction and correctness classification).

The 30B-A3B architecture (30.5B total, 3.3B activated) means it achieves these results at **~10x inference efficiency** compared to dense 30B models.

## 4. Trade-offs

**Wins:**
- **MoE efficiency**: 30.5B total / 3.3B active = ~9:1 sparsity ratio, enabling dense-30B-quality at dense-3B compute cost.
- **Fully open pipeline**: Training methodology (pretraining data synthesis, SFT, RL) is fully documented in a tech report (arXiv 2510.24701) even if training data/code is not released.
- **Deep agent family**: 18+ companion papers create a comprehensive knowledge base for deep research agents.
- **Production ready**: Available on OpenRouter, Alibaba Cloud Bailian, and via local VLLM deployment.
- **Comprehensive tool ecosystem**: Web search, academic search, web page reading, Python sandbox, file parsing (including video/audio).

**Losses:**
- **Heavy mode not open-sourced**: The test-time scaling IterResearch mode that unlocks maximum performance is not released. Only the ReAct mode is available.
- **Training data not released**: Despite documenting the synthesis pipeline, no training data is published.
- **Chinese ecosystem dependencies**: Heavy reliance on Alibaba Cloud services (DashScope, Bailian, ModelScope) may create friction for Western developers.
- **Reproduction difficulty**: The FAQ explicitly states that reproducing paper results requires exact prompts and tools from the codebase, and the model is not general-purpose.
- **Cost**: Requires 8 GPUs (A100/H100) for the full VLLM deployment as shown in the run script.
- **API key proliferation**: Requires API keys from 4+ services (Serper, Jina, OpenAI, DashScope, SandboxFusion).

## 5. Design Rationale

The project makes several deliberate architectural choices:

1. **MoE over dense**: The 30B-A3B MoE architecture is chosen because deep research agents need broad knowledge (large total parameters) but benefit from fast inference (small active parameters). The 1:9 activation ratio lets them scale knowledge without proportional compute cost.

2. **Synthetic data over human annotation**: Agentic interaction data is expensive to collect from humans. The fully automated pipeline scales to millions of trajectories, covering agentic pre-training, SFT, and RL stages.

3. **On-policy RL with GRPO**: The custom GRPO variant (token-level PG, leave-one-out advantage, negative sample filtering) addresses the non-stationary environment problem in agent RL -- where policy changes affect both action selection AND the observations received.

4. **ReAct over function-calling**: The model uses a ReAct-style loop with XML tags rather than OpenAI-style function calling or tool-use API. This provides a simpler, more transparent action space that is easier to train and debug.

5. **Parallel inference over sequential**: The run_multi_react.py uses ThreadPoolExecutor to process multiple questions simultaneously, with sticky port assignment (same question -> same VLLM port) to maintain KV cache benefits across rollout iterations.

6. **External API tools over in-model reasoning**: Search and page reading are delegated to external services (Serper, Jina) rather than being handled by the model itself. The model focuses on reasoning, planning, and synthesis.

## 6. Transfer to Lyra

**Most transferable idea: Automated Synthetic Data Pipeline for Agentic Training**

The most impactful idea for Lyra is the **fully automated synthetic data generation pipeline** that powers the three training stages (agentic pre-training, SFT, RL). Tongyi DeepResearch's pipeline uses a task formalization approach (detailed in their WebShaper paper) where agentic tasks are decomposed into formal schemas, and synthetic trajectories are generated iteratively with validation.

For Lyra, this translates to: build an automated pipeline that generates diverse agent-environment interaction trajectories for Lyra's specific domains (code generation, testing, deployment automation), then use these trajectories for continuous fine-tuning via RL (GRPO variant).

Additionally, the **ReAct tool-use protocol with XML tags** is a clean, debuggable pattern that Lyra's command/plugin system could adopt for tool orchestration.

**Workstream route**: 7.4-TrainingPipeline (RL/GRPO for agent optimization) or 7.1-DataPipeline (synthetic data generation for agentic interactions). The ReAct loop architecture maps to §4.4 (Router/Orchestrator).

**Impact**: 8/10 -- Synthetic data pipeline is the critical bottleneck for agent improvement.
**Effort**: 6/10 -- Building the pipeline is well-understood; the challenge is domain adaptation.
**Tier**: Foundation (the synthetic data approach is foundational to any agent improvement cycle; it enables downstream work but is not itself a user-facing feature).

**LICENSE**: Apache 2.0 -- fully permissive for both commercial and research use. No restrictions on derivative works.
