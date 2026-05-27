"""L4.1 — JournaledLLM proxy + mid-turn replay tests.

Requires harness_eternal (Restate-based testing harness) which is not yet
available in this repository. Skipped until harness_eternal package exists.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="harness_eternal package not yet available")


def test_journaled_llm_stub() -> None:
    """Placeholder — tests ported when harness_eternal is ready."""
    pass
