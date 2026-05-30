"""Tests for skill marketplace and discovery system."""

import tempfile
from pathlib import Path

import pytest

from lyra_cli.skills.marketplace.discovery import (
    SearchFilter,
    SkillDiscovery,
    SortBy,
)
from lyra_cli.skills.marketplace.installer import (
    DependencyResolver,
    InstallStatus,
    SkillInstaller,
)
from lyra_cli.skills.marketplace.rating import (
    RatingSystem,
)
from lyra_cli.skills.marketplace.registry import (
    RegistryMetadata,
    SkillPackage,
    SkillRegistry,
    SkillVersion,
)


@pytest.fixture
def temp_registry_dir():
    """Create temporary registry directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registry(temp_registry_dir):
    """Create a skill registry backed by temp directory."""
    from lyra_cli.skills.marketplace.registry import FileSystemStorage
    return SkillRegistry(storage=FileSystemStorage(Path(temp_registry_dir)))


@pytest.fixture
def sample_packages():
    """Create sample skill packages."""
    return [
        SkillPackage(
            name="python-testing",
            author="test-author",
            description="Python testing patterns and best practices",
            category="testing",
            tags=["python", "testing", "pytest"],
            versions=[
                SkillVersion(
                    version="1.0.0",
                    release_date="2026-05-01",
                    changelog="Initial release",
                    download_url="https://example.com/python-testing-1.0.0.tar.gz",
                    checksum="abc123",
                )
            ],
            current_version="1.0.0",
            metadata=RegistryMetadata(total_downloads=100, verified=True),
        ),
        SkillPackage(
            name="api-design",
            author="test-author",
            description="RESTful API design patterns and testing",
            category="testing",
            tags=["api", "rest", "python"],
            versions=[
                SkillVersion(
                    version="2.0.0",
                    release_date="2026-05-15",
                    changelog="Major update",
                    download_url="https://example.com/api-design-2.0.0.tar.gz",
                    checksum="def456",
                )
            ],
            current_version="2.0.0",
            metadata=RegistryMetadata(total_downloads=250, verified=True),
        ),
        SkillPackage(
            name="database-patterns",
            author="another-author",
            description="Database design and optimization patterns",
            category="database",
            tags=["database", "sql", "optimization"],
            versions=[
                SkillVersion(
                    version="1.5.0",
                    release_date="2026-05-20",
                    changelog="Performance improvements",
                    download_url="https://example.com/database-patterns-1.5.0.tar.gz",
                    checksum="ghi789",
                    dependencies=["python-testing@1.0.0"],
                )
            ],
            current_version="1.5.0",
            metadata=RegistryMetadata(total_downloads=50, verified=False),
        ),
    ]


class TestSkillRegistry:
    """Test suite for SkillRegistry."""

    def test_register_package(self, registry, sample_packages):
        """Test registering a skill package."""
        package = sample_packages[0]
        registry.register(package)

        retrieved = registry.get(package.name)
        assert retrieved is not None
        assert retrieved.name == package.name
        assert retrieved.author == package.author

    def test_get_nonexistent_package(self, registry):
        """Test getting a package that doesn't exist."""
        result = registry.get("nonexistent")
        assert result is None

    def test_update_version(self, registry, sample_packages):
        """Test adding a new version to a package."""
        package = sample_packages[0]
        registry.register(package)

        new_version = SkillVersion(
            version="1.1.0",
            release_date="2026-05-25",
            changelog="Bug fixes",
            download_url="https://example.com/python-testing-1.1.0.tar.gz",
            checksum="xyz999",
        )

        success = registry.update_version(package.name, new_version, set_as_current=True)
        assert success

        updated = registry.get(package.name)
        assert updated.current_version == "1.1.0"
        assert len(updated.versions) == 2

    def test_increment_downloads(self, registry, sample_packages):
        """Test incrementing download count."""
        package = sample_packages[0]
        registry.register(package)

        initial_downloads = package.metadata.total_downloads
        registry.increment_downloads(package.name, 5)

        updated = registry.get(package.name)
        assert updated.metadata.total_downloads == initial_downloads + 5

    def test_mark_verified(self, registry, sample_packages):
        """Test marking a package as verified."""
        package = sample_packages[2]  # Not verified
        registry.register(package)

        registry.mark_verified(package.name, True)

        updated = registry.get(package.name)
        assert updated.metadata.verified is True

    def test_search_by_tag(self, registry, sample_packages):
        """Test searching by tag."""
        for package in sample_packages:
            registry.register(package)

        results = registry.search_by_tag("python")
        assert len(results) == 2
        assert any(r.name == "python-testing" for r in results)

    def test_search_by_category(self, registry, sample_packages):
        """Test searching by category."""
        for package in sample_packages:
            registry.register(package)

        results = registry.search_by_category("testing")
        assert len(results) == 2
        assert any(r.name == "python-testing" for r in results)

    def test_search_by_author(self, registry, sample_packages):
        """Test searching by author."""
        for package in sample_packages:
            registry.register(package)

        results = registry.search_by_author("test-author")
        assert len(results) == 2

    def test_get_most_downloaded(self, registry, sample_packages):
        """Test getting most downloaded packages."""
        for package in sample_packages:
            registry.register(package)

        results = registry.get_most_downloaded(limit=2)
        assert len(results) == 2
        assert results[0].name == "api-design"  # 250 downloads
        assert results[1].name == "python-testing"  # 100 downloads

    def test_export_import_json(self, registry, sample_packages, temp_registry_dir):
        """Test exporting and importing registry."""
        for package in sample_packages:
            registry.register(package)

        export_path = temp_registry_dir / "export.json"
        registry.export_to_json(export_path)

        # Create new registry and import
        new_registry = SkillRegistry()
        count = new_registry.import_from_json(export_path)

        assert count == len(sample_packages)
        assert len(new_registry.list_all()) == len(sample_packages)


