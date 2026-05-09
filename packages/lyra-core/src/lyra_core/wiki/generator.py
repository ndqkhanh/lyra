"""Repo wiki + onboarding generators.

The wiki layout:

```
.lyra/wiki/
  index.md          ← repo overview + table of contents
  packages/
    <pkg>.md        ← one page per top-level package
  inventory.md      ← per-language file counts
```

Onboarding plans are pure dataclasses; the slash command renders
them as Markdown so they're easy to paste into a doc / Slack
thread without any extra formatting.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence


__all__ = [
    "OnboardingPlan",
    "WikiBundle",
    "WikiPage",
    "generate_onboarding",
    "generate_wiki",
]


# Files / dirs we always skip — keeps the wiki cheap and avoids
# leaking dev-environment noise into the briefing.
_DEFAULT_IGNORES: tuple[str, ...] = (
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".lyra",  # never recurse into the wiki we're writing
    "dist",
    "build",
    ".DS_Store",
)

_LANG_BY_EXT: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".md": "markdown",
    ".sh": "shell",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
}


@dataclass(frozen=True)
class WikiPage:
    """One markdown page produced by the generator."""

    relative_path: str        # e.g. ``packages/lyra-cli.md``
    title: str
    body: str

    def render(self) -> str:
        return f"# {self.title}\n\n{self.body.rstrip()}\n"


@dataclass(frozen=True)
class WikiBundle:
    """All pages produced by one generator run."""

    repo_root: Path
    pages: tuple[WikiPage, ...]

    def write(self, out_dir: Path | str | None = None) -> Path:
        target = Path(out_dir) if out_dir else (self.repo_root / ".lyra" / "wiki")
        for page in self.pages:
            page_path = target / page.relative_path
            page_path.parent.mkdir(parents=True, exist_ok=True)
            page_path.write_text(page.render(), encoding="utf-8")
        return target


@dataclass(frozen=True)
class OnboardingPlan:
    """A teammate's first-week briefing."""

    role: str
    repo_root: Path
    sections: tuple[tuple[str, str], ...]

    def render(self) -> str:
        lines = [f"# Onboarding plan — {self.role}", ""]
        lines.append(
            f"Repo root: `{self.repo_root}`. Auto-generated from the live "
            "wiki bundle; rerun ``/team-onboarding`` to refresh."
        )
        lines.append("")
        for heading, body in self.sections:
            lines.append(f"## {heading}")
            lines.append("")
            lines.append(body.rstrip())
            lines.append("")
        return "\n".join(lines)


# ----- helpers -------------------------------------------------------


def _iter_files(root: Path, ignores: Sequence[str]) -> Iterable[Path]:
    ignore_set = {*ignores}
    for current, dirs, files in os.walk(root):
        # Mutate in-place so os.walk skips ignored subtrees.
        dirs[:] = [d for d in dirs if d not in ignore_set]
        for fname in files:
            if fname in ignore_set:
                continue
            yield Path(current) / fname


def _detect_packages(root: Path) -> list[Path]:
    """Best-effort: a ``packages/`` dir or any direct subdir with ``src/``."""
    out: list[Path] = []
    pkgs = root / "packages"
    if pkgs.is_dir():
        out.extend(sorted(p for p in pkgs.iterdir() if p.is_dir()))
        return out
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "src").exists():
            out.append(child)
    return out


def _read_first_paragraph(path: Path) -> str:
    """Return the first non-heading paragraph of *path*.

    Markdown headings (``#``) are treated as scaffolding so the
    summary picks up the first real prose block — otherwise every
    package page would show its own H1 echo as the summary.
    """
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    chunks: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if chunks:
                break
            continue
        if stripped.startswith("#"):
            if chunks:
                break
            continue
        chunks.append(line.rstrip())
    return " ".join(chunks).strip()


