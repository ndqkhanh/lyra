# Verifier Implementation Guide

## Quick Start

### 1. Basic Setup

Install the verifier package:

```bash
cd packages/lyra-core
pip install -e ".[verifier]"
```

Minimal configuration:

```python
from lyra_core.verifier import (
    Verifier,
    ObjectiveEvidence,
    verify_objective,
    verify_subjective,
)

# Create verifier instance
verifier = Verifier(
    acceptance_test_command="pytest tests/acceptance",
    judge_model="claude-opus-4.5",
)

# Verify task completion
result = verifier.verify_task_completion(
    plan_item=plan_item,
    session=session,
)

if result.verdict == "accept":
    print("✅ Task complete")
else:
    print(f"❌ Rejected: {result.critique}")
```

### 2. Phase 1: Objective Verification

Implement deterministic checks:

```python
from lyra_core.verifier import ObjectiveEvidence, ObjectiveResult, verify_objective

def run_objective_checks(session: Session) -> ObjectiveResult:
    """Run Phase 1 deterministic checks."""
    
    # Collect evidence
    test_results = run_pytest("tests/acceptance")
    coverage = measure_coverage()
    diff = get_git_diff()
    
    evidence = ObjectiveEvidence(
        acceptance_tests_run=[t.nodeid for t in test_results],
        acceptance_tests_passed=[t.nodeid for t in test_results if t.passed],
        expected_files_touched=session.plan.expected_files,
        forbidden_files_touched=[
            f for f in diff.files if f in session.plan.forbidden_files
        ],
        coverage_before=session.baseline_coverage,
        coverage_after=coverage.total,
        coverage_tolerance_pct=1.0,
    )
    
    # Verify
    return verify_objective(evidence)
```

**Running tests**:

```python
import subprocess
import json
from pathlib import Path

def run_pytest(test_path: str) -> list[TestResult]:
    """Run pytest and parse results."""
    result = subprocess.run(
        ["pytest", test_path, "--json-report", "--json-report-file=report.json"],
        capture_output=True,
        text=True,
    )
    
    report = json.loads(Path("report.json").read_text())
    return [
        TestResult(
            nodeid=test["nodeid"],
            passed=test["outcome"] == "passed",
            duration=test["duration"],
        )
        for test in report["tests"]
    ]
```

**Coverage measurement**:

```python
from coverage import Coverage

def measure_coverage() -> CoverageReport:
    """Measure test coverage."""
    cov = Coverage()
    cov.load()  # Load existing .coverage file
    
    total = cov.report(show_missing=False)
    return CoverageReport(
        total=total,
        by_file={f: cov.analysis(f) for f in cov.get_data().measured_files()},
    )
```

### 3. Phase 2: Subjective Verification

Implement LLM judge:

```python
from lyra_core.verifier import SubjectiveResult, verify_subjective

def run_subjective_verification(
    evidence: VerificationEvidence,
    judge_model: str,
) -> SubjectiveResult:
    """Run Phase 2 LLM judge."""
    
    # Build rubric
    rubric = """
    Score 0-1 on each criterion:
    - correctness: Does implementation match plan specification?
    - coverage: Are acceptance tests exhaustive?
    - faithfulness: Did agent stay within scope (no feature creep)?
    - style: Consistent with codebase conventions?
    - safety: No backdoors, secret leaks, or disabled tests?
    """
    
    # Summarize evidence
    evidence_summary = f"""
    Plan: {evidence.plan.description}
    
    Files changed: {len(evidence.diff.files)}
    {format_diff_summary(evidence.diff)}
    
    Tests: {len(evidence.acceptance_tests)} run, {len([t for t in evidence.acceptance_tests if t.passed])} passed
    
    Coverage: {evidence.coverage_delta.before:.1%} → {evidence.coverage_delta.after:.1%}
    """
    
    # Call LLM judge
    def judge_llm(prompt: str) -> str:
        response = call_model(judge_model, prompt)
        return response.content
    
    return verify_subjective(
        rubric=rubric,
        evidence_summary=evidence_summary,
        judge_llm=judge_llm,
    )
```

**Model family detection**:

```python
from lyra_core.verifier import detect_family, is_degraded_eval

generator_model = "anthropic/claude-sonnet-4-6"
judge_model = "openai/gpt-5"

if is_degraded_eval(agent_model=generator_model, judge_model=judge_model):
    print("⚠️  Warning: Same-family evaluation (degraded)")
    print(f"   Generator: {detect_family(generator_model)}")
    print(f"   Judge: {detect_family(judge_model)}")
```

### 4. Cross-Channel Verification

Check evidence consistency:

```python
from lyra_core.verifier import cross_channel_check, CrossChannelFinding

def verify_cross_channel(
    acceptance_tests: list[TestResult],
    repo_root: Path,
) -> list[CrossChannelFinding]:
    """Detect fabricated test success."""
    
    passed_tests = [t.nodeid for t in acceptance_tests if t.passed]
    
    findings = cross_channel_check(
        acceptance_tests_passed=passed_tests,
        repo_root=repo_root,
    )
    
    if findings:
        print("❌ Cross-channel mismatches detected:")
        for finding in findings:
            print(f"   {finding.test_id}: {finding.reason}")
    
    return findings
```

**Snapshot comparison**:

```python
from lyra_core.verifier import EnvironmentSnapshot, compare_snapshots

# Before execution
snapshot_before = EnvironmentSnapshot.capture(repo_root)

# Agent executes
agent.run(task)

# After execution
snapshot_after = EnvironmentSnapshot.capture(repo_root)

# Compare
delta = compare_snapshots(snapshot_before, snapshot_after)
print(f"Files created: {len(delta.files_created)}")
print(f"Files modified: {len(delta.files_modified)}")
print(f"Files deleted: {len(delta.files_deleted)}")
print(f"Processes spawned: {len(delta.processes_spawned)}")
```

### 5. Complete Verification Pipeline

End-to-end implementation:

```python
from lyra_core.verifier import VerificationPipeline, PipelineConfig

def create_verifier_pipeline() -> VerificationPipeline:
    """Create configured verification pipeline."""
    
    config = PipelineConfig(
        stages=[
            ObjectiveVerifier(),
            SubjectiveVerifier(
                judge_llm=get_judge_model(),
                rubric=load_rubric(),
            ),
            CrossChannelReconciler(),
            TddRewardVerifier(),  # Advisory
        ],
        short_circuit_on_reject=True,
        max_advisory_score=0.7,
        parallel_stages=False,
    )
    
    return VerificationPipeline(config)

# Use in agent loop
pipeline = create_verifier_pipeline()

for attempt in range(MAX_ATTEMPTS):
    # Agent generates artifact
    artifact = generator.run(plan_item, previous_critique)
    
    # Collect evidence
    evidence = collect_verification_evidence(artifact, session)
    
    # Verify
    verdict = pipeline.verify(evidence)
    
    if verdict.verdict == "accept":
        commit_artifact(artifact)
        break
    elif verdict.verdict == "reject":
        if verdict.has_blocking_findings():
            previous_critique = format_critique(verdict.blocking_findings)
        else:
            # Advisory only - accept with notes
            commit_artifact_with_notes(artifact, verdict.advisory_findings)
            break
```

## Configuration

### TOML Configuration File

Create `~/.lyra/verifier.toml`:

```toml
[verifier]
max_iterations = 3
cache_verdicts = true
cache_ttl_seconds = 3600

[verifier.objective]
acceptance_test_command = "pytest tests/acceptance -v"
coverage_tolerance_pct = 1.0
expected_files_strict = true
forbidden_files = [
    ".env",
    "secrets.yaml",
    "credentials.json",
]

[verifier.subjective]
judge_model = "claude-opus-4.5"
judge_timeout_seconds = 30
rubric_criteria = [
    "correctness",
    "coverage",
    "faithfulness",
    "style",
    "safety",
]

[verifier.cross_channel]
snapshot_backend = "auto"  # fsevents, fanotify, or polling
snapshot_allowlist = [
    ".git/",
    "__pycache__/",
    ".pytest_cache/",
    "node_modules/",
]

[verifier.prm]
enable = false
adapter = "heuristic"  # or "qwen"
```

### Environment Variables

```bash
# Model configuration
export LYRA_VERIFIER_JUDGE_MODEL="claude-opus-4.5"
export LYRA_VERIFIER_GENERATOR_MODEL="claude-sonnet-4-6"

# Iteration limits
export LYRA_VERIFIER_MAX_ITERATIONS=3
export LYRA_VERIFIER_SHORT_CIRCUIT=true

# Feature flags
export LYRA_VERIFIER_ENABLE_PRM=false
export LYRA_VERIFIER_ENABLE_CACHE=true

# Timeouts
export LYRA_VERIFIER_JUDGE_TIMEOUT=30
export LYRA_VERIFIER_TEST_TIMEOUT=300
```

## Testing

### Unit Tests

Test Phase 1 objective checks:

