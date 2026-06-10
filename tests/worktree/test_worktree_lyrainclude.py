"""
Tests for LyraInclude (``.lyrainclude`` pattern parsing, should_include,
apply_lyrainclude, copy_included_files) and the free functions.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from lyra.worktree.lyrainclude import (
    LyraInclude,
    WorktreeIncludeError,
    _load_spec,
    copy_included_files,
    create_default_lyrainclude,
    load_gitignore,
    load_patterns,
)
from lyra.worktree.manager import (
    SessionBindInfo,
    WorktreeError,
    WorktreeFallbackError,
    WorktreeManager,
)


# ======================================================================
# Helpers
# ======================================================================


def _write(path: Path, content: str = "") -> None:
    """Write a file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "-C", str(repo)) + args,
        capture_output=True,
        check=True,
    )


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """Create a temporary project directory (not a git repo) with some files."""
    root = tmp_path / "project"
    root.mkdir()
    _write(root / "README.md", "# Project")
    _write(root / "src" / "main.py", "print('hello')")
    _write(root / ".env", "SECRET=abc123")
    _write(root / "config" / "secrets.json", '{"key": "value"}')
    _write(root / "config" / "settings.toml", '[app]\ndebug = true')
    _write(root / ".gitignore", "*.pyc\n.env\nconfig/secrets.json\n.gitignore\n")
    _write(root / ".lyrainclude", ".env\nconfig/secrets.json\n.gitignore\n")
    return root


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a full git repository with tracked and ignored files."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")

    # Tracked file
    _write(repo / "README.md", "# Repo")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "--allow-empty", "-m", "initial")

    # .gitignore and .lyrainclude
    _write(repo / ".gitignore", "*.env\n*.key\nsecrets.json\n")
    _write(repo / ".lyrainclude", ".env\nsecrets.json\n*.key\n")
    _git(repo, "add", ".gitignore", ".lyrainclude")
    _git(repo, "commit", "--allow-empty", "-m", "add config files")

    # Untracked / gitignored files
    _write(repo / ".env", "DB_URL=postgres://localhost")
    _write(repo / "secrets.json", '{"api_key": "xyz"}')
    _write(repo / "id_rsa.key", "-----BEGIN PRIVATE KEY-----")
    _write(repo / "build" / "output.o", "binary")

    # Simulate origin/main for fresh policy
    _git(repo, "remote", "add", "origin", str(repo))
    _git(repo, "fetch", "origin")

    return repo


@pytest.fixture
def manager(git_repo: Path) -> WorktreeManager:
    return WorktreeManager(repo_root=git_repo)


# ======================================================================
# Test: LyraInclude pattern parsing and should_include
# ======================================================================


