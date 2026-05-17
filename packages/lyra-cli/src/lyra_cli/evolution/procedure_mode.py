"""Procedure mode for editing Python evolution code."""
from pathlib import Path
from typing import Optional


class ProcedureMode:
    """Enable meta-agent to edit Python evolution code."""

    def __init__(self, procedures_dir: Path):
        self.procedures_dir = Path(procedures_dir)
        self.procedures_dir.mkdir(parents=True, exist_ok=True)

    def read_procedure(self, name: str) -> Optional[str]:
        """Read a procedure file."""
        path = self.procedures_dir / f"{name}.py"
        if path.exists():
            return path.read_text()
        return None

    def write_procedure(self, name: str, content: str) -> bool:
        """Write a procedure file."""
        path = self.procedures_dir / f"{name}.py"
        try:
            path.write_text(content)
            return True
        except Exception:
            return False

    def validate_syntax(self, content: str) -> tuple[bool, str]:
        """Validate Python syntax."""
        try:
            compile(content, "<string>", "exec")
            return True, "Valid"
        except SyntaxError as e:
            return False, str(e)
