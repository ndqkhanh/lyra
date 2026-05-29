"""Tests for Phase 3 Learning modules."""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from lyra_cli.learning.experience_memory import (
    ExperienceMemory,
)
from lyra_cli.learning.skill_library import (
    SkillLibrary,
    VerificationTest,
)
from lyra_cli.learning.verifier import (
    Evidence,
    MemoryClaim,
    MemoryVerifier,
)

# ============================================================================
# Experience Memory Tests
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def experience_memory(temp_dir):
    """Create experience memory."""
    return ExperienceMemory(data_dir=temp_dir)


def test_experience_add_experience(experience_memory):
    """Test adding experience records."""
    record_id = experience_memory.add_experience(
        task_description="Fix authentication bug",
        context={"language": "python", "framework": "flask"},
        strategy_used="strategy_000000",
        outcome="success",
        evidence=["Tests passed", "Bug no longer reproduces"],
    )

    assert record_id is not None
    assert experience_memory.stats["total_experiences"] == 1
    assert experience_memory.stats["successful_experiences"] == 1


def test_experience_learn_strategy(experience_memory):
    """Test learning new strategies."""
    strategy_id = experience_memory.learn_strategy(
        description="Use debugger to trace execution",
        context={"task_type": "debugging"},
        actions=["Set breakpoint", "Step through code", "Inspect variables"],
    )

    assert strategy_id is not None
    assert len(experience_memory.strategies) == 1
    assert experience_memory.stats["strategies_learned"] == 1


def test_experience_retrieve_strategies(experience_memory):
    """Test conservative strategy retrieval."""
    # Learn a strategy
    strategy_id = experience_memory.learn_strategy(
        description="Test-driven development",
        context={"task_type": "feature", "language": "python"},
        actions=["Write test", "Implement", "Refactor"],
    )

    # Add successful experiences to build confidence
    for _ in range(5):
        experience_memory.add_experience(
            task_description="Add new feature",
            context={"task_type": "feature", "language": "python"},
            strategy_used=strategy_id,
            outcome="success",
            evidence=["Tests pass"],
        )

    # Retrieve strategies
    strategies = experience_memory.retrieve_strategies(
        context={"task_type": "feature", "language": "python"},
        min_confidence=0.7,
    )

    assert len(strategies) > 0
    assert strategies[0].confidence >= 0.7


def test_experience_strategy_confidence(experience_memory):
    """Test strategy confidence updates."""
    strategy_id = experience_memory.learn_strategy(
        description="Code review checklist",
        context={"task_type": "review"},
        actions=["Check tests", "Check security", "Check style"],
    )

    strategy = experience_memory.strategies[strategy_id]
    initial_confidence = strategy.confidence

    # Add successful experience
    experience_memory.add_experience(
        task_description="Review PR",
        context={"task_type": "review"},
        strategy_used=strategy_id,
        outcome="success",
        evidence=["All checks passed"],
    )

    # Confidence should increase
    assert strategy.confidence > initial_confidence


def test_experience_persistence(temp_dir):
    """Test experience memory persistence."""
    # Create and add data
    mem1 = ExperienceMemory(data_dir=temp_dir)
    mem1.learn_strategy(
        description="Test strategy",
        context={"test": "context"},
        actions=["action1"],
    )

    # Create new instance
    mem2 = ExperienceMemory(data_dir=temp_dir)
    assert len(mem2.strategies) == 1


# ============================================================================
# Memory Verifier Tests
# ============================================================================

@pytest.fixture
def verifier():
    """Create memory verifier."""
    return MemoryVerifier(min_evidence_count=2, min_confidence=0.8)


def test_verifier_extract_evidence(verifier):
    """Test evidence extraction."""
    observation = """
    The authentication system uses JWT tokens.
    Tokens are stored in HTTP-only cookies.
    The system validates tokens on every request.
    """

    claim = "The system uses JWT tokens for authentication"

    evidence = verifier.extract_evidence(observation, claim)

    assert len(evidence) > 0
    assert any("JWT" in e.content for e in evidence)


