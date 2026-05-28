"""
Agentic Zettelkasten Memory — A-Mem architecture (ICLR 2026 MemAgent Workshop).

Self-organizing memory where the LLM autonomously constructs, links, and evolves
memory notes. Ranked #1 across 6 foundation models on LoCoMo with 93.6% token
reduction vs MemGPT.

Core components:
    NoteConstructor  — LLM decides what/how to store
    LinkGenerator    — Autonomous bidirectional link creation
    MemoryEvolver    — Updates existing memories when new info arrives
    ZettelkastenMemoryStore — Full integration combining all three operations
"""

from lyra_memory.agentic.link_generator import LinkGenerator, LinkType
from lyra_memory.agentic.memory_evolver import MemoryEvolver
from lyra_memory.agentic.note_constructor import NoteConstructor
from lyra_memory.agentic.zettelkasten_store import (
    AgenticMemoryNote,
    ZettelkastenMemoryStore,
)

__all__ = [
    "AgenticMemoryNote",
    "LinkGenerator",
    "LinkType",
    "MemoryEvolver",
    "NoteConstructor",
    "ZettelkastenMemoryStore",
]
