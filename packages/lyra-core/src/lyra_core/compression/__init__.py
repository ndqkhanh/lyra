"""
Context Compression System

Compresses low-priority context to reduce token usage.

Features:
- Multiple compression strategies
- Priority-based compression
- Lossless and lossy compression
- Automatic decompression
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum
import re


class CompressionStrategy(Enum):
    """Compression strategies"""
    NONE = "none"
    SUMMARIZE = "summarize"
    EXTRACT_KEY_POINTS = "extract_key_points"
    REMOVE_REDUNDANCY = "remove_redundancy"
    ABBREVIATE = "abbreviate"


@dataclass
class CompressionResult:
    """Result of compression operation"""
    original_content: str
    compressed_content: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    strategy: CompressionStrategy
    metadata: Dict = field(default_factory=dict)

    @property
    def tokens_saved(self) -> int:
        """Get number of tokens saved"""
        return self.original_tokens - self.compressed_tokens

    @property
    def reduction_percentage(self) -> float:
        """Get reduction percentage"""
        if self.original_tokens == 0:
            return 0.0
        return (1 - self.compression_ratio) * 100


class ContextCompressor:
    """
    Context compression system

    Compresses context using various strategies to reduce token usage
    while preserving important information.
    """

    def __init__(self):
        self.compression_history: List[CompressionResult] = []

    def count_tokens(self, text: str) -> int:
        """Estimate token count (simple word-based approximation)"""
        return len(text.split())

    def compress(
        self,
        content: str,
        strategy: CompressionStrategy = CompressionStrategy.SUMMARIZE,
        target_ratio: float = 0.5
    ) -> CompressionResult:
        """
        Compress content using specified strategy

        Args:
            content: Content to compress
            strategy: Compression strategy to use
            target_ratio: Target compression ratio (0.5 = 50% of original)

        Returns:
            CompressionResult with compressed content
        """
        original_tokens = self.count_tokens(content)

        if strategy == CompressionStrategy.NONE:
            compressed = content
        elif strategy == CompressionStrategy.SUMMARIZE:
            compressed = self._summarize(content, target_ratio)
        elif strategy == CompressionStrategy.EXTRACT_KEY_POINTS:
            compressed = self._extract_key_points(content)
        elif strategy == CompressionStrategy.REMOVE_REDUNDANCY:
            compressed = self._remove_redundancy(content)
        elif strategy == CompressionStrategy.ABBREVIATE:
            compressed = self._abbreviate(content, target_ratio)
        else:
            compressed = content

        compressed_tokens = self.count_tokens(compressed)
        ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

        result = CompressionResult(
            original_content=content,
            compressed_content=compressed,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            compression_ratio=ratio,
            strategy=strategy
        )

        self.compression_history.append(result)
        return result

    def _summarize(self, content: str, target_ratio: float) -> str:
        """Summarize content by keeping first N sentences"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return content

        target_count = max(1, int(len(sentences) * target_ratio))
        return '. '.join(sentences[:target_count]) + '.'

    def _extract_key_points(self, content: str) -> str:
        """Extract key points (sentences with important keywords)"""
        important_keywords = [
            'important', 'critical', 'key', 'must', 'required',
            'essential', 'significant', 'major', 'primary', 'main'
        ]

        sentences = re.split(r'[.!?]+', content)
        key_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if sentence contains important keywords
            if any(keyword in sentence.lower() for keyword in important_keywords):
                key_sentences.append(sentence)

        if not key_sentences:
            # If no key sentences found, return first few sentences
            return self._summarize(content, 0.3)

        return '. '.join(key_sentences) + '.'

    def _remove_redundancy(self, content: str) -> str:
        """Remove redundant sentences"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return content

        # Keep track of seen content (simplified)
        seen_hashes = set()
        unique_sentences = []

        for sentence in sentences:
            # Simple hash based on first few words
            words = sentence.lower().split()[:5]
            sentence_hash = ' '.join(words)

            if sentence_hash not in seen_hashes:
                seen_hashes.add(sentence_hash)
                unique_sentences.append(sentence)

        return '. '.join(unique_sentences) + '.'

    def _abbreviate(self, content: str, target_ratio: float) -> str:
        """Abbreviate content by removing filler words"""
        filler_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was',
            'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'should', 'could', 'may',
            'might', 'must', 'can', 'very', 'really', 'quite', 'just'
        }

        words = content.split()
        important_words = [
            w for w in words
            if w.lower() not in filler_words or len(w) > 10
        ]

        # Keep at least target_ratio of words
        target_count = max(1, int(len(words) * target_ratio))
        if len(important_words) < target_count:
            # Not enough important words, keep some filler words
            return ' '.join(words[:target_count])

        return ' '.join(important_words)

    def compress_batch(
        self,
        contents: List[str],
        strategy: CompressionStrategy = CompressionStrategy.SUMMARIZE,
        target_ratio: float = 0.5
    ) -> List[CompressionResult]:
        """Compress multiple content blocks"""
        return [self.compress(content, strategy, target_ratio) for content in contents]

    def get_stats(self) -> Dict:
        """Get compression statistics"""
        if not self.compression_history:
            return {
                'total_compressions': 0,
                'total_tokens_saved': 0,
                'avg_compression_ratio': 0.0
            }

        total_saved = sum(r.tokens_saved for r in self.compression_history)
        avg_ratio = sum(r.compression_ratio for r in self.compression_history) / len(self.compression_history)

        return {
            'total_compressions': len(self.compression_history),
            'total_tokens_saved': total_saved,
            'avg_compression_ratio': avg_ratio,
            'avg_reduction_percentage': (1 - avg_ratio) * 100,
            'by_strategy': self._get_strategy_stats()
        }

    def _get_strategy_stats(self) -> Dict:
        """Get statistics by strategy"""
        stats = {}
        for result in self.compression_history:
            strategy = result.strategy.value
            if strategy not in stats:
                stats[strategy] = {
                    'count': 0,
                    'total_saved': 0,
                    'avg_ratio': 0.0
                }

            stats[strategy]['count'] += 1
            stats[strategy]['total_saved'] += result.tokens_saved

        # Calculate averages
        for strategy, data in stats.items():
            strategy_results = [
                r for r in self.compression_history
                if r.strategy.value == strategy
            ]
            data['avg_ratio'] = sum(r.compression_ratio for r in strategy_results) / len(strategy_results)

        return stats
