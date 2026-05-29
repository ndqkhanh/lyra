"""Discovery agents for parallel source discovery."""

from lyra_research.agents.discovery.arxiv_agent import ArxivAgent
from lyra_research.agents.discovery.discovery_base import DiscoveryAgent
from lyra_research.agents.discovery.github_agent import GithubAgent
from lyra_research.agents.discovery.huggingface_agent import HuggingFaceAgent
from lyra_research.agents.discovery.openreview_agent import OpenReviewAgent
from lyra_research.agents.discovery.semantic_scholar_agent import SemanticScholarAgent
from lyra_research.agents.discovery.web_agent import WebAgent

__all__ = [
    "DiscoveryAgent",
    "ArxivAgent",
    "SemanticScholarAgent",
    "GithubAgent",
    "WebAgent",
    "OpenReviewAgent",
    "HuggingFaceAgent",
]
