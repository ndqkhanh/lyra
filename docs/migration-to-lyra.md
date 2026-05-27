<!-- lyra-legacy-aware: this migration guide intentionally references both
     legacy names (`open-coding` / `.opencoding/` from v1.6 and
     `open-harness` / `.open-harness/` from v1.7) when explaining the rename
     chain that lands at `lyra` / `.lyra/` in v1.7.1. -->

# Migrating to **Lyra** (from `open-coding` *or* `open-harness`)

This project has been renamed twice. v1.7.1 finalizes the brand as
**Lyra** — a **L**ightweight **Y**ielding **R**easoning **A**gent — a
general-purpose, CLI-native coding agent harness. If you're upgrading from
**either** legacy release, this document is the one-stop reference: what
changed, what migrates automatically, what you have to do by hand, and
how to roll back.

> **v3.0.0 note.** As of v3.0.0 the TDD gate is an **opt-in plugin**,
> off by default. Sessions that were relying on the v1.x / v2.x
> auto-armed gate must add `/tdd-gate on` (or persist with
> `/config set tdd_gate=on` or `[plugins.tdd] enabled = true` in
> `~/.lyra/settings.toml`). The `/phase`, `/red-proof`, and
> `/tdd-gate` slashes still ship — see the new "v3.0.0 — TDD becomes
> opt-in" section near the bottom of this document.

| Release       | Brand            | Project state dir       | CLI                    | Alias |
|---------------|------------------|-------------------------|------------------------|-------|
| v1.6 and prior | `open-coding`   | `.opencoding/`          | `opencoding`           | —     |
| v1.7 (transitional) | `open-harness` | `.open-harness/`   | `open-harness`         | `oh`  |
| **v1.7.1** (current) | **`lyra`** | **`.lyra/`**         | **`lyra`**             | **`ly`** |

If you're on v1.6 (`.opencoding/`), you can jump straight to v1.7.1
— the chained migrator handles both transitions in a single first run.

## TL;DR

- Install the new CLI (`lyra`, alias `ly`).
- Run it once from your repo. It will:
  - Detect the newest legacy state dir (`.open-harness/` → else
    `.opencoding/`) and **copy** it to `.lyra/` (non-destructive — your
    old tree stays put).
  - Write the appropriate marker file at the root of `.lyra/`:
    `MIGRATED_FROM_OPEN_HARNESS` when the source was
    `.open-harness/`, or `MIGRATED_FROM_OPENCODING` when the
    source was `.opencoding/`. Each marker carries a one-line
    provenance note and is safe to delete after you've verified
    your state.
  - Do the same for the user-global state: `~/.open-harness/` or
    `~/.opencoding/` → `~/.lyra/`.
  - Migrate any legacy `~/.opencoding/sessions/*.jsonl` into
    `.lyra/state.db` (SQLite+FTS5).
- Update imports: `opencoding_*` or `open_harness_*` → `lyra_*`.
- Update any scripts that hard-coded `.opencoding/...` or
  `.open-harness/...` paths to `.lyra/...`.
- Old `opencoding` and `open-harness` CLIs are **not** aliased — swap
  the binary name in CI, Makefiles, and shell functions.

That's it for 95% of projects. The rest of this doc is the detailed map.

## What renamed (both hops)

