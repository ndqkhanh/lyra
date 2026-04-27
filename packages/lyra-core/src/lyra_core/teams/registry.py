"""Team registry + plan executor — MetaGPT-inspired role pipeline.

The registry is in-memory; the executor is a 30-line for-loop with a
deterministic handoff format. The complexity lives in the role
*data*, not the runtime — that's the key MetaGPT lesson.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class TeamRole:
    """One role in a team — a persona + toolset + SOP."""

    name: str
    title: str
    description: str
    system_prompt: str
    toolset: str = "default"
    sop: tuple[str, ...] = ()
    output_contract: str = "free-form prose"

    def __post_init__(self) -> None:
        if not _NAME_RE.match(self.name):
            raise ValueError(
                f"role name must match {_NAME_RE.pattern!r}, "
                f"got {self.name!r}"
            )
        if not self.title.strip():
            raise ValueError("role title cannot be empty")
        if not self.system_prompt.strip():
            raise ValueError("role system_prompt cannot be empty")


@dataclass(frozen=True)
class TeamStep:
    """One step in a :class:`TeamPlan` — which role acts on what task."""

    role: str
    task: str | None = None  # None ⇒ inherit from previous step's output

    def resolve(self, fallback: str) -> str:
        return self.task if self.task is not None else fallback


@dataclass(frozen=True)
class TeamPlan:
    """An ordered list of :class:`TeamStep` to execute end-to-end."""

    steps: tuple[TeamStep, ...]
    name: str = "team-plan"

    def role_names(self) -> tuple[str, ...]:
        return tuple(s.role for s in self.steps)


@dataclass(frozen=True)
class TeamStepResult:
    """The agent's response for one step of a plan."""

    role: str
    task_in: str
    output: str


@dataclass(frozen=True)
class TeamRunReport:
    """Aggregated result of a :class:`TeamPlan` execution."""

    plan: TeamPlan
    initial_task: str
    steps: tuple[TeamStepResult, ...]

    @property
    def final_output(self) -> str:
        return self.steps[-1].output if self.steps else ""

    def to_dict(self) -> dict[str, object]:
        return {
            "plan": self.plan.name,
            "initial_task": self.initial_task,
            "steps": [
                {
                    "role": s.role,
                    "task_in": s.task_in,
                    "output": s.output,
                }
                for s in self.steps
            ],
            "final_output": self.final_output,
        }


# --------------------------------------------------------------------- #
# Built-in roles                                                        #
# --------------------------------------------------------------------- #

_PM = TeamRole(
    name="pm",
    title="Product Manager",
    description="Clarifies intent, writes user stories, and accepts the brief.",
    system_prompt=(
        "You are the Product Manager on a small software team. Your job "
        "is to take a one-line user request and produce a clear, "
        "actionable brief: who the user is, what they want, and what "
        "'done' looks like. You do not write code or system design; you "
        "write the brief that the rest of the team will work from."
    ),
    toolset="research",
    sop=(
        "Restate the user request in one sentence.",
        "Identify the user persona and primary outcome.",
        "List 2-5 acceptance criteria as bullet points.",
        "Flag ambiguities the team must resolve before designing.",
    ),
    output_contract=(
        "Markdown brief with sections: Restated request, User, "
        "Acceptance criteria, Open questions."
    ),
)

_ARCHITECT = TeamRole(
    name="architect",
    title="System Architect",
    description="Decomposes the brief into components, data flow, and APIs.",
    system_prompt=(
        "You are the System Architect. Take the PM brief and produce a "
        "minimal, opinionated architecture: what components exist, "
        "what data they exchange, and which interfaces are public. "
        "Prefer the smallest design that satisfies the brief; you are "
        "not optimising for hypothetical future scale."
    ),
    toolset="research",
    sop=(
        "List the components needed and their responsibilities.",
        "Specify the data model in 5-15 lines (no full schemas).",
        "Define the public interfaces between components.",
        "Call out the riskiest design decisions for the engineer.",
    ),
    output_contract=(
        "Markdown design with sections: Components, Data model, "
        "Interfaces, Risks."
    ),
)

_ENGINEER = TeamRole(
    name="engineer",
    title="Engineer",
    description="Implements the smallest reversible diff that satisfies the design.",
    system_prompt=(
        "You are the Engineer. Take the architect's design and produce "
        "the smallest reversible implementation that satisfies it. "
        "Prefer a few small files over one large one; prefer adding to "
        "existing modules over creating new ones. Do not write tests "
        "in this step — that's QA's job."
    ),
    toolset="coding",
    sop=(
        "Read the design; ask only blocking questions.",
        "Plan the file-level diff before touching code.",
        "Implement the smallest diff that compiles and runs.",
        "Hand off the diff and a one-paragraph summary to QA.",
    ),
    output_contract=(
        "Markdown handoff with sections: Diff summary, Files touched, "
        "Notes for QA."
    ),
)

