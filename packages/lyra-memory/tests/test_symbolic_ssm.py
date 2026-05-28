"""Tests for Symbolic SSM (Mermaid Canvas) and CraniMem gate."""

import tempfile
from pathlib import Path

from lyra_memory.symbolic_ssm import (
    CraniMemGate,
    SymbolicRepresentation,
    SymbolicShortTermMemory,
    _estimate_tokens,
    _slugify,
)

SAMPLE_BASH_OUTPUT = """test_foo.py
test_bar.py
src/main.py
def test_addition():
def test_subtraction():
class TestCalculator:
FAILED tests/test_foo.py::test_addition - AssertionError: 2 != 3
FAILED tests/test_bar.py::test_subtraction - ValueError: invalid input
8 passed, 2 failed, 1 warning in 5.23s"""


class TestSymbolicShortTermMemory:
    def test_compress_returns_representation(self):
        sstm = SymbolicShortTermMemory(refs_dir=Path(tempfile.mkdtemp()))
        rep = sstm.compress("bash", SAMPLE_BASH_OUTPUT * 5)
        assert isinstance(rep, SymbolicRepresentation)
        assert rep.node_id.startswith("bash-")
        assert len(rep.mermaid_graph) > 0
        assert len(rep.summary) > 0

    def test_compress_saves_ref_file(self):
        sstm = SymbolicShortTermMemory(refs_dir=Path(tempfile.mkdtemp()))
        rep = sstm.compress("bash", SAMPLE_BASH_OUTPUT)
        ref_path = Path(rep.ref_path)
        assert ref_path.exists()
        content = ref_path.read_text()
        assert SAMPLE_BASH_OUTPUT in content
        assert rep.node_id in content

    def test_recall_retrieves_full_text(self):
        sstm = SymbolicShortTermMemory(refs_dir=Path(tempfile.mkdtemp()))
        rep = sstm.compress("bash", SAMPLE_BASH_OUTPUT)
        recalled = sstm.recall(rep.node_id)
        assert recalled is not None
        assert SAMPLE_BASH_OUTPUT in recalled

    def test_recall_returns_none_for_unknown_id(self):
        sstm = SymbolicShortTermMemory(refs_dir=Path(tempfile.mkdtemp()))
        assert sstm.recall("nonexistent-1234abcd") is None

    def test_extracts_file_entities(self):
        sstm = SymbolicShortTermMemory(refs_dir=Path(tempfile.mkdtemp()))
        entities = sstm._extract_entities(SAMPLE_BASH_OUTPUT)
        files = [e for e in entities if e.kind == "file"]
        assert len(files) >= 2
        file_names = {e.name for e in files}
        assert "test_foo.py" in file_names or any("test_foo" in n for n in file_names)

    def test_extracts_function_entities(self):
        sstm = SymbolicShortTermMemory(refs_dir=Path(tempfile.mkdtemp()))
        entities = sstm._extract_entities(SAMPLE_BASH_OUTPUT)
        funcs = [e for e in entities if e.kind == "function"]
        assert len(funcs) >= 2

    def test_extracts_error_entities(self):
        sstm = SymbolicShortTermMemory(refs_dir=Path(tempfile.mkdtemp()))
        entities = sstm._extract_entities(SAMPLE_BASH_OUTPUT)
        errors = [e for e in entities if e.kind == "error"]
        assert len(errors) >= 2

    def test_extracts_result_entities(self):
        sstm = SymbolicShortTermMemory(refs_dir=Path(tempfile.mkdtemp()))
        entities = sstm._extract_entities(SAMPLE_BASH_OUTPUT)
        results = [e for e in entities if e.kind == "result"]
        assert len(results) >= 1

    def test_mermaid_graph_is_valid(self):
        sstm = SymbolicShortTermMemory(refs_dir=Path(tempfile.mkdtemp()))
        entities = sstm._extract_entities(SAMPLE_BASH_OUTPUT)
        relations = sstm._extract_relations(entities)
        graph = sstm._build_mermaid(entities, relations)
        assert graph.startswith("graph TD")
        assert "-->" in graph or "---" in graph

    def test_compression_achieves_token_savings(self):
        sstm = SymbolicShortTermMemory(refs_dir=Path(tempfile.mkdtemp()))
        long_output = SAMPLE_BASH_OUTPUT * 20
        rep = sstm.compress("bash", long_output)
        assert rep.token_savings > 0.0

    def test_context_tokens_are_lower_than_original(self):
        sstm = SymbolicShortTermMemory(refs_dir=Path(tempfile.mkdtemp()))
        rep = sstm.compress("bash", SAMPLE_BASH_OUTPUT * 10)
        original_tokens = _estimate_tokens(SAMPLE_BASH_OUTPUT * 10)
        assert rep.context_tokens < original_tokens


class TestCraniMemGate:
    def test_admits_when_no_goals_set(self):
        gate = CraniMemGate()
        admitted, score = gate.should_admit("any content here")
        assert admitted is True
        assert score == 1.0

    def test_admits_aligned_content(self):
        gate = CraniMemGate(min_goal_alignment=0.3)
        gate.set_goals(["implement authentication system"])
        admitted, score = gate.should_admit("authentication module with login and password")
        assert admitted is True
        assert score > 0

    def test_rejects_misaligned_content(self):
        gate = CraniMemGate(min_goal_alignment=0.3)
        gate.set_goals(["implement authentication system"])
        admitted, score = gate.should_admit("fix the CSS padding on the footer")
        assert admitted is False

    def test_add_and_remove_goals(self):
        gate = CraniMemGate()
        gate.add_goal("goal-a")
        gate.add_goal("goal-b")
        assert len(gate.active_goals) == 2
        gate.remove_goal("goal-a")
        assert gate.active_goals == ["goal-b"]
        gate.remove_goal("nonexistent")
        assert gate.active_goals == ["goal-b"]

    def test_set_goals_replaces_all(self):
        gate = CraniMemGate()
        gate.add_goal("old-goal")
        gate.set_goals(["new-goal-1", "new-goal-2"])
        assert len(gate.active_goals) == 2

    def test_duplicate_goal_not_added(self):
        gate = CraniMemGate()
        gate.add_goal("goal")
        gate.add_goal("goal")
        assert len(gate.active_goals) == 1


class TestHelpers:
    def test_estimate_tokens(self):
        assert _estimate_tokens("") == 1
        assert _estimate_tokens("hello") == 1
        assert _estimate_tokens("a" * 100) == 25

    def test_slugify_normal(self):
        assert _slugify("hello_world") == "hello_world"

    def test_slugify_special_chars(self):
        assert _slugify("hello world.py") == "hello_world_py"

    def test_slugify_long_name(self):
        long_name = "a" * 100
        assert len(_slugify(long_name)) == 40
