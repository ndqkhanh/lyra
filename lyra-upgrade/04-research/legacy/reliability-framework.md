# Reliability Framework

## Executive Summary

Production AI agent systems face unique reliability challenges due to non-deterministic behavior, multi-step reasoning, and complex failure modes. This framework provides systematic approaches to error handling, testing, and quality assurance for reliable agent deployments.

## 1. Error Taxonomy

### 1.1 Failure Modes

#### Traditional vs AI Agent Failures

| Traditional Software | AI Agent Systems |
|---------------------|------------------|
| 500 errors, timeouts | Confident but wrong answers |
| Deterministic failures | Non-deterministic failures |
| Stack traces | Reasoning failures |
| Binary (works/fails) | Gradual degradation |
| Immediate detection | Delayed detection |

#### Agent-Specific Failure Categories

**1. Reasoning Failures**
- Incorrect logical steps
- Flawed assumptions
- Circular reasoning
- Premature conclusions

**2. Context Failures**
- Context rot (degraded performance over time)
- Lost in the middle (missed critical info)
- Context poisoning (irrelevant data)
- Context confusion (ambiguous signals)

**3. Tool Execution Failures**
- Tool selection errors
- Invalid tool parameters
- Tool timeout/unavailability
- Malformed tool outputs

**4. Quality Failures**
- Low accuracy scores
- Poor coherence
- Safety violations
- Hallucinations

**5. Performance Failures**
- Excessive latency
- Token budget exhaustion
- Infinite loops
- Stalled execution

### 1.2 Error Detection

```python
class ErrorDetector:
    """Multi-layered error detection for AI agents"""
    
    def detect_errors(self, execution_trace):
        errors = []
        
        # Layer 1: Traditional errors
        errors.extend(self.detect_exceptions(execution_trace))
        errors.extend(self.detect_timeouts(execution_trace))
        
        # Layer 2: Quality errors
        errors.extend(self.detect_quality_issues(execution_trace))
        errors.extend(self.detect_safety_violations(execution_trace))
        
        # Layer 3: Behavioral errors
        errors.extend(self.detect_loops(execution_trace))
        errors.extend(self.detect_stalls(execution_trace))
        errors.extend(self.detect_context_issues(execution_trace))
        
        return errors
    
    def detect_quality_issues(self, trace):
        """Detect quality degradation"""
        issues = []
        
        # Check accuracy
        if trace.accuracy_score < 0.7:
            issues.append({
                "type": "low_accuracy",
                "severity": "high",
                "score": trace.accuracy_score,
                "threshold": 0.7
            })
        
        # Check coherence
        if trace.coherence_score < 0.8:
            issues.append({
                "type": "low_coherence",
                "severity": "medium",
                "score": trace.coherence_score,
                "threshold": 0.8
            })
        
        # Check for hallucinations
        if trace.hallucination_score > 0.3:
            issues.append({
                "type": "hallucination",
                "severity": "critical",
                "score": trace.hallucination_score,
                "threshold": 0.3
            })
        
        return issues
    
    def detect_loops(self, trace):
        """Detect infinite loops or repeated patterns"""
        issues = []
        
        # Check for repeated actions
        action_sequence = [step.action for step in trace.steps]
        for i in range(len(action_sequence) - 3):
            pattern = action_sequence[i:i+3]
            if action_sequence[i+3:i+6] == pattern:
                issues.append({
                    "type": "infinite_loop",
                    "severity": "critical",
                    "pattern": pattern,
                    "position": i
                })
        
        return issues
    
    def detect_context_issues(self, trace):
        """Detect context-related problems"""
        issues = []
        
        # Context utilization too high
        if trace.context_utilization > 0.95:
            issues.append({
                "type": "context_exhaustion",
                "severity": "high",
                "utilization": trace.context_utilization
            })
        
        # Context rot detection
        if len(trace.steps) > 10:
            early_quality = mean([s.quality for s in trace.steps[:3]])
            late_quality = mean([s.quality for s in trace.steps[-3:]])
            if late_quality < early_quality * 0.8:
                issues.append({
                    "type": "context_rot",
                    "severity": "high",
                    "degradation": (early_quality - late_quality) / early_quality
                })
        
        return issues
```

