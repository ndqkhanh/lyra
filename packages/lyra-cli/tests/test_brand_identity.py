"""Phase 0 — Brand identity contract for the v1.7.1 rename → LYRA.

These tests pin the *post-rename* state of the monorepo (the v1.7.1
``open-harness -> lyra`` step). They are written before any code moves
so we have a hard, automated definition of "done" for the rename.

Each test asserts one independently-checkable fact. If a test fails, the
message tells you exactly which file is still on the old brand so the
rename can be driven off this suite alone.

Path arithmetic: every path is computed relative to this file via
``Path(__file__).resolve().parents[N]`` so the tests survive the
``projects/open-harness/ -> projects/lyra/`` directory rename (the file
moves with its package, and the parents math stays the same).

The legacy scan covers *all* historical brand tokens:
``opencoding``, ``open-coding``, ``open_coding``, ``OpenCoding`` (v1.6),
``open-harness``, ``open_harness``, ``OpenHarness`` (v1.7).
Files that legitimately carry legacy tokens (migration docs, migration
modules, this file, CHANGELOG) must either be in the allowlist below or
carry the ``lyra-legacy-aware`` marker in their contents.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

# Test file lives at:
#   projects/<project-dir>/packages/<cli-pkg>/tests/test_brand_identity.py
#   parents[0]=tests, [1]=<cli-pkg>, [2]=packages, [3]=<project-dir>,
#   [4]=projects, [5]=repo root.
_TESTS_DIR = Path(__file__).resolve().parent
_CLI_PKG_DIR = _TESTS_DIR.parent
_PACKAGES_DIR = _CLI_PKG_DIR.parent
_PROJECT_DIR = _PACKAGES_DIR.parent
_PROJECTS_DIR = _PROJECT_DIR.parent
_REPO_ROOT = _PROJECTS_DIR.parent


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# -------------------------------------------------------------------- #
# 1. Project directory                                                 #
# -------------------------------------------------------------------- #
def test_project_dir_renamed_to_lyra() -> None:
    assert (_PROJECTS_DIR / "lyra").is_dir(), (
        f"Expected projects/lyra/ to exist; got {_PROJECT_DIR.name} "
        f"under {_PROJECTS_DIR}"
    )
    assert not (_PROJECTS_DIR / "open-harness").exists(), (
        "projects/open-harness/ should be renamed away to projects/lyra/."
    )
    assert not (_PROJECTS_DIR / "open-coding").exists(), (
        "projects/open-coding/ from v1.6 should have been renamed long ago."
    )


# -------------------------------------------------------------------- #
# 2. Workspace pyproject                                               #
# -------------------------------------------------------------------- #
def test_workspace_pyproject_name_is_lyra_workspace() -> None:
    ws = _PROJECTS_DIR / "lyra" / "pyproject.toml"
    assert ws.is_file(), f"workspace pyproject missing at {ws}"
    content = _read(ws)
    assert 'name = "lyra-workspace"' in content, (
        "workspace [project].name must be 'lyra-workspace'"
    )


def test_workspace_testpaths_and_ruff_point_at_lyra_packages() -> None:
    ws_content = _read(_PROJECTS_DIR / "lyra" / "pyproject.toml")
    for pkg in ("core", "cli", "skills", "mcp", "evals"):
        expected = f'"packages/lyra-{pkg}/tests"'
        assert expected in ws_content, (
            f"workspace [tool.pytest].testpaths must include {expected}"
        )
        expected_src = f'"packages/lyra-{pkg}/src"'
        assert expected_src in ws_content, (
            f"workspace [tool.ruff].src must include {expected_src}"
        )


# -------------------------------------------------------------------- #
# 3. Each package pyproject                                            #
# -------------------------------------------------------------------- #
_EXPECTED_PACKAGES = ("core", "cli", "skills", "mcp", "evals")


@pytest.mark.parametrize("suffix", _EXPECTED_PACKAGES)
def test_each_package_name_is_lyra_prefixed(suffix: str) -> None:
    pkg_dir = _PROJECTS_DIR / "lyra" / "packages" / f"lyra-{suffix}"
    assert pkg_dir.is_dir(), f"missing package dir {pkg_dir}"
    content = _read(pkg_dir / "pyproject.toml")
    assert f'name = "lyra-{suffix}"' in content


def test_inter_package_dependencies_are_renamed() -> None:
    cli_pp = _read(
        _PROJECTS_DIR / "lyra" / "packages" / "lyra-cli" / "pyproject.toml"
    )
    assert '"lyra-core"' in cli_pp, (
        "lyra-cli must depend on lyra-core (not open-harness-core)"
    )
    assert '"open-harness-core"' not in cli_pp
    assert '"opencoding-core"' not in cli_pp


def test_package_data_refers_to_new_module_name() -> None:
    cli_pp = _read(
        _PROJECTS_DIR / "lyra" / "packages" / "lyra-cli" / "pyproject.toml"
    )
    assert '"lyra_cli"' in cli_pp, (
        "[tool.setuptools.package-data] key must be 'lyra_cli'"
    )
    assert '"open_harness_cli"' not in cli_pp
    assert '"opencoding_cli"' not in cli_pp


# -------------------------------------------------------------------- #
# 4. CLI entry scripts                                                 #
# -------------------------------------------------------------------- #
def test_cli_scripts_are_lyra_and_ly() -> None:
    cli_pp = _read(
        _PROJECTS_DIR / "lyra" / "packages" / "lyra-cli" / "pyproject.toml"
    )
    # Both scripts must exist, both must point at the new module.
    assert 'lyra = "lyra_cli.__main__:app"' in cli_pp, (
        "[project.scripts] must expose `lyra`"
    )
    assert 'ly = "lyra_cli.__main__:app"' in cli_pp, (
        "[project.scripts] must expose the short alias `ly`"
    )
    # And the legacy entry points must be gone.
    assert "open-harness = " not in cli_pp
    assert '\noh = ' not in cli_pp
    assert "opencoding = " not in cli_pp


# -------------------------------------------------------------------- #
# 5. Module imports under new names                                    #
# -------------------------------------------------------------------- #
@pytest.mark.parametrize("mod", [
    "lyra_core",
    "lyra_cli",
    "lyra_skills",
    "lyra_mcp",
    "lyra_evals",
])
def test_module_imports_under_new_name(mod: str) -> None:
    import importlib

    try:
        importlib.import_module(mod)
    except ModuleNotFoundError as exc:  # pragma: no cover - goes green post-rename
        pytest.fail(f"module `{mod}` must be importable after the rename ({exc})")


# -------------------------------------------------------------------- #
# 6. State dir default is `.lyra`, with chained legacy list            #
# -------------------------------------------------------------------- #
def test_repo_layout_state_dir_default_is_lyra(tmp_path: Path) -> None:
    try:
        from lyra_core.paths import RepoLayout
    except ModuleNotFoundError as exc:
        pytest.fail(f"lyra_core.paths.RepoLayout must exist ({exc})")

    layout = RepoLayout(repo_root=tmp_path)
    # The canonical attribute name is `state_dir`. `.open-harness` and
    # `.opencoding` are both legacy.
    assert layout.state_dir == tmp_path / ".lyra"


def test_repo_layout_exposes_chained_legacy_state_dirs(tmp_path: Path) -> None:
    """Migration must cover BOTH v1.6 (.opencoding) and v1.7 (.open-harness)."""
    try:
        from lyra_core.paths import RepoLayout
    except ModuleNotFoundError as exc:
        pytest.fail(f"lyra_core.paths.RepoLayout must exist ({exc})")

    layout = RepoLayout(repo_root=tmp_path)
    # List, newest-first: prefer migrating from .open-harness (closer),
    # fall back to .opencoding.
    assert layout.legacy_state_dirs == [
        tmp_path / ".open-harness",
        tmp_path / ".opencoding",
    ], "legacy_state_dirs must list newest-first: .open-harness, .opencoding"


# -------------------------------------------------------------------- #
# 7. Banner renders with the new brand tokens                          #
# -------------------------------------------------------------------- #
def test_banner_contains_new_brand_tokens(tmp_path: Path) -> None:
    try:
        from lyra_cli.interactive.banner import render_banner
    except ModuleNotFoundError as exc:
        pytest.fail(f"lyra_cli.interactive.banner.render_banner must exist ({exc})")

    ansi = re.compile(r"\x1b\[[0-9;]*m")
    banner = render_banner(
        repo_root=tmp_path,
        model="claude-opus-4.5",
        mode="plan",
        term_cols=140,
    )
    stripped = ansi.sub("", banner)
    # Brand name (display form) must be there; old brand must not be.
    assert "lyra" in stripped.lower()
    assert "open-harness" not in stripped.lower()
    assert "opencoding" not in stripped.lower()


# -------------------------------------------------------------------- #
# 8. No lingering legacy tokens in tracked source, docs, configs       #
# -------------------------------------------------------------------- #
# All historical brand tokens across v1.6 (opencoding) and v1.7
# (open-harness). After v1.7.1 the canonical brand is `lyra`.
_LEGACY_PATTERN = re.compile(
    r"opencoding|open-coding|open_coding|OpenCoding"
    r"|open-harness|open_harness|OpenHarness"
)

# Files that are allowed to mention legacy names on purpose.
# - CHANGELOG keeps the full rename history (v1.6 opencoding → v1.7
#   open-harness → v1.7.1 lyra).
# - docs/migration-to-lyra.md is the user-facing guide and explicitly
#   covers BOTH legacy brands.
# - this test file and test_state_dir_migration*.py literally assert
#   the migration contract and therefore carry legacy tokens by design.
# - migrations/state_v1.py must reference `.opencoding` to find it.
# - migrations/__init__.py hosts the chained `migrate_legacy_state`
#   orchestrator that walks both `.open-harness` and `.opencoding`.
# - lyra_core/paths.py exposes `legacy_state_dirs` for the migrator.
_ALLOWLIST_PATH_PARTS = (
    "CHANGELOG.md",
    "migration-to-lyra.md",
    "test_brand_identity.py",
    "test_state_dir_migration.py",
    "test_state_dir_migration_v2.py",
    "/migrations/state_v1.py",
    "/migrations/__init__.py",
    "/lyra_core/paths.py",
)

# A file can opt out of the scan by including this marker anywhere.
_LEGACY_AWARE_MARKER = "lyra-legacy-aware"

# Directories we never scan (generated / vendored).
_SKIP_DIRS = (
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".ruff_cache",
    ".mypy_cache",
    "refs",
    ".ui-refs",
    "node_modules",
    "build",
    "dist",
    ".egg-info",
)


_INTERESTING_SUFFIXES = {".py", ".toml", ".md", ".yaml", ".yml", ".txt", ".cfg", ".tmpl"}


def _iter_tracked_files() -> list[Path]:
    """Walk the Lyra project tree for code-ish files, skipping vendor/build dirs.

    Scope is ``projects/lyra/`` (the project directory), NOT the whole
    workspace — the contract is about Lyra's own tracked source, not stray
    files that may live under sibling projects in the same workspace.

    git-independent (this workspace isn't a checked-in git repo).
    """
    files: list[Path] = []
    for root, dirnames, filenames in os.walk(_PROJECT_DIR):
        # Prune skipped dirs in-place for efficiency.
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.endswith(".egg-info")]
        for name in filenames:
            p = Path(root) / name
            if p.suffix not in _INTERESTING_SUFFIXES:
                continue
            path_str = str(p)
            if any(part in path_str for part in _ALLOWLIST_PATH_PARTS):
                continue
            files.append(p)
    return files


def test_no_legacy_brand_tokens_in_tracked_source() -> None:
    offenders: list[str] = []
    for f in _iter_tracked_files():
        try:
            text = _read(f)
        except UnicodeDecodeError:
            continue
        # Opt-out marker lets the file carry legacy tokens intentionally.
        if _LEGACY_AWARE_MARKER in text:
            continue
        if _LEGACY_PATTERN.search(text):
            offenders.append(str(f.relative_to(_PROJECT_DIR)))
    assert not offenders, (
        "Legacy brand tokens still present in:\n  " + "\n  ".join(sorted(offenders))
    )
