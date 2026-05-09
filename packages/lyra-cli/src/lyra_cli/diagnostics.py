"""Probes powering ``lyra doctor`` and ``lyra setup``.

The check logic lives here as pure functions so the rich/Typer
front-ends in :mod:`commands.doctor` and :mod:`commands.setup` are
just renderers. Each probe returns a :class:`Probe` row — a
JSON-friendly snapshot of one health signal — and never raises
on a failed check (the *failure* is data, not an exception).

Probe categories:

* **runtime** — Python version, OS, ``git`` on PATH.
* **packages** — Lyra's own packages (``lyra-core``, ``lyra-skills``,
  …) plus optional integrations the user might have installed
  (``langsmith``, ``langfuse``, ``aiosandbox``).
* **providers** — env-var presence for every supported LLM
  provider; used by ``lyra setup`` to pick a default cascade and
  by ``lyra doctor`` to surface which keys the user still needs.
* **state** — repo-local layout (``SOUL.md``, ``policy.yaml``, the
  ``.lyra/`` tree) so the user can tell at a glance whether the
  current directory has been initialised.

The probes are deliberately *cheap*: no network hits, no provider
SDK construction. ``lyra doctor`` is supposed to run in <100ms on
every machine; expensive smoke tests live in dedicated commands
(``lyra evals``, ``lyra mcp doctor``).
"""
from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from .paths import RepoLayout


@dataclass(frozen=True)
class Probe:
    """One health-check row.

    Attributes:
        category: ``"runtime"`` | ``"packages"`` | ``"providers"``
            | ``"state"`` | ``"integration"``.
        name: Unique handle within the category (``anthropic-key``,
            ``lyra-core``, ``soul-md``).
        ok: ``True`` when the check passed, ``False`` when it failed.
        detail: Short human-readable string explaining the result —
            version number, file path, or "missing".
        meta: Free-form structured payload for callers (the JSON
            renderer ships this verbatim). Defaults to ``{}``.
    """

    category: str
    name: str
    ok: bool
    detail: str
    meta: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "name": self.name,
            "ok": self.ok,
            "detail": self.detail,
            "meta": dict(self.meta or {}),
        }


# Order matches the auto-cascade in :mod:`lyra_cli.llm_factory` so the
# UX puts the highest-precedence provider first — the user sees
# DeepSeek → Anthropic → OpenAI even when reading ``--json``.
_PROVIDER_KEYS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("deepseek", ("DEEPSEEK_API_KEY",)),
    ("anthropic", ("ANTHROPIC_API_KEY",)),
    ("openai", ("OPENAI_API_KEY",)),
    ("gemini", ("GEMINI_API_KEY", "GOOGLE_API_KEY")),
    ("xai", ("XAI_API_KEY", "GROK_API_KEY")),
    ("groq", ("GROQ_API_KEY",)),
    ("cerebras", ("CEREBRAS_API_KEY",)),
    ("mistral", ("MISTRAL_API_KEY",)),
    ("dashscope", ("DASHSCOPE_API_KEY", "QWEN_API_KEY")),
    ("openrouter", ("OPENROUTER_API_KEY",)),
)


def probe_runtime() -> list[Probe]:
    """Python / OS / git availability."""
    # Lyra's pyproject pins ``requires-python = ">=3.9"``; mirror that
    # here so the probe doesn't second-guess the package metadata
    # (and so it still passes on the same interpreter that ships the
    # CLI). Bump in lockstep with pyproject when we drop 3.9.
    python_ok = sys.version_info >= (3, 9)
    git_path = shutil.which("git")
    return [
        Probe(
            category="runtime",
            name="python",
            ok=python_ok,
            detail=sys.version.split()[0],
            meta={"required": ">=3.9", "actual": sys.version.split()[0]},
        ),
        Probe(
            category="runtime",
            name="platform",
            ok=True,
            detail=platform.platform(),
            meta={"system": platform.system(), "release": platform.release()},
        ),
        Probe(
            category="runtime",
            name="git",
            ok=git_path is not None,
            detail=git_path or "missing",
            meta={"path": git_path},
        ),
    ]


