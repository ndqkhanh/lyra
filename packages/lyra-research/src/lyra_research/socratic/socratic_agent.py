"""
Socratic Questioning Agent

Implements State-Challenge-Reflect (SCR) protocol for deep exploration.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class IntentType(Enum):
    """User intent types"""
    EXPLORATORY = "exploratory"
    GOAL_ORIENTED = "goal_oriented"


@dataclass
class UserState:
    """Current user understanding state"""
    query: str
    certainty: float  # 0.0 to 1.0
    assumptions: List[str] = field(default_factory=list)
    knowledge_gaps: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Challenge:
    """Socratic challenge to user's understanding"""
    type: str  # "contradiction", "clarification", "alternatives"
    question: str
    reasoning: str
    expected_response_type: str = "reflection"


@dataclass
class SocraticDialogue:
    """Dialogue session tracking"""
    turns: List[Dict[str, Any]] = field(default_factory=list)
    current_state: Optional[UserState] = None
    intent: Optional[IntentType] = None

    def add_turn(self, turn_type: str, content: Any):
        """Add a turn to the dialogue"""
        self.turns.append({
            "type": turn_type,
            "content": content,
            "turn_number": len(self.turns) + 1
        })


class SocraticQuestioningAgent:
    """
    State-Challenge-Reflect protocol for deep exploration

    Engages users in Socratic dialogue to deepen understanding.
    """

    def __init__(self):
        """Initialize Socratic agent"""
        self.intent_detector = None  # Would be IntentDetector()
        self.challenge_generator = None  # Would be ChallengeGenerator()
        self.reflection_analyzer = None  # Would be ReflectionAnalyzer()

    def engage(self, query: str, context: Dict[str, Any]) -> SocraticDialogue:
        """
        Engage in Socratic dialogue

        Args:
            query: User's research query
            context: Research context

        Returns:
            SocraticDialogue with initial challenge
        """
        # Detect intent: exploratory vs goal-oriented
        intent = self.detect_intent(query, context)

        if intent == IntentType.GOAL_ORIENTED:
            # For goal-oriented queries, use direct research
            return self.direct_research(query, context)

        # Exploratory: Use SCR protocol
        dialogue = SocraticDialogue()
        dialogue.intent = intent

        # State: Extract user's current understanding
        state = self.extract_state(query, context)
        dialogue.current_state = state
        dialogue.add_turn("state", state)

        # Challenge: Question assumptions
        challenge = self.generate_challenge(state)
        dialogue.add_turn("challenge", challenge)

        # Reflect: Wait for user response
        # (This is interactive, so we return the challenge and wait)

        return dialogue

    def detect_intent(self, query: str, context: Dict[str, Any]) -> IntentType:
        """
        Detect user intent: exploratory vs goal-oriented

        Args:
            query: User query
            context: Research context

        Returns:
            IntentType
        """
        # Exploratory indicators
        exploratory_keywords = [
            "explore", "understand", "learn about", "what is",
            "how does", "why", "curious", "investigate"
        ]

        # Goal-oriented indicators
        goal_keywords = [
            "find", "search", "list", "compare", "best",
            "recommend", "which", "should i", "need to"
        ]

        query_lower = query.lower()

        exploratory_score = sum(1 for kw in exploratory_keywords if kw in query_lower)
        goal_score = sum(1 for kw in goal_keywords if kw in query_lower)

        if exploratory_score > goal_score:
            return IntentType.EXPLORATORY
        else:
            return IntentType.GOAL_ORIENTED

    def extract_state(self, query: str, context: Dict[str, Any]) -> UserState:
        """
        Extract user's current understanding state

        Args:
            query: User query
            context: Research context

        Returns:
            UserState
        """
        # Estimate certainty from query phrasing
        certainty = self.estimate_certainty(query)

        # Extract implicit assumptions
        assumptions = self.extract_assumptions(query)

        # Identify knowledge gaps
        gaps = self.identify_gaps(query, context)

        return UserState(
            query=query,
            certainty=certainty,
            assumptions=assumptions,
            knowledge_gaps=gaps,
            context=context
        )

    def estimate_certainty(self, query: str) -> float:
        """
        Estimate user's certainty level from query phrasing

        Args:
            query: User query

        Returns:
            Certainty score (0.0 to 1.0)
        """
        # High certainty indicators
        high_certainty = ["definitely", "certainly", "obviously", "clearly", "must be"]

        # Low certainty indicators
        low_certainty = ["maybe", "perhaps", "might", "could be", "not sure", "wondering"]

        query_lower = query.lower()

        if any(phrase in query_lower for phrase in high_certainty):
            return 0.9
        elif any(phrase in query_lower for phrase in low_certainty):
            return 0.3
        else:
            return 0.5  # Medium certainty

    def extract_assumptions(self, query: str) -> List[str]:
        """
        Extract implicit assumptions from query

        Args:
            query: User query

        Returns:
            List of assumptions
        """
        assumptions = []

        # Look for assumption patterns
        if "because" in query.lower():
            # Extract reasoning after "because"
            parts = query.lower().split("because")
            if len(parts) > 1:
                assumptions.append(f"Assumes: {parts[1].strip()}")

        if "since" in query.lower():
            parts = query.lower().split("since")
            if len(parts) > 1:
                assumptions.append(f"Assumes: {parts[1].strip()}")

        return assumptions

    def identify_gaps(self, query: str, context: Dict[str, Any]) -> List[str]:
        """
        Identify knowledge gaps from query

        Args:
            query: User query
            context: Research context

        Returns:
            List of knowledge gaps
        """
        gaps = []

        # Check for question words indicating gaps
        if "how" in query.lower():
            gaps.append("Mechanism/process understanding")
        if "why" in query.lower():
            gaps.append("Causal/rationale understanding")
        if "what" in query.lower():
            gaps.append("Definitional/conceptual understanding")

        return gaps

    def generate_challenge(self, state: UserState) -> Challenge:
        """
        Generate Socratic challenge based on certainty level

        Args:
            state: User state

        Returns:
            Challenge
        """
        if state.certainty > 0.8:
            # High certainty: Trigger contradiction
            return self.generate_contradiction(state)
        elif state.certainty < 0.3:
            # Low certainty: Clarifying questions
            return self.generate_clarification(state)
        else:
            # Medium certainty: Explore alternatives
            return self.generate_alternatives(state)

    def generate_contradiction(self, state: UserState) -> Challenge:
        """
        Generate contradiction challenge for high-certainty state

        Args:
            state: User state

        Returns:
            Challenge with contradiction
        """
        return Challenge(
            type="contradiction",
            question=f"You seem certain about '{state.query}'. What evidence would change your mind?",
            reasoning="High certainty detected - testing falsifiability",
            expected_response_type="counter_evidence"
        )

    def generate_clarification(self, state: UserState) -> Challenge:
        """
        Generate clarification challenge for low-certainty state

        Args:
            state: User state

        Returns:
            Challenge with clarification
        """
        if state.knowledge_gaps:
            gap = state.knowledge_gaps[0]
            return Challenge(
                type="clarification",
                question=f"Let's start with {gap}. What specifically would you like to understand?",
                reasoning="Low certainty - need to clarify scope",
                expected_response_type="clarification"
            )
        else:
            return Challenge(
                type="clarification",
                question="What aspect of this topic interests you most?",
                reasoning="Low certainty - exploring interests",
                expected_response_type="clarification"
            )

    def generate_alternatives(self, state: UserState) -> Challenge:
        """
        Generate alternatives challenge for medium-certainty state

        Args:
            state: User state

        Returns:
            Challenge with alternatives
        """
        return Challenge(
            type="alternatives",
            question=f"What alternative explanations or approaches have you considered for '{state.query}'?",
            reasoning="Medium certainty - exploring alternatives",
            expected_response_type="alternatives"
        )

    def direct_research(self, query: str, context: Dict[str, Any]) -> SocraticDialogue:
        """
        Handle goal-oriented queries with direct research

        Args:
            query: User query
            context: Research context

        Returns:
            SocraticDialogue indicating direct research mode
        """
        dialogue = SocraticDialogue()
        dialogue.intent = IntentType.GOAL_ORIENTED
        dialogue.add_turn("direct_research", {
            "query": query,
            "mode": "goal_oriented",
            "message": "Proceeding with direct research (goal-oriented query detected)"
        })
        return dialogue