def _language_inventory(root: Path, ignores: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in _iter_files(root, ignores):
        ext = path.suffix.lower()
        lang = _LANG_BY_EXT.get(ext)
        if lang is None:
            continue
        counts[lang] = counts.get(lang, 0) + 1
    return counts


def _package_summary(pkg: Path, summariser: Callable[[Path], str] | None) -> str:
    if summariser is not None:
        return summariser(pkg).strip()
    readme = pkg / "README.md"
    if readme.exists():
        para = _read_first_paragraph(readme)
        if para:
            return para
    pyproject = pkg / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        for line in text.splitlines():
            if line.strip().startswith("description"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return f"Top-level Python package at `{pkg.name}`."


# ----- public generators --------------------------------------------


def generate_wiki(
    repo_root: Path | str,
    *,
    ignores: Sequence[str] | None = None,
    summariser: Callable[[Path], str] | None = None,
) -> WikiBundle:
    """Crawl *repo_root* and produce a :class:`WikiBundle` (no I/O)."""
    root = Path(repo_root).resolve()
    ig = tuple(ignores) if ignores else _DEFAULT_IGNORES

    pages: list[WikiPage] = []

    # ---- packages ----------------------------------------------------
    packages = _detect_packages(root)
    pkg_lines = []
    for pkg in packages:
        rel = pkg.relative_to(root)
        summary = _package_summary(pkg, summariser)
        pkg_page = WikiPage(
            relative_path=f"packages/{pkg.name}.md",
            title=f"Package · {pkg.name}",
            body=(
                f"Path: `{rel}`\n\n"
                f"{summary}\n"
            ),
        )
        pages.append(pkg_page)
        pkg_lines.append(f"- [`{pkg.name}`](./packages/{pkg.name}.md): {summary}")

    # ---- language inventory -----------------------------------------
    inv = _language_inventory(root, ig)
    inv_body = "\n".join(
        f"- **{lang}**: {count} file(s)"
        for lang, count in sorted(inv.items(), key=lambda kv: (-kv[1], kv[0]))
    ) or "_no recognised source files_"
    pages.append(WikiPage(
        relative_path="inventory.md",
        title="Language inventory",
        body=inv_body,
    ))

    # ---- index ------------------------------------------------------
    overview_lines = [
        f"Repo root: `{root}`.",
        "",
        "## Packages",
        "",
        *(pkg_lines or ["_no packages detected_"]),
        "",
        "## See also",
        "",
        "- [Language inventory](./inventory.md)",
    ]
    pages.insert(0, WikiPage(
        relative_path="index.md",
        title=f"Repo wiki · {root.name}",
        body="\n".join(overview_lines),
    ))

    return WikiBundle(repo_root=root, pages=tuple(pages))


_DEFAULT_ROLE_TIPS: dict[str, list[tuple[str, str]]] = {
    "engineer": [
        (
            "Day 1 — Environment",
            "Clone the repo, install the workspace package, run the test suite. "
            "Read the top-level README first; then walk through the `Packages` "
            "section of the wiki index.",
        ),
        (
            "Day 2 — TDD posture",
            "Read CONTRIBUTING.md (if present) and the TDD section of the "
            "wiki. Pair on a single bugfix using RED → GREEN → REFACTOR.",
        ),
        (
            "Day 3 — Slash commands tour",
            "Run the REPL with `lyra repl --help`. Try `/effort`, `/checkpoint`, "
            "`/replay`, `/wiki`. These shape day-to-day collaboration.",
        ),
    ],
    "designer": [
        (
            "Day 1 — UI surface",
            "Open the `apps/web` (or equivalent) directory and run the dev "
            "server. The wiki packages page lists which package owns which "
            "surface.",
        ),
        (
            "Day 2 — Tokens + a11y",
            "Skim the design tokens module and the accessibility audit "
            "instructions in the wiki.",
        ),
    ],
    "pm": [
        (
            "Day 1 — Product surface",
            "Read the top-level README and skim the wiki index to see which "
            "components ship today.",
        ),
        (
            "Day 2 — Roadmap",
            "Read `docs/superpowers/plans/` for live roadmaps and waves; "
            "they're the source of truth for what's shipping next.",
        ),
    ],
}


def generate_onboarding(
    repo_root: Path | str,
    *,
    role: str = "engineer",
    extra_sections: Iterable[tuple[str, str]] | None = None,
) -> OnboardingPlan:
    """Build a role-specific onboarding plan rooted at *repo_root*."""
    root = Path(repo_root).resolve()
    role_key = role.lower().strip() or "engineer"
    base = _DEFAULT_ROLE_TIPS.get(role_key, _DEFAULT_ROLE_TIPS["engineer"])
    sections = list(base)
    bundle = generate_wiki(root)
    pkg_count = sum(1 for p in bundle.pages if p.relative_path.startswith("packages/"))
    sections.append((
        "What's in the repo right now",
        (
            f"{pkg_count} top-level package(s) detected. "
            "Open `.lyra/wiki/index.md` for the live tour generated by `/wiki`."
        ),
    ))
    if extra_sections:
        sections.extend(extra_sections)
    return OnboardingPlan(role=role_key, repo_root=root, sections=tuple(sections))