def test_verifier_detect_contradictions(verifier):
    """Test contradiction detection."""
    verifier.add_existing_memory("The system uses session-based authentication")

    claim = "The system does not use session-based authentication"

    contradictions = verifier.detect_contradictions(claim)

    assert len(contradictions) > 0


def test_verifier_approve_valid_claim(verifier):
    """Test approving valid claims."""
    claim = MemoryClaim(
        claim_id="claim_001",
        content="The API returns JSON responses",
        claim_type="fact",
        evidence=[
            Evidence(
                evidence_id="ev1",
                content="API endpoint returns JSON",
                source="observation",
                confidence=0.9,
            ),
            Evidence(
                evidence_id="ev2",
                content="Response has Content-Type: application/json",
                source="observation",
                confidence=0.95,
            ),
        ],
        confidence=0.9,
    )

    result = verifier.verify_claim(claim)

    assert result.approved is True
    assert result.confidence >= 0.8


def test_verifier_reject_insufficient_evidence(verifier):
    """Test rejecting claims with insufficient evidence."""
    claim = MemoryClaim(
        claim_id="claim_002",
        content="The system is secure",
        claim_type="inference",
        evidence=[
            Evidence(
                evidence_id="ev1",
                content="Uses HTTPS",
                source="observation",
                confidence=0.8,
            ),
        ],
        confidence=0.7,
    )

    result = verifier.verify_claim(claim)

    assert result.approved is False
    assert "Insufficient evidence" in result.reason


def test_verifier_reject_contradictions(verifier):
    """Test rejecting contradictory claims."""
    verifier.add_existing_memory("The database uses PostgreSQL")

    claim = MemoryClaim(
        claim_id="claim_003",
        content="The database does not use PostgreSQL",
        claim_type="fact",
        evidence=[
            Evidence(
                evidence_id="ev1",
                content="Database is MySQL",
                source="observation",
                confidence=0.9,
            ),
            Evidence(
                evidence_id="ev2",
                content="Connection string shows MySQL",
                source="observation",
                confidence=0.9,
            ),
        ],
        confidence=0.9,
    )

    result = verifier.verify_claim(claim)

    assert result.approved is False
    assert len(result.contradictions) > 0


def test_verifier_precision(verifier):
    """Test verifier precision calculation."""
    # Approve some claims
    for i in range(10):
        claim = MemoryClaim(
            claim_id=f"claim_{i}",
            content=f"Valid claim {i}",
            claim_type="fact",
            evidence=[
                Evidence(f"ev{i}_1", "Evidence 1", "obs", 0.9),
                Evidence(f"ev{i}_2", "Evidence 2", "obs", 0.9),
            ],
            confidence=0.9,
        )
        verifier.verify_claim(claim)

    precision = verifier.get_precision()
    assert precision >= 0.95  # Target: >95% precision


# ============================================================================
# Skill Library Tests
# ============================================================================

@pytest.fixture
def skill_library(temp_dir):
    """Create skill library."""
    return SkillLibrary(data_dir=temp_dir)


def test_skill_add_skill(skill_library):
    """Test adding skills."""
    tests = [
        VerificationTest(
            test_id="test_001",
            description="Verify output format",
            expected_output="JSON",
        ),
    ]

    skill_id = skill_library.add_skill(
        name="Format JSON",
        description="Format data as JSON",
        category="formatting",
        implementation="json.dumps(data)",
        verification_tests=tests,
    )

    assert skill_id is not None
    assert len(skill_library.skills) == 1


def test_skill_mandatory_tests(skill_library):
    """Test that skills require verification tests."""
    with pytest.raises(ValueError, match="must have at least one verification test"):
        skill_library.add_skill(
            name="No tests",
            description="Skill without tests",
            category="test",
            implementation="pass",
            verification_tests=[],
        )


