"""
ECC Compatibility Layer

Provides compatibility between ECC and Lyra architectures.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ECCCompatibilityLayer:
    """Main compatibility layer for ECC integration."""

    def __init__(self, ecc_path: Optional[Path] = None):
        """
        Initialize ECC compatibility layer.

        Args:
            ecc_path: Path to ECC installation (defaults to ~/.claude)
        """
        self.ecc_path = ecc_path or Path.home() / ".claude"
        self.skills_path = self.ecc_path / "skills"
        self.agents_path = self.ecc_path / "agents"
        self.rules_path = self.ecc_path / "rules"
        self.hooks_path = self.ecc_path / "hooks"

        self.initialized = False
        self.compatibility_matrix = {}

    def initialize(self) -> bool:
        """
        Initialize compatibility layer.

        Returns:
            True if initialization successful
        """
        try:
            # Check if ECC paths exist
            if not self.ecc_path.exists():
                logger.warning(f"ECC path not found: {self.ecc_path}")
                return False

            # Build compatibility matrix
            self.compatibility_matrix = self._build_compatibility_matrix()

            self.initialized = True
            logger.info("ECC compatibility layer initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize ECC compatibility: {e}")
            return False

    def _build_compatibility_matrix(self) -> Dict:
        """Build compatibility matrix between ECC and Lyra."""
        matrix = {
            "skills": {
                "ecc_count": self._count_ecc_skills(),
                "lyra_compatible": True,
                "conversion_needed": True,
            },
            "agents": {
                "ecc_count": self._count_ecc_agents(),
                "lyra_compatible": True,
                "merge_strategy": "unified_registry",
            },
            "hooks": {
                "ecc_types": ["PreToolUse", "PostToolUse", "SessionStart", "SessionEnd", "Stop"],
                "lyra_compatible": True,
                "adapter_needed": True,
            },
            "rules": {
                "ecc_count": self._count_ecc_rules(),
                "lyra_compatible": True,
                "language_detection": True,
            },
        }
        return matrix

    def _count_ecc_skills(self) -> int:
        """Count ECC skills."""
        if not self.skills_path.exists():
            return 0
        return len(list(self.skills_path.glob("**/*.md")))

    def _count_ecc_agents(self) -> int:
        """Count ECC agents."""
        if not self.agents_path.exists():
            return 0
        return len(list(self.agents_path.glob("*.md")))

    def _count_ecc_rules(self) -> int:
        """Count ECC rules."""
        if not self.rules_path.exists():
            return 0
        return len(list(self.rules_path.glob("**/*.md")))

    def get_compatibility_report(self) -> Dict:
        """
        Get compatibility report.

        Returns:
            Dictionary with compatibility information
        """
        if not self.initialized:
            self.initialize()

        return {
            "initialized": self.initialized,
            "ecc_path": str(self.ecc_path),
            "matrix": self.compatibility_matrix,
            "status": "ready" if self.initialized else "not_ready",
        }
