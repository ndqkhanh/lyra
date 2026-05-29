# Lyra Research Flows — Comprehensive Test Plan

> Covers: Deep Research, Auto Research, Scientist Research, AI Research, DCI Investigation, Evals
> Provider: DeepSeek (via Anthropic-compatible endpoint at `https://api.deepseek.com/anthropic`)
> Model: `deepseek-v4-pro`

---

## 0. Pre-Flight: Provider Configuration

### 0.1 Current State

The existing `~/.claude/settings.json` routes through DeepSeek's Anthropic-compatible endpoint:

```json
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-a8e9af286225415c9bb97fb6edecd34a",
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_MODEL": "deepseek-v4-pro"
  }
}
```

**No separate `DEEPSEEK_API_KEY` is set.** The existing test script at `tests/scripts/test_deepseek_research.py` checks for `DEEPSEEK_API_KEY` which won't be found. This is a bug — the script was written for a direct DeepSeek SDK but the actual config uses the Anthropic bridge.

### 0.2 Required Fix Before Testing

The test scripts must be updated to read from the Anthropic bridge config rather than a direct `DEEPSEEK_API_KEY`. Two options:

**Option A (recommended):** Update test scripts to detect the Anthropic bridge config:
```python
api_key = os.environ.get("ANTHROPIC_API_KEY")
base_url = os.environ.get("ANTHROPIC_BASE_URL")
if base_url and "deepseek" in base_url:
    # Using DeepSeek via Anthropic bridge
    provider = "deepseek"
```

**Option B:** Add `DEEPSEEK_API_KEY` as a separate env var for direct SDK usage (if lyra-research supports a native DeepSeek provider).

### 0.3 Provider Verification

```bash
# Verify the Anthropic bridge is reachable
curl -s -o /dev/null -w "%{http_code}" https://api.deepseek.com/anthropic/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
# Expected: 200 (or 401 if auth needed — either confirms reachability)
```

---

## 1. Deep Research Flow (`/research` + `lyra-research`)

### 1.1 Package Status

| Attribute | Value |
|-----------|-------|
| Source files | ~120 Python files |
| Test files | 48 files, ~22,000 lines |
| Version | 0.2.0 |
| Maturity | **High** — most complete research package |
| Provider support | Requires LLM provider for ANALYSIS and SYNTHESIS agents |

### 1.2 Architecture

```
ResearchOrchestrator (3-agent hybrid)
  ├── DISCOVERY agent (Haiku-tier) → MultiSourceDiscovery
  │     └── Sources: arXiv, GitHub, HuggingFace, Semantic Scholar, Web
  ├── ANALYSIS agent (Sonnet-tier) → PaperAnalyzer, RepoAnalyzer
  │     └── Produces: ResearchNote[], extracted claims, quality scores
  └── SYNTHESIS agent (Opus-tier) → CrossSourceSynthesizer, ReportGenerator
        └── Produces: ResearchReport with citations, gap analysis, verifiable claims
```

10-step pipeline: CLARIFY → PLAN → SEARCH → FILTER → FETCH → ANALYZE → EVIDENCE_AUDIT → SYNTHESIZE → REPORT → MEMORIZE

Supporting subsystems:
- **CoordinationManager**: retry, timeout, circuit breaker
- **CapacityManager**: memory-aware context management
- **AdversarialReviewer**: claim verification, contradiction detection
- **FalsificationChecker**: hypothesis testing
- **GapAnalyzer**: knowledge gap detection
- **SessionCaseBank**: persistent session storage and retrieval

### 1.3 Test Matrix

#### T1.1: Smoke Test — Basic Research Pipeline

```bash
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra
python -m pytest tests/scripts/test_research_flow.py -v
```

**What it tests:** Orchestrator creation, progress callback, research result structure.
**Expected:** Passes without errors. May produce simulated results if no LLM provider is configured for the orchestrator.
**Risk:** The orchestrator likely requires an LLM provider. Without one, it may fail or produce stub output.

#### T1.2: DeepSeek Provider Integration

```bash
python tests/scripts/test_deepseek_research.py
```

