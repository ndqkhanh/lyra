"""
Synthesis agents for deep research.

Provides 4 specialized synthesis agents:
- CrossSourceSynthesizer: Synthesize findings across sources
- ContradictionDetector: Detect contradictions between sources
- EvidenceAuditor: Audit evidence quality and citation accuracy
- FalsificationChecker: Check for falsification attempts
"""

from lyra_research.agents.synthesis.synthesis_base import (
    SynthesisAgent,
    SynthesisResult,
)
from lyra_research.agents.synthesis.cross_source_synthesizer import (
    CrossSourceSynthesizerAgent,
)
from lyra_research.agents.synthesis.contradiction_detector import (
    ContradictionDetectorAgent,
)
from lyra_research.agents.synthesis.evidence_auditor import (
    EvidenceAuditorAgent,
)
from lyra_research.agents.synthesis.falsification_checker import (
    FalsificationCheckerAgent,
)

__all__ = [
    "SynthesisAgent",
    "SynthesisResult",
    "CrossSourceSynthesizerAgent",
    "ContradictionDetectorAgent",
    "EvidenceAuditorAgent",
    "FalsificationCheckerAgent",
]
