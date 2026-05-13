"""
Deep analysis engine for research sources.

Analyzes papers, repositories, and provides quality scoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import re


@dataclass
class PaperAnalysis:
    """Analysis of a research paper."""
    paper_id: str
    title: str

    # Methodology
    methodology: str = ""
    datasets_used: List[str] = field(default_factory=list)
    evaluation_metrics: List[str] = field(default_factory=list)

    # Results
    key_findings: List[str] = field(default_factory=list)
    performance_claims: List[str] = field(default_factory=list)

    # Quality indicators
    citation_count: int = 0
    author_h_index: float = 0.0
    venue_tier: str = ""  # A*, A, B, C
    reproducibility_score: float = 0.0

    # Critical evaluation
    strengths: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    potential_biases: List[str] = field(default_factory=list)

    # Metadata
    analyzed_at: datetime = field(default_factory=datetime.now)


@dataclass
class RepositoryAnalysis:
    """Analysis of a code repository."""
    repo_id: str
    full_name: str

    # Code quality
    code_quality_score: float = 0.0
    test_coverage: float = 0.0
    documentation_score: float = 0.0

    # Community health
    stars: int = 0
    forks: int = 0
    contributors: int = 0
    open_issues: int = 0
    last_commit_days: int = 0

    # Maintenance
    is_maintained: bool = True
    maintenance_score: float = 0.0

    # Features
    has_tests: bool = False
    has_ci: bool = False
    has_docs: bool = False
    has_license: bool = False

    # Critical evaluation
    strengths: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    # Metadata
    analyzed_at: datetime = field(default_factory=datetime.now)


@dataclass
class QualityScore:
    """Quality score for a research source."""
    overall: float  # 0.0-1.0
    relevance: float  # 0.0-1.0
    authority: float  # 0.0-1.0
    recency: float  # 0.0-1.0
    impact: float  # 0.0-1.0
    credibility: float  # 0.0-1.0

    def __post_init__(self):
        """Ensure scores are in valid range."""
        for field_name in ['overall', 'relevance', 'authority', 'recency', 'impact', 'credibility']:
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                setattr(self, field_name, max(0.0, min(1.0, value)))


class PaperAnalyzer:
    """Analyze research papers."""

    def analyze(self, paper_content: str, metadata: Dict) -> PaperAnalysis:
        """
        Analyze a research paper.

        Args:
            paper_content: Full text of the paper
            metadata: Paper metadata (title, authors, citations, etc.)

        Returns:
            Paper analysis
        """
        analysis = PaperAnalysis(
            paper_id=metadata.get('id', ''),
            title=metadata.get('title', ''),
            citation_count=metadata.get('citations', 0),
        )

        # Extract methodology
        analysis.methodology = self._extract_methodology(paper_content)

        # Extract datasets
        analysis.datasets_used = self._extract_datasets(paper_content)

        # Extract metrics
        analysis.evaluation_metrics = self._extract_metrics(paper_content)

        # Extract findings
        analysis.key_findings = self._extract_findings(paper_content)

        # Calculate reproducibility
        analysis.reproducibility_score = self._assess_reproducibility(paper_content)

        # Critical evaluation
        analysis.strengths = self._identify_strengths(paper_content, metadata)
        analysis.limitations = self._identify_limitations(paper_content)
        analysis.potential_biases = self._detect_biases(paper_content)

        return analysis

    def _extract_methodology(self, content: str) -> str:
        """Extract methodology section."""
        # Look for methodology section
        patterns = [
            r'(?:methodology|method|approach).*?(?=\n\n|\Z)',
            r'(?:we propose|we present|we introduce).*?(?=\.|;)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0)[:500]  # First 500 chars

        return ""

    def _extract_datasets(self, content: str) -> List[str]:
        """Extract dataset names."""
        # Common dataset patterns
        datasets = []

        # Look for explicit dataset mentions
        dataset_patterns = [
            r'(?:ImageNet|COCO|MNIST|CIFAR|SQuAD|GLUE|SuperGLUE)',
            r'(?:dataset|corpus):\s*([A-Z][A-Za-z0-9\-]+)',
        ]

        for pattern in dataset_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            datasets.extend(matches)

        return list(set(datasets))[:10]  # Top 10 unique

    def _extract_metrics(self, content: str) -> List[str]:
        """Extract evaluation metrics."""
        metrics = []

        # Common metrics
        metric_patterns = [
            r'(?:accuracy|precision|recall|F1|BLEU|ROUGE|perplexity|AUC)',
            r'(?:top-[0-9]|mAP|IoU|PSNR|SSIM)',
        ]

        for pattern in metric_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            metrics.extend(matches)

        return list(set(metrics))[:10]

    def _extract_findings(self, content: str) -> List[str]:
        """Extract key findings."""
        findings = []

        # Look for result statements
        result_patterns = [
            r'(?:we find|we show|we demonstrate|results show).*?(?=\.|;)',
            r'(?:achieves?|outperforms?|improves?).*?(?=\.|;)',
        ]

        for pattern in result_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            findings.extend(matches[:3])  # Top 3 per pattern

        return findings[:5]  # Top 5 overall

    def _assess_reproducibility(self, content: str) -> float:
        """Assess reproducibility based on content."""
        score = 0.0

        # Check for code availability
        if re.search(r'(?:code|implementation).*?(?:available|github|repository)', content, re.IGNORECASE):
            score += 0.3

        # Check for hyperparameters
        if re.search(r'(?:hyperparameter|learning rate|batch size)', content, re.IGNORECASE):
            score += 0.2

        # Check for dataset details
        if re.search(r'(?:dataset|training set|test set).*?(?:split|size|samples)', content, re.IGNORECASE):
            score += 0.2

        # Check for experimental setup
        if re.search(r'(?:experimental setup|implementation details|training procedure)', content, re.IGNORECASE):
            score += 0.3

        return min(score, 1.0)

    def _identify_strengths(self, content: str, metadata: Dict) -> List[str]:
        """Identify paper strengths."""
        strengths = []

        # High citation count
        if metadata.get('citations', 0) > 100:
            strengths.append(f"Highly cited ({metadata['citations']} citations)")

        # Novel approach
        if re.search(r'(?:novel|new|first|original)', content, re.IGNORECASE):
            strengths.append("Claims novelty")

        # Strong results
        if re.search(r'(?:state-of-the-art|SOTA|outperform|best)', content, re.IGNORECASE):
            strengths.append("Claims strong performance")

        # Comprehensive evaluation
        if re.search(r'(?:extensive|comprehensive|thorough).*?(?:evaluation|experiments)', content, re.IGNORECASE):
            strengths.append("Comprehensive evaluation")

        return strengths[:5]

    def _identify_limitations(self, content: str) -> List[str]:
        """Identify paper limitations."""
        limitations = []

        # Look for limitation section
        limitation_match = re.search(
            r'(?:limitation|weakness|drawback).*?(?=\n\n|\Z)',
            content,
            re.IGNORECASE | re.DOTALL
        )

        if limitation_match:
            limitations.append(limitation_match.group(0)[:200])

        # Look for caveats
        caveat_patterns = [
            r'(?:however|but|although).*?(?=\.|;)',
            r'(?:does not|cannot|unable to).*?(?=\.|;)',
        ]

        for pattern in caveat_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            limitations.extend(matches[:2])

        return limitations[:5]

    def _detect_biases(self, content: str) -> List[str]:
        """Detect potential biases."""
        biases = []

        # Dataset bias
        if re.search(r'(?:English|Western|WEIRD)', content, re.IGNORECASE):
            biases.append("Potential dataset bias (English/Western-centric)")

        # Evaluation bias
        if not re.search(r'(?:baseline|comparison|prior work)', content, re.IGNORECASE):
            biases.append("Limited baseline comparisons")

        # Generalization concerns
        if re.search(r'(?:specific|particular|limited).*?(?:domain|dataset|setting)', content, re.IGNORECASE):
            biases.append("Limited generalization claims")

        return biases[:3]


class RepositoryAnalyzer:
    """Analyze code repositories."""

    def analyze(self, repo_metadata: Dict, readme_content: Optional[str] = None) -> RepositoryAnalysis:
        """
        Analyze a code repository.

        Args:
            repo_metadata: Repository metadata from GitHub API
            readme_content: Optional README content

        Returns:
            Repository analysis
        """
        analysis = RepositoryAnalysis(
            repo_id=str(repo_metadata.get('id', '')),
            full_name=repo_metadata.get('full_name', ''),
            stars=repo_metadata.get('stars', 0),
            forks=repo_metadata.get('forks', 0),
            open_issues=repo_metadata.get('open_issues', 0),
        )

        # Analyze features
        analysis.has_license = bool(repo_metadata.get('license'))
        analysis.has_docs = self._has_documentation(repo_metadata, readme_content)
        analysis.has_tests = self._has_tests(repo_metadata)
        analysis.has_ci = self._has_ci(repo_metadata)

        # Calculate scores
        analysis.code_quality_score = self._calculate_code_quality(repo_metadata, readme_content)
        analysis.documentation_score = self._calculate_doc_score(readme_content)
        analysis.maintenance_score = self._calculate_maintenance_score(repo_metadata)
        analysis.is_maintained = analysis.maintenance_score > 0.5

        # Critical evaluation
        analysis.strengths = self._identify_repo_strengths(analysis, repo_metadata)
        analysis.limitations = self._identify_repo_limitations(analysis, repo_metadata)

        return analysis

    def _has_documentation(self, metadata: Dict, readme: Optional[str]) -> bool:
        """Check if repo has documentation."""
        if readme and len(readme) > 500:
            return True
        return metadata.get('has_wiki', False) or metadata.get('has_pages', False)

    def _has_tests(self, metadata: Dict) -> bool:
        """Check if repo has tests (heuristic)."""
        # Would need to fetch repo contents for accurate check
        # For now, use language as proxy
        language = metadata.get('language', '').lower()
        return language in ['python', 'javascript', 'typescript', 'java', 'go', 'rust']

    def _has_ci(self, metadata: Dict) -> bool:
        """Check if repo has CI (heuristic)."""
        # Would need to check for .github/workflows or similar
        # For now, assume popular repos have CI
        return metadata.get('stars', 0) > 100

    def _calculate_code_quality(self, metadata: Dict, readme: Optional[str]) -> float:
        """Calculate code quality score."""
        score = 0.0

        # Stars indicate quality
        stars = metadata.get('stars', 0)
        if stars > 1000:
            score += 0.3
        elif stars > 100:
            score += 0.2
        elif stars > 10:
            score += 0.1

        # License
        if metadata.get('license'):
            score += 0.2

        # README quality
        if readme and len(readme) > 1000:
            score += 0.2

        # Recent activity
        if metadata.get('last_commit_days', 365) < 30:
            score += 0.3

        return min(score, 1.0)

    def _calculate_doc_score(self, readme: Optional[str]) -> float:
        """Calculate documentation score."""
        if not readme:
            return 0.0

        score = 0.0

        # Length
        if len(readme) > 2000:
            score += 0.3
        elif len(readme) > 500:
            score += 0.2

        # Installation instructions
        if re.search(r'(?:install|setup|getting started)', readme, re.IGNORECASE):
            score += 0.2

        # Usage examples
        if re.search(r'(?:usage|example|quickstart)', readme, re.IGNORECASE):
            score += 0.2

        # API documentation
        if re.search(r'(?:API|documentation|reference)', readme, re.IGNORECASE):
            score += 0.2

        # Code blocks
        if '```' in readme or '    ' in readme:
            score += 0.1

        return min(score, 1.0)

    def _calculate_maintenance_score(self, metadata: Dict) -> float:
        """Calculate maintenance score."""
        score = 0.0

        # Recent commits
        last_commit_days = metadata.get('last_commit_days', 365)
        if last_commit_days < 30:
            score += 0.4
        elif last_commit_days < 90:
            score += 0.3
        elif last_commit_days < 180:
            score += 0.2
        elif last_commit_days < 365:
            score += 0.1

        # Low open issues
        open_issues = metadata.get('open_issues', 0)
        stars = metadata.get('stars', 1)
        issue_ratio = open_issues / max(stars, 1)
        if issue_ratio < 0.1:
            score += 0.3
        elif issue_ratio < 0.2:
            score += 0.2
        elif issue_ratio < 0.3:
            score += 0.1

        # Active contributors
        if metadata.get('contributors', 0) > 10:
            score += 0.3
        elif metadata.get('contributors', 0) > 5:
            score += 0.2
        elif metadata.get('contributors', 0) > 1:
            score += 0.1

        return min(score, 1.0)

    def _identify_repo_strengths(self, analysis: RepositoryAnalysis, metadata: Dict) -> List[str]:
        """Identify repository strengths."""
        strengths = []

        if analysis.stars > 1000:
            strengths.append(f"Highly popular ({analysis.stars} stars)")

        if analysis.has_license:
            strengths.append("Open source license")

        if analysis.documentation_score > 0.7:
            strengths.append("Well documented")

        if analysis.maintenance_score > 0.7:
            strengths.append("Actively maintained")

        if analysis.has_ci:
            strengths.append("Has CI/CD")

        return strengths

    def _identify_repo_limitations(self, analysis: RepositoryAnalysis, metadata: Dict) -> List[str]:
        """Identify repository limitations."""
        limitations = []

        if not analysis.has_license:
            limitations.append("No license specified")

        if analysis.documentation_score < 0.3:
            limitations.append("Limited documentation")

        if not analysis.is_maintained:
            limitations.append("Not actively maintained")

        if analysis.open_issues > 100:
            limitations.append(f"Many open issues ({analysis.open_issues})")

        return limitations


class QualityScorer:
    """Calculate quality scores for research sources."""

    def score_paper(self, paper_analysis: PaperAnalysis, query: str) -> QualityScore:
        """
        Score a paper's quality.

        Args:
            paper_analysis: Paper analysis
            query: Original search query

        Returns:
            Quality score
        """
        # Relevance (based on title match)
        relevance = self._calculate_relevance(paper_analysis.title, query)

        # Authority (based on citations)
        authority = min(paper_analysis.citation_count / 1000.0, 1.0)

        # Recency (papers from last 2 years get full score)
        recency = 1.0  # Would need publication date

        # Impact (based on citations and venue)
        impact = authority  # Simplified

        # Credibility (based on reproducibility)
        credibility = paper_analysis.reproducibility_score

        # Overall (weighted average)
        overall = (
            0.3 * relevance +
            0.2 * authority +
            0.1 * recency +
            0.2 * impact +
            0.2 * credibility
        )

        return QualityScore(
            overall=overall,
            relevance=relevance,
            authority=authority,
            recency=recency,
            impact=impact,
            credibility=credibility,
        )

    def score_repository(self, repo_analysis: RepositoryAnalysis, query: str) -> QualityScore:
        """
        Score a repository's quality.

        Args:
            repo_analysis: Repository analysis
            query: Original search query

        Returns:
            Quality score
        """
        # Relevance (based on name match)
        relevance = self._calculate_relevance(repo_analysis.full_name, query)

        # Authority (based on stars)
        authority = min(repo_analysis.stars / 10000.0, 1.0)

        # Recency (based on last commit)
        recency = max(0.0, 1.0 - repo_analysis.last_commit_days / 365.0)

        # Impact (based on stars and forks)
        impact = min((repo_analysis.stars + repo_analysis.forks * 2) / 15000.0, 1.0)

        # Credibility (based on code quality and maintenance)
        credibility = (repo_analysis.code_quality_score + repo_analysis.maintenance_score) / 2.0

        # Overall
        overall = (
            0.3 * relevance +
            0.2 * authority +
            0.1 * recency +
            0.2 * impact +
            0.2 * credibility
        )

        return QualityScore(
            overall=overall,
            relevance=relevance,
            authority=authority,
            recency=recency,
            impact=impact,
            credibility=credibility,
        )

    def _calculate_relevance(self, text: str, query: str) -> float:
        """Calculate relevance score."""
        text_lower = text.lower()
        query_lower = query.lower()
        query_terms = query_lower.split()

        # Count matching terms
        matches = sum(1 for term in query_terms if term in text_lower)

        return matches / len(query_terms) if query_terms else 0.0
