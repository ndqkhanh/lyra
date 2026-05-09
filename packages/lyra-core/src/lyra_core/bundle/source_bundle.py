"""L311-4 — Software 3.0 SourceBundle.

The bundle is six parts: persona + skills + tools + memory + evals +
verifier ([`docs/239`](../../../../../../docs/239-software-3-0-paradigm.md) §(b)).
Every part is required ((``LBL-BUNDLE-SIX``)); a bundle missing any
part fails validation and cannot be installed.

The bundle is **directory-shaped** (not a tarball, not a zip) so a
human can ``ls`` and ``cat`` the parts without unpacking. Tarball
distribution is a v3.11.x follow-up (just `tar -czf`).

The manifest is **stdlib-parseable** — keys are enumerable, values are
plain strings or short lists, no anchors / refs / merges. We
deliberately do not add a YAML dep just for this file; the parser is
~30 lines and lives in :func:`_parse_minimal_yaml`.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal


class BundleValidationError(ValueError):
    """Raised when a bundle is missing required parts or has invalid manifest."""


# ---- typed parts ------------------------------------------------------


@dataclass(frozen=True)
class PersonaSpec:
    """The system prompt / role text. Required."""

    path: str  # relative to bundle root, e.g. "persona.md"
    text: str

    @property
    def length_chars(self) -> int:
        return len(self.text)


@dataclass(frozen=True)
class SkillRef:
    """One Markdown skill file with progressive-disclosure frontmatter."""

    path: str
    name: str
    description: str
    frontmatter: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolSpec:
    """One tool — either a native handler name or an MCP server descriptor."""

    kind: Literal["native", "mcp"]
    name: str
    server: str | None = None  # for MCP: e.g. "stdio:./mcp/server.py"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemorySpec:
    """Seed memory file + optional schema descriptor."""

    seed_path: str
    seed_text: str
    schema_path: str | None = None


@dataclass(frozen=True)
class EvalSpec:
    """Eval suite — golden traces JSONL + judge rubric."""

    golden_path: str
    rubric_path: str
    eval_count: int  # number of trace lines in the JSONL


@dataclass(frozen=True)
class VerifierSpec:
    """Automated checker bound by task domain."""

    domain: str
    command: str
    budget_seconds: int


@dataclass(frozen=True)
class RoutineSpec:
    """One routine declaration from a bundle.yaml.

    Bundles can ship cron / webhook / api-triggered routines that
    Lyra v3.7 L37-8 registers at install time. The bundle's MCP
    server (or a named skill) is the routine's workflow.

    Manifest shape::

        routines:
          - kind: cron
            name: weekly-feed
            schedule: "0 9 * * MON"
            handler: skills/01-paper-ingest.md
          - kind: webhook
            name: on-paper-event
            handler: skills/01-paper-ingest.md
            repo: owner/repo
            events: push
          - kind: api
            name: manual-trigger
            handler: skills/01-paper-ingest.md
            path: /bundles/openfang/trigger
    """

    kind: Literal["cron", "webhook", "api"]
    name: str
    handler: str
    schedule: str = ""             # for cron
    timezone: str = "UTC"          # for cron
    repo: str = ""                 # for webhook
    events: tuple[str, ...] = ()   # for webhook
    path: str = ""                 # for api


# ---- manifest ---------------------------------------------------------


@dataclass(frozen=True)
class BundleManifest:
    api_version: str
    kind: str
    name: str
    version: str
    description: str = ""
    dual_use: bool = False
    smoke_eval_threshold: float = 0.95


# ---- bundle -----------------------------------------------------------


@dataclass(frozen=True)
class SourceBundle:
    """A loaded six-part bundle (plus optional routines)."""

    root: Path
    manifest: BundleManifest
    persona: PersonaSpec
    skills: tuple[SkillRef, ...]
    tools: tuple[ToolSpec, ...]
    memory: MemorySpec
    evals: EvalSpec
    verifier: VerifierSpec
    routines: tuple[RoutineSpec, ...] = ()

    # ---- factory --------------------------------------------------

    @classmethod
    def load(cls, root: Path | str) -> "SourceBundle":
        root = Path(root).resolve()
        if not root.is_dir():
            raise BundleValidationError(f"bundle root not a directory: {root}")
        manifest_path = root / "bundle.yaml"
        if not manifest_path.exists():
            raise BundleValidationError(
                f"missing bundle.yaml at {manifest_path}"
            )
        meta = _parse_minimal_yaml(manifest_path.read_text(encoding="utf-8"))

        manifest = BundleManifest(
            api_version=str(meta.get("apiVersion", "lyra.dev/v3")),
            kind=str(meta.get("kind", "SourceBundle")),
            name=_required_str(meta, "name"),
            version=_required_str(meta, "version"),
            description=str(meta.get("description", "")),
            dual_use=_as_bool(meta.get("dual_use", False)),
            smoke_eval_threshold=float(meta.get("smoke_eval_threshold", 0.95)),
        )

        persona = _load_persona(root, meta.get("persona", "persona.md"))
        skills = tuple(_load_skills(root, meta.get("skills", "skills/")))
        tools = tuple(_load_tools(meta.get("tools", [])))
        memory = _load_memory(root, meta.get("memory", {}))
        evals = _load_evals(root, meta.get("evals", {}))
        verifier = _load_verifier(meta.get("verifier", {}))
        routines = tuple(_load_routines(meta.get("routines", [])))

        bundle = cls(
            root=root,
            manifest=manifest,
            persona=persona,
            skills=skills,
            tools=tools,
            memory=memory,
            evals=evals,
            verifier=verifier,
            routines=routines,
        )
        return bundle

    # ---- validation -----------------------------------------------

    def validate(self) -> None:
        """Enforce ``LBL-BUNDLE-SIX``: every part must be non-empty."""
        if not self.persona.text.strip():
            raise BundleValidationError("persona text is empty")
        if not self.skills:
            raise BundleValidationError("skills list is empty")
        if not self.tools:
            raise BundleValidationError("tools list is empty")
        if not self.memory.seed_text.strip():
            raise BundleValidationError("memory seed is empty")
        if self.evals.eval_count == 0:
            raise BundleValidationError("evals.golden has no entries")
        if not self.verifier.command.strip():
            raise BundleValidationError("verifier.command is empty")
        if not (0.0 <= self.manifest.smoke_eval_threshold <= 1.0):
            raise BundleValidationError(
                f"smoke_eval_threshold {self.manifest.smoke_eval_threshold} "
                f"outside [0,1]"
            )

    # ---- hashing --------------------------------------------------

    def hash(self) -> str:
        """Stable content hash. Used by ``LBL-BUNDLE-IDEMPOTENT``."""
        h = hashlib.sha256()
        h.update(self.manifest.name.encode())
        h.update(b"\0")
        h.update(self.manifest.version.encode())
        h.update(b"\0")
        h.update(self.persona.text.encode())
        h.update(b"\0")
        for s in self.skills:
            h.update(s.path.encode())
            h.update(b"\0")
        for t in self.tools:
            h.update(f"{t.kind}:{t.name}".encode())
            h.update(b"\0")
        h.update(self.memory.seed_text.encode())
        h.update(b"\0")
        h.update(self.verifier.command.encode())
        return h.hexdigest()

    # ---- summary --------------------------------------------------

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.manifest.name,
            "version": self.manifest.version,
            "dual_use": self.manifest.dual_use,
            "skills": len(self.skills),
            "tools": len(self.tools),
            "evals": self.evals.eval_count,
            "verifier_domain": self.verifier.domain,
            "hash": self.hash()[:16],
        }


# ---- helpers ----------------------------------------------------------


def _required_str(meta: dict[str, Any], key: str) -> str:
    val = meta.get(key)
    if val is None or str(val).strip() == "":
        raise BundleValidationError(f"manifest missing required key {key!r}")
    return str(val)


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("true", "yes", "1", "y")


def _load_persona(root: Path, path: Any) -> PersonaSpec:
    rel = str(path)
    p = (root / rel).resolve()
    if not p.exists():
        raise BundleValidationError(f"persona file missing: {p}")
    return PersonaSpec(path=rel, text=p.read_text(encoding="utf-8"))


def _load_skills(root: Path, dir_path: Any) -> Iterable[SkillRef]:
    rel = str(dir_path).rstrip("/") + "/"
    skills_dir = (root / rel).resolve()
    if not skills_dir.is_dir():
        raise BundleValidationError(f"skills directory missing: {skills_dir}")
    for p in sorted(skills_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        meta, _ = _split_frontmatter(text)
        yield SkillRef(
            path=str(p.relative_to(root)),
            name=str(meta.get("name") or p.stem),
            description=str(meta.get("description") or ""),
            frontmatter=meta,
        )


def _load_tools(raw: Any) -> Iterable[ToolSpec]:
    if not isinstance(raw, list):
        return
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("kind", "native")
        if kind not in ("native", "mcp"):
            raise BundleValidationError(f"tool.kind must be native|mcp, got {kind!r}")
        yield ToolSpec(
            kind=kind,
            name=str(entry.get("name") or "?"),
            server=entry.get("server"),
            metadata={k: v for k, v in entry.items() if k not in ("kind", "name", "server")},
        )


def _load_memory(root: Path, raw: Any) -> MemorySpec:
    if not isinstance(raw, dict):
        raise BundleValidationError("memory section must be a mapping")
    seed = str(raw.get("seed") or "MEMORY.md")
    p = (root / seed).resolve()
    if not p.exists():
        raise BundleValidationError(f"memory seed missing: {p}")
    return MemorySpec(
        seed_path=seed,
        seed_text=p.read_text(encoding="utf-8"),
        schema_path=raw.get("schema"),
    )


def _load_evals(root: Path, raw: Any) -> EvalSpec:
    if not isinstance(raw, dict):
        raise BundleValidationError("evals section must be a mapping")
    golden = str(raw.get("golden") or "evals/golden.jsonl")
    rubric = str(raw.get("rubric") or "evals/rubric.md")
    gp = (root / golden).resolve()
    rp = (root / rubric).resolve()
    if not gp.exists():
        raise BundleValidationError(f"evals.golden missing: {gp}")
    if not rp.exists():
        raise BundleValidationError(f"evals.rubric missing: {rp}")
    eval_count = sum(
        1 for line in gp.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    return EvalSpec(golden_path=golden, rubric_path=rubric, eval_count=eval_count)


def _load_verifier(raw: Any) -> VerifierSpec:
    if not isinstance(raw, dict):
        raise BundleValidationError("verifier section must be a mapping")
    return VerifierSpec(
        domain=str(raw.get("domain") or "generic"),
        command=str(raw.get("command") or ""),
        budget_seconds=int(raw.get("budget_seconds") or 600),
    )


def _load_routines(raw: Any) -> Iterable[RoutineSpec]:
    """Parse the optional ``routines:`` section. Skips invalid entries
    rather than raising — bundles that don't ship routines have no
    section at all, and a malformed entry shouldn't sink the load."""
    if not isinstance(raw, list):
        return
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind") or "").strip()
        if kind not in ("cron", "webhook", "api"):
            continue
        name = str(entry.get("name") or "").strip()
        handler = str(entry.get("handler") or "").strip()
        if not name or not handler:
            continue
        events_raw = entry.get("events") or ()
        if isinstance(events_raw, str):
            events_raw = (events_raw,)
        yield RoutineSpec(
            kind=kind,  # type: ignore[arg-type]
            name=name,
            handler=handler,
            schedule=str(entry.get("schedule") or ""),
            timezone=str(entry.get("timezone") or "UTC"),
            repo=str(entry.get("repo") or ""),
            events=tuple(events_raw),
            path=str(entry.get("path") or ""),
        )


