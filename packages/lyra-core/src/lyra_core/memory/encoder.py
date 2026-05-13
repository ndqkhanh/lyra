"""Fragment Encoder — extracts structured memory from agent turns (Phase M2).

Given a turn (user message + assistant response + tool calls), the Encoder
produces 0–N Fragments typed as Fact / Decision / Preference / Skill /
Observation. A turn with nothing memorable returns [].

Two modes:
  - **LLM mode** (production): single LLM call per turn with a tight
    extraction prompt. The model is told to ignore tool boilerplate, file
    contents, and one-turn re-statements.
  - **Rule mode** (default / testing): fast heuristic extraction with no
    LLM call — useful for unit tests and offline replay.

Key design decisions:
  - DECISION fragments must include `structured["rationale"]` — this is
    enforced by the Fragment schema itself.
  - OBSERVATION defaults to confidence=0.5; everything else is 0.7.
  - Entities are extracted with a simple noun-phrase regex (production
    should replace this with spaCy/NER or the LLM output).

Research grounding:
  - Mem0 two-stage extraction (GPT-class extractor + ADD/UPDATE/DELETE router)
  - FluxMem STIM capacity-4-page LRU, motivated by Cowan's chunk model
  - Design proposal §4 encoder prompt sketch and §12 open question 2
    (granularity: per-atomic-claim for FACT/DECISION, per-turn for OBSERVATION)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .schema import Fragment, FragmentType, MemoryTier, Provenance, VisibilityScope


# ---------------------------------------------------------------------------
# Turn — input to the Encoder
# ---------------------------------------------------------------------------


@dataclass
class Turn:
    """One agent turn to be encoded into fragments."""

    user_message: str
    assistant_response: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    provenance: Provenance | None = None
    session_id: str = "default"
    agent_id: str = "lyra"
    user_id: str = "local"

    def full_text(self) -> str:
        parts = []
        if self.user_message:
            parts.append(f"User: {self.user_message}")
        if self.assistant_response:
            parts.append(f"Assistant: {self.assistant_response}")
        for tc in self.tool_calls:
            name = tc.get("name", "tool")
            result = tc.get("result", "")
            parts.append(f"Tool[{name}]: {result[:200]}")
        return "\n".join(parts)

    def get_provenance(self) -> Provenance:
        if self.provenance:
            return self.provenance
        return Provenance(
            agent_id=self.agent_id,
            session_id=self.session_id,
            user_id=self.user_id,
            tool_calls=[tc.get("name", "") for tc in self.tool_calls],
        )


# ---------------------------------------------------------------------------
# Heuristic entity extraction
# ---------------------------------------------------------------------------

_ENTITY_RE = re.compile(r"`([^`]+)`|([A-Z][A-Za-z0-9_]{2,}(?:\.[A-Za-z0-9_]+)*)")


def _extract_entities(text: str, max_entities: int = 5) -> list[str]:
    """Extract code symbols and backtick-quoted terms from text."""
    seen: dict[str, None] = {}
    for m in _ENTITY_RE.finditer(text):
        token = m.group(1) or m.group(2)
        if token and token not in seen:
            seen[token] = None
        if len(seen) >= max_entities:
            break
    return list(seen)


# ---------------------------------------------------------------------------
# Rule-based extraction helpers (no LLM call)
# ---------------------------------------------------------------------------

_DECISION_PATTERNS = [
    re.compile(r"\b(decided|chose|adopted|switched|picked|selected|will use)\b", re.I),
    re.compile(r"\b(instead of|over|rather than|because|therefore|so we)\b", re.I),
]

_PREFERENCE_PATTERNS = [
    re.compile(r"\b(prefer|want|like|always|never|avoid|don'?t use)\b", re.I),
    re.compile(r"\buser (wants|prefers|likes|asks)\b", re.I),
]

_SKILL_PATTERNS = [
    re.compile(r"\b(run|execute|invoke|call)\b.{0,30}`[^`]+`", re.I),
    re.compile(r"```[a-z]*\n", re.I),
]

_OBSERVATION_PATTERNS = [
    re.compile(r"\b(noticed|found|observed|seems|appears|looks like|turns out)\b", re.I),
    re.compile(r"\b(failed|broke|error|exception|traceback)\b", re.I),
]


def _score_patterns(text: str, patterns: list[re.Pattern]) -> int:
    return sum(1 for p in patterns if p.search(text))


def _extract_rationale(text: str) -> str:
    """Pull a brief rationale from decision-like text."""
    for kw in ("because", "since", "due to", "as", "so that"):
        idx = text.lower().find(kw)
        if idx != -1:
            snippet = text[idx: idx + 150].strip()
            return snippet
    # Fallback: last 120 chars of text
    return text[-120:].strip()


def _split_sentences(text: str) -> list[str]:
    """Very rough sentence splitter."""
    return [s.strip() for s in re.split(r"[.!?]\s+", text) if len(s.strip()) > 15]


# ---------------------------------------------------------------------------
# RuleEncoder
# ---------------------------------------------------------------------------


class RuleEncoder:
    """Heuristic encoder — no LLM call.

    Used for unit tests and offline replay. Production should use LLMEncoder.
    Rules are intentionally simple; the goal is reasonable recall, not precision.
    """

    def encode(self, turn: Turn) -> list[Fragment]:
        text = turn.full_text()
        prov = turn.get_provenance()
        frags: list[Fragment] = []

        # Classify the turn at a high level
        decision_score = _score_patterns(text, _DECISION_PATTERNS)
        pref_score = _score_patterns(text, _PREFERENCE_PATTERNS)
        obs_score = _score_patterns(text, _OBSERVATION_PATTERNS)
        skill_score = _score_patterns(text, _SKILL_PATTERNS)

        if decision_score >= 1:
            rationale = _extract_rationale(text)
            content = self._first_sentence(turn.assistant_response or text, 200)
            if content:
                frags.append(Fragment.make(
                    tier=MemoryTier.T2_PROCEDURAL,
                    type=FragmentType.DECISION,
                    content=content,
                    provenance=prov,
                    structured={"rationale": rationale},
                    entities=_extract_entities(text),
                    confidence=0.7,
                    visibility="project",
                ))

        if pref_score >= 1 and not decision_score:
            content = self._first_sentence(
                turn.user_message or turn.assistant_response, 200
            )
            if content:
                frags.append(Fragment.make(
                    tier=MemoryTier.T3_USER,
                    type=FragmentType.PREFERENCE,
                    content=content,
                    provenance=prov,
                    entities=_extract_entities(text),
                    confidence=0.7,
                    visibility="private",
                ))

        if obs_score >= 1 and not frags:
            content = self._first_sentence(turn.assistant_response or text, 200)
            if content:
                frags.append(Fragment.make(
                    tier=MemoryTier.T1_SESSION,
                    type=FragmentType.OBSERVATION,
                    content=content,
                    provenance=prov,
                    entities=_extract_entities(text),
                    # OBSERVATION defaults to 0.5 via Fragment.make
                    visibility="task",
                ))

        if skill_score >= 1 and not frags:
            content = self._first_sentence(turn.assistant_response or text, 200)
            if content:
                frags.append(Fragment.make(
                    tier=MemoryTier.T2_PROCEDURAL,
                    type=FragmentType.SKILL,
                    content=content,
                    provenance=prov,
                    entities=_extract_entities(text),
                    confidence=0.7,
                    visibility="project",
                ))

        # Generic FACT fallback for substantial assistant responses
        if not frags and len(turn.assistant_response) > 60:
            content = self._first_sentence(turn.assistant_response, 200)
            if content:
                frags.append(Fragment.make(
                    tier=MemoryTier.T2_SEMANTIC,
                    type=FragmentType.FACT,
                    content=content,
                    provenance=prov,
                    entities=_extract_entities(text),
                    confidence=0.6,
                    visibility="project",
                ))

        return frags

    @staticmethod
    def _first_sentence(text: str, max_len: int) -> str:
        if not text:
            return ""
        sentences = _split_sentences(text)
        if sentences:
            return sentences[0][:max_len]
        return text[:max_len].strip()


# ---------------------------------------------------------------------------
# LLMEncoder (stub — wired to real LLM in integration layer)
# ---------------------------------------------------------------------------


class LLMEncoder:
    """LLM-based encoder for production use.

    Takes a single LLM call per turn (or batched). The prompt is the
    design-proposal §13 encoder prompt. Falls back to RuleEncoder if
    the LLM call fails.

    Production wiring: inject an ``llm_fn(prompt: str) -> str`` callable.
    Testing: pass ``llm_fn=None`` to force RuleEncoder fallback.
    """

    _PROMPT_TEMPLATE = """\