| Concept                  | v1.6 (`open-coding`)            | v1.7 (`open-harness`)            | **v1.7.1 (`lyra`)**                |
|--------------------------|----------------------------------|-----------------------------------|-------------------------------------|
| Project directory        | `projects/open-coding/`          | `projects/open-harness/`          | **`projects/lyra/`**                |
| Primary CLI              | `opencoding`                     | `open-harness`                    | **`lyra`**                          |
| CLI alias                | —                                | `oh`                              | **`ly`**                            |
| Project state dir        | `./.opencoding/`                 | `./.open-harness/`                | **`./.lyra/`**                      |
| User-global state dir    | `~/.opencoding/`                 | `~/.open-harness/`                | **`~/.lyra/`**                      |
| Core package             | `opencoding-core`                | `open-harness-core`               | **`lyra-core`**                     |
| CLI package              | `opencoding-cli`                 | `open-harness-cli`                | **`lyra-cli`**                      |
| Skills package           | `opencoding-skills`              | `open-harness-skills`             | **`lyra-skills`**                   |
| MCP package              | `opencoding-mcp`                 | `open-harness-mcp`                | **`lyra-mcp`**                      |
| Evals package            | `opencoding-evals`               | `open-harness-evals`              | **`lyra-evals`**                    |
| Core import              | `from opencoding_core …`         | `from open_harness_core …`        | **`from lyra_core …`**              |
| CLI import               | `from opencoding_cli …`          | `from open_harness_cli …`         | **`from lyra_cli …`**               |
| Skills import            | `from opencoding_skills …`       | `from open_harness_skills …`      | **`from lyra_skills …`**            |
| Entry-point group        | `opencoding.plugins`             | `open_harness.plugins`            | **`lyra.plugins`**                  |

## What migrates automatically

On the first run of `lyra` (or `ly`) in a repo, the CLI invokes
`lyra_core.migrations.migrate_legacy_state`, which orchestrates the
chained migration. It walks the legacy source list **newest-first**
(`.open-harness/` → `.opencoding/`) and stops at the first hit:

1. If `.lyra/` already exists **and** is non-empty, migration is a
   no-op (idempotent — the orchestrator treats a populated
   destination as "already done" and leaves both sides untouched).
2. Otherwise, the orchestrator picks the newest legacy dir that
   exists and **recursively copies** it (not moves) to `.lyra/`.
3. The marker corresponding to the actual source directory is written
   to `.lyra/`. So a user who's been on v1.7 gets
   `MIGRATED_FROM_OPEN_HARNESS`; a user who skipped straight from
   v1.6 gets `MIGRATED_FROM_OPENCODING`. Either way, the run is
   idempotent.
4. The same logic runs for the user-global pair:
   `~/.open-harness/` *or* `~/.opencoding/` → `~/.lyra/`.

Why copy instead of move? Because if something blows up during
migration, you still have the untouched old tree to roll back to.

Why newest-first? Because a user who ran v1.7 *also* has v1.6 artifacts
sitting next to v1.7 artifacts. The v1.7 state is closer to v1.7.1 by
construction, so migrating *from* it preserves more work.

JSONL session logs (`~/.opencoding/sessions/*.jsonl` — from v1.6 days)
migrate separately via
`lyra_core.sessions.jsonl_migration.migrate_jsonl_sessions`: they're
parsed, inserted into `.lyra/state.db` (SQLite+FTS5, hermes pattern),
and a `JSONL_MIGRATED` manifest file is written alongside the
legacy `sessions/` directory listing the ingested file names, so
re-runs append only newly-added JSONL.

## What you have to do by hand

### 1. Install the new CLI

```bash
# Remove whichever old packages you had — both variants listed.
pip uninstall -y \
  opencoding-cli opencoding-core opencoding-skills opencoding-mcp opencoding-evals \
  open-harness-cli open-harness-core open-harness-skills open-harness-mcp open-harness-evals

python3 -m pip install -e packages/lyra-core \
                        -e packages/lyra-skills \
                        -e packages/lyra-mcp \
                        -e packages/lyra-evals \
                        -e packages/lyra-cli
```

`pip uninstall` is recommended — the old packages are **not** aliased,
and leaving multiple installed creates an import-resolution hazard
(Python will pick whichever is earliest on `sys.path`).

### 2. Swap CLI invocations

Search your repo for every legacy invocation and replace it. A
one-liner that covers both hops:

