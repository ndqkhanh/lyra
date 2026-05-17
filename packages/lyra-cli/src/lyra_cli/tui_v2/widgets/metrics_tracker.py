"""Per-operation metrics tracking."""
import time
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    op_type: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    tokens_in: int = 0
    tokens_out: int = 0
    model: str = ""

    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.tokens_in + self.tokens_out


class MetricsTracker:
    """Track tokens and time per operation like Claude Code.

    Example output: "3m 49s · ↑ 754 tokens · deepseek-chat"
    """

    def __init__(self):
        self.operations: Dict[str, OperationMetrics] = {}

    def start_operation(self, op_id: str, op_type: str) -> None:
        """Start tracking an operation."""
        self.operations[op_id] = OperationMetrics(op_type=op_type)

    def end_operation(
        self,
        op_id: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        model: str = "",
    ) -> None:
        """End tracking and record metrics."""
        if op_id in self.operations:
            op = self.operations[op_id]
            op.end_time = time.time()
            op.tokens_in = tokens_in
            op.tokens_out = tokens_out
            op.model = model

    def format_summary(self, op_id: str) -> str:
        """Format operation summary like Claude Code.

        Args:
            op_id: Operation ID to format

        Returns:
            Formatted string like "3m 49s · ↑ 754 tokens · deepseek-chat"
        """
        if op_id not in self.operations:
            return ""

        op = self.operations[op_id]
        duration = op.duration

        # Format duration
        if duration < 60:
            duration_str = f"{int(duration)}s"
        else:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            duration_str = f"{minutes}m {seconds}s"

        # Format tokens with direction arrow
        total_tokens = op.total_tokens
        if total_tokens > 0:
            # ↑ for output-heavy, ↓ for input-heavy
            arrow = "↑" if op.tokens_out > op.tokens_in else "↓"
            tokens_str = f"{arrow} {total_tokens:,} tokens"
        else:
            tokens_str = ""

        # Build summary
        parts = [duration_str]
        if tokens_str:
            parts.append(tokens_str)
        if op.model:
            parts.append(op.model)

        return " · ".join(parts)

    def get_operation(self, op_id: str) -> Optional[OperationMetrics]:
        """Get operation metrics."""
        return self.operations.get(op_id)

    def clear(self) -> None:
        """Clear all tracked operations."""
        self.operations.clear()
