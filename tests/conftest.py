"""pytest configuration for Lyra TUI tests.

Ensures the package is importable regardless of CWD.
"""
import sys
from pathlib import Path

# Ensure packages are importable
_HERE = Path(__file__).parent
_LYRA_CLI_SRC = _HERE / "packages" / "lyra-cli" / "src"
if _LYRA_CLI_SRC.is_dir() and str(_LYRA_CLI_SRC) not in sys.path:
    sys.path.insert(0, str(_LYRA_CLI_SRC))

# Optional mark for textual-dependent tests
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "textual: marks tests that require the `textual` library (skip if not installed)",
    )

def pytest_collection_modifyitems(items):
    """Auto-skip tests missing textual dependency."""
    import pytest
    try:
        import textual  # noqa: F401
    except ImportError:
        skip_textual = pytest.mark.skip(reason="requires textual library")
        for item in items:
            if "textual" in item.keywords:
                item.add_marker(skip_textual)
