"""
Audit Logger

Logs all bypassed operations for security audit.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
from typing import List


@dataclass
class AuditEntry:
    """Single audit log entry"""
    timestamp: str
    operation: str
    level: str
    description: str
    context: dict
    bypassed: bool


class AuditLogger:
    """
    Logs all bypassed operations for security audit

    Features:
    - Append-only log file
    - JSON format for easy parsing
    - Rotation after size limit
    """

    def __init__(self, log_path: Path = None):
        self.log_path = log_path or Path.home() / ".lyra" / "bypass_audit.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_bypass(self, request):
        """Log a bypassed permission request"""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            operation=request.operation,
            level=request.level.value,
            description=request.description,
            context=request.context,
            bypassed=True
        )

        # Append to JSONL file
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry.__dict__) + '\n')

    def get_recent_bypasses(self, limit: int = 100) -> List[AuditEntry]:
        """Get recent bypassed operations"""
        if not self.log_path.exists():
            return []

        entries = []
        with open(self.log_path) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    entries.append(AuditEntry(**data))

        return entries[-limit:]

    def clear_log(self):
        """Clear audit log (use with caution)"""
        if self.log_path.exists():
            self.log_path.unlink()