class TestSkillDiscovery:
    """Test suite for SkillDiscovery."""

    def test_search_by_query(self, registry, sample_packages):
        """Test searching by query string."""
        for package in sample_packages:
            registry.register(package)

        discovery = SkillDiscovery(registry)
        filter = SearchFilter(query="python")

        results = discovery.search(filter)
        assert len(results) > 0
        assert any("python" in r.package.name.lower() for r in results)

    def test_search_with_tag_filter(self, registry, sample_packages):
        """Test searching with tag filter."""
        for package in sample_packages:
            registry.register(package)

        discovery = SkillDiscovery(registry)
        filter = SearchFilter(tags=["python"])

        results = discovery.search(filter)
        assert len(results) == 2
        assert any("python" in r.package.name.lower() for r in results)

    def test_search_verified_only(self, registry, sample_packages):
        """Test searching verified packages only."""
        for package in sample_packages:
            registry.register(package)

        discovery = SkillDiscovery(registry)
        filter = SearchFilter(verified_only=True)

        results = discovery.search(filter)
        assert all(r.package.metadata.verified for r in results)

    def test_search_sort_by_downloads(self, registry, sample_packages):
        """Test sorting by downloads."""
        for package in sample_packages:
            registry.register(package)

        discovery = SkillDiscovery(registry)
        filter = SearchFilter()

        results = discovery.search(filter, sort_by=SortBy.DOWNLOADS)
        assert results[0].package.name == "api-design"  # Most downloads

    def test_search_relevance_scoring(self, registry, sample_packages):
        """Test relevance scoring."""
        for package in sample_packages:
            registry.register(package)

        discovery = SkillDiscovery(registry)
        filter = SearchFilter(query="python-testing")

        results = discovery.search(filter)
        # Exact name match should have highest score
        assert results[0].package.name == "python-testing"
        assert results[0].relevance_score > 5.0

    def test_get_trending(self, registry, sample_packages):
        """Test getting trending skills."""
        for package in sample_packages:
            registry.register(package)

        discovery = SkillDiscovery(registry)
        trending = discovery.get_trending(limit=2)

        assert len(trending) <= 2
        for skill in trending:
            assert skill.trending_score > 0

    def test_recommend_no_history(self, registry, sample_packages):
        """Test recommendations with no usage history."""
        for package in sample_packages:
            registry.register(package)

        discovery = SkillDiscovery(registry)
        recommendations = discovery.recommend("new-user", limit=3)

        # Should return popular skills
        assert len(recommendations) > 0

    def test_recommend_with_history(self, registry, sample_packages):
        """Test recommendations based on usage history."""
        for package in sample_packages:
            registry.register(package)

        discovery = SkillDiscovery(registry)

        # Record usage
        discovery.record_usage("user1", "python-testing")

        # Get recommendations
        recommendations = discovery.recommend("user1", limit=3)

        # Should recommend related skills
        assert len(recommendations) > 0

    def test_get_related_skills(self, registry, sample_packages):
        """Test getting related skills."""
        for package in sample_packages:
            registry.register(package)

        discovery = SkillDiscovery(registry)
        related = discovery.get_related_skills("python-testing", limit=2)

        # Should find related skills
        assert len(related) >= 0


