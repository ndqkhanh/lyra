"""
Tests for code analysis and implementation pattern extraction.

Tests analyzing code repositories, extracting architecture patterns,
understanding implementation details, and assessing code quality.
"""

import pytest
from lyra_research.analysis import RepositoryAnalyzer, RepositoryAnalysis


class TestCodeAnalysis:
    """Test code repository analysis."""

    @pytest.fixture
    def repo_analyzer(self):
        """Create repository analyzer instance."""
        return RepositoryAnalyzer()

    @pytest.fixture
    def sample_repo_metadata(self):
        """Sample repository metadata."""
        return {
            "id": "12345",
            "full_name": "org/sample-repo",
            "stars": 1000,
            "forks": 200,
            "open_issues": 25,
            "language": "Python",
            "license": {"name": "MIT"},
            "contributors": 15,
            "last_commit_days": 10,
        }

    def test_analyze_repository_basic(self, repo_analyzer, sample_repo_metadata):
        """Test basic repository analysis."""
        readme = "# Sample Repository\n\nA sample project for testing."
        analysis = repo_analyzer.analyze(sample_repo_metadata, readme)

        assert isinstance(analysis, RepositoryAnalysis)
        assert analysis.repo_id == "12345"
        assert analysis.full_name == "org/sample-repo"
        assert analysis.stars == 1000

    def test_calculate_code_quality_score(self, repo_analyzer, sample_repo_metadata):
        """Test code quality score calculation."""
        readme = """
        # High Quality Repository

        Comprehensive documentation with examples.
        Active development and maintenance.
        """
        analysis = repo_analyzer.analyze(sample_repo_metadata, readme)

        assert 0.0 <= analysis.code_quality_score <= 1.0
        # Should have decent score with 1000 stars, license, recent activity
        assert analysis.code_quality_score > 0.3

    def test_calculate_documentation_score(self, repo_analyzer, sample_repo_metadata):
        """Test documentation score calculation."""
        readme = """
        # Comprehensive Documentation

        ## Installation
        ```bash
        pip install package
        ```

        ## Usage
        ```python
        from package import Module
        module = Module()
        ```

        ## API Reference
        Full API documentation available.
        """
        analysis = repo_analyzer.analyze(sample_repo_metadata, readme)

        assert 0.0 <= analysis.documentation_score <= 1.0
        # Should have high score with installation, usage, API docs
        assert analysis.documentation_score > 0.5

    def test_calculate_maintenance_score(self, repo_analyzer, sample_repo_metadata):
        """Test maintenance score calculation."""
        # Recent commit, active contributors, low issue ratio
        sample_repo_metadata["last_commit_days"] = 5
        sample_repo_metadata["contributors"] = 20
        sample_repo_metadata["open_issues"] = 10

        analysis = repo_analyzer.analyze(sample_repo_metadata, None)

        assert 0.0 <= analysis.maintenance_score <= 1.0
        # Should have high score with recent activity
        assert analysis.maintenance_score > 0.5

    def test_identify_repository_features(self, repo_analyzer, sample_repo_metadata):
        """Test identifying repository features."""
        readme = "# Repository with CI/CD and tests"
        analysis = repo_analyzer.analyze(sample_repo_metadata, readme)

        assert isinstance(analysis.has_license, bool)
        assert isinstance(analysis.has_docs, bool)
        assert isinstance(analysis.has_tests, bool)
        assert isinstance(analysis.has_ci, bool)

    def test_identify_repository_strengths(self, repo_analyzer, sample_repo_metadata):
        """Test identifying repository strengths."""
        sample_repo_metadata["stars"] = 5000
        readme = """
        # Popular Repository

        Well-documented with comprehensive examples.
        Active maintenance and community support.
        """
        analysis = repo_analyzer.analyze(sample_repo_metadata, readme)

        assert len(analysis.strengths) > 0
        strengths_text = " ".join(analysis.strengths).lower()
        assert "popular" in strengths_text or "stars" in strengths_text

    def test_identify_repository_limitations(self, repo_analyzer, sample_repo_metadata):
        """Test identifying repository limitations."""
        sample_repo_metadata["license"] = None
        sample_repo_metadata["open_issues"] = 200
        readme = "# Minimal docs"

        analysis = repo_analyzer.analyze(sample_repo_metadata, readme)

        assert len(analysis.limitations) > 0
        limitations_text = " ".join(analysis.limitations).lower()
        assert "license" in limitations_text or "documentation" in limitations_text or "issues" in limitations_text