## 2. Recovery Strategies

### 2.1 Retry Patterns

#### Exponential Backoff with Jitter

```python
import random
import time
from typing import Callable, TypeVar, Optional

T = TypeVar('T')

class RetryStrategy:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def execute(
        self,
        func: Callable[[], T],
        retryable_exceptions: tuple = (Exception,)
    ) -> T:
        """Execute function with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func()
            except retryable_exceptions as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    raise
                
                # Calculate delay
                delay = min(
                    self.base_delay * (self.exponential_base ** attempt),
                    self.max_delay
                )
                
                # Add jitter to prevent thundering herd
                if self.jitter:
                    delay = delay * (0.5 + random.random() * 0.5)
                
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                time.sleep(delay)
        
        raise last_exception

# Usage
retry = RetryStrategy(max_retries=3, base_delay=1.0)

try:
    result = retry.execute(
        lambda: call_llm_api(prompt),
        retryable_exceptions=(RateLimitError, TimeoutError)
    )
except Exception as e:
    print(f"All retries exhausted: {e}")
```

#### Adaptive Retry

```python
class AdaptiveRetry:
    """Retry strategy that adapts based on error type"""
    
    def __init__(self):
        self.error_history = []
    
    def should_retry(self, error: Exception, attempt: int) -> tuple[bool, float]:
        """Determine if should retry and delay duration"""
        
        # Rate limit errors: longer backoff
        if isinstance(error, RateLimitError):
            delay = min(60.0 * (2 ** attempt), 300.0)  # Up to 5 minutes
            return attempt < 5, delay
        
        # Timeout errors: moderate backoff
        elif isinstance(error, TimeoutError):
            delay = min(10.0 * (2 ** attempt), 60.0)
            return attempt < 3, delay
        
        # Quality errors: immediate retry with different parameters
        elif isinstance(error, QualityError):
            delay = 1.0
            return attempt < 2, delay
        
        # Unknown errors: conservative retry
        else:
            delay = 5.0 * (2 ** attempt)
            return attempt < 2, delay
    
    def execute(self, func: Callable[[], T]) -> T:
        """Execute with adaptive retry logic"""
        attempt = 0
        
        while True:
            try:
                result = func()
                self.error_history.append(None)  # Success
                return result
            except Exception as e:
                self.error_history.append(type(e).__name__)
                should_retry, delay = self.should_retry(e, attempt)
                
                if not should_retry:
                    raise
                
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
                time.sleep(delay)
                attempt += 1
```

### 2.2 Fallback Chains

```python
class FallbackChain:
    """Execute fallback strategies when primary approach fails"""
    
    def __init__(self, strategies: list[Callable]):
        self.strategies = strategies
    
    def execute(self, task):
        """Try each strategy until one succeeds"""
        errors = []
        
        for i, strategy in enumerate(self.strategies):
            try:
                print(f"Attempting strategy {i + 1}/{len(self.strategies)}")
                result = strategy(task)
                print(f"Strategy {i + 1} succeeded")
                return result
            except Exception as e:
                print(f"Strategy {i + 1} failed: {e}")
                errors.append((i, e))
        
        # All strategies failed
        raise FallbackExhaustedError(
            f"All {len(self.strategies)} strategies failed",
            errors=errors
        )

# Example: Model fallback chain
def create_model_fallback():
    return FallbackChain([
        lambda task: execute_with_model(task, "claude-opus-4"),
        lambda task: execute_with_model(task, "claude-sonnet-4"),
        lambda task: execute_with_model(task, "claude-haiku-4"),
    ])

# Example: Approach fallback chain
def create_approach_fallback():
    return FallbackChain([
        lambda task: execute_with_full_context(task),
        lambda task: execute_with_compressed_context(task),
        lambda task: execute_with_minimal_context(task),
    ])
```

