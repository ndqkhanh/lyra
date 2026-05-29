"""
Example: Complete Research Pipeline with AutoResearch Integration

Demonstrates all five AutoResearchClaw features working together
"""

import os

from anthropic import Anthropic
from lyra_autoresearch import (
    # Evolution
    EvolutionEngine,
    HITLMode,
    LessonCategory,
    LessonSeverity,
    Perspective,
    # HITL
    create_gate_config,
    # Execution
    execute_with_healing,
    # Debate
    run_debate,
    # Citations
    verify_citations,
)


def main():
    """Run complete research pipeline"""

    print("=" * 60)
    print("AutoResearch Integration Demo")
    print("=" * 60)

    # Initialize components
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    evolution = EvolutionEngine()
    gates = create_gate_config(mode=HITLMode.CRITICAL_GATES)

    # Stage 1: Hypothesis Formation with Debate
    print("\n[Stage 1] Hypothesis Formation")
    print("-" * 60)

    hypothesis = "Sparse attention mechanisms can reduce transformer complexity from O(n²) to O(n log n)"
    context = """
    Current transformers use full attention, which scales quadratically.
    Recent work on sparse patterns shows promise but lacks rigorous analysis.
    """

    debate_result = run_debate(
        topic=hypothesis,
        context=context,
        perspectives=[
            Perspective.SKEPTIC,
            Perspective.OPTIMIST,
            Perspective.METHODOLOGIST,
        ],
        num_rounds=2,
        llm_client=client,
    )

    print(f"Debate completed: {len(debate_result.rounds)} rounds")
    print(f"Consensus: {debate_result.consensus_reached}")
    print(f"\nFinal Synthesis:\n{debate_result.final_synthesis}")

    # Gate: Review hypothesis
    decision = gates.process_gate(
        stage_id="5",
        stage_name="Hypothesis Review",
        output=debate_result.final_synthesis,
    )

    if not decision.approved:
        print("Hypothesis rejected by gate")
        return

    # Stage 2: Experiment Design
    print("\n[Stage 2] Experiment Design")
    print("-" * 60)

    experiment_design = {
        "method": "sparse_attention",
        "datasets": ["wikitext-103", "ptb"],
        "metrics": ["perplexity", "throughput", "memory"],
    }

    print(f"Design: {experiment_design}")

    # Gate: Review design
    decision = gates.process_gate(
        stage_id="9",
        stage_name="Experiment Design Review",
        output=experiment_design,
    )

    if not decision.approved:
        print("Design rejected by gate")
        return

    # Stage 3: Experiment Execution with Self-Healing
    print("\n[Stage 3] Experiment Execution")
    print("-" * 60)

    def run_experiment():
        """Simulate experiment (may fail)"""
        import random
        if random.random() < 0.3:
            raise ValueError("Hyperparameter out of range")
        return {"perplexity": 42.5, "throughput": 1250, "memory": "8GB"}

    def refine_experiment(error, context):
        """Refine on failure"""
        print(f"  Refining after: {error}")
        context["learning_rate"] = context.get("learning_rate", 0.001) * 0.5
        return context

    def pivot_experiment(error, context):
        """Pivot on repeated failure"""
        print(f"  Pivoting after: {error}")
        context["method"] = "alternative_sparse_pattern"
        return context

    exec_result = execute_with_healing(
        task_fn=run_experiment,
        refine_fn=refine_experiment,
        pivot_fn=pivot_experiment,
        max_refines=3,
        max_pivots=2,
    )

    if exec_result.success:
        print(f"✓ Experiment succeeded after {exec_result.iterations} iterations")
        print(f"  Results: {exec_result.output}")
        print(f"  Insights: {exec_result.insights}")

        # Record success lesson
        evolution.record_lesson(
            category=LessonCategory.EXPERIMENT,
            severity=LessonSeverity.INFO,
            description=f"Experiment succeeded with {exec_result.iterations} iterations",
            context={"strategy": "self_healing", "iterations": exec_result.iterations},
        )
    else:
        print(f"✗ Experiment failed after {exec_result.iterations} iterations")

        # Record failure lesson
        evolution.record_lesson(
            category=LessonCategory.EXPERIMENT,
            severity=LessonSeverity.ERROR,
            description=f"Experiment failed: {exec_result.error_message}",
            context={
                "failure_type": exec_result.failure_type.value if exec_result.failure_type else "unknown",
                "iterations": exec_result.iterations,
            },
        )
        return

    # Stage 4: Result Analysis
    print("\n[Stage 4] Result Analysis")
    print("-" * 60)

    analysis = f"""
    Results show {exec_result.output['perplexity']} perplexity,
    {exec_result.output['throughput']} tokens/sec throughput.
    Memory usage: {exec_result.output['memory']}.
    """

    print(analysis)

    # Gate: Review analysis
    decision = gates.process_gate(
        stage_id="15",
        stage_name="Result Analysis Review",
        output=analysis,
    )

    if not decision.approved:
        print("Analysis rejected by gate")
        return

    # Stage 5: Paper Generation with Citation Verification
    print("\n[Stage 5] Paper Generation")
    print("-" * 60)

    paper_text = """
    # Sparse Attention for Efficient Transformers

    ## Abstract
    We propose a sparse attention mechanism that reduces complexity.
    Building on [Vaswani et al., 2017] and recent work arXiv:1706.03762,
    we demonstrate O(n log n) complexity.

    ## Related Work
    Transformers [Vaswani et al., 2017] use full attention.
    Recent sparse patterns [Child et al., 2019] show promise.
    See doi:10.1234/example.2023 for details.
    """

    print("Verifying citations...")
    citation_report = verify_citations(paper_text)

    print(f"\nCitation Integrity Score: {citation_report.integrity_score:.2%}")
    print(f"Verified: {citation_report.verified_count}/{citation_report.total_count}")
    print(f"Suspicious: {citation_report.suspicious_count}")
    print(f"Hallucinated: {citation_report.hallucinated_count}")

    if citation_report.hallucinated_count > 0:
        print("\n⚠️  Warning: Hallucinated citations detected!")
        evolution.record_lesson(
            category=LessonCategory.WRITING,
            severity=LessonSeverity.ERROR,
            description="Paper contains hallucinated citations",
            context={"count": citation_report.hallucinated_count},
        )

    # Gate: Review paper
    decision = gates.process_gate(
        stage_id="20",
        stage_name="Paper Review",
        output=paper_text,
    )

    if not decision.approved:
        print("Paper rejected by gate")
        return

    # Stage 6: Evolution - Learn from this run
    print("\n[Stage 6] Evolution")
    print("-" * 60)

    print("Running evolution cycle...")
    synthesized_skills = evolution.evolve(sync_to_memoria=False)

    print(f"Synthesized {len(synthesized_skills)} new skills")
    for skill in synthesized_skills:
        print(f"  - {skill.name}: {skill.description}")

    # Final Statistics
    print("\n" + "=" * 60)
    print("Pipeline Complete")
    print("=" * 60)

    gate_stats = gates.get_statistics()
    print("\nGate Statistics:")
    print(f"  Total gates: {gate_stats['total_gates']}")
    print(f"  Approved: {gate_stats['approved']}")
    print(f"  Rejected: {gate_stats['rejected']}")
    print(f"  Modified: {gate_stats['modified']}")

    print("\nEvolution:")
    print(f"  Lessons recorded: {len(evolution.store.get_lessons())}")
    print(f"  Skills synthesized: {len(synthesized_skills)}")

    print("\n✓ Research pipeline completed successfully!")


if __name__ == "__main__":
    main()
