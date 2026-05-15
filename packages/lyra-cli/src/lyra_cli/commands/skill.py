"""``lyra skill`` — install and inspect skills (Phase N.3).

The skill installer's logic lives in :mod:`lyra_skills.installer`; this
module is just the Typer wrapper that turns it into a command-line UX.
We intentionally keep the wrapper thin so embedded callers
(:class:`lyra_cli.client.LyraClient` users, the future HTTP API)
talk to the installer directly without going through Click.
"""
from __future__ import annotations

import json as _json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table


def _user_skills_root() -> Path:
    """Where ``lyra skill add`` writes by default.

    ``$LYRA_HOME`` overrides this so test suites and multi-tenant
    hosts can sandbox installs without prepending temp dirs to
    every command. Falls back to ``~/.lyra/skills`` (the same
    directory :func:`lyra_cli.interactive.skills_inject._user_skill_root`
    resolves at chat injection time).
    """
    home = os.environ.get("LYRA_HOME")
    base = Path(home) if home else Path.home() / ".lyra"
    return base / "skills"


skill_app = typer.Typer(
    name="skill",
    help=(
        "Install, list, and remove SKILL.md packs. "
        "Default install root is $LYRA_HOME/skills (~/.lyra/skills)."
    ),
    no_args_is_help=True,
)
_console = Console()


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


