# Commands & Interactive Mode — Brainstorm (§4.9)

> **Workstream:** §4.9 (commands)  
> **Date:** 2026-06-06  
> **Status:** Breakthrough ideation

## Context Review

### From SYNTHESIS.md
No explicit "ui-commands" section found in SYNTHESIS. Commands are implicitly referenced in:
- Agent View UX patterns (peek/attach/detach interactions)
- Fleet steering surface (state-grouped rows, filters)
- Human-in-the-loop patterns (steer-by-exception)

### From Existing Plan (plans/09-commands.md)
**Current design:**
- Built-in commands: `/model`, `/effort`, `/skills`, `/memory`, `/fleet`, `/cost`, `/config`, `/help`, `/dream`
- Custom commands: `.lyra/commands/<name>.md` with YAML frontmatter
- Command palette: `/` opens fuzzy-search palette
- Interactive mode: REPL with syntax highlighting, multi-line input, history search (Ctrl+R)
- Keybindings: e.g., Ctrl+K → `/code-review`

**Parity tier:** Port Claude Code's implementation directly (A)
**Breakthrough tier:** Must beat Claude Code on measurable dimension (B)

### From BASELINE.md
- **Status:** None — no slash-command system exists
- **Gap:** No command registry, no palette, no keybindings, no interactive REPL