You extract structured memory fragments from a coding-agent turn.
Output a JSON list of fragments. Each fragment is one atomic claim.

Allowed types: fact | decision | preference | skill | observation.

For type=decision, ALWAYS include "rationale": WHY the decision was made.
For type=preference, the subject is the USER.
For type=observation, mark confidence ~0.5 by default.

Ignore: tool boilerplate, file contents (the file system is the source of
truth), re-statements of things the user said one turn ago.

Each fragment: type, content (≤200 chars), entities (≤5 noun-phrases),
confidence (0..1), structured (optional dict with type-specific fields).

If the turn produces nothing memorable, return [].

--- TURN ---
{turn_text}
--- END ---

JSON:"""

    def __init__(self, llm_fn=None) -> None:
        self._llm_fn = llm_fn
        self._fallback = RuleEncoder()

    def encode(self, turn: Turn) -> list[Fragment]:
        if self._llm_fn is None:
            return self._fallback.encode(turn)

        prompt = self._PROMPT_TEMPLATE.format(turn_text=turn.full_text()[:4000])
        try:
            raw = self._llm_fn(prompt)
            return self._parse_llm_output(raw, turn)
        except Exception:
            return self._fallback.encode(turn)

    def _parse_llm_output(self, raw: str, turn: Turn) -> list[Fragment]:
        import json

        prov = turn.get_provenance()
        frags: list[Fragment] = []

        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"```$", "", raw.rstrip())

        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            return self._fallback.encode(turn)

        if not isinstance(items, list):
            return self._fallback.encode(turn)

        for item in items:
            if not isinstance(item, dict):
                continue
            ftype_str = item.get("type", "fact").lower()
            try:
                ftype = FragmentType(ftype_str)
            except ValueError:
                continue

            content = str(item.get("content", ""))[:200]
            if not content:
                continue

            structured = dict(item.get("structured", {}))
            confidence = float(item.get("confidence", 0.5 if ftype is FragmentType.OBSERVATION else 0.7))
            entities = [str(e) for e in item.get("entities", [])][:5]

            tier = _infer_tier(ftype)
            visibility: VisibilityScope = _infer_visibility(ftype)

            # DECISION: ensure rationale present
            if ftype is FragmentType.DECISION and "rationale" not in structured:
                structured["rationale"] = content  # use content as fallback rationale

            try:
                frags.append(Fragment.make(
                    tier=tier,
                    type=ftype,
                    content=content,
                    provenance=prov,
                    structured=structured,
                    entities=entities,
                    confidence=confidence,
                    visibility=visibility,
                ))
            except ValueError:
                continue

        return frags


def _infer_tier(ftype: FragmentType) -> MemoryTier:
    return {
        FragmentType.FACT: MemoryTier.T2_SEMANTIC,
        FragmentType.DECISION: MemoryTier.T2_PROCEDURAL,
        FragmentType.PREFERENCE: MemoryTier.T3_USER,
        FragmentType.SKILL: MemoryTier.T2_PROCEDURAL,
        FragmentType.OBSERVATION: MemoryTier.T1_SESSION,
    }[ftype]


def _infer_visibility(ftype: FragmentType) -> VisibilityScope:
    return {
        FragmentType.FACT: "project",
        FragmentType.DECISION: "project",
        FragmentType.PREFERENCE: "private",
        FragmentType.SKILL: "project",
        FragmentType.OBSERVATION: "task",
    }[ftype]


__all__ = ["LLMEncoder", "RuleEncoder", "Turn"]
