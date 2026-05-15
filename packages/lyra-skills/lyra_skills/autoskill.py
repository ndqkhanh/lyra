"""
AutoSkill: Lifelong Learning for Agent Skills

Implements dialogue-driven skill extraction with 4-axis Judge evaluation:
- Correctness
- Efficiency
- Generalizability
- Novelty

Based on research: docs/167 (autoskill-experience-driven-lifelong-learning.md)
Impact: Continuous skill library growth, +35-44pp cross-model transfer
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib
from datetime import datetime


@dataclass
class DialogueTurn:
    """Single turn in agent-environment dialogue."""
    turn_id: int
    user_input: str
    agent_action: str
    environment_feedback: str
    success: bool
    timestamp: datetime


@dataclass
class SkillCandidate:
    """Candidate skill extracted from dialogue."""
    id: str
    name: str
    description: str
    code: str
    source_dialogue: List[int]  # Turn IDs
    judge_scores: Dict[str, float]  # correctness, efficiency, generalizability, novelty
    overall_score: float


class FourAxisJudge:
    """
    4-axis Judge for skill evaluation.

    Evaluates skills on:
    - Correctness: Does it solve the task?
    - Efficiency: Is it optimal?
    - Generalizability: Does it transfer?
    - Novelty: Is it new?
    """

    def __init__(self, llm):
        """
        Initialize 4-axis Judge.

        Args:
            llm: LLM for evaluation
        """
        self.llm = llm

    def evaluate(
        self,
        skill_candidate: SkillCandidate,
        existing_skills: List[SkillCandidate]
    ) -> Dict[str, float]:
        """
        Evaluate skill on 4 axes.

        Args:
            skill_candidate: Skill to evaluate
            existing_skills: Existing skills in library

        Returns:
            Dictionary with scores for each axis
        """
        prompt = f"""Evaluate this skill on 4 axes (0.0-1.0 each):

Skill:
Name: {skill_candidate.name}
Description: {skill_candidate.description}
Code:
{skill_candidate.code}

Existing Skills: {len(existing_skills)}

Evaluate:
1. Correctness: Does it solve the intended task correctly?
2. Efficiency: Is the implementation optimal (time/space)?
3. Generalizability: Can it transfer to similar tasks?
4. Novelty: Is it different from existing skills?

Output JSON:
{{
  "correctness": 0.9,
  "efficiency": 0.8,
  "generalizability": 0.85,
  "novelty": 0.7,
  "reasoning": "Brief explanation for each score"
}}
"""

        try:
            response = self.llm.generate(prompt)
            scores = json.loads(response)

            # Compute overall score (weighted average)
            overall = (
                0.4 * scores['correctness'] +
                0.2 * scores['efficiency'] +
                0.3 * scores['generalizability'] +
                0.1 * scores['novelty']
            )

            scores['overall'] = overall
            return scores
        except Exception as e:
            print(f"Error evaluating skill: {e}")
            return {
                'correctness': 0.5,
                'efficiency': 0.5,
                'generalizability': 0.5,
                'novelty': 0.5,
                'overall': 0.5
            }


class AutoSkillPipeline:
    """
    AutoSkill: Lifelong learning pipeline.

    Pipeline:
    1. Dialogue Collection: Agent-environment interactions
    2. Skill Extraction: Extract reusable patterns
    3. 4-Axis Evaluation: Judge skill quality
    4. Library Update: Add high-quality skills
    """

    def __init__(
        self,
        llm_extractor,
        llm_judge,
        skills_dir: Path,
        acceptance_threshold: float = 0.7
    ):
        """
        Initialize AutoSkill pipeline.

        Args:
            llm_extractor: LLM for skill extraction
            llm_judge: LLM for 4-axis evaluation
            skills_dir: Directory to save skills
            acceptance_threshold: Minimum overall score to accept skill
        """
        self.extractor = llm_extractor
        self.judge = FourAxisJudge(llm_judge)
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        self.acceptance_threshold = acceptance_threshold
        self.skill_library: List[SkillCandidate] = []
        self.dialogue_history: List[DialogueTurn] = []

    def run(
        self,
        dialogues: List[List[DialogueTurn]],
        max_skills: int = 100
    ) -> List[Path]:
        """
        Run AutoSkill lifelong learning.

        Args:
            dialogues: List of dialogue sessions
            max_skills: Maximum skills to maintain

        Returns:
            List of generated skill file paths
        """
        skill_files = []

        for session_idx, dialogue in enumerate(dialogues):
            print(f"\n=== AutoSkill Session {session_idx + 1}/{len(dialogues)} ===")

            # Add to history
            self.dialogue_history.extend(dialogue)

            # Extract skill candidates
            candidates = self._extract_skills_from_dialogue(dialogue)

            # Evaluate with 4-axis Judge
            for candidate in candidates:
                scores = self.judge.evaluate(candidate, self.skill_library)
                candidate.judge_scores = scores
                candidate.overall_score = scores['overall']

                # Accept if above threshold
                if candidate.overall_score >= self.acceptance_threshold:
                    skill_file = self._materialize_skill(candidate)
                    skill_files.append(skill_file)
                    self.skill_library.append(candidate)

                    print(f"Accepted skill: {candidate.name} (score: {candidate.overall_score:.2f})")
                else:
                    print(f"Rejected skill: {candidate.name} (score: {candidate.overall_score:.2f})")

            # Prune library if too large
            if len(self.skill_library) > max_skills:
                self._prune_library(max_skills)

        return skill_files

    def _extract_skills_from_dialogue(
        self,
        dialogue: List[DialogueTurn]
    ) -> List[SkillCandidate]:
        """Extract skill candidates from dialogue."""
        # Format dialogue
        dialogue_text = "\n".join([
            f"Turn {turn.turn_id}:\n"
            f"  User: {turn.user_input}\n"
            f"  Agent: {turn.agent_action}\n"
            f"  Feedback: {turn.environment_feedback}\n"
            f"  Success: {turn.success}"
            for turn in dialogue
        ])

        prompt = f"""Extract reusable skills from this agent-environment dialogue.

