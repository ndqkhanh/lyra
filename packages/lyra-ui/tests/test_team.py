"""Tests for team management."""

from lyra_ui import (
    TeamManager,
    UserRole,
)

# TeamManager Tests


def test_team_manager_init(tmp_path):
    """Test team manager initialization."""
    manager = TeamManager(storage_path=tmp_path)
    assert manager.storage_path == tmp_path
    assert manager.current_team is None
    assert len(manager.templates) == 0


def test_create_team(tmp_path):
    """Test creating team."""
    manager = TeamManager(storage_path=tmp_path)
    config = manager.create_team(
        team_id="team1",
        team_name="Test Team",
        settings={"theme": "dark"},
    )
    assert config.team_id == "team1"
    assert config.team_name == "Test Team"
    assert config.settings == {"theme": "dark"}
    assert manager.current_team == config


def test_add_member(tmp_path):
    """Test adding team member."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")

    member = manager.add_member(
        user_id="user1",
        username="alice",
        email="alice@example.com",
        role=UserRole.ADMIN,
    )
    assert member.user_id == "user1"
    assert member.username == "alice"
    assert member.email == "alice@example.com"
    assert member.role == UserRole.ADMIN
    assert len(manager.current_team.members) == 1


def test_add_member_no_team(tmp_path):
    """Test adding member without active team."""
    manager = TeamManager(storage_path=tmp_path)
    try:
        manager.add_member("user1", "alice", "alice@example.com")
        raise AssertionError("Should raise ValueError")
    except ValueError as e:
        assert "No active team" in str(e)


def test_remove_member(tmp_path):
    """Test removing team member."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")
    manager.add_member("user1", "alice", "alice@example.com")
    manager.add_member("user2", "bob", "bob@example.com")

    manager.remove_member("user1")
    assert len(manager.current_team.members) == 1
    assert manager.current_team.members[0].user_id == "user2"


def test_update_member_role(tmp_path):
    """Test updating member role."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")
    manager.add_member("user1", "alice", "alice@example.com", UserRole.MEMBER)

    manager.update_member_role("user1", UserRole.ADMIN)
    assert manager.current_team.members[0].role == UserRole.ADMIN


def test_set_quota(tmp_path):
    """Test setting usage quota."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")

    manager.set_quota("user1", tokens_limit=100000, cost_limit=10.0)
    assert "user1" in manager.current_team.quotas
    quota = manager.current_team.quotas["user1"]
    assert quota.tokens_limit == 100000
    assert quota.cost_limit == 10.0


def test_update_usage(tmp_path):
    """Test updating usage."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")
    manager.set_quota("user1", 100000, 10.0)

    manager.update_usage("user1", tokens=5000, cost=0.5)
    quota = manager.current_team.quotas["user1"]
    assert quota.tokens_used == 5000
    assert quota.cost_used == 0.5

    manager.update_usage("user1", tokens=3000, cost=0.3)
    assert quota.tokens_used == 8000
    assert quota.cost_used == 0.8


def test_check_quota_within_limit(tmp_path):
    """Test checking quota within limit."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")
    manager.set_quota("user1", 100000, 10.0)
    manager.update_usage("user1", 50000, 5.0)

    assert manager.check_quota("user1") is True


def test_check_quota_exceeded(tmp_path):
    """Test checking quota exceeded."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")
    manager.set_quota("user1", 100000, 10.0)
    manager.update_usage("user1", 100000, 10.0)

    assert manager.check_quota("user1") is False


def test_check_quota_no_quota(tmp_path):
    """Test checking quota with no quota set."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")

    assert manager.check_quota("user1") is True


def test_add_template(tmp_path):
    """Test adding prompt template."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")

    template = manager.add_template(
        template_id="t1",
        name="Code Review",
        description="Template for code reviews",
        template="Review the following code: {code}",
        variables=["code"],
        created_by="user1",
    )
    assert template.id == "t1"
    assert template.name == "Code Review"
    assert template.variables == ["code"]
    assert len(manager.templates) == 1


def test_get_template(tmp_path):
    """Test getting template."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")
    manager.add_template("t1", "Test", "Description", "Template text")

    template = manager.get_template("t1")
    assert template is not None
    assert template.id == "t1"

    template = manager.get_template("nonexistent")
    assert template is None


