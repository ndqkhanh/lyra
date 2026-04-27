"""Shared pytest fixtures for ``lyra-cli`` test suite.

The single autouse fixture in this file is the load-bearing one:
:func:`_isolate_lyra_state` redirects ``LYRA_HOME`` to a per-test
temporary directory before *every* test runs. Without it, the test
runner inherits the developer's real ``~/.lyra/auth.json`` (saved by
``lyra connect``) and the project's ``.env`` walked-up by
:func:`lyra_core.providers.dotenv.dotenv_value`.

Why this matters:

* Tests like ``test_build_llm_auto_raises_no_provider_configured…``
  asserts that with *no* provider configured the auto cascade fails
  loud. A real developer who has just run ``lyra connect deepseek
  …`` would persist a key into ``~/.lyra/auth.json``;
  :func:`lyra_cli.llm_factory._hydrate_env_from_authjson` would then
  resurrect it inside the test process and the cascade would silently
  pick deepseek, hiding the regression.

* Tests that pin a specific provider (e.g. ``OPENAI_API_KEY``) would
  see ``DEEPSEEK_API_KEY`` slip in ahead of them in the cascade.

The fixture also chdir's into ``tmp_path`` so the project-local
``.env`` walker can't escape the sandbox either. Tests that need the
real ``$HOME`` can override ``LYRA_HOME`` themselves — pytest's
``monkeypatch`` last-write-wins ordering guarantees that's safe.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_lyra_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Pin ``LYRA_HOME`` to ``tmp_path/.lyra`` and chdir into ``tmp_path``.

    Autouse so individual tests do not need to remember to clean up.
    The ``.lyra`` directory is *not* pre-created — tests that exercise
    "fresh install" paths expect ``mkdir(parents=True)`` to succeed
    without ``exist_ok=True`` on first contact, and the auth/budget
    stores ``mkdir(exist_ok=True)`` themselves before writing.
    """
    monkeypatch.setenv("LYRA_HOME", str(tmp_path / ".lyra"))
    monkeypatch.chdir(tmp_path)