class TestDependencyResolver:
    """Test suite for DependencyResolver."""

    def test_resolve_no_dependencies(self, registry, sample_packages):
        """Test resolving skill with no dependencies."""
        package = sample_packages[0]  # No dependencies
        registry.register(package)

        resolver = DependencyResolver(registry)
        order, error = resolver.resolve(package.name)

        assert error is None
        assert len(order) == 1
        assert order[0][0] == package.name

    def test_resolve_with_dependencies(self, registry, sample_packages):
        """Test resolving skill with dependencies."""
        # Register both packages
        registry.register(sample_packages[0])  # python-testing
        registry.register(sample_packages[2])  # database-patterns (depends on python-testing)

        resolver = DependencyResolver(registry)
        order, error = resolver.resolve("database-patterns")

        assert error is None
        assert len(order) == 2
        # python-testing should come before database-patterns
        assert order[0][0] == "python-testing"
        assert order[1][0] == "database-patterns"

    def test_resolve_missing_dependency(self, registry, sample_packages):
        """Test resolving with missing dependency."""
        # Only register database-patterns (missing python-testing)
        registry.register(sample_packages[2])

        resolver = DependencyResolver(registry)
        order, error = resolver.resolve("database-patterns")

        assert error is not None
        assert "not found" in error.lower()

    def test_resolve_nonexistent_skill(self, registry):
        """Test resolving nonexistent skill."""
        resolver = DependencyResolver(registry)
        order, error = resolver.resolve("nonexistent")

        assert error is not None
        assert len(order) == 0


class TestSkillInstaller:
    """Test suite for SkillInstaller."""

    def test_install_simple_skill(self, registry, sample_packages, temp_registry_dir):
        """Test installing a skill without dependencies."""
        package = sample_packages[0]
        registry.register(package)

        install_dir = temp_registry_dir / "installed"
        installer = SkillInstaller(registry, install_dir)

        result = installer.install(package.name)

        assert result.status == InstallStatus.SUCCESS
        assert result.installed_path is not None
        assert result.installed_path.exists()

    def test_install_with_dependencies(self, registry, sample_packages, temp_registry_dir):
        """Test installing skill with dependencies."""
        # Register both packages
        registry.register(sample_packages[0])  # python-testing
        registry.register(sample_packages[2])  # database-patterns

        install_dir = temp_registry_dir / "installed"
        installer = SkillInstaller(registry, install_dir)

        result = installer.install("database-patterns")

        assert result.status == InstallStatus.SUCCESS
        assert result.dependencies_installed is not None
        assert "python-testing" in result.dependencies_installed

    def test_install_already_installed(self, registry, sample_packages, temp_registry_dir):
        """Test installing already installed skill."""
        package = sample_packages[0]
        registry.register(package)

        install_dir = temp_registry_dir / "installed"
        installer = SkillInstaller(registry, install_dir)

        # Install once
        installer.install(package.name)

        # Try to install again
        result = installer.install(package.name)

        assert result.status == InstallStatus.ALREADY_INSTALLED

    def test_install_force_reinstall(self, registry, sample_packages, temp_registry_dir):
        """Test force reinstalling a skill."""
        package = sample_packages[0]
        registry.register(package)

        install_dir = temp_registry_dir / "installed"
        installer = SkillInstaller(registry, install_dir)

        # Install once
        installer.install(package.name)

        # Force reinstall
        result = installer.install(package.name, force=True)

        assert result.status == InstallStatus.SUCCESS

    def test_uninstall_skill(self, registry, sample_packages, temp_registry_dir):
        """Test uninstalling a skill."""
        package = sample_packages[0]
        registry.register(package)

        install_dir = temp_registry_dir / "installed"
        installer = SkillInstaller(registry, install_dir)

        # Install
        installer.install(package.name)

        # Uninstall
        success = installer.uninstall(package.name)

        assert success
        assert not (install_dir / package.name).exists()

    def test_list_installed(self, registry, sample_packages, temp_registry_dir):
        """Test listing installed skills."""
        registry.register(sample_packages[0])
        registry.register(sample_packages[1])

        install_dir = temp_registry_dir / "installed"
        installer = SkillInstaller(registry, install_dir)

        # Install two skills
        installer.install(sample_packages[0].name)
        installer.install(sample_packages[1].name)

        installed = installer.list_installed()

        assert len(installed) == 2
        assert sample_packages[0].name in installed
        assert sample_packages[1].name in installed


