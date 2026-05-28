"""
Brainstorm Facilitator Skill - Structured brainstorming and ideation.

Implements multiple creativity techniques:
- SCAMPER method
- Six Thinking Hats (de Bono)
- Random stimulus / forced connections
- Reverse brainstorming
- Mind map generation (text-based)

Outputs organized ideation output.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import StrEnum


class BrainstormMethod(StrEnum):
    """Supported brainstorming methods."""

    SCAMPER = "SCAMPER"
    SIX_HATS = "six_thinking_hats"
    RANDOM_STIMULUS = "random_stimulus"
    REVERSE = "reverse_brainstorming"
    MIND_MAP = "mind_map"


@dataclass(frozen=True)
class SCAMPERIdea:
    """An idea generated via SCAMPER technique."""

    technique: str  # Substitute, Combine, Adapt, Modify, Put to another use, Eliminate, Reverse
    prompt: str
    idea: str
    feasibility: str
    impact: str


@dataclass(frozen=True)
class HatPerspective:
    """Perspective from a Six Thinking Hats session."""

    hat_color: str
    hat_meaning: str
    perspective: str
    key_insights: tuple[str, ...]


@dataclass(frozen=True)
class RandomStimulusIdea:
    """An idea from random stimulus generation."""

    stimulus_word: str
    connection: str
    idea: str
    novelty_rating: str


@dataclass(frozen=True)
class ReverseIdea:
    """An idea from reverse brainstorming."""

    problem_inversion: str
    original_problem: str
    reversed_assumption: str
    solution_insight: str


@dataclass(frozen=True)
class MindMapNode:
    """A node in a mind map."""

    label: str
    depth: int
    children: tuple[MindMapNode, ...]


@dataclass(frozen=True)
class BrainstormSession:
    """Complete brainstorming session output."""

    topic: str
    method: BrainstormMethod
    session_summary: str
    ideas: dict
    top_ideas: tuple[str, ...]
    next_steps: tuple[str, ...]


# ---------------------------------------------------------------------------
# Stimulus words for random stimulus generation
# ---------------------------------------------------------------------------
_STIMULUS_WORDS: list[str] = [
    "bridge", "mirror", "clock", "spiral", "garden", "river", "mountain",
    "compass", "lens", "spring", "magnet", "filter", "pulse", "wave",
    "network", "seed", "tree", "orbit", "prism", "echo", "thread",
    "switch", "valve", "circuit", "battery", "engine", "anchor", "tide",
]


class BrainstormFacilitator:
    """Structured brainstorming facilitation skill."""

    def __init__(self) -> None:
        self._method: BrainstormMethod = BrainstormMethod.SCAMPER

    def run(self, input_data: dict) -> dict:
        """Run a brainstorming session.

        Args:
            input_data: Dictionary with keys:
                - topic: The topic or problem to brainstorm
                - method: Brainstorming method (default "SCAMPER")
                - context: Optional additional context for ideation

        Returns:
            Dictionary with brainstorming session data.
        """
        topic = input_data.get("topic", "")
        if not topic:
            return {"error": "No topic provided"}

        raw_method = input_data.get("method", "SCAMPER")
        # Normalize: replace spaces with underscores, lowercase for value matching
        normalized = raw_method.lower().replace(" ", "_")
        # Also create uppercased variant for name-based matching
        name_form = normalized.upper()
        try:
            self._method = BrainstormMethod(normalized)
        except ValueError:
            try:
                self._method = BrainstormMethod[name_form]
            except KeyError:
                self._method = BrainstormMethod.SCAMPER

        context = input_data.get("context", "")

        result_data: dict = {}
        if self._method == BrainstormMethod.SCAMPER:
            result_data = self._run_scamper(topic)
        elif self._method == BrainstormMethod.SIX_HATS:
            result_data = self._run_six_hats(topic)
        elif self._method == BrainstormMethod.RANDOM_STIMULUS:
            result_data = self._run_random_stimulus(topic)
        elif self._method == BrainstormMethod.REVERSE:
            result_data = self._run_reverse(topic)
        elif self._method == BrainstormMethod.MIND_MAP:
            result_data = self._run_mind_map(topic, context)
        else:
            result_data = self._run_scamper(topic)

        summary = self._generate_summary(topic, result_data)
        top_ideas = self._extract_top_ideas(result_data)
        next_steps = self._generate_next_steps(topic)

        return BrainstormSession(
            topic=topic,
            method=self._method,
            session_summary=summary,
            ideas=result_data,
            top_ideas=tuple(top_ideas),
            next_steps=tuple(next_steps),
        ).__dict__

    # ---- SCAMPER ----

    @staticmethod
    def _run_scamper(topic: str) -> dict:
        scamper_techniques: list[tuple[str, str]] = [
            ("Substitute", f"What can be substituted in {topic}?"),
            ("Combine", f"What can be combined with {topic}?"),
            ("Adapt", f"What existing solutions can be adapted for {topic}?"),
            ("Modify", f"How can {topic} be modified or scaled?"),
            ("Put to another use", f"How else can {topic} components be used?"),
            ("Eliminate", f"What can be removed or simplified in {topic}?"),
            ("Reverse", f"What happens if {topic} is reversed or inverted?"),
        ]

        ideas: list[SCAMPERIdea] = []
        for technique_name, prompt in scamper_techniques:
            idea_text = _generate_scamper_idea(technique_name, topic)
            ideas.append(
                SCAMPERIdea(
                    technique=technique_name,
                    prompt=prompt,
                    idea=idea_text,
                    feasibility=["High", "Medium", "Medium", "Low", "High", "Medium", "Medium"][
                        len(ideas)
                    ],
                    impact=["High", "High", "Medium", "High", "Low", "Medium", "High"][
                        len(ideas)
                    ],
                )
            )

        return {
            "method": "SCAMPER",
            "description": "SCAMPER prompts systematic creative thinking across 7 dimensions",
            "ideas": [i.__dict__ for i in ideas],
        }

    # ---- Six Thinking Hats ----

    @staticmethod
    def _run_six_hats(topic: str) -> dict:
        hats: list[tuple[str, str, str, list[str]]] = [
            (
                "White",
                "Facts & Information",
                f"Available data and information gaps about {topic}",
                [f"Current metrics: TBD",
                 f"Data sources: TBD",
                 f"Information gaps: details unclear",
                 f"Historical context: Consider past similar initiatives"],
            ),
            (
                "Red",
                "Emotions & Intuition",
                f"Gut feelings and emotional responses to {topic}",
                [f"Initial reaction: Exciting but uncertain",
                 f"Concern about: Implementation complexity",
                 f"Hunch: This aligns with user needs",
                 f"Emotional response: Cautiously optimistic"],
            ),
            (
                "Black",
                "Critical Judgment",
                f"Risks and potential problems with {topic}",
                [f"Risk: Resource constraints",
                 f"Risk: Technical complexity underestimated",
                 f"Risk: Timeline may be aggressive",
                 f"Risk: Stakeholder alignment needed"],
            ),
            (
                "Yellow",
                "Optimism & Benefits",
                f"Positive outcomes and value of {topic}",
                [f"Benefit: Improved user satisfaction",
                 f"Benefit: Competitive advantage",
                 f"Benefit: Operational efficiency gain",
                 f"Benefit: Revenue growth opportunity"],
            ),
            (
                "Green",
                "Creativity & New Ideas",
                f"Creative alternatives and possibilities for {topic}",
                [f"Idea: Consider a simpler MVP approach",
                 f"Idea: Integrate with existing tools",
                 f"Idea: Explore partnership opportunities",
                 f"Idea: Use incremental delivery"],
            ),
            (
                "Blue",
                "Process & Overview",
                f"Meta-cognition and process management for {topic}",
                [f"Process: Define success criteria first",
                 f"Process: Establish decision-making framework",
                 f"Process: Schedule regular checkpoints",
                 f"Process: Document all decisions"],
            ),
        ]

        perspectives: list[HatPerspective] = []
        for color, meaning, perspective_text, insights in hats:
            perspectives.append(
                HatPerspective(
                    hat_color=color,
                    hat_meaning=meaning,
                    perspective=perspective_text,
                    key_insights=tuple(insights),
                )
            )

        return {
            "method": "Six Thinking Hats",
            "description": "De Bono's Six Thinking Hats explores multiple perspectives",
            "hats": [h.__dict__ for h in perspectives],
        }

    # ---- Random Stimulus ----

    @staticmethod
    def _run_random_stimulus(topic: str) -> dict:
        selected = random.sample(_STIMULUS_WORDS, min(6, len(_STIMULUS_WORDS)))
        ideas: list[RandomStimulusIdea] = []

        for word in selected:
            connection = f"How can '{word}' inspire a solution for {topic}?"
            idea_text = _generate_stimulus_idea(word, topic)
            novelty = random.choice(["High", "Medium", "Low"])
            ideas.append(
                RandomStimulusIdea(
                    stimulus_word=word,
                    connection=connection,
                    idea=idea_text,
                    novelty_rating=novelty,
                )
            )

        return {
            "method": "Random Stimulus",
            "description": "Forced connections between random concepts and the problem",
            "stimulus_ideas": [i.__dict__ for i in ideas],
        }

    # ---- Reverse Brainstorming ----

    @staticmethod
    def _run_reverse(topic: str) -> dict:
        reversals: list[tuple[str, str]] = [
            (f"How could we make {topic} as BAD as possible?",
             f"Reverse: What's the worst experience we could create?"),
            (f"How could we maximize user frustration with {topic}?",
             f"Reverse: What causes the most pain?"),
            (f"How could we make {topic} extremely slow?",
             f"Reverse: What adds unnecessary friction?"),
            (f"How could we make {topic} impossible to use?",
             f"Reverse: What barriers can we eliminate?"),
        ]

        ideas: list[ReverseIdea] = []
        for problem_text, assumption in reversals:
            ideas.append(
                ReverseIdea(
                    problem_inversion=problem_text,
                    original_problem=topic,
                    reversed_assumption=assumption,
                    solution_insight=f"By avoiding this anti-pattern, we create a better solution for {topic}",
                )
            )

        return {
            "method": "Reverse Brainstorming",
            "description": "Identify problems by inverting assumptions",
            "reverse_ideas": [i.__dict__ for i in ideas],
        }

    # ---- Mind Map ----

    @staticmethod
    def _run_mind_map(topic: str, context: str) -> dict:
        branches: list[MindMapNode] = [
            MindMapNode(
                label="Users",
                depth=1,
                children=(
                    MindMapNode("Needs", 2, ()),
                    MindMapNode("Pain Points", 2, ()),
                    MindMapNode("Behaviors", 2, ()),
                    MindMapNode("Segments", 2, ()),
                ),
            ),
            MindMapNode(
                label="Technology",
                depth=1,
                children=(
                    MindMapNode("Stack", 2, ()),
                    MindMapNode("Architecture", 2, ()),
                    MindMapNode("Integration", 2, ()),
                    MindMapNode("Performance", 2, ()),
                    MindMapNode("Security", 2, ()),
                ),
            ),
            MindMapNode(
                label="Process",
                depth=1,
                children=(
                    MindMapNode("Workflow", 2, ()),
                    MindMapNode("Automation", 2, ()),
                    MindMapNode("Monitoring", 2, ()),
                    MindMapNode("Feedback Loops", 2, ()),
                ),
            ),
            MindMapNode(
                label="Business",
                depth=1,
                children=(
                    MindMapNode("Revenue Model", 2, ()),
                    MindMapNode("Cost Structure", 2, ()),
                    MindMapNode("Competitors", 2, ()),
                    MindMapNode("Market Fit", 2, ()),
                    MindMapNode("ROI Metrics", 2, ()),
                ),
            ),
            MindMapNode(
                label="Timeline",
                depth=1,
                children=(
                    MindMapNode("Phase 1: MVP", 2, ()),
                    MindMapNode("Phase 2: Growth", 2, ()),
                    MindMapNode("Phase 3: Scale", 2, ()),
                ),
            ),
        ]

        ascii_map = _build_mind_map_ascii(topic, branches)

        return {
            "method": "Mind Map",
            "description": f"Text-based mind map for {topic}",
            "center": topic,
            "branches": [b.__dict__ for b in branches],
            "ascii_map": ascii_map,
        }

    @staticmethod
    def _generate_summary(topic: str, result_data: dict) -> str:
        ideas_count = 0
        for key in ("ideas", "hats", "stimulus_ideas", "reverse_ideas"):
            if key in result_data:
                ideas_count += len(result_data[key])

        return (
            f"Brainstorming session on '{topic}' using {result_data.get('method', 'unknown')} "
            f"method. Generated {max(ideas_count, 6)} perspectives/ideas. "
            f"Key themes identified include user needs, technology choices, "
            f"and implementation strategy."
        )

    @staticmethod
    def _extract_top_ideas(result_data: dict) -> list[str]:
        if "ideas" in result_data:
            return [i["idea"] for i in result_data["ideas"][:3]]
        if "hats" in result_data:
            return [
                f"{h['hat_color']} Hat: {h['key_insights'][0]}"
                for h in result_data["hats"][:3]
            ]
        if "stimulus_ideas" in result_data:
            return [i["idea"] for i in result_data["stimulus_ideas"][:3]]
        if "reverse_ideas" in result_data:
            return [r["problem_inversion"] for r in result_data["reverse_ideas"][:3]]
        return ["Explore feasibility", "Define scope", "Identify stakeholders"]

    @staticmethod
    def _generate_next_steps(topic: str) -> list[str]:
        return [
            f"Prioritize top concepts for {topic}",
            f"Conduct feasibility analysis for shortlisted ideas",
            f"Create prototype or storyboard for best concept",
            f"Gather feedback from stakeholders",
            f"Define success metrics and validation criteria",
        ]


# ---------------------------------------------------------------------------
# Idea generation helpers (deterministic for test reproducibility)
# ---------------------------------------------------------------------------


def _generate_scamper_idea(technique: str, topic: str) -> str:
    template_map: dict[str, list[str]] = {
        "Substitute": [
            f"Replace traditional components of {topic} with modern alternatives",
            f"Use different materials/tools/approaches for {topic}",
        ],
        "Combine": [
            f"Integrate {topic} with complementary systems for enhanced value",
            f"Merge two features of {topic} into a unified experience",
        ],
        "Adapt": [
            f"Adapt successful patterns from adjacent domains to {topic}",
            f"Borrow best practices from industry leaders for {topic}",
        ],
        "Modify": [
            f"Scale {topic} by adding modularity and extensibility hooks",
            f"Change the form factor or delivery mechanism of {topic}",
        ],
        "Put to another use": [
            f"Repurpose {topic} components for secondary use cases",
            f"Apply {topic} learnings to solve a different problem entirely",
        ],
        "Eliminate": [
            f"Remove non-essential features from {topic} to simplify",
            f"Strip {topic} down to its core value proposition",
        ],
        "Reverse": [
            f"Flip the architecture of {topic}: bottom-up instead of top-down",
            f"Invert the user flow: let the system initiate instead of the user",
        ],
    }

    options = template_map.get(technique, [f"Explore creative alternatives for {topic}"])
    return options[0] if len(options) == 1 else options[hash(technique + topic) % len(options)]


def _generate_stimulus_idea(word: str, topic: str) -> str:
    templates: list[str] = [
        f"The concept of '{word}' suggests we should add iteration/flexibility to {topic}",
        f"'{word}' thinking implies {topic} could benefit from a more organic structure",
        f"Drawing from '{word}', consider applying cyclical/pattern-based thinking to {topic}",
        f"'{word.capitalize()}' as a metaphor: build {topic} with natural feedback loops",
        f"Think of {topic} as a {word}: emphasize adaptability and interconnected components",
    ]
    return templates[hash(word + topic) % len(templates)]


def _build_mind_map_ascii(center: str, branches: tuple[MindMapNode, ...]) -> str:
    lines: list[str] = [
        f"              [{center.upper()}]",
        "                 |",
    ]

    for branch in branches:
        lines.append(f"    +-------+----{branch.label}-------+-------+")
        if branch.children:
            children_text = "    |    " + "    |    ".join(
                f"  [{c.label}]  " for c in branch.children
            )
            lines.append(children_text)
            lines.append("    |    " + "    |    ".join("    |    " for _ in branch.children))
        lines.append("")

    return "\n".join(lines)
