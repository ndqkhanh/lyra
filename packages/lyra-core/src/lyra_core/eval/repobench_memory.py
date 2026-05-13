"""
RepoBench-Memory Evaluation Harness for Lyra's T3 Memory System.

This module implements the RepoBench benchmark (ICLR 2024) adapted for evaluating
Lyra's T3 (User/Team) memory system. RepoBench is a repository-level code completion
benchmark that tests the ability to retrieve and use cross-file context.

Reference: https://github.com/Leolty/repobench
Paper: https://arxiv.org/abs/2306.03091

Three evaluation tasks:
- RepoBench-R (Retrieval): Tests ability to retrieve relevant code snippets
- RepoBench-C (Completion): Measures next-line prediction with cross-file context
- RepoBench-P (Pipeline): Combines retrieval and completion end-to-end

Three evaluation contexts:
- cross_file_first: First occurrence of cross-file module usage
- cross_file_random: Subsequent occurrences of cross-file usage
- in_file: No cross-file dependencies (baseline)

Metrics:
- Exact Match (EM): Exact string match
- Edit Similarity (ES): Levenshtein-based similarity
- CodeBLEU: Code-aware BLEU metric
- Accuracy@k: Top-k retrieval accuracy
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal

try:
    from datasets import load_dataset
    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False

try:
    from codebleu import calc_codebleu
    HAS_CODEBLEU = True
except ImportError:
    HAS_CODEBLEU = False


class EvalContext(str, Enum):
    """Evaluation context types for RepoBench."""
    CROSS_FILE_FIRST = "cross_file_first"
    CROSS_FILE_RANDOM = "cross_file_random"
    IN_FILE = "in_file"


class EvalTask(str, Enum):
    """Evaluation task types for RepoBench."""
    RETRIEVAL = "retrieval"  # RepoBench-R
    COMPLETION = "completion"  # RepoBench-C
    PIPELINE = "pipeline"  # RepoBench-P


@dataclass
class RepoBenchSample:
    """A single sample from RepoBench dataset."""
    repo_name: str
    file_path: str
    context: str  # Code context before the target line
    target: str  # Ground truth completion
    cross_file_context: list[str] = field(default_factory=list)  # Relevant snippets from other files
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalMetrics:
    """Evaluation metrics for a single sample or dataset."""
    exact_match: float = 0.0
    edit_similarity: float = 0.0
    codebleu: float = 0.0
    accuracy_at_1: float = 0.0
    accuracy_at_3: float = 0.0
    accuracy_at_5: float = 0.0
    num_samples: int = 0


@dataclass
class EvalResult:
    """Complete evaluation result for a task."""
    task: EvalTask
    context: EvalContext
    language: Literal["python", "java"]
    metrics: EvalMetrics
    per_sample_results: list[dict[str, Any]] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


class RepoBenchMemoryEval:
    """
    RepoBench-Memory evaluation harness for Lyra's T3 memory system.

    This class loads RepoBench datasets, generates completions using Lyra's
    LLM providers with T3 memory context, and computes evaluation metrics.
    """

    def __init__(
        self,
        t3_memory_dir: Path | str | None = None,
        cache_dir: Path | str | None = None,
    ):
        """
        Initialize RepoBench-Memory evaluator.

        Args:
            t3_memory_dir: Directory containing T3 memory files (user.md, team.md)
            cache_dir: Directory for caching datasets and results
        """
        self.t3_memory_dir = Path(t3_memory_dir) if t3_memory_dir else None
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".cache" / "lyra" / "repobench"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not HAS_DATASETS:
            raise ImportError(
                "datasets library is required for RepoBench evaluation. "
                "Install with: pip install datasets"
            )

    def load_dataset(
        self,
        language: Literal["python", "java"],
        context: EvalContext,
        split: Literal["train", "test"] = "test",
        max_samples: int | None = None,
    ) -> list[RepoBenchSample]:
        """
        Load RepoBench dataset from Hugging Face.

        Args:
            language: Programming language (python or java)
            context: Evaluation context type
            split: Dataset split (train or test)
            max_samples: Maximum number of samples to load (None for all)

        Returns:
            List of RepoBenchSample objects
        """
        # RepoBench dataset naming convention on Hugging Face
        dataset_name = f"tianyang/repobench_{language}_{context.value}"

        try:
            dataset = load_dataset(dataset_name, split=split, cache_dir=str(self.cache_dir))
        except Exception as e:
            raise RuntimeError(
                f"Failed to load RepoBench dataset '{dataset_name}': {e}\n"
                f"Make sure you have internet connection and the dataset exists on Hugging Face."
            ) from e

        samples = []
        for i, item in enumerate(dataset):
            if max_samples and i >= max_samples:
                break

            # Dataset items are dict-like objects from Hugging Face datasets
            item_dict = dict(item) if not isinstance(item, dict) else item
            sample = RepoBenchSample(
                repo_name=item_dict.get("repo_name", "unknown"),
                file_path=item_dict.get("file_path", "unknown"),
                context=item_dict.get("context", ""),
                target=item_dict.get("target", ""),
                cross_file_context=item_dict.get("cross_file_context", []),
                metadata=item_dict.get("metadata", {}),
            )
            samples.append(sample)

        return samples

    def compute_exact_match(self, prediction: str, target: str) -> float:
        """
        Compute Exact Match (EM) score.

        Args:
            prediction: Predicted completion
            target: Ground truth completion

        Returns:
            1.0 if exact match, 0.0 otherwise
        """
        return 1.0 if prediction.strip() == target.strip() else 0.0

    def compute_edit_similarity(self, prediction: str, target: str) -> float:
        """
        Compute Edit Similarity (ES) using Levenshtein distance.

        Args:
            prediction: Predicted completion
            target: Ground truth completion

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Levenshtein distance implementation
        pred = prediction.strip()
        tgt = target.strip()

        if len(pred) == 0 and len(tgt) == 0:
            return 1.0
        if len(pred) == 0 or len(tgt) == 0:
            return 0.0

        # Dynamic programming for Levenshtein distance
        m, n = len(pred), len(tgt)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if pred[i - 1] == tgt[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

        distance = dp[m][n]
        max_len = max(len(pred), len(tgt))
        return 1.0 - (distance / max_len)

    def compute_codebleu(
        self,
        prediction: str,
        target: str,
        language: Literal["python", "java"],
    ) -> float:
        """
        Compute CodeBLEU score.

        Args:
            prediction: Predicted completion
            target: Ground truth completion
            language: Programming language

        Returns:
            CodeBLEU score between 0.0 and 1.0
        """
        if not HAS_CODEBLEU:
            # Fallback to simple token-based BLEU if codebleu not available
            return self._compute_simple_bleu(prediction, target)

        try:
            result = calc_codebleu(
                [target],
                [prediction],
                lang=language,
                weights=(0.25, 0.25, 0.25, 0.25),
                tokenizer=None,
            )
            return result["codebleu"]
        except Exception:
            # Fallback on error
            return self._compute_simple_bleu(prediction, target)

    def _compute_simple_bleu(self, prediction: str, target: str) -> float:
        """Simple token-based BLEU as fallback."""
        pred_tokens = prediction.strip().split()
        tgt_tokens = target.strip().split()

        if not pred_tokens or not tgt_tokens:
            return 0.0

        # Unigram precision
        matches = sum(1 for token in pred_tokens if token in tgt_tokens)
        precision = matches / len(pred_tokens) if pred_tokens else 0.0

        # Brevity penalty
        bp = 1.0 if len(pred_tokens) >= len(tgt_tokens) else len(pred_tokens) / len(tgt_tokens)

        return bp * precision

    def compute_accuracy_at_k(
        self,
        retrieved: list[str],
        relevant: list[str],
        k: int,
    ) -> float:
        """
        Compute Accuracy@k for retrieval task.

        Args:
            retrieved: List of retrieved snippets (ranked)
            relevant: List of relevant snippets (ground truth)
            k: Top-k cutoff

        Returns:
            1.0 if any relevant snippet in top-k, 0.0 otherwise
        """
        if not relevant:
            return 1.0  # No relevant snippets to retrieve

        top_k = retrieved[:k]
        return 1.0 if any(snippet in relevant for snippet in top_k) else 0.0

    def evaluate_completion(
        self,
        samples: list[RepoBenchSample],
        generate_fn: Callable[[str, list[str]], str],
        language: Literal["python", "java"],
        context: EvalContext,
    ) -> EvalResult:
        """
        Evaluate completion task (RepoBench-C).

        Args:
            samples: List of evaluation samples
            generate_fn: Function that takes (context, cross_file_context) and returns prediction
            language: Programming language
            context: Evaluation context type

        Returns:
            EvalResult with aggregated metrics
        """
        total_em = 0.0
        total_es = 0.0
        total_cb = 0.0
        per_sample_results = []

        for sample in samples:
            # Generate prediction using provided function
            prediction = generate_fn(sample.context, sample.cross_file_context)

            # Compute metrics
            em = self.compute_exact_match(prediction, sample.target)
            es = self.compute_edit_similarity(prediction, sample.target)
            cb = self.compute_codebleu(prediction, sample.target, language)

            total_em += em
            total_es += es
            total_cb += cb

            per_sample_results.append({
                "repo_name": sample.repo_name,
                "file_path": sample.file_path,
                "prediction": prediction,
                "target": sample.target,
                "exact_match": em,
                "edit_similarity": es,
                "codebleu": cb,
            })

        n = len(samples)
        metrics = EvalMetrics(
            exact_match=total_em / n if n > 0 else 0.0,
            edit_similarity=total_es / n if n > 0 else 0.0,
            codebleu=total_cb / n if n > 0 else 0.0,
            num_samples=n,
        )

        return EvalResult(
            task=EvalTask.COMPLETION,
            context=context,
            language=language,
            metrics=metrics,
            per_sample_results=per_sample_results,
        )

    def evaluate_retrieval(
        self,
        samples: list[RepoBenchSample],
        retrieve_fn: Callable[[str], list[str]],
        context: EvalContext,
    ) -> EvalResult:
        """
        Evaluate retrieval task (RepoBench-R).

        Args:
            samples: List of evaluation samples
            retrieve_fn: Function that takes context and returns ranked list of retrieved snippets
            context: Evaluation context type

        Returns:
            EvalResult with aggregated metrics
        """
        total_acc1 = 0.0
        total_acc3 = 0.0
        total_acc5 = 0.0
        per_sample_results = []

        for sample in samples:
            # Retrieve snippets using provided function
            retrieved = retrieve_fn(sample.context)
            relevant = sample.cross_file_context

            # Compute accuracy@k
            acc1 = self.compute_accuracy_at_k(retrieved, relevant, k=1)
            acc3 = self.compute_accuracy_at_k(retrieved, relevant, k=3)
            acc5 = self.compute_accuracy_at_k(retrieved, relevant, k=5)

            total_acc1 += acc1
            total_acc3 += acc3
            total_acc5 += acc5

            per_sample_results.append({
                "repo_name": sample.repo_name,
                "file_path": sample.file_path,
                "retrieved": retrieved[:5],  # Top-5 for inspection
                "relevant": relevant,
                "accuracy_at_1": acc1,
                "accuracy_at_3": acc3,
                "accuracy_at_5": acc5,
            })

        n = len(samples)
        metrics = EvalMetrics(
            accuracy_at_1=total_acc1 / n if n > 0 else 0.0,
            accuracy_at_3=total_acc3 / n if n > 0 else 0.0,
            accuracy_at_5=total_acc5 / n if n > 0 else 0.0,
            num_samples=n,
        )

        return EvalResult(
            task=EvalTask.RETRIEVAL,
            context=context,
            language="python",  # Language not critical for retrieval
            metrics=metrics,
            per_sample_results=per_sample_results,
        )

    def save_results(self, result: EvalResult, output_path: Path | str) -> None:
        """
        Save evaluation results to JSON file.

        Args:
            result: EvalResult to save
            output_path: Path to output JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result_dict = {
            "task": result.task.value,
            "context": result.context.value,
            "language": result.language,
            "metrics": {
                "exact_match": result.metrics.exact_match,
                "edit_similarity": result.metrics.edit_similarity,
                "codebleu": result.metrics.codebleu,
                "accuracy_at_1": result.metrics.accuracy_at_1,
                "accuracy_at_3": result.metrics.accuracy_at_3,
                "accuracy_at_5": result.metrics.accuracy_at_5,
                "num_samples": result.metrics.num_samples,
            },
            "per_sample_results": result.per_sample_results,
            "config": result.config,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)

    def load_results(self, input_path: Path | str) -> EvalResult:
        """
        Load evaluation results from JSON file.

        Args:
            input_path: Path to input JSON file

        Returns:
            EvalResult object
        """
        with open(input_path, "r", encoding="utf-8") as f:
            result_dict = json.load(f)

        metrics = EvalMetrics(
            exact_match=result_dict["metrics"]["exact_match"],
            edit_similarity=result_dict["metrics"]["edit_similarity"],
            codebleu=result_dict["metrics"]["codebleu"],
            accuracy_at_1=result_dict["metrics"]["accuracy_at_1"],
            accuracy_at_3=result_dict["metrics"]["accuracy_at_3"],
            accuracy_at_5=result_dict["metrics"]["accuracy_at_5"],
            num_samples=result_dict["metrics"]["num_samples"],
        )

        return EvalResult(
            task=EvalTask(result_dict["task"]),
            context=EvalContext(result_dict["context"]),
            language=result_dict["language"],
            metrics=metrics,
            per_sample_results=result_dict.get("per_sample_results", []),
            config=result_dict.get("config", {}),
        )
