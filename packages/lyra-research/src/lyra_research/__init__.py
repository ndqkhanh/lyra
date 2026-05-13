"""
Lyra Research - Deep Research Agent

Multi-source research discovery, analysis, and synthesis.
"""

from lyra_research.discovery import (
    ArXivDiscovery,
    GitHubDiscovery,
    MultiSourceDiscovery,
    ResearchSource,
    SemanticScholarDiscovery,
    SourceType,
)
from lyra_research.fetchers import ContentFetcher, ParsedContent, PDFExtractor, READMEParser, WebScraper
from lyra_research.analysis import (
    PaperAnalysis,
    PaperAnalyzer,
    QualityScore,
    QualityScorer,
    RepositoryAnalysis,
    RepositoryAnalyzer,
)

__version__ = "0.1.0"

__all__ = [
    "ArXivDiscovery",
    "GitHubDiscovery",
    "SemanticScholarDiscovery",
    "MultiSourceDiscovery",
    "ResearchSource",
    "SourceType",
    "ContentFetcher",
    "ParsedContent",
    "PDFExtractor",
    "READMEParser",
    "WebScraper",
    "PaperAnalysis",
    "PaperAnalyzer",
    "RepositoryAnalysis",
    "RepositoryAnalyzer",
    "QualityScore",
    "QualityScorer",
]