```bash
rg -l '\b(opencoding|open-harness|oh)\b' | xargs sed -i.bak \
  -e 's/\bopencoding\b/lyra/g' \
  -e 's/\bopen-harness\b/lyra/g' \
  -e 's/\boh\b/ly/g'
```

Typical hit sites:

- `Makefile` targets
- GitHub Actions / GitLab CI / Jenkinsfiles
- shell aliases / zsh functions / fish abbreviations
- pre-commit hooks
- `justfile`
- editor tasks (VSCode `tasks.json`, JetBrains run configurations)

Note the `\boh\b` match — if you used `oh` as a standalone word in
some other context (unlikely, but possible in shell aliases), filter
those false positives by hand. `ly` is even less likely to collide.

### 3. Swap Python imports

Same drill, now covering **both** legacy namespaces:

```bash
rg -l '(opencoding|open_harness)_(core|cli|skills|mcp|evals)' | xargs sed -i.bak \
  -e 's/opencoding_core/lyra_core/g' \
  -e 's/opencoding_cli/lyra_cli/g' \
  -e 's/opencoding_skills/lyra_skills/g' \
  -e 's/opencoding_mcp/lyra_mcp/g' \
  -e 's/opencoding_evals/lyra_evals/g' \
  -e 's/open_harness_core/lyra_core/g' \
  -e 's/open_harness_cli/lyra_cli/g' \
  -e 's/open_harness_skills/lyra_skills/g' \
  -e 's/open_harness_mcp/lyra_mcp/g' \
  -e 's/open_harness_evals/lyra_evals/g'
```

After this, re-run your test suite. If anything imports from the old
names, you'll get an `ImportError` — there's no shim, by design.

### 4. Swap config paths

If any of your configs, scripts, or docs hard-code `.opencoding/...` or
`.open-harness/...` paths, update them:

```bash
rg -l '\.(opencoding|open-harness)' | xargs sed -i.bak \
  -e 's#\.opencoding#.lyra#g' \
  -e 's#\.open-harness#.lyra#g'
```

Common offenders:

- `.gitignore` (e.g. `.opencoding/state.db`, `.open-harness/state.db`)
- Docker bind mounts (`-v $PWD/.open-harness:/data/.open-harness`)
- CI cache paths
- Custom plugins that read `.open-harness/config.toml`

### 5. Plugin developers: update entry-point groups

If you ship a plugin via `pyproject.toml`, update the entry-point
group name to the current one:

```toml
[project.entry-points."lyra.plugins"]
my_plugin = "my_pkg.plugin:Plugin"
```

(was `opencoding.plugins` in v1.6, `open_harness.plugins` in v1.7.)

### 6. If you use the MCP namespace

The MCP server/client moved too. If you reference the server's manifest
URL by path, replace `/opencoding/mcp` or `/open-harness/mcp` with
`/lyra/mcp` in whatever serves it.

## Behavioral changes you should know about

Everything in this section landed in the v1.7 fusion release and
survives unchanged through v1.7.1 — only the names and state-dir
location changed between v1.7 and v1.7.1.

- **Session store is SQLite+FTS5.** The old v1.6 JSONL format is
  read-only and auto-migrated the first time the new CLI runs. Don't
  keep appending to the JSONL files — the store will have diverged.
