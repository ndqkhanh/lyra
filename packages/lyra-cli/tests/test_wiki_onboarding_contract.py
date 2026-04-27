"""Wave-E Task 15: ``/wiki`` + ``/team-onboarding`` contract tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.session import InteractiveSession
from lyra_core.wiki import (
    WikiBundle,
    generate_onboarding,
    generate_wiki,
)


def _seed_repo(root: Path) -> None:
    pkgs = root / "packages"
    pkg = pkgs / "demo-pkg"
    (pkg / "src" / "demo_pkg").mkdir(parents=True)
    (pkg / "README.md").write_text(
        "# demo-pkg\n\nFirst paragraph that should appear in the wiki.\n\n"
        "Second paragraph that should NOT.\n",
        encoding="utf-8",
    )
    (pkg / "src" / "demo_pkg" / "__init__.py").write_text("'demo'\n", encoding="utf-8")


# ---------- generators -----------------------------------------------


def test_generate_wiki_emits_index_packages_inventory(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = generate_wiki(tmp_path)
    paths = {p.relative_path for p in bundle.pages}
    assert "index.md" in paths
    assert "packages/demo-pkg.md" in paths
    assert "inventory.md" in paths


def test_generate_wiki_includes_summary_from_readme(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = generate_wiki(tmp_path)
    pkg_page = next(p for p in bundle.pages if p.relative_path.endswith("demo-pkg.md"))
    assert "First paragraph" in pkg_page.body
    assert "Second paragraph" not in pkg_page.body


def test_generate_wiki_inventory_counts_python_files(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = generate_wiki(tmp_path)
    inv_page = next(p for p in bundle.pages if p.relative_path == "inventory.md")
    assert "python" in inv_page.body
    assert "1 file" in inv_page.body


def test_wiki_bundle_writes_to_disk(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    bundle = generate_wiki(tmp_path)
    target = bundle.write(tmp_path / ".lyra" / "wiki")
    assert (target / "index.md").exists()
    assert (target / "packages" / "demo-pkg.md").exists()
    assert (target / "inventory.md").exists()


def test_generate_onboarding_includes_role_specific_section(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    plan = generate_onboarding(tmp_path, role="engineer")
    md = plan.render()
    assert "engineer" in md.lower()
    assert "TDD" in md
    assert ".lyra/wiki/index.md" in md


def test_generate_onboarding_pm_role(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    plan = generate_onboarding(tmp_path, role="pm")
    md = plan.render()
    assert "Product surface" in md or "Roadmap" in md


def test_generate_onboarding_unknown_role_falls_back_to_engineer(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    plan = generate_onboarding(tmp_path, role="space-cadet")
    md = plan.render()
    assert "Day 1 — Environment" in md  # the engineer template


# ---------- slash commands ------------------------------------------


def test_slash_wiki_preview_default(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    s = InteractiveSession(repo_root=tmp_path)
    res = s.dispatch("/wiki")
    assert "Repo wiki" in res.output
    assert "demo-pkg" in res.output


def test_slash_wiki_generate_writes_to_disk(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    s = InteractiveSession(repo_root=tmp_path)
    res = s.dispatch("/wiki generate")
    target_dir = tmp_path / ".lyra" / "wiki"
    assert (target_dir / "index.md").exists()
    assert "wrote" in res.output and "page" in res.output


def test_slash_wiki_unknown_arg(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    s = InteractiveSession(repo_root=tmp_path)
    res = s.dispatch("/wiki rewind")
    assert "usage" in res.output


def test_slash_team_onboarding_default_engineer(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    s = InteractiveSession(repo_root=tmp_path)
    res = s.dispatch("/team-onboarding")
    assert "engineer" in res.output.lower()
    assert "Day 1" in res.output


def test_slash_team_onboarding_role_argument(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    s = InteractiveSession(repo_root=tmp_path)
    res = s.dispatch("/team-onboarding designer")
    assert "designer" in res.output.lower()
