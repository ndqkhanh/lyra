# Research Workflows User Guide

> Complete guide to Lyra's research capabilities: deep research, auto research, scientist research, and AI research workflows

**Version**: 1.0.0  
**Last Updated**: 2026-05-30  
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Deep Research Workflow](#deep-research-workflow)
4. [Auto Research Workflow](#auto-research-workflow)
5. [Scientist Research Workflow](#scientist-research-workflow)
6. [AI Research Workflow](#ai-research-workflow)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [API Reference](#api-reference)
10. [Configuration](#configuration)

---

## Overview

Lyra provides four specialized research workflows, each designed for different research needs:

| Workflow | Best For | Key Features | Typical Duration |
|----------|----------|--------------|------------------|
| **Deep Research** | Multi-hop exploration, comprehensive analysis | Source chaining, adversarial review, gap analysis | 10-30 minutes |
| **Auto Research** | Autonomous loops, self-healing execution | Citation verification, debate panels, evolution | 15-45 minutes |
| **Scientist Research** | Hypothesis testing, experimentation | Hypothesis generation, trial harnesses, statistical analysis | 20-60 minutes |
| **AI Research** | Paper/code analysis, technique extraction | PDF parsing, repository analysis, knowledge graphs | 5-20 minutes |

### When to Use Each Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    Research Decision Tree                    │
└─────────────────────────────────────────────────────────────┘

Need to explore a topic comprehensively?
├─ Yes → Deep Research
│   ├─ Quick overview (10 sources) → depth="quick"
│   ├─ Standard analysis (30 sources) → depth="standard"
│   └─ Exhaustive research (50+ sources) → depth="deep"
│
Need autonomous execution with self-correction?
├─ Yes → Auto Research
│   ├─ Citation verification required → enable_verification=True
│   ├─ Multi-perspective analysis → enable_debate=True
│   └─ Learn from failures → enable_evolution=True
│
Need to test hypotheses experimentally?
├─ Yes → Scientist Research
│   ├─ Single hypothesis → propose_hypothesis()
│   ├─ Multiple hypotheses → batch_propose()
│   └─ A/B testing → create_harness(type="comparison")
│
Need to analyze papers or code?
└─ Yes → AI Research
    ├─ Paper analysis → analyze_paper()
    ├─ Code analysis → analyze_repository()
    └─ Technique extraction → extract_techniques()
```

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Lyra Research Architecture                  │
└─────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  User Interface  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Research Router  │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
   │  Deep   │         │  Auto   │         │Scientist│
   │Research │         │Research │         │Research │
   └────┬────┘         └────┬────┘         └────┬────┘
        │                   │                    │
        └───────────────────┼────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  AI Research   │
                    │   (Shared)     │
                    └───────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌────▼────┐        ┌────▼────┐
   │Discovery│         │Analysis │        │Synthesis│
   │ (Haiku) │         │(Sonnet) │        │ (Opus)  │
   └─────────┘         └─────────┘        └─────────┘
```

### Key Components

- **Research Router**: Intelligent routing to appropriate workflow
- **Discovery Agent**: Fast parallel source discovery (Haiku)
- **Analysis Agent**: Deep paper/code analysis (Sonnet)
- **Synthesis Agent**: Report generation and synthesis (Opus)
- **Memory System**: Persistent storage across sessions
- **Coordination Manager**: Retry, timeout, circuit breaker

---

## Getting Started

### Installation

```bash
# Install research packages
pip install lyra-research lyra-autoresearch lyra-science-pipeline

# Verify installation
python -c "import lyra_research; print(lyra_research.__version__)"
```

### Quick Start

```python
from lyra_research import ResearchOrchestrator

# Initialize orchestrator
orchestrator = ResearchOrchestrator(
    output_dir="./research_output"
)

# Run quick research
progress = orchestrator.research(
    topic="LLM reasoning capabilities",
    depth="quick",
    sources=["arxiv", "github"]
)

# Check results
print(f"Found {progress.sources_found} sources")
print(f"Report: {progress.report.summary}")
```

### Environment Setup

```bash
# Required environment variables
export ANTHROPIC_API_KEY="your-api-key"
export DEEPSEEK_API_KEY="your-deepseek-key"  # Optional, for cost optimization

# Optional configuration
export LYRA_OUTPUT_DIR="./research_output"
export LYRA_LOG_LEVEL="INFO"
export LYRA_MAX_SOURCES=50
```

### Configuration File

Create `~/.lyra/config.yaml`:

```yaml
research:
  default_depth: "standard"
  default_sources: ["arxiv", "github", "semantic_scholar"]
  max_sources_per_type: 20
  enable_verification: true
  
model_routing:
  provider: "anthropic"  # or "deepseek"
  discovery_model: "claude-haiku-4-5"
  analysis_model: "claude-sonnet-4-6"
  synthesis_model: "claude-opus-4-5"
  
memory:
  corpus_path: "~/.lyra/corpus"
  max_entries: 10000
  enable_persistence: true
```

---

## Deep Research Workflow

### Overview

Deep Research performs multi-hop exploration with source chaining, adversarial review, and comprehensive synthesis.

**Use Cases:**
- Literature reviews
- Technology landscape analysis
- Competitive research
- Academic research

### Basic Usage

```python
from lyra_research import ResearchOrchestrator

orchestrator = ResearchOrchestrator(output_dir="./output")

# Quick research (10 sources, 1 hop, ~2 minutes)
progress = orchestrator.research(
    topic="Multi-agent coordination",
    depth="quick",
    sources=["arxiv"]
)

# Standard research (30 sources, 2-3 hops, ~10 minutes)
progress = orchestrator.research(
    topic="LLM tool use",
    depth="standard",
    sources=["arxiv", "github"]
)

# Deep research (50+ sources, 3-5 hops, ~30 minutes)
progress = orchestrator.research(
    topic="Autonomous AI agents",
    depth="deep",
    sources=["arxiv", "github", "semantic_scholar"],
    enable_verification=True
)
```

### Advanced Features

#### Multi-Hop Source Chaining

```python
# Enable citation traversal
progress = orchestrator.research(
    topic="LLM reasoning",
    depth="deep",
    enable_citation_chaining=True,
    max_citation_depth=3
)

# Access citation network
for source in progress.sources:
    print(f"{source.title}")
    print(f"  Citations: {source.forward_citations}")
    print(f"  References: {source.backward_citations}")
```

#### Adversarial Review

```python
# Enable verification for critical research
progress = orchestrator.research(
    topic="AI safety mechanisms",
    depth="deep",
    enable_verification=True,
    verification_threshold=0.8  # 80% claims must be verified
)

# Check verification results
print(f"Verification rate: {progress.verification_rate:.1%}")
print(f"Contradictions found: {len(progress.contradictions)}")
print(f"Gaps identified: {len(progress.gaps)}")
```

#### Gap Analysis

```python
# Identify research gaps
progress = orchestrator.research(
    topic="Multi-agent systems",
    depth="deep",
    enable_gap_analysis=True
)

# Review gaps
for gap in progress.gaps:
    print(f"Gap: {gap.description}")
    print(f"  Severity: {gap.severity}")
    print(f"  Suggested research: {gap.suggestions}")
```

### Progress Tracking

```python
# Track progress in real-time
def progress_callback(progress):
    print(f"Phase: {progress.current_phase}")
    print(f"Sources found: {sum(progress.sources_found.values())}")
    print(f"Papers analyzed: {progress.papers_analyzed}")
    print(f"Elapsed: {progress.elapsed_seconds}s")

progress = orchestrator.research(
    topic="LLM agents",
    depth="standard",
    progress_callback=progress_callback
)
```

### Output Structure

```
research_output/
├── report.md                    # Main research report
├── sources.json                 # All discovered sources
├── analysis/
│   ├── papers/                  # Paper analyses
│   │   ├── arxiv_2605_20025.json
│   │   └── ...
│   └── repositories/            # Repository analyses
│       ├── org_repo.json
│       └── ...
├── synthesis/
│   ├── knowledge_graph.json    # Concept relationships
│   ├── taxonomy.json           # Field taxonomy
│   └── contradictions.json     # Identified contradictions
├── verification/
│   ├── claims.json             # Verified claims
│   └── gaps.json               # Research gaps
└── metadata.json               # Session metadata
```

### Example: Complete Deep Research

```python
from lyra_research import ResearchOrchestrator
from pathlib import Path

# Initialize
orchestrator = ResearchOrchestrator(
    output_dir="./llm_agents_research"
)

# Run comprehensive research
progress = orchestrator.research(
    topic="LLM-based autonomous agents",
    depth="deep",
    sources=["arxiv", "github", "semantic_scholar"],
    enable_verification=True,
    enable_gap_analysis=True,
    enable_citation_chaining=True,
    max_sources=50
)

# Results
print(f"✓ Research complete in {progress.elapsed_seconds}s")
print(f"✓ Found {sum(progress.sources_found.values())} sources")
print(f"✓ Analyzed {progress.papers_analyzed} papers")
print(f"✓ Verification rate: {progress.verification_rate:.1%}")
print(f"✓ Report saved to: {progress.report_path}")

# Access report
report = progress.report
print(f"\nKey Findings:")
for finding in report.key_findings[:5]:
    print(f"  • {finding}")

print(f"\nResearch Gaps:")
for gap in progress.gaps[:3]:
    print(f"  • {gap.description}")
```

**Expected Output:**
```
✓ Research complete in 1847s
✓ Found 52 sources
✓ Analyzed 38 papers
✓ Verification rate: 87.3%
✓ Report saved to: ./llm_agents_research/report.md

Key Findings:
  • Multi-agent systems improve task completion by 34% over single agents
  • Tool-calling capabilities are essential for real-world applications
  • Memory systems enable context retention across sessions
  • Adversarial review improves claim accuracy by 23%
  • Citation networks reveal 3 major research clusters

Research Gaps:
  • Limited evaluation of long-term agent behavior
  • Insufficient benchmarks for multi-agent coordination
  • Lack of standardized safety protocols
```

---

## Auto Research Workflow

### Overview

Auto Research provides autonomous execution with self-healing, citation verification, multi-agent debates, and cross-run learning.

**Use Cases:**
- Autonomous research loops
- Citation-critical research
- Multi-perspective analysis
- Self-improving research systems

### Basic Usage

```python
from lyra_autoresearch import SelfHealingExecutor, CitationVerifier

# Initialize executor
executor = SelfHealingExecutor(
    max_retries=3,
    enable_pivot=True,
    enable_refine=True
)

# Run research with self-healing
def research_task():
    # Your research logic
    return {"status": "success", "findings": [...]}

result = executor.execute(research_task)
print(f"Retries: {executor.retry_count}")
print(f"Pivots: {executor.pivot_count}")
```

### Citation Verification

```python
from lyra_autoresearch import CitationVerifier, VerifyStatus

verifier = CitationVerifier()

# Verify single claim
claim = "AutoGPT uses GPT-4 for autonomous task execution"
source = {
    "id": "arxiv:2605.20025",
    "content": "AutoGPT leverages GPT-4 to autonomously execute tasks..."
}

result = verifier.verify(claim, source)
print(f"Status: {result.status}")  # VERIFIED, NOT_FOUND, CONTRADICTS
print(f"Confidence: {result.confidence:.2f}")

# Batch verification
claims = [
    "Claim 1 about agents",
    "Claim 2 about tools",
    "Claim 3 about memory"
]
sources = [...]  # List of source documents

results = verifier.verify_batch(claims, sources)
verified_count = sum(1 for r in results if r.status == VerifyStatus.VERIFIED)
print(f"Verified: {verified_count}/{len(claims)}")
```

### Multi-Agent Debate

```python
from lyra_autoresearch import DebatePanel, Perspective

# Create debate panel
panel = DebatePanel(
    topic="LLM reasoning capabilities",
    perspectives=[
        Perspective(name="Optimist", stance="pro"),
        Perspective(name="Skeptic", stance="con"),
        Perspective(name="Pragmatist", stance="neutral")
    ],
    max_rounds=5
)

# Run debate
result = panel.run_debate()

print(f"Converged: {result.converged}")
print(f"Rounds: {result.rounds_completed}")
print(f"\nConsensus Points:")
for point in result.consensus_points:
    print(f"  • {point}")

print(f"\nRemaining Disagreements:")
for disagreement in result.disagreements:
    print(f"  • {disagreement}")
```

### Self-Healing Execution

```python
from lyra_autoresearch import SelfHealingExecutor, FailureType

executor = SelfHealingExecutor(max_retries=3)

# Define task with potential failures
def flaky_research_task():
    # Simulate transient failure
    if random.random() < 0.3:
        raise RuntimeError("API timeout")
    return {"status": "success", "data": [...]}

# Define pivot strategy
def pivot_strategy():
    # Alternative approach when primary fails
    return {"status": "success", "data": [...], "strategy": "alternative"}

# Execute with healing
result = executor.execute(
    flaky_research_task,
    pivot_fn=pivot_strategy
)

print(f"Success: {result['status'] == 'success'}")
print(f"Retries: {executor.retry_count}")
print(f"Pivots: {executor.pivot_count}")
```

### Evolution & Learning

```python
from lyra_autoresearch import EvolutionEngine, LessonEntry, LessonCategory

engine = EvolutionEngine()

# Record lesson from research run
lesson = LessonEntry(
    category=LessonCategory.QUERY_REFINEMENT,
    severity="HIGH",
    description="Broad queries need domain-specific terms",
    context={"query": "AI", "refined": "AI reasoning systems"},
    success_rate_before=0.3,
    success_rate_after=0.8
)

engine.record_lesson(lesson)

# Apply lessons to new research
recommendations = engine.get_recommendations(
    context={"domain": "machine learning", "task": "source_selection"}
)

print("Recommendations based on past lessons:")
for rec in recommendations:
    print(f"  • {rec}")
```

### Example: Complete Auto Research

```python
from lyra_autoresearch import (
    SelfHealingExecutor,
    CitationVerifier,
    DebatePanel,
    EvolutionEngine
)

# Initialize components
executor = SelfHealingExecutor(max_retries=3)
verifier = CitationVerifier()
evolution = EvolutionEngine()

# Define research task
def autonomous_research(topic):
    # Discovery phase
    sources = discover_sources(topic)
    
    # Analysis with verification
    claims = extract_claims(sources)
    verified = verifier.verify_batch(claims, sources)
    
    # Multi-perspective debate
    panel = DebatePanel(topic=topic, perspectives=[...])
    debate_result = panel.run_debate()
    
    return {
        "sources": sources,
        "verified_claims": verified,
        "consensus": debate_result.consensus_points
    }

# Execute with self-healing
result = executor.execute(lambda: autonomous_research("LLM agents"))

# Record lessons
if executor.pivot_count > 0:
    evolution.record_lesson(LessonEntry(
        category="STRATEGY_ADAPTATION",
        description="Pivot improved success rate",
        success_rate_before=0.0,
        success_rate_after=1.0
    ))

print(f"✓ Research complete")
print(f"✓ Verified claims: {len(result['verified_claims'])}")
print(f"✓ Consensus points: {len(result['consensus'])}")
print(f"✓ Lessons learned: {evolution.lesson_count()}")
```

---

## Scientist Research Workflow

### Overview

Scientist Research enables hypothesis-driven experimentation with trial harnesses and statistical analysis.

**Use Cases:**
- A/B testing
- Hypothesis validation
- Experimental research
- Performance benchmarking

### Basic Usage

```python
from lyra_research import SibylPipeline, TrialHarness

# Initialize pipeline
pipeline = SibylPipeline()

# Propose hypothesis
hypothesis = pipeline.propose_hypothesis(
    statement="Increasing context window improves reasoning accuracy",
    independent_var="context_window_size",
    dependent_var="reasoning_accuracy",
    expected_effect="positive"
)

print(f"Hypothesis ID: {hypothesis.id}")
print(f"Status: {hypothesis.status}")  # proposed

# Create experiment harness
harness = pipeline.create_harness(
    sandbox_type="docker",
    variables={
        "model": "gpt-4",
        "context_sizes": [4096, 8192, 16384, 32768],
        "test_cases": 100
    }
)

# Run experiment
result = await pipeline.run_experiment(hypothesis.id, harness.id)

print(f"Outcome: {result.outcome}")  # confirmed/refuted
print(f"Effect size: {result.effect_size:.3f}")
print(f"Significance: {result.significance:.3f}")
```

### Multiple Hypotheses

```python
# Batch hypothesis generation
hypotheses = [
    ("Multi-agent systems improve completion rate", "num_agents", "completion_rate", "positive"),
    ("Temperature affects response diversity", "temperature", "diversity_score", "positive"),
    ("Longer prompts reduce accuracy", "prompt_length", "accuracy", "negative")
]

for statement, iv, dv, effect in hypotheses:
    h = pipeline.propose_hypothesis(statement, iv, dv, effect)
    print(f"Created: {h.id}")

# Run all experiments
results = []
for h in pipeline.hypotheses:
    harness = pipeline.create_harness("simulation", {...})
    result = await pipeline.run_experiment(h.id, harness.id)
    results.append(result)

# Analyze results
analysis = pipeline.analyze_results()
for item in analysis:
    print(f"{item['hypothesis']}: {item['conclusion']}")
```

### Trial Harness Configuration

```python
from lyra_research import TrialConfig, TrialHarness

# Configure trial
config = TrialConfig(
    sandbox_type="docker",
    timeout_seconds=300,
    max_retries=3,
    variables={
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000
    }
)

# Create harness
harness = TrialHarness(config)

# Run trial
trial = await harness.run_trial(
    trial_id="trial_001",
    test_fn=lambda: run_model_test(...)
)

print(f"Status: {trial.status}")
print(f"Duration: {trial.duration_seconds}s")
print(f"Result: {trial.result}")
```

### Example: A/B Testing

```python
from lyra_research import SibylPipeline

pipeline = SibylPipeline()

# Hypothesis: Model A outperforms Model B
hypothesis = pipeline.propose_hypothesis(
    statement="GPT-4 achieves higher accuracy than GPT-3.5",
    independent_var="model_version",
    dependent_var="accuracy",
    expected_effect="positive"
)

# Create comparison harness
harness = pipeline.create_harness(
    sandbox_type="comparison",
    variables={
        "model_a": "gpt-4",
        "model_b": "gpt-3.5-turbo",
        "test_cases": 500,
        "metrics": ["accuracy", "latency", "cost"]
    }
)

# Run A/B test
result = await pipeline.run_experiment(hypothesis.id, harness.id)

print(f"Hypothesis: {hypothesis.statement}")
print(f"Outcome: {result.outcome}")
print(f"Effect size: {result.effect_size:.3f}")
print(f"p-value: {result.significance:.4f}")

# Detailed metrics
print(f"\nModel A (GPT-4):")
print(f"  Accuracy: {result.metrics['model_a']['accuracy']:.2%}")
print(f"  Latency: {result.metrics['model_a']['latency']:.0f}ms")
print(f"  Cost: ${result.metrics['model_a']['cost']:.2f}")

print(f"\nModel B (GPT-3.5):")
print(f"  Accuracy: {result.metrics['model_b']['accuracy']:.2%}")
print(f"  Latency: {result.metrics['model_b']['latency']:.0f}ms")
print(f"  Cost: ${result.metrics['model_b']['cost']:.2f}")
```

---

## AI Research Workflow

### Overview

AI Research provides specialized tools for analyzing papers, code repositories, and extracting techniques.

**Use Cases:**
- Paper analysis
- Code repository analysis
- Technique extraction
- Knowledge graph construction

### Paper Analysis

```python
from lyra_research import PaperAnalyzer

analyzer = PaperAnalyzer()

# Analyze paper
paper = {
    "id": "arxiv:2605.20025",
    "title": "AutoResearchClaw",
    "abstract": "We present AutoResearchClaw...",
    "content": "Full paper content..."
}

analysis = analyzer.analyze(paper)

print(f"Paper: {analysis.paper_id}")
print(f"Quality Score: {analysis.quality_score:.2f}")
print(f"\nKey Findings:")
for finding in analysis.key_findings:
    print(f"  • {finding}")

print(f"\nMethodology:")
for method in analysis.methods:
    print(f"  • {method}")

print(f"\nResults:")
for result in analysis.results:
    print(f"  • {result}")
```

### Repository Analysis

```python
from lyra_research import RepositoryAnalyzer

analyzer = RepositoryAnalyzer()

# Analyze repository
repo = {
    "id": "github:org/repo",
    "name": "awesome-llm-agents",
    "description": "Multi-agent system framework",
    "readme": "# Awesome LLM Agents\n\n...",
    "languages": {"Python": 85, "JavaScript": 15}
}

analysis = analyzer.analyze(repo)

print(f"Repository: {analysis.repo_id}")
print(f"Primary Language: {analysis.primary_language}")
print(f"Quality Score: {analysis.quality_score:.2f}")

print(f"\nKey Features:")
for feature in analysis.key_features:
    print(f"  • {feature}")

print(f"\nArchitecture:")
for component in analysis.architecture:
    print(f"  • {component}")
```

### Knowledge Graph Construction

```python
from lyra_research import KnowledgeGraph, ConceptExtractor, RelationshipDiscovery

# Extract concepts
extractor = ConceptExtractor()
text = "Multi-agent systems use tool-calling capabilities..."
concepts = extractor.extract(text)

# Discover relationships
discovery = RelationshipDiscovery()
relationships = discovery.discover(text)

# Build knowledge graph
kg = KnowledgeGraph()

for concept in concepts:
    kg.add_node(concept.id, node_type="concept", properties={"name": concept.name})

for rel in relationships:
    kg.add_edge(rel.source, rel.target, edge_type=rel.type)

# Query graph
path = kg.find_path("multi-agent", "tool-calling")
print(f"Path: {' → '.join(path)}")

# Export graph
kg.export("knowledge_graph.json")
```

### Example: Complete Paper Analysis Pipeline

```python
from lyra_research import PaperAnalyzer, RepositoryAnalyzer, KnowledgeGraph

# Analyze multiple papers
analyzer = PaperAnalyzer()
papers = [...]  # List of papers

analyses = []
for paper in papers:
    analysis = analyzer.analyze(paper)
    analyses.append(analysis)
    print(f"✓ Analyzed: {paper['title']}")

# Build knowledge graph from analyses
kg = KnowledgeGraph()
for analysis in analyses:
    # Add concepts
    for concept in analysis.concepts:
        kg.add_node(concept.id, node_type="concept", properties=concept.properties)
    
    # Add relationships
    for rel in analysis.relationships:
        kg.add_edge(rel.source, rel.target, edge_type=rel.type)

# Find research clusters
clusters = kg.find_clusters()
print(f"\nResearch Clusters: {len(clusters)}")
for i, cluster in enumerate(clusters):
    print(f"  Cluster {i+1}: {len(cluster)} concepts")

# Identify central concepts
central = kg.get_central_nodes(top_k=5)
print(f"\nCentral Concepts:")
for node in central:
    print(f"  • {node.name} (degree: {node.degree})")
```

---

## Best Practices

### Choosing Research Depth

| Depth | Sources | Hops | Duration | Use When |
|-------|---------|------|----------|----------|
| **quick** | 10-15 | 1 | 2-5 min | Initial exploration, quick overview |
| **standard** | 25-35 | 2-3 | 8-15 min | Regular research, balanced coverage |
| **deep** | 45-60 | 3-5 | 20-40 min | Comprehensive analysis, critical research |

### Source Selection Strategy

```python
# Academic research: prioritize papers
sources = ["arxiv", "semantic_scholar", "acl_anthology"]

# Industry research: prioritize code
sources = ["github", "huggingface"]

# Comprehensive: use all sources
sources = ["arxiv", "github", "semantic_scholar", "huggingface"]
```

### Cost Optimization

```python
# Use DeepSeek for cost savings (3-5x cheaper)
orchestrator = ResearchOrchestrator(
    provider="deepseek",
    model_routing={
        "discovery": "deepseek-chat",      # $0.14/M tokens
        "analysis": "deepseek-v4-flash",   # $1.37/M tokens
        "synthesis": "deepseek-v4-pro"     # $11.16/M tokens
    }
)

# Track costs
from lyra_model_router import UsageTracker

tracker = UsageTracker(budget_limit=10.0)
orchestrator.set_usage_tracker(tracker)

progress = orchestrator.research(topic="...", depth="standard")

stats = tracker.get_stats()
print(f"Total cost: ${stats.total_cost:.2f}")
print(f"Budget remaining: ${10.0 - stats.total_cost:.2f}")
```

### Performance Optimization

```python
# Parallel source discovery
orchestrator = ResearchOrchestrator(
    max_parallel_sources=5,  # Discover from 5 sources simultaneously
    max_parallel_analyses=3   # Analyze 3 papers simultaneously
)

# Caching for repeated queries
orchestrator = ResearchOrchestrator(
    enable_cache=True,
    cache_ttl_hours=24
)

# Incremental research (resume from checkpoint)
progress = orchestrator.research(
    topic="LLM agents",
    depth="deep",
    checkpoint_path="./checkpoint.json"
)
```

### Memory Management

```python
# Configure corpus size
orchestrator = ResearchOrchestrator(
    corpus_max_entries=10000,
    corpus_cleanup_threshold=0.8  # Clean when 80% full
)

# Access corpus
corpus = orchestrator.corpus
print(f"Entries: {len(corpus)}")
print(f"Size: {corpus.size_mb:.1f} MB")

# Query corpus
results = corpus.search("multi-agent systems", limit=10)
for result in results:
    print(f"  • {result.title} (score: {result.relevance:.2f})")
```

### Quality Assurance

```python
# Enable all quality checks
orchestrator = ResearchOrchestrator(
    enable_verification=True,        # Adversarial review
    enable_gap_analysis=True,        # Identify gaps
    enable_contradiction_detection=True,  # Find contradictions
    verification_threshold=0.8       # 80% claims verified
)

progress = orchestrator.research(topic="...", depth="deep")

# Review quality metrics
print(f"Verification rate: {progress.verification_rate:.1%}")
print(f"Contradictions: {len(progress.contradictions)}")
print(f"Gaps: {len(progress.gaps)}")
print(f"Report quality: {progress.report.quality_score:.2f}")
```

---

## Troubleshooting

### Common Issues

#### Issue: Research times out

**Symptoms:**
```
TimeoutError: Research exceeded 1800 seconds
```

**Solutions:**
```python
# Increase timeout
orchestrator = ResearchOrchestrator(
    timeout_seconds=3600  # 1 hour
)

# Or reduce scope
progress = orchestrator.research(
    topic="...",
    depth="quick",  # Use quick instead of deep
    max_sources=15   # Limit sources
)
```

#### Issue: API rate limits

**Symptoms:**
```
RateLimitError: Too many requests
```

**Solutions:**
```python
# Enable rate limiting
orchestrator = ResearchOrchestrator(
    enable_rate_limiting=True,
    requests_per_minute=50
)

# Or use exponential backoff
from lyra_research import RetryPolicy

policy = RetryPolicy(
    max_retries=5,
    backoff_factor=2.0
)
orchestrator.set_retry_policy(policy)
```

#### Issue: Low verification rate

**Symptoms:**
```
Warning: Verification rate 45% below threshold 80%
```

**Solutions:**
```python
# Increase source quality threshold
orchestrator = ResearchOrchestrator(
    min_source_quality=0.7,  # Only high-quality sources
    enable_citation_chaining=True  # Follow citations
)

# Or adjust verification threshold
progress = orchestrator.research(
    topic="...",
    verification_threshold=0.6  # Lower threshold
)
```

#### Issue: Out of memory

**Symptoms:**
```
MemoryError: Corpus size exceeded limit
```

**Solutions:**
```python
# Enable automatic cleanup
orchestrator = ResearchOrchestrator(
    corpus_max_entries=5000,
    enable_auto_cleanup=True
)

# Or use streaming mode
orchestrator = ResearchOrchestrator(
    streaming_mode=True,  # Don't store all in memory
    output_dir="./output"
)
```

#### Issue: Poor quality results

**Symptoms:**
- Low quality scores
- Irrelevant sources
- Incomplete analysis

**Solutions:**
```python
# Improve query specificity
progress = orchestrator.research(
    topic="LLM-based autonomous agents with tool use",  # Specific
    # NOT: "AI agents"  # Too broad
    depth="deep",
    enable_query_refinement=True
)

# Filter low-quality sources
orchestrator = ResearchOrchestrator(
    min_source_quality=0.6,
    min_citation_count=10,
    max_source_age_years=3
)
```

### Debugging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("lyra_research")

# Run with debug output
orchestrator = ResearchOrchestrator(
    log_level="DEBUG",
    log_file="./research_debug.log"
)

progress = orchestrator.research(topic="...", depth="standard")

# Inspect progress
print(f"Current phase: {progress.current_phase}")
print(f"Sources found: {progress.sources_found}")
print(f"Errors: {progress.errors}")
```

---

## API Reference

### ResearchOrchestrator

Main orchestrator for deep research workflows.

```python
class ResearchOrchestrator:
    def __init__(
        self,
        output_dir: str | Path,
        provider: str = "anthropic",
        timeout_seconds: int = 1800,
        max_sources: int = 50,
        enable_verification: bool = False,
        enable_cache: bool = True
    )
    
    def research(
        self,
        topic: str,
        depth: str = "standard",  # "quick", "standard", "deep"
        sources: list[str] = None,
        enable_verification: bool = None,
        enable_gap_analysis: bool = False,
        progress_callback: Callable = None
    ) -> ResearchProgress
```

**Parameters:**
- `topic`: Research topic (required)
- `depth`: Research depth - "quick" (10 sources), "standard" (30 sources), "deep" (50+ sources)
- `sources`: List of sources - ["arxiv", "github", "semantic_scholar", "huggingface"]
- `enable_verification`: Enable adversarial review
- `enable_gap_analysis`: Identify research gaps
- `progress_callback`: Function called with progress updates

**Returns:**
- `ResearchProgress`: Progress object with results

### ResearchProgress

```python
@dataclass
class ResearchProgress:
    is_complete: bool
    current_phase: str
    sources_found: dict[str, int]
    papers_analyzed: int
    repos_analyzed: int
    elapsed_seconds: float
    verification_rate: float
    gaps: list[ResearchGap]
    contradictions: list[Contradiction]
    report: ResearchReport
    report_path: Path
    error: Exception | None
```

### SelfHealingExecutor

Autonomous execution with retry, pivot, and refine capabilities.

```python
class SelfHealingExecutor:
    def __init__(
        self,
        max_retries: int = 3,
        enable_pivot: bool = True,
        enable_refine: bool = True
    )
    
    def execute(
        self,
        task: Callable,
        pivot_fn: Callable = None,
        refine_fn: Callable = None
    ) -> Any
```

**Properties:**
- `retry_count`: Number of retries performed
- `pivot_count`: Number of pivots performed
- `refine_count`: Number of refinements performed

### CitationVerifier

4-layer citation verification system.

```python
class CitationVerifier:
    def verify(
        self,
        claim: str,
        source: dict
    ) -> VerificationResult
    
    def verify_batch(
        self,
        claims: list[str],
        sources: list[dict]
    ) -> list[VerificationResult]

@dataclass
class VerificationResult:
    status: VerifyStatus  # VERIFIED, NOT_FOUND, CONTRADICTS, PARTIAL
    confidence: float
    evidence: str
```

### SibylPipeline

Hypothesis-driven experimentation pipeline.

```python
class SibylPipeline:
    def propose_hypothesis(
        self,
        statement: str,
        independent_var: str,
        dependent_var: str,
        expected_effect: str  # "positive", "negative", "neutral"
    ) -> Hypothesis
    
    def create_harness(
        self,
        sandbox_type: str,  # "docker", "simulation", "comparison"
        variables: dict
    ) -> TrialHarness
    
    async def run_experiment(
        self,
        hypothesis_id: str,
        harness_id: str
    ) -> ExperimentResult
```

### PaperAnalyzer

Analyze research papers.

```python
class PaperAnalyzer:
    def analyze(self, paper: dict) -> PaperAnalysis
    def extract_methodology(self, content: str) -> list[str]
    def extract_results(self, content: str) -> list[str]

@dataclass
class PaperAnalysis:
    paper_id: str
    quality_score: float
    key_findings: list[str]
    methods: list[str]
    results: list[str]
    concepts: list[Concept]
```

### RepositoryAnalyzer

Analyze code repositories.

```python
class RepositoryAnalyzer:
    def analyze(self, repo: dict) -> RepositoryAnalysis
    def extract_architecture(self, readme: str) -> list[str]
    def assess_quality(self, repo_info: dict) -> float

@dataclass
class RepositoryAnalysis:
    repo_id: str
    primary_language: str
    quality_score: float
    key_features: list[str]
    architecture: list[str]
```

### KnowledgeGraph

Build and query knowledge graphs.

```python
class KnowledgeGraph:
    def add_node(self, node_id: str, node_type: str, properties: dict)
    def add_edge(self, source: str, target: str, edge_type: str)
    def find_path(self, start: str, end: str) -> list[str]
    def find_clusters(self) -> list[list[str]]
    def get_central_nodes(self, top_k: int) -> list[Node]
    def export(self, path: str)
```

---

## Configuration

### Global Configuration

`~/.lyra/config.yaml`:

```yaml
# Research settings
research:
  default_depth: "standard"
  default_sources: ["arxiv", "github"]
  max_sources_per_type: 20
  enable_verification: true
  enable_gap_analysis: true
  enable_citation_chaining: true
  
# Model routing
model_routing:
  provider: "anthropic"  # or "deepseek"
  discovery_model: "claude-haiku-4-5"
  analysis_model: "claude-sonnet-4-6"
  synthesis_model: "claude-opus-4-5"
  
# DeepSeek configuration (optional)
deepseek:
  api_key: "${DEEPSEEK_API_KEY}"
  base_url: "https://api.deepseek.com"
  models:
    chat: "deepseek-chat"
    flash: "deepseek-v4-flash"
    pro: "deepseek-v4-pro"
  
# Memory settings
memory:
  corpus_path: "~/.lyra/corpus"
  max_entries: 10000
  enable_persistence: true
  cleanup_threshold: 0.8
  
# Performance
performance:
  max_parallel_sources: 5
  max_parallel_analyses: 3
  enable_cache: true
  cache_ttl_hours: 24
  
# Quality
quality:
  min_source_quality: 0.5
  min_citation_count: 5
  max_source_age_years: 5
  verification_threshold: 0.8
```

### Project Configuration

`.lyra/config.yaml` (project-specific):

```yaml
# Override global settings for this project
research:
  default_depth: "deep"
  default_sources: ["arxiv", "semantic_scholar", "acl_anthology"]
  
model_routing:
  provider: "deepseek"  # Use DeepSeek for cost savings
  
output:
  format: "markdown"  # or "json", "html"
  include_metadata: true
  include_sources: true
```

### Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional - DeepSeek
export DEEPSEEK_API_KEY="sk-..."

# Optional - Configuration
export LYRA_CONFIG_PATH="~/.lyra/config.yaml"
export LYRA_OUTPUT_DIR="./research_output"
export LYRA_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
export LYRA_MAX_SOURCES=50
export LYRA_ENABLE_CACHE=true
```

---

## Performance Benchmarks

### Latency Targets

| Operation | Target | Acceptable | Critical |
|-----------|--------|------------|----------|
| Discovery (per source) | <5s | <10s | >15s |
| Paper analysis | <3s | <5s | >10s |
| Synthesis | <10s | <20s | >30s |
| Report generation | <15s | <30s | >60s |
| Model routing | <50ms | <100ms | >200ms |

### Cost Estimates (DeepSeek)

| Research Depth | Sources | Estimated Cost | Duration |
|----------------|---------|----------------|----------|
| Quick | 10-15 | $0.30-$0.50 | 2-5 min |
| Standard | 25-35 | $1.00-$2.00 | 8-15 min |
| Deep | 45-60 | $2.50-$5.00 | 20-40 min |

### Memory Usage

| Component | Typical | Maximum |
|-----------|---------|---------|
| Orchestrator | 50-100 MB | 200 MB |
| Corpus (1000 entries) | 30-50 MB | 100 MB |
| Knowledge graph (1000 nodes) | 20-30 MB | 50 MB |

---

## Examples Gallery

### Example 1: Literature Review

```python
# Comprehensive literature review on LLM reasoning
orchestrator = ResearchOrchestrator(output_dir="./lit_review")

progress = orchestrator.research(
    topic="Large language model reasoning capabilities and limitations",
    depth="deep",
    sources=["arxiv", "semantic_scholar", "acl_anthology"],
    enable_verification=True,
    enable_gap_analysis=True
)

print(f"✓ Analyzed {progress.papers_analyzed} papers")
print(f"✓ Identified {len(progress.gaps)} research gaps")
```

### Example 2: Technology Landscape Analysis

```python
# Analyze multi-agent frameworks
orchestrator = ResearchOrchestrator(output_dir="./tech_landscape")

progress = orchestrator.research(
    topic="Multi-agent system frameworks and implementations",
    depth="standard",
    sources=["github", "huggingface", "arxiv"],
    enable_citation_chaining=True
)

# Analyze top repositories
for repo in progress.top_repositories[:5]:
    print(f"• {repo.name} - {repo.stars} stars")
```

### Example 3: Hypothesis Testing

```python
# Test hypothesis about model performance
from lyra_research import SibylPipeline

pipeline = SibylPipeline()

hypothesis = pipeline.propose_hypothesis(
    statement="Larger context windows improve reasoning accuracy",
    independent_var="context_size",
    dependent_var="accuracy",
    expected_effect="positive"
)

harness = pipeline.create_harness(
    "simulation",
    {"context_sizes": [4096, 8192, 16384, 32768], "test_cases": 200}
)

result = await pipeline.run_experiment(hypothesis.id, harness.id)
print(f"Hypothesis {result.outcome}: effect size = {result.effect_size:.3f}")
```

### Example 4: Citation-Critical Research

```python
# Research with strict citation verification
from lyra_autoresearch import CitationVerifier

orchestrator = ResearchOrchestrator(output_dir="./verified_research")
verifier = CitationVerifier()

progress = orchestrator.research(
    topic="AI safety mechanisms in autonomous systems",
    depth="deep",
    enable_verification=True,
    verification_threshold=0.9  # 90% verification required
)

# Verify all claims
for claim in progress.report.claims:
    result = verifier.verify(claim.text, claim.source)
    if result.status != VerifyStatus.VERIFIED:
        print(f"⚠ Unverified: {claim.text}")
```

### Example 5: Multi-Perspective Analysis

```python
# Use debate panel for controversial topics
from lyra_autoresearch import DebatePanel, Perspective

panel = DebatePanel(
    topic="AGI timeline predictions",
    perspectives=[
        Perspective(name="Optimist", stance="pro"),
        Perspective(name="Skeptic", stance="con"),
        Perspective(name="Researcher", stance="neutral")
    ]
)

result = panel.run_debate()
print(f"Consensus: {result.consensus_points}")
print(f"Disagreements: {result.disagreements}")
```

---

## Additional Resources

### Documentation
- [Architecture Overview](../architecture/research-engine.md)
- [Testing Guide](../testing/RESEARCH-WORKFLOWS-TESTING.md)
- [API Documentation](../API_DOCUMENTATION.md)
- [Developer Guide](../DEVELOPER_GUIDE.md)

### Related Packages
- `lyra-research` - Deep research engine
- `lyra-autoresearch` - AutoResearchClaw integration
- `lyra-science-pipeline` - Hypothesis testing
- `lyra-model-router` - Intelligent model routing

### External Resources
- [AutoResearchClaw Paper](https://arxiv.org/abs/2605.20025)
- [Anthropic API Documentation](https://docs.anthropic.com)
- [DeepSeek API Documentation](https://api.deepseek.com/docs)

---

## Support & Community

### Getting Help
- GitHub Issues: Report bugs and request features
- Documentation: Check this guide and API reference
- Examples: See `examples/` directory for more use cases

### Contributing
Contributions welcome! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

### License
MIT License - See [LICENSE](../../LICENSE) for details.

---

**Last Updated**: 2026-05-30  
**Version**: 1.0.0  
**Maintained By**: Lyra Research Team