def probe_providers() -> list[Probe]:
    """Env-var presence for every supported LLM provider.

    A provider is "configured" when *any* of its accepted env vars
    is set to a non-empty string. We never read the value (just
    its presence), so this is safe to ship through ``--json``
    output.
    """
    out: list[Probe] = []
    for slug, env_vars in _PROVIDER_KEYS:
        present = next(
            (v for v in env_vars if (os.environ.get(v) or "").strip()),
            None,
        )
        out.append(
            Probe(
                category="providers",
                name=f"{slug}-key",
                ok=present is not None,
                detail=present or f"set one of {', '.join(env_vars)}",
                meta={"env_vars": list(env_vars), "found": present},
            )
        )
    return out


_LYRA_PACKAGES: tuple[str, ...] = (
    "lyra-core", "lyra-skills", "lyra-mcp", "lyra-evals", "lyra-cli",
)


_OPTIONAL_INTEGRATIONS: tuple[tuple[str, str], ...] = (
    ("langsmith", "LangSmith tracing observer"),
    ("langfuse", "Langfuse tracing observer"),
    ("aiosandbox", "Ephemeral container sandbox provider"),
    ("docker", "Docker SDK (sandbox runtime)"),
    ("rich", "Terminal rendering (required)"),
)


def probe_packages() -> list[Probe]:
    """Lyra's own packages + optional integrations."""
    out: list[Probe] = []
    for pkg in _LYRA_PACKAGES:
        try:
            ver = importlib_metadata.version(pkg)
            out.append(
                Probe(
                    category="packages",
                    name=pkg,
                    ok=True,
                    detail=ver,
                    meta={"version": ver, "optional": False},
                )
            )
        except importlib_metadata.PackageNotFoundError:
            out.append(
                Probe(
                    category="packages",
                    name=pkg,
                    ok=False,
                    detail="not installed",
                    meta={"version": None, "optional": False},
                )
            )
    for pkg, label in _OPTIONAL_INTEGRATIONS:
        try:
            ver = importlib_metadata.version(pkg)
            out.append(
                Probe(
                    category="integration",
                    name=pkg,
                    ok=True,
                    detail=f"{label} ({ver})",
                    meta={"version": ver, "optional": True, "label": label},
                )
            )
        except importlib_metadata.PackageNotFoundError:
            out.append(
                Probe(
                    category="integration",
                    name=pkg,
                    ok=False,
                    detail=f"{label} not installed",
                    meta={"version": None, "optional": True, "label": label},
                )
            )
    return out


def probe_state(repo_root: Path) -> list[Probe]:
    """Local repo layout (``.lyra/``, ``SOUL.md``, ``policy.yaml``)."""
    layout = RepoLayout(repo_root=Path(repo_root).resolve())
    targets = (
        ("soul-md", layout.soul_md, "SOUL.md (run `lyra init` to create)"),
        ("policy", layout.policy_yaml, "policy.yaml"),
        ("plans-dir", layout.plans_dir, "plans/"),
        ("sessions-dir", layout.sessions_dir, "sessions/"),
    )
    out: list[Probe] = [
        Probe(
            category="state",
            name="repo",
            ok=True,
            detail=str(layout.repo_root),
            meta={"path": str(layout.repo_root)},
        ),
    ]
    for name, path, label in targets:
        exists = path.exists()
        out.append(
            Probe(
                category="state",
                name=name,
                ok=exists,
                detail=str(path) if exists else f"{label} (missing)",
                meta={"path": str(path), "exists": exists, "label": label},
            )
        )
    return out


def run_all(repo_root: Path | str | None = None) -> list[Probe]:
    """Convenience: every probe, in stable category order.

    Tests, ``lyra doctor``, and ``lyra setup`` all share this
    aggregator so a future probe lands everywhere at once.
    """
    root = Path(repo_root or Path.cwd())
    out: list[Probe] = []
    out.extend(probe_runtime())
    out.extend(probe_state(root))
    out.extend(probe_packages())
    out.extend(probe_providers())
    return out


def configured_providers(probes: list[Probe] | None = None) -> list[str]:
    """Return slugs of providers with credentials present.

    Used by ``lyra setup`` to decide which provider to highlight
    as the recommended default. Order follows ``_PROVIDER_KEYS``
    (the auto-cascade order) so the first hit is the cheapest /
    most-preferred match.
    """
    rows = probes or probe_providers()
    return [
        p.name.removesuffix("-key")
        for p in rows
        if p.category == "providers" and p.ok
    ]


__all__ = [
    "Probe",
    "configured_providers",
    "probe_packages",
    "probe_providers",
    "probe_runtime",
    "probe_state",
    "run_all",
]
