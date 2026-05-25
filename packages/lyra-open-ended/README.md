# lyra-open-ended

Open-ended learning engine for self-directed AGI — self-proposed goals, self-evaluation, and auto-curriculum generation.

## Overview

The `lyra-open-ended` package provides an `OpenEndedLearner` that continuously proposes learning goals,
self-evaluates outcomes, and dynamically generates curricula. It uses heuristic-based goal proposal to
fill domain coverage gaps, respect difficulty progression, and follow prerequisite chains.

## Components

- **OpenEndedLearner**: Core engine that manages goals, outcomes, and curricula
- **LearningGoal**: A single learning objective with difficulty, domain, and prerequisite metadata
- **GoalOutcome**: Structured self-evaluation result for a completed goal
- **CurriculumStep**: A phase-aligned set of learning goals
- **LearnerProfile**: Snapshot of learner state including capabilities and progress

## Usage

```python
from lyra_open_ended import OpenEndedLearner

learner = OpenEndedLearner("agent-1")
goal = learner.propose_goal()
outcome = learner.self_evaluate(goal, "Successfully completed the goal. Learned key concepts.")
learner.record_outcome(goal, outcome)
curriculum = learner.update_curriculum()
```
