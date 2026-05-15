"""
Ctx2Skill: Adversarial Self-Play for Context-Specific Skill Discovery

Implements 5-role adversarial loop for discovering skills from context documents:
- Challenger: Generates hard questions
- Reasoner: Attempts to answer with current skills
- Judge: Evaluates answer quality
- Proposer: Suggests skill improvements
- Generator: Materializes skills as SKILL.md

Based on research: docs/154 (ctx2skill-self-evolving-context-skills.md)
Impact: +5.4pp on GPT-4.1 with skills
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib


@dataclass
class SkillProposal:
    """Proposed skill from adversarial loop."""
    id: str
    title: str
    description: str
    keywords: List[str]
    body: str
    confidence: float
    source_questions: List[str]


class Ctx2SkillPipeline:
    """
    Context-to-Skill adversarial self-play pipeline.

    Discovers skills from context documents through iterative
    adversarial questioning and skill refinement.
    """

    def __init__(
        self,
        llm_challenger,
        llm_reasoner,
        llm_judge,
        llm_proposer,
        llm_generator,
        skills_dir: Path
    ):
        """
        Initialize Ctx2Skill pipeline.

        Args:
            llm_challenger: LLM for generating hard questions
            llm_reasoner: LLM for answering questions
            llm_judge: LLM for evaluating answers
            llm_proposer: LLM for proposing skills
            llm_generator: LLM for generating skill files
            skills_dir: Directory to save generated skills
        """
        self.challenger = llm_challenger
        self.reasoner = llm_reasoner
        self.judge = llm_judge
        self.proposer = llm_proposer
        self.generator = llm_generator
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        self.hard_probe: List[str] = []
        self.easy_probe: List[str] = []

    def run(
        self,
        context_docs: List[str],
        iterations: int = 5,
        questions_per_iter: int = 10
    ) -> List[Path]:
        """
        Run Ctx2Skill pipeline.

        Args:
            context_docs: Context documents to extract skills from
            iterations: Number of adversarial iterations
            questions_per_iter: Questions to generate per iteration

        Returns:
            List of paths to generated skill files
        """
        skills: List[SkillProposal] = []
        skill_files: List[Path] = []

        for iteration in range(iterations):
            print(f"\n=== Ctx2Skill Iteration {iteration + 1}/{iterations} ===")

            # Step 1: Challenger generates hard questions
            questions = self._generate_questions(
                context_docs,
                difficulty="hard",
                k=questions_per_iter
            )

            # Step 2: Reasoner attempts to answer with current skills
            answers = self._answer_questions(questions, skills)

            # Step 3: Judge evaluates answers
            evaluations = self._evaluate_answers(questions, answers)

            # Step 4: Build probe sets
            failures = [
                q for q, e in zip(questions, evaluations)
                if not e['correct']
            ]
            successes = [
                q for q, e in zip(questions, evaluations)
                if e['correct']
            ]

            self.hard_probe.extend(failures[:3])
            self.easy_probe.extend(successes[:3])

            # Step 5: Proposer suggests skill improvements
            if failures:
                proposals = self._propose_skills(
                    failures=failures,
                    current_skills=skills,
                    context=context_docs
                )

                # Step 6: Generator materializes skills
                for proposal in proposals:
                    skill_file = self._generate_skill_file(proposal)
                    skill_files.append(skill_file)
                    skills.append(proposal)

            # Step 7: Cross-Time Replay (select best skill set)
            if iteration > 0:
                skills = self._cross_time_replay(skills)

        return skill_files

    def _generate_questions(
        self,
        context_docs: List[str],
        difficulty: str,
        k: int
    ) -> List[str]:
        """Generate questions from context."""
        context_text = "\n\n".join(context_docs[:5])  # Limit context

        prompt = f"""Generate {k} {difficulty} questions from this context.

Context:
{context_text}

Requirements:
- Questions should test deep understanding
- Focus on non-obvious insights
- Require synthesis across multiple facts
- {difficulty} difficulty level

Output JSON array of questions:
["Question 1?", "Question 2?", ...]
"""

        response = self.challenger.generate(prompt)
        try:
            questions = json.loads(response)
            return questions[:k]
        except:
            return []

    def _answer_questions(
        self,
        questions: List[str],
        skills: List[SkillProposal]
    ) -> List[str]:
        """Answer questions using current skills."""
        # Format skills for context
        skills_text = "\n\n".join([
            f"Skill: {s.title}\n{s.body}"
            for s in skills
        ])

        answers = []
        for question in questions:
            prompt = f"""Answer this question using the provided skills.

Skills:
{skills_text}

Question: {question}

Answer:"""

            answer = self.reasoner.generate(prompt)
            answers.append(answer)

        return answers

    def _evaluate_answers(
        self,
        questions: List[str],
        answers: List[str]
    ) -> List[Dict[str, Any]]:
        """Evaluate answer quality."""
        evaluations = []

        for question, answer in zip(questions, answers):
            prompt = f"""Evaluate this answer.

Question: {question}
Answer: {answer}

Is the answer:
1. Correct and complete?
2. Well-reasoned?
3. Grounded in facts?