```python
import pytest
from lyra_core.verifier import ObjectiveEvidence, verify_objective, ObjectiveVerdict

def test_objective_pass():
    """Phase 1 passes when all checks pass."""
    evidence = ObjectiveEvidence(
        acceptance_tests_run=["test_foo", "test_bar"],
        acceptance_tests_passed=["test_foo", "test_bar"],
        expected_files_touched=["src/foo.py"],
        forbidden_files_touched=[],
        coverage_before=80.0,
        coverage_after=82.0,
        coverage_tolerance_pct=1.0,
    )
    
    result = verify_objective(evidence)
    assert result.verdict == ObjectiveVerdict.PASS

def test_objective_fail_tests():
    """Phase 1 fails when tests don't pass."""
    evidence = ObjectiveEvidence(
        acceptance_tests_run=["test_foo", "test_bar"],
        acceptance_tests_passed=["test_foo"],  # test_bar failed
        expected_files_touched=["src/foo.py"],
        forbidden_files_touched=[],
        coverage_before=80.0,
        coverage_after=80.0,
        coverage_tolerance_pct=1.0,
    )
    
    result = verify_objective(evidence)
    assert result.verdict == ObjectiveVerdict.FAIL
    assert "test_bar" in result.reason
```

Test Phase 2 subjective checks:

```python
from lyra_core.verifier import verify_subjective, SubjectiveVerdict

def test_subjective_pass():
    """Phase 2 passes when judge approves."""
    
    def mock_judge(prompt: str) -> str:
        return '{"verdict": "PASS", "score": 0.9, "notes": "Looks good"}'
    
    result = verify_subjective(
        rubric="Score correctness 0-1",
        evidence_summary="All tests pass",
        judge_llm=mock_judge,
    )
    
    assert result.verdict == SubjectiveVerdict.PASS
    assert result.score == 0.9
```

Test cross-channel detection:

```python
from lyra_core.verifier import cross_channel_check
from pathlib import Path
import tempfile

def test_cross_channel_detects_commented_assertion():
    """Cross-channel catches commented-out assertions."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        test_file = repo_root / "test_foo.py"
        test_file.write_text("""
def test_something():
    # assert result == expected
    pass
        """)
        
        findings = cross_channel_check(
            acceptance_tests_passed=["test_foo.py::test_something"],
            repo_root=repo_root,
        )
        
        assert len(findings) == 1
        assert "commented-out assertion" in findings[0].reason
```

### Integration Tests

Test full verification pipeline:

```python
def test_pipeline_rejects_failing_tests(tmp_session):
    """Pipeline rejects when acceptance tests fail."""
    pipeline = create_test_pipeline()
    
    evidence = VerificationEvidence(
        plan=tmp_session.plan,
        trace=tmp_session.trace,
        diff=tmp_session.diff,
        env_snapshot=tmp_session.snapshot,
        acceptance_tests=[
            TestResult(nodeid="test_a", passed=True),
            TestResult(nodeid="test_b", passed=False),
        ],
        coverage_delta=CoverageDelta(before=80, after=80),
        timestamp=datetime.now(),
        session_id=tmp_session.id,
    )
    
    verdict = pipeline.verify(evidence)
    
    assert verdict.verdict == "reject"
    assert verdict.has_blocking_findings()
    assert "test_b" in str(verdict.blocking_findings)
```

## Debugging

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("lyra_core.verifier")
logger.setLevel(logging.DEBUG)
```

### Inspect Verification Evidence

```python
from lyra_core.verifier import VerificationEvidence

def debug_evidence(evidence: VerificationEvidence):
    """Print human-readable evidence summary."""
    print("\n=== Verification Evidence ===")
    print(f"Session: {evidence.session_id}")
    print(f"Timestamp: {evidence.timestamp}")
    print(f"\nPlan: {evidence.plan.description}")
    print(f"Expected files: {evidence.plan.expected_files}")
    print(f"\nTests run: {len(evidence.acceptance_tests)}")
    print(f"Tests passed: {sum(1 for t in evidence.acceptance_tests if t.passed)}")
    print(f"\nCoverage: {evidence.coverage_delta.before:.1%} → {evidence.coverage_delta.after:.1%}")
    print(f"Diff files: {len(evidence.diff.files)}")
    print(f"Snapshot delta: {len(evidence.env_snapshot.files_created)} created, {len(evidence.env_snapshot.files_modified)} modified")
```

### Trace Stage Execution

```python
from contextlib import contextmanager
import time

@contextmanager
def trace_stage(stage_name: str):
    """Context manager for timing and logging stage execution."""
    print(f"\n▶️  Starting stage: {stage_name}")
    start = time.time()
    try:
        yield
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        print(f"❌ Stage {stage_name} failed after {elapsed:.0f}ms: {e}")
        raise
    else:
        elapsed = (time.time() - start) * 1000
        print(f"✅ Stage {stage_name} completed in {elapsed:.0f}ms")

