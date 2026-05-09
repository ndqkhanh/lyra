"""``lyra_core.auth`` — connect-flow primitives.

Three concerns live here:

* :mod:`~lyra_core.auth.preflight` — cheap HTTP round-trip that proves
  an API key actually works *before* we persist it. Returned as a
  :class:`~lyra_core.auth.preflight.PreflightResult`.
* :mod:`~lyra_core.auth.diagnostics` — translate raw HTTP status codes
  + bodies into single-line human-readable explanations.
* :mod:`~lyra_core.auth.store` — load/save ``~/.lyra/auth.json`` with
  mode-0600 enforcement so a leaked key requires a deliberate chmod.

These primitives back the ``lyra connect`` Typer subcommand and the
``/connect`` REPL slash; both lean on preflight + store to write keys
the user just pasted.

We deliberately do *not* re-export the submodule symbols here. Tests
monkey-patch ``lyra_core.auth.preflight._http_get`` directly, and a
package-level ``from .preflight import preflight`` would shadow the
submodule name with the function and break that pattern.
"""
from __future__ import annotations