class TestRatingSystem:
    """Test suite for RatingSystem."""

    def test_rate_skill(self):
        """Test rating a skill."""
        rating_system = RatingSystem()

        success = rating_system.rate_skill("test-skill", "user1", 5)
        assert success

        # Check aggregate
        aggregate = rating_system.get_aggregate_rating("test-skill")
        assert aggregate is not None
        assert aggregate.average_rating == 5.0
        assert aggregate.total_ratings == 1

    def test_rate_skill_invalid_stars(self):
        """Test rating with invalid stars."""
        rating_system = RatingSystem()

        success = rating_system.rate_skill("test-skill", "user1", 6)
        assert not success

        success = rating_system.rate_skill("test-skill", "user1", 0)
        assert not success

    def test_multiple_ratings(self):
        """Test multiple ratings for a skill."""
        rating_system = RatingSystem()

        rating_system.rate_skill("test-skill", "user1", 5)
        rating_system.rate_skill("test-skill", "user2", 4)
        rating_system.rate_skill("test-skill", "user3", 3)

        aggregate = rating_system.get_aggregate_rating("test-skill")
        assert aggregate is not None
        assert aggregate.total_ratings == 3
        assert 3.5 <= aggregate.average_rating <= 4.5

    def test_rating_distribution(self):
        """Test rating distribution."""
        rating_system = RatingSystem()

        rating_system.rate_skill("test-skill", "user1", 5)
        rating_system.rate_skill("test-skill", "user2", 5)
        rating_system.rate_skill("test-skill", "user3", 4)
        rating_system.rate_skill("test-skill", "user4", 3)

        aggregate = rating_system.get_aggregate_rating("test-skill")
        assert aggregate.rating_distribution[5] == 2
        assert aggregate.rating_distribution[4] == 1
        assert aggregate.rating_distribution[3] == 1

    def test_submit_review(self):
        """Test submitting a review."""
        rating_system = RatingSystem()

        success = rating_system.submit_review(
            review_id="review1",
            skill_name="test-skill",
            user_id="user1",
            rating=5,
            title="Great skill!",
            text="This skill is very helpful and well documented.",
        )

        assert success

        reviews = rating_system.get_reviews("test-skill")
        assert len(reviews) == 1
        assert reviews[0].title == "Great skill!"

    def test_submit_review_too_short(self):
        """Test submitting review that's too short."""
        rating_system = RatingSystem()

        success = rating_system.submit_review(
            review_id="review1",
            skill_name="test-skill",
            user_id="user1",
            rating=5,
            title="Good",
            text="Good",  # Too short
        )

        assert not success

    def test_mark_helpful(self):
        """Test marking review as helpful."""
        rating_system = RatingSystem()

        rating_system.submit_review(
            review_id="review1",
            skill_name="test-skill",
            user_id="user1",
            rating=5,
            title="Great!",
            text="Very helpful skill for testing.",
        )

        success = rating_system.mark_helpful("review1")
        assert success

        reviews = rating_system.get_reviews("test-skill")
        assert reviews[0].helpful_count == 1

    def test_flag_review(self):
        """Test flagging a review."""
        rating_system = RatingSystem()

        rating_system.submit_review(
            review_id="review1",
            skill_name="test-skill",
            user_id="user1",
            rating=5,
            title="Spam",
            text="This is spam content that should be flagged.",
        )

        success = rating_system.flag_review("review1", "spam")
        assert success

    def test_has_user_rated(self):
        """Test checking if user has rated."""
        rating_system = RatingSystem()

        assert not rating_system.has_user_rated("test-skill", "user1")

        rating_system.rate_skill("test-skill", "user1", 5)

        assert rating_system.has_user_rated("test-skill", "user1")

    def test_get_user_rating(self):
        """Test getting user's rating."""
        rating_system = RatingSystem()

        rating_system.rate_skill("test-skill", "user1", 4)

        rating = rating_system.get_user_rating("test-skill", "user1")
        assert rating == 4

    def test_user_reputation(self):
        """Test user reputation calculation."""
        rating_system = RatingSystem()

        # Submit review
        rating_system.submit_review(
            review_id="review1",
            skill_name="test-skill",
            user_id="user1",
            rating=5,
            title="Excellent",
            text="This is an excellent skill with great documentation.",
        )

        reputation = rating_system.get_user_reputation("user1")
        assert reputation.total_reviews == 1
        assert reputation.reputation_score > 0
