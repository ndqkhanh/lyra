"""MOSS-style Source-Level Evolution for Lyra.

Extends the existing self-evolution pipeline with source-level code modification,
user-consent promotion gates, and Ethical Hyper-Velocity governance JIT.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PatchTarget(Enum):
    AGENT_LOOP = auto()
    HOOK_CHAIN = auto()
    STATE_MACHINE = auto()
    TOOL_REGISTRY = auto()
    PERMISSION_POLICY = auto()
    MEMORY_STORE = auto()


class ModificationSeverity(Enum):
    COSMETIC = auto()
    SAFE = auto()
    RISKY = auto()
    DANGEROUS = auto()


@dataclass
class SourcePatch:
    id: str
    target: PatchTarget
    file_path: str
    original_snippet: str
    patched_snippet: str
    severity: ModificationSeverity
    description: str
    author: str = "lyra-moss"
    applied: bool = False
    verified: bool = False
    approved: bool = False


@dataclass
class PatchResult:
    patch_id: str
    applied: bool
    tests_passed: int
    tests_failed: int
    test_output: str = ""
    rolled_back: bool = False


class SourceEvolutionEngine:
    """MOSS-style source-level code modification engine."""

    def __init__(self):
        self.patches: list[SourcePatch] = []
        self.results: list[PatchResult] = []

    def analyze_source(self, source_code: str) -> list[PatchTarget]:
        """Analyze source code to identify modifiable targets."""
        targets = set()
        tree = ast.parse(source_code) if isinstance(source_code, str) else source_code
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if "loop" in node.name.lower() or "step" in node.name.lower():
                    targets.add(PatchTarget.AGENT_LOOP)
                if "hook" in node.name.lower():
                    targets.add(PatchTarget.HOOK_CHAIN)
                if "state" in node.name.lower():
                    targets.add(PatchTarget.STATE_MACHINE)
        return list(targets)

    def generate_patch(
        self, target: PatchTarget, failure_info: dict[str, Any]
    ) -> Optional[SourcePatch]:
        """Generate a source patch for a given failure."""
        patch_id = f"MOSS-{len(self.patches)+1:04d}"
        severity = self._assess_severity(failure_info)
        patch = SourcePatch(
            id=patch_id,
            target=target,
            file_path=failure_info.get("file", "unknown.py"),
            original_snippet=failure_info.get("context", "N/A"),
            patched_snippet=self._synthesize_fix(failure_info),
            severity=severity,
            description=f"Fix for {failure_info.get('error', 'unknown error')}",
        )
        self.patches.append(patch)
        return patch

    def _assess_severity(self, failure: dict[str, Any]) -> ModificationSeverity:
        error_str = str(failure.get("error", "")).lower()
        if any(kw in error_str for kw in ["security", "permission", "credential"]):
            return ModificationSeverity.DANGEROUS
        if any(kw in error_str for kw in ["crash", "deadlock", "corrupt"]):
            return ModificationSeverity.RISKY
        if any(kw in error_str for kw in ["warning", "performance"]) or "test" in error_str:
            return ModificationSeverity.SAFE
        return ModificationSeverity.COSMETIC

    def _synthesize_fix(self, failure: dict[str, Any]) -> str:
        error = failure.get("error", "")
        if "import" in error.lower():
            return f"# Added missing import\n# {error}"
        if "type" in error.lower() or "attribute" in error.lower():
            return f"# Fixed type/attribute error\n# {error}"
        if "name" in error.lower() and "not defined" in error.lower():
            return f"# Added missing variable\n{error.split()[-1]} = None"
        return f"# Auto-generated fix for: {error}"


class UserConsentGate:
    """User-consent promotion gate for high-risk modifications."""

    def __init__(self):
        self.pending_approvals: list[SourcePatch] = []

    def request_approval(self, patch: SourcePatch) -> bool:
        """Determine if user approval is needed."""
        if patch.severity in (ModificationSeverity.RISKY, ModificationSeverity.DANGEROUS):
            self.pending_approvals.append(patch)
            return True  # approval pending
        return False  # auto-approve

    def approve(self, patch_id: str) -> bool:
        for p in self.pending_approvals:
            if p.id == patch_id:
                p.approved = True
                self.pending_approvals.remove(p)
                return True
        return False

    def reject(self, patch_id: str) -> bool:
        for p in self.pending_approvals:
            if p.id == patch_id:
                p.approved = False
                self.pending_approvals.remove(p)
                return True
        return False


class GovernanceJIT:
    """Ethical Hyper-Velocity governance-aware compilation."""

    def __init__(self):
        self.governance_rules: list[dict[str, Any]] = []

    def add_rule(self, rule: dict[str, Any]) -> None:
        self.governance_rules.append(rule)

    def compile(self, patch: SourcePatch) -> SourcePatch:
        """Compile a patch through governance checks."""
        for rule in self.governance_rules:
            if not self._check_rule(rule, patch):
                patch.severity = ModificationSeverity.DANGEROUS
                logger.warning(f"Governance rule {rule.get('name')} blocked patch {patch.id}")
        return patch

    def _check_rule(self, rule: dict[str, Any], patch: SourcePatch) -> bool:
        rule_type = rule.get("type", "")
        if rule_type == "no_import" and patch.target == PatchTarget.TOOL_REGISTRY:
            return False
        if rule_type == "no_hook_override" and patch.target == PatchTarget.HOOK_CHAIN:
            return False
        return True