### Key Sources to Fuse
1. **Claude Code docs** (§3.1): slash commands as markdown files, autocomplete, REPL
2. **Agent View UX** (§3.1.39): peek/attach/detach patterns, suggested reply (Tab)
3. **Interactive shells:** Fish shell autocomplete, Zsh completion system, fzf fuzzy finder
4. **Voice interfaces** (§3.13): push-to-talk, always-listening, barge-in patterns
5. **Context engineering:** Command context injection (what's visible when `/foo` runs)
6. **Planning systems** (§3.21): Commands as workflow triggers (MCTS, AFlow)

---

## Breakthrough Idea 1: Context-Aware Command Synthesis

### Sources Fused
- **SkillNet** (2603.04448): Auto-generate skill packages from execution trajectories
- **GEPA** (ICLR 2026 Oral): Gradient-free prompt evolution
- **Q-DAPS** (2605.12398): Difficulty estimation as entropy over candidate answers
- **Claude Code commands**: YAML frontmatter for arguments/description

### Mechanism
Instead of users manually authoring `.lyra/commands/<name>.md`, Lyra **observes repeated patterns** in user interactions and **auto-synthesizes** custom commands:

1. **Pattern detection:** Track command sequences (e.g., user types `/model opus` → `/effort high` → "review this PR" three times in a week)
2. **Entropy estimation:** Use Q-DAPS to detect when a command sequence has low entropy (predictable) vs high entropy (exploratory)
3. **Auto-synthesis:** When entropy drops below threshold (sequence is stable), generate a candidate command:
   ```markdown
   ---
   name: review-pr-opus
   description: Review PR with Opus at high effort
   arguments:
     - name: pr_url
       required: true
   keybinding: Ctrl+Shift+R
   ---
   /model opus
   /effort high
   Review the PR at {{pr_url}} for correctness, security, and performance.
   ```
4. **Confirmation loop:** Propose the command to user ("I noticed you often run this sequence. Save it as `/review-pr-opus`?")
5. **Evolution:** Commands created this way are marked as `auto_generated: true` in frontmatter. Lyra continues tracking usage and can suggest refinements (GEPA-style prompt evolution).

### Why It Beats Baseline
- **Claude Code baseline:** Users manually write commands. Learning cost: high. Adoption: low (most users won't bother).
- **This approach:** Zero-effort command creation. Lyra learns your workflow and distills it into reusable commands. Learning happens in the background.
- **Measurable win:** Time-to-first-custom-command. Baseline: days (user must learn YAML format). This: hours (first pattern detected after ~3 repetitions).

### Impact × Effort
- **Impact:** 8/10 — transforms commands from "power-user feature" to "works for everyone"
- **Effort:** 6/10 — pattern detector (2 weeks), Q-DAPS integration (1 week), synthesis engine (2 weeks), confirmation UX (1 week)
- **Net:** High leverage

### Failure Modes
1. **False positives:** Lyra detects a "pattern" that's actually exploratory. Mitigation: High confirmation threshold (≥3 repetitions with <30% variance), explicit user confirmation.
2. **Privacy:** User patterns might reveal sensitive workflows. Mitigation: Pattern detection happens locally, no telemetry. User can disable with `LYRA_NO_AUTO_COMMANDS=1`.
3. **Overfitting:** Auto-generated command is too specific (e.g., hardcodes a branch name). Mitigation: Parameterize detected variables automatically (regex-based variable extraction).
4. **Command explosion:** User ends up with 50 auto-generated commands. Mitigation: Decay unused commands (if not invoked in 30 days, archive to `.lyra/commands/archived/`).

### Stress Test
**Q:** Does this actually save time vs. just typing the sequence?  
**A:** For 3-step sequences, marginal. For 5+ step sequences with arguments, significant. Real win: **keybinding support**. `/review-pr-opus` → Ctrl+Shift+R means zero typing.

**Q:** What if the user's workflow changes?  
**A:** GEPA evolution. Lyra detects when an auto-generated command is frequently edited after invocation → suggests updating the template.

**Q:** Does this work across sessions?  
**A:** Yes, if patterns span sessions. Needs cross-session pattern persistence (`.lyra/state/command_patterns.json`).

---

## Breakthrough Idea 2: Voice-First Command Interface

### Sources Fused
- **Moshi** (2410.00037): 160ms speech-to-speech latency, Inner Monologue architecture
- **Smart Turn** (pipecat-ai): Barge-in for cascaded pipelines
- **Fish shell**: As-you-type suggestions
- **Agent View**: Suggested reply on Tab
- **Claude Code voice** (§3.1.29): Push-to-talk dictation

### Mechanism
Commands are **voice-native**, not text-native:

1. **Push-to-talk:** User holds a hotkey (e.g., Space) and speaks: "Lyra, review this PR with Opus"
2. **Speech-to-intent:** Whisper transcribes → lightweight intent classifier (Haiku-class) maps to command:
   - Input: "review this PR with Opus"
   - Intent: `/review-pr-opus pr_url=<current_git_branch_pr>`
   - Execution: Command runs with inferred arguments
3. **Voice feedback:** TTS confirms: "Reviewing PR #1234 with Opus at high effort" (Kokoro or piper)
4. **Barge-in:** If Lyra is mid-execution, user can interrupt (Smart Turn pattern) to redirect: "Actually, use Sonnet instead"
5. **Visual echo:** Terminal shows the inferred command in dim text before execution (user can Ctrl+C to cancel)

**Advanced:** Always-listening mode (opt-in). VAD detects "Lyra" wake word → listens for command → executes.

### Why It Beats Baseline
- **Claude Code baseline:** Text-only commands. Voice dictation exists but is generic transcription, not command-aware.
- **This approach:** Voice is the **primary interface** for commands. Faster than typing `/model opus /effort high`. More natural for review/feedback workflows ("Lyra, summarize the last 10 messages").
- **Measurable win:** Command invocation latency. Baseline: ~3-5s (type `/review-pr-opus`, tab-complete, enter). This: ~1-2s (hold Space, speak, release). 50%+ latency reduction for commands with multi-word names.

### Impact × Effort
- **Impact:** 7/10 — High for voice users, zero for text-only users (needs opt-in)
- **Effort:** 7/10 — VAD (1 week), Whisper integration (1 week), intent classifier (2 weeks), TTS feedback (1 week), Smart Turn barge-in (2 weeks)
- **Net:** Medium-high leverage, gated on voice infrastructure (§4.18)

### Failure Modes
1. **Transcription errors:** Whisper mishears "Opus" as "Office". Mitigation: Show visual echo; user can Ctrl+C before execution. Phonetic correction layer (common command names).
2. **Ambient noise:** VAD triggers on background speech. Mitigation: Push-to-talk default; always-listening is opt-in with aggressive VAD tuning.
3. **Latency:** 800-2750ms cascaded pipeline (Whisper→Haiku→Kokoro) vs 1-2s target. Mitigation: Cache Whisper model in memory; use faster TTS (piper ~200ms vs Kokoro ~500ms). Intent classifier is cheap (Haiku, <200ms).
4. **Multi-language:** VI+EN support needed. Whisper large-v3 supports both but VI accuracy lower. Mitigation: Language detection from Whisper metadata; fallback to text command if confidence <70%.

### Stress Test
**Q:** Is voice faster than typing for power users?  
**A:** No, for single-word commands (`/help`). Yes, for multi-word commands with arguments (`/review-pr-opus pr_url=...`). Biggest win: hands-free workflows (user is away from keyboard, on phone/tablet).

**Q:** Does this require §4.18 voice infrastructure?  
**A:** Partially. Needs Whisper (STT) and Kokoro (TTS), but NOT full-duplex S2S. Can be built incrementally: (1) push-to-talk → text command, (2) add TTS feedback, (3) add barge-in later.

**Q:** What if user has accent/speech impediment?  
**A:** Whisper is robust to accents but not perfect. Fallback: user edits the visual echo before confirming (press Enter to accept, or edit first). Accessibility: voice is opt-in; text commands remain primary.

---

## Breakthrough Idea 3: Command-as-Workflow Planner

### Sources Fused
- **AFlow** (ICLR 2025): MCTS over agent workflows
- **COMPASS** (2510.08790): Meta-thinker for hierarchical context management
- **Claude Code workflows** (§3.1.36): DAG engine for multi-step tasks
- **SkillNet composition**: Commands compose into higher-order workflows

### Mechanism
Commands are not just **actions** — they're **workflow nodes** in a planning graph:

1. **Command as node:** Each command is a node in a DAG. Example:
   - `/fetch-pr` → fetches PR diff
   - `/review-code` → reviews fetched code
   - `/post-comment` → posts review as PR comment
2. **Composition syntax:** User defines workflows as command pipelines:
   ```yaml
   # .lyra/commands/auto-review-pr.md
   ---
   name: auto-review-pr
   description: Fetch, review, and comment on a PR automatically
   workflow:
     - /fetch-pr pr_url={{pr_url}}
     - /review-code | /effort high | /model opus
     - /post-comment pr_url={{pr_url}} comment="{{review_output}}"
   ---
   ```
3. **MCTS planning:** When user invokes `/auto-review-pr`, Lyra uses MCTS to search the space of **valid command orderings**:
   - Base ordering: fetch → review → post
   - Alternative 1: fetch → `/check-ci` → review → post (if CI failed, skip review)
   - Alternative 2: fetch → review → `/human-confirm` → post (require human approval before posting)
4. **Difficulty-based triggering:** Use Q-DAPS to estimate workflow difficulty. Simple workflows (3 steps, all deterministic) run as-is. Complex workflows (5+ steps, branching logic) invoke MCTS to find optimal ordering.
5. **Value agent scoring:** Each workflow candidate is scored by a value agent (SWE-Search pattern) based on: estimated latency, token cost, success probability.

### Why It Beats Baseline
- **Claude Code baseline:** Commands are atomic. No composition, no planning. Users manually chain commands via `;` or `&&` in shell, but no semantic understanding.
- **This approach:** Commands are **first-class workflow primitives**. Lyra can reason about command dependencies, optimize execution order, parallelize independent commands.
- **Measurable win:** Workflow execution time. Baseline: serial execution (fetch → review → post = 30s + 20s + 5s = 55s). This: parallel + smart ordering (fetch || check-ci, then review, then post = 30s + 20s + 5s = 55s, but if CI failed, skip review = 30s + 5s = 35s). 30%+ time savings on complex workflows.

### Impact × Effort
- **Impact:** 9/10 — Unlocks autonomous, multi-step command workflows. Bridges commands and planning (§4.20).
- **Effort:** 8/10 — Workflow DAG engine (3 weeks), MCTS integration (3 weeks), value agent (2 weeks), Q-DAPS trigger (1 week)
- **Net:** High leverage, but heavy lift. Should be **gated on MCTS planning infrastructure** (§4.20).

### Failure Modes
1. **Circular dependencies:** User defines workflow where `/a` depends on `/b` which depends on `/a`. Mitigation: Cycle detection at workflow parse time. Reject cyclic workflows with clear error.
2. **MCTS overhead:** MCTS search costs tokens (each node evaluation = agent roll-out). For simple workflows, this is pure waste. Mitigation: Difficulty-based triggering (Q-DAPS entropy). Only invoke MCTS when workflow complexity warrants it.
3. **Command compatibility:** Not all commands compose cleanly. Example: `/review-code` expects a file path, but `/fetch-pr` returns a PR object. Mitigation: Command output schema (YAML frontmatter declares output type). Lyra validates compatibility at parse time.
4. **Debugging workflows:** When a 7-step workflow fails at step 5, user needs to debug. Mitigation: Structured logging (each command logs inputs/outputs). Workflow replay (re-run from step N).

### Stress Test
**Q:** Is MCTS overkill for most workflows?  
**A:** Yes, for linear workflows (95% of cases). Real value: **branching workflows** with conditional logic (if CI failed, if human said no, if file >1000 lines). These are rare but high-value (autonomous PR review, deploy pipelines).

**Q:** Does this need §4.20 planning infrastructure?  
**A:** Ideally, yes. But MVP: DAG engine + serial execution (no MCTS). Users get composition, no planning overhead. MCTS added later for complex workflows.

**Q:** Can users understand workflows?  
**A:** Depends on syntax. YAML pipelines are readable for linear workflows. Branching logic needs a clearer DSL (if/then/else). Alternative: visual workflow editor (§4.28 desktop GUI).

---

## Breakthrough Idea 4: Ambient Command Suggestions

### Sources Fused
- **Agent View suggested reply** (§3.1.39): Tab to accept suggested next action
- **Fish shell as-you-type**: Real-time command suggestions based on history
- **GitHub Copilot**: Context-aware code completion
- **Q-DAPS**: Difficulty estimation → suggest command escalation

### Mechanism
Lyra **proactively suggests commands** based on current context:

1. **Context sensing:** Lyra monitors current state:
   - Git branch (if on `fix/bug-123`, suggest `/test` or `/review-code`)
   - Open files (if editing `auth.py`, suggest `/security-review`)
   - Recent errors (if test failed 3 times, suggest `/debug` or `/escalate opus`)
   - Time of day (if 5pm Friday, suggest `/wrap-up` to summarize open tasks)
2. **Suggestion surface:** Suggestions appear in:
   - **Statusline:** Bottom bar shows dim suggestion: `[Tab: /test]`
   - **After errors:** If command fails, suggest next step: "Command failed. Try `/retry` or `/escalate opus`?"
   - **Idle detection:** If user idle >30s in session, suggest: "Continue working? Try `/resume-last` or `/plan-next`"
3. **One-key accept:** User presses Tab to accept suggestion (Fish shell pattern).
4. **Learning:** Lyra tracks which suggestions user accepts → re-ranks future suggestions (simple frequency model, no ML needed).

### Why It Beats Baseline
- **Claude Code baseline:** User must remember command names. Discovery is manual (`/help` to see list).
- **This approach:** Lyra **pushes** relevant commands to user based on context. Reduces cognitive load. Faster workflow.
- **Measurable win:** Command discovery time. Baseline: user must read `/help` output (15+ commands). This: suggestion appears immediately when relevant. 80%+ reduction in command lookup latency.

### Impact × Effort
- **Impact:** 7/10 — High for new users (command discovery). Medium for power users (already know commands).
- **Effort:** 4/10 — Context sensing (2 weeks), suggestion ranking (1 week), statusline integration (1 week)
- **Net:** High leverage, relatively cheap

### Failure Modes
1. **Annoying suggestions:** User doesn't want suggestions when focused. Mitigation: Opt-out (`LYRA_NO_SUGGESTIONS=1`). Suggestions are dim/non-intrusive. Only shown in idle state or after errors.
2. **Wrong suggestions:** Lyra suggests `/test` but user wants to write more code first. Mitigation: Suggestions are non-blocking (user can ignore). Ranking improves over time.
3. **Privacy:** Context sensing might infer sensitive workflow. Mitigation: All sensing happens locally. No telemetry.

### Stress Test
**Q:** Is this just annoying autocomplete?  
**A:** No, if done right. Key: suggestions are **contextual** (not random), **non-intrusive** (dim text, easy to ignore), and **one-key accept** (Tab). Compare to Copilot: users love it when suggestions are relevant, ignore when not.

**Q:** Does this need ML?  
**A:** No. Simple rules + frequency tracking covers 80% of cases:
   - If in git repo + on branch → suggest `/test`, `/review-code`
   - If test failed → suggest `/debug`, `/escalate`
   - If editing security-sensitive file → suggest `/security-review`
   - Frequency model: if user always runs `/test` after editing, rank it higher.

---

## Strongest Ideas (Promotion to Plan)

### Tier (B) Candidates

1. **Context-Aware Command Synthesis** (Idea 1)
   - **Why promote:** Transforms commands from power-user feature to mainstream. Zero-effort learning.
   - **Gating:** Needs pattern detection + Q-DAPS integration. Can be built incrementally.
   - **Measured win:** Time-to-first-custom-command (days → hours).

2. **Ambient Command Suggestions** (Idea 4)
   - **Why promote:** Cheap to build (4/10 effort), high impact for discovery (7/10). Complements parity tier.
   - **Gating:** None. Can ship in Phase 1 alongside basic command system.
   - **Measured win:** Command discovery latency (80%+ reduction).

### Tier (C) Research Bets

3. **Command-as-Workflow Planner** (Idea 3)
   - **Why defer:** Heavy lift (8/10 effort), requires §4.20 planning infrastructure. High impact (9/10) but needs foundation first.
   - **Path:** Ship MVP (DAG composition, no MCTS) in Phase 2. Add MCTS planning in Phase 3 after §4.20 lands.

4. **Voice-First Command Interface** (Idea 2)
   - **Why defer:** Requires §4.18 voice infrastructure. Medium-high effort (7/10), opt-in feature (7/10 impact for voice users only).
   - **Path:** Ship after §4.18 voice lands. Can be built incrementally (push-to-talk → TTS feedback → barge-in).

---

## Integration Notes

### Synergies with Other Workstreams
- **§4.4 Skills:** Auto-synthesized commands can trigger skills (command → skill invocation).
- **§4.10 Hooks:** Commands fire PostToolUse hooks (e.g., `/test` → hook auto-formats code).
- **§4.18 Voice:** Voice-first commands (Idea 2) depend on §4.18 infrastructure.
- **§4.20 Planning:** Command-as-workflow (Idea 3) needs §4.20 MCTS.
- **§4.22 Steering:** Ambient suggestions (Idea 4) are a form of proactive steering.

### Architecture Impact
- **Command registry:** Extend from simple dict to support:
  - Pattern tracking (for Idea 1)
  - Context sensing (for Idea 4)
  - Workflow DAG (for Idea 3)
- **Storage:** `.lyra/commands/` for user commands, `.lyra/state/command_patterns.json` for auto-synthesis state.

### Migration Path
1. **Phase 1:** Parity (A) + Ambient Suggestions (Idea 4) — low risk, high value
2. **Phase 2:** Context-Aware Synthesis (Idea 1) — medium risk, high value
3. **Phase 3:** Workflow DAG MVP (Idea 3, no MCTS) — medium risk, very high value
4. **Phase 4:** Voice-first (Idea 2) after §4.18 ships
5. **Phase 5:** Full workflow planning (Idea 3 + MCTS) after §4.20 ships

---

## Final Recommendation

**Promote to Plan (B tier):**
1. Context-Aware Command Synthesis (Idea 1)
2. Ambient Command Suggestions (Idea 4)

**Park for later phases:**
3. Command-as-Workflow Planner (Idea 3) — MVP in Phase 3, full version in Phase 5
4. Voice-First Commands (Idea 2) — Phase 4 after §4.18

**Rationale:** Ideas 1 and 4 are **buildable today** without heavy dependencies, **high-impact** for usability, and **measurably better** than Claude Code's baseline (auto-learning + proactive discovery vs. manual authoring + manual lookup). Ideas 3 and 4 are strong but need infrastructure that doesn't exist yet — defer to preserve momentum.