# ---- minimal YAML parser ----------------------------------------------


def _parse_minimal_yaml(text: str) -> dict[str, Any]:
    """Parse a deliberately-restricted YAML subset.

    Supports: top-level scalars, top-level mapping (`key: value`), list of
    mappings under a key (`tools: [-{...}, -{...}]` or block-style with
    `- key: value` lines), nested single-level mappings under a key.

    Anything fancier (anchors, multi-doc, flow-style mixed) is out of scope —
    add it when a bundle actually needs it, not preemptively.
    """
    result: dict[str, Any] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        # Top-level (column 0) only
        if raw[:1] in (" ", "\t"):
            i += 1
            continue
        m = re.match(r"^([a-zA-Z_][\w-]*)\s*:\s*(.*)$", raw)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            # Could be a nested block; collect the indented lines.
            block: list[str] = []
            j = i + 1
            while j < len(lines):
                s = lines[j]
                if s.strip() == "":
                    block.append(s)
                    j += 1
                    continue
                if s.startswith(" ") or s.startswith("\t"):
                    block.append(s)
                    j += 1
                    continue
                break
            i = j
            parsed = _parse_block(block)
            result[key] = parsed
        else:
            result[key] = _scalar(val)
            i += 1
    return result


def _parse_block(lines: list[str]) -> Any:
    """Parse a nested block (already de-indented context).

    Detects: list-of-mappings (first non-blank line starts with `- `) vs
    mapping. List items can span multiple lines, with sibling keys
    indented one level deeper than the leading ``- ``.
    """
    stripped = [l.rstrip() for l in lines if l.strip() and not l.lstrip().startswith("#")]
    if not stripped:
        return {}

    is_list = stripped[0].lstrip().startswith("- ")
    if is_list:
        out_list: list[Any] = []
        idx = 0
        while idx < len(stripped):
            line = stripped[idx]
            ls = line.lstrip()
            if not ls.startswith("- "):
                idx += 1
                continue
            payload = ls[2:]
            mm = re.match(r"^([a-zA-Z_][\w-]*)\s*:\s*(.*)$", payload)
            entry: dict[str, Any] = {}
            if mm:
                entry[mm.group(1)] = _scalar(mm.group(2).strip())
            # Sibling keys for this list item: subsequent lines that are
            # indented MORE than the `- ` line and don't start a new item.
            base_indent = len(line) - len(ls)
            idx2 = idx + 1
            while idx2 < len(stripped):
                sib = stripped[idx2]
                sib_ls = sib.lstrip()
                sib_indent = len(sib) - len(sib_ls)
                if sib_ls.startswith("- ") and sib_indent <= base_indent:
                    break
                if sib_indent <= base_indent:
                    break
                m2 = re.match(r"^([a-zA-Z_][\w-]*)\s*:\s*(.*)$", sib_ls)
                if m2:
                    entry[m2.group(1)] = _scalar(m2.group(2).strip())
                idx2 += 1
            out_list.append(entry)
            idx = idx2
        return out_list

    # Mapping block: collect key: value lines at any indent depth.
    out_map: dict[str, Any] = {}
    for l in stripped:
        mm = re.match(r"^\s+([a-zA-Z_][\w-]*)\s*:\s*(.*)$", l)
        if mm:
            out_map[mm.group(1)] = _scalar(mm.group(2).strip())
    return out_map


def _scalar(val: str) -> Any:
    if val == "" or val.lower() == "null":
        return None
    if val.lower() in ("true", "false"):
        return val.lower() == "true"
    if re.match(r"^-?\d+$", val):
        return int(val)
    if re.match(r"^-?\d+\.\d+$", val):
        return float(val)
    return val.strip("\"'")


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    head = text[4:end]
    body = text[end + 5 :]
    meta: dict[str, Any] = {}
    for raw_line in head.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.startswith("#"):
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = _scalar(v.strip())
    return meta, body


__all__ = [
    "BundleManifest",
    "BundleValidationError",
    "EvalSpec",
    "MemorySpec",
    "PersonaSpec",
    "RoutineSpec",
    "SkillRef",
    "SourceBundle",
    "ToolSpec",
    "VerifierSpec",
]
