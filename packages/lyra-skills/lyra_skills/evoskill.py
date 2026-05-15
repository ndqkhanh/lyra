"""
EvoSkill: Failure-Driven Skill Discovery for Coding Agents

Implements evolutionary skill discovery through:
- Pareto frontier search (k=3 programs)
- Failure harvesting from task execution
- Executor/Proposer/Skill-Builder pipeline

Based on research: docs/168 (evoskill-coding-agent-skill-discovery.md)
Impact: +7.3pp OfficeQA, +12.1pp SealQA, +5.3pp zero-shot transfer
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib


@dataclass
class AgentProgram:
    """Agent program on Pareto frontier."""
    id: str
    code: str
    skills: List[str]  # Skill IDs used by this program
    metrics: Dict[str, float]  # pass_rate, avg_steps, etc.
    generation: int


@dataclass
class FailureCase:
    """Failed task execution."""
    task_id: str
    task_description: str
    agent_program_id: str
    error_message: str
    execution_trace: str
    missing_capability: str


@dataclass
class SkillProposal:
    """Proposed skill from failure analysis."""
    id: str
    name: str
    description: str
    code: str
    keywords: List[str]
    addresses_failures: List[str]  # Task IDs
    confidence: float


class ParetoFrontier:
    """
    Maintains k=3 programs on Pareto frontier.

    Evicts dominated programs, captures complementary failure modes.
    """

    def __init__(self, k: int = 3):
        """
        Initialize Pareto frontier.

        Args:
            k: Number of programs to maintain (default: 3)
        """
        self.k = k
        self.programs: List[AgentProgram] = []

    def add(self, program: AgentProgram) -> bool:
        """
        Add program to frontier, evict dominated.

        Args:
            program: AgentProgram to add

        Returns:
            True if program was added
        """
        # Check if dominated by existing programs
        for existing in self.programs:
            if self._dominates(existing.metrics, program.metrics):
                return False

        # Remove programs dominated by new program
        self.programs = [
            p for p in self.programs
            if not self._dominates(program.metrics, p.metrics)
        ]

        # Add new program
        self.programs.append(program)

        # If over capacity, evict by crowding distance
        if len(self.programs) > self.k:
            self.programs = self._crowding_distance_selection(self.programs, self.k)

        return True

    def _dominates(self, m1: Dict[str, float], m2: Dict[str, float]) -> bool:
        """
        Check if m1 dominates m2.

        Args:
            m1: Metrics 1
            m2: Metrics 2

        Returns:
            True if m1 dominates m2
        """
        better_in_all = all(m1.get(k, 0) >= m2.get(k, 0) for k in m1.keys())
        better_in_some = any(m1.get(k, 0) > m2.get(k, 0) for k in m1.keys())
        return better_in_all and better_in_some

    def _crowding_distance_selection(
        self,
        programs: List[AgentProgram],
        k: int
    ) -> List[AgentProgram]:
        """
        Select k programs with highest crowding distance.

        Args:
            programs: List of programs
            k: Number to select

        Returns:
            Selected programs
        """
        if len(programs) <= k:
            return programs

        # Compute crowding distance for each program
        distances = []
        for i, program in enumerate(programs):
            distance = self._compute_crowding_distance(i, programs)
            distances.append((program, distance))

        # Sort by distance, keep top k
        distances.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in distances[:k]]

    def _compute_crowding_distance(
        self,
        idx: int,
        programs: List[AgentProgram]
    ) -> float:
        """Compute crowding distance for program at idx."""
        if len(programs) <= 2:
            return float('inf')

        distance = 0.0
        metrics_keys = list(programs[0].metrics.keys())

        for key in metrics_keys:
            # Sort by this metric
            sorted_programs = sorted(programs, key=lambda p: p.metrics.get(key, 0))
            sorted_idx = sorted_programs.index(programs[idx])

            # Boundary points get infinite distance
            if sorted_idx == 0 or sorted_idx == len(programs) - 1:
                return float('inf')

            # Compute distance
            metric_range = (
                sorted_programs[-1].metrics.get(key, 0) -
                sorted_programs[0].metrics.get(key, 0)
            )

            if metric_range > 0:
                distance += (
                    sorted_programs[sorted_idx + 1].metrics.get(key, 0) -
                    sorted_programs[sorted_idx - 1].metrics.get(key, 0)
                ) / metric_range

        return distance

    def get_programs(self) -> List[AgentProgram]:
        """Get all programs on frontier."""
        return self.programs


class EvoSkillPipeline:
    """
    EvoSkill: Evolutionary skill discovery pipeline.

    Pipeline:
    1. Executor: Run agent programs on tasks, collect failures
    2. Proposer: Analyze failures, propose skills
    3. Skill-Builder: Materialize skills as code
    4. Evolution: Update Pareto frontier
    """

    def __init__(
        self,
        llm_executor,
        llm_proposer,
        llm_builder,
        skills_dir: Path,
        k: int = 3
    ):
        """
        Initialize EvoSkill pipeline.

        Args:
            llm_executor: LLM for executing tasks
            llm_proposer: LLM for proposing skills
            llm_builder: LLM for building skills
            skills_dir: Directory to save skills
            k: Pareto frontier size
        """
        self.executor = llm_executor
        self.proposer = llm_proposer
        self.builder = llm_builder
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        self.frontier = ParetoFrontier(k=k)
        self.all_skills: Dict[str, SkillProposal] = {}
        self.failure_history: List[FailureCase] = []

    def run(
        self,
        tasks: List[Dict[str, Any]],
        generations: int = 10
    ) -> List[Path]:
        """
        Run EvoSkill evolutionary loop.

        Args:
            tasks: List of tasks to solve
            generations: Number of evolutionary generations

        Returns:
            List of generated skill file paths
        """
        skill_files = []

        # Initialize with base program (no skills)
        base_program = AgentProgram(
            id="gen0_prog0",
            code="# Base agent with no skills",
            skills=[],
            metrics={'pass_rate': 0.0, 'avg_steps': 0.0},
            generation=0
        )
        self.frontier.add(base_program)

        for gen in range(generations):
            print(f"\n=== EvoSkill Generation {gen + 1}/{generations} ===")

            # Step 1: Execute programs on tasks, collect failures
            failures = self._execute_and_collect_failures(tasks)

            if not failures:
                print("No failures, evolution complete!")
                break

            # Step 2: Propose skills from failures
            proposals = self._propose_skills_from_failures(failures)

            # Step 3: Build skills
            for proposal in proposals:
                skill_file = self._build_skill(proposal)
                skill_files.append(skill_file)
                self.all_skills[proposal.id] = proposal

            # Step 4: Create new programs with skills
            new_programs = self._create_programs_with_skills(gen + 1)

            # Step 5: Evaluate and update frontier
            for program in new_programs:
                metrics = self._evaluate_program(program, tasks)
                program.metrics = metrics
                self.frontier.add(program)

            print(f"Frontier size: {len(self.frontier.programs)}")
            print(f"Total skills: {len(self.all_skills)}")

        return skill_files

    def _execute_and_collect_failures(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[FailureCase]:
        """Execute frontier programs on tasks, collect failures."""
        failures = []

        for program in self.frontier.get_programs():
            for task in tasks[:10]:  # Limit to 10 tasks per program
                # Execute task with program
                result = self._execute_task(program, task)

                if not result['success']:
                    failure = FailureCase(
                        task_id=task['id'],
                        task_description=task['description'],
                        agent_program_id=program.id,
                        error_message=result['error'],
                        execution_trace=result['trace'],
                        missing_capability=result.get('missing_capability', 'unknown')
                    )
                    failures.append(failure)
                    self.failure_history.append(failure)

        return failures

    def _execute_task(
        self,
        program: AgentProgram,
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a task with an agent program."""
        # Load skills
        skills_text = "\n\n".join([
            self.all_skills[skill_id].code
            for skill_id in program.skills
            if skill_id in self.all_skills
        ])

        prompt = f"""Execute this task using the provided skills.

Skills:
{skills_text}

Task: {task['description']}

Execute and return result."""

        try:
            result = self.executor.generate(prompt)
            # Simple success check (in production, use actual validation)
            success = "error" not in result.lower()

            return {
                'success': success,
                'result': result,
                'error': '' if success else result,
                'trace': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'trace': str(e),
                'missing_capability': 'execution_error'
            }

    def _propose_skills_from_failures(
        self,
        failures: List[FailureCase]
    ) -> List[SkillProposal]:
        """Propose skills to address failures."""
        # Group failures by missing capability
        capability_groups: Dict[str, List[FailureCase]] = {}
        for failure in failures:
            cap = failure.missing_capability
            if cap not in capability_groups:
                capability_groups[cap] = []
            capability_groups[cap].append(failure)

        proposals = []

        for capability, group_failures in capability_groups.items():
            # Analyze failures
            failures_text = "\n".join([
                f"- Task: {f.task_description}\n  Error: {f.error_message}"
                for f in group_failures[:5]
            ])

            prompt = f"""Propose a skill to address these failures.

Missing Capability: {capability}

Failures:
{failures_text}

Propose a skill that would help solve these tasks.

Output JSON:
{{
  "name": "Skill Name",
  "description": "What this skill does",
  "code": "# Python code for skill\\ndef skill_function():\\n    pass",
  "keywords": ["keyword1", "keyword2"],
  "confidence": 0.8
}}
"""

            try:
                response = self.proposer.generate(prompt)
                proposal_data = json.loads(response)

                skill_id = f"evoskill_{hashlib.md5(proposal_data['name'].encode()).hexdigest()[:12]}"

                proposal = SkillProposal(
                    id=skill_id,
                    name=proposal_data['name'],
                    description=proposal_data['description'],
                    code=proposal_data['code'],
                    keywords=proposal_data['keywords'],
                    addresses_failures=[f.task_id for f in group_failures],
                    confidence=proposal_data.get('confidence', 0.8)
                )

                proposals.append(proposal)
            except Exception as e:
                print(f"Error proposing skill: {e}")
                continue

        return proposals

    def _build_skill(self, proposal: SkillProposal) -> Path:
        """Build SKILL.md file from proposal."""
        skill_content = f"""---
id: {proposal.id}
version: "1.0.0"
description: {proposal.description}
keywords: {json.dumps(proposal.keywords)}
applies_to: [agent, execute]
progressive: true
tier: on_demand
source: evoskill
confidence: {proposal.confidence}
---

# {proposal.name}

{proposal.description}

## Implementation

```python
{proposal.code}
```

## Addresses Failures

This skill was discovered to address {len(proposal.addresses_failures)} task failures.

## Usage

This skill activates when keywords match: {", ".join(proposal.keywords)}

---

**Generated by**: EvoSkill Failure-Driven Discovery
**Confidence**: {proposal.confidence:.2f}
**Version**: 1.0.0
"""

        skill_file = self.skills_dir / f"{proposal.id}.md"
        with open(skill_file, 'w') as f:
            f.write(skill_content)

        print(f"Built skill: {skill_file}")
        return skill_file

    def _create_programs_with_skills(self, generation: int) -> List[AgentProgram]:
        """Create new programs by combining skills."""
        new_programs = []

        # Round-robin parent selection from frontier
        for i, parent in enumerate(self.frontier.get_programs()):
            # Add one new skill to parent
            available_skills = [
                s_id for s_id in self.all_skills.keys()
                if s_id not in parent.skills
            ]

            if available_skills:
                new_skill = available_skills[0]  # Take first available
                new_program = AgentProgram(
                    id=f"gen{generation}_prog{i}",
                    code=f"# Program with skills: {parent.skills + [new_skill]}",
                    skills=parent.skills + [new_skill],
                    metrics={},
                    generation=generation
                )
                new_programs.append(new_program)

        return new_programs

    def _evaluate_program(
        self,
        program: AgentProgram,
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Evaluate program on tasks."""
        successes = 0
        total_steps = 0

        for task in tasks[:20]:  # Evaluate on 20 tasks
            result = self._execute_task(program, task)
            if result['success']:
                successes += 1
            total_steps += len(result['trace'].split('\n'))

        return {
            'pass_rate': successes / len(tasks[:20]),
            'avg_steps': total_steps / len(tasks[:20])
        }


# Usage example
"""
from lyra_skills.evoskill import EvoSkillPipeline
from lyra_core.llm import build_llm

# Initialize LLMs
llm = build_llm("deepseek-v4-pro")

# Create pipeline
pipeline = EvoSkillPipeline(
    llm_executor=llm,
    llm_proposer=llm,
    llm_builder=llm,
    skills_dir=Path("~/.lyra/skills/evoskill").expanduser(),
    k=3
)

# Define tasks
tasks = [
    {"id": "task1", "description": "Parse JSON file"},
    {"id": "task2", "description": "Filter data by date"},
    # ... more tasks
]

# Run evolution
skill_files = pipeline.run(tasks, generations=10)

print(f"Generated {len(skill_files)} skills")
"""
