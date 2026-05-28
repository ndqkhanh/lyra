"""Question-driven reflection for memory strengthening.

Generates factual, relational, and applied questions from consolidated
memories and tests recall to identify weak memories needing reinforcement.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class QuestionType(StrEnum):
    FACTUAL = "factual"
    RELATIONAL = "relational"
    APPLIED = "applied"


class SignalStrength(StrEnum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass(frozen=True)
class ReflectionQuestion:
    question_id: str
    question_type: QuestionType
    text: str
    source_memory_id: str
    created_at: float


@dataclass(frozen=True)
class ReflectionSignal:
    memory_id: str
    strength: SignalStrength
    score: float
    question_count: int
    weak_questions: list[str]
    timestamp: float


@dataclass(frozen=True)
class ReflectionSession:
    signals: list[ReflectionSignal]
    questions_generated: int
    weak_memories: int
    moderate_memories: int
    strong_memories: int
    elapsed_ms: float


class QuestionDrivenReflector:
    """Generate questions from consolidated memories and test recall.

    For each memory, generates 3 question types:
    - Factual: "What is X?" — tests basic recall
    - Relational: "How does X relate to Y?" — tests contextual understanding
    - Applied: "When would you use X?" — tests practical knowledge

    Low-scoring answers indicate weak memories that need strengthening.
    """

    WEAK_THRESHOLD = 0.4
    STRONG_THRESHOLD = 0.8

    _FACTUAL_TEMPLATES: list[str] = [
        "What is {entity}?",
        "Define {entity}.",
        "What does {entity} refer to?",
    ]

    _RELATIONAL_TEMPLATES: list[str] = [
        "How does {entity} relate to {related}?",
        "What is the connection between {entity} and {related}?",
        "Why is {entity} important for {related}?",
    ]

    _APPLIED_TEMPLATES: list[str] = [
        "When would you use {entity}?",
        "In what context is {entity} most useful?",
        "What problem does {entity} solve?",
    ]

    def reflect(
        self,
        fragments: list[dict],
        related_entities: dict[str, list[str]] | None = None,
    ) -> ReflectionSession:
        start = time.perf_counter()
        signals: list[ReflectionSignal] = []
        total_questions = 0

        related = related_entities or {}

        for frag in fragments:
            memory_id = frag.get("id", "")
            entity = frag.get("entity", frag.get("name", ""))
            content = frag.get("content", "")

            if not entity or not content:
                continue

            questions = self._generate_questions(
                memory_id, entity, related.get(memory_id, [])
            )
            total_questions += len(questions)

            score = self._score_recall(memory_id, content, questions)
            weak_qs = [q.text for q in questions if self._assess_question(q, content) < self.WEAK_THRESHOLD]

            if score >= self.STRONG_THRESHOLD:
                strength = SignalStrength.STRONG
            elif score >= self.WEAK_THRESHOLD:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK

            signals.append(ReflectionSignal(
                memory_id=memory_id,
                strength=strength,
                score=round(score, 4),
                question_count=len(questions),
                weak_questions=weak_qs,
                timestamp=time.time(),
            ))

        elapsed = (time.perf_counter() - start) * 1000
        return ReflectionSession(
            signals=signals,
            questions_generated=total_questions,
            weak_memories=sum(1 for s in signals if s.strength == SignalStrength.WEAK),
            moderate_memories=sum(1 for s in signals if s.strength == SignalStrength.MODERATE),
            strong_memories=sum(1 for s in signals if s.strength == SignalStrength.STRONG),
            elapsed_ms=round(elapsed, 2),
        )

    def _generate_questions(
        self,
        memory_id: str,
        entity: str,
        related_entities: list[str],
    ) -> list[ReflectionQuestion]:
        questions: list[ReflectionQuestion] = []

        for template in self._FACTUAL_TEMPLATES[:1]:
            q_text = template.format(entity=entity)
            qid = hashlib.sha256(f"factual|{memory_id}|{q_text}".encode()).hexdigest()[:10]
            questions.append(ReflectionQuestion(
                question_id=qid,
                question_type=QuestionType.FACTUAL,
                text=q_text,
                source_memory_id=memory_id,
                created_at=time.time(),
            ))

        if related_entities:
            rel = related_entities[0]
            for template in self._RELATIONAL_TEMPLATES[:1]:
                q_text = template.format(entity=entity, related=rel)
                qid = hashlib.sha256(f"relational|{memory_id}|{q_text}".encode()).hexdigest()[:10]
                questions.append(ReflectionQuestion(
                    question_id=qid,
                    question_type=QuestionType.RELATIONAL,
                    text=q_text,
                    source_memory_id=memory_id,
                    created_at=time.time(),
                ))

        for template in self._APPLIED_TEMPLATES[:1]:
            q_text = template.format(entity=entity)
            qid = hashlib.sha256(f"applied|{memory_id}|{q_text}".encode()).hexdigest()[:10]
            questions.append(ReflectionQuestion(
                question_id=qid,
                question_type=QuestionType.APPLIED,
                text=q_text,
                source_memory_id=memory_id,
                created_at=time.time(),
            ))

        return questions

    def _score_recall(
        self,
        _memory_id: str,
        content: str,
        questions: list[ReflectionQuestion],
    ) -> float:
        if not questions:
            return 1.0
        scores = [self._assess_question(q, content) for q in questions]
        return sum(scores) / len(scores)

    def _assess_question(
        self, question: ReflectionQuestion, content: str
    ) -> float:
        content_lower = content.lower()
        if question.question_type == QuestionType.FACTUAL:
            keywords = self._extract_keywords(question.text)
            matches = sum(1 for kw in keywords if kw.lower() in content_lower)
            return min(1.0, matches / max(len(keywords), 1))
        elif question.question_type == QuestionType.RELATIONAL:
            return 0.5 if len(content_lower) > 50 else 0.2
        else:
            return 0.7 if len(content_lower) > 30 else 0.3

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        words = text.lower().replace("?", "").replace(".", "").split()
        stopwords = {"what", "is", "the", "a", "an", "of", "in", "to", "for",
                      "does", "how", "when", "would", "you", "are", "was"}
        return [w for w in words if w not in stopwords and len(w) > 2]

    def stats(self) -> dict:
        return {
            "weak_threshold": self.WEAK_THRESHOLD,
            "strong_threshold": self.STRONG_THRESHOLD,
            "question_types": [t.value for t in QuestionType],
        }