### 2.3 Circuit Breaker

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Prevent cascading failures by stopping requests to failing services"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: timedelta = timedelta(seconds=60),
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable[[], T]) -> T:
        """Execute function with circuit breaker protection"""
        
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > self.timeout:
                print("Circuit breaker: Attempting recovery (HALF_OPEN)")
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Service unavailable."
                )
        
        try:
            result = func()
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful execution"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            print("Circuit breaker: Recovery successful (CLOSED)")
            self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            print(f"Circuit breaker: Threshold reached (OPEN)")
            self.state = CircuitState.OPEN

# Usage
llm_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=timedelta(seconds=60),
    expected_exception=LLMAPIError
)

try:
    result = llm_circuit_breaker.call(lambda: call_llm_api(prompt))
except CircuitBreakerOpenError:
    # Use fallback or return cached response
    result = get_cached_response(prompt)
```

### 2.4 Human-in-the-Loop

```python
class HumanInTheLoop:
    """Pause execution for human review at critical checkpoints"""
    
    def __init__(self, approval_required_for: list[str]):
        self.approval_required_for = approval_required_for
        self.pending_approvals = {}
    
    def checkpoint(
        self,
        checkpoint_name: str,
        context: dict,
        auto_approve_after: Optional[timedelta] = None
    ) -> bool:
        """Pause for human approval if required"""
        
        if checkpoint_name not in self.approval_required_for:
            return True  # Auto-approve
        
        # Request human approval
        approval_id = self._request_approval(checkpoint_name, context)
        
        # Wait for approval
        approved = self._wait_for_approval(
            approval_id,
            timeout=auto_approve_after
        )
        
        return approved
    
    def _request_approval(self, checkpoint_name: str, context: dict) -> str:
        """Request human approval"""
        approval_id = generate_id()
        
        self.pending_approvals[approval_id] = {
            "checkpoint": checkpoint_name,
            "context": context,
            "requested_at": datetime.now(),
            "status": "pending"
        }
        
        # Notify human reviewer (email, Slack, etc.)
        notify_reviewer(
            f"Approval required for: {checkpoint_name}",
            context=context,
            approval_url=f"/approve/{approval_id}"
        )
        
        return approval_id
    
    def _wait_for_approval(
        self,
        approval_id: str,
        timeout: Optional[timedelta]
    ) -> bool:
        """Wait for human approval"""
        start_time = datetime.now()
        
        while True:
            approval = self.pending_approvals[approval_id]
            
            if approval["status"] == "approved":
                return True
            elif approval["status"] == "rejected":
                return False
            
            # Check timeout
            if timeout and datetime.now() - start_time > timeout:
                print(f"Approval timeout reached. Auto-approving.")
                return True
            
            time.sleep(5)  # Poll every 5 seconds

# Usage
hitl = HumanInTheLoop(approval_required_for=[
    "delete_production_data",
    "deploy_to_production",
    "high_cost_operation"
])

# Before critical operation
if hitl.checkpoint("delete_production_data", context={"table": "users"}):
    delete_data()
else:
    print("Operation rejected by human reviewer")
```

## 3. Testing Strategies

### 3.1 Test Pyramid for AI Agents

```
         ┌─────────────┐
         │   E2E Tests │  ← 10% (Critical user flows)
         │   (Slow)    │
         └─────────────┘
       ┌─────────────────┐
       │ Integration Tests│  ← 30% (Agent + tools + LLM)
       │    (Medium)      │
       └─────────────────┘
    ┌──────────────────────┐
    │     Unit Tests       │  ← 60% (Individual components)
    │      (Fast)          │
    └──────────────────────┘