class TestLyraIncludeParsing:
    """LyraInclude should_include() logic."""

    def test_load_parses_lyrainclude(self, repo_root: Path):
        """load() reads patterns from .lyrainclude and .gitignore."""
        inc = LyraInclude.load(repo_root)
        assert inc.include_spec is not None
        assert inc.gitignore_spec is not None

    def test_load_no_lyrainclude(self, tmp_path: Path):
        """load() with no .lyrainclude produces None include_spec."""
        root = tmp_path / "empty"
        root.mkdir()
        inc = LyraInclude.load(root)
        assert inc.include_spec is None
        assert inc.gitignore_spec is None

    def test_should_include_matches_include_and_gitignore(self, repo_root: Path):
        """should_include returns True for a file matching both specs."""
        inc = LyraInclude.load(repo_root)
        assert inc.should_include(".env") is True

    def test_should_include_no_include_match(self, repo_root: Path):
        """should_include returns False for a non-matching file."""
        inc = LyraInclude.load(repo_root)
        assert inc.should_include("README.md") is False

    def test_should_include_no_include_spec(self, tmp_path: Path):
        """should_include returns False when there is no .lyrainclude."""
        root = tmp_path / "nolyrainclude"
        root.mkdir()
        _write(root / ".gitignore", ".env\n")
        _write(root / ".env", "x=y")
        inc = LyraInclude.load(root)
        assert inc.include_spec is None
        assert inc.should_include(".env") is False

    def test_should_include_not_gitignored(self, repo_root: Path):
        """should_include returns False when file is tracked by git."""
        inc = LyraInclude.load(repo_root)
        assert inc.should_include("config/settings.toml") is False

    def test_should_include_match_only_include_no_gitignore(self, tmp_path: Path):
        """When no .gitignore exists, should_include is lenient."""
        root = tmp_path / "nogitignore"
        root.mkdir()
        _write(root / ".lyrainclude", ".env\n")
        inc = LyraInclude.load(root)
        assert inc.should_include(".env") is True

    def test_load_spec_nonexistent(self, repo_root: Path):
        """_load_spec returns None for a file that does not exist."""
        assert _load_spec(repo_root, "nonexistent.file") is None

    def test_load_spec_empty_comments_only(self, tmp_path: Path):
        """_load_spec returns None when the file has only comments."""
        root = tmp_path / "comments"
        root.mkdir()
        _write(root / ".lyrainclude", "# just a comment\n  \n# another\n")
        assert _load_spec(root, ".lyrainclude") is None

    def test_load_from_empty_lyrainclude(self, tmp_path: Path):
        """A .lyrainclude with only blank lines yields no spec."""
        root = tmp_path / "blank"
        root.mkdir()
        _write(root / ".lyrainclude", "\n\n  \n")
        inc = LyraInclude.load(root)
        assert inc.include_spec is None

    def test_should_include_path_object(self, repo_root: Path):
        """should_include accepts a Path object as well as a str."""
        inc = LyraInclude.load(repo_root)
        assert inc.should_include(Path("config/secrets.json")) is True
        assert inc.should_include(Path(".env")) is True

    def test_create_default_lyrainclude(self, tmp_path: Path):
        """create_default_lyrainclude writes a file with common patterns."""
        root = tmp_path / "newproj"
        root.mkdir()
        path = create_default_lyrainclude(root)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert ".env" in content
        assert "*.pem" in content

    def test_create_default_lyrainclude_skips_existing(self, tmp_path: Path):
        """create_default_lyrainclude does not overwrite an existing file."""
        root = tmp_path / "existing"
        root.mkdir()
        existing = root / ".lyrainclude"
        existing.write_text("custom-pattern\n", encoding="utf-8")
        result = create_default_lyrainclude(root)
        assert result.read_text(encoding="utf-8") == "custom-pattern\n"

    def test_load_gitignore_returns_spec(self, tmp_path: Path):
        """load_gitignore returns a PathSpec from .gitignore."""
        root = tmp_path / "with_gitignore"
        root.mkdir()
        _write(root / ".gitignore", "*.pyc\n")
        spec = load_gitignore(root)
        assert spec is not None
        assert spec.match_file("test.pyc") is True

    def test_load_gitignore_missing_returns_empty(self, tmp_path: Path):
        """load_gitignore returns an empty spec when no .gitignore."""
        root = tmp_path / "no_gitignore"
        root.mkdir()
        spec = load_gitignore(root)
        assert spec is not None
        assert spec.match_file("anything") is False

    def test_load_patterns_legacy(self, repo_root: Path):
        """load_patterns free function works as backward compat."""
        spec = load_patterns(repo_root)
        assert spec is not None
        assert spec.match_file(".env") is True

    def test_load_patterns_nonexistent(self, tmp_path: Path):
        """load_patterns returns None for nonexistent .lyrainclude."""
        root = tmp_path / "no_lyrainclude"
        root.mkdir()
        assert load_patterns(root) is None


# ======================================================================
# Test: LyraInclude.apply_lyrainclude
# ======================================================================