Dialogue:
{dialogue_text}

Identify patterns that could be generalized into reusable skills.

Output JSON array:
[
  {{
    "name": "Skill Name",
    "description": "What this skill does",
    "code": "# Python implementation\\ndef skill():\\n    pass",
    "source_turns": [1, 2, 3]
  }}
]
"""

        try:
            response = self.extractor.generate(prompt)
            candidates_data = json.loads(response)

            candidates = []
            for data in candidates_data:
                skill_id = f"autoskill_{hashlib.md5(data['name'].encode()).hexdigest()[:12]}"

                candidate = SkillCandidate(
                    id=skill_id,
                    name=data['name'],
                    description=data['description'],
                    code=data['code'],
                    source_dialogue=data.get('source_turns', []),
                    judge_scores={},
                    overall_score=0.0
                )

                candidates.append(candidate)

            return candidates
        except Exception as e:
            print(f"Error extracting skills: {e}")
            return []

    def _materialize_skill(self, candidate: SkillCandidate) -> Path:
        """Materialize skill as SKILL.md file."""
        skill_content = f"""---
id: {candidate.id}
version: "1.0.0"
description: {candidate.description}
keywords: []
applies_to: [agent, execute]
progressive: true
tier: on_demand
source: autoskill
judge_scores:
  correctness: {candidate.judge_scores.get('correctness', 0.0):.2f}
  efficiency: {candidate.judge_scores.get('efficiency', 0.0):.2f}
  generalizability: {candidate.judge_scores.get('generalizability', 0.0):.2f}
  novelty: {candidate.judge_scores.get('novelty', 0.0):.2f}
  overall: {candidate.overall_score:.2f}
---

# {candidate.name}

{candidate.description}

## Implementation

```python
{candidate.code}
```

## Source Dialogue

Extracted from dialogue turns: {', '.join(map(str, candidate.source_dialogue))}

## Judge Evaluation

- **Correctness**: {candidate.judge_scores.get('correctness', 0.0):.2f}
- **Efficiency**: {candidate.judge_scores.get('efficiency', 0.0):.2f}
- **Generalizability**: {candidate.judge_scores.get('generalizability', 0.0):.2f}
- **Novelty**: {candidate.judge_scores.get('novelty', 0.0):.2f}
- **Overall**: {candidate.overall_score:.2f}

## Usage

This skill was learned through lifelong learning from agent-environment interactions.

---

**Generated by**: AutoSkill Lifelong Learning
**Overall Score**: {candidate.overall_score:.2f}
**Version**: 1.0.0
"""

        skill_file = self.skills_dir / f"{candidate.id}.md"
        with open(skill_file, 'w') as f:
            f.write(skill_content)

        print(f"Materialized skill: {skill_file}")
        return skill_file

    def _prune_library(self, max_skills: int) -> None:
        """Prune library to max_skills by removing lowest-scoring skills."""
        # Sort by overall score
        self.skill_library.sort(key=lambda s: s.overall_score, reverse=True)

        # Keep top max_skills
        pruned = self.skill_library[max_skills:]
        self.skill_library = self.skill_library[:max_skills]

        print(f"Pruned {len(pruned)} skills from library")

        # Remove pruned skill files
        for skill in pruned:
            skill_file = self.skills_dir / f"{skill.id}.md"
            if skill_file.exists():
                skill_file.unlink()

    def get_library_stats(self) -> Dict[str, Any]:
        """Get statistics about skill library."""
        if not self.skill_library:
            return {
                'total_skills': 0,
                'avg_score': 0.0,
                'score_distribution': {}
            }

        scores = [s.overall_score for s in self.skill_library]

        return {
            'total_skills': len(self.skill_library),
            'avg_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'score_distribution': {
                'high (>0.8)': sum(1 for s in scores if s > 0.8),
                'medium (0.6-0.8)': sum(1 for s in scores if 0.6 <= s <= 0.8),
                'low (<0.6)': sum(1 for s in scores if s < 0.6)
            }
        }


# Usage example
"""
from lyra_skills.autoskill import AutoSkillPipeline, DialogueTurn
from lyra_core.llm import build_llm
from datetime import datetime

# Initialize LLMs
llm = build_llm("deepseek-v4-pro")

# Create pipeline
pipeline = AutoSkillPipeline(
    llm_extractor=llm,
    llm_judge=llm,
    skills_dir=Path("~/.lyra/skills/autoskill").expanduser(),
    acceptance_threshold=0.7
)

# Create dialogue sessions
dialogues = [
    [
        DialogueTurn(
            turn_id=1,
            user_input="Parse this JSON file",
            agent_action="import json; data = json.load(f)",
            environment_feedback="Success",
            success=True,
            timestamp=datetime.now()
        ),
        # ... more turns
    ]
]

# Run lifelong learning
skill_files = pipeline.run(dialogues, max_skills=100)

# Get stats
stats = pipeline.get_library_stats()
print(f"Library: {stats['total_skills']} skills, avg score: {stats['avg_score']:.2f}")
"""
