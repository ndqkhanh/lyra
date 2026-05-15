"""
MEMTIER Memory System Integration

Integrates all three memory tiers:
- Episodic: Append-only JSONL log of events
- Semantic: LLM-distilled facts from episodic clusters
- Procedural: Skills, tools, executable knowledge (existing SQLite FTS5)

Based on research: docs/151-153 (MEMTIER papers)
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import logging

from lyra_core.memory.episodic import EpisodicMemory
from lyra_core.memory.semantic_consolidator import SemanticConsolidator
from lyra_core.memory.two_stage_retrieval import TwoStageRetriever
from lyra_core.memory.cognitive_weight import CognitiveWeightAttributor

logger = logging.getLogger(__name__)


class MemTierMemorySystem:
    """
    Complete MEMTIER 3-tier memory system.

    Provides unified interface to all memory tiers with automatic
    consolidation and cognitive weight attribution.
    """

    def __init__(
        self,
        memory_dir: Optional[Path] = None,
        procedural_db: Optional[str] = None,
        llm_model: str = "deepseek-v4-flash",
        auto_consolidate: bool = True
    ):
        """
        Initialize MEMTIER memory system.

        Args:
            memory_dir: Base directory for memory storage
            procedural_db: Path to procedural memory SQLite DB
            llm_model: LLM model for semantic consolidation
            auto_consolidate: Whether to auto-consolidate on init
        """
        if memory_dir is None:
            memory_dir = Path.home() / ".lyra" / "memory"

        if procedural_db is None:
            procedural_db = str(memory_dir / "procedural.db")

        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Initialize tiers
        self.episodic = EpisodicMemory(memory_dir / "episodic")
        self.semantic = SemanticConsolidator(
            self.episodic,
            semantic_store_path=memory_dir / "semantic_facts.json",
            llm_model=llm_model
        )
        self.procedural_db = procedural_db

        # Initialize cognitive weight attributor
        self.attributor = CognitiveWeightAttributor(procedural_db)

        # Initialize two-stage retriever
        self.retriever = TwoStageRetriever(
            self.semantic,
            self.episodic,
            procedural_db
        )

        # Auto-consolidate if enabled
        if auto_consolidate:
            self._check_consolidation_needed()

        logger.info("MEMTIER memory system initialized")

    def log_event(
        self,
        session_id: str,
        project: str,
        event_type: str,
        content: str,
        tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log an event to episodic memory.

        Args:
            session_id: Session identifier
            project: Project name
            event_type: Type of event (user_input, tool_call, agent_response, error)
            content: Event content
            tokens: Token count
            metadata: Additional metadata

        Returns:
            Entry ID
        """
        entry = self.episodic.append_event(
            session_id=session_id,
            project=project,
            event_type=event_type,
            content=content,
            tokens=tokens,
            metadata=metadata
        )

        logger.debug(f"Logged {event_type} event: {entry.id}")
        return entry.id

    def search(
        self,
        query: str,
        k: int = 10,
        include_episodic: bool = True,
        include_semantic: bool = True,
        include_procedural: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search across all memory tiers using two-stage retrieval.

        Args:
            query: Search query
            k: Number of results
            include_episodic: Include episodic memory
            include_semantic: Include semantic facts
            include_procedural: Include procedural memory

        Returns:
            List of search results with scores
        """
        # Use two-stage retrieval
        results = self.retriever.retrieve(
            query=query,
            k=k,
            include_procedural=include_procedural
        )

        # Filter by tier if requested
        filtered_results = []
        for result in results:
            if result.source == "episodic" and not include_episodic:
                continue
            if result.source == "semantic" and not include_semantic:
                continue
            if result.source == "procedural" and not include_procedural:
                continue

            filtered_results.append({
                'id': result.id,
                'content': result.content,
                'score': result.score,
                'source': result.source,
                'session_id': result.session_id,
                'timestamp': result.timestamp,
                'cognitive_weight': result.cognitive_weight
            })

        return filtered_results

    def consolidate(self, llm, days_back: int = 1) -> Dict[str, Any]:
        """
        Run semantic consolidation: extract facts from episodic memory.

        Args:
            llm: LLM instance for fact extraction
            days_back: Number of days to consolidate

        Returns:
            Consolidation statistics
        """
        logger.info(f"Starting consolidation for last {days_back} day(s)")

        stats = self.semantic.consolidate(
            llm=llm,
            days_back=days_back
        )

        logger.info(
            f"Consolidation complete: {stats['facts_added']} facts added, "
            f"{stats['facts_deduplicated']} deduplicated"
        )

        return stats

    def update_cognitive_weights(self, session_id: str) -> None:
        """
        Update cognitive weights based on tool call outcomes.

        Args:
            session_id: Session to analyze
        """
        logger.info(f"Updating cognitive weights for session {session_id}")
        self.attributor.update_weights_for_session(session_id)

    def prune_low_weight_memories(self, threshold: float = -0.5) -> int:
        """
        Remove memories with low cognitive weight.

        Args:
            threshold: Minimum weight to keep

        Returns:
            Number of entries pruned
        """
        count = self.attributor.prune_low_weight_entries(threshold)
        logger.info(f"Pruned {count} low-weight entries")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about all memory tiers."""
        episodic_stats = self.episodic.get_stats()
        retrieval_stats = self.retriever.get_retrieval_stats()

        return {
            'episodic': episodic_stats,
            'semantic': {
                'total_facts': len(self.semantic.facts),
                'avg_confidence': sum(f.confidence for f in self.semantic.facts) / len(self.semantic.facts) if self.semantic.facts else 0.0
            },
            'procedural': {
                'total_entries': retrieval_stats['procedural_entries']
            },
            'total_memory_items': (
                episodic_stats['total_entries'] +
                len(self.semantic.facts) +
                retrieval_stats['procedural_entries']
            )
        }

    def _check_consolidation_needed(self) -> bool:
        """
        Check if consolidation is needed.

        Returns:
            True if consolidation should run
        """
        unpromoted = self.episodic.get_unpromoted_entries(limit=100)

        if len(unpromoted) >= 50:
            logger.info(f"{len(unpromoted)} unpromoted entries, consolidation recommended")
            return True

        return False

    def export_memory(self, output_path: Path) -> None:
        """
        Export all memory to a single JSON file for backup.

        Args:
            output_path: Path to export file
        """
        import json

        export_data = {
            'exported_at': datetime.now().isoformat(),
            'stats': self.get_stats(),
            'semantic_facts': [
                {
                    'id': f.id,
                    'fact': f.fact,
                    'tags': f.tags,
                    'confidence': f.confidence,
                    'cognitive_weight': f.cognitive_weight
                }
                for f in self.semantic.facts
            ]
        }

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Memory exported to {output_path}")


# Singleton instance for global access
_memory_system: Optional[MemTierMemorySystem] = None


def get_memory_system(
    memory_dir: Optional[Path] = None,
    **kwargs
) -> MemTierMemorySystem:
    """
    Get or create the global memory system instance.

    Args:
        memory_dir: Base directory for memory storage
        **kwargs: Additional arguments for MemTierMemorySystem

    Returns:
        MemTierMemorySystem instance
    """
    global _memory_system

    if _memory_system is None:
        _memory_system = MemTierMemorySystem(memory_dir=memory_dir, **kwargs)

    return _memory_system


# Convenience functions for common operations
def log_user_input(session_id: str, project: str, content: str) -> str:
    """Log user input to episodic memory."""
    memory = get_memory_system()
    return memory.log_event(session_id, project, "user_input", content)


def log_tool_call(
    session_id: str,
    project: str,
    tool_name: str,
    args: Dict[str, Any],
    result: Any
) -> str:
    """Log tool call to episodic memory."""
    memory = get_memory_system()
    content = f"Tool: {tool_name}, Args: {args}, Result: {result}"
    return memory.log_event(session_id, project, "tool_call", content)


def log_agent_response(session_id: str, project: str, content: str) -> str:
    """Log agent response to episodic memory."""
    memory = get_memory_system()
    return memory.log_event(session_id, project, "agent_response", content)


def search_memory(query: str, k: int = 10) -> List[Dict[str, Any]]:
    """Search across all memory tiers."""
    memory = get_memory_system()
    return memory.search(query, k=k)