def test_skill_execute(skill_library):
    """Test skill execution."""
    tests = [
        VerificationTest(
            test_id="test_001",
            description="Test execution",
        ),
    ]

    skill_id = skill_library.add_skill(
        name="Test skill",
        description="A test skill",
        category="test",
        implementation="return 'success'",
        verification_tests=tests,
    )

    success, output, error = skill_library.execute_skill(
        skill_id,
        {"input": "test"},
    )

    assert success is True
    assert output is not None
    assert skill_library.stats["total_executions"] == 1


def test_skill_repeated_error_prevention(skill_library):
    """Test repeated error prevention."""
    tests = [
        VerificationTest(
            test_id="test_001",
            description="Test",
        ),
    ]

    skill_id = skill_library.add_skill(
        name="Error skill",
        description="Skill that errors",
        category="test",
        implementation="raise Exception('error')",
        verification_tests=tests,
    )

    # Simulate error
    skill = skill_library.skills[skill_id]
    skill.add_execution(
        input_context={"input": "test"},
        output=None,
        success=False,
        error="Test error",
    )

    # Record error pattern
    error_signature = f"{skill_id}_{{'input': 'test'}}"
    skill_library.error_patterns[error_signature] = 1
    skill_library._save_state()

    # Try to execute again - should be prevented
    success, output, error = skill_library.execute_skill(
        skill_id,
        {"input": "test"},
    )

    assert success is False
    assert "Repeated error pattern" in error


def test_skill_improvement(skill_library):
    """Test skill improvement."""
    tests = [
        VerificationTest(
            test_id="test_001",
            description="Test",
        ),
    ]

    skill_id = skill_library.add_skill(
        name="Improvable skill",
        description="Skill to improve",
        category="test",
        implementation="v1",
        verification_tests=tests,
    )

    skill = skill_library.skills[skill_id]
    initial_version = skill.version

    # Improve skill
    success = skill_library.improve_skill(skill_id, "v2")

    assert success is True
    assert skill.version > initial_version
    assert skill.implementation == "v2"


def test_skill_needs_improvement(skill_library):
    """Test identifying skills needing improvement."""
    tests = [
        VerificationTest(
            test_id="test_001",
            description="Test",
        ),
    ]

    skill_id = skill_library.add_skill(
        name="Low success skill",
        description="Skill with low success rate",
        category="test",
        implementation="sometimes fails",
        verification_tests=tests,
    )

    skill = skill_library.skills[skill_id]

    # Add executions with low success rate
    for i in range(10):
        skill.add_execution(
            input_context={"i": i},
            output="result",
            success=(i < 3),  # 30% success rate
        )

    needs_improvement = skill_library.get_skills_needing_improvement(threshold=0.7)

    assert len(needs_improvement) > 0
    assert skill_id in [s.skill_id for s in needs_improvement]


def test_skill_error_reduction(skill_library):
    """Test error reduction rate calculation."""
    tests = [
        VerificationTest(
            test_id="test_001",
            description="Test",
        ),
    ]

    skill_library.add_skill(
        name="Test skill",
        description="Test",
        category="test",
        implementation="test",
        verification_tests=tests,
    )

    # Simulate prevented errors
    skill_library.stats["repeated_errors_prevented"] = 8
    skill_library.stats["failed_executions"] = 2

    error_reduction = skill_library.get_error_reduction_rate()

    assert error_reduction == 0.8  # 80% reduction


def test_skill_persistence(temp_dir):
    """Test skill library persistence."""
    tests = [
        VerificationTest(
            test_id="test_001",
            description="Test",
        ),
    ]

    # Create and add skill
    lib1 = SkillLibrary(data_dir=temp_dir)
    lib1.add_skill(
        name="Persistent skill",
        description="Test persistence",
        category="test",
        implementation="test",
        verification_tests=tests,
    )

    # Create new instance
    lib2 = SkillLibrary(data_dir=temp_dir)
    assert len(lib2.skills) == 1


# ============================================================================
# ECC Learning Tests — Observation Capture, Instinct Extraction, Evolution
# ============================================================================