Output JSON:
{{
  "correct": true/false,
  "reasoning": "explanation",
  "score": 0.0-1.0
}}
"""

            response = self.judge.generate(prompt)
            try:
                evaluation = json.loads(response)
                evaluations.append(evaluation)
            except:
                evaluations.append({
                    'correct': False,
                    'reasoning': 'Parse error',
                    'score': 0.0
                })

        return evaluations

    def _propose_skills(
        self,
        failures: List[str],
        current_skills: List[SkillProposal],
        context: List[str]
    ) -> List[SkillProposal]:
        """Propose new skills based on failures."""
        failures_text = "\n".join(f"- {q}" for q in failures[:5])
        context_text = "\n\n".join(context[:3])

        prompt = f"""Propose skills to address these failed questions.

Failed Questions:
{failures_text}

Context:
{context_text}

Current Skills: {len(current_skills)}

Propose 1-3 new skills that would help answer these questions.

Output JSON array:
[
  {{
    "title": "Skill Title",
    "description": "What this skill does",
    "keywords": ["keyword1", "keyword2"],
    "body": "Detailed skill content...",
    "confidence": 0.8
  }}
]
"""

        response = self.proposer.generate(prompt)
        try:
            proposals_data = json.loads(response)
            proposals = []

            for p in proposals_data:
                skill_id = hashlib.md5(p['title'].encode()).hexdigest()[:12]
                proposals.append(SkillProposal(
                    id=f"ctx2skill_{skill_id}",
                    title=p['title'],
                    description=p['description'],
                    keywords=p['keywords'],
                    body=p['body'],
                    confidence=p.get('confidence', 0.8),
                    source_questions=failures[:3]
                ))

            return proposals
        except:
            return []

    def _generate_skill_file(self, proposal: SkillProposal) -> Path:
        """Generate SKILL.md file from proposal."""
        skill_content = f"""---
id: {proposal.id}
version: "1.0.0"
description: {proposal.description}
keywords: {json.dumps(proposal.keywords)}
applies_to: [agent, plan]
progressive: true
tier: on_demand
source: ctx2skill
confidence: {proposal.confidence}
---

# {proposal.title}

{proposal.body}

## Source Questions

This skill was discovered to address:
{chr(10).join(f"- {q}" for q in proposal.source_questions)}

## Usage

This skill activates when keywords match: {", ".join(proposal.keywords)}

---

**Generated by**: Ctx2Skill Adversarial Self-Play
**Confidence**: {proposal.confidence:.2f}
**Version**: 1.0.0
"""

        skill_file = self.skills_dir / f"{proposal.id}.md"
        with open(skill_file, 'w') as f:
            f.write(skill_content)

        print(f"Generated skill: {skill_file}")
        return skill_file

    def _cross_time_replay(
        self,
        skills: List[SkillProposal]
    ) -> List[SkillProposal]:
        """
        Cross-Time Replay: Select skill set that maximizes ρ_h · ρ_e.

        Args:
            skills: All skills from all iterations

        Returns:
            Best skill subset
        """
        if not self.hard_probe or not self.easy_probe:
            return skills

        # Evaluate each skill on hard and easy probes
        skill_scores = []

        for skill in skills:
            # Evaluate on hard probe
            hard_answers = self._answer_questions(self.hard_probe, [skill])
            hard_evals = self._evaluate_answers(self.hard_probe, hard_answers)
            rho_h = sum(e['correct'] for e in hard_evals) / len(hard_evals)

            # Evaluate on easy probe
            easy_answers = self._answer_questions(self.easy_probe, [skill])
            easy_evals = self._evaluate_answers(self.easy_probe, easy_answers)
            rho_e = sum(e['correct'] for e in easy_evals) / len(easy_evals)

            # Product score
            score = rho_h * rho_e

            skill_scores.append((skill, score))

        # Sort by score and keep top skills
        skill_scores.sort(key=lambda x: x[1], reverse=True)

        # Keep top 50% of skills
        keep_count = max(1, len(skills) // 2)
        best_skills = [s for s, _ in skill_scores[:keep_count]]

        print(f"Cross-Time Replay: Kept {len(best_skills)}/{len(skills)} skills")

        return best_skills


# Factory function
def run_ctx2skill(
    context_docs: List[str],
    llm_model: str = "deepseek-v4-pro",
    skills_dir: str = "~/.lyra/skills/ctx2skill",
    iterations: int = 5
) -> List[Path]:
    """
    Run Ctx2Skill pipeline on context documents.

    Args:
        context_docs: Context documents
        llm_model: LLM model to use
        skills_dir: Output directory for skills
        iterations: Number of iterations

    Returns:
        List of generated skill file paths
    """
    from lyra_core.llm import build_llm

    # Initialize LLMs (can use same model for all roles)
    llm = build_llm(llm_model)

    pipeline = Ctx2SkillPipeline(
        llm_challenger=llm,
        llm_reasoner=llm,
        llm_judge=llm,
        llm_proposer=llm,
        llm_generator=llm,
        skills_dir=Path(skills_dir).expanduser()
    )

    skill_files = pipeline.run(
        context_docs=context_docs,
        iterations=iterations
    )

    return skill_files


# Usage example
"""
from lyra_core.skills.ctx2skill import run_ctx2skill

# Load context documents
context_docs = [
    "Document 1 content...",
    "Document 2 content...",
    "Document 3 content..."
]

# Run Ctx2Skill
skill_files = run_ctx2skill(
    context_docs=context_docs,
    llm_model="deepseek-v4-pro",
    iterations=5
)

print(f"Generated {len(skill_files)} skills:")
for skill_file in skill_files:
    print(f"  - {skill_file}")
"""