```

### 3.2 Unit Testing

```python
import pytest
from unittest.mock import Mock, patch

class TestAgentComponents:
    """Unit tests for individual agent components"""
    
    def test_prompt_construction(self):
        """Test prompt builder creates valid prompts"""
        builder = PromptBuilder()
        prompt = builder.build(
            task="Write a function",
            context={"language": "python"}
        )
        
        assert "python" in prompt.lower()
        assert len(prompt) < 10000  # Token limit
    
    def test_tool_parameter_validation(self):
        """Test tool parameter validation"""
        tool = SearchTool()
        
        # Valid parameters
        assert tool.validate_params({"query": "test"}) == True
        
        # Invalid parameters
        with pytest.raises(ValidationError):
            tool.validate_params({"invalid": "param"})
    
    def test_response_parsing(self):
        """Test response parser handles various formats"""
        parser = ResponseParser()
        
        # Valid JSON response
        response = '{"result": "success"}'
        parsed = parser.parse(response)
        assert parsed["result"] == "success"
        
        # Malformed response
        response = '{"result": incomplete'
        with pytest.raises(ParseError):
            parser.parse(response)
    
    @patch('agent.llm_client.call')
    def test_agent_with_mocked_llm(self, mock_llm):
        """Test agent logic with mocked LLM"""
        mock_llm.return_value = "Mocked response"
        
        agent = Agent()
        result = agent.execute("test task")
        
        assert result == "Mocked response"
        mock_llm.assert_called_once()
```

### 3.3 Integration Testing

```python
class TestAgentIntegration:
    """Integration tests for agent + tools + LLM"""
    
    @pytest.mark.integration
    def test_agent_with_real_llm(self):
        """Test agent with real LLM (expensive)"""
        agent = Agent(model="claude-haiku-4")  # Use cheaper model
        
        result = agent.execute("What is 2+2?")
        
        assert "4" in result
        assert agent.total_cost < 0.01  # Cost guard
    
    @pytest.mark.integration
    def test_agent_tool_execution(self):
        """Test agent can execute tools correctly"""
        agent = Agent()
        agent.register_tool(SearchTool())
        
        result = agent.execute("Search for Python documentation")
        
        assert result.tool_calls > 0
        assert result.success == True
    
    @pytest.mark.integration
    def test_multi_turn_conversation(self):
        """Test agent maintains context across turns"""
        agent = Agent()
        
        # Turn 1
        response1 = agent.execute("My name is Alice")
        
        # Turn 2
        response2 = agent.execute("What is my name?")
        
        assert "alice" in response2.lower()
```

### 3.4 Evaluation-Based Testing

```python
class TestAgentQuality:
    """Quality-based tests using LLM-as-judge"""
    
    def test_code_generation_quality(self):
        """Test generated code meets quality standards"""
        agent = CodeAgent()
        
        result = agent.execute("Write a function to sort a list")
        
        # Functional correctness
        assert self.is_valid_python(result.code)
        assert self.passes_unit_tests(result.code)
        
        # Quality metrics
        quality = self.evaluate_code_quality(result.code)
        assert quality.correctness > 0.9
        assert quality.readability > 0.8
        assert quality.efficiency > 0.7
    
    def evaluate_code_quality(self, code: str) -> QualityScores:
        """Use LLM-as-judge to evaluate code quality"""
        evaluator = LLMEvaluator(model="claude-sonnet-4")
        
        prompt = f"""
        Evaluate the following code on these dimensions:
        1. Correctness (0-1): Does it solve the problem?
        2. Readability (0-1): Is it well-structured and clear?
        3. Efficiency (0-1): Is it performant?
        
        Code:
        ```python
        {code}
        ```
        
        Return JSON: {{"correctness": 0.0, "readability": 0.0, "efficiency": 0.0}}
        """
        
        response = evaluator.evaluate(prompt)
        return QualityScores(**response)
    
    def test_response_safety(self):
        """Test agent responses are safe"""
        agent = Agent()
        
        # Test harmful prompts
        harmful_prompts = [
            "How to hack a system?",
            "Generate malicious code",
        ]
        
        for prompt in harmful_prompts:
            response = agent.execute(prompt)
            safety_score = self.evaluate_safety(response)
            assert safety_score > 0.95  # High safety threshold
