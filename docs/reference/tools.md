---
title: Tools reference
description: Every built-in tool with its schema, default permission grid, side-effects, and intended use.
---

# Tools reference <span class="lyra-badge reference">reference</span>

This page catalogues every built-in tool Lyra ships. MCP-provided
tools are covered in [Add an MCP server](../howto/add-mcp-server.md).

For the conceptual grounding, see
[Tools and hooks](../concepts/tools-and-hooks.md).

## Convention

Each tool entry follows this shape:

| Field | Meaning |
|---|---|
| **schema** | Argument types Lyra type-checks before dispatch |
| **side-effects** | Filesystem / network / process / state effects |
| **default permission** | The permission bridge's verdict in default mode |
| **subagent inheritance** | What scope a subagent gets by default |
| **typical hook** | Built-in hook that wraps this tool |

## Read-only tools

### `view`

Read a file or directory listing.

| Field | Value |
|---|---|
| schema | `path: str, offset?: int, limit?: int` |
| side-effects | none |
| default permission | allow |
| subagent inheritance | inherits parent's read scope |
| typical hook | `secret-redactor` (post) |

Used by every tool flow that needs to read code; the kernel prefers
`view` over `bash cat` for traceability and offset/limit support.

### `glob`

Glob-style file search.

| Field | Value |
|---|---|
| schema | `pattern: str, path?: str` |
| side-effects | none |
| default permission | allow |

