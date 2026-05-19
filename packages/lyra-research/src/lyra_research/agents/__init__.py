"""
Specialized agents for Lyra Deep Research.

Discovery agents: ArXiv, Semantic Scholar, GitHub, Web, OpenReview, HuggingFace
Analysis agents: Paper analysis, Repo analysis, Citation analysis, Quality scoring
"""

from lyra_research.agents.discovery.discovery_base import DiscoveryAgent
from lyra_research.agents.analysis.analysis_base import AnalysisAgent

__all__ = ["DiscoveryAgent", "AnalysisAgent"]
