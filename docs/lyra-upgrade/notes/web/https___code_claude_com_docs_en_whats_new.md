# What's New (Claude Code Official Docs)

**Source**: https://code.claude.com/docs/en/whats-new
**Org**: Anthropic
**Coverage**: Weekly digests, March 2026 -- May 2026 (v2.1.83 through v2.1.157)
**Note type**: Primary source -- official Anthropic documentation for Claude Code releases

---

## Key Technical Claims

### 1. Dynamic Workflows (Week 22, v2.1.150-157, research preview)
Claude writes its own orchestration scripts to fan out work across dozens to hundreds of subagents in the background. The workflow script is generated dynamically for the task at hand rather than being a pre-defined template. Managed via `/workflows`. Use cases: codebase-wide audits, large migrations, cross-checked research questions.

### 2. Security Guidance Plugin (Week 22, plugin)
A three-layer in-session security review that operates alongside the coding process. The key architectural insight is that each layer operates independently with a fresh, impartial reviewer -- Claude never grades its own work.

### 3. Agent View (Week 20, research preview)
`claude agents` is a unified dashboard showing every active session: what is running, what is blocked on user input, and what is done. Background sessions keep running without an attached terminal. Users can attach to any row to drop into the full conversation, then press `<-` to return to the list. Supports dispatch flags (`--add-dir`, `--settings`, `--mcp-config`, `--plugin-dir`, `--model`, etc.).

### 4. /goal (Week 20, v2.1.139)
A persistent completion condition: Claude keeps working across turns without the user prompting each step. After every turn a fast model checks whether the condition holds; if not, Claude starts another turn. The goal clears once the condition is met. Works in interactive, `-p`, and Remote Control modes.

### 5. Ultraplan (Week 15, research preview)
Plan mode executes in the cloud from the CLI. Claude drafts the plan in a Claude Code on the web session while the terminal stays free. The user can review and comment on sections in the browser, request revisions, and choose remote execution or pull back to local CLI. As of v2.1.101 the first run auto-creates a default cloud environment.

### 6. Monitor Tool (Week 15, v2.1.98)
A built-in tool that spawns a background watcher and streams events into the conversation as new transcript messages. Claude reacts to each event immediately. Pairs with `/loop` which is now self-pacing (omitting the interval lets Claude schedule the next tick based on the task).

### 7. Auto Mode (Week 13, research preview, expanded Week 21)
A permission-prompt classifier that replaces the approve/deny cycle for safe actions. Safe edits and commands run without interruption; destructive or suspicious actions are blocked and surfaced. The middle ground between approving every file write and `--dangerously-skip-permissions`. Expand to Pro accounts in Week 21.

### 8. Fast Mode (Weeks 20-22)
Fast mode defaults to Opus 4.8 at $10/$50 per MTok (Week 22), roughly 2.5x speed for 2x the standard rate. Opus 4.7 and 4.6 fast mode stay at $30/$150.

### 9. Opus 4.8 (Week 22)
New default model for Max, Team Premium, Enterprise pay-as-you-go, and Anthropic API. Defaults to high effort. `/effort xhigh` for the hardest tasks.

---

## Architecture/Mechanism Details

### Security Guidance Plugin: Three-Layer Architecture

This is the most mechanically detailed feature in the documentation and the most relevant for Lyra.

**Layer 1: Per-edit pattern match** (no model call, zero cost)
- Runs after every `Edit`, `Write`, `NotebookEdit` tool call
- Scans new content for known risky patterns (deterministic regex/substring match)
- Pattern categories: dynamic code execution (`eval(`, `new Function`, `os.system`), unsafe deserialization (`pickle`), DOM injection (`dangerouslySetInnerHTML`, `.innerHTML =`), workflow file edits
- Each warning fires once per pattern per file per session (deduplication)
- Extensible via `.claude/security-patterns.yaml` or `.json` (up to 50 custom patterns)
- Custom rules support: `rule_name`, `reminder` (capped 1 KB), `regex` or `substrings`, `paths` and `exclude_paths` glob patterns
- Path globs are full-path matches, so project-relative patterns need `**/` prefix