Pattern matching follows
[Python `fnmatch`](https://docs.python.org/3/library/fnmatch.html);
uses `**` for recursive.

### `grep`

Ripgrep-backed code search.

| Field | Value |
|---|---|
| schema | `pattern: str, path?: str, type?: str, glob?: str, output_mode?: "content" \| "files_with_matches" \| "count"` |
| side-effects | spawns `rg` subprocess |
| default permission | allow |

Returns up to a few thousand lines by default; truncates and reports
"at least N matches" when overflowing.

### `web_fetch`

Fetch a URL and convert to markdown.

| Field | Value |
|---|---|
| schema | `url: str` |
| side-effects | network egress |
| default permission | ask in `default`; allow in `acceptEdits`; allow in `bypass` |
| typical hook | `large-write-guard` if response > 1 MB |

Uses an isolated fetch worker; no cookies, no auth headers, no
redirects to private IPs.

### `web_search`

Search-engine-backed query.

| Field | Value |
|---|---|
| schema | `query: str` |
| side-effects | network egress |
| default permission | ask in `default`; allow in `acceptEdits` |

## Write tools

### `write`

Write a file (creates parent dirs).

| Field | Value |
|---|---|
| schema | `path: str, content: str` |
| side-effects | filesystem write inside repo or `~/.lyra/` |
| default permission | ask in `default`; allow in `acceptEdits`; allow in `bypass` |
| subagent inheritance | repo-scoped; user-global needs explicit grant |
| typical hook | `path-quarantine`, `secret-redactor`, `large-write-guard` |

Refuses paths outside `repo()` or `~/.lyra/` unless the
`path-quarantine` hook is disabled.

### `edit`

Targeted edit (single string replace).

| Field | Value |
|---|---|
| schema | `path: str, old_string: str, new_string: str, replace_all?: bool` |
| side-effects | filesystem write |
| default permission | same as `write` |
| typical hook | `tdd-anchor` (denies writes to `tests/` in green phase) |

Fails if `old_string` is not unique in the file (unless
`replace_all=true`). Lyra prefers `edit` over `write` for partial
file changes — the diff is smaller and the verifier can attribute the
change to a specific intent.

### `multiedit`

Apply multiple edits to a single file in one call.

| Field | Value |
|---|---|
| schema | `path: str, edits: list[{old_string, new_string, replace_all?}]` |
| side-effects | filesystem write |
| default permission | same as `write` |

All edits succeed or all fail — atomic. Used when a refactor needs
multiple coordinated changes.

### `delete`

Delete a file.

| Field | Value |
|---|---|
| schema | `path: str` |
| side-effects | filesystem delete |
| default permission | ask in all modes except `bypass` |
| subagent inheritance | denied unless explicitly granted |

## Process tools

### `bash`

Run a shell command in the repo working directory.

| Field | Value |
|---|---|
| schema | `command: str, working_directory?: str, block_until_ms?: int, required_permissions?: list[str]` |
| side-effects | arbitrary |
| default permission | ask in `default`; allow in `acceptEdits` for safe-pattern commands; allow in `bypass`; per-pattern overrides |
| typical hook | `dangerous-bash-guard`, `cost-warner`, quotas |

The kernel maintains a **safe-pattern allowlist** (e.g. `git status`,
`pytest`, `npm test`) that auto-allow even in `default`. The full list
lives in `lyra_core/permissions/safe_patterns.yaml`.

Long-running commands (block_until_ms 0 or commands exceeding the
block) are moved to background and stream output to a per-terminal
file under `.lyra/terminals/`.

### `subagent_spawn`

Spawn a child agent with a constrained scope.

| Field | Value |
|---|---|
| schema | `description: str, prompt: str, subagent_type: str, model?: str, readonly?: bool` |
| side-effects | new agent loop |
| default permission | allow in all modes; subject to `subagent-depth-cap` (≤ 3) |
| subagent inheritance | child cannot grant more than parent has |
| typical hook | `subagent-depth-cap` |

See [concept: Subagents](../concepts/subagents.md).

## Knowledge / state tools

### `read_memory`

Read from L3 / L4 memory by query.

| Field | Value |
|---|---|
| schema | `query: str, tier?: "L3" \| "L4" \| "both", k?: int` |
| side-effects | none |
| default permission | allow |

### `write_memory`

Write a fact / artifact to L3 / L4.

| Field | Value |
|---|---|
| schema | `tier: "L3" \| "L4", content: str, kind?: str, tags?: list[str]` |
| side-effects | append to memory store |
| default permission | allow in any mode |

### `time_travel_replay`

Reconstruct transcript / state at a previous step (debug mode).

| Field | Value |
|---|---|
| schema | `session_id: str, step: int` |
| side-effects | none (no LLM call) |
| default permission | allow |

## Verification tools

### `run_tests`

Wrapper around the project's test runner.

| Field | Value |
|---|---|
| schema | `paths?: list[str], pattern?: str, framework?: str` |
| side-effects | runs subprocess; modifies coverage files |
| default permission | allow |
| typical hook | TDD gate observes results |

Auto-detects the framework (`pytest`, `vitest`, `jest`, `gradle test`,
`go test`). Output is parsed into a structured `TestRunResult` so the
verifier and TDD gate can act on it without re-parsing.

### `lint` / `typecheck`

Wrappers around `ruff`, `mypy`, `eslint`, `tsc`, etc.

| Field | Value |
|---|---|
| schema | `paths?: list[str], strict?: bool` |
| side-effects | runs subprocess |
| default permission | allow |

Auto-detects the toolchain.

## Defining a new tool

```python title="my_tool.py"
from lyra_core.tools import tool, ToolResult

@tool(
    name="hash_file",
    schema={"path": "str", "algo": "Literal['sha256','md5']"},
    side_effects=[],
    default_permission="allow",
)
def hash_file(path: str, algo: str = "sha256") -> ToolResult:
    import hashlib
    digest = getattr(hashlib, algo)()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return ToolResult.ok(digest.hexdigest())
```

Then expose via a [plugin](../howto/write-plugin.md) or drop in
`~/.lyra/tools/`. Tools must be **deterministic-on-success** (i.e.
same args → same observable effect or same returned value); the
verifier relies on this.

## Tool calls in the trace

Every tool call emits:

- `Tool.call(tool, args_ref)` (args are stored in the artifact store
  by hash; large args don't bloat the trace)
- `Tool.result(result_ref, exit_code, duration_ms)`

Surrounding events: `PermissionBridge.decision`, `Hook.start/end`.

[← Reference: hooks](hooks.md){ .md-button }
[Continue: permission modes →](permission-modes.md){ .md-button .md-button--primary }