from lyra_cli.learning.instinct_extractor import (
    Instinct,
    InstinctExtractor,
    get_instinct_extractor,
)
from lyra_cli.learning.observation_capture import (
    Observation,
    ObservationCapture,
    get_observation_capture,
)
from lyra_cli.learning.project_detector import (
    EvolutionPipeline,
    ProjectDetector,
    get_evolution_pipeline,
)


class TestObservationCapture:
    def test_capture_and_retrieve(self, temp_dir):
        oc = ObservationCapture(data_dir=Path(temp_dir))
        obs = Observation(
            timestamp=datetime.now(),
            session_id="test-session",
            tool_name="Write",
            tool_input={"file": "test.py"},
            tool_output={"result": "ok"},
            user_prompt="write a function",
            agent_response="I created test.py",
            project_id="proj-1",
        )
        oc.capture(obs)
        results = oc.get_observations(project_id="proj-1")
        assert len(results) == 1
        assert results[0]["tool_name"] == "Write"

    def test_capture_global_when_no_project(self, temp_dir):
        oc = ObservationCapture(data_dir=Path(temp_dir))
        obs = Observation(
            timestamp=datetime.now(),
            session_id="test",
            tool_name="Bash",
            tool_input={"cmd": "ls"},
            tool_output=None,
            user_prompt=None,
            agent_response=None,
            project_id=None,
        )
        oc.capture(obs)
        results = oc.get_observations()
        assert len(results) == 1

    def test_capture_from_hook(self, temp_dir):
        oc = ObservationCapture(data_dir=Path(temp_dir))
        oc.capture_from_hook(
            hook_context={"tool_name": "Read", "tool_input": {"path": "f.py"}},
            session_id="s1",
            project_id="p1",
        )
        results = oc.get_observations(project_id="p1")
        assert any(r["tool_name"] == "Read" for r in results)

    def test_get_observations_missing_project(self, temp_dir):
        oc = ObservationCapture(data_dir=Path(temp_dir))
        results = oc.get_observations(project_id="nonexistent")
        assert results == []

    def test_get_observations_respects_limit(self, temp_dir):
        oc = ObservationCapture(data_dir=Path(temp_dir))
        for i in range(10):
            oc.capture(Observation(
                timestamp=datetime.now(), session_id=f"s{i}",
                tool_name=f"tool_{i}", tool_input={}, tool_output=None,
                user_prompt=None, agent_response=None, project_id="p",
            ))
        results = oc.get_observations(project_id="p", limit=3)
        assert len(results) == 3

    def test_singleton(self):
        oc1 = get_observation_capture()
        oc2 = get_observation_capture()
        assert oc1 is oc2


class TestInstinctExtractor:
    def test_extract_corrections(self):
        ie = InstinctExtractor()
        obs_list = [
            {"tool_name": "Write", "user_prompt": "create a module", "timestamp": "2026-05-27T10:00:00", "project_id": "test"},
            {"tool_name": "Write", "user_prompt": "no, that's not what I asked", "timestamp": "2026-05-27T10:01:00", "project_id": "test"},
        ]
        instincts = ie.extract_from_observations(obs_list)
        assert any("correction" in i.id for i in instincts)

    def test_extract_repeated_tools(self):
        ie = InstinctExtractor()
        obs_list = [
            {"tool_name": "Write", "user_prompt": "", "timestamp": "2026-05-27T10:00:00", "project_id": "test"},
            {"tool_name": "Write", "user_prompt": "", "timestamp": "2026-05-27T10:01:00", "project_id": "test"},
            {"tool_name": "Write", "user_prompt": "", "timestamp": "2026-05-27T10:02:00", "project_id": "test"},
        ]
        instincts = ie.extract_from_observations(obs_list)
        assert any("repeated" in i.id for i in instincts)

    def test_save_and_load_instinct(self, temp_dir):
        ie = InstinctExtractor(instincts_dir=Path(temp_dir))
        instinct = Instinct(
            id="test-001", trigger="on file write", action="run linter",
            confidence=0.85, domain="code-style", evidence=["rule: pep8"],
            scope="global", project_id=None, created_at=datetime.now(),
        )
        ie.save_instinct(instinct)
        loaded = ie.load_instincts()
        assert len(loaded) == 1
        assert loaded[0].id == "test-001"

    def test_extract_empty_observations(self):
        ie = InstinctExtractor()
        instincts = ie.extract_from_observations([])
        assert instincts == []

    def test_singleton(self):
        ie1 = get_instinct_extractor()
        ie2 = get_instinct_extractor()
        assert ie1 is ie2