**Layer 2: End-of-turn model review** (separate Claude call)
- Runs as a `Stop` hook (background, does not delay Claude's reply)
- Computes git diff of everything changed during the turn (edits, Bash commands, subagent changes)
- Sends diff to a **separate** Claude instance with a fresh context and security-focused prompt
- Catches: authorization bypass, IDOR, injection, SSRF, weak cryptography
- Covers up to 30 changed files per turn
- Fires at most 3 times in a row before yielding back to user
- If findings found, Claude is re-prompted and addresses them as follow-up
- Configurable model via `SECURITY_REVIEW_MODEL` env var (defaults to Opus 4.7)

**Layer 3: Commit/push agentic review** (deepest)
- Fires on `PostToolUse` on `Bash` filtered to `git commit` and `git push`
- Reads surrounding code: callers, sanitizers, related files
- Agentic -- may take several model turns per review
- Capped at 20 reviews per rolling hour
- Deduplicated against Layer 2 findings (clean commits produce no visible output)
- Configurable model via `SG_AGENTIC_MODEL` env var
- Falls back to single-shot review if `claude-agent-sdk` not importable
- Only reviews commits Claude makes through Bash tool (not user shell commands)

**Integration mechanism**: The entire plugin is built on standard Claude Code hooks:
- `SessionStart` -- bootstrap Python environment
- `UserPromptSubmit` -- capture working-tree baseline for diff
- `PostToolUse` on `Edit`/`Write`/`NotebookEdit` -- per-edit pattern match
- `Stop` -- end-of-turn diff review (background)
- `PostToolUse` on `Bash(git commit *)` and `Bash(git push *)` -- commit review (background)

**Extension points**:
- `.claude/claude-security-guidance.md` -- natural language threat model and review checklist (up to 8 KB combined across user/project/local scopes)
- `.claude/security-patterns.yaml`/`.yml`/`.json` -- custom deterministic patterns (up to 50 rules)
- Rule file lookup: user scope (`~/.claude/`), project scope (`.claude/`), local scope (`.claude/*.local.*`)
- All paths concatenated; additive only (cannot suppress built-in checks)
- Individual layers disableable via env vars: `ENABLE_PATTERN_RULES`, `ENABLE_STOP_REVIEW`, `ENABLE_COMMIT_REVIEW`, `ENABLE_CODE_SECURITY_REVIEW`, `SECURITY_GUIDANCE_DISABLE`

**Review independence**: The plugin never asks the writing Claude to grade itself. Layer 1 is a deterministic match. Layers 2 and 3 use a separate Claude call with a fresh context, security-focused prompt, and no investment in the original approach.

### Dynamic Workflows Architecture

- Claude writes an orchestration script for the specific task
- The script fans out work across many subagents running in background
- Subagents operate independently, each with their own context
- Managed via `/workflows` command
- Use case: "create a workflow that migrates every internal fetch() call to the new HttpClient wrapper"

### Agent View Architecture

- `claude agents` opens a TUI dashboard
- Each row = one session (running, blocked on input, or done)
- Background sessions persist without a terminal attached
- Detach/attach model: press `<-` to return to list; attach to any row for full conversation
- Dispatch flags configure background sessions at creation time

### /goal Architecture

- Condition set by user (e.g., "all tests in test/auth pass and the lint step is clean")
- After every Claude turn, a fast model evaluates whether the condition holds
- If not satisfied, Claude starts another turn autonomously
- Goal clears once condition is met
- Works across interactive, `-p`, and Remote Control modes

### Auto Mode Architecture

- Classifier handles permission prompts
- Safe actions (edits, reads, common commands) run without interruption
- Destructive or suspicious actions are blocked and surfaced
- Configurable via `"defaultMode": "auto"` in `~/.claude/settings.json`
- Expand: hard deny rules (Week 19) block actions unconditionally regardless of allow exceptions

---

## Numbers & Benchmarks

| Feature | Detail |
|---------|--------|
| Fast mode pricing (Opus 4.8) | $10/$50 per MTok (input/output), ~2.5x speed |
| Fast mode pricing (Opus 4.7/4.6) | $30/$150 per MTok |
| Standard rate vs fast mode | ~2.5x speed for ~2x the cost |
| Security review: files per turn | Up to 30 changed files per end-of-turn review |
| Security review: re-prompt limit | At most 3 consecutive reviews before yielding |
| Security review: commit limit | 20 agentic reviews per rolling hour |
| Security patterns: custom rules | Up to 50 custom rules per project |
| Security patterns: reminder cap | 1 KB per rule reminder |
| Security guidance file | 8 KB combined cap across all scopes |
| Opus 4.8 default effort | `high` (was `medium`) |
| Opus 4.8 xhigh effort | `/effort xhigh` for hardest tasks |
| Plugin install fallback model | Opus 4.7 default for security reviews |
| Python requirement | 3.8+ for security-guidance plugin |
| Claude Code CLI requirement | v2.1.144+ for security-guidance plugin |
| Max iterations goal check | After each turn, fast model evaluates condition |
| Status line refresh interval | Configurable via `refreshInterval` setting |

---

## Transfer to Lyra

### Core Transferable Idea: Multi-Layer Agentic Self-Review Pipeline

The security-guidance plugin architecture is directly transferable to Lyra's **verification pipeline**. The key insight is the three-layer defense-in-depth design where each layer operates independently with increasing cost, context, and depth:

1. **Per-edit deterministic checks** (zero cost, instant) -- catch syntax errors, lint violations, pattern violations
2. **Per-turn semantic model review** (moderate cost) -- catch logical bugs, test failures, functional regressions
3. **Commit/push deep review** (higher cost) -- catch architecture violations, cross-file invariants, design pattern conformance

The critical pattern is that the reviewer is always a **separate, impartial instance** with no investment in the written code. This solves the "self-grading" problem that all autonomous coding agents face.

### Second Transferable Idea: Dynamic Workflow Orchestration

Dynamic workflows (Claude writing its own orchestration scripts) is essentially what Lyra's workflow engine should become. Instead of pre-defined pipeline templates, Lyra should be able to generate task-specific orchestration scripts that fan out across subagents. This maps to Lyra's multi-agent architecture.

### Third Transferable Idea: Extension-Point Architecture for Verification

The security-guidance plugin's extension model (Markdown guidance + YAML patterns + layered lookup paths) provides a clean pattern for Lyra's rule configuration. Users should be able to add project-specific verification rules via `.lyra/verification-rules.yaml` and `.lyra/verification-guidance.md` without modifying Lyra's built-in checks.

### Workstream Route

This maps to **Lyra's verification infrastructure workstream** -- the in-loop self-verification and safety layer. It parallels §4.2 (verification pipeline) and §4.x (safety/security) of the Lyra upgrade architecture debate.

Specifically:
- **§4.x**: Verification infrastructure -- multi-layer self-review pipeline
- The per-edit pattern check could be implemented as a PreToolUse hook in Lyra's tool loop
- The end-of-turn model review maps to Lyra's verification phase after each action
- The commit/push review maps to Lyra's pre-commit verification gate

### Configuration Pattern for Lyra

```
.lyra/verification-rules.yaml     # custom deterministic patterns (additive)
.lyra/verification-guidance.md    # natural language review checklist
.lyra/verification-rules.local.md # gitignored personal overrides
```

Each verification layer independently disableable via env vars or Lyra config:
```
LYRA_VERIFY_SYNTAX=0    # disable per-edit checks
LYRA_VERIFY_LOGIC=0     # disable per-turn model review
LYRA_VERIFY_DEEP=0      # disable commit/push deep review
```

---

## Related Pages

- https://code.claude.com/docs/en/security-guidance -- full security-guidance plugin docs
- https://code.claude.com/docs/en/workflows -- dynamic workflows
- https://code.claude.com/docs/en/agent-view -- agent view dashboard
- https://code.claude.com/docs/en/goal -- persistent goals
- https://code.claude.com/docs/en/ultraplan -- cloud planning
- https://code.claude.com/docs/en/permission-modes -- auto mode configuration
- https://code.claude.com/docs/en/fast-mode -- fast mode pricing