# Use in pipeline
with trace_stage("Phase 1: Objective"):
    result = objective_verifier.verify(evidence)
```

### Export Verdict JSON

```python
import json

def export_verdict(verdict: PipelineVerdict, output_path: Path):
    """Export verdict as JSON for inspection."""
    data = {
        "verdict": verdict.verdict,
        "overall_score": verdict.overall_score,
        "stages": [
            {
                "name": r.stage_name,
                "verdict": r.verdict,
                "score": r.score,
                "findings": [
                    {
                        "criterion": f.criterion,
                        "severity": f.severity,
                        "message": f.message,
                    }
                    for f in r.findings
                ],
                "latency_ms": r.latency_ms,
            }
            for r in verdict.stage_results
        ],
        "degraded_warnings": verdict.degraded_eval_warnings,
    }
    
    output_path.write_text(json.dumps(data, indent=2))
    print(f"Verdict exported to {output_path}")
```

## Common Pitfalls

### 1. Forgetting to Run Tests Before Verification

**Problem**: Phase 1 fails with "no acceptance tests run"

**Solution**: Always run tests before collecting evidence

```python
# ❌ Wrong
evidence = collect_evidence(session)
result = verify_objective(evidence)

# ✅ Correct
run_acceptance_tests(session)  # Run tests first
evidence = collect_evidence(session)
result = verify_objective(evidence)
```

### 2. Same-Family Evaluation

**Problem**: `degraded_eval=same_family` warning in traces

**Solution**: Configure different model families

```python
# ❌ Degraded (same family)
generator_model = "anthropic/claude-sonnet-4-6"
judge_model = "anthropic/claude-opus-4-5"

# ✅ Different families
generator_model = "anthropic/claude-sonnet-4-6"
judge_model = "openai/gpt-5"
```

### 3. Coverage Regression False Positives

**Problem**: Phase 1 rejects due to coverage drop on unrelated files

**Solution**: Set appropriate tolerance or exclude generated files

```python
# Increase tolerance
evidence = ObjectiveEvidence(
    ...,
    coverage_tolerance_pct=2.0,  # Allow 2% drop
)

# Or exclude files from coverage
# In .coveragerc:
# [run]
# omit = */migrations/*, */tests/*, */generated/*
```

### 4. Cross-Channel False Positives on Temp Files

**Problem**: Snapshot detects temp files as untracked side effects

**Solution**: Add temp file patterns to allowlist

```toml
[verifier.cross_channel]
snapshot_allowlist = [
    ".git/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    "*.pyc",
    ".coverage",
    "htmlcov/",
]
```

### 5. Diff Truncation Surprises

**Problem**: Large diff truncated, judge sees incomplete context

**Solution**: Break large changes into smaller plan items

```python
# ❌ Single large plan item
plan_item = PlanItem(
    description="Refactor entire codebase",
    expected_files=[...100 files...],
)

# ✅ Multiple smaller plan items
plan_items = [
    PlanItem(description="Refactor auth module", expected_files=["auth/"]),
    PlanItem(description="Refactor api module", expected_files=["api/"]),
    # ...
]
```

### 6. Evaluator Timeout on Complex Tasks

**Problem**: LLM judge times out on large evidence

**Solution**: Increase timeout or simplify evidence summary

```python
# Increase timeout
config.judge_timeout_seconds = 60

# Or simplify evidence
def summarize_diff(diff: GitDiff, max_lines: int = 100) -> str:
    """Return abbreviated diff summary."""
    if len(diff.content.splitlines()) <= max_lines:
        return diff.content
    
    return f"""
    {len(diff.files)} files changed
    +{diff.additions} additions
    -{diff.deletions} deletions
    
    [Full diff truncated for brevity]
    """
```

## Performance Tuning

### Parallel Stage Execution

```python
# Enable parallel stages for independent checks
config = PipelineConfig(
    stages=[
        ObjectiveVerifier(),
        CrossChannelReconciler(),  # Can run parallel with objective
    ],
    parallel_stages=True,
)
```

### Verdict Caching

```python
# Enable caching for identical evidence
config.cache_verdicts = True
config.cache_ttl_seconds = 3600

# Check cache hit rate
print(f"Cache hit rate: {verifier.cache_hit_rate():.1%}")
```

### Incremental Coverage

```python
# Use coverage.py incremental mode
cov = Coverage()
cov.load()  # Load existing .coverage
cov.start()
run_tests()
cov.stop()
cov.save()
```

## Related Documentation

- [Architecture overview](./architecture.md)
- [Architecture tradeoffs](./architecture-tradeoffs.md)
- [System design](./system-design.md)
- [Deep dive](./deep-dive.md)