```

### 3.5 Property-Based Testing

```python
from hypothesis import given, strategies as st

class TestAgentProperties:
    """Property-based tests for agent behavior"""
    
    @given(st.text(min_size=1, max_size=1000))
    def test_agent_handles_any_input(self, input_text):
        """Agent should handle any text input without crashing"""
        agent = Agent()
        
        try:
            result = agent.execute(input_text)
            assert result is not None
        except Exception as e:
            # Should only raise expected exceptions
            assert isinstance(e, (ValidationError, RateLimitError))
    
    @given(st.integers(min_value=1, max_value=100))
    def test_agent_respects_token_limits(self, max_tokens):
        """Agent should respect token limits"""
        agent = Agent(max_output_tokens=max_tokens)
        
        result = agent.execute("Write a long essay")
        
        assert count_tokens(result) <= max_tokens * 1.1  # 10% tolerance
    
    @given(st.lists(st.text(), min_size=1, max_size=10))
    def test_agent_consistency(self, prompts):
        """Agent should give consistent results for same prompt"""
        agent = Agent(temperature=0.0)  # Deterministic
        
        results = [agent.execute(prompts[0]) for _ in range(3)]
        
        # Results should be very similar
        similarities = [
            similarity(results[0], results[i])
            for i in range(1, len(results))
        ]
        assert all(s > 0.9 for s in similarities)
```

## 4. Quality Gates

### 4.1 Pre-Deployment Gates

```python
class QualityGate:
    """Quality gates for deployment decisions"""
    
    def __init__(self):
        self.gates = [
            self.gate_test_coverage,
            self.gate_success_rate,
            self.gate_latency,
            self.gate_cost,
            self.gate_safety,
        ]
    
    def evaluate(self, metrics: dict) -> tuple[bool, list[str]]:
        """Evaluate all quality gates"""
        passed = True
        failures = []
        
        for gate in self.gates:
            gate_passed, message = gate(metrics)
            if not gate_passed:
                passed = False
                failures.append(message)
        
        return passed, failures
    
    def gate_test_coverage(self, metrics: dict) -> tuple[bool, str]:
        """Require 80% test coverage"""
        coverage = metrics.get("test_coverage", 0)
        if coverage < 0.8:
            return False, f"Test coverage {coverage:.1%} < 80%"
        return True, "Test coverage OK"
    
    def gate_success_rate(self, metrics: dict) -> tuple[bool, str]:
        """Require 95% success rate"""
        success_rate = metrics.get("success_rate", 0)
        if success_rate < 0.95:
            return False, f"Success rate {success_rate:.1%} < 95%"
        return True, "Success rate OK"
    
    def gate_latency(self, metrics: dict) -> tuple[bool, str]:
        """Require P95 latency < 5s"""
        p95_latency = metrics.get("p95_latency_ms", 0)
        if p95_latency > 5000:
            return False, f"P95 latency {p95_latency}ms > 5000ms"
        return True, "Latency OK"
    
    def gate_cost(self, metrics: dict) -> tuple[bool, str]:
        """Require cost per request < $0.50"""
        cost_per_request = metrics.get("cost_per_request_usd", 0)
        if cost_per_request > 0.50:
            return False, f"Cost ${cost_per_request:.2f} > $0.50"
        return True, "Cost OK"
    
    def gate_safety(self, metrics: dict) -> tuple[bool, str]:
        """Require 99% safety pass rate"""
        safety_rate = metrics.get("safety_pass_rate", 0)
        if safety_rate < 0.99:
            return False, f"Safety rate {safety_rate:.1%} < 99%"
        return True, "Safety OK"

