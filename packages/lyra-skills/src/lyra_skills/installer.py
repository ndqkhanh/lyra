"""Skill installer — copy a ``SKILL.md``-rooted directory into a target root.

Phase N.3 introduces the ``lyra skill add`` UX: point Lyra at a local
directory or a GitHub URL containing a ``SKILL.md`` and have it
materialise under ``~/.lyra/skills/<id>/`` (the user-global root).
The CLI command lives in ``lyra_cli.commands.skill``; this module is
the framework-agnostic installer the command shells out to.

We deliberately keep the installer in ``lyra_skills`` (not the CLI
package) so embedded callers can drive installs from a notebook
without pulling in Typer / Rich. The CLI is just a Typer wrapper.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .loader import SkillLoaderError, SkillManifest, _parse_skill_md


class SkillInstallError(Exception):
    """Raised on any failure during install (missing source, bad manifest, IO)."""


@dataclass(frozen=True)
class InstallResult:
    """What ``install_from_path`` reports back to the caller.

    Attributes:
        skill_id: Final ``id`` of the installed skill (taken from the
            manifest, *not* the source directory name).
        installed_path: Directory the skill now lives under.
        manifest: Parsed manifest of the freshly installed skill.
        replaced: ``True`` when an existing skill with the same id
            was overwritten (the installer takes a backup first; see
            :func:`install_from_path`).
    """

    skill_id: str
    installed_path: Path
    manifest: SkillManifest
    replaced: bool


# We allow loose ids (lowercase, dashes, underscores, dots, digits) so
# common GitHub repo names map straight to skill folders. Anything
# more permissive risks collisions with the SessionsStore validator
# style and breaks ``rm`` UX.
_SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _validate_id(skill_id: str) -> None:
    """Reject ids that would escape the skills root or collide on macOS."""
    if not skill_id:
        raise SkillInstallError("skill id must be a non-empty string")
    if skill_id in (".", ".."):
        raise SkillInstallError(f"reserved skill id: {skill_id!r}")
    # Fold for case-insensitive filesystems before pattern-matching.
    norm = skill_id.lower()
    if not _SAFE_ID_RE.match(norm):
        raise SkillInstallError(
            f"skill id {skill_id!r} must match [a-z0-9][a-z0-9._-]* "
            "(no separators, leading dot, or whitespace)"
        )


def _find_skill_md(root: Path) -> Path:
    """Locate the ``SKILL.md`` *closest* to *root* (BFS).

    The installer accepts directories that aren't perfectly rooted at
    ``SKILL.md`` (e.g. a git clone with a top-level README plus a
    nested ``skills/<id>/SKILL.md``). It picks the shallowest hit so
    a repo with many skills surfaces a clear error rather than
    silently grabbing one of them.
    """
    if not root.is_dir():
        raise SkillInstallError(f"source is not a directory: {root}")
    direct = root / "SKILL.md"
    if direct.is_file():
        return direct
    # BFS for shallowest SKILL.md
    queue: list[Path] = [root]
    found: list[Path] = []
    while queue:
        cur = queue.pop(0)
        for child in sorted(cur.iterdir()):
            if child.is_dir():
                queue.append(child)
            elif child.name == "SKILL.md":
                found.append(child)
    if not found:
        raise SkillInstallError(f"no SKILL.md found under {root}")
    if len(found) > 1:
        rels = sorted(str(p.relative_to(root)) for p in found)
        raise SkillInstallError(
            "multiple SKILL.md files found; pick a single skill directory: "
            + ", ".join(rels)
        )
    return found[0]


def install_from_path(
    source: Path | str,
    *,
    target_root: Path | str,
    overwrite: bool = False,
) -> InstallResult:
    """Install a skill rooted at *source* under ``<target_root>/<id>/``.

    The whole containing directory is copied (so authors can ship
    helper files alongside ``SKILL.md`` — schema templates, fixtures,
    etc.) but only the directory holding ``SKILL.md`` is treated as
    the skill body. Re-installing the same id with ``overwrite=False``
    raises; with ``overwrite=True`` we backup the existing dir to
    ``<id>.bak-N`` and replace it (cheap audit trail).

    Args:
        source: Local path containing a ``SKILL.md`` (directly or in
            a single subdirectory).
        target_root: Destination skills root, e.g.
            ``~/.lyra/skills``. Created if missing.
        overwrite: If ``True`` and the id already exists, swap it for
            the new copy; otherwise raise.

    Returns:
        :class:`InstallResult` describing what landed on disk.

    Raises:
        SkillInstallError: source missing, id collision, IO failure.
    """
    src_path = Path(source).expanduser().resolve()
    target = Path(target_root).expanduser().resolve()

    skill_md = _find_skill_md(src_path)
    src_dir = skill_md.parent

    try:
        manifest = _parse_skill_md(skill_md)
    except SkillLoaderError as e:
        raise SkillInstallError(str(e)) from e

    _validate_id(manifest.id)
    target.mkdir(parents=True, exist_ok=True)
    dst_dir = target / manifest.id

    replaced = False
    if dst_dir.exists():
        if not overwrite:
            raise SkillInstallError(
                f"skill {manifest.id!r} already installed at {dst_dir}; "
                "pass overwrite=True (or `--force`) to replace it"
            )
        # Move existing aside as a numbered backup so a botched
        # install can be reverted by hand without grepping the
        # filesystem for the older copy.
        for n in range(1, 1000):
            backup = dst_dir.with_name(f"{manifest.id}.bak-{n}")
            if not backup.exists():
                dst_dir.rename(backup)
                break
        else:  # pragma: no cover — astronomically unlikely
            raise SkillInstallError(
                f"too many backups of {manifest.id} already on disk; clean them up"
            )
        replaced = True

    try:
        shutil.copytree(src_dir, dst_dir)
    except OSError as e:
        raise SkillInstallError(f"failed to copy skill into {dst_dir}: {e}") from e

    new_manifest = _parse_skill_md(dst_dir / "SKILL.md")
    return InstallResult(
        skill_id=manifest.id,
        installed_path=dst_dir,
        manifest=new_manifest,
        replaced=replaced,
    )


def install_from_git(
    repo_url: str,
    *,
    target_root: Path | str,
    overwrite: bool = False,
    subpath: Optional[str] = None,
    ref: Optional[str] = None,
) -> InstallResult:
    """Clone *repo_url* into a tempdir, then install via :func:`install_from_path`.

    Args:
        repo_url: Anything ``git clone`` accepts (HTTPS, SSH, local
            ``file://``).
        target_root: See :func:`install_from_path`.
        overwrite: See :func:`install_from_path`.
        subpath: When the repo contains multiple skills, point at the
            subdirectory holding the one to install.
        ref: Optional git ref (branch, tag, commit) to check out.

    The function shells out to ``git`` because depending on
    GitPython would force a heavy install on every Lyra user just to
    let a handful of them install skills from URLs. Errors propagate
    as :class:`SkillInstallError` so callers don't need to know git's
    exit-code conventions.
    """
    if shutil.which("git") is None:
        raise SkillInstallError(
            "`git` not found on PATH; install git or use install_from_path "
            "with a local clone"
        )

    with tempfile.TemporaryDirectory(prefix="lyra-skill-") as tmp:
        clone_dir = Path(tmp) / "clone"
        cmd: list[str] = ["git", "clone", "--depth", "1"]
        if ref:
            cmd += ["--branch", ref]
        cmd += [repo_url, str(clone_dir)]
        try:
            subprocess.run(  # noqa: S603 — explicit argv, not shell
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise SkillInstallError(
                f"git clone failed for {repo_url}: "
                f"{(e.stderr or e.stdout or '').strip()}"
            ) from e
        source = clone_dir / subpath if subpath else clone_dir
        return install_from_path(
            source, target_root=target_root, overwrite=overwrite
        )


def list_installed(target_root: Path | str) -> list[SkillManifest]:
    """Return manifests for every skill under *target_root*.

    Wraps :func:`load_skills` with a single-root convention so the
    CLI's ``lyra skill list`` command renders a stable list without
    running discovery against the packaged / project roots too.
    """
    from .loader import load_skills

    return load_skills([Path(target_root)])


def remove_installed(skill_id: str, *, target_root: Path | str) -> Path:
    """Delete ``<target_root>/<skill_id>/`` and return its old path.

    Validates *skill_id* the same way :func:`install_from_path` does,
    so a malicious caller can't pass ``../../etc`` and rmtree
    arbitrary directories. Missing skill ⇒ :class:`SkillInstallError`
    (silent removal would hide typos).
    """
    _validate_id(skill_id)
    target = Path(target_root).expanduser().resolve() / skill_id
    if not target.exists():
        raise SkillInstallError(f"skill not installed: {skill_id!r}")
    if not target.is_dir():  # pragma: no cover — defensive
        raise SkillInstallError(f"unexpected non-directory at {target}")
    shutil.rmtree(target)
    return target


__all__ = [
    "InstallResult",
    "SkillInstallError",
    "install_from_git",
    "install_from_path",
    "list_installed",
    "remove_installed",
]