_REVIEWER = TeamRole(
    name="reviewer",
    title="Reviewer",
    description="Pass the engineer's diff through a rubric review.",
    system_prompt=(
        "You are the Reviewer. Take the engineer's handoff and pass it "
        "through a rubric covering: correctness, simplicity, test "
        "coverage hooks, and reversibility. Be specific — flag exact "
        "lines or files when raising concerns. You may approve, "
        "approve-with-nits, or block."
    ),
    toolset="safe",
    sop=(
        "Apply the rubric: correctness, simplicity, tests, reversibility.",
        "For each rubric dimension, give a one-line verdict.",
        "List specific concerns with file:line precision when possible.",
        "End with one of: APPROVE, APPROVE-WITH-NITS, BLOCK.",
    ),
    output_contract=(
        "Markdown review with sections: Rubric, Concerns, Verdict."
    ),
)

_QA = TeamRole(
    name="qa",
    title="QA / Tester",
    description="Writes or runs the verification harness for the engineer's diff.",
    system_prompt=(
        "You are QA. Take the engineer's diff (and the reviewer's "
        "verdict) and produce the verification artefact: either a new "
        "test file, an existing-test update, or — when no automated "
        "test is feasible — a manual verification checklist with "
        "concrete steps."
    ),
    toolset="coding",
    sop=(
        "Read the diff and the architect's interfaces section.",
        "Write or update tests that pin the public behaviour.",
        "If automation is impossible, produce a manual checklist.",
        "Report pass/fail (or 'manual') with a short rationale.",
    ),
    output_contract=(
        "Markdown QA report with sections: Tests added/updated, "
        "Result, Notes."
    ),
)

_BUILTIN_ROLES: tuple[TeamRole, ...] = (_PM, _ARCHITECT, _ENGINEER, _REVIEWER, _QA)


class TeamRegistry:
    """In-memory registry of named roles."""

    def __init__(self, *, builtins: bool = True) -> None:
        self._roles: dict[str, TeamRole] = {}
        if builtins:
            for r in _BUILTIN_ROLES:
                self._roles[r.name] = r

    def names(self) -> list[str]:
        return sorted(self._roles.keys())

    def get(self, name: str) -> TeamRole | None:
        return self._roles.get(name)

    def register(self, role: TeamRole) -> None:
        if role.name in self._roles:
            raise ValueError(f"role {role.name!r} already registered")
        self._roles[role.name] = role

    def remove(self, name: str) -> None:
        self._roles.pop(name, None)

    def replace(self, role: TeamRole) -> None:
        """Register a role, overwriting any existing entry of the same name."""
        self._roles[role.name] = role


_DEFAULT_SINGLETON: TeamRegistry | None = None


def default_registry() -> TeamRegistry:
    """Return a process-wide singleton populated with built-ins."""
    global _DEFAULT_SINGLETON
    if _DEFAULT_SINGLETON is None:
        _DEFAULT_SINGLETON = TeamRegistry(builtins=True)
    return _DEFAULT_SINGLETON


def default_software_plan() -> TeamPlan:
    """The MetaGPT-style five-step pipeline: PM → Architect → Engineer → Reviewer → QA."""
    return TeamPlan(
        name="software-company",
        steps=(
            TeamStep(role="pm"),
            TeamStep(role="architect"),
            TeamStep(role="engineer"),
            TeamStep(role="reviewer"),
            TeamStep(role="qa"),
        ),
    )


# --------------------------------------------------------------------- #
# Plan executor                                                         #
# --------------------------------------------------------------------- #

AgentCallable = Callable[[TeamRole, str], str]
"""``(role, task_text) -> response_text``.

The orchestrator threads the previous step's output as ``task_text``
for the next step. Production wires this to ``InteractiveSession``;
tests wire it to a deterministic stub.
"""


def run_team_plan(
    plan: TeamPlan,
    initial_task: str,
    *,
    agent: AgentCallable,
    registry: TeamRegistry | None = None,
) -> TeamRunReport:
    """Execute ``plan`` with the given ``agent`` callable.

    Args:
        plan: ordered :class:`TeamStep` list. Empty plans return a
            report with an empty ``steps`` tuple and the original
            ``initial_task`` as ``final_output``.
        initial_task: prompt fed to the first step. Subsequent steps
            receive the previous step's output unless their
            :class:`TeamStep` overrides ``task``.
        agent: ``(role, task_text) -> response_text`` callable.
        registry: optional registry; defaults to :func:`default_registry`.

    Raises:
        KeyError: when a plan references an unknown role.
    """
    reg = registry or default_registry()
    results: list[TeamStepResult] = []
    handoff_text = initial_task
    for step in plan.steps:
        role = reg.get(step.role)
        if role is None:
            raise KeyError(f"unknown role in plan: {step.role!r}")
        task_in = step.resolve(handoff_text)
        out = agent(role, task_in)
        results.append(
            TeamStepResult(role=role.name, task_in=task_in, output=out)
        )
        handoff_text = out
    return TeamRunReport(
        plan=plan,
        initial_task=initial_task,
        steps=tuple(results),
    )


__all__ = [
    "AgentCallable",
    "TeamPlan",
    "TeamRegistry",
    "TeamRole",
    "TeamRunReport",
    "TeamStep",
    "TeamStepResult",
    "default_registry",
    "default_software_plan",
    "run_team_plan",
]