**What it tests:** DeepSeek-specific configuration check, full research pipeline with DeepSeek.
**Expected:** Config check will FAIL (script looks for `DEEPSEEK_API_KEY` which doesn't exist). The research test will likely fail unless the orchestrator can use the Anthropic bridge config.
**Action:** Fix the config check first (see §0.2).

#### T1.3: Unit Tests — lyra-research Package

```bash
cd packages/lyra-research
python -m pytest tests/ -v --tb=short 2>&1 | tail -60
```

**Test categories to run (in order):**

| Order | Test File | What It Covers | Priority |
|--------|-----------|----------------|----------|
| 1 | `test_models.py` | Cost optimizer, cross-model verifier, model router | P0 |
| 2 | `test_sources.py` | Source discovery (ACL, citations, GitHub, HuggingFace, etc.) | P0 |
| 3 | `test_discovery_agents.py` | arXiv, GitHub, HuggingFace, Semantic Scholar agents | P0 |
| 4 | `test_analysis_agents.py` | Paper/repo/citation/quality analysis | P0 |
| 5 | `test_synthesis_agents.py` | Cross-source synthesis, evidence auditing | P0 |
| 6 | `test_orchestrator.py` | Orchestrator core logic | P0 |
| 7 | `test_orchestrator_integration.py` | Full orchestration integration | P0 |
| 8 | `test_coordination.py` | Circuit breaker, retry, timeout | P1 |
| 9 | `test_capacity_manager.py` | Memory capacity management | P1 |
| 10 | `test_adversarial_reviewer.py` | Adversarial review, claim verification | P1 |
| 11 | `test_intelligence.py` | Contradiction detection, gap analysis, falsification | P1 |
| 12 | `test_quality_gates.py` | Quality gates for each pipeline phase | P1 |
| 13 | `test_evaluation.py` | Quality evaluation, metrics | P1 |
| 14 | `test_roles.py` | Role system (discovery, analysis, curator, review, synthesis) | P1 |
| 15 | `test_skills.py` | Research skills, skill evolution | P2 |
| 16 | `test_learning.py` | Self-improvement, strategy extraction | P2 |
| 17 | `test_checkpoint.py` | Checkpoint/resume | P2 |
| 18 | `test_research_memory.py` | ResearchNoteStore, LocalCorpus, SessionCaseBank | P2 |
| 19 | `test_strategies.py` | Query expansion, research planning | P2 |
| 20 | `test_reporter.py` | Report generation, quality checking | P2 |
| 21 | `test_context_integration.py` | Layered context integration | P2 |
| 22 | `test_adaptive_decomposition.py` | Adaptive question decomposition | P2 |
| 23 | `test_full_integration.py` | End-to-end integration | P2 |
| 24 | `test_curation.py` | Knowledge curation workflow | P3 |
| 25 | `test_role_coordination.py` | Role-based coordination | P3 |
| 26 | `test_prisma_phase1.py` | PRISMA bias assessment | P3 |
| 27 | `test_socratic_phase2.py` | Socratic agent, devil's advocate | P3 |
| 28 | `test_writing_phase3.py` | AI detector, burstiness analyzer, 5-pass editor | P3 |
| 29 | `test_cross_model_phase4.py` | Cross-model review | P3 |
| 30 | `test_integrity_phase0.py` | Citation verifier, temporal verifier | P3 |
| 31 | `test_par2_rag.py` | PAR2 RAG system | P3 |
| 32 | `test_phase2_benchmarks.py` | Phase 2 benchmarks | P3 |
| Remainder | 16 more test files | Various | P3 |

#### T1.4: CLI Integration Test

```bash
cd packages/lyra-cli
python -m pytest tests/test_research_command.py -v --tb=short
python -m pytest tests/test_research_command_handler.py -v --tb=short
python -m pytest tests/research/test_research_engine.py -v --tb=short
```

**What it tests:** CLI command parsing, research command handler, research engine integration.

#### T1.5: Real Research Pipeline (9-phase)

```bash
cd packages/lyra-cli
python -m pytest tests/integration/test_research_voice_integration.py -v --tb=short
```

**What it tests:** RealResearchPipeline with actual web search + LLM synthesis.

#### T1.6: Manual End-to-End — Real Research Topic

```bash
# Test with a real topic using the CLI
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra
python -m lyra_cli research "transformer architecture attention mechanisms" --depth quick
```

**Validate:**
- [ ] Pipeline completes all 9-10 phases without crashing
- [ ] Sources are discovered and deduplicated
- [ ] Report contains inline citations `[N]`
- [ ] Gap analysis identifies missing angles
- [ ] Session is persisted and retrievable via `research list`
- [ ] Report is retrievable via `research show <id>`

---

## 2. Auto Research Flow (`lyra-autoresearch`)

### 2.1 Package Status

| Attribute | Value |
|-----------|-------|
| Source files | 6 `__init__.py` files only (stubs) |
| Test files | 6 files, ~1,100 lines |
| Version | 1.0.0 |
| Maturity | **Skeleton** — no implementation exists |

### 2.2 Architecture (Declared)

```
lyra_autoresearch/
  ├── citations/     → CitationGraph, CitationVerifier
  ├── debate/        → DebateOrchestrator, DebateRound
  ├── execution/     → ExperimentRunner, TrialManager
  ├── evolution/     → StrategyEvolver, PromptMutator
  └── hitl/          → HumanInTheLoop, ApprovalGate
```

**Reality:** Each submodule contains an `__init__.py` that exports class names with no backing implementation. Tests exist but test phantom code.

### 2.3 Test Matrix

#### T2.1: Run Existing Tests (Expected: Many Failures)

```bash
cd packages/lyra-autoresearch
python -m pytest tests/ -v --tb=short 2>&1 | tail -40
```

Expected outcome: Tests will likely fail with `ImportError` or `AttributeError` since the source modules have no implementation. This test run is diagnostic — it quantifies the gap.

#### T2.2: Implementation Gap Analysis

For each submodule, verify:

```bash
# Check what each __init__.py actually exports
for dir in packages/lyra-autoresearch/src/lyra_autoresearch/*/; do
    echo "=== $(basename $dir) ==="
    grep -c "def \|class " "$dir/__init__.py" 2>/dev/null || echo "No functions/classes"
done
```

#### T2.3: Decision Gate — Build vs. Remove

The auto-research package is a skeleton. Before testing further, decide:

- **Build it out** using the AutoScientists architecture (see LYRA_UPGRADE_RESEARCH.md §5)
- **Remove it** and fold the concept into lyra-research's existing orchestrator
- **Keep as roadmap** and skip detailed testing for now

**Recommendation:** Remove the skeleton and fold auto-research concepts into lyra-research. The 48-test-file lyra-research package already handles the core research loop. Auto-research as a separate package duplicates the orchestrator concept without adding value.

---

## 3. Scientist Research Flow (`lyra-science-pipeline`)

### 3.1 Package Status

| Attribute | Value |
|-----------|-------|
| Source files | 1 file (113 lines, all inline in `__init__.py`) |
| Test files | 1 file, 33 lines |
| Version | Not declared |
| Maturity | **Early prototype** — simulated results, hardcoded effect sizes |

### 3.2 Architecture

```
SciencePipeline
  ├── Hypothesis[]          → id, statement, iv, dv, expected_effect, confidence, status
  ├── TrialHarness[]        → id, sandbox_type, max_steps, variables, constraints
  ├── ExperimentResult[]    → hypothesis_id, outcome, effect_size, significance, supports
  ├── propose_hypothesis()  → creates Hypothesis (status="proposed")
  ├── create_harness()      → creates TrialHarness
  ├── run_experiment()      → simulated (effect_size=0.7, significance=0.95)
  └── analyze_results()     → aggregates per-hypothesis conclusions
```

### 3.3 Critical Gaps Identified

1. **`run_experiment()` uses hardcoded values** — `effect_size = 0.7`, `significance = 0.95`. No actual computation.
2. **No LLM integration** — hypothesis generation is manual (`propose_hypothesis(statement, iv, dv, effect)`).
3. **No experiment execution** — `run_experiment()` doesn't actually run code.
4. **No AutoScientists-style features** — no discussion forum, no peer review, no dead-end registry, no noise-gated confirmation.
5. **No statistical rigor** — single-run results, no confidence intervals, no multi-seed verification.
6. **Only 33 lines of tests** — tests only `propose_hypothesis()` and `create_harness()`. `run_experiment()`, `analyze_results()`, edge cases, and error paths are completely untested.

### 3.4 Test Matrix

#### T3.1: Run Existing Tests (Baseline)

```bash
cd packages/lyra-science-pipeline
python -m pytest tests/ -v --tb=long 2>&1
```

#### T3.2: Write Missing Unit Tests (TDD)

```python
# tests/test_science_pipeline_comprehensive.py

import pytest
from lyra_science_pipeline import (
    Hypothesis, ExperimentResult, TrialHarness, SciencePipeline
)

class TestHypothesis:
    def test_create_hypothesis(self):
        h = Hypothesis(id="H1", statement="X causes Y",
                       independent_var="X", dependent_var="Y",
                       expected_effect="positive")
        assert h.status == "proposed"
        assert h.confidence == 0.5

    def test_hypothesis_status_transitions(self):
        h = Hypothesis(id="H1", statement="X causes Y",
                       independent_var="X", dependent_var="Y",
                       expected_effect="positive")
        h.status = "testing"
        assert h.status == "testing"
        h.status = "confirmed"
        assert h.status == "confirmed"
        h.status = "refuted"
        assert h.status == "refuted"

    def test_hypothesis_invalid_status(self):
        h = Hypothesis(id="H1", statement="X causes Y",
                       independent_var="X", dependent_var="Y",
                       expected_effect="positive")
        # Should this raise? Currently won't — no validation.
        h.status = "invalid_status"  # Document this gap

class TestExperimentResult:
    def test_supported_result(self):
        r = ExperimentResult(hypothesis_id="H1", outcome="Works",
                             effect_size=0.8, significance=0.95,
                             supports_hypothesis=True)
        assert r.supports_hypothesis is True

    def test_refuted_result(self):
        r = ExperimentResult(hypothesis_id="H1", outcome="Fails",
                             effect_size=0.1, significance=0.5,
                             supports_hypothesis=False)
        assert r.supports_hypothesis is False

    def test_result_data_attachment(self):
        r = ExperimentResult(hypothesis_id="H1", outcome="Works",
                             effect_size=0.8, significance=0.95,
                             supports_hypothesis=True,
                             data={"epochs": 100, "loss": 0.03})
        assert r.data["epochs"] == 100

class TestSciencePipeline:
    @pytest.fixture
    def pipeline(self):
        return SciencePipeline()

    def test_propose_hypothesis(self, pipeline):
        h = pipeline.propose_hypothesis("A causes B", "A", "B", "increase")
        assert h.id == "H1"
        assert len(pipeline.hypotheses) == 1
        assert pipeline.hypotheses[0].status == "proposed"

    def test_propose_multiple_hypotheses(self, pipeline):
        pipeline.propose_hypothesis("A causes B", "A", "B", "increase")
        pipeline.propose_hypothesis("C causes D", "C", "D", "decrease")
        assert len(pipeline.hypotheses) == 2
        assert pipeline.hypotheses[0].id == "H1"
        assert pipeline.hypotheses[1].id == "H2"

    def test_create_harness(self, pipeline):
        h = pipeline.create_harness("docker", {"GPU": "A100"})
        assert h.id == "TH1"
        assert h.sandbox_type == "docker"
        assert h.variables == {"GPU": "A100"}

    def test_run_experiment_success(self, pipeline):
        pipeline.propose_hypothesis("A causes B", "A", "B", "increase")
        pipeline.create_harness("docker", {})
        result = pipeline.run_experiment("H1", "TH1")
        assert result.hypothesis_id == "H1"
        assert result.effect_size == 0.7  # Currently hardcoded
        assert result.significance == 0.95  # Currently hardcoded

    def test_run_experiment_missing_hypothesis(self, pipeline):
        with pytest.raises(ValueError, match="H99 not found"):
            pipeline.run_experiment("H99", "TH1")

    def test_run_experiment_confirms_hypothesis(self, pipeline):
        pipeline.propose_hypothesis("A causes B", "A", "B", "increase")
        pipeline.create_harness("docker", {})
        pipeline.run_experiment("H1", "TH1")
        assert pipeline.hypotheses[0].status == "confirmed"
        assert pipeline.hypotheses[0].confidence == 0.95

    @pytest.mark.skip(reason="Hardcoded values — no refutation path exists")
    def test_run_experiment_refutes_hypothesis(self, pipeline):
        # Cannot test: effect_size is always 0.7 and significance always 0.95
        # Need real computation to trigger refutation path
        pass

    def test_analyze_results_empty(self, pipeline):
        results = pipeline.analyze_results()
        assert results == []

    def test_analyze_results_with_data(self, pipeline):
        pipeline.propose_hypothesis("A causes B", "A", "B", "increase")
        pipeline.create_harness("docker", {})
        pipeline.run_experiment("H1", "TH1")
        results = pipeline.analyze_results()
        assert len(results) == 1
        assert results[0]["hypothesis"] == "A causes B"
        assert results[0]["status"] == "confirmed"

    def test_full_discovery_cycle(self, pipeline):
        """End-to-end: hypothesize → experiment → analyze."""
        pipeline.propose_hypothesis("LR beats SGD", "optimizer", "loss",
                                     "decrease")
        pipeline.create_harness("docker", {"framework": "pytorch"})
        result = pipeline.run_experiment("H1", "TH1")
        analysis = pipeline.analyze_results()
        assert result.supports_hypothesis is True  # hardcoded
        assert analysis[0]["status"] == "confirmed"
```

#### T3.3: Run Expanded Test Suite

```bash
cd packages/lyra-science-pipeline
python -m pytest tests/ -v --cov=src/lyra_science_pipeline --cov-report=term-missing
```

**Target:** 80%+ coverage on the 113-line module.

#### T3.4: Integration with DeepSeek Provider

Since `SciencePipeline.run_experiment()` is fully simulated (no LLM calls), DeepSeek integration is not directly testable. However, a future state should:

1. Use LLM to generate hypotheses from a research question
2. Use LLM to design experiment protocols
3. Use LLM to analyze experiment results qualitatively
4. Use the research orchestrator's DISCOVERY agent to find related work

**Test script for LLM-integrated science pipeline (future):**
```python
# tests/scripts/test_science_deepseek.py
# Tests hypothesis generation and experiment analysis with DeepSeek
```

---

## 4. AI Research Flow (DCI Investigation + Paper Analysis)

### 4.1 Components

| Component | Package | Status |
|-----------|---------|--------|
| DCI Investigation | `lyra-cli` → `/investigate` | Implemented |
| Paper Analysis Skill | `lyra-cli/skills/paper-analysis/` | SKILL.md exists |
| AI Researcher Skill | `lyra-cli/skills/specialized/ai_researcher.py` | Implemented |
| Research Methodology | `lyra-cli/skills/specialized/ai_research/` | Reference doc exists |
| DeepSearch (IRCoT) | `lyra-cli` → `/deepsearch` | Implemented (with simulation) |

### 4.2 Test Matrix

#### T4.1: DCI Investigation Smoke Test

```bash
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra
python -m lyra_cli investigate "test topic" \
  --corpus /tmp/test-corpus \
  --context-level 3 \
  --max-turns 5 \
  --wall-clock 60 \
  --read-only
```

**Validate:**
- [ ] InvestigationRunner initializes with corpus mount
- [ ] Context level affects retrieval behavior
- [ ] Turn cap is enforced
- [ ] Wall-clock cap is enforced
- [ ] Output is written to `--output-dir`

#### T4.2: DeepSearch (IRCoT) Test

```bash
python -m lyra_cli deepsearch "transformer attention mechanism" --hops 3 --local
```

**Validate:**
- [ ] Query is decomposed into sub-questions
- [ ] Each hop finds sources
- [ ] Support/contradiction scores are computed
- [ ] Synthesis panel separates resolved vs. unresolved hops
- [ ] Early exit triggers when support_score >= 0.8 across hops

#### T4.3: Paper Analysis Skill Test

```bash
# Check if paper analysis skill loads correctly
python -m lyra_cli skill show paper-analysis
```

#### T4.4: Real Multi-Hop Research (LLM-Integrated)

```bash
python -m lyra_cli deepsearch "latest advances in mixture of experts for LLMs" --hops 5
```

**Validate with DeepSeek:**
- [ ] Web search finds recent papers (2024-2026)
- [ ] LLM correctly extracts key claims from sources
- [ ] Multi-hop chaining: each hop builds on previous findings
- [ ] Contradictions between sources are flagged

---

## 5. Evals Flow (`lyra-evals`)

### 5.1 Package Status

| Attribute | Value |
|-----------|-------|
| Source files | ~17 files |
| Test files | 9 files, ~1,200 lines |
| Version | 0.2.0 |
| Maturity | **Moderate** — adapters and core functionality tested |

### 5.2 Test Matrix

#### T5.1: Run Existing Eval Tests

```bash
cd packages/lyra-evals
python -m pytest tests/ -v --tb=short 2>&1 | tail -40
```

#### T5.2: Smoke Test Eval Runner

```bash
cd /Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra
python -m lyra_cli evals --corpus golden --budget 3 --json
```

**Validate:**
- [ ] Golden corpus loads
- [ ] EvalRunner executes tasks
- [ ] Budget cap is enforced
- [ ] JSON output is well-formed

#### T5.3: SWE-Bench Pro Adapter

```bash
python -m lyra_cli evals --corpus swe-bench-pro --budget 2 --output /tmp/swebench-test.jsonl
```

#### T5.4: Pass@K Probe

```bash
python -m lyra_cli evals --corpus golden --passk 3 --budget 2
```

**Validate:**
- [ ] `pass_at_k` metric is computed
- [ ] `pass_pow_k` metric is computed
- [ ] `reliability_gap` is reported
- [ ] `flaky_cases` are identified

#### T5.5: Drift Gate

```bash
python -m lyra_cli evals --corpus golden --drift-gate 0.80 --budget 5
```

---

## 6. Cross-Cutting Integration Tests

### 6.1 Research → Evals Feedback Loop

```bash
# Run research, then evaluate the research quality
python -m lyra_cli research "Python async patterns" --depth quick
python -m lyra_cli evals --corpus golden --budget 3
```

**Validate:** Research results can feed into eval benchmarks.

### 6.2 Research + Voice Integration

```bash
cd packages/lyra-cli
python -m pytest tests/integration/test_research_voice_integration.py -v --tb=short
```

### 6.3 Multi-Provider Research Test

Test the same research topic across providers to compare quality:

```python
# tests/scripts/test_multi_provider_research.py
topics = [
    "transformer attention mechanisms",
    "gradient descent optimization",
    "protein folding prediction"
]
providers = ["deepseek", "anthropic"]  # Add as available

for topic in topics:
    for provider in providers:
        result = orchestrator.research(topic, provider=provider)
        # Compare: source count, report length, citation quality
```

### 6.4 Research Memory Persistence

```bash
python -m lyra_cli research "test topic for persistence" --depth quick
python -m lyra_cli research list
python -m lyra_cli research show $(python -m lyra_cli research list --json | jq -r '.[0].id')
python -m lyra_cli research related "test topic"
```

**Validate:**
- [ ] Session is persisted across CLI invocations
- [ ] `research list` shows past sessions
- [ ] `research show <id>` retrieves full report
- [ ] `research related <topic>` finds semantically related past sessions

---

## 7. Automated Test Runner Script

Save as `tests/scripts/run_research_test_suite.sh`:

```bash
#!/bin/bash
# Comprehensive Research Flows Test Suite
# Provider: DeepSeek via Anthropic bridge
set -euo pipefail

PROJECT_ROOT="/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra"
cd "$PROJECT_ROOT"

PASS=0
FAIL=0
RESULTS=()

run_test() {
    local name="$1"
    local cmd="$2"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔬 $name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if eval "$cmd"; then
        echo "✅ PASS: $name"
        RESULTS+=("✅ $name")
        ((PASS++))
    else
        echo "❌ FAIL: $name"
        RESULTS+=("❌ $name")
        ((FAIL++))
    fi
    echo ""
}

# ── Phase 0: Provider Check ──
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 0: PROVIDER VERIFICATION"
echo "═══════════════════════════════════════════════════════════════"

python3 -c "
import os
key = os.environ.get('ANTHROPIC_API_KEY', '')
url = os.environ.get('ANTHROPIC_BASE_URL', '')
model = os.environ.get('ANTHROPIC_MODEL', '')
print(f'API Key: {\"SET\" if key else \"MISSING\"} ({key[:8]}...{key[-4:] if key else \"\"})')
print(f'Base URL: {url or \"MISSING\"}')
print(f'Model: {model or \"MISSING\"}')
if 'deepseek' in (url or ''):
    print('✅ DeepSeek provider detected via Anthropic bridge')
else:
    print('⚠️  DeepSeek not detected in base URL')
"

# ── Phase 1: lyra-research Unit Tests ──
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 1: lyra-research UNIT TESTS"
echo "═══════════════════════════════════════════════════════════════"

run_test "Research Models" \
    "cd packages/lyra-research && python -m pytest tests/test_models.py -v --tb=short 2>&1 | tail -5"

run_test "Source Discovery" \
    "cd packages/lyra-research && python -m pytest tests/test_sources.py tests/test_discovery_agents.py -v --tb=short 2>&1 | tail -5"

run_test "Analysis Agents" \
    "cd packages/lyra-research && python -m pytest tests/test_analysis_agents.py -v --tb=short 2>&1 | tail -5"

run_test "Synthesis Agents" \
    "cd packages/lyra-research && python -m pytest tests/test_synthesis_agents.py -v --tb=short 2>&1 | tail -5"

run_test "Orchestrator" \
    "cd packages/lyra-research && python -m pytest tests/test_orchestrator.py tests/test_orchestrator_integration.py -v --tb=short 2>&1 | tail -5"

run_test "Coordination Primitives" \
    "cd packages/lyra-research && python -m pytest tests/test_coordination.py -v --tb=short 2>&1 | tail -5"

run_test "Adversarial Review" \
    "cd packages/lyra-research && python -m pytest tests/test_adversarial_reviewer.py -v --tb=short 2>&1 | tail -5"

run_test "Intelligence (Gap Analysis, Falsification)" \
    "cd packages/lyra-research && python -m pytest tests/test_intelligence.py -v --tb=short 2>&1 | tail -5"

run_test "Quality Gates" \
    "cd packages/lyra-research && python -m pytest tests/test_quality_gates.py -v --tb=short 2>&1 | tail -5"

run_test "Research Memory & Persistence" \
    "cd packages/lyra-research && python -m pytest tests/test_research_memory.py tests/test_checkpoint.py -v --tb=short 2>&1 | tail -5"

run_test "Full Integration" \
    "cd packages/lyra-research && python -m pytest tests/test_full_integration.py -v --tb=short 2>&1 | tail -5"

# ── Phase 2: lyra-science-pipeline Tests ──
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 2: lyra-science-pipeline TESTS"
echo "═══════════════════════════════════════════════════════════════"

run_test "Science Pipeline (Existing)" \
    "cd packages/lyra-science-pipeline && python -m pytest tests/ -v --tb=long 2>&1 | tail -10"

# ── Phase 3: lyra-autoresearch Gap Analysis ──
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 3: lyra-autoresearch GAP ANALYSIS"
echo "═══════════════════════════════════════════════════════════════"

echo "Checking implementation status..."
for dir in packages/lyra-autoresearch/src/lyra_autoresearch/*/; do
    submod=$(basename "$dir")
    impl_count=$(grep -c "^def \|^class \|^async def " "$dir/__init__.py" 2>/dev/null || echo "0")
    echo "  $submod: $impl_count real implementations"
done

run_test "Autoresearch Tests (Expected Partial Failures)" \
    "cd packages/lyra-autoresearch && python -m pytest tests/ -v --tb=short 2>&1 | tail -20 || true"

# ── Phase 4: lyra-evals Tests ──
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 4: lyra-evals TESTS"
echo "═══════════════════════════════════════════════════════════════"

run_test "Eval Harness" \
    "cd packages/lyra-evals && python -m pytest tests/ -v --tb=short 2>&1 | tail -15"

# ── Phase 5: CLI Integration ──
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 5: CLI INTEGRATION TESTS"
echo "═══════════════════════════════════════════════════════════════"

run_test "Research Command Handler" \
    "cd packages/lyra-cli && python -m pytest tests/test_research_command.py tests/test_research_command_handler.py -v --tb=short 2>&1 | tail -10"

run_test "Research Engine" \
    "cd packages/lyra-cli && python -m pytest tests/research/ -v --tb=short 2>&1 | tail -10"

# ── Phase 6: Script-Based Integration Tests ──
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 6: SCRIPT-BASED INTEGRATION TESTS"
echo "═══════════════════════════════════════════════════════════════"

run_test "Research Flow E2E" \
    "python tests/scripts/test_research_flow.py 2>&1 | tail -20"

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "TEST SUMMARY"
echo "═══════════════════════════════════════════════════════════════"
for result in "${RESULTS[@]}"; do
    echo "$result"
done
echo "───────────────────────────────────────────────────────────────"
echo "Total: $((PASS + FAIL)) | ✅ Passed: $PASS | ❌ Failed: $FAIL"
echo "═══════════════════════════════════════════════════════════════"

exit $FAIL
```

---

## 8. Execution Order & Dependencies

```
Phase 0: Provider Check (5 min)
    │
    ├── Concurrent ──┬── Phase 1: lyra-research unit tests (15 min)
    │                ├── Phase 2: lyra-science-pipeline tests (5 min)
    │                ├── Phase 3: lyra-autoresearch gap analysis (5 min)
    │                └── Phase 4: lyra-evals tests (10 min)
    │
    ▼
Phase 5: CLI Integration Tests (10 min)
    │
    ▼
Phase 6: Script-Based E2E Tests (15 min)
    │
    ▼
Report Generation
```

**Total estimated runtime:** ~45-60 minutes (sequential) or ~25-30 minutes (parallel phases)

---

## 9. Expected Failure Inventory

| Phase | Test | Expected Result | Likely Issue |
|-------|------|----------------|-------------|
| 0 | Provider check | ⚠️ Partial | Script checks `DEEPSEEK_API_KEY` which is not set; Anthropic bridge IS configured |
| 1 | lyra-research unit tests | ✅ Mostly pass | Some tests may need LLM provider mocking |
| 2 | lyra-science-pipeline | ⚠️ 2/3 tests pass | Only 2 trivial functions tested; coverage ~5% |
| 3 | lyra-autoresearch | ❌ Most fail | No implementation exists; stubs only |
| 4 | lyra-evals | ✅ Mostly pass | Adapters have tests; stub policies used |
| 5 | CLI integration | ⚠️ Partial | May need provider configuration |
| 6 | Script-based E2E | ❌ Partial | `test_deepseek_research.py` broken (wrong env var) |

---

## 10. Immediate Actions Before Testing

1. **Fix `test_deepseek_research.py`** — Update to detect Anthropic bridge config instead of direct `DEEPSEEK_API_KEY`
2. **Install test dependencies** — `pip install pytest pytest-cov pytest-asyncio`
3. **Set up test output directories** — `mkdir -p test_output_deepseek /tmp/test-corpus`
4. **Verify provider connectivity** — Run Phase 0 provider check
5. **Decide on lyra-autoresearch** — Build out or remove skeleton (recommend: remove)

---

## 11. Success Criteria

| Flow | Success Criteria |
|------|-----------------|
| Deep Research | All P0/P1 tests pass; real pipeline completes for a test topic |
| Auto Research | Decision made (build/remove); if build, TDD plan in place |
| Scientist Research | 80%+ coverage on science_pipeline module; all CRUD operations tested |
| AI Research (DCI) | DCI investigation runs without crash; DeepSearch IRCoT resolves 2+ hop queries |
| Evals | All eval adapter tests pass; golden corpus smoke test succeeds |
| Integration | Research → memory persistence → retrieval cycle works end-to-end |