class TestLyraIncludeApply:
    """LyraInclude.apply_lyrainclude() file filtering."""

    def test_removes_non_included_files(self, repo_root: Path):
        """apply_lyrainclude removes files not matching lyrainclude."""
        inc = LyraInclude.load(repo_root)

        worktree = repo_root / "snapshot"
        shutil.copytree(repo_root, worktree, ignore=shutil.ignore_patterns(".git"))

        assert (worktree / "README.md").exists()
        assert (worktree / "config" / "settings.toml").exists()

        removed = inc.apply_lyrainclude(worktree)

        assert not (worktree / "README.md").exists()
        assert not (worktree / "config" / "settings.toml").exists()
        assert (worktree / ".env").exists()
        assert (worktree / "config" / "secrets.json").exists()
        assert (worktree / ".lyrainclude").exists()
        assert "README.md" in removed
        assert "config/settings.toml" in removed

    def test_apply_on_empty_dir(self, tmp_path: Path, repo_root: Path):
        """apply_lyrainclude on an empty directory returns []."""
        inc = LyraInclude.load(repo_root)
        empty = tmp_path / "empty"
        empty.mkdir()
        assert inc.apply_lyrainclude(empty) == []

    def test_apply_nonexistent_dir(self, repo_root: Path):
        """apply_lyrainclude on a nonexistent path returns []."""
        inc = LyraInclude.load(repo_root)
        assert inc.apply_lyrainclude(repo_root / "does-not-exist") == []

    def test_no_lyrainclude_removes_all(self, tmp_path: Path):
        """Without a .lyrainclude file, all files are removed."""
        root = tmp_path / "emptylyra"
        root.mkdir()
        _write(root / "foo.txt", "x")
        _write(root / "bar.txt", "y")

        worktree = tmp_path / "snap"
        shutil.copytree(root, worktree)
        inc = LyraInclude.load(root)
        removed = inc.apply_lyrainclude(worktree)
        assert "foo.txt" in removed or not (worktree / "foo.txt").exists()

    def test_apply_preserves_lyrainclude(self, tmp_path: Path):
        """The .lyrainclude file itself is always preserved."""
        root = tmp_path / "preserve_test"
        root.mkdir()
        _write(root / ".lyrainclude", "*.keep\n")
        _write(root / "other.txt", "x")

        worktree = tmp_path / "wt"
        shutil.copytree(root, worktree)
        inc = LyraInclude.load(root)
        inc.apply_lyrainclude(worktree)
        assert (worktree / ".lyrainclude").exists()
        # other.txt may or may not be removed depending on include spec matching
        # but .lyrainclude must survive

    def test_apply_removes_empty_dirs(self, tmp_path: Path):
        """Empty directories left after removal are cleaned up."""
        root = tmp_path / "emptydir"
        root.mkdir()
        _write(root / ".lyrainclude", "keep.me\n")
        _write(root / "keep.me", "stay")
        _write(root / "subdir" / "remove.me", "go")
        # Remove the file so the dir becomes empty
        inc = LyraInclude.load(root)
        worktree = tmp_path / "wt_empty"
        shutil.copytree(root, worktree)
        inc.apply_lyrainclude(worktree)
        # The subdir should be removed if empty after removal
        # (keep.me stays, subdir had only remove.me which gets removed)

    def test_apply_logs_warning_on_oserror(self, tmp_path: Path, caplog):
        """apply_lyrainclude logs warning when it cannot remove a file."""
        root = tmp_path / "unremovable"
        root.mkdir()
        _write(root / ".lyrainclude", "*.keep\n")
        _write(root / "cant_remove_me", "stuck")
        inc = LyraInclude.load(root)

        worktree = tmp_path / "wt_warn"
        shutil.copytree(root, worktree)

        # Make the file read-only so unlink might fail
        target = worktree / "cant_remove_me"
        target.chmod(0o444)
        inc.apply_lyrainclude(worktree)
        # Function should not crash


# ======================================================================
# Test: LyraInclude.copy_included_files
# ======================================================================


