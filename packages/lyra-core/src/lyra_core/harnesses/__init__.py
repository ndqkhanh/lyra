"""Deprecated re-export shim: :mod:`lyra_core.harnesses` → :mod:`lyra_core.adapters`.

In v3.5 the package was renamed from ``harnesses`` to ``adapters`` to
align with the rest of the codebase (Lyra is a *harness* — its plugins
are *adapters* to upstream orchestration strategies, not harnesses
themselves).

All existing imports of the form

    from lyra_core.harnesses import HarnessPlugin
    from lyra_core.harnesses.base import get_harness
    from lyra_core.harnesses.dag_teams import DAG, Scheduler

continue to work via this shim. New code should prefer the canonical
``lyra_core.adapters`` path. The shim is scheduled for removal in v4.0.
"""
from __future__ import annotations

import warnings

from lyra_core.adapters import (
    DAG,
    DAGValidationError,
    HarnessPlugin,
    Node,
    Scheduler,
    get_harness,
    register_harness,
    validate_dag,
)

# Emit a single import-time DeprecationWarning so the user sees the
# rename when they run with -W default. We don't warn on every access
# because that would make pytest output unreadable.
warnings.warn(
    "lyra_core.harnesses is deprecated since v3.5; "
    "import from lyra_core.adapters instead. "
    "This shim will be removed in v4.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "DAG",
    "DAGValidationError",
    "HarnessPlugin",
    "Node",
    "Scheduler",
    "get_harness",
    "register_harness",
    "validate_dag",
]