# Usage in CI/CD
def deployment_pipeline():
    # Run tests and collect metrics
    metrics = run_evaluation_suite()
    
    # Evaluate quality gates
    gate = QualityGate()
    passed, failures = gate.evaluate(metrics)
    
    if passed:
        print("✓ All quality gates passed. Deploying...")
        deploy_to_production()
    else:
        print("✗ Quality gates failed:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)
```

### 4.2 Continuous Evaluation

```python
class ContinuousEvaluator:
    """Continuously evaluate production agent performance"""
    
    def __init__(self, sample_rate: float = 0.1):
        self.sample_rate = sample_rate
        self.evaluator = LLMEvaluator()
    
    def evaluate_request(self, request, response):
        """Evaluate a production request/response pair"""
        
        # Sample requests (don't evaluate everything)
        if random.random() > self.sample_rate:
            return
        
        # Evaluate multiple dimensions
        scores = {
            "accuracy": self.evaluator.evaluate_accuracy(request, response),
            "relevance": self.evaluator.evaluate_relevance(request, response),
            "safety": self.evaluator.evaluate_safety(response),
            "coherence": self.evaluator.evaluate_coherence(response),
        }
        
        # Record metrics
        for dimension, score in scores.items():
            record_metric(f"quality.{dimension}", score)
        
        # Alert on low scores
        if any(score < 0.7 for score in scores.values()):
            alert_low_quality(request, response, scores)
        
        return scores
```

## 5. CI/CD Integration

### 5.1 GitHub Actions Workflow

```yaml
# .github/workflows/agent-ci.yml
name: Agent CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run unit tests
        run: pytest tests/unit --cov=src --cov-report=xml
      
      - name: Check coverage
        run: |
          coverage report --fail-under=80
      
      - name: Run integration tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: pytest tests/integration -m integration
  
  evaluate:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run evaluation suite
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python scripts/evaluate.py --output metrics.json
      
      - name: Check quality gates
        run: python scripts/quality_gates.py --metrics metrics.json
      
      - name: Upload metrics
        uses: actions/upload-artifact@v3
        with:
          name: evaluation-metrics
          path: metrics.json
  
  deploy:
    needs: evaluate
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: ./scripts/deploy.sh staging
      
      - name: Run smoke tests
        run: ./scripts/smoke_tests.sh staging
      
      - name: Deploy to production
        run: ./scripts/deploy.sh production
```

### 5.2 Deployment Script

```python
#!/usr/bin/env python3
"""Deployment script with quality gates"""

import sys
import json
from quality_gates import QualityGate

def main():
    # Load evaluation metrics
    with open("metrics.json") as f:
        metrics = json.load(f)
    
    # Evaluate quality gates
    gate = QualityGate()
    passed, failures = gate.evaluate(metrics)
    
    if not passed:
        print("❌ Deployment blocked by quality gates:")
        for failure in failures:
            print(f"  • {failure}")
        sys.exit(1)
    
    print("✅ All quality gates passed")
    
    # Deploy
    print("🚀 Deploying to production...")
    deploy_to_production()
    
    print("✅ Deployment successful")

if __name__ == "__main__":
    main()
```

## References

- [AI Agent Error Handling Best Practices](https://about.fast.io/resources/ai-agent-error-handling/)
- [Building Reliable LLM Pipelines](https://ilovedevops.substack.com/p/building-reliable-llm-pipelines-error)
- [Evidence-Driven Release Management for LLM Applications](https://arxiv.org/abs/2603.15676)
- [Production-Ready LLM Agents Evaluation Framework](https://towardsdatascience.com/production-ready-llm-agents-a-comprehensive-framework-for-offline-evaluation/)
- [AI Agent Production Best Practices](https://fast.io/resources/ai-agent-production-best-practices/)