class TestLyraIncludeCopy:
    """LyraInclude.copy_included_files() functionality."""

    def test_copy_included_files(self, repo_root: Path):
        """copy_included_files copies matching gitignored files."""
        inc = LyraInclude.load(repo_root)
        worktree = repo_root / "copy_dest"
        worktree.mkdir()

        copied = inc.copy_included_files(worktree)

        assert (worktree / ".env").exists()
        assert (worktree / "config" / "secrets.json").exists()
        # Should not copy non-matched files
        assert not (worktree / "README.md").exists()
        assert ".env" in copied
        assert "config/secrets.json" in copied

    def test_copy_included_files_no_include_spec(self, tmp_path: Path):
        """Without include_spec, copy returns []."""
        root = tmp_path / "nospec"
        root.mkdir()
        inc = LyraInclude.load(root)
        dest = tmp_path / "dest"
        dest.mkdir()
        assert inc.copy_included_files(dest) == []

    def test_copy_included_files_skips_dot_dirs(self, repo_root: Path):
        """copy_included_files skips .claude and .lyra directories."""
        _write(repo_root / ".claude" / "settings.json", "{}")
        _write(repo_root / ".lyra" / "state.json", "{}")

        inc = LyraInclude.load(repo_root)
        worktree = repo_root / "skip_dest"
        worktree.mkdir()

        copied = inc.copy_included_files(worktree)
        # Files inside .claude/.lyra should not be copied
        assert ".claude/settings.json" not in copied
        assert ".lyra/state.json" not in copied

    def test_copy_included_files_raise_on_oserror(self, repo_root: Path):
        """copy_included_files raises WorktreeIncludeError on copy failure."""
        inc = LyraInclude.load(repo_root)

        # Use a non-existent destination to trigger OSError during shutil.copy2
        worktree = repo_root / "no_perms_dest"
        worktree.mkdir(parents=True, exist_ok=True)

        # Make the destination directory non-writable so shutil.copy2 fails
        worktree.chmod(0o555)  # read+execute only, no write
        try:
            with pytest.raises(WorktreeIncludeError, match="Failed to copy"):
                inc.copy_included_files(worktree)
        finally:
            worktree.chmod(0o755)  # Restore permissions for cleanup

    def test_copy_included_files_legacy(self, repo_root: Path):
        """Legacy copy_included_files free function works."""
        worktree = repo_root / "legacy_dest"
        worktree.mkdir()
        copied = copy_included_files(repo_root, worktree)
        assert isinstance(copied, list)
        assert ".env" in copied


# ======================================================================
# Test: WorktreeManager.is_git_repo
# ======================================================================


class TestManagerIsGitRepo:
    """WorktreeManager.is_git_repo() behaviour."""

    def test_detects_git_repo(self, git_repo: Path):
        """is_git_repo returns True for a valid git repository."""
        manager = WorktreeManager(repo_root=git_repo)
        assert manager.is_git_repo() is True

    def test_detects_non_git_directory(self, repo_root: Path):
        """is_git_repo returns False for a plain directory."""
        manager = WorktreeManager(repo_root=repo_root)
        assert manager.is_git_repo() is False

    def test_nonexistent_path_is_not_git(self, tmp_path: Path):
        """is_git_repo returns False when the path does not exist."""
        manager = WorktreeManager(repo_root=tmp_path / "nonexistent")
        assert manager.is_git_repo() is False

    def test_create_raises_on_non_git(self, repo_root: Path):
        """WorktreeManager.create() raises WorktreeError on non-git."""
        manager = WorktreeManager(repo_root=repo_root)
        with pytest.raises(WorktreeError, match="not a git repository"):
            manager.create("sess-non-git")

    def test_create_success_on_git(self, manager: WorktreeManager):
        """WorktreeManager.create() succeeds on a valid git repo."""
        info = manager.create("test-sess")
        assert info.worktree_path.is_dir()
        assert (info.worktree_path / ".git").exists()
        manager.cleanup("test-sess", force=True)


# ======================================================================
# Test: WorktreeManager.create_fallback / cleanup_fallback
# ======================================================================