def test_list_templates(tmp_path):
    """Test listing templates."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")
    manager.add_template("t1", "Template 1", "Desc 1", "Text 1")
    manager.add_template("t2", "Template 2", "Desc 2", "Text 2")

    templates = manager.list_templates()
    assert len(templates) == 2


def test_save_and_load_team(tmp_path):
    """Test saving and loading team."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")
    manager.add_member("user1", "alice", "alice@example.com")
    manager.set_quota("user1", 100000, 10.0)
    manager.add_template("t1", "Template", "Description", "Text")

    manager.save_team()
    assert (tmp_path / "team1.json").exists()

    manager2 = TeamManager(storage_path=tmp_path)
    manager2.load_team("team1")
    assert manager2.current_team.team_id == "team1"
    assert len(manager2.current_team.members) == 1
    assert len(manager2.current_team.quotas) == 1
    assert len(manager2.templates) == 1


def test_get_team_analytics(tmp_path):
    """Test getting team analytics."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")
    manager.add_member("user1", "alice", "alice@example.com", UserRole.ADMIN)
    manager.add_member("user2", "bob", "bob@example.com", UserRole.MEMBER)
    manager.set_quota("user1", 100000, 10.0)
    manager.update_usage("user1", 50000, 5.0)
    manager.add_template("t1", "Template", "Description", "Text")

    analytics = manager.get_team_analytics()
    assert analytics["team_id"] == "team1"
    assert analytics["total_members"] == 2
    assert analytics["role_distribution"]["admin"] == 1
    assert analytics["role_distribution"]["member"] == 1
    assert analytics["total_tokens_used"] == 50000
    assert analytics["total_cost"] == 5.0
    assert analytics["total_templates"] == 1


# Integration Tests


def test_complete_team_workflow(tmp_path):
    """Test complete team workflow."""
    manager = TeamManager(storage_path=tmp_path)

    # Create team
    manager.create_team("engineering", "Engineering Team", {"theme": "dark"})

    # Add members
    manager.add_member("alice", "Alice", "alice@example.com", UserRole.ADMIN)
    manager.add_member("bob", "Bob", "bob@example.com", UserRole.MEMBER)
    manager.add_member("charlie", "Charlie", "charlie@example.com", UserRole.VIEWER)

    # Set quotas
    manager.set_quota("alice", 200000, 20.0)
    manager.set_quota("bob", 100000, 10.0)

    # Update usage
    manager.update_usage("alice", 50000, 5.0)
    manager.update_usage("bob", 30000, 3.0)

    # Add templates
    manager.add_template(
        "code-review",
        "Code Review",
        "Template for code reviews",
        "Review: {code}",
        ["code"],
        "alice",
    )

    # Save
    manager.save_team()

    # Load in new manager
    manager2 = TeamManager(storage_path=tmp_path)
    manager2.load_team("engineering")

    # Verify
    assert manager2.current_team.team_name == "Engineering Team"
    assert len(manager2.current_team.members) == 3
    assert len(manager2.current_team.quotas) == 2
    assert len(manager2.templates) == 1

    # Check analytics
    analytics = manager2.get_team_analytics()
    assert analytics["total_members"] == 3
    assert analytics["total_tokens_used"] == 80000
    assert analytics["total_cost"] == 8.0


def test_team_member_lifecycle(tmp_path):
    """Test team member lifecycle."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")

    # Add member
    manager.add_member("user1", "alice", "alice@example.com", UserRole.MEMBER)
    assert len(manager.current_team.members) == 1

    # Update role
    manager.update_member_role("user1", UserRole.ADMIN)
    assert manager.current_team.members[0].role == UserRole.ADMIN

    # Remove member
    manager.remove_member("user1")
    assert len(manager.current_team.members) == 0


def test_quota_management(tmp_path):
    """Test quota management."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")

    # Set quota
    manager.set_quota("user1", 100000, 10.0)
    assert manager.check_quota("user1") is True

    # Use some quota
    manager.update_usage("user1", 50000, 5.0)
    assert manager.check_quota("user1") is True

    # Exceed quota
    manager.update_usage("user1", 50000, 5.0)
    assert manager.check_quota("user1") is False


def test_template_management(tmp_path):
    """Test template management."""
    manager = TeamManager(storage_path=tmp_path)
    manager.create_team("team1", "Test Team")

    # Add templates
    manager.add_template("t1", "Template 1", "Desc 1", "Text 1")
    manager.add_template("t2", "Template 2", "Desc 2", "Text 2")

    # List templates
    templates = manager.list_templates()
    assert len(templates) == 2

    # Get specific template
    template = manager.get_template("t1")
    assert template.name == "Template 1"
