"""
Structured Multi-Agent Debate System

Implements AutoResearchClaw's debate mechanism for hypothesis refinement:
- Pre-experiment debates to sharpen ideas
- Post-experiment debates to validate results
- Multiple perspectives (skeptic, optimist, methodologist, domain expert)
- Synthesis and consensus building

Based on: researchclaw/pipeline/debate.py
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from openai import OpenAI

logger = logging.getLogger(__name__)


class Perspective(Enum):
    """Agent perspective in debate"""
    SKEPTIC = "skeptic"              # Challenges assumptions
    OPTIMIST = "optimist"            # Explores potential
    METHODOLOGIST = "methodologist"  # Focuses on rigor
    DOMAIN_EXPERT = "domain_expert"  # Provides context
    PRAGMATIST = "pragmatist"        # Considers feasibility


@dataclass
class DebateMessage:
    """Single message in debate"""
    perspective: Perspective
    content: str
    round_number: int


@dataclass
class DebateRound:
    """One round of debate"""
    round_number: int
    messages: list[DebateMessage]
    synthesis: str | None = None


@dataclass
class DebateResult:
    """Complete debate result"""
    topic: str
    rounds: list[DebateRound]
    final_synthesis: str
    consensus_reached: bool
    key_insights: list[str]


class DebateAgent:
    """Single agent with specific perspective"""

    def __init__(
        self,
        perspective: Perspective,
        llm_client: Any,
        model: str = "claude-3-5-sonnet-20241022",
    ):
        self.perspective = perspective
        self.llm_client = llm_client
        self.model = model

    def generate_response(
        self,
        topic: str,
        context: str,
        previous_messages: list[DebateMessage],
    ) -> str:
        """Generate response from this perspective"""

        # Build perspective-specific system prompt
        system_prompts = {
            Perspective.SKEPTIC: (
                "You are a skeptical researcher. Challenge assumptions, "
                "identify potential flaws, and ask hard questions. "
                "Be constructive but rigorous."
            ),
            Perspective.OPTIMIST: (
                "You are an optimistic researcher. Explore potential, "
                "identify opportunities, and build on ideas. "
                "Be enthusiastic but grounded."
            ),
            Perspective.METHODOLOGIST: (
                "You are a methodological expert. Focus on experimental rigor, "
                "statistical validity, and reproducibility. "
                "Ensure the approach is sound."
            ),
            Perspective.DOMAIN_EXPERT: (
                "You are a domain expert. Provide context from the field, "
                "cite relevant work, and connect to existing knowledge. "
                "Ground the discussion in reality."
            ),
            Perspective.PRAGMATIST: (
                "You are a pragmatic researcher. Consider feasibility, "
                "resource constraints, and practical implementation. "
                "Keep the discussion actionable."
            ),
        }

        system_prompt = system_prompts[self.perspective]

        # Build conversation history
        history = f"Topic: {topic}\n\nContext: {context}\n\n"
        if previous_messages:
            history += "Previous discussion:\n"
            for msg in previous_messages:
                history += f"[{msg.perspective.value}]: {msg.content}\n\n"

        user_prompt = (
            f"{history}\n"
            f"As the {self.perspective.value}, provide your perspective on this topic. "
            f"Be specific and constructive. Limit to 3-4 sentences."
        )

        try:
            if isinstance(self.llm_client, Anthropic):
                response = self.llm_client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return response.content[0].text
            elif isinstance(self.llm_client, OpenAI):
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                return response.choices[0].message.content
            else:
                raise ValueError(f"Unsupported LLM client: {type(self.llm_client)}")
        except Exception as e:
            logger.error(f"Agent {self.perspective.value} failed: {e}")
            return f"[Error generating response: {e}]"


class DebatePanel:
    """
    Multi-agent debate panel

    Orchestrates structured debates with multiple perspectives
    """

    def __init__(
        self,
        perspectives: list[Perspective],
        llm_client: Any,
        model: str = "claude-3-5-sonnet-20241022",
    ):
        self.agents = [
            DebateAgent(p, llm_client, model)
            for p in perspectives
        ]
        self.llm_client = llm_client
        self.model = model

    def run_round(
        self,
        topic: str,
        context: str,
        round_number: int,
        previous_messages: list[DebateMessage],
    ) -> DebateRound:
        """Run one round of debate"""

        messages = []

        # Each agent responds in sequence
        for agent in self.agents:
            response = agent.generate_response(
                topic=topic,
                context=context,
                previous_messages=previous_messages + messages,
            )

            message = DebateMessage(
                perspective=agent.perspective,
                content=response,
                round_number=round_number,
            )
            messages.append(message)

        # Synthesize round
        synthesis = self._synthesize_round(topic, messages)

        return DebateRound(
            round_number=round_number,
            messages=messages,
            synthesis=synthesis,
        )

    def _synthesize_round(self, topic: str, messages: list[DebateMessage]) -> str:
        """Synthesize insights from a round"""

        discussion = "\n\n".join([
            f"[{msg.perspective.value}]: {msg.content}"
            for msg in messages
        ])

        prompt = (
            f"Topic: {topic}\n\n"
            f"Discussion:\n{discussion}\n\n"
            f"Synthesize the key insights and areas of agreement/disagreement. "
            f"Be concise (2-3 sentences)."
        )

        try:
            if isinstance(self.llm_client, Anthropic):
                response = self.llm_client.messages.create(
                    model=self.model,
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            elif isinstance(self.llm_client, OpenAI):
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return "[Synthesis unavailable]"

    def run_debate(
        self,
        topic: str,
        context: str,
        num_rounds: int = 2,
    ) -> DebateResult:
        """
        Run complete multi-round debate

        Args:
            topic: Research question or hypothesis
            context: Background information
            num_rounds: Number of debate rounds (default: 2)

        Returns:
            DebateResult with all rounds and final synthesis
        """

        rounds = []
        all_messages = []

        for round_num in range(1, num_rounds + 1):
            debate_round = self.run_round(
                topic=topic,
                context=context,
                round_number=round_num,
                previous_messages=all_messages,
            )
            rounds.append(debate_round)
            all_messages.extend(debate_round.messages)

        # Final synthesis
        final_synthesis = self._generate_final_synthesis(topic, rounds)

        # Extract key insights
        key_insights = self._extract_key_insights(rounds)

        # Check consensus
        consensus_reached = self._check_consensus(rounds)

        return DebateResult(
            topic=topic,
            rounds=rounds,
            final_synthesis=final_synthesis,
            consensus_reached=consensus_reached,
            key_insights=key_insights,
        )

    def _generate_final_synthesis(
        self,
        topic: str,
        rounds: list[DebateRound],
    ) -> str:
        """Generate final synthesis across all rounds"""

        round_summaries = "\n\n".join([
            f"Round {r.round_number} synthesis: {r.synthesis}"
            for r in rounds
        ])

        prompt = (
            f"Topic: {topic}\n\n"
            f"Debate progression:\n{round_summaries}\n\n"
            f"Provide a final synthesis that:\n"
            f"1. Summarizes the refined understanding\n"
            f"2. Highlights key improvements to the original idea\n"
            f"3. Identifies remaining concerns or open questions\n"
            f"Limit to 4-5 sentences."
        )

        try:
            if isinstance(self.llm_client, Anthropic):
                response = self.llm_client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            elif isinstance(self.llm_client, OpenAI):
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Final synthesis failed: {e}")
            return "[Final synthesis unavailable]"

    def _extract_key_insights(self, rounds: list[DebateRound]) -> list[str]:
        """Extract key insights from debate"""

        # Simple extraction: collect unique points from syntheses
        insights = []
        for debate_round in rounds:
            if debate_round.synthesis:
                # Split by sentence
                sentences = debate_round.synthesis.split('. ')
                insights.extend([s.strip() for s in sentences if s.strip()])

        # Deduplicate and limit
        unique_insights = list(dict.fromkeys(insights))
        return unique_insights[:5]

    def _check_consensus(self, rounds: list[DebateRound]) -> bool:
        """Check if consensus was reached (simplified heuristic)"""

        if len(rounds) < 2:
            return False

        # Check if later rounds show convergence
        # Heuristic: if synthesis mentions "agreement" or "consensus"
        last_synthesis = rounds[-1].synthesis.lower()
        consensus_keywords = ["agreement", "consensus", "converge", "align"]

        return any(keyword in last_synthesis for keyword in consensus_keywords)


def run_debate(
    topic: str,
    context: str,
    perspectives: list[Perspective] | None = None,
    num_rounds: int = 2,
    llm_client: Any | None = None,
    model: str = "claude-3-5-sonnet-20241022",
) -> DebateResult:
    """
    Convenience function: Run a structured debate

    Args:
        topic: Research question or hypothesis
        context: Background information
        perspectives: List of perspectives (default: skeptic, optimist, methodologist)
        num_rounds: Number of debate rounds (default: 2)
        llm_client: LLM client (Anthropic or OpenAI)
        model: Model name

    Returns:
        DebateResult with complete debate transcript and synthesis
    """

    if perspectives is None:
        perspectives = [
            Perspective.SKEPTIC,
            Perspective.OPTIMIST,
            Perspective.METHODOLOGIST,
        ]

    if llm_client is None:
        # Try to create default client
        try:
            llm_client = Anthropic()
        except Exception:
            try:
                llm_client = OpenAI()
                model = "gpt-4"
            except Exception as e:
                raise ValueError(f"No LLM client available: {e}")

    panel = DebatePanel(
        perspectives=perspectives,
        llm_client=llm_client,
        model=model,
    )

    return panel.run_debate(topic, context, num_rounds)
