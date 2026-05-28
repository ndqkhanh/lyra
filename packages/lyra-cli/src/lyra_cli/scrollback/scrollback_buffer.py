"""Scrollback buffer - Conversation history with line limit"""

import os
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ScrollbackLine:
    """A single line in the scrollback buffer"""
    content: str
    timestamp: datetime
    line_type: str = "text"  # text, tool, error, system
    metadata: dict | None = None


class ScrollbackBuffer:
    """Manages conversation history with configurable line limit

    Features:
    - Store conversation lines with timestamps
    - Automatic pruning when limit exceeded
    - Save/load history to/from file
    - Search through history
    - Export history in various formats
    """

    def __init__(self, max_lines: int = 10000):
        """Initialize scrollback buffer

        Args:
            max_lines: Maximum number of lines to keep (default: 10,000)
        """
        self.max_lines = max_lines
        self.lines: list[ScrollbackLine] = []
        self.current_position = 0  # For scrolling through history

    def append(
        self,
        content: str,
        line_type: str = "text",
        metadata: dict | None = None
    ):
        """Append a line to the buffer

        Args:
            content: Line content
            line_type: Type of line (text, tool, error, system)
            metadata: Optional metadata dictionary
        """
        line = ScrollbackLine(
            content=content,
            timestamp=datetime.now(),
            line_type=line_type,
            metadata=metadata or {}
        )

        self.lines.append(line)

        # Prune if exceeded limit
        if len(self.lines) > self.max_lines:
            self._prune_oldest()

    def append_multiple(self, lines: list[str], line_type: str = "text"):
        """Append multiple lines at once

        Args:
            lines: List of line contents
            line_type: Type for all lines
        """
        for content in lines:
            self.append(content, line_type)

    def _prune_oldest(self):
        """Remove oldest lines to stay within limit"""
        excess = len(self.lines) - self.max_lines
        if excess > 0:
            self.lines = self.lines[excess:]

    def get_lines(
        self,
        start: int | None = None,
        end: int | None = None,
        line_type: str | None = None
    ) -> list[ScrollbackLine]:
        """Get lines from buffer

        Args:
            start: Start index (inclusive), None for beginning
            end: End index (exclusive), None for end
            line_type: Filter by line type, None for all

        Returns:
            List of ScrollbackLine objects
        """
        lines = self.lines[start:end]

        if line_type:
            lines = [line for line in lines if line.line_type == line_type]

        return lines

    def get_recent(self, count: int = 100) -> list[ScrollbackLine]:
        """Get most recent N lines

        Args:
            count: Number of recent lines to get

        Returns:
            List of most recent ScrollbackLine objects
        """
        return self.lines[-count:]

    def search(
        self,
        query: str,
        case_sensitive: bool = False,
        line_type: str | None = None
    ) -> list[tuple[int, ScrollbackLine]]:
        """Search for lines containing query

        Args:
            query: Search query
            case_sensitive: Whether search is case-sensitive
            line_type: Filter by line type

        Returns:
            List of (index, ScrollbackLine) tuples
        """
        results = []

        for i, line in enumerate(self.lines):
            # Filter by type if specified
            if line_type and line.line_type != line_type:
                continue

            # Search in content
            content = line.content
            search_query = query

            if not case_sensitive:
                content = content.lower()
                search_query = search_query.lower()

            if search_query in content:
                results.append((i, line))

        return results

    def clear(self):
        """Clear all lines from buffer"""
        self.lines = []
        self.current_position = 0

    def get_line_count(self) -> int:
        """Get total number of lines in buffer

        Returns:
            Number of lines
        """
        return len(self.lines)

    def get_line_count_by_type(self) -> dict[str, int]:
        """Get line counts by type

        Returns:
            Dictionary mapping line type to count
        """
        counts = {}
        for line in self.lines:
            counts[line.line_type] = counts.get(line.line_type, 0) + 1
        return counts

    def save_to_file(self, filepath: str, format: str = "text"):
        """Save buffer to file

        Args:
            filepath: Path to save file
            format: Output format (text, json, markdown)
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if format == "text":
            self._save_as_text(filepath)
        elif format == "json":
            self._save_as_json(filepath)
        elif format == "markdown":
            self._save_as_markdown(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _save_as_text(self, filepath: str):
        """Save as plain text file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for line in self.lines:
                timestamp = line.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] [{line.line_type}] {line.content}\n")

    def _save_as_json(self, filepath: str):
        """Save as JSON file"""
        import json

        data = []
        for line in self.lines:
            data.append({
                "content": line.content,
                "timestamp": line.timestamp.isoformat(),
                "line_type": line.line_type,
                "metadata": line.metadata
            })

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_as_markdown(self, filepath: str):
        """Save as Markdown file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Lyra Conversation History\n\n")

            current_type = None
            for line in self.lines:
                # Add section headers for type changes
                if line.line_type != current_type:
                    current_type = line.line_type
                    f.write(f"\n## {line.line_type.title()}\n\n")

                timestamp = line.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"**{timestamp}**: {line.content}\n\n")

    def load_from_file(self, filepath: str, format: str = "json"):
        """Load buffer from file

        Args:
            filepath: Path to load file
            format: Input format (json only for now)
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        if format == "json":
            self._load_from_json(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _load_from_json(self, filepath: str):
        """Load from JSON file"""
        import json

        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)

        self.lines = []
        for item in data:
            line = ScrollbackLine(
                content=item["content"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                line_type=item.get("line_type", "text"),
                metadata=item.get("metadata")
            )
            self.lines.append(line)

        # Prune if loaded data exceeds limit
        if len(self.lines) > self.max_lines:
            self._prune_oldest()

    def get_statistics(self) -> dict:
        """Get buffer statistics

        Returns:
            Dictionary with statistics
        """
        if not self.lines:
            return {
                "total_lines": 0,
                "by_type": {},
                "oldest": None,
                "newest": None,
                "capacity_used": 0.0
            }

        return {
            "total_lines": len(self.lines),
            "by_type": self.get_line_count_by_type(),
            "oldest": self.lines[0].timestamp.isoformat(),
            "newest": self.lines[-1].timestamp.isoformat(),
            "capacity_used": (len(self.lines) / self.max_lines) * 100
        }

    def export_range(
        self,
        start_time: datetime,
        end_time: datetime,
        filepath: str,
        format: str = "text"
    ):
        """Export lines within time range

        Args:
            start_time: Start timestamp
            end_time: End timestamp
            filepath: Output file path
            format: Output format
        """
        # Filter lines by time range
        filtered_lines = [
            line for line in self.lines
            if start_time <= line.timestamp <= end_time
        ]

        # Create temporary buffer with filtered lines
        temp_buffer = ScrollbackBuffer(max_lines=len(filtered_lines))
        temp_buffer.lines = filtered_lines

        # Save using existing save method
        temp_buffer.save_to_file(filepath, format)

    def get_context_window(
        self,
        center_index: int,
        before: int = 5,
        after: int = 5
    ) -> list[ScrollbackLine]:
        """Get lines around a specific index (context window)

        Args:
            center_index: Center line index
            before: Number of lines before center
            after: Number of lines after center

        Returns:
            List of lines in context window
        """
        start = max(0, center_index - before)
        end = min(len(self.lines), center_index + after + 1)

        return self.lines[start:end]


def main():
    """Test scrollback buffer"""
    buffer = ScrollbackBuffer(max_lines=100)

    print("Scrollback Buffer Test")
    print("=" * 40)
    print()

    # Add some lines
    buffer.append("User: Hello!", "text")
    buffer.append("Assistant: Hi there!", "text")
    buffer.append("Tool: Read file.txt", "tool")
    buffer.append("Error: File not found", "error")

    print("Added 4 lines")
    print(f"Total lines: {buffer.get_line_count()}")
    print()

    # Get statistics
    stats = buffer.get_statistics()
    print("Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()

    # Search
    results = buffer.search("file", case_sensitive=False)
    print(f"Search results for 'file': {len(results)} matches")
    for idx, line in results:
        print(f"  [{idx}] {line.content}")
    print()

    # Save to file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    buffer.save_to_file(filepath, format="json")
    print(f"Saved to: {filepath}")

    # Load from file
    buffer2 = ScrollbackBuffer()
    buffer2.load_from_file(filepath, format="json")
    print(f"Loaded {buffer2.get_line_count()} lines")

    # Cleanup
    os.unlink(filepath)


if __name__ == "__main__":
    main()
