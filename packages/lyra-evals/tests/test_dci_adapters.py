"""Tests for the DCI eval adapters — BCP, multi-hop QA, BRIGHT.

Cite: arXiv:2605.05242 (paper Table 1); DCI-Agent-Lite eval scripts.

Phase 0: contracts + loader + scorer only. Each adapter ships its
JSONL loader, its task dataclass, and its scoring function; the
actual benchmark run wires through ``InvestigationRunner`` and
lives in a follow-up.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_evals.adapters.bright import (
    BrightTask,
    load_bright,
    score_bright,
)
from lyra_evals.adapters.browsecomp_plus import (
    BCPTask,
    load_browsecomp_plus,
    score_bcp,
)
from lyra_evals.adapters.multihop_qa import (
    MultiHopQATask,
    load_multihop_qa,
    score_multihop_qa,
)


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


# ---------------------------------------------------------------------------
# BrowseComp-Plus
# ---------------------------------------------------------------------------


class TestBCPAdapter:
    def test_loads_well_formed_jsonl(self, tmp_path: Path) -> None:
        f = _write_jsonl(
            tmp_path / "bcp.jsonl",
            [
                {"instance_id": "bcp-1", "question": "Q1", "gold_answer": "FORTY_TWO"},
                {"instance_id": "bcp-2", "question": "Q2", "gold_answer": "rome"},
            ],
        )
        tasks = load_browsecomp_plus(f, corpus_root=tmp_path)
        assert len(tasks) == 2
        assert isinstance(tasks[0], BCPTask)
        assert tasks[0].instance_id == "bcp-1"

    def test_limit_caps_intake(self, tmp_path: Path) -> None:
        f = _write_jsonl(
            tmp_path / "bcp.jsonl",
            [
                {"instance_id": f"bcp-{i}", "question": "Q", "gold_answer": "A"}
                for i in range(5)
            ],
        )
        tasks = load_browsecomp_plus(f, corpus_root=tmp_path, limit=2)
        assert len(tasks) == 2

    def test_blank_lines_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "bcp.jsonl"
        f.write_text(
            json.dumps({"instance_id": "x", "question": "q", "gold_answer": "a"})
            + "\n\n\n",
        )
        tasks = load_browsecomp_plus(f, corpus_root=tmp_path)
        assert len(tasks) == 1

    def test_rejects_missing_keys(self, tmp_path: Path) -> None:
        f = _write_jsonl(
            tmp_path / "bcp.jsonl",
            [{"instance_id": "x", "question": "q"}],   # no gold_answer
        )
        with pytest.raises(ValueError, match="missing keys"):
            load_browsecomp_plus(f, corpus_root=tmp_path)

    def test_score_passes_on_substring_match(self, tmp_path: Path) -> None:
        task = BCPTask(
            instance_id="x", question="q",
            gold_answer="FORTY_TWO", corpus_root=tmp_path,
        )
        result = score_bcp(task=task, predicted="The answer is FORTY_TWO per intro.md:2")
        assert result.passed is True

    def test_score_fails_when_gold_absent(self, tmp_path: Path) -> None:
        task = BCPTask(
            instance_id="x", question="q",
            gold_answer="FORTY_TWO", corpus_root=tmp_path,
        )
        result = score_bcp(task=task, predicted="I don't know")
        assert result.passed is False

    def test_score_is_case_insensitive(self, tmp_path: Path) -> None:
        task = BCPTask(
            instance_id="x", question="q",
            gold_answer="Rome", corpus_root=tmp_path,
        )
        assert score_bcp(task=task, predicted="rome is the answer").passed is True


# ---------------------------------------------------------------------------
# Multi-hop QA
# ---------------------------------------------------------------------------


class TestMultiHopQAAdapter:
    def test_loads_all_six_datasets(self, tmp_path: Path) -> None:
        rows = []
        for ds in ("hotpotqa", "musique", "2wiki", "nq", "trivia", "bamboogle"):
            rows.append(
                {
                    "instance_id": f"{ds}-1", "dataset": ds,
                    "question": "q", "gold_answers": ["a"],
                }
            )
        f = _write_jsonl(tmp_path / "qa.jsonl", rows)
        tasks = load_multihop_qa(f, corpus_root=tmp_path)
        assert len(tasks) == 6
        assert {t.dataset for t in tasks} == {
            "hotpotqa", "musique", "2wiki", "nq", "trivia", "bamboogle",
        }

    def test_string_gold_promoted_to_tuple(self, tmp_path: Path) -> None:
        f = _write_jsonl(
            tmp_path / "qa.jsonl",
            [{
                "instance_id": "h-1", "dataset": "hotpotqa",
                "question": "q", "gold_answers": "single string",
            }],
        )
        tasks = load_multihop_qa(f, corpus_root=tmp_path)
        assert tasks[0].gold_answers == ("single string",)

    def test_supporting_facts_optional(self, tmp_path: Path) -> None:
        f = _write_jsonl(
            tmp_path / "qa.jsonl",
            [{
                "instance_id": "h-1", "dataset": "hotpotqa",
                "question": "q", "gold_answers": ["a"],
                "supporting_facts": ["doc1:para3"],
            }],
        )
        tasks = load_multihop_qa(f, corpus_root=tmp_path)
        assert tasks[0].supporting_facts == ("doc1:para3",)

    def test_rejects_unknown_dataset(self, tmp_path: Path) -> None:
        f = _write_jsonl(
            tmp_path / "qa.jsonl",
            [{
                "instance_id": "x", "dataset": "made_up",
                "question": "q", "gold_answers": ["a"],
            }],
        )
        with pytest.raises(ValueError, match="unsupported dataset"):
            load_multihop_qa(f, corpus_root=tmp_path)

    def test_score_passes_with_any_alias(self, tmp_path: Path) -> None:
        task = MultiHopQATask(
            instance_id="x", dataset="hotpotqa", question="q",
            gold_answers=("Eiffel Tower", "the Eiffel Tower"),
            corpus_root=tmp_path,
        )
        r = score_multihop_qa(task=task, predicted="It is the eiffel tower in Paris")
        assert r.passed is True

    def test_score_normalises_punctuation(self, tmp_path: Path) -> None:
        task = MultiHopQATask(
            instance_id="x", dataset="hotpotqa", question="q",
            gold_answers=("FORTY-TWO",),
            corpus_root=tmp_path,
        )
        r = score_multihop_qa(task=task, predicted="Answer: FORTY-TWO.")
        assert r.passed is True

    def test_score_fails_clean_on_miss(self, tmp_path: Path) -> None:
        task = MultiHopQATask(
            instance_id="x", dataset="hotpotqa", question="q",
            gold_answers=("Rome",),
            corpus_root=tmp_path,
        )
        r = score_multihop_qa(task=task, predicted="Paris")
        assert r.passed is False
        assert "Rome" in r.reason


# ---------------------------------------------------------------------------
# BRIGHT
# ---------------------------------------------------------------------------


class TestBrightAdapter:
    def test_loads_all_four_splits(self, tmp_path: Path) -> None:
        rows = [
            {
                "instance_id": f"{s}-1", "split": s,
                "question": "q", "gold_doc_ids": ["d1", "d2"],
            }
            for s in ("biology", "earth_science", "economics", "robotics")
        ]
        f = _write_jsonl(tmp_path / "bright.jsonl", rows)
        tasks = load_bright(f, corpus_root=tmp_path)
        assert len(tasks) == 4

    def test_rejects_unknown_split(self, tmp_path: Path) -> None:
        f = _write_jsonl(
            tmp_path / "bright.jsonl",
            [{
                "instance_id": "x", "split": "chemistry",
                "question": "q", "gold_doc_ids": ["d1"],
            }],
        )
        with pytest.raises(ValueError, match="unsupported split"):
            load_bright(f, corpus_root=tmp_path)

    def test_score_mrr_at_rank_one(self, tmp_path: Path) -> None:
        task = BrightTask(
            instance_id="x", split="biology", question="q",
            gold_doc_ids=("d1", "d2"), corpus_root=tmp_path,
        )
        r = score_bright(task=task, predicted="d1 then d2 then d3")
        assert r.passed is True
        assert "1.000" in r.reason

    def test_score_mrr_at_rank_three(self, tmp_path: Path) -> None:
        task = BrightTask(
            instance_id="x", split="biology", question="q",
            gold_doc_ids=("d3",), corpus_root=tmp_path,
        )
        r = score_bright(task=task, predicted="d_other d_other2 d3 d4")
        assert r.passed is True
        # 1/3 ≈ 0.333
        assert "0.333" in r.reason

    def test_score_zero_when_gold_missing(self, tmp_path: Path) -> None:
        task = BrightTask(
            instance_id="x", split="biology", question="q",
            gold_doc_ids=("d9",), corpus_root=tmp_path,
        )
        r = score_bright(task=task, predicted="d1 d2 d3")
        assert r.passed is False
        assert "mrr@10=0.000" in r.reason

    def test_score_honours_k_cap(self, tmp_path: Path) -> None:
        """Gold appears at rank 11 — outside the k=10 window, so MRR=0."""
        task = BrightTask(
            instance_id="x", split="biology", question="q",
            gold_doc_ids=("d_target",), corpus_root=tmp_path,
        )
        predicted = " ".join([f"d{i}" for i in range(10)]) + " d_target"
        r = score_bright(task=task, predicted=predicted, k=10)
        assert r.passed is False

    def test_score_caps_at_k(self, tmp_path: Path) -> None:
        task = BrightTask(
            instance_id="x", split="biology", question="q",
            gold_doc_ids=("d_target",), corpus_root=tmp_path,
        )
        predicted = " ".join([f"d{i}" for i in range(50)]) + " d_target"
        r = score_bright(task=task, predicted=predicted, k=3)
        # d_target is at position 51 — outside k=3 window
        assert r.passed is False
