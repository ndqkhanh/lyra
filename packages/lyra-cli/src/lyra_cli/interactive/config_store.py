"""Config store backing ``/config`` (Wave-C Task 11).

Lyra has historically scattered persistent settings across env vars
(``HARNESS_REASONING_EFFORT``), ad-hoc dotfiles (``~/.lyra/sessions``),
and runtime defaults (``InteractiveSession.theme = "aurora"``). That
worked fine while only one or two knobs existed; v1.7.5 ships nine,
and pretty soon we need a single source of truth users can hand-edit.

Design choices for this module:

* **One file per user, not per repo.** Settings like the chosen
  theme or vim mode follow the user across projects, so the default
  path is ``~/.lyra/config.yaml``. The repo-local override pattern
  (``./.lyra/config.yaml``) ships in Wave D.
* **Strings on disk.** All values are stored as strings; coercion to
  ``bool`` / ``float`` happens in :func:`apply_to_session` where the
  contract for each key is known. This keeps the YAML/JSON file
  trivially hand-editable (no ``true`` vs ``"true"`` foot-guns).
* **Soft YAML dependency.** PyYAML is optional; when missing we
  fall back to a forgiving line-oriented parser (``key: value``).
  Saving without PyYAML uses the same simple format. Round-trip
  fidelity is preserved for the well-known keys we care about.
* **Best-effort load.** Any exception while reading a malformed
  file is swallowed and we return an empty :class:`Config`. The
  REPL boot must never crash because the user's editor mangled the
  config; ``/config list`` will still show the defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Well-known keys recognised by the live session. The ordering here
# drives ``/config list``, so put the most-used knobs first.
KNOWN_KEYS: tuple[str, ...] = (
    "theme",
    "vim",
    "permission_mode",
    "tdd_gate",
    "effort",
    "budget_cap_usd",
    "model",
    "mode",
)

# Boolean aliases accepted by ``/config set`` for the ``vim`` /
# ``tdd_gate`` keys. Anything outside this set falls through to the
# raw string and the per-key validator decides what to do.
_TRUTHY = {"on", "true", "1", "yes", "y"}
_FALSY = {"off", "false", "0", "no", "n"}

# Hard cap on ``~/.lyra/config.yaml`` payload — a malicious or runaway
# editor-generated file (e.g. a YAML bomb / billion-laughs) must not
# DoS REPL boot. 256 KiB is comfortably more than the entire schema
# could ever need (8 known keys × generous values) and small enough
# that a buggy script can't fill RAM.
MAX_CONFIG_BYTES: int = 256 * 1024


@dataclass
class Config:
    """In-memory key→string store with optional disk backing."""

    path: Path | None = None
    _data: dict[str, str] = field(default_factory=dict, repr=False)

    # ---- factory ----------------------------------------------------------

    @classmethod
    def load(cls, path: Path | None) -> "Config":
        """Read ``path`` if it exists; otherwise return an empty store.

        The store remembers ``path`` so subsequent :meth:`save` calls
        don't need it re-passed. Files larger than
        :data:`MAX_CONFIG_BYTES` are refused with an empty store so a
        runaway ``~/.lyra/config.yaml`` (or a YAML bomb) cannot blow
        up REPL boot or starve memory.
        """
        if path is None:
            return cls(path=None)
        try:
            size = path.stat().st_size
        except (OSError, FileNotFoundError):
            return cls(path=path)
        if size > MAX_CONFIG_BYTES:
            # Treat oversized configs the same way we treat malformed
            # ones: pretend they're empty rather than crash, and let
            # the user re-`/config set` to recover.
            return cls(path=path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, FileNotFoundError):
            return cls(path=path)
        try:
            data = _parse(text)
        except Exception:
            # Defensive: a corrupt file must not break boot. Discard
            # the bad payload and let the user re-`/config set`.
            data = {}
        return cls(path=path, _data=data)

    # ---- accessors --------------------------------------------------------

    def get(self, key: str, *, default: str | None = None) -> str | None:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        # Coerce to string so the on-disk format stays line-oriented
        # and free of YAML type guessing.
        self._data[key] = "" if value is None else str(value)

    def as_dict(self) -> dict[str, str]:
        return dict(self._data)

    # ---- persistence ------------------------------------------------------

    def save(self) -> None:
        if self.path is None:
            return  # purely in-memory store; nothing to persist
        # Atomic write: a crash mid-save should leave the previous
        # config intact, not a half-truncated file.
        from .sessions_store import _atomic_write_text  # local: keep cold-start cheap

        _atomic_write_text(self.path, _dump(self._data))


# ---------------------------------------------------------------------------
# Bridge from Config → live InteractiveSession
# ---------------------------------------------------------------------------


def apply_to_session(cfg: Config, session: object) -> None:
    """Push known keys from ``cfg`` onto ``session`` in-place.

    Unknown keys are silently ignored — they're still stored on disk
    so future versions of Lyra can grow into them without losing the
    user's prior settings.
    """
    theme = cfg.get("theme")
    if theme:
        # Defer import to avoid a circular dep at module load.
        from . import themes as _t  # type: ignore[import-not-found]

        if theme in _t.names():
            setattr(session, "theme", theme)
            try:
                _t.set_active_skin(theme)
            except Exception:
                # Best-effort: a missing renderer dep should not
                # block boot.
                pass

    vim = cfg.get("vim")
    if vim is not None and vim.lower() in _TRUTHY | _FALSY:
        setattr(session, "vim_mode", _to_bool(vim))

    perm = cfg.get("permission_mode")
    if perm in {"strict", "normal", "yolo"}:
        setattr(session, "permission_mode", perm)

    tdd = cfg.get("tdd_gate")
    if tdd is not None and tdd.lower() in _TRUTHY | _FALSY:
        setattr(session, "tdd_gate_enabled", _to_bool(tdd))

    effort = cfg.get("effort")
    if effort:
        # Side-effect: also set the env vars the LLM provider reads,
        # so ``/effort`` and ``/config set effort=high`` stay in sync.
        try:
            from .effort import apply_effort

            apply_effort(effort)
        except Exception:
            pass

    cap = cfg.get("budget_cap_usd")
    if cap:
        try:
            setattr(session, "budget_cap_usd", float(cap))
        except (TypeError, ValueError):
            pass

    model = cfg.get("model")
    if model:
        setattr(session, "model", model)

    mode = cfg.get("mode")
    if mode:
        setattr(session, "mode", mode)


def to_bool(value: str) -> bool:
    """Public helper used by `_cmd_config` to coerce on/off → bool."""
    return _to_bool(value)


def _to_bool(value: str) -> bool:
    return value.lower() in _TRUTHY


# ---------------------------------------------------------------------------
# Tiny YAML-ish parser/dumper (PyYAML optional)
# ---------------------------------------------------------------------------


def _parse(text: str) -> dict[str, str]:
    """Parse ``text`` as ``key: value`` lines, falling back through PyYAML.

    Comments (``#``) and blank lines are skipped. Quoted values get
    their wrapping quotes stripped. PyYAML is preferred when available
    because it handles nested structures the line-oriented format
    can't, but the fallback covers the 95% case (flat string map).
    """
    try:
        import yaml  # type: ignore[import-not-found]

        loaded = yaml.safe_load(text)
        if isinstance(loaded, dict):
            return {str(k): _stringify(v) for k, v in loaded.items()}
    except Exception:
        # PyYAML missing or file is not real YAML — fall through.
        pass

    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        out[key] = value
    return out


def _dump(data: dict[str, str]) -> str:
    lines = ["# Lyra config — generated by /config; safe to hand-edit."]
    for key in sorted(data):
        value = data[key]
        # Quote values that look like comments or contain a colon so
        # the round-trip parser unambiguously picks them up.
        needs_quote = (":" in value) or value.lstrip().startswith("#")
        rendered = f'"{value}"' if needs_quote else value
        lines.append(f"{key}: {rendered}")
    return "\n".join(lines) + "\n"


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "on" if value else "off"
    return str(value)
