"""Stdlib-only .env parser for provider credentials.

Mirrors claw-code's ``parse_dotenv`` / ``load_dotenv_file`` /
``dotenv_value`` semantics so users can move a ``.env`` file from
claw-code to Lyra without edits. Zero dependencies — we do not pull
``python-dotenv`` because the format is a trivial ``KEY=VALUE`` grammar
and shipping a 12-file package for that would bloat the CLI install.

Grammar (minimal, intentionally):

* Lines starting with ``#`` are comments.
* Blank lines are ignored.
* Lines without ``=`` are ignored (no ``KEY`` without value).
* ``export KEY=VALUE`` strips the export prefix.
* Values wrapped in matching single or double quotes are stripped.
* Whitespace around ``KEY`` and ``VALUE`` is trimmed; interior
  whitespace is preserved for values.

Anything fancier (variable interpolation, line continuations, etc.)
is intentionally not supported — simpler grammar = fewer edge-case
bugs. If a user needs interpolation they should use real shell
sourcing + ``env``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional


def parse_dotenv(content: str) -> Dict[str, str]:
    """Parse a ``.env`` file body into a dict.

    Returns a fresh dict on every call (no module-level cache); the
    parser is pure, so callers can safely memoise at a higher level if
    they want.
    """
    out: Dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        if not key:
            continue
        val = val.strip()
        if len(val) >= 2 and (
            (val.startswith('"') and val.endswith('"'))
            or (val.startswith("'") and val.endswith("'"))
        ):
            val = val[1:-1]
        out[key] = val
    return out


def load_dotenv_file(path: Path) -> Optional[Dict[str, str]]:
    """Read and parse a ``.env`` file from *path*.

    Returns ``None`` if the file is missing so callers can use this as
    a soft fallback (``load_dotenv_file(p) or {}``). Raises the usual
    ``PermissionError`` / encoding errors so real problems aren't
    silently swallowed.
    """
    try:
        body = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    return parse_dotenv(body)


def find_dotenv_path(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from *start* looking for a ``.env`` file.

    Mirrors claw-code's "nearest ancestor wins" lookup so users who
    invoke ``lyra`` from a sub-directory still pick up the project
    root's ``.env``. Returns ``None`` once the filesystem root is
    reached without a match. ``start`` defaults to ``Path.cwd()``;
    callers can pin it for tests.
    """
    try:
        here = (start or Path.cwd()).resolve()
    except FileNotFoundError:
        return None
    # ``Path.parents`` is finite; iterating includes the root itself
    # via the loop guard below. ``here`` is checked first so a project
    # root match short-circuits before any climb.
    for candidate in (here, *here.parents):
        env_path = candidate / ".env"
        if env_path.is_file():
            return env_path
    return None


def dotenv_value(key: str) -> Optional[str]:
    """Look up *key* in the nearest-ancestor ``.env`` file.

    Searches the current working directory first and walks up to the
    filesystem root, mirroring claw-code's discovery rule. Returns
    ``None`` when (a) no ``.env`` exists on the path, (b) the key is
    absent, or (c) the value is empty. The empty-string-as-None rule
    matches claw-code's behaviour and prevents false-positives for
    users who intentionally cleared a stale export with ``KEY=``.
    """
    path = find_dotenv_path()
    if path is None:
        return None
    values = load_dotenv_file(path)
    if not values:
        return None
    v = values.get(key, "")
    return v if v else None


__all__ = ["parse_dotenv", "load_dotenv_file", "find_dotenv_path", "dotenv_value"]
