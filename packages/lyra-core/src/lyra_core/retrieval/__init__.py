"""Retrieval-augmented generation (RAG) layer for the Lyra agent.

Currently hosts the v1.8 *Skill-RAG* contract (Wave-1 §3.3) — hidden-state
prober + a four-skill recovery router (Query Rewriting, Question
Decomposition, Evidence Focusing, Exit) backed by the existing
``..memory.procedural`` skill registry.
"""
from __future__ import annotations

from .skill_rag import (
    HiddenStateProber,
    ProberVerdict,
    RecoverySkill,
    RetrievalAttempt,
    RetrievalResult,
    SkillRagRouter,
)

__all__ = [
    "HiddenStateProber",
    "ProberVerdict",
    "RecoverySkill",
    "RetrievalAttempt",
    "RetrievalResult",
    "SkillRagRouter",
]
