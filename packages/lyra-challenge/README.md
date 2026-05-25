# Lyra Challenge

Benchmark evaluation suites and competitive challenge infrastructure for Lyra agents.

## Features

- Challenge suite definitions (SWE-bench, HumanEval, competitive programming)
- Test harness for running agents against benchmarks
- Multiple grading strategies (exact match, fuzzy, partial credit, semantic)
- Agent ranking and percentile computation
- Problem difficulty estimation
- Domain-filtered problem retrieval

## Quick Start

```python
from lyra_challenge import ChallengeEngine, ChallengeProblem, TestCase, ChallengeSuite

engine = ChallengeEngine()

suite = ChallengeSuite(
    suite_id="my_bench",
    name="My Benchmark",
    description="A custom benchmark suite.",
    problems=(
        ChallengeProblem(
            problem_id="p1",
            title="FizzBuzz",
            description="Write fizzbuzz.",
            domain="CODE_GENERATION",
            difficulty="EASY",
            test_cases=(
                TestCase(test_id="t1", input_data="3", expected_output="Fizz"),
            ),
        ),
    ),
)

engine.register_suite(suite)
result = engine.grade_solution(suite.problems[0], "Fizz")
print(f"Score: {result.score}")
```

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
