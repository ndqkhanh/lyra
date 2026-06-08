"""Test fixtures for agent tests.

Provides a ``temp_cwd`` fixture that temporarily changes to a temporary
directory so that memory store files (``data/memory/*.json``) do not pollute
the project working tree.
"""

import os
import tempfile

import pytest


@pytest.fixture
def temp_cwd() -> str:
    """Temporarily change CWD to a temporary directory.

    Yields the tmpdir path.  The original CWD is restored after the test.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(old_cwd)