class TestProjectDetector:
    def test_detect_project_from_cwd(self):
        pd = ProjectDetector()
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            pytest.skip("Not in a git repository")
        git_root = Path(result.stdout.strip())
        project_id = pd.detect_project_id(cwd=git_root)
        if project_id is None:
            pytest.skip("No remote origin configured")
        assert len(project_id) == 16

    def test_get_project_name(self):
        pd = ProjectDetector()
        name = pd.get_project_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_detect_nonexistent_dir(self):
        pd = ProjectDetector()
        project_id = pd.detect_project_id(cwd=Path("/nonexistent/path"))
        assert project_id is None


class TestEvolutionPipeline:
    def test_evolve_to_skill(self, temp_dir):
        ep = EvolutionPipeline()
        ep.evolved_dir = Path(temp_dir)
        instinct = Instinct(
            id="test-001", trigger="on write", action="run tests",
            confidence=0.9, domain="testing", evidence=["99% pass rate"],
            scope="project", project_id="p1", created_at=datetime.now(),
        )
        skill_path = ep.evolve_to_skill(instinct, "auto-test")
        assert skill_path.exists()
        content = skill_path.read_text()
        assert "run tests" in content

    def test_evolve_to_command(self, temp_dir):
        ep = EvolutionPipeline()
        ep.evolved_dir = Path(temp_dir)
        instinct = Instinct(
            id="test-002", trigger="on lint fail", action="auto-format",
            confidence=0.8, domain="code-style", evidence=["save-time"],
            scope="project", project_id="p1", created_at=datetime.now(),
        )
        cmd_path = ep.evolve_to_command(instinct, "auto-format")
        assert cmd_path.exists()
        content = cmd_path.read_text()
        assert "auto-format" in content

    def test_cluster_instincts(self):
        ep = EvolutionPipeline()
        instincts = [
            Instinct("a", "t1", "a1", 0.7, "testing", [], "global", None, datetime.now()),
            Instinct("b", "t2", "a2", 0.8, "testing", [], "global", None, datetime.now()),
            Instinct("c", "t3", "a3", 0.9, "code-style", [], "global", None, datetime.now()),
        ]
        clusters = ep.cluster_instincts(instincts)
        assert "testing" in clusters
        assert "code-style" in clusters
        assert len(clusters["testing"]) == 2

    def test_promote_to_global(self, temp_dir):
        ie = InstinctExtractor(instincts_dir=Path(temp_dir))
        instinct = Instinct(
            id="promote-me", trigger="on commit", action="run hooks",
            confidence=0.9, domain="git", evidence=["faster"],
            scope="project", project_id="p1", created_at=datetime.now(),
        )
        ie.save_instinct(instinct)
        ep = EvolutionPipeline()
        result = ep.promote_to_global(instinct)
        assert result is True
        assert instinct.scope == "global"

    def test_promote_already_global(self):
        ep = EvolutionPipeline()
        instinct = Instinct(
            id="global-1", trigger="on save", action="format",
            confidence=0.7, domain="code-style", evidence=["clean"],
            scope="global", project_id=None, created_at=datetime.now(),
        )
        result = ep.promote_to_global(instinct)
        assert result is False

    def test_singleton(self):
        ep1 = get_evolution_pipeline()
        ep2 = get_evolution_pipeline()
        assert ep1 is ep2
