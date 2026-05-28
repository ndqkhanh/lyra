"""Reverse Engineer Skill — code analysis and decompilation support.

Analyzes compiled/obfuscated code for:
- Binary analysis patterns
- Obfuscation detection
- API usage reconstruction
- Control flow recovery
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ObfuscationType(StrEnum):
    NONE = "none"
    MINIFICATION = "minification"
    PACKING = "packing"
    ENCRYPTION = "encryption"
    CONTROL_FLOW = "control_flow"


@dataclass(frozen=True)
class CodeArtifact:
    type: str
    confidence: float
    description: str
    location: str


class ReverseEngineerSkill:
    """Analyzes code for obfuscation and reconstructs intent."""

    _OBFUSCATION_MARKERS = {
        ObfuscationType.PACKING: (r"eval\s*\(.*fromCharCode", r"base64\.decode", r"atob\("),
        ObfuscationType.ENCRYPTION: (r"AES\.decrypt", r"decrypt\s*\(", r"XOR.*key"),
        ObfuscationType.CONTROL_FLOW: (r"switch\s*\(.*true\)", r"while\s*\(true\).*switch"),
        ObfuscationType.MINIFICATION: (r"^var\s+[a-z]{1,2}=.{100,}$", r"function\s+[a-z]{1,2}\("),
    }

    def run(self, input_data: dict) -> dict:
        source = input_data.get("source", "")
        artifacts: list[CodeArtifact] = []

        detected_types: list[ObfuscationType] = []
        for obf_type, patterns in self._OBFUSCATION_MARKERS.items():
            import re
            for pattern in patterns:
                if re.search(pattern, source, re.IGNORECASE | re.MULTILINE):
                    detected_types.append(obf_type)
                    break

        import re
        api_calls = re.findall(r'(?:https?://|wss?://)[^\s"\'<>]+', source)
        for url in api_calls[:10]:
            artifacts.append(CodeArtifact("api_endpoint", 0.9,
                f"Network endpoint: {url}", url))

        string_literals = re.findall(r'"([^"]{20,})"', source)
        for s in string_literals[:5]:
            artifacts.append(CodeArtifact("string_literal", 0.7,
                f"Long string literal: {s[:80]}...", s[:80]))

        return {
            "obfuscation_detected": detected_types,
            "obfuscation_level": len(detected_types),
            "artifacts": [a.__dict__ for a in artifacts],
            "total_artifacts": len(artifacts),
        }