- **AgentLoop replaces the old v1.6 ad-hoc conversation driver.** If
  you built anything against internal driver symbols (you shouldn't
  have — they weren't `__all__`-exported), look at
  `lyra_core.agent.loop.AgentLoop` and `lyra_core.plugins.Plugin` for
  the replacements.
- **Plugins get new hooks.** `pre_llm_call(ctx)` and
  `on_session_end(ctx)` are stable; the v1.6 `on_turn_complete` hook
  is gone — migrate to `post_llm_call(ctx, response)` for the same
  semantics.
- **Unified command registry.** If you registered slash commands via
  the old v1.6 scattered handler mechanism, port them to `CommandSpec`
  entries added to `lyra_cli.commands.registry.COMMAND_REGISTRY`.
- **Provider registry carries capability metadata.** Code that reads
  LLM capabilities should pull from `lyra_core.providers.registry`
  instead of maintaining its own model lists.
- **LSP tool available but off by default.** Opt in via `--lsp` on
  the CLI or `[tools.lsp] enabled = true` in `~/.lyra/config.toml`;
  the tool raises `LSPUnavailable` if no backend is installed.
- **Small/smart model split is on by default (v2.7.1).** The session
  carries a `fast_model` slot (default `deepseek-v4-flash` →
  `deepseek-chat`) used for chat / tool calls / summaries, and a
  `smart_model` slot (default `deepseek-v4-pro` → `deepseek-reasoner`)
  used for `lyra plan`, `/spawn`, cron fan-out, and the verifier's
  Phase-2 LLM evaluator. Inspect or override the slots from the REPL
  with `/model`, `/model fast`, `/model smart`, `/model fast=<slug>`,
  `/model smart=<slug>`, or persistently in `~/.lyra/settings.json`
  via `fast_model` / `smart_model`. Legacy `--model <slug>` and
  `/model <slug>` still pin a universal model and override both
  slots — the escape hatch. **Migration impact:** if you scripted
  `--model` flags assuming a single global model, nothing changes —
  the universal pin still wins. If you used the legacy four-role
  config (`generator` / `planner` / `evaluator` / `safety`), it's
  still accepted but mapped onto fast/smart at load (`generator` →
  fast slot's *fallback*; the rest → smart slot). See
  [`docs/architecture.md` §3.11](architecture.md#311-smallsmart-model-routing-v271)
  for the full rationale.

## Git history across both renames

We kept git history contiguous. To trace a renamed file's history,
use the `--follow` flag:

```bash
git log --follow -- projects/lyra/packages/lyra-core/src/lyra_core/agent/loop.py
```

This follows the rename chain through `open-coding` → `open-harness`
→ `lyra` and any module-level moves underneath.

## Rolling back

If v1.7.1 causes a regression on your project:

1. Stop using the new CLI (`pip uninstall lyra-*`).
2. Reinstall whichever legacy packages you were on (`opencoding-*`
   from the last v0.1.0 tag, or `open-harness-*` from the transitional
   v1.7 tree).
3. Point your tooling back at `.opencoding/` or `.open-harness/` — we
   **never delete** either directory during migration; they're still
   there, exactly as you left them.
4. Open a bug with the migration symptoms. We'll triage it against
   the `test_brand_identity` and `test_state_dir_migration_v2`
   contract tests in
   `projects/lyra/packages/lyra-cli/tests/`.

## FAQ

**Q: Why the second rename?**
A: `open-harness` was descriptive but generic; the name didn't carry a
personality a product could rally around. **Lyra** (the lyre — the
instrument, and the constellation) is a short, memorable four-letter
brand that reads well as a shell alias (`ly`), scans cleanly as an
ASCII logo, and carries a Greek-mythology connotation of *resonance*
and *pattern* — appropriate for a harness whose whole design discipline
is to make agent behaviour reproducible and TDD-provable. The backronym
(**L**ightweight **Y**ielding **R**easoning **A**gent) is optional
flavour for the README; the product is "Lyra."

**Q: Is `ly` a permanent alias or an experiment?**
A: Permanent. Two letters, no collisions with common CLIs (`oh` was
fine but collided with the word "oh" in error messages; `ly` is
silent). Tests lock both `lyra` and `ly` in the brand-identity
contract.

**Q: Do I lose my old sessions?**
A: No. Both legacy trees are **copied**, not moved. Legacy JSONL
sessions migrate into the SQLite store on first run, and the original
JSONL files stay on disk for audit.

**Q: I'm on v1.6 (`.opencoding/`). Do I need to stop at v1.7 first?**
A: No. The chained migrator at `lyra_core.migrations.migrate_legacy_state`
handles both legacy source dirs in one pass. If only `.opencoding/`
exists, it migrates directly to `.lyra/` with the
`MIGRATED_FROM_OPENCODING` marker and the one-line provenance note,
so future contributors know which legacy brand the data came from.

**Q: What if I have BOTH `.opencoding/` and `.open-harness/`?**
A: The orchestrator prefers the newer (`.open-harness/`) — that's
closer to the v1.7.1 state so you lose less work. The older
`.opencoding/` directory is left untouched for rollback.

**Q: Can I skip the migration and keep `.opencoding/` or
`.open-harness/` as my state dir?**
A: Not supported. The code only knows `.lyra/`. You'd need to hack
`paths.py` and re-pin every plugin; don't do that — just let the
migrator run.

**Q: What if `pip` refuses to uninstall because of a permissions
issue?**
A: You're on macOS with the system Python. Pass
`--break-system-packages`, use a venv, or reinstall with elevated
permissions. None of those change the migration plan.

**Q: What changed in the CLI UX beyond the rename?**
A: The v1.7 fusion release (still shipping under v1.7.1) brought:
claw-code tool cards, fence-aware Markdown streaming, threaded Braille
spinner, opencode leader-chord keybinds, unified slash command
registry, Claude-Code-style welcome card and boxed input. All
opt-in-friendly; the REPL still feels like `claude` / `opencode` if
that's what you were expecting.

**Q: How do I verify the migration worked?**
A: Run `ls .lyra/ ~/.lyra/ 2>/dev/null | grep MIGRATED_FROM`. You
should see one of the marker files (`MIGRATED_FROM_OPEN_HARNESS` or
`MIGRATED_FROM_OPENCODING`) in either location if a migration was
performed. The file itself contains a one-line provenance note.
Subsequent runs emit no notification — that's idempotency working.

## v3.0.0 — TDD becomes opt-in

v3.0.0 (released 2026-04-27) repositions Lyra from a "TDD-first
kernel" to a **general-purpose CLI coding agent**, on par with
`claw-code`, `opencode`, and `hermes-agent`. The TDD plugin still
ships — every component (`lyra_core.tdd.state`, `lyra_core.hooks.tdd_gate`,
`/phase`, `/red-proof`, `/tdd-gate`) is identical to v2.x — but the
default posture changed:

| Behaviour                                  | v2.x default | v3.0.0 default |
|--------------------------------------------|--------------|----------------|
| `InteractiveSession.tdd_gate_enabled`      | `True`       | `False`        |
| Edits to `src/**` blocked without RED      | yes          | no             |
| `/review` flags TDD-off as a verifier fail | yes          | no — neutral   |
| Mode prompts say "TDD-first"               | yes          | no — "CLI-native" |
| `/ultrareview` voice "TDD discipline"      | always       | only when on   |
| Banner tagline includes "TDD-first"        | yes          | no             |

**To restore the v2.x posture in one keystroke:**

```text
plan › /tdd-gate on
[tdd-gate] TDD plugin enabled; edits to src/** without a preceding
           RED test are now blocked.
```

**To make it the default for every session:**

```bash
lyra config set tdd_gate=on
# or edit ~/.lyra/config.yaml directly:
#   tdd_gate: on
# or ~/.lyra/settings.toml:
#   [plugins.tdd]
#   enabled = true
```

If you used `--no-tdd` or `--no-plan` flags in v2.x scripts, they
still work — they just have no effect on a TDD-off session by
default. CI scripts that set `LYRA_TDD_GATE=on` continue to take
precedence over the config defaults.

The only externally visible breakage from this change is in the
verifier rubrics (`/ultrareview`): if your eval harness asserts that
the third reviewer voice is `"reviewer-B (TDD discipline)"`, it
will now read `"reviewer-B (test coverage)"` whenever the gate is
off. Pin the gate on for those evals or update the assertion.