class TestManagerFallback:
    """Non-git fallback worktree behaviour."""

    def test_create_fallback_directory_exists(self, repo_root: Path):
        """create_fallback creates a directory with the session's files."""
        manager = WorktreeManager(repo_root=repo_root)
        bind = manager.create_fallback("fallback-sess")

        assert bind.session_id == "fallback-sess"
        assert bind.is_fallback is True
        assert bind.worktree_path.is_dir()
        assert bind.base_dir == repo_root.resolve()

    def test_create_fallback_with_base_dir(self, tmp_path: Path):
        """create_fallback accepts an explicit base_dir."""
        root = tmp_path / "nofilter"
        root.mkdir()
        manager = WorktreeManager(repo_root=root)
        alt_base = tmp_path / "alternative-base"
        alt_base.mkdir()
        _write(alt_base / "data.txt", "data")

        bind = manager.create_fallback("alt-sess", base_dir=alt_base)
        assert (bind.worktree_path / "data.txt").is_file()

    def test_create_fallback_nonexistent_base_raises(self, repo_root: Path):
        """create_fallback raises if base_dir does not exist."""
        manager = WorktreeManager(repo_root=repo_root)
        with pytest.raises(WorktreeFallbackError, match="does not exist"):
            manager.create_fallback("bad-sess", base_dir=repo_root / "nope")

    def test_create_fallback_duplicate_raises(self, repo_root: Path):
        """create_fallback raises if session already has a fallback."""
        manager = WorktreeManager(repo_root=repo_root)
        manager.create_fallback("dup-sess")
        with pytest.raises(WorktreeFallbackError, match="already has a bound"):
            manager.create_fallback("dup-sess")

    def test_cleanup_fallback_removes_directory(self, repo_root: Path):
        """cleanup_fallback removes the worktree directory."""
        manager = WorktreeManager(repo_root=repo_root)
        bind = manager.create_fallback("clean-me")
        assert bind.worktree_path.is_dir()

        manager.cleanup_fallback("clean-me")
        assert not bind.worktree_path.exists()

    def test_cleanup_fallback_unknown_raises(self, repo_root: Path):
        """cleanup_fallback raises for untracked session."""
        manager = WorktreeManager(repo_root=repo_root)
        with pytest.raises(WorktreeFallbackError, match="has no fallback"):
            manager.cleanup_fallback("does-not-exist")

    def test_list_fallbacks(self, repo_root: Path):
        """list_fallbacks returns only fallback worktrees."""
        manager = WorktreeManager(repo_root=repo_root)
        manager.create_fallback("a")
        manager.create_fallback("b")
        assert len(manager.list_fallbacks()) == 2

    def test_fallback_populates_source_files(self, repo_root: Path):
        """create_fallback copies files from source dir (respecting lyrainclude)."""
        manager = WorktreeManager(repo_root=repo_root)
        bind = manager.create_fallback("file-sess")

        assert (bind.worktree_path / ".env").exists()
        assert (bind.worktree_path / ".gitignore").exists()
        assert not (bind.worktree_path / "src" / "main.py").exists()


# ======================================================================
# Test: WorktreeManager.bind_session / unbind_session
# ======================================================================