@skill_app.command("add")
def add(
    source: str = typer.Argument(
        ..., help="Local path or git URL pointing at a SKILL.md-rooted directory.",
    ),
    target: Optional[str] = typer.Option(
        None, "--target",
        help="Override install root (default: ~/.lyra/skills or $LYRA_HOME/skills).",
    ),
    subpath: Optional[str] = typer.Option(
        None, "--subpath",
        help="When the source repo holds many skills, point at one with this subpath.",
    ),
    ref: Optional[str] = typer.Option(
        None, "--ref", help="Git ref (branch/tag/commit) to checkout when source is a URL.",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing skill with the same id.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit a JSON result row."),
) -> None:
    """Install a skill from a local path or git URL."""
    from lyra_skills.installer import (
        SkillInstallError,
        install_from_git,
        install_from_path,
    )

    root = Path(target) if target else _user_skills_root()

    is_url = "://" in source or source.endswith(".git") or source.startswith("git@")
    try:
        if is_url:
            result = install_from_git(
                source,
                target_root=root,
                overwrite=force,
                subpath=subpath,
                ref=ref,
            )
        else:
            result = install_from_path(
                Path(source).expanduser(),
                target_root=root,
                overwrite=force,
            )
    except SkillInstallError as e:
        if json_out:
            typer.echo(_json.dumps({"ok": False, "error": str(e)}))
        else:
            _console.print(f"[red]install failed:[/] {e}")
        raise typer.Exit(code=1)

    payload = {
        "ok": True,
        "id": result.skill_id,
        "path": str(result.installed_path),
        "replaced": result.replaced,
        "version": result.manifest.version,
        "description": result.manifest.description,
    }
    if json_out:
        typer.echo(_json.dumps(payload))
    else:
        verb = "replaced" if result.replaced else "installed"
        _console.print(
            f"[green]{verb}[/] [bold]{result.skill_id}[/] "
            f"({result.manifest.version or 'no-version'}) → {result.installed_path}"
        )
        if result.manifest.description:
            _console.print(f"  [dim]{result.manifest.description}[/]")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@skill_app.command("list")
def _list(
    target: Optional[str] = typer.Option(
        None, "--target",
        help="Override install root (default: ~/.lyra/skills).",
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """List installed skills under the target root."""
    from lyra_skills.installer import list_installed

    root = Path(target) if target else _user_skills_root()
    skills = list_installed(root)

    if json_out:
        rows = [
            {
                "id": s.id,
                "name": s.name,
                "version": s.version,
                "description": s.description,
                "progressive": s.progressive,
                "applies_to": list(s.applies_to),
                "keywords": list(s.keywords),
                "path": s.path,
            }
            for s in skills
        ]
        typer.echo(_json.dumps(rows))
        return

    if not skills:
        _console.print(f"[dim]no skills installed under {root}[/]")
        return
    table = Table(title=f"installed skills — {root}")
    table.add_column("id", style="cyan")
    table.add_column("name")
    table.add_column("version")
    table.add_column("description", overflow="fold")
    for s in skills:
        table.add_row(s.id, s.name, s.version or "-", s.description or "")
    _console.print(table)


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------


@skill_app.command("remove")
def remove(
    skill_id: str = typer.Argument(..., help="Skill id to remove (must already be installed)."),
    target: Optional[str] = typer.Option(
        None, "--target", help="Override install root (default: ~/.lyra/skills).",
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Remove an installed skill."""
    from lyra_skills.installer import SkillInstallError, remove_installed

    root = Path(target) if target else _user_skills_root()
    try:
        removed = remove_installed(skill_id, target_root=root)
    except SkillInstallError as e:
        if json_out:
            typer.echo(_json.dumps({"ok": False, "error": str(e)}))
        else:
            _console.print(f"[red]remove failed:[/] {e}")
        raise typer.Exit(code=1)

    if json_out:
        typer.echo(_json.dumps({"ok": True, "id": skill_id, "path": str(removed)}))
    else:
        _console.print(f"[green]removed[/] [bold]{skill_id}[/] from {removed}")


# ---------------------------------------------------------------------------
# stats (Phase O.3 — Read-Write Reflective Learning)
# ---------------------------------------------------------------------------


def _format_age(ts: float, *, now: float) -> str:
    """Render ``ts`` as a compact relative age (``"3m ago"``, ``"never"``)."""
    if ts <= 0:
        return "never"
    delta = max(0.0, now - ts)
    if delta < 60:
        return f"{int(delta)}s ago"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    return f"{int(delta // 86400)}d ago"


@skill_app.command("stats")
def stats(
    top: Optional[int] = typer.Option(
        None,
        "--top",
        help="Show only the top-N skills by utility (default: all).",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit one JSON list of stats rows."
    ),
) -> None:
    """Show per-skill utility from the Read-Write Reflective Learning ledger.

    Phase O (v3.5): every progressive skill activation noted during a
    chat turn is settled to ``~/.lyra/skill_ledger.json`` on
    ``turn_complete`` (success) or ``turn_rejected`` (failure). This
    command surfaces the resulting utility table so users can see
    which skills earn their slot in the system prompt and which are
    candidates for ``lyra skill reflect``.

    Columns:

    * ``id`` — skill identifier (matches ``lyra skill list``).
    * ``successes`` / ``failures`` — count over the ledger's history.
    * ``utility`` — ``[-1.0, +1.0]`` blend of success ratio and
      recency. Negative = recent failures, 0 = unused / balanced,
      positive = useful.
    * ``last_used`` — relative age (``"3m ago"`` / ``"never"``).
    * ``last_failure_reason`` — verbatim reason from the most
      recent ``turn_rejected`` for this skill, truncated.
    """
    import time

    try:
        from lyra_skills.ledger import load_ledger, top_n, utility_score
    except Exception as e:
        if json_out:
            typer.echo(_json.dumps({"ok": False, "error": f"ledger unavailable: {e}"}))
        else:
            _console.print(f"[red]ledger unavailable:[/] {e}")
        raise typer.Exit(code=1)

    ledger = load_ledger()
    rows = top_n(ledger, n=top if top is not None else len(ledger.skills) or 1)
    if top is not None:
        rows = rows[: max(0, int(top))]

    now = time.time()

    if json_out:
        payload = [
            {
                "id": s.skill_id,
                "successes": s.successes,
                "failures": s.failures,
                "utility": utility_score(s),
                "last_used_at": s.last_used_at,
                "last_used_age": _format_age(s.last_used_at, now=now),
                "last_failure_reason": s.last_failure_reason,
            }
            for s in rows
        ]
        typer.echo(_json.dumps(payload))
        return

    if not rows:
        _console.print("[dim]no skill activations recorded yet — chat with Lyra to populate the ledger[/]")
        return

    table = Table(title="skill ledger — utility-ranked")
    table.add_column("id", style="cyan", no_wrap=True)
    table.add_column("successes", justify="right", style="green")
    table.add_column("failures", justify="right", style="red")
    table.add_column("utility", justify="right")
    table.add_column("last_used", justify="right")
    table.add_column("last_failure_reason", overflow="fold")
    for s in rows:
        u = utility_score(s)
        u_style = "green" if u > 0.1 else ("red" if u < -0.1 else "yellow")
        reason = s.last_failure_reason
        if len(reason) > 64:
            reason = reason[:61] + "..."
        table.add_row(
            s.skill_id,
            str(s.successes),
            str(s.failures),
            f"[{u_style}]{u:+.2f}[/]",
            _format_age(s.last_used_at, now=now),
            reason,
        )
    _console.print(table)


# ---------------------------------------------------------------------------
# reflect (Phase O.4 — Read-Write Reflective Learning)
# ---------------------------------------------------------------------------


_REFLECT_PROMPT_TEMPLATE = """You are improving a Lyra skill that has been failing.

A "skill" is a markdown file (SKILL.md) that gets injected into the
agent's system prompt when its keywords match the user's request.
The skill is failing — the user is rejecting turns where this skill
was active. Your job is to rewrite SKILL.md so the agent's behaviour
matches what the user actually wanted.

Constraints:

* Keep the YAML front-matter (id, name, version, description, keywords).
* Bump ``version`` (semver patch or minor — your call).
* Preserve the skill's stated purpose; sharpen *how* it's applied.
* Be concrete: replace vague guidance with specific steps,
  examples, or anti-patterns.
* Keep the rewrite under 200 lines.

Output ONLY the full new SKILL.md, no markdown fences, no commentary.

==== current SKILL.md ====
{current_md}

==== ledger summary ====
skill_id: {skill_id}
successes: {successes}
failures: {failures}
last_failure_reason: {last_failure_reason}

==== recent failure outcomes ====
{recent_failures}

==== rewrite SKILL.md ====
"""


def _format_recent_failures(stats: object) -> str:
    """Pull the failure history from the ledger stats into a readable list."""
    history = getattr(stats, "history", []) or []
    failures = [h for h in history if getattr(h, "kind", "") == "failure"]
    if not failures:
        return "(no per-failure detail recorded)"
    lines: list[str] = []
    for f in failures[-10:]:
        ts = getattr(f, "ts", 0)
        det = getattr(f, "detail", "") or getattr(f, "error_kind", "") or "(no detail)"
        lines.append(f"- ts={ts:.0f}: {det}")
    return "\n".join(lines)


def _call_llm_for_reflection(prompt: str) -> str:
    """One-shot LLM call. Tests monkeypatch this to inject a stub.

    Uses :func:`lyra_cli.llm_factory.build_llm` to honour the user's
    configured default provider (CLI ``setup`` flow), so reflection
    runs through whichever model the user is paying for. Falls back
    to ``"auto"`` so a fresh install with no model selected still
    produces a sensible error rather than a stack trace.
    """
    from harness_core.messages import Message

    from ..llm_factory import build_llm

    provider = build_llm("auto")
    reply = provider.generate(
        [Message.user(prompt)],
        max_tokens=2048,
    )
    text = getattr(reply, "text", None) or getattr(reply, "content", None)
    if not isinstance(text, str):
        raise typer.Exit(code=1)
    return text


@skill_app.command("reflect")
def reflect(
    skill_id: str = typer.Argument(
        ..., help="Skill id to rewrite (must be installed locally)."
    ),
    target: Optional[str] = typer.Option(
        None, "--target",
        help="Override install root (default: ~/.lyra/skills).",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help=(
            "Write the LLM proposal to SKILL.md. Default is dry-run "
            "(prints proposal, leaves disk untouched). Backs up the "
            "previous SKILL.md to SKILL.md.bak."
        ),
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit a JSON proposal row."),
) -> None:
    """Propose an improved SKILL.md from recent failures (Phase O.4).

    Read-Write Reflective Learning closes the loop: when a skill has
    been failing (per ``lyra skill stats``), feed its current text
    plus its failure history into the LLM and let it propose a
    sharper version. Default is dry-run so you can inspect the
    proposal before committing; ``--apply`` writes it (with a
    ``SKILL.md.bak`` you can roll back to).

    The LLM uses the same provider as your default ``lyra chat``
    model (configured via ``lyra setup``), so reflection respects
    your budget settings and provider preferences.
    """
    root = Path(target) if target else _user_skills_root()
    skill_dir = root / skill_id
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        if json_out:
            typer.echo(
                _json.dumps(
                    {
                        "ok": False,
                        "error": f"skill '{skill_id}' is not installed under {root}",
                    }
                )
            )
        else:
            _console.print(
                f"[red]reflect failed:[/] skill '{skill_id}' is not installed under {root}"
            )
        raise typer.Exit(code=1)

    try:
        from lyra_skills.ledger import load_ledger
    except Exception as e:
        if json_out:
            typer.echo(_json.dumps({"ok": False, "error": f"ledger unavailable: {e}"}))
        else:
            _console.print(f"[red]reflect failed:[/] ledger unavailable: {e}")
        raise typer.Exit(code=1)

    ledger = load_ledger()
    stats = ledger.get(skill_id)
    if stats is None or stats.failures == 0:
        msg = (
            f"no failures recorded for skill '{skill_id}' — "
            f"reflection is failure-driven so there's nothing to learn yet."
        )
        if json_out:
            typer.echo(
                _json.dumps(
                    {
                        "ok": True,
                        "id": skill_id,
                        "applied": False,
                        "proposal": "",
                        "path": str(skill_md),
                        "skipped_reason": "no_failures",
                    }
                )
            )
        else:
            _console.print(f"[yellow]{msg}[/]")
        return

    current_md = skill_md.read_text(encoding="utf-8")
    prompt = _REFLECT_PROMPT_TEMPLATE.format(
        current_md=current_md,
        skill_id=skill_id,
        successes=stats.successes,
        failures=stats.failures,
        last_failure_reason=stats.last_failure_reason or "(unspecified)",
        recent_failures=_format_recent_failures(stats),
    )

    try:
        proposal = _call_llm_for_reflection(prompt)
    except typer.Exit:
        raise
    except Exception as e:
        if json_out:
            typer.echo(
                _json.dumps({"ok": False, "error": f"LLM call failed: {e}"})
            )
        else:
            _console.print(f"[red]reflect failed:[/] LLM call failed: {e}")
        raise typer.Exit(code=1)

    proposal = proposal.strip() + "\n"

    applied = False
    if apply:
        backup = skill_md.with_suffix(".md.bak")
        try:
            backup.write_text(current_md, encoding="utf-8")
            skill_md.write_text(proposal, encoding="utf-8")
            applied = True
        except OSError as e:
            if json_out:
                typer.echo(_json.dumps({"ok": False, "error": f"write failed: {e}"}))
            else:
                _console.print(f"[red]reflect failed:[/] write failed: {e}")
            raise typer.Exit(code=1)

    if json_out:
        typer.echo(
            _json.dumps(
                {
                    "ok": True,
                    "id": skill_id,
                    "applied": applied,
                    "proposal": proposal,
                    "path": str(skill_md),
                }
            )
        )
        return

    if applied:
        _console.print(
            f"[green]applied[/] proposal to [bold]{skill_id}[/] (backup: SKILL.md.bak)"
        )
    else:
        _console.print(
            f"[cyan]proposal[/] for [bold]{skill_id}[/] (dry-run, "
            f"re-run with --apply to commit):\n"
        )
        _console.print(proposal)


# ---------------------------------------------------------------------------
# consolidate (Phase O.5 — dream daemon)
# ---------------------------------------------------------------------------


_STOPWORDS = frozenset(
    """
    a an and are as at be but by can do does for from has have he her him his
    i in is it its like make me my of on or our please she should so
    that the their them there these they this to too us was we were
    what which who why will with would you your yours
    """.split()
)


def _stem(tok: str) -> str:
    """Drop trailing ``s``/``es`` on 5+ char tokens (naive plural strip).

    Lets ``test`` and ``tests`` match the same cluster without
    pulling in nltk. We deliberately leave shorter words alone
    (``is``, ``us``) and never strip a double-s ending (``glass``,
    ``compass``) — those would be over-aggressive false matches.
    """
    if len(tok) < 5:
        return tok
    if tok.endswith("ies") and len(tok) >= 6:
        return tok[:-3] + "y"
    if tok.endswith("ss"):
        return tok
    if tok.endswith("es") and len(tok) >= 6:
        return tok[:-2]
    if tok.endswith("s"):
        return tok[:-1]
    return tok


def _tokenise(text: str) -> set[str]:
    """Lower-case word-bag tokenisation, dropping stopwords + short tokens.

    Deliberately tiny: the goal is to cluster lexically-similar
    prompts, not to do real NLP. The skill-proposal LLM call gets
    the raw prompts back so it can read intent.
    """
    out: set[str] = set()
    for tok in "".join(c.lower() if c.isalnum() else " " for c in text).split():
        if len(tok) >= 3 and tok not in _STOPWORDS:
            out.add(_stem(tok))
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _load_user_prompts(events_path: Path) -> list[dict]:
    """Read ``events.jsonl`` and return ``user.prompt`` rows.

    Returns each prompt as ``{"line": str, "ts": str, "session_id":
    str, "tokens": set[str]}``. Malformed lines and non-prompt rows
    are silently dropped.
    """
    if not events_path.is_file():
        return []
    out: list[dict] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = _json.loads(line)
        except _json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or row.get("kind") != "user.prompt":
            continue
        data = row.get("data") or {}
        text = (data.get("line") or "").strip()
        if not text:
            continue
        out.append(
            {
                "line": text,
                "ts": row.get("ts") or "",
                "session_id": data.get("session_id") or "",
                "tokens": _tokenise(text),
            }
        )
    return out


def _cluster_prompts(
    prompts: list[dict], *, min_size: int = 3, similarity: float = 0.4
) -> list[list[dict]]:
    """Greedy single-link clustering by Jaccard similarity.

    O(n²) on the prompt list which is fine for typical user
    histories (hundreds of turns). Each prompt joins the first
    cluster whose centroid token set has Jaccard >= ``similarity``;
    otherwise it seeds a new cluster.

    Clusters smaller than ``min_size`` are dropped — a single
    occurrence isn't enough signal to justify a skill.
    """
    clusters: list[list[dict]] = []
    centroids: list[set[str]] = []
    for p in prompts:
        placed = False
        for i, cent in enumerate(centroids):
            if _jaccard(p["tokens"], cent) >= similarity:
                clusters[i].append(p)
                centroids[i] = cent | p["tokens"]
                placed = True
                break
        if not placed:
            clusters.append([p])
            centroids.append(set(p["tokens"]))
    return [c for c in clusters if len(c) >= min_size]


def _parse_skill_id(proposal_md: str) -> str | None:
    """Extract ``id:`` from the front-matter of a SKILL.md proposal."""
    lines = proposal_md.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.strip().startswith("id:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


_CONSOLIDATE_PROMPT_TEMPLATE = """You are designing a new Lyra skill from a recurring user request pattern.

A "skill" is a markdown file (SKILL.md) that gets injected into the
agent's system prompt when its keywords match the user's request.
Below are several user prompts that look semantically similar — the
user keeps asking for variants of the same thing. Propose a SKILL.md
that, if installed, would let the agent handle requests of this
shape consistently.

Constraints:

* Output ONLY a valid SKILL.md, including YAML front-matter:

      ---
      id: <kebab-case-id>
      name: <human readable>
      version: 0.1.0
      description: <one sentence>
      keywords: [k1, k2, k3]
      progressive: true
      ---

* Keep the body under 100 lines and concrete.
* Prefer ``progressive: true`` so the body only injects when keywords match.

==== recurring user prompts (cluster of {n}) ====
{samples}

==== now write SKILL.md ====
"""


def _call_llm_for_consolidation(prompt: str) -> str:
    """One-shot LLM call. Tests monkeypatch this to inject a stub.

    Mirrors :func:`_call_llm_for_reflection` so future-us can refactor
    them into a single ``_one_shot(prompt)`` helper without breaking
    tests.
    """
    from harness_core.messages import Message

    from ..llm_factory import build_llm

    provider = build_llm("auto")
    reply = provider.generate(
        [Message.user(prompt)],
        max_tokens=2048,
    )
    text = getattr(reply, "text", None) or getattr(reply, "content", None)
    if not isinstance(text, str):
        raise typer.Exit(code=1)
    return text


@skill_app.command("consolidate")
def consolidate(
    from_: str = typer.Option(
        ...,
        "--from",
        help="Path to events.jsonl (HIR log) to scan for recurring prompts.",
    ),
    target: Optional[str] = typer.Option(
        None,
        "--target",
        help="Override skills install root (default: ~/.lyra/skills).",
    ),
    min_cluster: int = typer.Option(
        3,
        "--min-cluster",
        help="Minimum cluster size to propose a candidate (default 3).",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help=(
            "Install accepted candidates directly into the skills root. "
            "Default is dry-run: candidates land in "
            "~/.lyra/skill_candidates/<id>/SKILL.md for review."
        ),
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit a JSON ``{candidates: […]}`` payload."
    ),
) -> None:
    """Scan recent sessions for recurring prompts → propose new skills (Phase O.5).

    Memento's "Dream Daemon" inspires this: when the same kind of
    user request shows up over and over, that's signal we should
    bake the response pattern into a SKILL.md so the agent stops
    re-deriving it from scratch every turn.

    Workflow:

    1. Read ``user.prompt`` rows from the HIR log (``--from``).
    2. Cluster lexically-similar prompts (Jaccard ≥ 0.4 on a small
       bag-of-words tokeniser, stopwords stripped). Singletons are
       discarded.
    3. For each cluster, ask the configured LLM to propose a
       SKILL.md.
    4. Without ``--apply``: write proposals under
       ``~/.lyra/skill_candidates/<id>/`` for human review.
       With ``--apply``: write directly under the skills root,
       skipping ids that already exist.
    """
    events_path = Path(from_).expanduser()
    prompts = _load_user_prompts(events_path)
    clusters = _cluster_prompts(prompts, min_size=int(min_cluster))

    target_root = Path(target) if target else _user_skills_root()
    candidates_root = target_root.parent / "skill_candidates"

    candidates: list[dict] = []
    for cluster in clusters:
        samples = "\n".join(f"- {p['line']}" for p in cluster[:8])
        prompt = _CONSOLIDATE_PROMPT_TEMPLATE.format(
            n=len(cluster),
            samples=samples,
        )
        try:
            proposal = _call_llm_for_consolidation(prompt).strip() + "\n"
        except typer.Exit:
            raise
        except Exception as e:
            candidates.append(
                {
                    "id": None,
                    "cluster_size": len(cluster),
                    "proposal": "",
                    "skipped_reason": f"llm_error:{e}",
                    "keywords": "",
                    "applied": False,
                }
            )
            continue

        sid = _parse_skill_id(proposal)
        if sid is None:
            candidates.append(
                {
                    "id": None,
                    "cluster_size": len(cluster),
                    "proposal": proposal,
                    "skipped_reason": "no_id_in_front_matter",
                    "keywords": "",
                    "applied": False,
                }
            )
            continue

        keywords = ""
        for line in proposal.splitlines():
            if line.strip().startswith("keywords:"):
                keywords = line.split(":", 1)[1].strip()
                break

        existing = (target_root / sid / "SKILL.md").is_file()
        if apply and existing:
            candidates.append(
                {
                    "id": sid,
                    "cluster_size": len(cluster),
                    "proposal": proposal,
                    "skipped_reason": "existing",
                    "keywords": keywords,
                    "applied": False,
                    "path": str(target_root / sid / "SKILL.md"),
                }
            )
            continue

        if apply:
            dest = target_root / sid
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "SKILL.md").write_text(proposal, encoding="utf-8")
            candidates.append(
                {
                    "id": sid,
                    "cluster_size": len(cluster),
                    "proposal": proposal,
                    "skipped_reason": None,
                    "keywords": keywords,
                    "applied": True,
                    "path": str(dest / "SKILL.md"),
                }
            )
        else:
            dest = candidates_root / sid
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "SKILL.md").write_text(proposal, encoding="utf-8")
            candidates.append(
                {
                    "id": sid,
                    "cluster_size": len(cluster),
                    "proposal": proposal,
                    "skipped_reason": None,
                    "keywords": keywords,
                    "applied": False,
                    "path": str(dest / "SKILL.md"),
                }
            )

    if json_out:
        typer.echo(_json.dumps({"ok": True, "candidates": candidates}))
        return

    if not candidates:
        _console.print(
            f"[dim]no recurring prompt clusters found in {events_path} "
            f"(min size {min_cluster}).[/]"
        )
        return

    table = Table(title=f"skill candidates from {events_path}")
    table.add_column("id", style="cyan")
    table.add_column("cluster", justify="right")
    table.add_column("status")
    table.add_column("path", overflow="fold")
    for cand in candidates:
        if cand["applied"]:
            status = "[green]installed[/]"
        elif cand.get("skipped_reason"):
            status = f"[yellow]skipped: {cand['skipped_reason']}[/]"
        else:
            status = "[cyan]proposed[/]"
        table.add_row(
            cand.get("id") or "-",
            str(cand["cluster_size"]),
            status,
            cand.get("path", "-"),
        )
    _console.print(table)


# ---------------------------------------------------------------------------
# optimize (Phase O.7 — closed-loop SKILL.md optimizer)
# ---------------------------------------------------------------------------


def _call_llm_for_optimize(
    prompt: str, *, system: str = "", max_tokens: int = 2048
) -> str:
    """One LLM call used by the optimizer Executor/Analyst/Mutator triple.

    Kept module-level so tests can monkeypatch a deterministic stub.
    The lyra provider doesn't natively expose Pydantic structured
    output, so the optimizer parses JSON from text — we just need a
    sync ``str -> str`` call here.
    """
    from harness_core.messages import Message

    from ..llm_factory import build_llm

    provider = build_llm("auto")
    messages: list = []
    if system:
        messages.append(Message.system(system))
    messages.append(Message.user(prompt))
    reply = provider.generate(messages, max_tokens=max_tokens, temperature=0.0)
    text = getattr(reply, "text", None) or getattr(reply, "content", None)
    if not isinstance(text, str):
        raise typer.Exit(code=1)
    return text


def _load_scenarios_yaml(path: Path) -> list:
    """Parse ``scenarios.yaml`` into a list of OptimizeScenario.

    Expected shape::

        - prompt: "user says X"
          eval: "did the agent do Y?"
        - prompt: "..."
          eval: "..."

    Accepts ``eval_criterion`` as an alias for ``eval`` so the YAML
    reads cleanly without quoting the reserved word.
    """
    import yaml

    from lyra_skills.optimizer import OptimizeScenario

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise typer.BadParameter(
            f"scenarios YAML at {path} must be a list of {{prompt, eval}} entries"
        )
    out: list = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            raise typer.BadParameter(
                f"scenarios[{i}] must be a mapping (got {type(row).__name__})"
            )
        prompt = str(row.get("prompt") or "").strip()
        criterion = str(
            row.get("eval_criterion") or row.get("eval") or ""
        ).strip()
        if not prompt or not criterion:
            raise typer.BadParameter(
                f"scenarios[{i}] needs both 'prompt' and 'eval' (got {row!r})"
            )
        out.append(OptimizeScenario(prompt=prompt, eval_criterion=criterion))
    if not out:
        raise typer.BadParameter(f"no scenarios in {path}")
    return out


class _ProviderLLMRunner:
    """Adapter binding lyra's provider call to the optimizer's protocol."""

    def call(self, prompt: str, *, system: str = "", max_tokens: int = 2048) -> str:
        return _call_llm_for_optimize(
            prompt, system=system, max_tokens=max_tokens
        )


@skill_app.command("optimize")
def optimize(
    skill_id: str = typer.Argument(
        ..., help="Skill id to optimize (must be installed locally)."
    ),
    scenarios: str = typer.Option(
        ...,
        "--scenarios",
        help="Path to scenarios YAML: list of {prompt, eval} entries.",
    ),
    target: Optional[str] = typer.Option(
        None,
        "--target",
        help="Override install root (default: ~/.lyra/skills).",
    ),
    max_rounds: int = typer.Option(
        20,
        "--max-rounds",
        min=1,
        max=50,
        help="Cap on optimizer iterations (each round = ~scenarios+2 LLM calls).",
    ),
    target_rate: float = typer.Option(
        1.0,
        "--target-rate",
        min=0.0,
        max=1.0,
        help="Stop early once pass rate hits this threshold.",
    ),
    apply: bool = typer.Option(
        False,
        "--apply",
        help=(
            "Write the optimized SKILL.md to disk (with .bak backup). "
            "Default is dry-run: print final score + unified diff."
        ),
    ),
    update_argus: bool = typer.Option(
        True,
        "--argus/--no-argus",
        help="Emit per-round telemetry to the Argus cascade (default on).",
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Run the Executor/Analyst/Mutator loop against a skill.

    Phase O.7 closes the lyra reflective-learning loop. Unlike
    ``lyra skill reflect`` (one-shot LLM rewrite), this command runs
    an iterative scored loop: score scenarios → analyse failures →
    propose ONE constrained mutation → re-score → accept if better,
    revert otherwise. Mutations are persisted to
    ``$LYRA_HOME/skill_mutations.jsonl`` for audit.

    Argus integration is on by default: each accepted round emits a
    ``SKILL_EXECUTED`` event and each rejected round emits
    ``SKILL_REJECTED``, so the Argus telemetry-driven promoter sees
    optimization wins as success signal.
    """
    import time as _time

    from lyra_skills.ledger import MutationRecord, append_mutation
    from lyra_skills.optimizer import (
        OptimizeResult,
        OptimizeRound,
        optimize_skill,
    )

    root = Path(target) if target else _user_skills_root()
    skill_dir = root / skill_id
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        msg = f"skill '{skill_id}' is not installed under {root}"
        if json_out:
            typer.echo(_json.dumps({"ok": False, "error": msg}))
        else:
            _console.print(f"[red]optimize failed:[/] {msg}")
        raise typer.Exit(code=1)

    scenarios_path = Path(scenarios).expanduser()
    if not scenarios_path.is_file():
        msg = f"scenarios YAML not found: {scenarios_path}"
        if json_out:
            typer.echo(_json.dumps({"ok": False, "error": msg}))
        else:
            _console.print(f"[red]optimize failed:[/] {msg}")
        raise typer.Exit(code=1)

    try:
        scenario_list = _load_scenarios_yaml(scenarios_path)
    except typer.BadParameter as e:
        if json_out:
            typer.echo(_json.dumps({"ok": False, "error": str(e)}))
        else:
            _console.print(f"[red]optimize failed:[/] {e}")
        raise typer.Exit(code=1)

    current_md = skill_md.read_text(encoding="utf-8")

    cascade = None
    if update_argus:
        try:
            cascade, _argus_root, _argus_skills = _build_argus_cascade(target)
        except Exception as e:  # noqa: BLE001 — argus is optional
            if not json_out:
                _console.print(
                    f"[yellow]argus telemetry disabled:[/] {e}"
                )
            cascade = None

    def _on_round(r: OptimizeRound) -> None:
        record = MutationRecord(
            ts=_time.time(),
            skill_id=skill_id,
            round_no=r.round_no,
            strategy=(
                r.mutation.strategy.value if r.mutation else ""
            ),
            pre_score=r.pre_score,
            post_score=r.post_score,
            accepted=r.accepted,
            target_section=(
                r.mutation.target_section if r.mutation else ""
            ),
            reasoning=(
                r.mutation.reasoning if r.mutation else ""
            ),
            error=r.error,
        )
        append_mutation(record)

        if cascade is not None:
            try:
                cascade.record_outcome(
                    skill_id,
                    success=r.accepted,
                    query=f"optimize round {r.round_no}",
                    score=r.post_score,
                    detail=(
                        r.mutation.reasoning if r.mutation else r.error
                    ),
                )
            except Exception:  # noqa: BLE001 — telemetry must never fail the loop
                pass

        if not json_out:
            verb = "[green]accept[/]" if r.accepted else "[yellow]revert[/]"
            strat = r.mutation.strategy.value if r.mutation else "-"
            note = r.error or (r.mutation.reasoning if r.mutation else "")
            _console.print(
                f"  round {r.round_no:>2}  {verb}  "
                f"{r.pre_score:.2f}→{r.post_score:.2f}  "
                f"[cyan]{strat}[/]  [dim]{note}[/]"
            )

    if not json_out:
        _console.print(
            f"[cyan]optimize[/] [bold]{skill_id}[/]  "
            f"({len(scenario_list)} scenarios, max {max_rounds} rounds, "
            f"target {target_rate:.2f})"
        )

    try:
        result: OptimizeResult = optimize_skill(
            skill_id,
            current_md=current_md,
            scenarios=scenario_list,
            llm=_ProviderLLMRunner(),
            max_rounds=max_rounds,
            target_pass_rate=target_rate,
            on_round=_on_round,
        )
    except Exception as e:  # noqa: BLE001 — surface LLM/IO errors uniformly
        if json_out:
            typer.echo(_json.dumps({"ok": False, "error": str(e)}))
        else:
            _console.print(f"[red]optimize failed:[/] {e}")
        raise typer.Exit(code=1)

    applied = False
    if apply and result.final_md != current_md:
        backup = skill_md.with_suffix(".md.bak")
        backup.write_text(current_md, encoding="utf-8")
        skill_md.write_text(result.final_md, encoding="utf-8")
        applied = True

    if json_out:
        payload = {
            "ok": True,
            "skill_id": result.skill_id,
            "initial_score": result.initial_score,
            "final_score": result.final_score,
            "rounds": [r.to_dict() for r in result.rounds],
            "target_reached": result.target_reached,
            "accepted_rounds": result.accepted_rounds,
            "applied": applied,
            "path": str(skill_md),
        }
        typer.echo(_json.dumps(payload))
        return

    _console.print(
        f"\n[bold]done[/]  initial={result.initial_score:.2f}  "
        f"final={result.final_score:.2f}  "
        f"rounds={len(result.rounds)} (accepted {result.accepted_rounds})  "
        f"target_reached={result.target_reached}"
    )
    if applied:
        _console.print(
            f"[green]applied[/] new SKILL.md to {skill_md} "
            f"(backup at {skill_md.with_suffix('.md.bak')})"
        )
    elif result.final_md != current_md:
        _console.print(
            "[dim]dry-run — re-run with --apply to write the new SKILL.md[/]"
        )
        if result.diff:
            _console.print(result.diff)


# ---------------------------------------------------------------------------
# Argus cascade commands (V3.8 Theme A)
# ---------------------------------------------------------------------------


def _build_argus_cascade(target: Optional[str]):
    """Construct a :class:`LyraArgusCascade` and index every installed skill.

    Lazy import keeps the ``harness_skill_router`` dependency off the
    cold path of unrelated commands.
    """
    from lyra_skills.argus_cascade import LyraArgusCascade
    from lyra_skills.installer import list_installed

    root = Path(target) if target else _user_skills_root()
    skills = list_installed(root)
    cascade = LyraArgusCascade()
    cascade.index_manifests(skills)
    return cascade, root, skills


@skill_app.command("route")
def route(
    query: str = typer.Argument(..., help="Natural-language description of what you need."),
    target: Optional[str] = typer.Option(
        None, "--target", help="Override install root (default: ~/.lyra/skills).",
    ),
    mode: str = typer.Option(
        "auto", "--mode",
        help="Cascade mode: auto, keyword, or semantic.",
    ),
    top_k: int = typer.Option(3, "--top-k", min=1, max=20),
    trace: bool = typer.Option(
        False, "--trace",
        help="Emit the full reasoning trace (per-tier elapsed_ms + bright lines).",
    ),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Route a query through Argus's five-tier cascade and rank the picks."""
    cascade, root, skills = _build_argus_cascade(target)
    if not skills:
        if json_out:
            typer.echo(_json.dumps({"ok": True, "picks": [], "reason": "no skills"}))
            return
        _console.print(f"[dim]no skills installed under {root}[/]")
        return

    result = cascade.route(query, mode=mode, top_k=top_k)

    if json_out:
        payload = {
            "ok": True,
            "query": query,
            "mode": mode,
            "picks": [
                {"id": p.manifest.id, "score": p.score, "reason": p.reason}
                for p in result.picks
            ],
        }
        if trace:
            payload["trace"] = {
                "tiers": list(result.tier_names),
                "elapsed_ms": result.total_elapsed_ms,
                "cost_usd": result.total_cost_usd,
                "bright_lines": list(result.bright_lines_tripped),
            }
        typer.echo(_json.dumps(payload))
        return

    if result.is_empty:
        _console.print(f"[dim]no skill matched '{query}' (mode={mode})[/]")
        return

    table = Table(title=f"argus route — {query!r} (mode={mode})")
    table.add_column("rank", justify="right")
    table.add_column("id", style="cyan")
    table.add_column("score", justify="right")
    table.add_column("reason", overflow="fold")
    for idx, pick in enumerate(result.picks, start=1):
        table.add_row(str(idx), pick.manifest.id, f"{pick.score:.3f}", pick.reason)
    _console.print(table)

    if trace:
        _console.print(
            f"[dim]tiers={list(result.tier_names)} "
            f"elapsed_ms={result.total_elapsed_ms:.2f} "
            f"bright_lines={list(result.bright_lines_tripped)}[/]"
        )


@skill_app.command("quality")
def quality(
    target: Optional[str] = typer.Option(None, "--target"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Run Argus's A7 description-quality scorer over the catalog."""
    cascade, root, skills = _build_argus_cascade(target)
    if not skills:
        _console.print(f"[dim]no skills installed under {root}[/]")
        return

    report = cascade.quality_score()

    if json_out:
        try:
            payload = report.to_json()  # type: ignore[attr-defined]
        except AttributeError:
            payload = {"summary": str(report)}
        typer.echo(_json.dumps(payload, default=str))
        return

    _console.print(report)


@skill_app.command("heartbeat")
def heartbeat(
    target: Optional[str] = typer.Option(None, "--target"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Run one Argus refinement pass — drift detection + telemetry rollup."""
    cascade, root, skills = _build_argus_cascade(target)
    if not skills:
        _console.print(f"[dim]no skills installed under {root}[/]")
        return

    result = cascade.heartbeat()

    if json_out:
        try:
            payload = {
                "ok": True,
                "drift_reports": [str(r) for r in getattr(result, "drift_reports", [])],
            }
        except Exception:
            payload = {"ok": True, "summary": str(result)}
        typer.echo(_json.dumps(payload))
        return

    _console.print(result)


@skill_app.command("retract")
def retract(
    skill_id: str = typer.Argument(..., help="Skill id to tombstone."),
    reason: str = typer.Option(
        ..., "--reason",
        help="Reason for retraction (lands in the Argus tombstone ledger).",
    ),
    target: Optional[str] = typer.Option(None, "--target"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Tombstone a skill so Argus never re-imports it (failure mode F-24)."""
    cascade, root, _skills = _build_argus_cascade(target)
    try:
        cascade.retract(skill_id, reason=reason)
    except KeyError:
        if json_out:
            typer.echo(_json.dumps({"ok": False, "error": f"unknown skill {skill_id!r}"}))
            raise typer.Exit(code=1)
        _console.print(f"[red]unknown skill {skill_id!r}[/]")
        raise typer.Exit(code=1)

    if json_out:
        typer.echo(_json.dumps({"ok": True, "skill_id": skill_id, "reason": reason}))
        return
    _console.print(f"[green]retracted {skill_id!r}[/]: {reason}")


__all__ = ["skill_app"]
