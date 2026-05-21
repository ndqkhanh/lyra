"""
Importance scoring system for memory records.

Implements multi-dimensional importance scoring to determine which memories
should be retained, strengthened, or pruned. Based on research from Auto-Dreamer
and cognitive psychology principles.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from lyra_memory.schema import MemoryType


class ImportanceCategory(str, Enum):
    """Categories for base importance scoring."""
    CRITICAL = "critical"  # User preferences, settings, identity
    HIGH = "high"  # Factual knowledge, decisions, outcomes
    MEDIUM = "medium"  # Task context, intermediate results
    LOW = "low"  # Casual conversation, acknowledgments
    NOISE = "noise"  # Greetings, filler, redundant info


@dataclass
class ImportanceScore:
    """
    Multi-dimensional importance score for a memory.
    
    Attributes:
        base_score: Base importance (0.0-1.0) from category
        emotional_salience: Boost from emotional content (0.0-0.3)
        user_flag_boost: Boost from explicit user marking (0.0-0.2)
        recency_boost: Temporary boost for recent memories (0.0-0.1)
        final_score: Combined importance score (0.0-1.0)
        category: Assigned importance category
    """
    base_score: float
    emotional_salience: float = 0.0
    user_flag_boost: float = 0.0
    recency_boost: float = 0.0
    final_score: float = 0.0
    category: ImportanceCategory = ImportanceCategory.MEDIUM
    
    def __post_init__(self):
        """Calculate final score after initialization."""
        self.final_score = min(1.0, max(0.0,
            self.base_score + 
            self.emotional_salience + 
            self.user_flag_boost + 
            self.recency_boost
        ))


class ImportanceScorer:
    """
    Scores memory importance using multiple dimensions.
    
    Scoring dimensions:
    1. Semantic importance (category-based)
    2. Emotional salience (frustration, satisfaction)
    3. User flags (explicit "remember this")
    4. Recency (temporary boost for new memories)
    """
    
    # Base scores by memory type
    TYPE_BASE_SCORES: Dict[MemoryType, float] = {
        MemoryType.PREFERENCE: 0.95,  # User preferences are critical
        MemoryType.PROCEDURAL: 0.85,  # Workflows are important
        MemoryType.SEMANTIC: 0.75,    # Facts are valuable
        MemoryType.FAILURE: 0.80,     # Learn from mistakes
        MemoryType.EPISODIC: 0.50,    # Events vary in importance
    }
    
    # Emotional keywords and their salience scores
    EMOTIONAL_KEYWORDS: Dict[str, float] = {
        # Frustration/confusion (high salience)
        "frustrated": 0.25,
        "confused": 0.25,
        "stuck": 0.25,
        "error": 0.20,
        "failed": 0.20,
        "broken": 0.20,
        "bug": 0.15,
        "issue": 0.15,
        "problem": 0.15,
        
        # Satisfaction (medium salience)
        "works": 0.15,
        "fixed": 0.15,
        "solved": 0.15,
        "success": 0.15,
        "great": 0.10,
        "perfect": 0.10,
        "excellent": 0.10,
        
        # Critical actions (high salience)
        "important": 0.25,
        "critical": 0.30,
        "urgent": 0.25,
        "remember": 0.30,
        "don't forget": 0.30,
        "must": 0.20,
        "always": 0.15,
        "never": 0.15,
    }
    
    # Content patterns for category classification
    CATEGORY_PATTERNS: Dict[ImportanceCategory, list[str]] = {
        ImportanceCategory.CRITICAL: [
            "my name is",
            "i prefer",
            "i like",
            "i hate",
            "i want",
            "always use",
            "never use",
            "remember that i",
        ],
        ImportanceCategory.HIGH: [
            "the project uses",
            "we decided to",
            "the architecture",
            "the database",
            "production",
            "deployment",
            "security",
        ],
        ImportanceCategory.LOW: [
            "thanks",
            "thank you",
            "ok",
            "okay",
            "sure",
            "got it",
            "understood",
        ],
        ImportanceCategory.NOISE: [
            "hello",
            "hi",
            "hey",
            "bye",
            "goodbye",
        ],
    }
    
    def __init__(self):
        """Initialize the importance scorer."""
        pass
    
    def score(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[Dict] = None,
        created_at: Optional[datetime] = None,
    ) -> ImportanceScore:
        """
        Score the importance of a memory.
        
        Args:
            content: Memory content text
            memory_type: Type of memory
            metadata: Optional metadata (may contain user_flagged=True)
            created_at: When memory was created (for recency boost)
            
        Returns:
            ImportanceScore with all dimensions calculated
        """
        metadata = metadata or {}
        
        # 1. Base score from memory type
        base_score = self.TYPE_BASE_SCORES.get(memory_type, 0.5)
        
        # 2. Classify content into category
        category = self._classify_content(content)
        
        # Adjust base score by category (override if category is more specific)
        category_adjustments = {
            ImportanceCategory.CRITICAL: 0.95,
            ImportanceCategory.HIGH: 0.80,
            ImportanceCategory.MEDIUM: 0.60,
            ImportanceCategory.LOW: 0.30,
            ImportanceCategory.NOISE: 0.10,
        }
        # For NOISE and LOW, use category score instead of max
        if category in (ImportanceCategory.NOISE, ImportanceCategory.LOW):
            base_score = category_adjustments[category]
        else:
            base_score = max(base_score, category_adjustments[category])
        
        # 3. Emotional salience
        emotional_salience = self._detect_emotional_salience(content)
        
        # 4. User flag boost
        user_flag_boost = 0.2 if metadata.get("user_flagged") else 0.0
        
        # 5. Recency boost (decays over 24 hours)
        recency_boost = self._calculate_recency_boost(created_at)
        
        return ImportanceScore(
            base_score=base_score,
            emotional_salience=emotional_salience,
            user_flag_boost=user_flag_boost,
            recency_boost=recency_boost,
            category=category,
        )
    
    def _classify_content(self, content: str) -> ImportanceCategory:
        """Classify content into importance category."""
        content_lower = content.lower()
        
        # Check patterns in priority order
        for category in [
            ImportanceCategory.CRITICAL,
            ImportanceCategory.NOISE,
            ImportanceCategory.LOW,
            ImportanceCategory.HIGH,
        ]:
            patterns = self.CATEGORY_PATTERNS.get(category, [])
            if any(pattern in content_lower for pattern in patterns):
                return category
        
        # Default to medium
        return ImportanceCategory.MEDIUM
    
    def _detect_emotional_salience(self, content: str) -> float:
        """Detect emotional salience from content."""
        content_lower = content.lower()
        
        max_salience = 0.0
        for keyword, salience in self.EMOTIONAL_KEYWORDS.items():
            if keyword in content_lower:
                max_salience = max(max_salience, salience)
        
        return min(0.3, max_salience)  # Cap at 0.3
    
    def _calculate_recency_boost(self, created_at: Optional[datetime]) -> float:
        """Calculate recency boost (decays over 24 hours)."""
        if not created_at:
            return 0.0
        
        now = datetime.now()
        age_hours = (now - created_at).total_seconds() / 3600
        
        # Exponential decay over 24 hours
        if age_hours < 0:
            return 0.0
        elif age_hours > 24:
            return 0.0
        else:
            # Boost from 0.1 (fresh) to 0.0 (24h old)
            return 0.1 * (1 - age_hours / 24)


__all__ = [
    "ImportanceCategory",
    "ImportanceScore",
    "ImportanceScorer",
]