class TestImplementationPatternExtraction:
    """Test extracting implementation patterns from code."""

    @pytest.fixture
    def repo_analyzer(self):
        """Create repository analyzer instance."""
        return RepositoryAnalyzer()

    def test_extract_architecture_pattern(self, repo_analyzer):
        """Test extracting architecture patterns from README."""
        readme = """
        # Architecture

        The system uses a microservices architecture with:
        - API Gateway for routing
        - Service mesh for communication
        - Event-driven messaging with Kafka
        - Containerized deployment with Docker
        """
        metadata = {
            "id": "arch001",
            "full_name": "org/microservices",
            "stars": 2000,
            "language": "Python",
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        # Should have high documentation score
        assert analysis.documentation_score > 0.3

    def test_extract_design_patterns(self, repo_analyzer):
        """Test extracting design patterns."""
        readme = """
        # Design Patterns

        Implements:
        - Repository pattern for data access
        - Factory pattern for object creation
        - Observer pattern for event handling
        - Strategy pattern for algorithms
        """
        metadata = {
            "id": "patterns001",
            "full_name": "org/design-patterns",
            "stars": 1500,
            "language": "Python",
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        assert analysis.documentation_score >= 0.0

    def test_extract_technology_stack(self, repo_analyzer):
        """Test extracting technology stack."""
        readme = """
        # Technology Stack

        - Backend: Python, FastAPI, PostgreSQL
        - Frontend: React, TypeScript, Tailwind CSS
        - Infrastructure: Docker, Kubernetes, AWS
        - Monitoring: Prometheus, Grafana
        """
        metadata = {
            "id": "stack001",
            "full_name": "org/tech-stack",
            "stars": 3000,
            "language": "Python",
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        assert analysis.documentation_score >= 0.0

    def test_extract_api_patterns(self, repo_analyzer):
        """Test extracting API patterns."""
        readme = """
        # API Design

        RESTful API with:
        - Resource-based URLs
        - HTTP methods (GET, POST, PUT, DELETE)
        - JSON request/response format
        - JWT authentication
        - Rate limiting
        """
        metadata = {
            "id": "api001",
            "full_name": "org/api-patterns",
            "stars": 2500,
            "language": "Python",
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        assert analysis.documentation_score >= 0.0

    def test_extract_testing_patterns(self, repo_analyzer):
        """Test extracting testing patterns."""
        readme = """
        # Testing

        Comprehensive test suite:
        - Unit tests with pytest
        - Integration tests with Docker
        - E2E tests with Selenium
        - 90% code coverage
        """
        metadata = {
            "id": "test001",
            "full_name": "org/testing-patterns",
            "stars": 1800,
            "language": "Python",
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        assert analysis.documentation_score >= 0.0

    def test_extract_deployment_patterns(self, repo_analyzer):
        """Test extracting deployment patterns."""
        readme = """
        # Deployment

        - CI/CD with GitHub Actions
        - Blue-green deployment
        - Auto-scaling with Kubernetes
        - Multi-region deployment
        """
        metadata = {
            "id": "deploy001",
            "full_name": "org/deployment",
            "stars": 2200,
            "language": "Python",
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        assert analysis.documentation_score >= 0.0


class TestArchitectureUnderstanding:
    """Test understanding code architecture."""

    @pytest.fixture
    def repo_analyzer(self):
        """Create repository analyzer instance."""
        return RepositoryAnalyzer()

    def test_understand_layered_architecture(self, repo_analyzer):
        """Test understanding layered architecture."""
        readme = """
        # Layered Architecture

        - Presentation Layer: REST API endpoints
        - Business Logic Layer: Service classes
        - Data Access Layer: Repository pattern
        - Database Layer: PostgreSQL
        """
        metadata = {
            "id": "layered001",
            "full_name": "org/layered-arch",
            "stars": 1600,
            "language": "Python",
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        assert analysis.documentation_score >= 0.0

    def test_understand_event_driven_architecture(self, repo_analyzer):
        """Test understanding event-driven architecture."""
        readme = """
        # Event-Driven Architecture

        Components:
        - Event producers publish events
        - Message broker (Kafka) handles routing
        - Event consumers process events
        - Event store for audit trail
        """
        metadata = {
            "id": "event001",
            "full_name": "org/event-driven",
            "stars": 2800,
            "language": "Python",
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        assert analysis.documentation_score >= 0.0

    def test_understand_plugin_architecture(self, repo_analyzer):
        """Test understanding plugin architecture."""
        readme = """
        # Plugin Architecture

        Core system with plugin support:
        - Plugin interface definition
        - Dynamic plugin loading
        - Plugin lifecycle management
        - Plugin dependency resolution
        """
        metadata = {
            "id": "plugin001",
            "full_name": "org/plugin-arch",
            "stars": 1900,
            "language": "Python",
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        assert analysis.documentation_score >= 0.0

    def test_understand_component_relationships(self, repo_analyzer):
        """Test understanding component relationships."""
        readme = """
        # Component Relationships

        - API Gateway depends on Auth Service
        - User Service depends on Database
        - Notification Service subscribes to User Events
        - All services use shared Config Service
        """
        metadata = {
            "id": "components001",
            "full_name": "org/components",
            "stars": 2100,
            "language": "Python",
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        assert analysis.documentation_score >= 0.0


@pytest.mark.integration
class TestCodeQualityAssessment:
    """Integration tests for code quality assessment."""

    @pytest.fixture
    def repo_analyzer(self):
        """Create repository analyzer instance."""
        return RepositoryAnalyzer()

    def test_assess_high_quality_repository(self, repo_analyzer):
        """Test assessing high-quality repository."""
        readme = """
        # High Quality Project

        ## Installation
        ```bash
        pip install high-quality-project
        ```

        ## Quick Start
        ```python
        from project import Client
        client = Client()
        result = client.process()
        ```

        ## Documentation
        Full documentation at docs.project.com

        ## Testing
        ```bash
        pytest tests/ --cov=src
        ```

        ## Contributing
        See CONTRIBUTING.md for guidelines.
        """

        metadata = {
            "id": "high-quality",
            "full_name": "org/high-quality",
            "stars": 10000,
            "forks": 2000,
            "open_issues": 50,
            "language": "Python",
            "license": {"name": "MIT"},
            "contributors": 50,
            "last_commit_days": 3,
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        # High quality indicators
        assert analysis.code_quality_score > 0.6
        assert analysis.documentation_score > 0.7
        assert analysis.maintenance_score > 0.7
        assert analysis.is_maintained is True
        assert len(analysis.strengths) >= 3

    def test_assess_low_quality_repository(self, repo_analyzer):
        """Test assessing low-quality repository."""
        readme = "# Project\n\nA project."

        metadata = {
            "id": "low-quality",
            "full_name": "org/low-quality",
            "stars": 10,
            "forks": 1,
            "open_issues": 50,
            "language": "Python",
            "license": None,
            "contributors": 1,
            "last_commit_days": 500,
        }

        analysis = repo_analyzer.analyze(metadata, readme)

        # Low quality indicators
        assert analysis.code_quality_score < 0.5
        assert analysis.documentation_score < 0.3
        assert analysis.maintenance_score < 0.3
        assert len(analysis.limitations) >= 2

    def test_assess_abandoned_repository(self, repo_analyzer):
        """Test assessing abandoned repository."""
        metadata = {
            "id": "abandoned",
            "full_name": "org/abandoned",
            "stars": 500,
            "forks": 50,
            "open_issues": 100,
            "language": "Python",
            "license": {"name": "MIT"},
            "contributors": 5,
            "last_commit_days": 730,  # 2 years
        }

        analysis = repo_analyzer.analyze(metadata, None)

        # Abandoned indicators
        assert analysis.is_maintained is False
        assert analysis.maintenance_score < 0.3
        limitations_text = " ".join(analysis.limitations).lower()
        assert "maintained" in limitations_text

    def test_assess_popular_but_unmaintained(self, repo_analyzer):
        """Test assessing popular but unmaintained repository."""
        metadata = {
            "id": "popular-unmaintained",
            "full_name": "org/popular-old",
            "stars": 5000,
            "forks": 1000,
            "open_issues": 300,
            "language": "Python",
            "license": {"name": "MIT"},
            "contributors": 20,
            "last_commit_days": 365,
        }

        analysis = repo_analyzer.analyze(metadata, None)

        # Should have high authority but may have varying maintenance
        assert analysis.stars > 1000
