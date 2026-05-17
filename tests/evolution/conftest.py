"""Pytest fixtures for evolution framework tests."""
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Create temporary workspace directory structure.

    Structure:
        workspace/
        ├── candidates/
        ├── evaluator/
        └── archive/
            └── scores/
    """
    temp_dir = Path(tempfile.mkdtemp())

    # Create directory structure
    (temp_dir / "workspace").mkdir()
    (temp_dir / "candidates").mkdir()
    (temp_dir / "evaluator").mkdir()
    (temp_dir / "archive" / "scores").mkdir(parents=True)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_candidate(temp_workspace: Path) -> Path:
    """Create sample candidate file."""
    candidate_file = temp_workspace / "candidates" / "candidate_001.py"
    candidate_file.write_text("""
def solve(x: int) -> int:
    '''Sample candidate function.'''
    return x * 2
""")
    return candidate_file


@pytest.fixture
def sample_evaluator(temp_workspace: Path) -> Path:
    """Create sample evaluator file."""
    evaluator_file = temp_workspace / "evaluator" / "test_cases.py"
    evaluator_file.write_text("""
# Secret test cases - should not be readable by agent
TEST_CASES = [
    (1, 2),
    (2, 4),
    (3, 6),
]
""")
    return evaluator_file


@pytest.fixture
def mock_harness(temp_workspace: Path):
    """Create harness with test configuration."""
    from lyra_cli.evolution.harness import EvolutionHarness

    # Create evolution directory structure
    evolution_dir = temp_workspace / "evolution"
    evolution_dir.mkdir()
    (evolution_dir / "archive" / "candidates").mkdir(parents=True)
    (evolution_dir / "archive" / "scores").mkdir(parents=True)
    (evolution_dir / "workspace").mkdir()
    (evolution_dir / "evaluator").mkdir()

    harness = EvolutionHarness(evolution_dir=evolution_dir)
    return harness


@pytest.fixture
def mock_cost_meter():
    """Create cost meter with test budget."""
    from lyra_cli.evolution.cost_meter import CostMeter, BudgetCap

    meter = CostMeter()
    budget = BudgetCap(
        max_tokens=10000,
        max_dollars=10.0,
        max_wall_clock_s=300.0,
    )

    return meter, budget