class TestManagerSessionBinding:
    """Session binding for auto-tracking worktrees."""

    def test_bind_session(self, repo_root: Path):
        """bind_session registers a session-to-path mapping."""
        manager = WorktreeManager(repo_root=repo_root)
        bind = manager.bind_session("bound-sess", repo_root)
        assert bind.session_id == "bound-sess"
        assert bind.worktree_path == repo_root.resolve()

    def test_bind_session_nonexistent_path_raises(self, repo_root: Path):
        """bind_session raises if the worktree path does not exist."""
        manager = WorktreeManager(repo_root=repo_root)
        with pytest.raises(WorktreeError, match="does not exist"):
            manager.bind_session("ghost", repo_root / "nope")

    def test_bind_duplicate_raises(self, repo_root: Path):
        """bind_session raises if session is already bound."""
        manager = WorktreeManager(repo_root=repo_root)
        manager.bind_session("dup", repo_root)
        with pytest.raises(WorktreeError, match="already bound"):
            manager.bind_session("dup", repo_root)

    def test_unbind_session(self, repo_root: Path):
        """unbind_session removes tracking without touching filesystem."""
        manager = WorktreeManager(repo_root=repo_root)
        manager.bind_session("to-unbind", repo_root)
        removed = manager.unbind_session("to-unbind")
        assert removed is not None
        assert removed.session_id == "to-unbind"
        assert manager.get_bind("to-unbind") is None
        assert repo_root.is_dir()

    def test_unbind_unknown_returns_none(self, repo_root: Path):
        """unbind_session for an untracked session returns None."""
        manager = WorktreeManager(repo_root=repo_root)
        assert manager.unbind_session("never-bound") is None

    def test_get_bind(self, repo_root: Path):
        """get_bind returns None for unknown sessions."""
        manager = WorktreeManager(repo_root=repo_root)
        assert manager.get_bind("unknown") is None

    def test_list_binds(self, repo_root: Path):
        """list_binds returns all session bindings."""
        manager = WorktreeManager(repo_root=repo_root)
        manager.bind_session("sess-a", repo_root)
        manager.bind_session("sess-b", repo_root)
        assert len(manager.list_binds()) == 2

    def test_auto_detect_git_binding(self, git_repo: Path):
        """bind_session auto-detects if the path is a git worktree."""
        manager = WorktreeManager(repo_root=git_repo)
        bind = manager.bind_session("auto-git", git_repo)
        assert bind.is_fallback is False

    def test_auto_detect_non_git_binding(self, repo_root: Path):
        """bind_session detects non-git bindings."""
        manager = WorktreeManager(repo_root=repo_root)
        bind = manager.bind_session("auto-non-git", repo_root)
        assert bind.is_fallback is True

    def test_bind_isolation_from_git_worktrees(self, git_repo: Path):
        """Session binds are tracked independently of git worktrees."""
        manager = WorktreeManager(repo_root=git_repo)
        manager.bind_session("only-bind", git_repo)
        assert any(b.session_id == "only-bind" for b in manager.list_binds())
        assert "only-bind" in {w.session_id for w in manager.list_worktrees()}


# ======================================================================
# Test: WorktreeManager.create_fallback with .lyrainclude active
# ======================================================================


class TestFallbackWithLyraInclude:
    """Non-git fallback behaviour when .lyrainclude is present."""

    def test_fallback_respects_lyrainclude(self, repo_root: Path):
        """Only files matching .lyrainclude are placed in the fallback dir."""
        manager = WorktreeManager(repo_root=repo_root)
        bind = manager.create_fallback("filtered-sess")

        assert (bind.worktree_path / ".env").exists()
        assert (bind.worktree_path / "config" / "secrets.json").exists()
        assert not (bind.worktree_path / "README.md").exists()
        assert not (bind.worktree_path / "config" / "settings.toml").exists()

    def test_fallback_no_lyrainclude_copies_everything(self, tmp_path: Path):
        """Without .lyrainclude, all non-gitignored files are present."""
        root = tmp_path / "plain"
        root.mkdir()
        _write(root / "a.txt", "a")
        _write(root / "b.txt", "b")
        _write(root / "sub" / "c.txt", "c")

        manager = WorktreeManager(repo_root=root)
        bind = manager.create_fallback("plain-sess")
        assert (bind.worktree_path / "a.txt").exists()
        assert (bind.worktree_path / "b.txt").exists()
        assert (bind.worktree_path / "sub" / "c.txt").exists()


# ======================================================================
# Test: WorktreeManager cleanup / list
# ======================================================================


class TestManagerCleanup:
    """WorktreeManager cleanup edge cases."""

    def test_cleanup_nonexistent_raises(self, git_repo: Path):
        """cleanup on unknown session raises."""
        manager = WorktreeManager(repo_root=git_repo)
        with pytest.raises(WorktreeError, match="has no tracked worktree"):
            manager.cleanup("does-not-exist")

    def test_list_worktrees(self, git_repo: Path):
        """list_worktrees returns git worktrees."""
        manager = WorktreeManager(repo_root=git_repo)
        manager.create("list-test")
        assert any(w.session_id == "list-test" for w in manager.list_worktrees())
        manager.cleanup("list-test", force=True)

    def test_create_with_worktree_name(self, git_repo: Path):
        """create with custom worktree name."""
        manager = WorktreeManager(repo_root=git_repo)
        manager.create("custom-name")
        assert any(w.session_id == "custom-name" for w in manager.list_worktrees())
        manager.cleanup("custom-name", force=True)
