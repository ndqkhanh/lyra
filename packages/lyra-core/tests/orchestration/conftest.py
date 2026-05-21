"""Test configuration for orchestration tests."""

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy for all tests."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()
