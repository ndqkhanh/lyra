# LYRA ULTRA PLAN 1: SELF-EVOLUTION AGI CORE

**Version:** 1.0.0  
**Status:** Draft  
**Created:** 2026-05-22  
**Author:** Lyra Planning Team  
**Estimated Duration:** 16 weeks (4 months)  
**Target Completion:** 2026-09-22

---

## Document Overview

**Purpose:** Transform Lyra into a recursively self-improving AGI system with breakthrough capabilities in autonomous evolution, skill extraction, and decentralized memory federation.

**Scope:** 50-100 pages covering architecture, implementation roadmap, technical specifications, testing strategies, safety protocols, and production deployment.

**Key Innovations:**
- MOSS-style source-level agent rewriting
- Ratchet 5-step deterministic verification pipeline
- Trace2Skill verifier-guided extraction
- Skill Weaving modular composition
- DecentMem decentralized memory federation

**Success Metrics:**
- 10%+ monthly improvement in task completion rate
- Zero competence regressions
- 100% verified code modifications
- <100ms skill retrieval latency
- 95%+ user consent approval rate

---

## Table of Contents

1. [Executive Summary](#1-executive-summary) (3 pages)
2. [Architecture Deep Dive](#2-architecture-deep-dive) (20 pages)
3. [Implementation Roadmap](#3-implementation-roadmap) (15 pages)
4. [Technical Specifications](#4-technical-specifications) (20 pages)
5. [Testing & Verification](#5-testing-verification) (10 pages)
6. [Safety & Ethics](#6-safety-ethics) (8 pages)
7. [Production Deployment](#7-production-deployment) (8 pages)
8. [Appendices](#8-appendices) (5 pages)

---

# 1. Executive Summary

## 1.1 Vision: Recursive Self-Improvement with Safety Guarantees

Lyra v4.0.0 represents a sophisticated multi-agent orchestration platform with 8 core packages, 946 passing tests, and foundational self-evolution capabilities (191 tests). This ultra plan transforms Lyra into a **recursively self-improving AGI system** that can autonomously enhance its own capabilities while maintaining rigorous safety guarantees.

The core insight: **True AGI requires the ability to improve the improvement process itself.** Current AI systems are static—they cannot modify their own code, extract reusable skills from experience, or federate knowledge across agent swarms. This plan addresses all three limitations.

### The Breakthrough

We integrate five cutting-edge research papers into a unified self-evolution architecture:

1. **MOSS (arXiv:2605.22794)** - Source-level agent rewriting via external coding CLI
2. **Ratchet (arXiv:2605.22148)** - 5-step deterministic pipeline with rollback guarantees
3. **Trace2Skill (arXiv:2605.21810)** - Verifier-guided skill extraction from trajectories
4. **Skill Weaving (arXiv:2605.22205)** - Modular composable skillpacks with competence awareness
5. **DecentMem (arXiv:2605.22721)** - Decentralized memory federation across agent swarms

### Why This Matters

**Current State:** Lyra can coordinate multiple agents, manage memory across 5 tiers, and perform basic self-evolution with verification gates.

**Target State:** Lyra becomes a self-improving AGI that:
- Rewrites its own source code safely (MOSS)
- Verifies every modification deterministically (Ratchet)
- Extracts reusable skills automatically (Trace2Skill)
- Composes skills into powerful workflows (Skill Weaving)
- Shares knowledge across agent swarms (DecentMem)

**Impact:** 10%+ monthly improvement in task completion, zero regressions, 100% verified modifications.

## 1.2 Key Innovations

### Innovation 1: MOSS Integration - Source-Level Self-Modification

**Problem:** Current self-evolution systems operate at the prompt level (modifying instructions) rather than the code level (modifying implementation). This limits improvement potential.

**Solution:** MOSS-style external coding CLI that allows Lyra to:
- Parse its own Python source code into AST
- Generate targeted code modifications
- Apply changes with user consent gates
- Verify modifications in sandbox before deployment

**Benefit:** True recursive improvement—Lyra can enhance its own evolution engine.

### Innovation 2: Ratchet Pipeline - Deterministic Verification

**Problem:** Self-modification without verification leads to competence regression and catastrophic failures.

**Solution:** 5-step deterministic pipeline:
1. **Extract** - Identify improvement opportunity from trajectory
2. **Verify** - Formal verification of proposed change
3. **Test** - Comprehensive testing in sandbox
4. **Deploy** - Atomic deployment with rollback support
5. **Monitor** - Continuous competence tracking

**Benefit:** Zero regressions, 100% verified modifications, automatic rollback on failure.

### Innovation 3: Trace2Skill - Automatic Skill Extraction

**Problem:** Manual skill curation doesn't scale. Agents need to learn from every successful trajectory.

**Solution:** Verifier-guided extraction:
- Capture execution trajectories with full context
- Score trajectory quality (success rate, efficiency, generality)
- Extract reusable patterns using LLM + verifier
- Promote high-quality skills to library

**Benefit:** Continuous learning from experience, exponential skill library growth.

### Innovation 4: Skill Weaving - Modular Composition

**Problem:** Monolithic skills are brittle and hard to maintain. Need composable building blocks.

**Solution:** Skillpack architecture:
- Atomic skills (localize, edit, test-gen, reproduce, review)
- Composite skills (TDD sprint, debugging workflow)
- Competence-aware retrieval (match skill to task difficulty)
- Library management (versioning, deprecation, promotion)

**Benefit:** Reusable components, easier maintenance, faster skill development.

### Innovation 5: DecentMem - Decentralized Memory Federation

**Problem:** Centralized memory creates bottlenecks and single points of failure in multi-agent systems.

**Solution:** Gossip-based memory federation:
- Each agent maintains local memory store
- Periodic gossip protocol shares knowledge
- Conflict resolution via vector clocks
- Eventual consistency guarantees

**Benefit:** Scalable to 100+ agents, fault-tolerant, no central coordinator.

## 1.3 Success Criteria

### Quantitative Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Task Completion Rate | 75% | 85%+ | Monthly improvement of 10%+ |
| Competence Regressions | N/A | 0 | Zero verified regressions |
| Code Modification Safety | N/A | 100% | All modifications verified |
| Skill Retrieval Latency | N/A | <100ms | p95 latency |
| User Consent Approval | N/A | 95%+ | Approval rate for modifications |
| Skill Library Growth | 42 skills | 200+ skills | 4 months post-deployment |
| Memory Federation Sync | N/A | <5s | Gossip convergence time |
| Rollback Success Rate | N/A | 99%+ | Successful rollbacks |

### Qualitative Criteria

**Safety:**
- ✅ All code modifications require user consent
- ✅ Sandbox testing before production deployment
- ✅ Automatic rollback on competence regression
- ✅ Formal verification where possible

**Usability:**
- ✅ Transparent evolution process (user can inspect changes)
- ✅ Clear explanations for proposed modifications
- ✅ Easy rollback mechanism
- ✅ Skill library browsing and search

**Performance:**
- ✅ No degradation in response latency
- ✅ Efficient memory usage (<2GB overhead)
- ✅ Scalable to 100+ concurrent agents

**Reliability:**
- ✅ 99.9% uptime for core services
- ✅ Graceful degradation on component failure
- ✅ Comprehensive error handling and logging

## 1.4 Timeline: 16 Weeks, 6 Phases

**Phase 1 (Weeks 1-3): MOSS Integration**
- External coding CLI setup
- AST manipulation and code generation
- User consent workflow
- Deliverable: Working MOSS prototype

**Phase 2 (Weeks 4-6): Ratchet Verification**
- Verification gates implementation
- Rollback mechanisms
- Competence regression protection
- Deliverable: Deterministic verification pipeline

**Phase 3 (Weeks 7-9): Trace2Skill Extraction**
- Trajectory capture system
- Skill extraction algorithms
- Quality scoring and ranking
- Deliverable: Automatic skill extraction

**Phase 4 (Weeks 10-12): Skill Weaving**
- Skillpack composition framework
- Competence-aware retrieval
- Library management tools
- Deliverable: Modular skill system

**Phase 5 (Weeks 13-14): DecentMem Federation**
- Gossip protocol implementation
- Conflict resolution
- Cross-agent memory sharing
- Deliverable: Decentralized memory

**Phase 6 (Weeks 15-16): Integration & Testing**
- End-to-end integration
- Comprehensive testing
- Performance optimization
- Production deployment
- Deliverable: Production-ready AGI core

### Risk Mitigation

**High Risk:** Code modification safety
- Mitigation: Multi-layer verification, sandbox testing, user consent gates

**Medium Risk:** Skill extraction quality
- Mitigation: Verifier-guided extraction, quality scoring, manual review

**Low Risk:** Memory federation convergence
- Mitigation: Proven gossip protocols, conflict resolution strategies

---

# 2. Architecture Deep Dive

## 2.1 System Overview

The Self-Evolution AGI Core consists of five integrated subsystems that work together to enable recursive self-improvement:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SELF-EVOLUTION AGI CORE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │    MOSS      │  │   Ratchet    │  │  Trace2Skill │        │
│  │ Source-Level │→ │ Verification │→ │  Extraction  │        │
│  │  Rewriting   │  │   Pipeline   │  │              │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│         ↓                  ↓                  ↓                │
│  ┌──────────────────────────────────────────────────┐         │
│  │           Skill Weaving Framework                │         │
│  │  • Atomic Skills    • Composite Skills           │         │
│  │  • Competence Map   • Library Management         │         │
│  └──────────────────────────────────────────────────┘         │
│         ↓                                                      │
│  ┌──────────────────────────────────────────────────┐         │
│  │         DecentMem Federation Layer               │         │
│  │  • Gossip Protocol  • Conflict Resolution        │         │
│  │  • Vector Clocks    • Eventual Consistency       │         │
│  └──────────────────────────────────────────────────┘         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    Existing Lyra v4.0.0                         │
│  • Multi-Agent Orchestration  • 5-Tier Memory System           │
│  • 946 Tests Passing          • 8 Core Packages                │
└─────────────────────────────────────────────────────────────────┘
```

### Integration with Existing Lyra Packages

| Existing Package | Integration Point | Enhancement |
|------------------|-------------------|-------------|
| `lyra-evolution` | MOSS + Ratchet replace current evolution engine | Source-level modification vs prompt-level |
| `lyra-skills` | Trace2Skill + Skill Weaving extend skill system | Automatic extraction + composition |
| `lyra-memory` | DecentMem adds federation layer | Decentralized sharing across agents |
| `lyra-orchestration` | Coordinates evolution pipeline | Multi-agent evolution workflows |
| `lyra-core` | Base types and interfaces | Evolution primitives |
| `lyra-meta-evolution` | Meta-learning layer | Evolution of evolution strategies |
| `lyra-gossip-memory` | DecentMem implementation target | Gossip protocol foundation |
| `lyra-competence-map` | Skill Weaving competence tracking | Regression protection |

## 2.2 MOSS Integration: Source-Level Self-Modification

### 2.2.1 Architecture

MOSS (Model-Oriented Source-level Self-modification) enables Lyra to modify its own Python source code safely and effectively.

```python
# Architecture Components
┌─────────────────────────────────────────────────────────┐
│                    MOSS Controller                       │
│  • Modification Planner                                 │
│  • User Consent Manager                                 │
│  • Rollback Coordinator                                 │
└────────────┬────────────────────────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼────┐      ┌────▼─────┐
│  AST   │      │   Code   │
│ Parser │      │Generator │
└───┬────┘      └────┬─────┘
    │                │
    └────────┬───────┘
             │
    ┌────────▼────────┐
    │  Sandbox Tester │
    │  • Isolated Env │
    │  • Test Runner  │
    │  • Verifier     │
    └─────────────────┘
```

### 2.2.2 Core Components

**1. AST Parser**
```python
from ast import parse, NodeTransformer, unparse
from typing import List, Dict, Any

class MOSSParser:
    """Parse Python source into manipulable AST."""
    
    def parse_file(self, filepath: str) -> ast.Module:
        """Parse Python file into AST."""
        with open(filepath, 'r') as f:
            source = f.read()
        return parse(source)
    
    def extract_functions(self, tree: ast.Module) -> List[ast.FunctionDef]:
        """Extract all function definitions."""
        return [node for node in ast.walk(tree) 
                if isinstance(node, ast.FunctionDef)]
    
    def extract_classes(self, tree: ast.Module) -> List[ast.ClassDef]:
        """Extract all class definitions."""
        return [node for node in ast.walk(tree) 
                if isinstance(node, ast.ClassDef)]
```

**2. Code Generator**
```python
class MOSSGenerator:
    """Generate code modifications from high-level intent."""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    async def generate_modification(
        self,
        current_code: str,
        intent: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate code modification from intent.
        
        Args:
            current_code: Current implementation
            intent: What to improve (e.g., "optimize for speed")
            context: Additional context (test results, profiling data)
        
        Returns:
            Modified code as string
        """
        prompt = f"""
        Current implementation:
        ```python
        {current_code}
        ```
        
        Improvement intent: {intent}
        Context: {context}
        
        Generate improved implementation that:
        1. Maintains API compatibility
        2. Improves on the stated intent
        3. Preserves existing functionality
        4. Includes docstrings and type hints
        
        Return only the improved code, no explanations.
        """
        
        response = await self.llm.generate(prompt)
        return self._extract_code(response)
```

**3. Sandbox Tester**
```python
import subprocess
import tempfile
from pathlib import Path

class SandboxTester:
    """Test code modifications in isolated environment."""
    
    def __init__(self, test_timeout: int = 60):
        self.timeout = test_timeout
    
    def test_modification(
        self,
        modified_code: str,
        test_suite: str,
        dependencies: List[str]
    ) -> TestResult:
        """Test modified code in sandbox.
        
        Creates temporary venv, installs dependencies,
        runs test suite, returns results.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create isolated environment
            venv_path = Path(tmpdir) / "venv"
            subprocess.run(["python", "-m", "venv", str(venv_path)])
            
            # Install dependencies
            pip = venv_path / "bin" / "pip"
            for dep in dependencies:
                subprocess.run([str(pip), "install", dep])
            
            # Write modified code
            code_path = Path(tmpdir) / "modified.py"
            code_path.write_text(modified_code)
            
            # Run tests
            pytest = venv_path / "bin" / "pytest"
            result = subprocess.run(
                [str(pytest), test_suite, "-v"],
                capture_output=True,
                timeout=self.timeout
            )
            
            return TestResult(
                passed=result.returncode == 0,
                stdout=result.stdout.decode(),
                stderr=result.stderr.decode()
            )
```

**4. User Consent Manager**
```python
from dataclasses import dataclass
from enum import Enum

class ConsentDecision(Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"

@dataclass
class ModificationProposal:
    """Proposed code modification for user review."""
    file_path: str
    current_code: str
    modified_code: str
    intent: str
    test_results: TestResult
    impact_analysis: Dict[str, Any]
    
class ConsentManager:
    """Manage user consent for code modifications."""
    
    async def request_consent(
        self,
        proposal: ModificationProposal
    ) -> ConsentDecision:
        """Present modification to user and get decision.
        
        Shows:
        - Diff of changes
        - Test results
        - Impact analysis
        - Rollback plan
        """
        # Generate diff
        diff = self._generate_diff(
            proposal.current_code,
            proposal.modified_code
        )
        
        # Present to user
        print(f"\n{'='*60}")
        print(f"MODIFICATION PROPOSAL: {proposal.file_path}")
        print(f"Intent: {proposal.intent}")
        print(f"\nChanges:")
        print(diff)
        print(f"\nTest Results: {'✅ PASSED' if proposal.test_results.passed else '❌ FAILED'}")
        print(f"\nImpact Analysis:")
        for key, value in proposal.impact_analysis.items():
            print(f"  {key}: {value}")
        print(f"{'='*60}\n")
        
        # Get user decision
        response = input("Approve modification? (yes/no/defer): ").lower()
        
        if response == "yes":
            return ConsentDecision.APPROVED
        elif response == "no":
            return ConsentDecision.REJECTED
        else:
            return ConsentDecision.DEFERRED
```

### 2.2.3 MOSS Workflow

```
1. IDENTIFY IMPROVEMENT OPPORTUNITY
   ↓
   • Analyze execution traces
   • Detect performance bottlenecks
   • Identify code smells
   ↓
2. PARSE CURRENT IMPLEMENTATION
   ↓
   • Load source file
   • Parse into AST
   • Extract target function/class
   ↓
3. GENERATE MODIFICATION
   ↓
   • LLM generates improved code
   • Validate syntax
   • Check API compatibility
   ↓
4. SANDBOX TESTING
   ↓
   • Create isolated environment
   • Run comprehensive tests
   • Verify no regressions
   ↓
5. REQUEST USER CONSENT
   ↓
   • Show diff and impact
   • User approves/rejects/defers
   ↓
6. APPLY MODIFICATION (if approved)
   ↓
   • Backup original code
   • Apply changes atomically
   • Update version control
   ↓
7. MONITOR PERFORMANCE
   ↓
   • Track metrics
   • Detect regressions
   • Rollback if needed
```

### 2.2.4 Safety Guarantees

**Multi-Layer Verification:**
1. **Syntax Check** - AST parsing validates Python syntax
2. **Type Check** - mypy validates type hints
3. **Test Suite** - Comprehensive tests in sandbox
4. **User Consent** - Human approval required
5. **Rollback Support** - Automatic revert on failure

**Isolation:**
- Sandbox testing in temporary venv
- No access to production data
- Resource limits (CPU, memory, time)

**Auditability:**
- All modifications logged
- Git commits for version control
- Rollback history maintained

## 2.3 Ratchet Pipeline: Deterministic Verification

### 2.3.1 The 5-Step Pipeline

Ratchet ensures every modification is verified deterministically before deployment, with automatic rollback on failure.

```
┌─────────────────────────────────────────────────────────────┐
│                    RATCHET PIPELINE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: EXTRACT                                           │
│  ┌─────────────────────────────────────────────┐          │
│  │ • Identify improvement opportunity          │          │
│  │ • Analyze execution trajectory              │          │
│  │ • Score potential impact                    │          │
│  └─────────────────────────────────────────────┘          │
│                      ↓                                      │
│  Step 2: VERIFY                                            │
│  ┌─────────────────────────────────────────────┐          │
│  │ • Formal verification (where possible)      │          │
│  │ • Property-based testing                    │          │
│  │ • Competence regression check               │          │
│  └─────────────────────────────────────────────┘          │
│                      ↓                                      │
│  Step 3: TEST                                              │
│  ┌─────────────────────────────────────────────┐          │
│  │ • Unit tests in sandbox                     │          │
│  │ • Integration tests                         │          │
│  │ • Performance benchmarks                    │          │
│  └─────────────────────────────────────────────┘          │
│                      ↓                                      │
│  Step 4: DEPLOY                                            │
│  ┌─────────────────────────────────────────────┐          │
│  │ • Atomic deployment                         │          │
│  │ • Version control commit                    │          │
│  │ • Rollback checkpoint                       │          │
│  └─────────────────────────────────────────────┘          │
│                      ↓                                      │
│  Step 5: MONITOR                                           │
│  ┌─────────────────────────────────────────────┐          │
│  │ • Continuous competence tracking            │          │
│  │ • Performance metrics                       │          │
│  │ • Automatic rollback on regression          │          │
│  └─────────────────────────────────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3.2 Core Components

**1. Extraction Engine**
```python
from dataclasses import dataclass
from typing import List, Optional
import numpy as np

@dataclass
class ImprovementOpportunity:
    """Identified opportunity for self-improvement."""
    target_file: str
    target_function: str
    issue_type: str  # "performance", "correctness", "maintainability"
    evidence: List[str]  # Execution traces, profiling data
    impact_score: float  # 0.0-1.0
    confidence: float  # 0.0-1.0

class ExtractionEngine:
    """Identify improvement opportunities from execution history."""
    
    def __init__(self, trajectory_store):
        self.trajectories = trajectory_store
        self.threshold_impact = 0.5
        self.threshold_confidence = 0.7
    
    def extract_opportunities(
        self,
        lookback_window: int = 100
    ) -> List[ImprovementOpportunity]:
        """Extract improvement opportunities from recent trajectories.
        
        Analyzes:
        - Performance bottlenecks (slow functions)
        - Correctness issues (test failures)
        - Maintainability problems (code smells)
        """
        opportunities = []
        
        # Get recent trajectories
        recent = self.trajectories.get_recent(lookback_window)
        
        # Analyze performance
        perf_issues = self._analyze_performance(recent)
        opportunities.extend(perf_issues)
        
        # Analyze correctness
        correctness_issues = self._analyze_correctness(recent)
        opportunities.extend(correctness_issues)
        
        # Analyze maintainability
        maint_issues = self._analyze_maintainability(recent)
        opportunities.extend(maint_issues)
        
        # Filter by thresholds
        filtered = [
            opp for opp in opportunities
            if opp.impact_score >= self.threshold_impact
            and opp.confidence >= self.threshold_confidence
        ]
        
        # Sort by impact * confidence
        filtered.sort(
            key=lambda x: x.impact_score * x.confidence,
            reverse=True
        )
        
        return filtered
    
    def _analyze_performance(
        self,
        trajectories: List[Trajectory]
    ) -> List[ImprovementOpportunity]:
        """Identify performance bottlenecks."""
        opportunities = []
        
        # Aggregate execution times by function
        func_times = {}
        for traj in trajectories:
            for span in traj.spans:
                if span.function_name not in func_times:
                    func_times[span.function_name] = []
                func_times[span.function_name].append(span.duration_ms)
        
        # Find slow functions (p95 > 1000ms)
        for func_name, times in func_times.items():
            p95 = np.percentile(times, 95)
            if p95 > 1000:
                opportunities.append(ImprovementOpportunity(
                    target_file=self._get_file_for_function(func_name),
                    target_function=func_name,
                    issue_type="performance",
                    evidence=[f"p95 latency: {p95:.0f}ms"],
                    impact_score=min(p95 / 5000, 1.0),
                    confidence=0.9
                ))
        
        return opportunities
```

**2. Verification Engine**
```python
from typing import Tuple, List
import ast

class VerificationEngine:
    """Verify code modifications before deployment."""
    
    def verify_modification(
        self,
        original_code: str,
        modified_code: str,
        test_suite: str
    ) -> Tuple[bool, List[str]]:
        """Comprehensive verification of modification.
        
        Returns:
            (passed, issues) - True if all checks pass, list of issues
        """
        issues = []
        
        # 1. Syntax verification
        if not self._verify_syntax(modified_code):
            issues.append("Syntax error in modified code")
        
        # 2. Type verification
        type_issues = self._verify_types(modified_code)
        issues.extend(type_issues)
        
        # 3. API compatibility
        if not self._verify_api_compatibility(original_code, modified_code):
            issues.append("API compatibility broken")
        
        # 4. Property-based testing
        property_issues = self._verify_properties(modified_code)
        issues.extend(property_issues)
        
        # 5. Test suite
        test_result = self._run_tests(modified_code, test_suite)
        if not test_result.passed:
            issues.append(f"Test failures: {test_result.failures}")
        
        # 6. Competence regression check
        if not self._verify_no_regression(original_code, modified_code):
            issues.append("Competence regression detected")
        
        return len(issues) == 0, issues
    
    def _verify_syntax(self, code: str) -> bool:
        """Verify Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def _verify_types(self, code: str) -> List[str]:
        """Run mypy type checking."""
        import subprocess
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as f:
            f.write(code)
            f.flush()
            
            result = subprocess.run(
                ['mypy', f.name, '--strict'],
                capture_output=True
            )
            
            if result.returncode != 0:
                return [result.stdout.decode()]
            return []
    
    def _verify_api_compatibility(
        self,
        original: str,
        modified: str
    ) -> bool:
        """Verify API signatures haven't changed."""
        orig_tree = ast.parse(original)
        mod_tree = ast.parse(modified)
        
        orig_funcs = self._extract_function_signatures(orig_tree)
        mod_funcs = self._extract_function_signatures(mod_tree)
        
        # Check all original functions still exist with same signature
        for name, sig in orig_funcs.items():
            if name not in mod_funcs:
                return False
            if mod_funcs[name] != sig:
                return False
        
        return True
    
    def _verify_no_regression(
        self,
        original: str,
        modified: str
    ) -> bool:
        """Verify no competence regression.
        
        Runs both versions on benchmark tasks and compares performance.
        """
        from lyra_competence_map import CompetenceTracker
        
        tracker = CompetenceTracker()
        
        # Benchmark original
        orig_score = tracker.benchmark(original)
        
        # Benchmark modified
        mod_score = tracker.benchmark(modified)
        
        # Modified must be >= original (no regression)
        return mod_score >= orig_score
```

**3. Test Orchestrator**
```python
from dataclasses import dataclass
from typing import List

@dataclass
class TestResult:
    """Result of test execution."""
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    duration_seconds: float
    failures: List[str]
    coverage_percent: float

class TestOrchestrator:
    """Orchestrate comprehensive testing in sandbox."""
    
    def __init__(self, sandbox_tester: SandboxTester):
        self.sandbox = sandbox_tester
    
    def run_comprehensive_tests(
        self,
        modified_code: str,
        test_suite: str
    ) -> TestResult:
        """Run all test types: unit, integration, performance.
        
        Returns aggregated test results.
        """
        results = []
        
        # 1. Unit tests
        unit_result = self.sandbox.test_modification(
            modified_code,
            test_suite + "/unit",
            dependencies=[]
        )
        results.append(unit_result)
        
        # 2. Integration tests
        integration_result = self.sandbox.test_modification(
            modified_code,
            test_suite + "/integration",
            dependencies=["pytest-asyncio"]
        )
        results.append(integration_result)
        
        # 3. Performance benchmarks
        perf_result = self._run_benchmarks(modified_code)
        results.append(perf_result)
        
        # Aggregate results
        return self._aggregate_results(results)
```

**4. Deployment Manager**
```python
import shutil
from pathlib import Path
from datetime import datetime

class DeploymentManager:
    """Manage atomic deployment with rollback support."""
    
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def deploy(
        self,
        target_file: Path,
        modified_code: str
    ) -> str:
        """Deploy modification atomically.
        
        Returns:
            checkpoint_id - ID for rollback
        """
        # Create checkpoint
        checkpoint_id = self._create_checkpoint(target_file)
        
        # Write modified code atomically
        temp_file = target_file.with_suffix('.tmp')
        temp_file.write_text(modified_code)
        temp_file.replace(target_file)
        
        # Git commit
        self._git_commit(target_file, checkpoint_id)
        
        return checkpoint_id
    
    def rollback(self, checkpoint_id: str) -> None:
        """Rollback to checkpoint."""
        checkpoint_path = self.backup_dir / checkpoint_id
        
        # Restore from backup
        metadata = self._load_checkpoint_metadata(checkpoint_id)
        target_file = Path(metadata['target_file'])
        
        shutil.copy(checkpoint_path / 'backup.py', target_file)
        
        # Git revert
        self._git_revert(checkpoint_id)
    
    def _create_checkpoint(self, target_file: Path) -> str:
        """Create backup checkpoint."""
        checkpoint_id = f"checkpoint_{datetime.now().isoformat()}"
        checkpoint_path = self.backup_dir / checkpoint_id
        checkpoint_path.mkdir()
        
        # Backup original file
        shutil.copy(target_file, checkpoint_path / 'backup.py')
        
        # Save metadata
        metadata = {
            'target_file': str(target_file),
            'timestamp': datetime.now().isoformat(),
            'git_commit': self._get_current_commit()
        }
        self._save_checkpoint_metadata(checkpoint_id, metadata)
        
        return checkpoint_id
```

**5. Competence Monitor**
```python
from collections import deque
import numpy as np

class CompetenceMonitor:
    """Monitor competence metrics and detect regressions."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics_history = deque(maxlen=window_size)
        self.baseline_score = None
    
    def record_metric(
        self,
        task_type: str,
        success: bool,
        duration_ms: float,
        quality_score: float
    ) -> None:
        """Record execution metric."""
        self.metrics_history.append({
            'task_type': task_type,
            'success': success,
            'duration_ms': duration_ms,
            'quality_score': quality_score,
            'timestamp': datetime.now()
        })
    
    def detect_regression(self) -> Tuple[bool, Optional[str]]:
        """Detect competence regression.
        
        Returns:
            (is_regression, reason)
        """
        if len(self.metrics_history) < 20:
            return False, None
        
        # Calculate current competence score
        current_score = self._calculate_competence_score(
            list(self.metrics_history)[-20:]
        )
        
        # Compare to baseline
        if self.baseline_score is None:
            self.baseline_score = current_score
            return False, None
        
        # Regression if current < 95% of baseline
        if current_score < 0.95 * self.baseline_score:
            return True, f"Competence dropped from {self.baseline_score:.2f} to {current_score:.2f}"
        
        return False, None
    
    def _calculate_competence_score(
        self,
        metrics: List[Dict]
    ) -> float:
        """Calculate aggregate competence score.
        
        Combines:
        - Success rate (40%)
        - Average quality (40%)
        - Speed (20%)
        """
        success_rate = np.mean([m['success'] for m in metrics])
        avg_quality = np.mean([m['quality_score'] for m in metrics])
        avg_speed = 1.0 / (1.0 + np.mean([m['duration_ms'] for m in metrics]) / 1000)
        
        return 0.4 * success_rate + 0.4 * avg_quality + 0.2 * avg_speed
```

### 2.3.3 Ratchet Guarantees

**Determinism:**
- Every step produces reproducible results
- Same input → same output
- No non-deterministic operations in verification

**Safety:**
- Zero regressions (verified before deployment)
- Automatic rollback on failure
- Checkpoint-based recovery

**Auditability:**
- Every modification logged
- Full verification trace
- Rollback history maintained

## 2.4 Trace2Skill: Automatic Skill Extraction

### 2.4.1 Architecture

Trace2Skill automatically extracts reusable skills from successful execution trajectories using verifier-guided refinement.

```
┌─────────────────────────────────────────────────────────────┐
│                  TRACE2SKILL PIPELINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. TRAJECTORY CAPTURE                                     │
│  ┌─────────────────────────────────────────────┐          │
│  │ • Execution spans with timing               │          │
│  │ • Input/output pairs                        │          │
│  │ • Context and metadata                      │          │
│  └─────────────────────────────────────────────┘          │
│                      ↓                                      │
│  2. CANDIDATE SCORING                                      │
│  ┌─────────────────────────────────────────────┐          │
│  │ • Success rate                              │          │
│  │ • Generality (applies to multiple tasks)    │          │
│  │ • Efficiency (time/cost)                    │          │
│  │ • Novelty (not already in library)          │          │
│  └─────────────────────────────────────────────┘          │
│                      ↓                                      │
│  3. SKILL EXTRACTION                                       │
│  ┌─────────────────────────────────────────────┐          │
│  │ • LLM extracts pattern                      │          │
│  │ • Generate SKILL.md                         │          │
│  │ • Create test cases                         │          │
│  └─────────────────────────────────────────────┘          │
│                      ↓                                      │
│  4. VERIFIER-GUIDED REFINEMENT                            │
│  ┌─────────────────────────────────────────────┐          │
│  │ • Verify skill correctness                  │          │
│  │ • Refine based on feedback                  │          │
│  │ • Iterate until verified                    │          │
│  └─────────────────────────────────────────────┘          │
│                      ↓                                      │
│  5. LIBRARY PROMOTION                                      │
│  ┌─────────────────────────────────────────────┐          │
│  │ • User review (gated)                       │          │
│  │ • Add to skill library                      │          │
│  │ • Update competence map                     │          │
│  └─────────────────────────────────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.4.2 Core Components

**1. Trajectory Capture**
```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class ExecutionSpan:
    """Single execution span in trajectory."""
    span_id: str
    parent_id: Optional[str]
    function_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    inputs: Dict[str, Any]
    outputs: Any
    success: bool
    error: Optional[str] = None

@dataclass
class Trajectory:
    """Complete execution trajectory."""
    trajectory_id: str
    task_description: str
    agent_id: str
    start_time: datetime
    end_time: datetime
    total_duration_ms: float
    spans: List[ExecutionSpan] = field(default_factory=list)
    success: bool = False
    final_output: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_span(self, span: ExecutionSpan) -> None:
        """Add execution span to trajectory."""
        self.spans.append(span)
    
    def get_critical_path(self) -> List[ExecutionSpan]:
        """Extract critical path (longest duration chain)."""
        # Build span tree
        span_map = {s.span_id: s for s in self.spans}
        
        # Find root spans (no parent)
        roots = [s for s in self.spans if s.parent_id is None]
        
        # DFS to find longest path
        def dfs(span: ExecutionSpan) -> List[ExecutionSpan]:
            children = [s for s in self.spans if s.parent_id == span.span_id]
            if not children:
                return [span]
            
            child_paths = [dfs(child) for child in children]
            longest = max(child_paths, key=lambda p: sum(s.duration_ms for s in p))
            return [span] + longest
        
        paths = [dfs(root) for root in roots]
        return max(paths, key=lambda p: sum(s.duration_ms for s in p))

class TrajectoryCapture:
    """Capture execution trajectories for skill extraction."""
    
    def __init__(self, storage_path: Path):
        self.storage = storage_path
        self.storage.mkdir(parents=True, exist_ok=True)
        self.current_trajectory: Optional[Trajectory] = None
        self.span_stack: List[str] = []
    
    def start_trajectory(
        self,
        task_description: str,
        agent_id: str
    ) -> str:
        """Start capturing new trajectory."""
        trajectory_id = f"traj_{datetime.now().isoformat()}"
        self.current_trajectory = Trajectory(
            trajectory_id=trajectory_id,
            task_description=task_description,
            agent_id=agent_id,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration_ms=0.0
        )
        return trajectory_id
    
    def start_span(
        self,
        function_name: str,
        inputs: Dict[str, Any]
    ) -> str:
        """Start execution span."""
        span_id = f"span_{len(self.current_trajectory.spans)}"
        parent_id = self.span_stack[-1] if self.span_stack else None
        
        span = ExecutionSpan(
            span_id=span_id,
            parent_id=parent_id,
            function_name=function_name,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration_ms=0.0,
            inputs=inputs,
            outputs=None,
            success=False
        )
        
        self.current_trajectory.add_span(span)
        self.span_stack.append(span_id)
        return span_id
    
    def end_span(
        self,
        span_id: str,
        outputs: Any,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """End execution span."""
        span = next(s for s in self.current_trajectory.spans if s.span_id == span_id)
        span.end_time = datetime.now()
        span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
        span.outputs = outputs
        span.success = success
        span.error = error
        
        self.span_stack.pop()
    
    def end_trajectory(
        self,
        success: bool,
        final_output: Any
    ) -> Trajectory:
        """End trajectory capture and save."""
        self.current_trajectory.end_time = datetime.now()
        self.current_trajectory.total_duration_ms = (
            self.current_trajectory.end_time - self.current_trajectory.start_time
        ).total_seconds() * 1000
        self.current_trajectory.success = success
        self.current_trajectory.final_output = final_output
        
        # Save to disk
        self._save_trajectory(self.current_trajectory)
        
        return self.current_trajectory
```

**2. Candidate Scoring**
```python
import numpy as np
from typing import List, Tuple

class CandidateScorer:
    """Score trajectories for skill extraction worthiness."""
    
    def __init__(self, skill_library):
        self.library = skill_library
        self.min_score = 0.6  # Minimum score for extraction
    
    def score_trajectory(self, trajectory: Trajectory) -> float:
        """Score trajectory on multiple dimensions.
        
        Returns score 0.0-1.0 indicating extraction worthiness.
        """
        # 1. Success rate (40%)
        success_score = 1.0 if trajectory.success else 0.0
        
        # 2. Generality (30%)
        generality_score = self._score_generality(trajectory)
        
        # 3. Efficiency (20%)
        efficiency_score = self._score_efficiency(trajectory)
        
        # 4. Novelty (10%)
        novelty_score = self._score_novelty(trajectory)
        
        total_score = (
            0.4 * success_score +
            0.3 * generality_score +
            0.2 * efficiency_score +
            0.1 * novelty_score
        )
        
        return total_score
    
    def _score_generality(self, trajectory: Trajectory) -> float:
        """Score how general/reusable the pattern is.
        
        Higher score = more general pattern.
        """
        # Check if pattern appears in multiple contexts
        similar_trajectories = self._find_similar_trajectories(trajectory)
        
        if len(similar_trajectories) < 3:
            return 0.3  # Too specific
        elif len(similar_trajectories) < 10:
            return 0.7  # Moderately general
        else:
            return 1.0  # Highly general
    
    def _score_efficiency(self, trajectory: Trajectory) -> float:
        """Score efficiency (time and cost).
        
        Higher score = more efficient.
        """
        # Compare to baseline for similar tasks
        baseline_duration = self._get_baseline_duration(trajectory.task_description)
        
        if baseline_duration is None:
            return 0.5  # No baseline, neutral score
        
        ratio = trajectory.total_duration_ms / baseline_duration
        
        if ratio < 0.5:
            return 1.0  # 2x faster
        elif ratio < 0.8:
            return 0.8  # Moderately faster
        elif ratio < 1.2:
            return 0.5  # Similar speed
        else:
            return 0.2  # Slower
    
    def _score_novelty(self, trajectory: Trajectory) -> float:
        """Score novelty (not already in library).
        
        Higher score = more novel.
        """
        # Extract pattern signature
        pattern = self._extract_pattern_signature(trajectory)
        
        # Check similarity to existing skills
        max_similarity = 0.0
        for skill in self.library.get_all_skills():
            similarity = self._compute_similarity(pattern, skill.pattern)
            max_similarity = max(max_similarity, similarity)
        
        # Novel if similarity < 0.7
        return 1.0 - max_similarity
    
    def get_extraction_candidates(
        self,
        trajectories: List[Trajectory],
        top_k: int = 10
    ) -> List[Tuple[Trajectory, float]]:
        """Get top candidates for skill extraction.
        
        Returns:
            List of (trajectory, score) sorted by score descending
        """
        scored = [
            (traj, self.score_trajectory(traj))
            for traj in trajectories
        ]
        
        # Filter by minimum score
        filtered = [(t, s) for t, s in scored if s >= self.min_score]
        
        # Sort by score descending
        filtered.sort(key=lambda x: x[1], reverse=True)
        
        return filtered[:top_k]
```

**3. Skill Extractor**
```python
from pathlib import Path

class SkillExtractor:
    """Extract reusable skills from trajectories."""
    
    def __init__(self, llm_client, verifier):
        self.llm = llm_client
        self.verifier = verifier
    
    async def extract_skill(
        self,
        trajectory: Trajectory
    ) -> Optional[Skill]:
        """Extract skill from trajectory.
        
        Uses LLM to identify pattern and generate SKILL.md.
        """
        # 1. Analyze trajectory
        analysis = await self._analyze_trajectory(trajectory)
        
        # 2. Generate skill description
        skill_desc = await self._generate_skill_description(trajectory, analysis)
        
        # 3. Generate SKILL.md
        skill_md = await self._generate_skill_markdown(skill_desc)
        
        # 4. Generate test cases
        test_cases = await self._generate_test_cases(trajectory, skill_desc)
        
        # 5. Create skill object
        skill = Skill(
            name=skill_desc['name'],
            description=skill_desc['description'],
            triggers=skill_desc['triggers'],
            content=skill_md,
            test_cases=test_cases,
            metadata={
                'extracted_from': trajectory.trajectory_id,
                'extraction_date': datetime.now().isoformat(),
                'success_rate': 1.0  # Initial
            }
        )
        
        return skill
    
    async def _analyze_trajectory(
        self,
        trajectory: Trajectory
    ) -> Dict[str, Any]:
        """Analyze trajectory to identify pattern."""
        prompt = f"""
        Analyze this execution trajectory and identify the reusable pattern:
        
        Task: {trajectory.task_description}
        Duration: {trajectory.total_duration_ms:.0f}ms
        Success: {trajectory.success}
        
        Critical path:
        {self._format_critical_path(trajectory.get_critical_path())}
        
        Identify:
        1. What problem does this solve?
        2. What is the general pattern?
        3. What are the key steps?
        4. What makes it reusable?
        5. What are the prerequisites?
        """
        
        response = await self.llm.generate(prompt)
        return self._parse_analysis(response)
    
    async def _generate_skill_description(
        self,
        trajectory: Trajectory,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate skill description."""
        prompt = f"""
        Based on this analysis, create a skill description:
        
        {analysis}
        
        Generate:
        1. Skill name (kebab-case, e.g., "parallel-exploration")
        2. One-line description
        3. Trigger phrases (when to use this skill)
        4. Tags for categorization
        
        Format as JSON.
        """
        
        response = await self.llm.generate(prompt)
        return json.loads(response)
    
    async def _generate_skill_markdown(
        self,
        skill_desc: Dict[str, Any]
    ) -> str:
        """Generate SKILL.md content."""
        prompt = f"""
        Generate a SKILL.md file for this skill:
        
        Name: {skill_desc['name']}
        Description: {skill_desc['description']}
        
        Include:
        1. Frontmatter (name, description, triggers, tags)
        2. Overview section
        3. When to use
        4. Step-by-step instructions
        5. Examples
        6. Common pitfalls
        
        Follow Claude Code skill format.
        """
        
        response = await self.llm.generate(prompt)
        return response
```

**4. Verifier-Guided Refinement**
```python
class SkillVerifier:
    """Verify and refine extracted skills."""
    
    def __init__(self, test_runner):
        self.test_runner = test_runner
        self.max_iterations = 3
    
    async def verify_and_refine(
        self,
        skill: Skill,
        extractor: SkillExtractor
    ) -> Tuple[bool, Skill]:
        """Verify skill and refine if needed.
        
        Returns:
            (verified, refined_skill)
        """
        for iteration in range(self.max_iterations):
            # Run verification tests
            result = await self._verify_skill(skill)
            
            if result.passed:
                return True, skill
            
            # Refine based on failures
            skill = await self._refine_skill(skill, result, extractor)
        
        # Failed to verify after max iterations
        return False, skill
    
    async def _verify_skill(self, skill: Skill) -> VerificationResult:
        """Run verification tests on skill."""
        results = []
        
        # 1. Syntax check
        syntax_ok = self._check_syntax(skill.content)
        results.append(('syntax', syntax_ok))
        
        # 2. Run test cases
        for test_case in skill.test_cases:
            test_result = await self.test_runner.run_test(skill, test_case)
            results.append((f'test_{test_case.name}', test_result.passed))
        
        # 3. Check completeness
        completeness_ok = self._check_completeness(skill)
        results.append(('completeness', completeness_ok))
        
        passed = all(r[1] for r in results)
        failures = [r[0] for r in results if not r[1]]
        
        return VerificationResult(passed=passed, failures=failures)
    
    async def _refine_skill(
        self,
        skill: Skill,
        result: VerificationResult,
        extractor: SkillExtractor
    ) -> Skill:
        """Refine skill based on verification failures."""
        prompt = f"""
        This skill failed verification:
        
        {skill.content}
        
        Failures: {result.failures}
        
        Refine the skill to fix these issues while maintaining its core functionality.
        """
        
        refined_content = await extractor.llm.generate(prompt)
        
        skill.content = refined_content
        skill.metadata['refinement_count'] = skill.metadata.get('refinement_count', 0) + 1
        
        return skill
```

### 2.4.3 Integration with Existing Skills System

Trace2Skill extends `lyra-skills` package:

```python
# packages/lyra-skills/src/lyra_skills/extractor/trace2skill.py

from lyra_skills.extractor import candidate, refiner, builder, promoter

class Trace2SkillPipeline:
    """Complete Trace2Skill pipeline."""
    
    def __init__(self, config):
        self.capture = TrajectoryCapture(config.storage_path)
        self.scorer = CandidateScorer(config.skill_library)
        self.extractor = SkillExtractor(config.llm_client, config.verifier)
        self.verifier = SkillVerifier(config.test_runner)
        self.promoter = promoter.SkillPromoter(config.user_library_path)
    
    async def process_trajectory(self, trajectory: Trajectory) -> Optional[Skill]:
        """Process single trajectory through pipeline."""
        # 1. Score
        score = self.scorer.score_trajectory(trajectory)
        if score < self.scorer.min_score:
            return None
        
        # 2. Extract
        skill = await self.extractor.extract_skill(trajectory)
        if skill is None:
            return None
        
        # 3. Verify and refine
        verified, refined_skill = await self.verifier.verify_and_refine(
            skill, self.extractor
        )
        if not verified:
            return None
        
        # 4. Promote (with user review)
        promoted = await self.promoter.promote_skill(refined_skill)
        
        return refined_skill if promoted else None
```

## 2.5 Skill Weaving: Modular Composition

### 2.5.1 Architecture

Skill Weaving enables modular composition of atomic skills into powerful composite workflows with competence-aware retrieval.

```
┌─────────────────────────────────────────────────────────────┐
│                  SKILL WEAVING FRAMEWORK                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ATOMIC SKILLS (Building Blocks)                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│  │Localize │ │  Edit   │ │Test-Gen │ │Reproduce│         │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘         │
│       ↓           ↓           ↓           ↓                │
│  ┌──────────────────────────────────────────────┐         │
│  │         COMPOSITION ENGINE                   │         │
│  │  • Dependency resolution                     │         │
│  │  • Execution ordering                        │         │
│  │  • Context passing                           │         │
│  └──────────────────────────────────────────────┘         │
│       ↓                                                     │
│  COMPOSITE SKILLS (Workflows)                              │
│  ┌─────────────────────────────────────────────┐          │
│  │ TDD Sprint: localize → test-gen → edit →   │          │
│  │             test → refactor → review        │          │
│  └─────────────────────────────────────────────┘          │
│       ↓                                                     │
│  ┌──────────────────────────────────────────────┐         │
│  │      COMPETENCE-AWARE RETRIEVAL              │         │
│  │  • Task difficulty estimation                │         │
│  │  • Skill competence matching                 │         │
│  │  • Regression protection                     │         │
│  └──────────────────────────────────────────────┘         │
│       ↓                                                     │
│  ┌──────────────────────────────────────────────┐         │
│  │         LIBRARY MANAGEMENT                   │         │
│  │  • Versioning (semver)                       │         │
│  │  • Deprecation tracking                      │         │
│  │  • Usage analytics                           │         │
│  └──────────────────────────────────────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.5.2 Core Components

**1. Skill Definition**
```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class SkillType(Enum):
    ATOMIC = "atomic"
    COMPOSITE = "composite"

@dataclass
class SkillDependency:
    """Dependency on another skill."""
    skill_name: str
    version_constraint: str  # e.g., ">=1.0.0,<2.0.0"
    optional: bool = False

@dataclass
class Skill:
    """Skill definition."""
    name: str
    version: str  # Semantic versioning
    type: SkillType
    description: str
    triggers: List[str]
    tags: List[str]
    content: str  # SKILL.md content
    dependencies: List[SkillDependency] = field(default_factory=list)
    test_cases: List[Any] = field(default_factory=list)
    competence_score: float = 0.0  # 0.0-1.0
    usage_count: int = 0
    success_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_atomic(self) -> bool:
        return self.type == SkillType.ATOMIC
    
    def is_composite(self) -> bool:
        return self.type == SkillType.COMPOSITE

@dataclass
class CompositeSkill(Skill):
    """Composite skill composed of other skills."""
    steps: List[str] = field(default_factory=list)  # Ordered skill names
    
    def __post_init__(self):
        self.type = SkillType.COMPOSITE
```

**2. Composition Engine**
```python
from typing import List, Dict, Set
import networkx as nx

class CompositionEngine:
    """Compose atomic skills into composite workflows."""
    
    def __init__(self, skill_library):
        self.library = skill_library
    
    def compose(
        self,
        skill_names: List[str],
        name: str,
        description: str
    ) -> CompositeSkill:
        """Compose skills into workflow.
        
        Args:
            skill_names: Ordered list of skill names
            name: Name for composite skill
            description: Description of composite skill
        
        Returns:
            CompositeSkill with resolved dependencies
        """
        # 1. Resolve dependencies
        all_deps = self._resolve_dependencies(skill_names)
        
        # 2. Validate composition
        self._validate_composition(skill_names, all_deps)
        
        # 3. Create composite skill
        composite = CompositeSkill(
            name=name,
            version="1.0.0",
            type=SkillType.COMPOSITE,
            description=description,
            triggers=[],
            tags=["composite"],
            content=self._generate_composite_content(skill_names),
            dependencies=all_deps,
            steps=skill_names
        )
        
        return composite
    
    def _resolve_dependencies(
        self,
        skill_names: List[str]
    ) -> List[SkillDependency]:
        """Resolve all dependencies recursively."""
        resolved = set()
        to_resolve = set(skill_names)
        
        while to_resolve:
            skill_name = to_resolve.pop()
            if skill_name in resolved:
                continue
            
            skill = self.library.get_skill(skill_name)
            resolved.add(skill_name)
            
            # Add dependencies to resolve
            for dep in skill.dependencies:
                if dep.skill_name not in resolved:
                    to_resolve.add(dep.skill_name)
        
        # Convert to dependency list
        deps = []
        for skill_name in resolved:
            if skill_name not in skill_names:  # Don't include direct skills
                skill = self.library.get_skill(skill_name)
                deps.append(SkillDependency(
                    skill_name=skill_name,
                    version_constraint=f"^{skill.version}"
                ))
        
        return deps
    
    def _validate_composition(
        self,
        skill_names: List[str],
        dependencies: List[SkillDependency]
    ) -> None:
        """Validate composition is valid.
        
        Checks:
        - No circular dependencies
        - All dependencies available
        - Version constraints satisfied
        """
        # Build dependency graph
        graph = nx.DiGraph()
        
        for skill_name in skill_names:
            skill = self.library.get_skill(skill_name)
            graph.add_node(skill_name)
            
            for dep in skill.dependencies:
                graph.add_edge(skill_name, dep.skill_name)
        
        # Check for cycles
        if not nx.is_directed_acyclic_graph(graph):
            cycles = list(nx.simple_cycles(graph))
            raise ValueError(f"Circular dependencies detected: {cycles}")
        
        # Check all dependencies available
        for dep in dependencies:
            if not self.library.has_skill(dep.skill_name):
                raise ValueError(f"Dependency not found: {dep.skill_name}")
    
    def execute_composite(
        self,
        composite: CompositeSkill,
        context: Dict[str, Any]
    ) -> Any:
        """Execute composite skill.
        
        Executes steps in order, passing context between steps.
        """
        result = None
        
        for step_name in composite.steps:
            skill = self.library.get_skill(step_name)
            
            # Execute step
            result = self._execute_skill(skill, context)
            
            # Update context with result
            context[f"{step_name}_result"] = result
        
        return result
```

**3. Competence-Aware Retrieval**
```python
from typing import List, Tuple
import numpy as np

class CompetenceAwareRetrieval:
    """Retrieve skills based on task difficulty and skill competence."""
    
    def __init__(self, skill_library, competence_map):
        self.library = skill_library
        self.competence_map = competence_map
    
    def retrieve(
        self,
        query: str,
        task_difficulty: float,  # 0.0-1.0
        top_k: int = 5
    ) -> List[Tuple[Skill, float]]:
        """Retrieve skills matching query and difficulty.
        
        Args:
            query: Task description
            task_difficulty: Estimated difficulty (0=easy, 1=hard)
            top_k: Number of skills to return
        
        Returns:
            List of (skill, score) sorted by relevance
        """
        # 1. Get candidate skills by semantic similarity
        candidates = self.library.search(query, top_k=top_k * 3)
        
        # 2. Score each candidate
        scored = []
        for skill in candidates:
            score = self._score_skill(skill, query, task_difficulty)
            scored.append((skill, score))
        
        # 3. Sort by score and return top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    
    def _score_skill(
        self,
        skill: Skill,
        query: str,
        task_difficulty: float
    ) -> float:
        """Score skill for task.
        
        Combines:
        - Semantic similarity (40%)
        - Competence match (30%)
        - Success rate (20%)
        - Recency (10%)
        """
        # Semantic similarity
        semantic_score = self._compute_semantic_similarity(skill, query)
        
        # Competence match (skill competence should match task difficulty)
        competence_diff = abs(skill.competence_score - task_difficulty)
        competence_score = 1.0 - competence_diff
        
        # Success rate
        success_score = skill.success_rate
        
        # Recency (prefer recently used skills)
        recency_score = self._compute_recency_score(skill)
        
        total_score = (
            0.4 * semantic_score +
            0.3 * competence_score +
            0.2 * success_score +
            0.1 * recency_score
        )
        
        return total_score
    
    def update_competence(
        self,
        skill: Skill,
        task_difficulty: float,
        success: bool
    ) -> None:
        """Update skill competence based on execution result.
        
        Uses exponential moving average to track competence.
        """
        # Update success rate
        alpha = 0.1  # Learning rate
        skill.success_rate = (
            alpha * (1.0 if success else 0.0) +
            (1 - alpha) * skill.success_rate
        )
        
        # Update competence score (EMA of task difficulties where successful)
        if success:
            skill.competence_score = (
                alpha * task_difficulty +
                (1 - alpha) * skill.competence_score
            )
        
        # Update usage count
        skill.usage_count += 1
        
        # Save to competence map
        self.competence_map.update(skill.name, {
            'competence_score': skill.competence_score,
            'success_rate': skill.success_rate,
            'usage_count': skill.usage_count
        })
```

**4. Library Management**
```python
from pathlib import Path
import json
from typing import Optional, List
from packaging import version

class SkillLibrary:
    """Manage skill library with versioning."""
    
    def __init__(self, library_path: Path):
        self.path = library_path
        self.path.mkdir(parents=True, exist_ok=True)
        self.skills: Dict[str, List[Skill]] = {}  # name -> versions
        self._load_library()
    
    def add_skill(self, skill: Skill) -> None:
        """Add skill to library."""
        if skill.name not in self.skills:
            self.skills[skill.name] = []
        
        # Check if version already exists
        existing = self._get_skill_version(skill.name, skill.version)
        if existing:
            raise ValueError(f"Skill {skill.name} v{skill.version} already exists")
        
        self.skills[skill.name].append(skill)
        self._save_skill(skill)
    
    def get_skill(
        self,
        name: str,
        version_constraint: Optional[str] = None
    ) -> Optional[Skill]:
        """Get skill by name and optional version constraint.
        
        Args:
            name: Skill name
            version_constraint: Version constraint (e.g., ">=1.0.0,<2.0.0")
        
        Returns:
            Latest matching skill or None
        """
        if name not in self.skills:
            return None
        
        versions = self.skills[name]
        
        if version_constraint is None:
            # Return latest version
            return max(versions, key=lambda s: version.parse(s.version))
        
        # Filter by version constraint
        matching = [
            s for s in versions
            if self._matches_constraint(s.version, version_constraint)
        ]
        
        if not matching:
            return None
        
        # Return latest matching
        return max(matching, key=lambda s: version.parse(s.version))
    
    def deprecate_skill(
        self,
        name: str,
        version_str: str,
        reason: str
    ) -> None:
        """Deprecate skill version."""
        skill = self._get_skill_version(name, version_str)
        if not skill:
            raise ValueError(f"Skill {name} v{version_str} not found")
        
        skill.metadata['deprecated'] = True
        skill.metadata['deprecation_reason'] = reason
        self._save_skill(skill)
    
    def get_usage_stats(self, name: str) -> Dict[str, Any]:
        """Get usage statistics for skill."""
        if name not in self.skills:
            return {}
        
        versions = self.skills[name]
        total_usage = sum(s.usage_count for s in versions)
        avg_success = np.mean([s.success_rate for s in versions])
        
        return {
            'total_versions': len(versions),
            'total_usage': total_usage,
            'average_success_rate': avg_success,
            'latest_version': max(versions, key=lambda s: version.parse(s.version)).version
        }
    
    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Skill]:
        """Search skills by query.
        
        Uses BM25 + semantic similarity.
        """
        all_skills = [
            skill
            for versions in self.skills.values()
            for skill in versions
            if not skill.metadata.get('deprecated', False)
        ]
        
        # Score by relevance
        scored = []
        for skill in all_skills:
            score = self._compute_relevance(skill, query)
            scored.append((skill, score))
        
        # Sort and return top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:top_k]]
```

### 2.5.3 Shipped Skillpacks

**Atomic Skills Pack:**
```yaml
# atomic-skills/localize/SKILL.md
name: localize
version: 1.0.0
type: atomic
description: Locate relevant code for a task
triggers:
  - "find the code for"
  - "where is the implementation"
  - "locate the function"
tags: [navigation, search, atomic]
```

**TDD Sprint Pack:**
```yaml
# tdd-sprint/7-phase/SKILL.md
name: tdd-sprint-7-phase
version: 1.0.0
type: composite
description: Complete TDD workflow from red to ship
dependencies:
  - localize: "^1.0.0"
  - test-gen: "^1.0.0"
  - edit: "^1.0.0"
  - reproduce: "^1.0.0"
  - review: "^1.0.0"
steps:
  - localize
  - test-gen
  - edit
  - reproduce
  - review
tags: [tdd, workflow, composite]
```

### 2.5.4 Integration with Existing Skills

Extends `lyra-skills` package:

```python
# packages/lyra-skills/src/lyra_skills/weaving.py

from lyra_skills.loader import SkillLoader
from lyra_skills.router import SkillRouter

class SkillWeaver:
    """Skill Weaving integration."""
    
    def __init__(self, config):
        self.loader = SkillLoader(config.skills_paths)
        self.router = SkillRouter(self.loader)
        self.composer = CompositionEngine(self.loader.library)
        self.retrieval = CompetenceAwareRetrieval(
            self.loader.library,
            config.competence_map
        )
    
    async def execute_task(
        self,
        task_description: str,
        task_difficulty: float
    ) -> Any:
        """Execute task using best-matching skill."""
        # Retrieve best skill
        skills = self.retrieval.retrieve(
            task_description,
            task_difficulty,
            top_k=1
        )
        
        if not skills:
            raise ValueError("No matching skill found")
        
        skill, score = skills[0]
        
        # Execute skill
        result = await self._execute_skill(skill, {'task': task_description})
        
        # Update competence
        success = result.get('success', False)
        self.retrieval.update_competence(skill, task_difficulty, success)
        
        return result
```

## 2.6 DecentMem: Decentralized Memory Federation

### 2.6.1 Architecture

DecentMem enables decentralized memory sharing across agent swarms using gossip protocols and eventual consistency.

```
┌─────────────────────────────────────────────────────────────┐
│              DECENTMEM FEDERATION LAYER                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Agent 1          Agent 2          Agent 3          Agent N │
│  ┌──────┐        ┌──────┐        ┌──────┐        ┌──────┐ │
│  │Local │        │Local │        │Local │        │Local │ │
│  │Memory│        │Memory│        │Memory│        │Memory│ │
│  └───┬──┘        └───┬──┘        └───┬──┘        └───┬──┘ │
│      │               │               │               │     │
│      └───────────────┴───────────────┴───────────────┘     │
│                      │                                      │
│              ┌───────▼────────┐                            │
│              │ Gossip Protocol│                            │
│              │ • Push/Pull    │                            │
│              │ • Anti-entropy │                            │
│              │ • Rumor spread │                            │
│              └───────┬────────┘                            │
│                      │                                      │
│              ┌───────▼────────┐                            │
│              │Conflict Resolver│                           │
│              │ • Vector clocks │                           │
│              │ • LWW strategy  │                           │
│              │ • Merge logic   │                           │
│              └───────┬────────┘                            │
│                      │                                      │
│              ┌───────▼────────┐                            │
│              │  Consistency   │                            │
│              │ • Eventual     │                            │
│              │ • Convergence  │                            │
│              │ • Guarantees   │                            │
│              └────────────────┘                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.6.2 Core Components

**1. Local Memory Store**
```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime
import uuid

@dataclass
class VectorClock:
    """Vector clock for causality tracking."""
    clocks: Dict[str, int] = field(default_factory=dict)
    
    def increment(self, agent_id: str) -> None:
        """Increment clock for agent."""
        self.clocks[agent_id] = self.clocks.get(agent_id, 0) + 1
    
    def merge(self, other: 'VectorClock') -> None:
        """Merge with another vector clock."""
        for agent_id, clock in other.clocks.items():
            self.clocks[agent_id] = max(
                self.clocks.get(agent_id, 0),
                clock
            )
    
    def happens_before(self, other: 'VectorClock') -> bool:
        """Check if this clock happens before other."""
        return (
            all(
                self.clocks.get(agent_id, 0) <= other.clocks.get(agent_id, 0)
                for agent_id in set(self.clocks.keys()) | set(other.clocks.keys())
            )
            and self.clocks != other.clocks
        )
    
    def concurrent(self, other: 'VectorClock') -> bool:
        """Check if clocks are concurrent (no causal relationship)."""
        return not self.happens_before(other) and not other.happens_before(self)

@dataclass
class FederatedMemory:
    """Memory entry with federation metadata."""
    id: str
    agent_id: str  # Originating agent
    content: str
    scope: str  # "local", "shared", "global"
    vector_clock: VectorClock
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    tombstone: bool = False  # For deletion tracking

class LocalMemoryStore:
    """Local memory store for single agent."""
    
    def __init__(self, agent_id: str, storage_path: Path):
        self.agent_id = agent_id
        self.storage = storage_path
        self.memories: Dict[str, FederatedMemory] = {}
        self.vector_clock = VectorClock()
        self._load_from_disk()
    
    def write(
        self,
        content: str,
        scope: str = "local",
        metadata: Optional[Dict] = None
    ) -> FederatedMemory:
        """Write memory to local store."""
        # Increment vector clock
        self.vector_clock.increment(self.agent_id)
        
        # Create memory
        memory = FederatedMemory(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            content=content,
            scope=scope,
            vector_clock=VectorClock(clocks=self.vector_clock.clocks.copy()),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata or {}
        )
        
        self.memories[memory.id] = memory
        self._save_to_disk(memory)
        
        return memory
    
    def read(self, memory_id: str) -> Optional[FederatedMemory]:
        """Read memory by ID."""
        return self.memories.get(memory_id)
    
    def delete(self, memory_id: str) -> None:
        """Delete memory (creates tombstone)."""
        if memory_id in self.memories:
            memory = self.memories[memory_id]
            memory.tombstone = True
            memory.updated_at = datetime.now()
            self.vector_clock.increment(self.agent_id)
            memory.vector_clock = VectorClock(clocks=self.vector_clock.clocks.copy())
            self._save_to_disk(memory)
    
    def get_shared_memories(self) -> List[FederatedMemory]:
        """Get memories eligible for sharing."""
        return [
            m for m in self.memories.values()
            if m.scope in ["shared", "global"] and not m.tombstone
        ]
    
    def merge_remote_memory(self, remote: FederatedMemory) -> bool:
        """Merge remote memory into local store.
        
        Returns:
            True if memory was merged, False if rejected
        """
        local = self.memories.get(remote.id)
        
        if local is None:
            # New memory, accept it
            self.memories[remote.id] = remote
            self.vector_clock.merge(remote.vector_clock)
            self._save_to_disk(remote)
            return True
        
        # Resolve conflict
        if remote.vector_clock.happens_before(local.vector_clock):
            # Remote is older, ignore
            return False
        elif local.vector_clock.happens_before(remote.vector_clock):
            # Remote is newer, accept
            self.memories[remote.id] = remote
            self.vector_clock.merge(remote.vector_clock)
            self._save_to_disk(remote)
            return True
        else:
            # Concurrent updates, use conflict resolution
            resolved = self._resolve_conflict(local, remote)
            self.memories[remote.id] = resolved
            self.vector_clock.merge(remote.vector_clock)
            self._save_to_disk(resolved)
            return True
    
    def _resolve_conflict(
        self,
        local: FederatedMemory,
        remote: FederatedMemory
    ) -> FederatedMemory:
        """Resolve concurrent updates using Last-Write-Wins."""
        if remote.updated_at > local.updated_at:
            return remote
        elif local.updated_at > remote.updated_at:
            return local
        else:
            # Same timestamp, use agent_id as tiebreaker
            return remote if remote.agent_id > local.agent_id else local
```

**2. Gossip Protocol**
```python
import asyncio
import random
from typing import List, Set

class GossipProtocol:
    """Gossip protocol for memory federation."""
    
    def __init__(
        self,
        agent_id: str,
        local_store: LocalMemoryStore,
        peer_manager: 'PeerManager',
        gossip_interval: float = 5.0,  # seconds
        fanout: int = 3  # number of peers to gossip with
    ):
        self.agent_id = agent_id
        self.local_store = local_store
        self.peer_manager = peer_manager
        self.gossip_interval = gossip_interval
        self.fanout = fanout
        self.running = False
    
    async def start(self) -> None:
        """Start gossip protocol."""
        self.running = True
        asyncio.create_task(self._gossip_loop())
    
    async def stop(self) -> None:
        """Stop gossip protocol."""
        self.running = False
    
    async def _gossip_loop(self) -> None:
        """Main gossip loop."""
        while self.running:
            try:
                await self._gossip_round()
            except Exception as e:
                print(f"Gossip error: {e}")
            
            await asyncio.sleep(self.gossip_interval)
    
    async def _gossip_round(self) -> None:
        """Execute one round of gossip."""
        # Select random peers
        peers = self.peer_manager.get_random_peers(self.fanout)
        
        if not peers:
            return
        
        # Get local memories to share
        local_memories = self.local_store.get_shared_memories()
        
        # Gossip with each peer
        tasks = [
            self._gossip_with_peer(peer, local_memories)
            for peer in peers
        ]
        await asyncio.gather(*tasks)
    
    async def _gossip_with_peer(
        self,
        peer: 'Peer',
        local_memories: List[FederatedMemory]
    ) -> None:
        """Gossip with single peer.
        
        Uses push-pull strategy:
        1. Push local memories to peer
        2. Pull peer's memories
        """
        try:
            # Push local memories
            await peer.push_memories(local_memories)
            
            # Pull peer memories
            remote_memories = await peer.pull_memories()
            
            # Merge remote memories
            for memory in remote_memories:
                self.local_store.merge_remote_memory(memory)
        
        except Exception as e:
            print(f"Error gossiping with {peer.agent_id}: {e}")
            self.peer_manager.mark_peer_failed(peer.agent_id)

class PeerManager:
    """Manage peer connections."""
    
    def __init__(self):
        self.peers: Dict[str, 'Peer'] = {}
        self.failed_peers: Set[str] = set()
    
    def add_peer(self, peer: 'Peer') -> None:
        """Add peer to manager."""
        self.peers[peer.agent_id] = peer
        self.failed_peers.discard(peer.agent_id)
    
    def remove_peer(self, agent_id: str) -> None:
        """Remove peer from manager."""
        self.peers.pop(agent_id, None)
    
    def get_random_peers(self, count: int) -> List['Peer']:
        """Get random active peers."""
        active_peers = [
            peer for peer in self.peers.values()
            if peer.agent_id not in self.failed_peers
        ]
        
        return random.sample(
            active_peers,
            min(count, len(active_peers))
        )
    
    def mark_peer_failed(self, agent_id: str) -> None:
        """Mark peer as failed."""
        self.failed_peers.add(agent_id)

@dataclass
class Peer:
    """Remote peer agent."""
    agent_id: str
    address: str  # Network address
    port: int
    
    async def push_memories(
        self,
        memories: List[FederatedMemory]
    ) -> None:
        """Push memories to peer."""
        # Send memories over network
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://{self.address}:{self.port}/gossip/push",
                json=[self._serialize_memory(m) for m in memories]
            ) as response:
                response.raise_for_status()
    
    async def pull_memories(self) -> List[FederatedMemory]:
        """Pull memories from peer."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{self.address}:{self.port}/gossip/pull"
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return [self._deserialize_memory(m) for m in data]
```

**3. Anti-Entropy Protocol**
```python
class AntiEntropyProtocol:
    """Anti-entropy protocol for eventual consistency."""
    
    def __init__(
        self,
        local_store: LocalMemoryStore,
        peer_manager: PeerManager,
        sync_interval: float = 60.0  # seconds
    ):
        self.local_store = local_store
        self.peer_manager = peer_manager
        self.sync_interval = sync_interval
        self.running = False
    
    async def start(self) -> None:
        """Start anti-entropy protocol."""
        self.running = True
        asyncio.create_task(self._sync_loop())
    
    async def stop(self) -> None:
        """Stop anti-entropy protocol."""
        self.running = False
    
    async def _sync_loop(self) -> None:
        """Main synchronization loop."""
        while self.running:
            try:
                await self._sync_round()
            except Exception as e:
                print(f"Sync error: {e}")
            
            await asyncio.sleep(self.sync_interval)
    
    async def _sync_round(self) -> None:
        """Execute one round of synchronization."""
        # Select random peer for full sync
        peers = self.peer_manager.get_random_peers(1)
        
        if not peers:
            return
        
        peer = peers[0]
        
        # Exchange memory digests
        local_digest = self._compute_digest()
        remote_digest = await peer.get_digest()
        
        # Find differences
        missing_local = remote_digest.keys() - local_digest.keys()
        missing_remote = local_digest.keys() - remote_digest.keys()
        
        # Pull missing memories
        if missing_local:
            missing_memories = await peer.get_memories(list(missing_local))
            for memory in missing_memories:
                self.local_store.merge_remote_memory(memory)
        
        # Push missing memories
        if missing_remote:
            memories_to_push = [
                self.local_store.read(mem_id)
                for mem_id in missing_remote
            ]
            await peer.push_memories([m for m in memories_to_push if m])
    
    def _compute_digest(self) -> Dict[str, str]:
        """Compute digest of local memories.
        
        Returns:
            Dict mapping memory_id to hash
        """
        digest = {}
        for memory in self.local_store.get_shared_memories():
            digest[memory.id] = self._hash_memory(memory)
        return digest
    
    def _hash_memory(self, memory: FederatedMemory) -> str:
        """Compute hash of memory."""
        import hashlib
        content = f"{memory.content}{memory.updated_at.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()
```

**4. Federation Manager**
```python
class FederationManager:
    """Manage memory federation for agent."""
    
    def __init__(
        self,
        agent_id: str,
        storage_path: Path,
        gossip_interval: float = 5.0,
        sync_interval: float = 60.0
    ):
        self.agent_id = agent_id
        self.local_store = LocalMemoryStore(agent_id, storage_path)
        self.peer_manager = PeerManager()
        self.gossip = GossipProtocol(
            agent_id,
            self.local_store,
            self.peer_manager,
            gossip_interval
        )
        self.anti_entropy = AntiEntropyProtocol(
            self.local_store,
            self.peer_manager,
            sync_interval
        )
    
    async def start(self) -> None:
        """Start federation."""
        await self.gossip.start()
        await self.anti_entropy.start()
    
    async def stop(self) -> None:
        """Stop federation."""
        await self.gossip.stop()
        await self.anti_entropy.stop()
    
    def write_memory(
        self,
        content: str,
        scope: str = "local",
        metadata: Optional[Dict] = None
    ) -> FederatedMemory:
        """Write memory to local store."""
        return self.local_store.write(content, scope, metadata)
    
    def read_memory(self, memory_id: str) -> Optional[FederatedMemory]:
        """Read memory from local store."""
        return self.local_store.read(memory_id)
    
    def search_memories(
        self,
        query: str,
        scope: Optional[str] = None
    ) -> List[FederatedMemory]:
        """Search memories by query."""
        # Filter by scope if specified
        memories = [
            m for m in self.local_store.memories.values()
            if not m.tombstone
            and (scope is None or m.scope == scope)
        ]
        
        # Score by relevance
        scored = [
            (m, self._compute_relevance(m, query))
            for m in memories
        ]
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [m for m, _ in scored]
    
    def add_peer(self, peer: Peer) -> None:
        """Add peer to federation."""
        self.peer_manager.add_peer(peer)
    
    def remove_peer(self, agent_id: str) -> None:
        """Remove peer from federation."""
        self.peer_manager.remove_peer(agent_id)
```

### 2.6.3 Integration with Existing Memory System

Extends `lyra-memory` and `lyra-gossip-memory` packages:

```python
# packages/lyra-gossip-memory/src/lyra_gossip_memory/federation.py

from lyra_memory import MemoryStore
from lyra_gossip_memory import FederationManager

class FederatedMemoryStore(MemoryStore):
    """Memory store with federation support."""
    
    def __init__(
        self,
        agent_id: str,
        storage_path: Path,
        enable_federation: bool = True
    ):
        super().__init__(storage_path)
        self.agent_id = agent_id
        
        if enable_federation:
            self.federation = FederationManager(
                agent_id,
                storage_path / "federation"
            )
        else:
            self.federation = None
    
    async def start(self) -> None:
        """Start federated memory store."""
        if self.federation:
            await self.federation.start()
    
    async def stop(self) -> None:
        """Stop federated memory store."""
        if self.federation:
            await self.federation.stop()
    
    def write(
        self,
        content: str,
        scope: str = "local",
        **kwargs
    ) -> MemoryRecord:
        """Write memory with federation support."""
        # Write to local store
        memory = super().write(content, scope=scope, **kwargs)
        
        # Write to federation if shared/global
        if self.federation and scope in ["shared", "global"]:
            self.federation.write_memory(
                content,
                scope,
                metadata={'memory_id': memory.id}
            )
        
        return memory
```

### 2.6.4 Consistency Guarantees

**Eventual Consistency:**
- All agents eventually converge to same state
- Convergence time: O(log N) gossip rounds
- Guaranteed by gossip + anti-entropy

**Causal Consistency:**
- Vector clocks track causality
- Concurrent updates detected and resolved
- No lost updates

**Conflict Resolution:**
- Last-Write-Wins (LWW) for concurrent updates
- Tombstones for deletion tracking
- Deterministic tiebreaking

# 3. Implementation Roadmap

## 3.1 Overview

16-week implementation plan divided into 6 phases, each with clear deliverables and success criteria.

```
Timeline: 16 weeks (4 months)
Start: Week 1 (2026-05-26)
End: Week 16 (2026-09-22)

Phase 1: MOSS Integration (Weeks 1-3)
Phase 2: Ratchet Verification (Weeks 4-6)
Phase 3: Trace2Skill Extraction (Weeks 7-9)
Phase 4: Skill Weaving (Weeks 10-12)
Phase 5: DecentMem Federation (Weeks 13-14)
Phase 6: Integration & Testing (Weeks 15-16)
```

## 3.2 Phase 1: MOSS Integration (Weeks 1-3)

**Goal:** Enable source-level self-modification with user consent gates.

### Week 1: External Coding CLI Setup

**Objectives:**
- Set up external coding CLI infrastructure
- Implement AST parser for Python source
- Create basic code generation pipeline

**Tasks:**
1. Create `packages/lyra-moss/` package structure
2. Implement `MOSSParser` class
   - AST parsing with `ast` module
   - Function/class extraction
   - Signature analysis
3. Implement `MOSSGenerator` class
   - LLM-based code generation
   - Template system for common patterns
   - Syntax validation
4. Write unit tests (target: 50+ tests)

**Deliverables:**
- `lyra-moss` package with parser and generator
- 50+ passing unit tests
- Documentation for MOSS API

**Success Criteria:**
- Can parse any valid Python file
- Can generate syntactically valid code
- 100% test coverage for parser

**Code Example:**
```python
# packages/lyra-moss/src/lyra_moss/parser.py
from ast import parse, NodeTransformer, unparse
from typing import List, Dict

class MOSSParser:
    def parse_file(self, filepath: str) -> ast.Module:
        with open(filepath, 'r') as f:
            return parse(f.read())
    
    def extract_functions(self, tree: ast.Module) -> List[ast.FunctionDef]:
        return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
```

### Week 2: AST Manipulation and Code Generation

**Objectives:**
- Implement AST transformation capabilities
- Create code generation templates
- Build modification proposal system

**Tasks:**
1. Implement `ASTTransformer` class
   - Function replacement
   - Class modification
   - Import management
2. Create code generation templates
   - Performance optimization patterns
   - Error handling patterns
   - Type hint additions
3. Implement `ModificationProposal` system
   - Diff generation
   - Impact analysis
   - Rollback planning
4. Write integration tests (target: 30+ tests)

**Deliverables:**
- AST transformation system
- Code generation templates
- Modification proposal system
- 30+ integration tests

**Success Criteria:**
- Can transform AST without breaking syntax
- Can generate proposals with diffs
- All transformations are reversible

**Code Example:**
```python
# packages/lyra-moss/src/lyra_moss/transformer.py
class ASTTransformer(NodeTransformer):
    def replace_function(
        self,
        tree: ast.Module,
        old_name: str,
        new_func: ast.FunctionDef
    ) -> ast.Module:
        class FunctionReplacer(NodeTransformer):
            def visit_FunctionDef(self, node):
                if node.name == old_name:
                    return new_func
                return node
        
        return FunctionReplacer().visit(tree)
```

### Week 3: User Consent Workflow

**Objectives:**
- Implement user consent management
- Create interactive approval UI
- Build rollback system

**Tasks:**
1. Implement `ConsentManager` class
   - Interactive prompts
   - Diff visualization
   - Approval tracking
2. Create consent UI
   - Rich terminal UI with `rich`
   - Side-by-side diff display
   - Impact summary
3. Implement rollback system
   - Git-based checkpoints
   - Automatic backup creation
   - One-click rollback
4. Write end-to-end tests (target: 20+ tests)

**Deliverables:**
- User consent system
- Interactive approval UI
- Rollback mechanism
- 20+ E2E tests

**Success Criteria:**
- User can approve/reject modifications
- Diffs are clearly visualized
- Rollback works 100% of the time

**Code Example:**
```python
# packages/lyra-moss/src/lyra_moss/consent.py
from rich.console import Console
from rich.syntax import Syntax

class ConsentManager:
    def __init__(self):
        self.console = Console()
    
    async def request_consent(
        self,
        proposal: ModificationProposal
    ) -> ConsentDecision:
        # Show diff
        diff = Syntax(proposal.diff, "diff", theme="monokai")
        self.console.print(diff)
        
        # Get decision
        response = input("Approve? (yes/no/defer): ")
        return ConsentDecision(response)
```

**Phase 1 Milestone:**
- ✅ MOSS package fully functional
- ✅ 100+ tests passing
- ✅ User consent workflow complete
- ✅ Documentation published

---

## 3.3 Phase 2: Ratchet Verification (Weeks 4-6)

**Goal:** Implement deterministic 5-step verification pipeline with rollback guarantees.

### Week 4: Verification Gates

**Objectives:**
- Implement extraction engine
- Create verification engine
- Build property-based testing

**Tasks:**
1. Implement `ExtractionEngine` class
   - Trajectory analysis
   - Performance bottleneck detection
   - Opportunity scoring
2. Implement `VerificationEngine` class
   - Syntax verification
   - Type checking with mypy
   - API compatibility checks
3. Add property-based testing
   - Hypothesis integration
   - Property definitions
   - Automated test generation
4. Write verification tests (target: 40+ tests)

**Deliverables:**
- Extraction engine
- Verification engine
- Property-based testing framework
- 40+ verification tests

**Success Criteria:**
- Can identify improvement opportunities
- Verification catches all syntax/type errors
- Property tests cover edge cases

**Code Example:**
```python
# packages/lyra-ratchet/src/lyra_ratchet/verification.py
class VerificationEngine:
    def verify_modification(
        self,
        original: str,
        modified: str
    ) -> Tuple[bool, List[str]]:
        issues = []
        
        # Syntax check
        if not self._verify_syntax(modified):
            issues.append("Syntax error")
        
        # Type check
        type_issues = self._verify_types(modified)
        issues.extend(type_issues)
        
        # API compatibility
        if not self._verify_api_compat(original, modified):
            issues.append("API incompatibility")
        
        return len(issues) == 0, issues
```

### Week 5: Rollback Mechanisms

**Objectives:**
- Implement deployment manager
- Create checkpoint system
- Build automatic rollback

**Tasks:**
1. Implement `DeploymentManager` class
   - Atomic deployment
   - Checkpoint creation
   - Git integration
2. Create checkpoint system
   - Backup storage
   - Metadata tracking
   - Restoration logic
3. Implement automatic rollback
   - Failure detection
   - Automatic revert
   - Notification system
4. Write deployment tests (target: 30+ tests)

**Deliverables:**
- Deployment manager
- Checkpoint system
- Automatic rollback
- 30+ deployment tests

**Success Criteria:**
- Deployments are atomic
- Rollback works in <1 second
- No data loss on rollback

**Code Example:**
```python
# packages/lyra-ratchet/src/lyra_ratchet/deployment.py
class DeploymentManager:
    def deploy(
        self,
        target_file: Path,
        modified_code: str
    ) -> str:
        # Create checkpoint
        checkpoint_id = self._create_checkpoint(target_file)
        
        # Deploy atomically
        temp = target_file.with_suffix('.tmp')
        temp.write_text(modified_code)
        temp.replace(target_file)
        
        return checkpoint_id
    
    def rollback(self, checkpoint_id: str) -> None:
        checkpoint = self.backup_dir / checkpoint_id
        metadata = self._load_metadata(checkpoint_id)
        shutil.copy(checkpoint / 'backup.py', metadata['target'])
```

### Week 6: Competence Regression Protection

**Objectives:**
- Implement competence monitor
- Create regression detection
- Build performance tracking

**Tasks:**
1. Implement `CompetenceMonitor` class
   - Metric tracking
   - Baseline establishment
   - Regression detection
2. Create regression detection
   - Statistical tests
   - Threshold configuration
   - Alert system
3. Build performance tracking
   - Benchmark suite
   - Metric collection
   - Trend analysis
4. Write monitoring tests (target: 25+ tests)

**Deliverables:**
- Competence monitor
- Regression detection
- Performance tracking
- 25+ monitoring tests

**Success Criteria:**
- Detects 100% of regressions
- False positive rate <5%
- Alerts within 1 minute

**Code Example:**
```python
# packages/lyra-ratchet/src/lyra_ratchet/monitor.py
class CompetenceMonitor:
    def detect_regression(self) -> Tuple[bool, Optional[str]]:
        if len(self.metrics_history) < 20:
            return False, None
        
        current = self._calculate_score(list(self.metrics_history)[-20:])
        
        if current < 0.95 * self.baseline_score:
            return True, f"Score dropped from {self.baseline_score:.2f} to {current:.2f}"
        
        return False, None
```

**Phase 2 Milestone:**
- ✅ Ratchet pipeline operational
- ✅ 95+ tests passing
- ✅ Zero regressions in testing
- ✅ Rollback verified

---

## 3.4 Phase 3: Trace2Skill Extraction (Weeks 7-9)

**Goal:** Automatic skill extraction from execution trajectories with verifier-guided refinement.

### Week 7: Trajectory Capture

**Objectives:**
- Implement trajectory capture system
- Create span tracking
- Build storage layer

**Tasks:**
1. Implement `TrajectoryCapture` class
   - Span start/end tracking
   - Context capture
   - Metadata collection
2. Create span tracking
   - Nested span support
   - Timing measurement
   - Input/output recording
3. Build storage layer
   - SQLite backend
   - Efficient querying
   - Compression
4. Write capture tests (target: 35+ tests)

**Deliverables:**
- Trajectory capture system
- Span tracking
- Storage layer
- 35+ capture tests

**Success Criteria:**
- Captures all execution spans
- <5% performance overhead
- Efficient storage (<1MB per trajectory)

**Code Example:**
```python
# packages/lyra-trace2skill/src/lyra_trace2skill/capture.py
class TrajectoryCapture:
    def start_span(
        self,
        function_name: str,
        inputs: Dict[str, Any]
    ) -> str:
        span_id = f"span_{len(self.current_trajectory.spans)}"
        parent_id = self.span_stack[-1] if self.span_stack else None
        
        span = ExecutionSpan(
            span_id=span_id,
            parent_id=parent_id,
            function_name=function_name,
            start_time=datetime.now(),
            inputs=inputs
        )
        
        self.current_trajectory.add_span(span)
        self.span_stack.append(span_id)
        return span_id
```

### Week 8: Skill Extraction Algorithms

**Objectives:**
- Implement candidate scoring
- Create skill extractor
- Build pattern recognition

**Tasks:**
1. Implement `CandidateScorer` class
   - Multi-dimensional scoring
   - Generality assessment
   - Novelty detection
2. Create `SkillExtractor` class
   - LLM-based extraction
   - SKILL.md generation
   - Test case creation
3. Build pattern recognition
   - Common pattern detection
   - Abstraction generation
   - Parameterization
4. Write extraction tests (target: 40+ tests)

**Deliverables:**
- Candidate scorer
- Skill extractor
- Pattern recognition
- 40+ extraction tests

**Success Criteria:**
- Extracts skills from 80%+ of successful trajectories
- Generated skills are syntactically valid
- Test cases cover main use cases

**Code Example:**
```python
# packages/lyra-trace2skill/src/lyra_trace2skill/extractor.py
class SkillExtractor:
    async def extract_skill(
        self,
        trajectory: Trajectory
    ) -> Optional[Skill]:
        # Analyze trajectory
        analysis = await self._analyze_trajectory(trajectory)
        
        # Generate skill description
        skill_desc = await self._generate_description(analysis)
        
        # Generate SKILL.md
        skill_md = await self._generate_markdown(skill_desc)
        
        # Create skill
        return Skill(
            name=skill_desc['name'],
            description=skill_desc['description'],
            content=skill_md
        )
```

### Week 9: Quality Scoring

**Objectives:**
- Implement quality metrics
- Create scoring system
- Build ranking algorithm

**Tasks:**
1. Implement quality metrics
   - Success rate tracking
   - Efficiency measurement
   - Generality scoring
2. Create scoring system
   - Weighted combination
   - Threshold configuration
   - Confidence intervals
3. Build ranking algorithm
   - Multi-criteria ranking
   - Pareto optimization
   - Top-k selection
4. Write scoring tests (target: 30+ tests)

**Deliverables:**
- Quality metrics
- Scoring system
- Ranking algorithm
- 30+ scoring tests

**Success Criteria:**
- Scores correlate with human judgment (>0.8)
- Top-ranked skills are high quality
- Scoring is deterministic

**Code Example:**
```python
# packages/lyra-trace2skill/src/lyra_trace2skill/scorer.py
class CandidateScorer:
    def score_trajectory(self, trajectory: Trajectory) -> float:
        success_score = 1.0 if trajectory.success else 0.0
        generality_score = self._score_generality(trajectory)
        efficiency_score = self._score_efficiency(trajectory)
        novelty_score = self._score_novelty(trajectory)
        
        return (
            0.4 * success_score +
            0.3 * generality_score +
            0.2 * efficiency_score +
            0.1 * novelty_score
        )
```

**Phase 3 Milestone:**
- ✅ Trace2Skill pipeline working
- ✅ 105+ tests passing
- ✅ Skills extracted automatically
- ✅ Quality scoring validated

---

## 3.5 Phase 4: Skill Weaving (Weeks 10-12)

**Goal:** Modular skill composition with competence-aware retrieval.

### Week 10: Skillpack Composition

**Objectives:**
- Implement composition engine
- Create dependency resolution
- Build execution orchestration

**Tasks:**
1. Implement `CompositionEngine` class
   - Skill composition
   - Dependency resolution
   - Validation
2. Create dependency resolution
   - Graph-based resolution
   - Cycle detection
   - Version constraints
3. Build execution orchestration
   - Step ordering
   - Context passing
   - Error handling
4. Write composition tests (target: 35+ tests)

**Deliverables:**
- Composition engine
- Dependency resolver
- Execution orchestrator
- 35+ composition tests

**Success Criteria:**
- Can compose arbitrary skills
- Detects circular dependencies
- Executes compositions correctly

**Code Example:**
```python
# packages/lyra-skill-weaver/src/lyra_skill_weaver/composer.py
class CompositionEngine:
    def compose(
        self,
        skill_names: List[str],
        name: str
    ) -> CompositeSkill:
        # Resolve dependencies
        deps = self._resolve_dependencies(skill_names)
        
        # Validate
        self._validate_composition(skill_names, deps)
        
        # Create composite
        return CompositeSkill(
            name=name,
            steps=skill_names,
            dependencies=deps
        )
```

### Week 11: Competence-Aware Retrieval

**Objectives:**
- Implement competence tracking
- Create retrieval system
- Build matching algorithm

**Tasks:**
1. Implement competence tracking
   - Score calculation
   - History tracking
   - Decay modeling
2. Create retrieval system
   - Multi-factor scoring
   - Task difficulty estimation
   - Skill matching
3. Build matching algorithm
   - Semantic similarity
   - Competence alignment
   - Success rate weighting
4. Write retrieval tests (target: 30+ tests)

**Deliverables:**
- Competence tracker
- Retrieval system
- Matching algorithm
- 30+ retrieval tests

**Success Criteria:**
- Retrieval latency <100ms p95
- Matches are relevant (>0.8 precision)
- Competence scores are accurate

**Code Example:**
```python
# packages/lyra-skill-weaver/src/lyra_skill_weaver/retrieval.py
class CompetenceAwareRetrieval:
    def retrieve(
        self,
        query: str,
        task_difficulty: float,
        top_k: int = 5
    ) -> List[Tuple[Skill, float]]:
        candidates = self.library.search(query, top_k * 3)
        
        scored = [
            (skill, self._score_skill(skill, query, task_difficulty))
            for skill in candidates
        ]
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
```

### Week 12: Library Management

**Objectives:**
- Implement skill library
- Create versioning system
- Build usage analytics

**Tasks:**
1. Implement `SkillLibrary` class
   - CRUD operations
   - Search functionality
   - Metadata management
2. Create versioning system
   - Semantic versioning
   - Version constraints
   - Deprecation tracking
3. Build usage analytics
   - Usage counting
   - Success rate tracking
   - Trend analysis
4. Write library tests (target: 40+ tests)

**Deliverables:**
- Skill library
- Versioning system
- Usage analytics
- 40+ library tests

**Success Criteria:**
- Library scales to 1000+ skills
- Search is fast (<50ms)
- Analytics are accurate

**Code Example:**
```python
# packages/lyra-skill-weaver/src/lyra_skill_weaver/library.py
class SkillLibrary:
    def get_skill(
        self,
        name: str,
        version_constraint: Optional[str] = None
    ) -> Optional[Skill]:
        if name not in self.skills:
            return None
        
        versions = self.skills[name]
        
        if version_constraint is None:
            return max(versions, key=lambda s: version.parse(s.version))
        
        matching = [
            s for s in versions
            if self._matches_constraint(s.version, version_constraint)
        ]
        
        return max(matching, key=lambda s: version.parse(s.version)) if matching else None
```

**Phase 4 Milestone:**
- ✅ Skill Weaving operational
- ✅ 105+ tests passing
- ✅ Composition works correctly
- ✅ Retrieval is fast and accurate

---

## 3.6 Phase 5: DecentMem Federation (Weeks 13-14)

**Goal:** Decentralized memory federation across agent swarms.

### Week 13: Memory Federation Protocol

**Objectives:**
- Implement gossip protocol
- Create vector clock system
- Build conflict resolution

**Tasks:**
1. Implement `GossipProtocol` class
   - Push/pull gossip
   - Peer selection
   - Message routing
2. Create vector clock system
   - Clock increment/merge
   - Causality tracking
   - Concurrent detection
3. Build conflict resolution
   - Last-Write-Wins strategy
   - Deterministic tiebreaking
   - Tombstone handling
4. Write federation tests (target: 45+ tests)

**Deliverables:**
- Gossip protocol
- Vector clock system
- Conflict resolver
- 45+ federation tests

**Success Criteria:**
- Gossip converges in <5 seconds
- Vector clocks track causality correctly
- Conflicts resolved deterministically

**Code Example:**
```python
# packages/lyra-gossip-memory/src/lyra_gossip_memory/gossip.py
class GossipProtocol:
    async def _gossip_round(self) -> None:
        peers = self.peer_manager.get_random_peers(self.fanout)
        local_memories = self.local_store.get_shared_memories()
        
        tasks = [
            self._gossip_with_peer(peer, local_memories)
            for peer in peers
        ]
        await asyncio.gather(*tasks)
    
    async def _gossip_with_peer(
        self,
        peer: Peer,
        local_memories: List[FederatedMemory]
    ) -> None:
        # Push local memories
        await peer.push_memories(local_memories)
        
        # Pull peer memories
        remote_memories = await peer.pull_memories()
        
        # Merge
        for memory in remote_memories:
            self.local_store.merge_remote_memory(memory)
```

### Week 14: Cross-Agent Memory Sharing

**Objectives:**
- Implement anti-entropy protocol
- Create federation manager
- Build peer discovery

**Tasks:**
1. Implement `AntiEntropyProtocol` class
   - Digest computation
   - Difference detection
   - Full synchronization
2. Create `FederationManager` class
   - Lifecycle management
   - Peer management
   - Query interface
3. Build peer discovery
   - Service discovery
   - Health checking
   - Automatic reconnection
4. Write sharing tests (target: 35+ tests)

**Deliverables:**
- Anti-entropy protocol
- Federation manager
- Peer discovery
- 35+ sharing tests

**Success Criteria:**
- Anti-entropy ensures consistency
- Federation scales to 100+ agents
- Peer discovery is automatic

**Code Example:**
```python
# packages/lyra-gossip-memory/src/lyra_gossip_memory/federation.py
class FederationManager:
    async def start(self) -> None:
        await self.gossip.start()
        await self.anti_entropy.start()
    
    def write_memory(
        self,
        content: str,
        scope: str = "local"
    ) -> FederatedMemory:
        return self.local_store.write(content, scope)
    
    def search_memories(
        self,
        query: str,
        scope: Optional[str] = None
    ) -> List[FederatedMemory]:
        memories = [
            m for m in self.local_store.memories.values()
            if not m.tombstone and (scope is None or m.scope == scope)
        ]
        return self._rank_by_relevance(memories, query)
```

**Phase 5 Milestone:**
- ✅ DecentMem operational
- ✅ 80+ tests passing
- ✅ Federation works across agents
- ✅ Consistency guaranteed

---

## 3.7 Phase 6: Integration & Testing (Weeks 15-16)

**Goal:** End-to-end integration and production deployment.

### Week 15: End-to-End Integration

**Objectives:**
- Integrate all components
- Create unified API
- Build orchestration layer

**Tasks:**
1. Integrate all components
   - MOSS + Ratchet pipeline
   - Trace2Skill + Skill Weaving
   - DecentMem federation
2. Create unified API
   - High-level interfaces
   - Configuration management
   - Error handling
3. Build orchestration layer
   - Component coordination
   - Workflow management
   - State tracking
4. Write integration tests (target: 50+ tests)

**Deliverables:**
- Integrated system
- Unified API
- Orchestration layer
- 50+ integration tests

**Success Criteria:**
- All components work together
- API is intuitive
- No integration bugs

**Code Example:**
```python
# packages/lyra-agi-core/src/lyra_agi_core/orchestrator.py
class AGICoreOrchestrator:
    def __init__(self, config):
        self.moss = MOSSController(config.moss)
        self.ratchet = RatchetPipeline(config.ratchet)
        self.trace2skill = Trace2SkillPipeline(config.trace2skill)
        self.weaver = SkillWeaver(config.weaver)
        self.federation = FederationManager(config.federation)
    
    async def evolve(self, improvement_intent: str) -> EvolutionResult:
        # 1. MOSS generates modification
        proposal = await self.moss.generate_modification(improvement_intent)
        
        # 2. Ratchet verifies
        verified = await self.ratchet.verify(proposal)
        if not verified:
            return EvolutionResult(success=False, reason="Verification failed")
        
        # 3. Deploy with rollback support
        checkpoint = await self.ratchet.deploy(proposal)
        
        # 4. Monitor for regression
        regression = await self.ratchet.monitor(checkpoint)
        if regression:
            await self.ratchet.rollback(checkpoint)
            return EvolutionResult(success=False, reason="Regression detected")
        
        return EvolutionResult(success=True, checkpoint=checkpoint)
```

### Week 16: Production Deployment

**Objectives:**
- Performance optimization
- Production hardening
- Documentation completion

**Tasks:**
1. Performance optimization
   - Profiling and bottleneck removal
   - Caching strategies
   - Parallel execution
2. Production hardening
   - Error handling
   - Logging and monitoring
   - Security review
3. Documentation completion
   - API documentation
   - User guides
   - Architecture docs
4. Final testing (target: 100+ tests)

**Deliverables:**
- Optimized system
- Production-ready deployment
- Complete documentation
- 100+ final tests

**Success Criteria:**
- Performance meets targets
- System is stable
- Documentation is complete

**Phase 6 Milestone:**
- ✅ System fully integrated
- ✅ 500+ total tests passing
- ✅ Production ready
- ✅ Documentation complete

---

## 3.8 Risk Management

### High-Risk Items

**Risk 1: Code Modification Safety**
- **Impact:** High (could break production systems)
- **Probability:** Medium
- **Mitigation:**
  - Multi-layer verification (syntax, types, tests)
  - Mandatory user consent
  - Automatic rollback on failure
  - Comprehensive testing in sandbox
- **Contingency:** Manual review process for critical modifications

**Risk 2: Skill Extraction Quality**
- **Impact:** Medium (low-quality skills reduce effectiveness)
- **Probability:** Medium
- **Mitigation:**
  - Verifier-guided refinement
  - Quality scoring with thresholds
  - User review before promotion
  - Continuous quality monitoring
- **Contingency:** Manual skill curation as fallback

**Risk 3: Memory Federation Convergence**
- **Impact:** Medium (inconsistent state across agents)
- **Probability:** Low
- **Mitigation:**
  - Proven gossip protocols
  - Anti-entropy for consistency
  - Vector clocks for causality
  - Comprehensive testing
- **Contingency:** Centralized memory as fallback

### Medium-Risk Items

**Risk 4: Performance Overhead**
- **Impact:** Medium (slower response times)
- **Probability:** Medium
- **Mitigation:**
  - Profiling and optimization
  - Caching strategies
  - Async execution
  - Resource limits
- **Contingency:** Disable expensive features

**Risk 5: Integration Complexity**
- **Impact:** Medium (delays in integration)
- **Probability:** Medium
- **Mitigation:**
  - Clear interfaces between components
  - Incremental integration
  - Comprehensive integration tests
  - Regular integration checkpoints
- **Contingency:** Simplify integration by removing non-critical features

### Low-Risk Items

**Risk 6: Documentation Gaps**
- **Impact:** Low (confusion for users)
- **Probability:** Low
- **Mitigation:**
  - Documentation as part of each phase
  - Code examples in docs
  - User testing of documentation
- **Contingency:** Community-driven documentation

---

## 3.9 Dependencies and Prerequisites

### Technical Dependencies

**Required:**
- Python 3.10+
- Anthropic API access (Claude)
- Git for version control
- SQLite for storage
- pytest for testing

**Optional:**
- mypy for type checking
- hypothesis for property testing
- rich for terminal UI
- aiohttp for networking

### Package Dependencies

**Existing Lyra Packages:**
- `lyra-core` - Base types and interfaces
- `lyra-evolution` - Current evolution system (to be upgraded)
- `lyra-skills` - Skill system (to be extended)
- `lyra-memory` - Memory system (to be federated)
- `lyra-orchestration` - Multi-agent coordination
- `lyra-competence-map` - Competence tracking

**New Packages:**
- `lyra-moss` - Source-level modification
- `lyra-ratchet` - Verification pipeline
- `lyra-trace2skill` - Skill extraction
- `lyra-skill-weaver` - Skill composition
- `lyra-gossip-memory` - Memory federation (upgrade)

### Team Prerequisites

**Required Skills:**
- Python expert (AST manipulation, async programming)
- LLM integration experience
- Distributed systems knowledge (gossip protocols)
- Testing expertise (unit, integration, E2E)

**Team Size:**
- 2-3 engineers for 16 weeks
- 1 tech lead for architecture oversight
- 1 QA engineer for testing

---

## 3.10 Success Metrics by Phase

| Phase | Tests | Coverage | Performance | Quality |
|-------|-------|----------|-------------|---------|
| Phase 1 | 100+ | >90% | N/A | User consent works |
| Phase 2 | 95+ | >90% | Rollback <1s | Zero regressions |
| Phase 3 | 105+ | >85% | <5% overhead | 80%+ extraction rate |
| Phase 4 | 105+ | >85% | <100ms retrieval | >0.8 precision |
| Phase 5 | 80+ | >85% | <5s convergence | Consistency guaranteed |
| Phase 6 | 100+ | >90% | All targets met | Production ready |
| **Total** | **585+** | **>88%** | **All met** | **High quality** |

---

# 4. Technical Specifications

## 4.1 System Architecture

### 4.1.1 Package Structure

```
lyra/
├── packages/
│   ├── lyra-core/                 # Base types and interfaces
│   ├── lyra-moss/                 # Source-level modification (NEW)
│   │   ├── src/lyra_moss/
│   │   │   ├── parser.py         # AST parsing
│   │   │   ├── generator.py      # Code generation
│   │   │   ├── transformer.py    # AST transformation
│   │   │   ├── consent.py        # User consent
│   │   │   └── sandbox.py        # Sandbox testing
│   │   └── tests/
│   ├── lyra-ratchet/              # Verification pipeline (NEW)
│   │   ├── src/lyra_ratchet/
│   │   │   ├── extraction.py     # Opportunity extraction
│   │   │   ├── verification.py   # Verification engine
│   │   │   ├── testing.py        # Test orchestration
│   │   │   ├── deployment.py     # Deployment manager
│   │   │   └── monitor.py        # Competence monitor
│   │   └── tests/
│   ├── lyra-trace2skill/          # Skill extraction (NEW)
│   │   ├── src/lyra_trace2skill/
│   │   │   ├── capture.py        # Trajectory capture
│   │   │   ├── scorer.py         # Candidate scoring
│   │   │   ├── extractor.py      # Skill extraction
│   │   │   └── verifier.py       # Verifier-guided refinement
│   │   └── tests/
│   ├── lyra-skill-weaver/         # Skill composition (NEW)
│   │   ├── src/lyra_skill_weaver/
│   │   │   ├── composer.py       # Composition engine
│   │   │   ├── retrieval.py      # Competence-aware retrieval
│   │   │   ├── library.py        # Library management
│   │   │   └── executor.py       # Skill execution
│   │   └── tests/
│   ├── lyra-gossip-memory/        # Memory federation (UPGRADE)
│   │   ├── src/lyra_gossip_memory/
│   │   │   ├── gossip.py         # Gossip protocol
│   │   │   ├── vector_clock.py   # Vector clocks
│   │   │   ├── conflict.py       # Conflict resolution
│   │   │   └── federation.py     # Federation manager
│   │   └── tests/
│   ├── lyra-agi-core/             # Integration layer (NEW)
│   │   ├── src/lyra_agi_core/
│   │   │   ├── orchestrator.py   # Component orchestration
│   │   │   ├── api.py            # Unified API
│   │   │   └── config.py         # Configuration
│   │   └── tests/
│   └── [existing packages...]
```

### 4.1.2 Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    EVOLUTION CYCLE                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. EXECUTION                                              │
│     ↓                                                       │
│     Agent executes task                                    │
│     Trajectory captured (Trace2Skill)                      │
│     ↓                                                       │
│  2. EXTRACTION                                             │
│     ↓                                                       │
│     Candidate scoring                                      │
│     Skill extraction (if worthy)                           │
│     Verifier-guided refinement                             │
│     ↓                                                       │
│  3. LIBRARY UPDATE                                         │
│     ↓                                                       │
│     Add to skill library (Skill Weaving)                   │
│     Update competence map                                  │
│     Federate to other agents (DecentMem)                   │
│     ↓                                                       │
│  4. SELF-MODIFICATION (periodic)                           │
│     ↓                                                       │
│     Identify improvement opportunity (Ratchet)             │
│     Generate code modification (MOSS)                      │
│     Verify and test (Ratchet)                              │
│     Request user consent (MOSS)                            │
│     Deploy with rollback (Ratchet)                         │
│     Monitor for regression (Ratchet)                       │
│     ↓                                                       │
│  5. CONTINUOUS IMPROVEMENT                                 │
│     ↓                                                       │
│     Repeat cycle with improved capabilities                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 4.2 API Specifications

### 4.2.1 MOSS API

```python
from lyra_moss import MOSSController, ModificationProposal, ConsentDecision

# Initialize MOSS
moss = MOSSController(
    llm_client=anthropic_client,
    sandbox_enabled=True,
    user_consent_required=True
)

# Generate modification
proposal = await moss.generate_modification(
    target_file="lyra_core/agent.py",
    target_function="execute_task",
    intent="Optimize for speed",
    context={"current_p95_ms": 1500, "target_p95_ms": 500}
)

# Request user consent
decision = await moss.request_consent(proposal)

if decision == ConsentDecision.APPROVED:
    # Apply modification
    checkpoint = await moss.apply_modification(proposal)
    print(f"Modification applied. Checkpoint: {checkpoint}")
else:
    print("Modification rejected by user")
```

### 4.2.2 Ratchet API

```python
from lyra_ratchet import RatchetPipeline, EvolutionResult

# Initialize Ratchet
ratchet = RatchetPipeline(
    verification_enabled=True,
    rollback_on_failure=True,
    competence_threshold=0.95
)

# Execute evolution pipeline
result = await ratchet.evolve(
    original_code=current_implementation,
    modified_code=improved_implementation,
    test_suite="tests/unit/test_agent.py"
)

if result.success:
    print(f"Evolution successful. Checkpoint: {result.checkpoint}")
else:
    print(f"Evolution failed: {result.reason}")
    # Automatic rollback already performed
```

### 4.2.3 Trace2Skill API

```python
from lyra_trace2skill import Trace2SkillPipeline, Trajectory

# Initialize pipeline
pipeline = Trace2SkillPipeline(
    storage_path=Path(".lyra/trajectories"),
    min_score=0.6,
    llm_client=anthropic_client
)

# Capture trajectory
trajectory_id = pipeline.start_trajectory(
    task_description="Implement authentication",
    agent_id="agent_001"
)

# ... execute task ...

# End trajectory
trajectory = pipeline.end_trajectory(
    trajectory_id=trajectory_id,
    success=True,
    final_output=result
)

# Extract skill (if worthy)
skill = await pipeline.process_trajectory(trajectory)

if skill:
    print(f"Extracted skill: {skill.name}")
else:
    print("Trajectory not worthy of extraction")
```

### 4.2.4 Skill Weaving API

```python
from lyra_skill_weaver import SkillWeaver, CompositeSkill

# Initialize weaver
weaver = SkillWeaver(
    library_path=Path(".lyra/skills"),
    competence_map_path=Path(".lyra/competence.db")
)

# Compose skills
composite = weaver.compose(
    skill_names=["localize", "test-gen", "edit", "review"],
    name="tdd-workflow",
    description="Complete TDD workflow"
)

# Execute task with best-matching skill
result = await weaver.execute_task(
    task_description="Fix bug in authentication",
    task_difficulty=0.7  # 0.0=easy, 1.0=hard
)

# Update competence
weaver.update_competence(
    skill_name=result.skill_used,
    task_difficulty=0.7,
    success=result.success
)
```

### 4.2.5 DecentMem API

```python
from lyra_gossip_memory import FederationManager, Peer

# Initialize federation
federation = FederationManager(
    agent_id="agent_001",
    storage_path=Path(".lyra/memory"),
    gossip_interval=5.0,
    sync_interval=60.0
)

# Start federation
await federation.start()

# Add peers
federation.add_peer(Peer(
    agent_id="agent_002",
    address="192.168.1.100",
    port=8080
))

# Write memory (automatically federated if scope=shared/global)
memory = federation.write_memory(
    content="User prefers TypeScript over JavaScript",
    scope="shared",
    metadata={"category": "preference"}
)

# Search memories (includes federated memories)
results = federation.search_memories(
    query="programming language preference",
    scope="shared"
)

# Stop federation
await federation.stop()
```

## 4.3 Configuration Specifications

### 4.3.1 MOSS Configuration

```yaml
# .lyra/config/moss.yaml
moss:
  llm:
    provider: anthropic
    model: claude-opus-4-7
    temperature: 0.2
  
  sandbox:
    enabled: true
    timeout_seconds: 60
    memory_limit_mb: 512
    cpu_limit_percent: 50
  
  consent:
    required: true
    auto_approve_safe: false
    show_diff: true
    show_impact: true
  
  backup:
    enabled: true
    backup_dir: .lyra/backups
    retention_days: 30
```

### 4.3.2 Ratchet Configuration

```yaml
# .lyra/config/ratchet.yaml
ratchet:
  verification:
    syntax_check: true
    type_check: true
    api_compatibility: true
    property_testing: true
  
  testing:
    unit_tests: true
    integration_tests: true
    performance_benchmarks: true
    timeout_seconds: 300
  
  deployment:
    atomic: true
    git_commit: true
    rollback_on_failure: true
  
  monitoring:
    competence_threshold: 0.95
    window_size: 100
    alert_on_regression: true
```

### 4.3.3 Trace2Skill Configuration

```yaml
# .lyra/config/trace2skill.yaml
trace2skill:
  capture:
    enabled: true
    storage_path: .lyra/trajectories
    compression: true
  
  scoring:
    min_score: 0.6
    success_weight: 0.4
    generality_weight: 0.3
    efficiency_weight: 0.2
    novelty_weight: 0.1
  
  extraction:
    llm_model: claude-opus-4-7
    max_iterations: 3
    verification_required: true
  
  promotion:
    user_review_required: true
    auto_promote_threshold: 0.9
```

### 4.3.4 Skill Weaving Configuration

```yaml
# .lyra/config/skill_weaving.yaml
skill_weaving:
  library:
    path: .lyra/skills
    max_skills: 10000
    cache_size: 100
  
  retrieval:
    semantic_weight: 0.4
    competence_weight: 0.3
    success_weight: 0.2
    recency_weight: 0.1
    top_k: 5
  
  composition:
    max_depth: 5
    cycle_detection: true
    version_constraints: true
  
  competence:
    learning_rate: 0.1
    decay_factor: 0.95
```

### 4.3.5 DecentMem Configuration

```yaml
# .lyra/config/decentmem.yaml
decentmem:
  gossip:
    enabled: true
    interval_seconds: 5.0
    fanout: 3
    max_message_size_kb: 100
  
  anti_entropy:
    enabled: true
    interval_seconds: 60.0
    full_sync: true
  
  conflict_resolution:
    strategy: last_write_wins
    use_vector_clocks: true
    tombstone_retention_days: 7
  
  network:
    port: 8080
    timeout_seconds: 10
    max_peers: 100
```

## 4.4 Database Schemas

### 4.4.1 Trajectory Storage

```sql
-- Trajectories table
CREATE TABLE trajectories (
    id TEXT PRIMARY KEY,
    task_description TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    total_duration_ms REAL NOT NULL,
    success BOOLEAN NOT NULL,
    final_output TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Execution spans table
CREATE TABLE execution_spans (
    id TEXT PRIMARY KEY,
    trajectory_id TEXT NOT NULL,
    parent_id TEXT,
    function_name TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    duration_ms REAL NOT NULL,
    inputs JSON,
    outputs JSON,
    success BOOLEAN NOT NULL,
    error TEXT,
    FOREIGN KEY (trajectory_id) REFERENCES trajectories(id)
);

CREATE INDEX idx_trajectories_agent ON trajectories(agent_id);
CREATE INDEX idx_trajectories_success ON trajectories(success);
CREATE INDEX idx_spans_trajectory ON execution_spans(trajectory_id);
```

### 4.4.2 Skill Library Storage

```sql
-- Skills table
CREATE TABLE skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL, -- 'atomic' or 'composite'
    description TEXT NOT NULL,
    content TEXT NOT NULL,
    competence_score REAL DEFAULT 0.0,
    usage_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, version)
);

-- Skill dependencies table
CREATE TABLE skill_dependencies (
    skill_id TEXT NOT NULL,
    dependency_name TEXT NOT NULL,
    version_constraint TEXT NOT NULL,
    optional BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    PRIMARY KEY (skill_id, dependency_name)
);

-- Skill triggers table
CREATE TABLE skill_triggers (
    skill_id TEXT NOT NULL,
    trigger TEXT NOT NULL,
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    PRIMARY KEY (skill_id, trigger)
);

CREATE INDEX idx_skills_name ON skills(name);
CREATE INDEX idx_skills_competence ON skills(competence_score);
CREATE INDEX idx_skills_usage ON skills(usage_count);
```

### 4.4.3 Federated Memory Storage

```sql
-- Federated memories table
CREATE TABLE federated_memories (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    scope TEXT NOT NULL, -- 'local', 'shared', 'global'
    vector_clock JSON NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    tombstone BOOLEAN DEFAULT FALSE,
    metadata JSON
);

-- Vector clock table (for efficient querying)
CREATE TABLE vector_clocks (
    memory_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    clock INTEGER NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES federated_memories(id),
    PRIMARY KEY (memory_id, agent_id)
);

CREATE INDEX idx_memories_agent ON federated_memories(agent_id);
CREATE INDEX idx_memories_scope ON federated_memories(scope);
CREATE INDEX idx_memories_tombstone ON federated_memories(tombstone);
CREATE INDEX idx_memories_updated ON federated_memories(updated_at);
```

### 4.4.4 Competence Tracking Storage

```sql
-- Competence history table
CREATE TABLE competence_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT NOT NULL,
    task_difficulty REAL NOT NULL,
    success BOOLEAN NOT NULL,
    duration_ms REAL NOT NULL,
    quality_score REAL NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Competence snapshots table (for efficient querying)
CREATE TABLE competence_snapshots (
    skill_name TEXT PRIMARY KEY,
    competence_score REAL NOT NULL,
    success_rate REAL NOT NULL,
    usage_count INTEGER NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_competence_skill ON competence_history(skill_name);
CREATE INDEX idx_competence_timestamp ON competence_history(timestamp);
```

## 4.5 Performance Specifications

### 4.5.1 Latency Targets

| Operation | Target (p50) | Target (p95) | Target (p99) |
|-----------|--------------|--------------|--------------|
| MOSS code generation | <2s | <5s | <10s |
| Ratchet verification | <5s | <15s | <30s |
| Trace2Skill extraction | <10s | <30s | <60s |
| Skill retrieval | <50ms | <100ms | <200ms |
| Gossip round | <1s | <3s | <5s |
| Memory federation sync | <30s | <60s | <120s |

### 4.5.2 Throughput Targets

| Operation | Target |
|-----------|--------|
| Trajectories captured per second | 100+ |
| Skills extracted per hour | 10+ |
| Modifications per day | 5+ |
| Gossip messages per second | 1000+ |
| Memory queries per second | 100+ |

### 4.5.3 Resource Limits

| Resource | Limit |
|----------|-------|
| Memory overhead | <2GB |
| CPU overhead | <20% |
| Disk space (per agent) | <10GB |
| Network bandwidth | <1MB/s |

# 5. Testing & Verification

## 5.1 Testing Strategy

### 5.1.1 Test Pyramid

```
                    ┌─────────────┐
                    │   E2E Tests │  50 tests
                    │   (10%)     │
                    └─────────────┘
                  ┌─────────────────┐
                  │Integration Tests│  150 tests
                  │     (25%)       │
                  └─────────────────┘
              ┌───────────────────────┐
              │     Unit Tests        │  385 tests
              │       (65%)           │
              └───────────────────────┘

Total: 585+ tests across all phases
Target Coverage: >88%
```

### 5.1.2 Test Categories

**Unit Tests (385 tests):**
- MOSS: 100 tests (parser, generator, transformer, consent)
- Ratchet: 95 tests (extraction, verification, deployment, monitoring)
- Trace2Skill: 105 tests (capture, scoring, extraction, verification)
- Skill Weaving: 105 tests (composition, retrieval, library)
- DecentMem: 80 tests (gossip, vector clocks, conflict resolution)

**Integration Tests (150 tests):**
- MOSS + Ratchet: 40 tests (end-to-end modification pipeline)
- Trace2Skill + Skill Weaving: 40 tests (extraction to library)
- DecentMem + Memory: 30 tests (federation with existing memory)
- Full pipeline: 40 tests (all components together)

**E2E Tests (50 tests):**
- Complete evolution cycles: 20 tests
- Multi-agent scenarios: 15 tests
- Failure and recovery: 15 tests

## 5.2 Unit Testing

### 5.2.1 MOSS Unit Tests

```python
# packages/lyra-moss/tests/test_parser.py
import pytest
from lyra_moss import MOSSParser

def test_parse_valid_file():
    """Test parsing valid Python file."""
    parser = MOSSParser()
    tree = parser.parse_file("examples/sample.py")
    assert tree is not None
    assert len(parser.extract_functions(tree)) > 0

def test_parse_invalid_syntax():
    """Test parsing file with syntax errors."""
    parser = MOSSParser()
    with pytest.raises(SyntaxError):
        parser.parse_file("examples/invalid.py")

def test_extract_function_signatures():
    """Test extracting function signatures."""
    parser = MOSSParser()
    tree = parser.parse_file("examples/sample.py")
    sigs = parser.extract_function_signatures(tree)
    assert "process_data" in sigs
    assert sigs["process_data"]["args"] == ["data", "config"]

@pytest.mark.parametrize("code,expected_count", [
    ("def foo(): pass", 1),
    ("def foo(): pass\ndef bar(): pass", 2),
    ("class A:\n    def foo(self): pass", 1),
])
def test_function_extraction_count(code, expected_count):
    """Test function extraction with various inputs."""
    parser = MOSSParser()
    tree = parser.parse(code)
    funcs = parser.extract_functions(tree)
    assert len(funcs) == expected_count
```

### 5.2.2 Ratchet Unit Tests

```python
# packages/lyra-ratchet/tests/test_verification.py
import pytest
from lyra_ratchet import VerificationEngine

@pytest.fixture
def verifier():
    return VerificationEngine()

def test_verify_syntax_valid(verifier):
    """Test syntax verification with valid code."""
    code = "def foo():\n    return 42"
    assert verifier._verify_syntax(code) is True

def test_verify_syntax_invalid(verifier):
    """Test syntax verification with invalid code."""
    code = "def foo(\n    return 42"
    assert verifier._verify_syntax(code) is False

def test_verify_api_compatibility(verifier):
    """Test API compatibility check."""
    original = "def foo(x, y):\n    return x + y"
    modified = "def foo(x, y, z=0):\n    return x + y + z"
    assert verifier._verify_api_compatibility(original, modified) is True

def test_verify_api_incompatibility(verifier):
    """Test API incompatibility detection."""
    original = "def foo(x, y):\n    return x + y"
    modified = "def foo(x):\n    return x * 2"
    assert verifier._verify_api_compatibility(original, modified) is False

@pytest.mark.asyncio
async def test_full_verification_pipeline(verifier):
    """Test complete verification pipeline."""
    original = "def slow_func(data):\n    return sum(data)"
    modified = "def slow_func(data):\n    return sum(data, 0)"
    
    passed, issues = await verifier.verify_modification(
        original, modified, "tests/test_slow_func.py"
    )
    assert passed is True
    assert len(issues) == 0
```

### 5.2.3 Property-Based Tests

```python
# packages/lyra-ratchet/tests/test_properties.py
from hypothesis import given, strategies as st
from lyra_ratchet import VerificationEngine

@given(st.text(min_size=1))
def test_parser_never_crashes(code):
    """Property: Parser should never crash on any input."""
    parser = MOSSParser()
    try:
        parser.parse(code)
    except SyntaxError:
        pass  # Expected for invalid syntax
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")

@given(st.lists(st.integers(), min_size=1))
def test_competence_score_bounded(metrics):
    """Property: Competence score always in [0, 1]."""
    monitor = CompetenceMonitor()
    for m in metrics:
        monitor.record_metric("task", True, 100, 0.8)
    
    score = monitor._calculate_competence_score(list(monitor.metrics_history))
    assert 0.0 <= score <= 1.0

@given(st.text(), st.text())
def test_vector_clock_properties(agent1, agent2):
    """Property: Vector clock causality is transitive."""
    if not agent1 or not agent2:
        return
    
    vc1 = VectorClock()
    vc1.increment(agent1)
    
    vc2 = VectorClock()
    vc2.merge(vc1)
    vc2.increment(agent2)
    
    vc3 = VectorClock()
    vc3.merge(vc2)
    
    # Transitivity: vc1 < vc2 < vc3
    assert vc1.happens_before(vc2)
    assert vc2.happens_before(vc3)
    assert vc1.happens_before(vc3)
```

## 5.3 Integration Testing

### 5.3.1 MOSS + Ratchet Integration

```python
# packages/lyra-agi-core/tests/integration/test_moss_ratchet.py
import pytest
from lyra_moss import MOSSController
from lyra_ratchet import RatchetPipeline

@pytest.mark.asyncio
async def test_end_to_end_modification():
    """Test complete modification pipeline."""
    # Setup
    moss = MOSSController(llm_client=mock_llm, user_consent_required=False)
    ratchet = RatchetPipeline(verification_enabled=True)
    
    # Generate modification
    proposal = await moss.generate_modification(
        target_file="examples/slow_function.py",
        target_function="process_data",
        intent="Optimize for speed"
    )
    
    # Verify with Ratchet
    result = await ratchet.verify(proposal)
    assert result.passed is True
    
    # Deploy
    checkpoint = await ratchet.deploy(proposal)
    assert checkpoint is not None
    
    # Monitor (should not regress)
    await asyncio.sleep(1)
    regression, reason = await ratchet.monitor(checkpoint)
    assert regression is False

@pytest.mark.asyncio
async def test_modification_with_rollback():
    """Test modification that triggers rollback."""
    moss = MOSSController(llm_client=mock_llm)
    ratchet = RatchetPipeline(rollback_on_failure=True)
    
    # Generate bad modification (intentionally breaks tests)
    proposal = await moss.generate_modification(
        target_file="examples/function.py",
        target_function="critical_func",
        intent="Break everything"  # Intentional
    )
    
    # Should fail verification
    result = await ratchet.verify(proposal)
    assert result.passed is False
    
    # Should not deploy
    with pytest.raises(VerificationError):
        await ratchet.deploy(proposal)
```

### 5.3.2 Trace2Skill + Skill Weaving Integration

```python
# packages/lyra-agi-core/tests/integration/test_trace2skill_weaving.py
import pytest
from lyra_trace2skill import Trace2SkillPipeline
from lyra_skill_weaver import SkillWeaver

@pytest.mark.asyncio
async def test_skill_extraction_to_library():
    """Test extracting skill and adding to library."""
    # Setup
    pipeline = Trace2SkillPipeline(storage_path=tmp_path)
    weaver = SkillWeaver(library_path=tmp_path / "skills")
    
    # Create successful trajectory
    trajectory = create_test_trajectory(success=True, duration_ms=500)
    
    # Extract skill
    skill = await pipeline.process_trajectory(trajectory)
    assert skill is not None
    
    # Add to library
    weaver.library.add_skill(skill)
    
    # Retrieve skill
    retrieved = weaver.library.get_skill(skill.name)
    assert retrieved is not None
    assert retrieved.name == skill.name

@pytest.mark.asyncio
async def test_skill_composition_execution():
    """Test composing and executing skills."""
    weaver = SkillWeaver(library_path=tmp_path / "skills")
    
    # Add atomic skills
    weaver.library.add_skill(create_atomic_skill("localize"))
    weaver.library.add_skill(create_atomic_skill("edit"))
    weaver.library.add_skill(create_atomic_skill("test"))
    
    # Compose
    composite = weaver.compose(
        skill_names=["localize", "edit", "test"],
        name="simple-workflow",
        description="Simple workflow"
    )
    
    # Execute
    result = await weaver.execute_composite(composite, {"task": "Fix bug"})
    assert result is not None
```

## 5.4 End-to-End Testing

### 5.4.1 Complete Evolution Cycle

```python
# packages/lyra-agi-core/tests/e2e/test_evolution_cycle.py
import pytest
from lyra_agi_core import AGICoreOrchestrator

@pytest.mark.asyncio
@pytest.mark.slow
async def test_complete_evolution_cycle():
    """Test complete evolution cycle from execution to self-modification."""
    # Setup
    orchestrator = AGICoreOrchestrator(config=test_config)
    await orchestrator.start()
    
    # 1. Execute task and capture trajectory
    task_result = await orchestrator.execute_task(
        "Implement sorting algorithm",
        agent_id="test_agent"
    )
    assert task_result.success is True
    
    # 2. Extract skill from trajectory
    skill = await orchestrator.extract_skill_from_last_trajectory()
    assert skill is not None
    assert skill.name == "sorting-algorithm"
    
    # 3. Identify improvement opportunity
    opportunity = await orchestrator.identify_improvement()
    assert opportunity is not None
    
    # 4. Generate and apply modification
    evolution_result = await orchestrator.evolve(opportunity)
    assert evolution_result.success is True
    
    # 5. Verify no regression
    await asyncio.sleep(5)
    regression = await orchestrator.check_regression()
    assert regression is False
    
    # Cleanup
    await orchestrator.stop()

@pytest.mark.asyncio
@pytest.mark.slow
async def test_multi_agent_federation():
    """Test memory federation across multiple agents."""
    # Setup 3 agents
    agents = [
        AGICoreOrchestrator(config=agent_config(i))
        for i in range(3)
    ]
    
    for agent in agents:
        await agent.start()
    
    # Connect agents as peers
    for i, agent in enumerate(agents):
        for j, peer in enumerate(agents):
            if i != j:
                agent.federation.add_peer(create_peer(j))
    
    # Agent 0 writes memory
    memory = agents[0].federation.write_memory(
        "Important fact",
        scope="shared"
    )
    
    # Wait for gossip to propagate
    await asyncio.sleep(10)
    
    # All agents should have the memory
    for agent in agents:
        results = agent.federation.search_memories("Important fact")
        assert len(results) > 0
        assert any(m.id == memory.id for m in results)
    
    # Cleanup
    for agent in agents:
        await agent.stop()
```

## 5.5 Performance Testing

### 5.5.1 Benchmark Suite

```python
# packages/lyra-agi-core/tests/benchmarks/test_performance.py
import pytest
from lyra_agi_core import AGICoreOrchestrator

@pytest.mark.benchmark
def test_skill_retrieval_latency(benchmark):
    """Benchmark skill retrieval latency."""
    weaver = SkillWeaver(library_path=test_library_with_1000_skills)
    
    result = benchmark(
        weaver.retrieve,
        query="implement authentication",
        task_difficulty=0.5,
        top_k=5
    )
    
    # Should be <100ms p95
    assert benchmark.stats['mean'] < 0.1

@pytest.mark.benchmark
def test_gossip_throughput(benchmark):
    """Benchmark gossip message throughput."""
    federation = FederationManager(agent_id="test", storage_path=tmp_path)
    
    def gossip_round():
        asyncio.run(federation.gossip._gossip_round())
    
    result = benchmark(gossip_round)
    
    # Should handle 1000+ messages/second
    assert 1.0 / benchmark.stats['mean'] > 1000

@pytest.mark.benchmark
def test_trajectory_capture_overhead(benchmark):
    """Benchmark trajectory capture overhead."""
    capture = TrajectoryCapture(storage_path=tmp_path)
    
    def execute_with_capture():
        capture.start_trajectory("test", "agent")
        span_id = capture.start_span("test_func", {})
        # Simulate work
        time.sleep(0.001)
        capture.end_span(span_id, "result", True)
        capture.end_trajectory(True, "result")
    
    result = benchmark(execute_with_capture)
    
    # Overhead should be <5%
    baseline = 0.001
    overhead = (benchmark.stats['mean'] - baseline) / baseline
    assert overhead < 0.05
```

## 5.6 Verification Methods

### 5.6.1 Formal Verification (Where Possible)

```python
# packages/lyra-ratchet/src/lyra_ratchet/formal_verification.py
from typing import Callable, Any

def verify_idempotence(func: Callable, input: Any) -> bool:
    """Verify function is idempotent: f(f(x)) = f(x)."""
    result1 = func(input)
    result2 = func(result1)
    return result1 == result2

def verify_commutativity(func: Callable, a: Any, b: Any) -> bool:
    """Verify function is commutative: f(a, b) = f(b, a)."""
    return func(a, b) == func(b, a)

def verify_associativity(func: Callable, a: Any, b: Any, c: Any) -> bool:
    """Verify function is associative: f(f(a, b), c) = f(a, f(b, c))."""
    return func(func(a, b), c) == func(a, func(b, c))

# Example: Verify vector clock merge is commutative and associative
def test_vector_clock_properties():
    vc1 = VectorClock({"a": 1, "b": 2})
    vc2 = VectorClock({"a": 2, "b": 1})
    vc3 = VectorClock({"a": 1, "b": 3})
    
    # Commutativity
    assert verify_commutativity(
        lambda x, y: x.merge(y),
        vc1.copy(),
        vc2.copy()
    )
    
    # Associativity
    assert verify_associativity(
        lambda x, y: x.merge(y),
        vc1.copy(),
        vc2.copy(),
        vc3.copy()
    )
```

### 5.6.2 Invariant Checking

```python
# packages/lyra-ratchet/src/lyra_ratchet/invariants.py

class InvariantChecker:
    """Check system invariants."""
    
    def check_competence_never_negative(self, monitor: CompetenceMonitor) -> bool:
        """Invariant: Competence scores are always >= 0."""
        for metric in monitor.metrics_history:
            if metric['quality_score'] < 0:
                return False
        return True
    
    def check_vector_clock_monotonic(self, vc: VectorClock) -> bool:
        """Invariant: Vector clocks are monotonically increasing."""
        for agent_id, clock in vc.clocks.items():
            if clock < 0:
                return False
        return True
    
    def check_no_circular_dependencies(self, library: SkillLibrary) -> bool:
        """Invariant: No circular dependencies in skill library."""
        import networkx as nx
        
        graph = nx.DiGraph()
        for skill in library.get_all_skills():
            graph.add_node(skill.name)
            for dep in skill.dependencies:
                graph.add_edge(skill.name, dep.skill_name)
        
        return nx.is_directed_acyclic_graph(graph)
```

## 5.7 Test Coverage Requirements

### 5.7.1 Coverage Targets by Package

| Package | Unit Coverage | Integration Coverage | Overall Target |
|---------|---------------|---------------------|----------------|
| lyra-moss | >90% | >85% | >88% |
| lyra-ratchet | >90% | >85% | >88% |
| lyra-trace2skill | >85% | >80% | >83% |
| lyra-skill-weaver | >85% | >80% | >83% |
| lyra-gossip-memory | >85% | >80% | >83% |
| lyra-agi-core | >90% | >90% | >90% |
| **Overall** | **>88%** | **>83%** | **>88%** |

### 5.7.2 Critical Path Coverage

**Must have 100% coverage:**
- User consent workflow
- Rollback mechanisms
- Conflict resolution
- Verification gates
- Safety checks

**Must have >95% coverage:**
- Code generation
- Skill extraction
- Competence tracking
- Memory federation

---

# 6. Safety & Ethics

## 6.1 Safety Principles

### 6.1.1 Core Safety Guarantees

**1. Human-in-the-Loop for Code Modifications**
- All source code modifications require explicit user consent
- Clear visualization of changes (side-by-side diff)
- Impact analysis shown before approval
- Easy rejection mechanism
- Audit trail of all decisions

**2. Verification Before Deployment**
- Multi-layer verification (syntax, types, tests, properties)
- Sandbox testing in isolated environment
- No deployment without passing all gates
- Formal verification where possible
- Competence regression protection

**3. Automatic Rollback on Failure**
- Checkpoint before every modification
- Continuous monitoring post-deployment
- Automatic rollback on regression detection
- One-click manual rollback
- No data loss guarantee

**4. Bounded Autonomy**
- Clear scope limits for self-modification
- Cannot modify safety systems
- Cannot bypass consent gates
- Cannot disable monitoring
- Cannot escalate privileges

**5. Transparency and Auditability**
- All modifications logged
- Full execution traces captured
- Decision rationale recorded
- Rollback history maintained
- Exportable audit logs

## 6.2 User Consent Framework

### 6.2.1 Consent Levels

```python
class ConsentLevel(Enum):
    """Levels of user consent required."""
    
    # No consent needed (read-only operations)
    NONE = "none"
    
    # Notification only (low-risk operations)
    NOTIFY = "notify"
    
    # Explicit approval required (medium-risk)
    APPROVE = "approve"
    
    # Detailed review required (high-risk)
    DETAILED_REVIEW = "detailed_review"
    
    # Prohibited (never allowed)
    PROHIBITED = "prohibited"

# Consent requirements by operation type
CONSENT_REQUIREMENTS = {
    # Read operations
    "read_code": ConsentLevel.NONE,
    "analyze_trajectory": ConsentLevel.NONE,
    "search_skills": ConsentLevel.NONE,
    
    # Low-risk modifications
    "add_docstring": ConsentLevel.NOTIFY,
    "format_code": ConsentLevel.NOTIFY,
    "add_type_hints": ConsentLevel.NOTIFY,
    
    # Medium-risk modifications
    "optimize_function": ConsentLevel.APPROVE,
    "refactor_code": ConsentLevel.APPROVE,
    "add_feature": ConsentLevel.APPROVE,
    
    # High-risk modifications
    "modify_safety_system": ConsentLevel.PROHIBITED,
    "modify_consent_system": ConsentLevel.PROHIBITED,
    "modify_rollback_system": ConsentLevel.PROHIBITED,
    "modify_authentication": ConsentLevel.DETAILED_REVIEW,
    "modify_data_handling": ConsentLevel.DETAILED_REVIEW,
}
```

### 6.2.2 Consent UI

```python
class ConsentUI:
    """Interactive consent interface."""
    
    def present_modification(
        self,
        proposal: ModificationProposal
    ) -> ConsentDecision:
        """Present modification for user review."""
        console = Console()
        
        # Header
        console.print(Panel(
            f"[bold]Code Modification Proposal[/bold]\n"
            f"File: {proposal.file_path}\n"
            f"Function: {proposal.target_function}\n"
            f"Intent: {proposal.intent}",
            style="cyan"
        ))
        
        # Diff
        console.print("\n[bold]Changes:[/bold]")
        diff = Syntax(proposal.diff, "diff", theme="monokai")
        console.print(diff)
        
        # Impact analysis
        console.print("\n[bold]Impact Analysis:[/bold]")
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Before", style="yellow")
        table.add_column("After", style="green")
        
        for metric, values in proposal.impact_analysis.items():
            table.add_row(metric, str(values['before']), str(values['after']))
        
        console.print(table)
        
        # Test results
        console.print(f"\n[bold]Test Results:[/bold]")
        if proposal.test_results.passed:
            console.print("✅ All tests passed", style="green")
        else:
            console.print("❌ Tests failed:", style="red")
            for failure in proposal.test_results.failures:
                console.print(f"  - {failure}", style="red")
        
        # Rollback plan
        console.print(f"\n[bold]Rollback Plan:[/bold]")
        console.print(f"Checkpoint will be created before deployment")
        console.print(f"Automatic rollback on regression detection")
        console.print(f"Manual rollback available via: lyra rollback {proposal.id}")
        
        # Get decision
        console.print("\n[bold]Decision:[/bold]")
        response = Prompt.ask(
            "Approve this modification?",
            choices=["yes", "no", "defer", "details"],
            default="no"
        )
        
        if response == "details":
            self._show_detailed_analysis(proposal)
            return self.present_modification(proposal)
        
        return ConsentDecision(response)
```

## 6.3 Safety Boundaries

### 6.3.1 Prohibited Modifications

**Never Allowed:**
- Modifying safety systems (consent, verification, rollback)
- Disabling monitoring or logging
- Bypassing security checks
- Escalating privileges
- Accessing unauthorized resources
- Modifying audit trails

**Requires Special Review:**
- Authentication/authorization code
- Data encryption/decryption
- Network security
- Payment processing
- User data handling
- Critical infrastructure

### 6.3.2 Scope Limitations

```python
class SafetyBoundaries:
    """Enforce safety boundaries."""
    
    PROHIBITED_FILES = [
        "lyra_moss/consent.py",
        "lyra_ratchet/verification.py",
        "lyra_ratchet/monitor.py",
        "lyra_agi_core/safety.py",
    ]
    
    PROHIBITED_FUNCTIONS = [
        "request_consent",
        "verify_modification",
        "detect_regression",
        "rollback",
    ]
    
    PROHIBITED_PATTERNS = [
        r"os\.system\(",
        r"subprocess\.call\(",
        r"eval\(",
        r"exec\(",
        r"__import__\(",
    ]
    
    def check_modification_allowed(
        self,
        proposal: ModificationProposal
    ) -> Tuple[bool, Optional[str]]:
        """Check if modification is within safety boundaries."""
        
        # Check prohibited files
        if any(pf in proposal.file_path for pf in self.PROHIBITED_FILES):
            return False, f"Cannot modify safety-critical file: {proposal.file_path}"
        
        # Check prohibited functions
        for func in self.PROHIBITED_FUNCTIONS:
            if func in proposal.target_function:
                return False, f"Cannot modify safety-critical function: {func}"
        
        # Check prohibited patterns
        for pattern in self.PROHIBITED_PATTERNS:
            if re.search(pattern, proposal.modified_code):
                return False, f"Prohibited pattern detected: {pattern}"
        
        return True, None
```

## 6.4 Ethical Considerations

### 6.4.1 Transparency

**Principle:** Users must understand what the system is doing and why.

**Implementation:**
- Clear explanations for all modifications
- Rationale for skill extraction
- Reasoning for competence scores
- Visible decision-making process
- Accessible audit logs

### 6.4.2 Accountability

**Principle:** Clear responsibility for system actions.

**Implementation:**
- All modifications attributed to specific agent
- User approval tracked
- Rollback history maintained
- Incident investigation support
- Clear escalation path

### 6.4.3 Fairness

**Principle:** System should not introduce or amplify biases.

**Implementation:**
- Skill extraction from diverse trajectories
- Competence scoring without bias
- Equal treatment of all agents
- Regular bias audits
- Diverse training data

### 6.4.4 Privacy

**Principle:** Respect user data and privacy.

**Implementation:**
- No unauthorized data access
- Secure memory federation
- Encrypted communication
- Data retention policies
- GDPR compliance

## 6.5 Governance Framework

### 6.5.1 Oversight Structure

```
┌─────────────────────────────────────────────────────────┐
│                  GOVERNANCE STRUCTURE                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Level 1: Automated Safety Systems                      │
│  ┌────────────────────────────────────────────┐        │
│  │ • Verification gates                       │        │
│  │ • Regression detection                     │        │
│  │ • Automatic rollback                       │        │
│  └────────────────────────────────────────────┘        │
│                      ↓                                   │
│  Level 2: User Consent                                  │
│  ┌────────────────────────────────────────────┐        │
│  │ • Modification approval                    │        │
│  │ • Skill promotion review                   │        │
│  │ • Configuration changes                    │        │
│  └────────────────────────────────────────────┘        │
│                      ↓                                   │
│  Level 3: Human Review (High-Risk)                      │
│  ┌────────────────────────────────────────────┐        │
│  │ • Security-critical changes                │        │
│  │ • Safety system modifications              │        │
│  │ • Policy updates                           │        │
│  └────────────────────────────────────────────┘        │
│                      ↓                                   │
│  Level 4: Audit & Compliance                            │
│  ┌────────────────────────────────────────────┐        │
│  │ • Regular audits                           │        │
│  │ • Compliance checks                        │        │
│  │ • Incident investigation                   │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 6.5.2 Incident Response

**Incident Classification:**
- **P0 (Critical):** Safety system failure, data loss, security breach
- **P1 (High):** Competence regression, failed rollback, consent bypass
- **P2 (Medium):** Performance degradation, skill extraction failure
- **P3 (Low):** Minor bugs, documentation issues

**Response Protocol:**
1. **Detection:** Automated monitoring or user report
2. **Assessment:** Classify severity and impact
3. **Containment:** Rollback if needed, isolate affected components
4. **Investigation:** Root cause analysis, audit log review
5. **Resolution:** Fix issue, deploy patch, verify
6. **Post-Mortem:** Document lessons learned, update safeguards

## 6.6 Compliance and Standards

### 6.6.1 Regulatory Compliance

**GDPR (General Data Protection Regulation):**
- Right to explanation for automated decisions
- Data minimization in trajectory capture
- Secure storage and transmission
- User consent for data processing
- Right to be forgotten

**AI Act (EU):**
- High-risk AI system classification
- Transparency requirements
- Human oversight mechanisms
- Robustness and accuracy standards
- Documentation and record-keeping

### 6.6.2 Industry Standards

**ISO/IEC 27001 (Information Security):**
- Security controls for code modification
- Access control for safety systems
- Incident management procedures
- Regular security audits

**ISO/IEC 25010 (Software Quality):**
- Functional correctness
- Performance efficiency
- Reliability and availability
- Security and maintainability

---

# 7. Production Deployment

## 7.1 Deployment Strategy

### 7.1.1 Phased Rollout

```
Phase 1: Internal Testing (Week 15)
├─ Deploy to development environment
├─ Internal team testing
├─ Performance validation
└─ Bug fixes

Phase 2: Alpha Release (Week 16, Days 1-2)
├─ Deploy to staging environment
├─ Limited alpha users (5-10)
├─ Intensive monitoring
└─ Feedback collection

Phase 3: Beta Release (Week 16, Days 3-4)
├─ Deploy to beta environment
├─ Expanded beta users (50-100)
├─ Feature validation
└─ Performance tuning

Phase 4: Canary Deployment (Week 16, Day 5)
├─ Deploy to 10% of production
├─ Monitor key metrics
├─ Gradual rollout if stable
└─ Rollback if issues

Phase 5: Full Production (Week 16, Days 6-7)
├─ Deploy to 100% of production
├─ Continuous monitoring
├─ On-call support
└─ Post-deployment review
```

### 7.1.2 Deployment Checklist

**Pre-Deployment:**
- [ ] All 585+ tests passing
- [ ] Code coverage >88%
- [ ] Performance benchmarks met
- [ ] Security review completed
- [ ] Documentation updated
- [ ] Rollback plan tested
- [ ] Monitoring configured
- [ ] Alerts set up
- [ ] On-call rotation scheduled
- [ ] Stakeholder notification sent

**Deployment:**
- [ ] Database migrations applied
- [ ] Configuration updated
- [ ] Services deployed
- [ ] Health checks passing
- [ ] Smoke tests passing
- [ ] Monitoring active
- [ ] Alerts enabled

**Post-Deployment:**
- [ ] Key metrics stable
- [ ] No error spikes
- [ ] Performance within targets
- [ ] User feedback positive
- [ ] Post-mortem scheduled

## 7.2 Monitoring and Observability

### 7.2.1 Key Metrics

**System Health:**
- Service uptime (target: 99.9%)
- Error rate (target: <0.1%)
- Response latency (p50, p95, p99)
- Resource utilization (CPU, memory, disk)

**Evolution Metrics:**
- Modifications per day
- Approval rate
- Rollback rate
- Competence score trend

**Skill Metrics:**
- Skills extracted per hour
- Skill quality score
- Skill usage count
- Success rate by skill

**Federation Metrics:**
- Gossip convergence time
- Memory sync latency
- Conflict resolution rate
- Peer connectivity

### 7.2.2 Monitoring Stack

```yaml
# Monitoring configuration
monitoring:
  metrics:
    provider: prometheus
    scrape_interval: 15s
    retention: 30d
  
  logging:
    provider: loki
    level: info
    retention: 90d
  
  tracing:
    provider: jaeger
    sampling_rate: 0.1
  
  alerting:
    provider: alertmanager
    channels:
      - slack
      - pagerduty
      - email
  
  dashboards:
    provider: grafana
    refresh_interval: 30s
```

### 7.2.3 Alert Rules

```yaml
# Alert rules
alerts:
  - name: HighErrorRate
    condition: error_rate > 0.01
    severity: critical
    notification: pagerduty
  
  - name: HighLatency
    condition: p95_latency > 1000ms
    severity: warning
    notification: slack
  
  - name: CompetenceRegression
    condition: competence_score < 0.95 * baseline
    severity: critical
    notification: pagerduty
  
  - name: RollbackFailure
    condition: rollback_failed == true
    severity: critical
    notification: pagerduty
  
  - name: FederationPartition
    condition: peer_connectivity < 0.8
    severity: warning
    notification: slack
```

## 7.3 Scaling Considerations

### 7.3.1 Horizontal Scaling

**Stateless Components:**
- MOSS code generation (scale to N instances)
- Ratchet verification (parallel verification)
- Skill extraction (distributed processing)

**Stateful Components:**
- Skill library (replicated with eventual consistency)
- Memory federation (gossip protocol scales naturally)
- Competence tracking (sharded by skill name)

### 7.3.2 Performance Optimization

**Caching:**
- Skill retrieval results (LRU cache, 100 entries)
- AST parsing results (file hash keyed)
- Verification results (code hash keyed)
- Competence scores (time-windowed)

**Parallelization:**
- Parallel test execution in sandbox
- Concurrent gossip with multiple peers
- Parallel skill extraction from trajectories
- Distributed verification

**Resource Limits:**
- Max concurrent modifications: 10
- Max trajectory storage: 10GB
- Max skill library size: 10,000 skills
- Max federation peers: 100

## 7.4 Operational Procedures

### 7.4.1 Routine Operations

**Daily:**
- Check system health dashboard
- Review error logs
- Monitor key metrics
- Verify backup completion

**Weekly:**
- Review evolution metrics
- Analyze skill quality
- Check competence trends
- Update documentation

**Monthly:**
- Security audit
- Performance review
- Capacity planning
- Incident retrospective

### 7.4.2 Emergency Procedures

**System-Wide Rollback:**
```bash
# Emergency rollback to last stable version
lyra rollback --all --to-checkpoint <checkpoint_id>

# Verify rollback
lyra verify --all

# Monitor for stability
lyra monitor --duration 1h
```

**Disable Self-Modification:**
```bash
# Temporarily disable evolution
lyra config set evolution.enabled false

# Restart services
lyra restart --all

# Re-enable after investigation
lyra config set evolution.enabled true
```

**Isolate Problematic Agent:**
```bash
# Remove agent from federation
lyra federation remove-peer <agent_id>

# Quarantine agent
lyra agent quarantine <agent_id>

# Investigate and fix
lyra agent diagnose <agent_id>
```

---

# 8. Appendices

## 8.1 Glossary

**AGI (Artificial General Intelligence):** AI system with human-level intelligence across diverse domains.

**AST (Abstract Syntax Tree):** Tree representation of source code structure.

**Competence Score:** Metric (0.0-1.0) indicating skill proficiency on tasks of varying difficulty.

**Composite Skill:** Skill composed of multiple atomic skills in sequence.

**DecentMem:** Decentralized memory federation system using gossip protocols.

**Gossip Protocol:** Distributed communication protocol where nodes randomly exchange information.

**MOSS (Model-Oriented Source-level Self-modification):** System for source-level code modification.

**Ratchet:** Deterministic verification pipeline ensuring zero regressions.

**Skill Weaving:** Framework for composing atomic skills into composite workflows.

**Trace2Skill:** System for extracting reusable skills from execution trajectories.

**Trajectory:** Complete execution trace including spans, inputs, outputs, and timing.

**Vector Clock:** Logical clock for tracking causality in distributed systems.

**Verifier-Guided Refinement:** Iterative improvement process using verification feedback.

## 8.2 Research Paper References

### 8.2.1 Core Papers

**MOSS: Model-Oriented Source-level Self-modification**
- arXiv: 2605.22794
- Key Contribution: External coding CLI for safe source-level agent rewriting
- Relevance: Foundation for MOSS integration

**Ratchet: Deterministic Verification Pipeline**
- arXiv: 2605.22148
- Key Contribution: 5-step pipeline with rollback guarantees
- Relevance: Verification and deployment strategy

**Trace2Skill: Verifier-Guided Skill Extraction**
- arXiv: 2605.21810
- Key Contribution: Automatic skill extraction from trajectories
- Relevance: Skill extraction methodology

**Skill Weaving: Modular Composable Skillpacks**
- arXiv: 2605.22205
- Key Contribution: Competence-aware skill composition
- Relevance: Skill composition framework

**DecentMem: Decentralized Memory Federation**
- arXiv: 2605.22721
- Key Contribution: Gossip-based memory sharing
- Relevance: Memory federation protocol

### 8.2.2 Related Work

**Voyager (2023):** Lifelong learning agent with skill library
**Reflexion (2023):** Learning from failure through self-reflection
**AutoGPT (2023):** Autonomous task execution with memory
**LangChain (2023):** Framework for LLM application development
**CrewAI (2024):** Multi-agent orchestration framework

## 8.3 Code Examples

### 8.3.1 Complete Evolution Cycle

```python
#!/usr/bin/env python3
"""
Complete self-evolution cycle example.
Demonstrates MOSS + Ratchet + Trace2Skill + Skill Weaving + DecentMem.
"""

import asyncio
from pathlib import Path
from lyra_agi_core import AGICoreOrchestrator, Config

async def main():
    # Initialize orchestrator
    config = Config.from_file(".lyra/config.yaml")
    orchestrator = AGICoreOrchestrator(config)
    
    print("Starting Self-Evolution AGI Core...")
    await orchestrator.start()
    
    # 1. Execute task with trajectory capture
    print("\n1. Executing task...")
    result = await orchestrator.execute_task(
        task_description="Implement binary search algorithm",
        agent_id="agent_001",
        capture_trajectory=True
    )
    print(f"   Task completed: {result.success}")
    
    # 2. Extract skill from trajectory
    print("\n2. Extracting skill from trajectory...")
    skill = await orchestrator.extract_skill_from_last_trajectory()
    if skill:
        print(f"   Extracted skill: {skill.name}")
        print(f"   Quality score: {skill.metadata['quality_score']:.2f}")
    else:
        print("   Trajectory not worthy of extraction")
    
    # 3. Identify improvement opportunity
    print("\n3. Identifying improvement opportunities...")
    opportunities = await orchestrator.identify_improvements(lookback=100)
    if opportunities:
        opp = opportunities[0]
        print(f"   Found opportunity: {opp.issue_type}")
        print(f"   Target: {opp.target_function}")
        print(f"   Impact score: {opp.impact_score:.2f}")
        
        # 4. Generate and verify modification
        print("\n4. Generating code modification...")
        proposal = await orchestrator.generate_modification(opp)
        print(f"   Generated proposal for {proposal.target_function}")
        
        # 5. Request user consent
        print("\n5. Requesting user consent...")
        decision = await orchestrator.request_consent(proposal)
        
        if decision.approved:
            # 6. Deploy with verification
            print("\n6. Deploying modification...")
            evolution_result = await orchestrator.deploy_modification(proposal)
            
            if evolution_result.success:
                print(f"   ✅ Deployment successful")
                print(f"   Checkpoint: {evolution_result.checkpoint}")
                
                # 7. Monitor for regression
                print("\n7. Monitoring for regression...")
                await asyncio.sleep(5)
                
                regression = await orchestrator.check_regression(
                    evolution_result.checkpoint
                )
                
                if regression:
                    print("   ⚠️  Regression detected, rolling back...")
                    await orchestrator.rollback(evolution_result.checkpoint)
                else:
                    print("   ✅ No regression detected")
            else:
                print(f"   ❌ Deployment failed: {evolution_result.reason}")
        else:
            print("   ❌ User rejected modification")
    else:
        print("   No improvement opportunities found")
    
    # 8. Federation status
    print("\n8. Memory federation status...")
    fed_stats = await orchestrator.get_federation_stats()
    print(f"   Connected peers: {fed_stats['peer_count']}")
    print(f"   Shared memories: {fed_stats['shared_memory_count']}")
    print(f"   Last sync: {fed_stats['last_sync_time']}")
    
    # Cleanup
    print("\nStopping Self-Evolution AGI Core...")
    await orchestrator.stop()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
```

### 8.3.2 Custom Skill Creation

```python
#!/usr/bin/env python3
"""
Example: Creating and using custom skills.
"""

from lyra_skill_weaver import SkillWeaver, Skill, SkillType

# Create atomic skill
debugging_skill = Skill(
    name="systematic-debugging",
    version="1.0.0",
    type=SkillType.ATOMIC,
    description="Systematic debugging workflow",
    triggers=[
        "debug the issue",
        "find the bug",
        "troubleshoot the problem"
    ],
    tags=["debugging", "troubleshooting"],
    content="""
# Systematic Debugging

## Overview
A structured approach to debugging issues.

## When to Use
- When encountering unexpected behavior
- When tests are failing
- When investigating production issues

## Steps

1. **Reproduce the Issue**
   - Create minimal reproduction case
   - Document exact steps
   - Verify it's reproducible

2. **Isolate the Problem**
   - Binary search through code
   - Add logging/breakpoints
   - Narrow down to specific function

3. **Understand the Root Cause**
   - Read relevant code carefully
   - Check assumptions
   - Trace execution flow

4. **Fix and Verify**
   - Implement fix
   - Add regression test
   - Verify fix works

5. **Document**
   - Update comments
   - Add to troubleshooting guide
   - Share learnings

## Common Pitfalls
- Jumping to conclusions without evidence
- Not creating reproduction case
- Fixing symptoms instead of root cause
""",
    dependencies=[],
    test_cases=[],
    competence_score=0.0,
    usage_count=0,
    success_rate=0.0
)

# Add to library
weaver = SkillWeaver(library_path=Path(".lyra/skills"))
weaver.library.add_skill(debugging_skill)

# Use skill
result = await weaver.execute_task(
    task_description="Debug authentication failure",
    task_difficulty=0.6
)

print(f"Used skill: {result.skill_used}")
print(f"Success: {result.success}")
```

### 8.3.3 Federation Setup

```python
#!/usr/bin/env python3
"""
Example: Setting up memory federation across agents.
"""

import asyncio
from lyra_gossip_memory import FederationManager, Peer

async def setup_federation():
    # Agent 1
    agent1 = FederationManager(
        agent_id="agent_001",
        storage_path=Path(".lyra/agent1/memory"),
        gossip_interval=5.0
    )
    
    # Agent 2
    agent2 = FederationManager(
        agent_id="agent_002",
        storage_path=Path(".lyra/agent2/memory"),
        gossip_interval=5.0
    )
    
    # Agent 3
    agent3 = FederationManager(
        agent_id="agent_003",
        storage_path=Path(".lyra/agent3/memory"),
        gossip_interval=5.0
    )
    
    # Start all agents
    await asyncio.gather(
        agent1.start(),
        agent2.start(),
        agent3.start()
    )
    
    # Connect agents as peers
    agent1.add_peer(Peer("agent_002", "localhost", 8081))
    agent1.add_peer(Peer("agent_003", "localhost", 8082))
    
    agent2.add_peer(Peer("agent_001", "localhost", 8080))
    agent2.add_peer(Peer("agent_003", "localhost", 8082))
    
    agent3.add_peer(Peer("agent_001", "localhost", 8080))
    agent3.add_peer(Peer("agent_002", "localhost", 8081))
    
    # Agent 1 writes shared memory
    memory = agent1.write_memory(
        content="Python is preferred for ML tasks",
        scope="shared",
        metadata={"category": "preference", "domain": "ml"}
    )
    
    print(f"Agent 1 wrote memory: {memory.id}")
    
    # Wait for gossip to propagate
    print("Waiting for gossip propagation...")
    await asyncio.sleep(10)
    
    # All agents should have the memory
    for i, agent in enumerate([agent1, agent2, agent3], 1):
        results = agent.search_memories("Python ML")
        print(f"Agent {i} found {len(results)} memories")
        if results:
            print(f"  Content: {results[0].content}")
    
    # Cleanup
    await asyncio.gather(
        agent1.stop(),
        agent2.stop(),
        agent3.stop()
    )

if __name__ == "__main__":
    asyncio.run(setup_federation())
```

## 8.4 Configuration Templates

### 8.4.1 Development Configuration

```yaml
# .lyra/config/development.yaml
environment: development

moss:
  llm:
    provider: anthropic
    model: claude-opus-4-7
    temperature: 0.2
  sandbox:
    enabled: true
    timeout_seconds: 60
  consent:
    required: true
    auto_approve_safe: false

ratchet:
  verification:
    syntax_check: true
    type_check: true
    api_compatibility: true
  testing:
    timeout_seconds: 300
  deployment:
    atomic: true
    rollback_on_failure: true
  monitoring:
    competence_threshold: 0.95

trace2skill:
  capture:
    enabled: true
    storage_path: .lyra/dev/trajectories
  scoring:
    min_score: 0.6
  extraction:
    llm_model: claude-opus-4-7

skill_weaving:
  library:
    path: .lyra/dev/skills
  retrieval:
    top_k: 5

decentmem:
  gossip:
    enabled: true
    interval_seconds: 5.0
    fanout: 3
  network:
    port: 8080
```

### 8.4.2 Production Configuration

```yaml
# .lyra/config/production.yaml
environment: production

moss:
  llm:
    provider: anthropic
    model: claude-opus-4-7
    temperature: 0.1  # Lower temperature for production
  sandbox:
    enabled: true
    timeout_seconds: 120  # Longer timeout
    memory_limit_mb: 1024
  consent:
    required: true
    auto_approve_safe: false
  backup:
    enabled: true
    retention_days: 90

ratchet:
  verification:
    syntax_check: true
    type_check: true
    api_compatibility: true
    property_testing: true
  testing:
    unit_tests: true
    integration_tests: true
    performance_benchmarks: true
    timeout_seconds: 600
  deployment:
    atomic: true
    git_commit: true
    rollback_on_failure: true
  monitoring:
    competence_threshold: 0.98  # Stricter threshold
    window_size: 200
    alert_on_regression: true

trace2skill:
  capture:
    enabled: true
    storage_path: /var/lyra/trajectories
    compression: true
  scoring:
    min_score: 0.7  # Higher threshold
  promotion:
    user_review_required: true

skill_weaving:
  library:
    path: /var/lyra/skills
    max_skills: 10000
    cache_size: 200
  retrieval:
    top_k: 5

decentmem:
  gossip:
    enabled: true
    interval_seconds: 10.0  # Less frequent
    fanout: 5
  anti_entropy:
    enabled: true
    interval_seconds: 120.0
  network:
    port: 8080
    timeout_seconds: 30
    max_peers: 100

monitoring:
  metrics:
    provider: prometheus
    scrape_interval: 15s
  logging:
    provider: loki
    level: info
  alerting:
    provider: alertmanager
    channels:
      - slack
      - pagerduty
```

## 8.5 Troubleshooting Guide

### 8.5.1 Common Issues

**Issue: Modification fails verification**
```
Symptom: Ratchet verification fails with type errors
Cause: Generated code has type inconsistencies
Solution:
1. Check mypy output in verification logs
2. Review generated code for type hints
3. Adjust MOSS generation prompt for stricter typing
4. Re-run verification
```

**Issue: Skill extraction produces low-quality skills**
```
Symptom: Extracted skills have low quality scores
Cause: Trajectories lack sufficient context or success signal
Solution:
1. Increase trajectory capture detail
2. Adjust scoring weights in config
3. Add more test cases to verification
4. Implement manual review step
```

**Issue: Memory federation not converging**
```
Symptom: Agents have inconsistent memory state
Cause: Network partition or gossip protocol issues
Solution:
1. Check network connectivity between peers
2. Verify gossip interval is appropriate
3. Enable anti-entropy protocol
4. Check vector clock implementation
5. Review conflict resolution logs
```

**Issue: Competence regression detected**
```
Symptom: Automatic rollback triggered after deployment
Cause: Modification degraded performance
Solution:
1. Review rollback logs for specific metrics
2. Analyze modification for performance issues
3. Adjust competence threshold if too strict
4. Add performance benchmarks to verification
```

### 8.5.2 Debug Commands

```bash
# Check system status
lyra status --verbose

# View recent modifications
lyra modifications list --limit 10

# Check verification logs
lyra logs verification --since 1h

# Test skill extraction
lyra trace2skill test --trajectory-id <id>

# Verify federation health
lyra federation status --all-peers

# Run diagnostics
lyra diagnose --full

# Export audit logs
lyra audit export --since 7d --format json
```

## 8.6 Future Enhancements

### 8.6.1 Short-Term (3-6 months)

**Enhanced Verification:**
- Formal verification for critical paths
- Symbolic execution for edge case detection
- Fuzz testing integration
- Contract-based verification

**Advanced Skill Composition:**
- Conditional skill execution
- Parallel skill execution
- Dynamic skill selection
- Skill versioning and migration

**Improved Federation:**
- Byzantine fault tolerance
- Encrypted gossip messages
- Adaptive gossip intervals
- Hierarchical federation

### 8.6.2 Long-Term (6-12 months)

**Meta-Learning:**
- Learn evolution strategies
- Optimize verification pipeline
- Adaptive competence thresholds
- Self-tuning hyperparameters

**Multi-Modal Evolution:**
- Visual code understanding
- Natural language specifications
- Diagram-based design
- Interactive evolution

**Distributed Training:**
- Federated learning for skill models
- Distributed competence tracking
- Cross-organization skill sharing
- Privacy-preserving federation

---

# 9. Conclusion

## 9.1 Summary

This ultra plan presents a comprehensive 16-week roadmap to transform Lyra v4.0.0 into a recursively self-improving AGI system. By integrating five breakthrough research innovations—MOSS, Ratchet, Trace2Skill, Skill Weaving, and DecentMem—we enable true autonomous evolution with rigorous safety guarantees.

**Key Achievements:**
- Source-level self-modification with user consent
- Deterministic verification with zero regressions
- Automatic skill extraction from experience
- Modular skill composition with competence awareness
- Decentralized memory federation across agent swarms

**Success Metrics:**
- 585+ tests passing (>88% coverage)
- 10%+ monthly improvement in task completion
- Zero competence regressions
- 100% verified modifications
- <100ms skill retrieval latency

## 9.2 Next Steps

**Immediate Actions (Week 1):**
1. Review and approve this plan
2. Assemble implementation team (2-3 engineers + tech lead + QA)
3. Set up development environment
4. Create project tracking board
5. Begin Phase 1: MOSS Integration

**Ongoing:**
- Weekly progress reviews
- Bi-weekly stakeholder updates
- Monthly risk assessments
- Continuous documentation updates

## 9.3 Contact and Support

**Technical Lead:** [To be assigned]  
**Project Manager:** [To be assigned]  
**Documentation:** `/Users/khanhnguyen/Downloads/MyCV/research/harness-engineering/projects/lyra/docs/`  
**Issue Tracker:** GitHub Issues  
**Discussion Forum:** GitHub Discussions

---

**Document Version:** 1.0.0  
**Last Updated:** 2026-05-22  
**Status:** Ready for Review  
**Total Pages:** ~95 pages  
**Total Words:** ~28,000 words

---

**END OF DOCUMENT**
