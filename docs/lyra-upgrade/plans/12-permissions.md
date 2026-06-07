# Permissions — Plan (§4.12)

> Run 1 — June 3, 2026 | Phase 1: Deny-first permission evaluation, compound command parsing, credential scoping, agent-view security

## Plain-Language Summary

Lyra currently has no permission system — every tool call either succeeds or fails without user awareness. This plan implements a deny-first permission model where rules are evaluated in order: deny -> ask -> allow (first match wins). It covers compound command parsing (pipelines, redirects, chains checked per-subcommand), symlink-aware path traversal prevention, per-session permission overrides, and credential scoping (each worktree session gets only its explicitly granted credentials). The key insight for an agent harness: permissions must be both fine-grained (per-tool, per-argument) and session-isolated (different sessions can have different permissions).

## 1. Problem

BASELINE.md rates Permissions maturity = `none`. Lyra has zero permission infrastructure:
- **No deny-first evaluation**: Every tool call can be executed. No way to block dangerous operations.
- **No compound command parsing**: `rm -rf / && echo "done"` treated as one command. Should evaluate each subcommand independently.
- **No path traversal prevention**: Write to `/etc/passwd` from a project session is allowed because there's no path check.
- **No credential scoping**: All credentials available to all sessions. A research agent can access production API keys.
- **No session override**: `bypass` mode for a session affects all sessions. No per-session permission differentiation.
- **No agent view security**: Background/unwatched sessions can make dangerous tool calls without visibility.

## 2. Evidence Synthesis

### Claude Code Permissions (§3.1)
The reference architecture: deny-first evaluation, three-action system (allow/ask/deny), tool-level rules with `ToolName(specifier)` format. Key specifics:
- Evaluation order: deny -> ask -> allow (first match wins)
- Compound command parsing: `&&`, `||`, `;`, `|`, `&`, newlines all parsed. Each subcommand checked independently.
- Process wrapper stripping: `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `xargs` (without flags) stripped before matching.
- Read-only commands: built-in set (`ls`, `cat`, `echo`, `pwd`, etc.) runs without prompt in every mode.
- Symlink handling: Allow rules check BOTH symlink path AND target. Deny rules block if EITHER matches.
- Permission modes: `default` (prompt on first use), `acceptEdits` (auto-approve file edits), `plan` (read-only), `auto` (auto-approve + background safety), `dontAsk` (auto-deny), `bypassPermissions` (skip all).
- JSON output capped at 10,000 characters.
- `additionalDirectories`: extends file access domain.

### Claude Code Sandboxing (§3.1)
OS-level enforcement: macOS Seatbelt, Linux bubblewrap. Dual-layer: permission rules + sandbox boundaries merged. Read/Edit deny rules merge with sandbox filesystem config. WebFetch deny rules merge with sandbox network allowlist.

### Claude Code Agent View Security (§3.1)
Background agents run with background permission mode (auto-deny tool calls that would prompt). File edit isolation via worktree by default.

### CaMeL (Google DeepMind, arXiv:2503.18813)
Dual-LLM architecture: Privileged LLM (sees task, generates plan) vs Quarantined LLM (sees data, executes). Capability-based data flow tracking with provenance + allowed readers. Formal security game (PI-SEC) with provable guarantees. 0 successful prompt injections out of 949 attacks on Gemini 2.5 Pro and o3 High (with policies). However, utility degradation is model-dependent: Claude 4 Sonnet drops from 86.6% to 74.2% (-12.4%), while weaker models like Claude 3.5 Sonnet drop from 90.72% to 63.92% (-26.8pp). 2.82x token overhead. Key structural insight: model-level defenses are probabilistic and fall to adaptive attacks; the system must be made robust regardless of model (2503.18813v2).

### Progent (UC Berkeley, arXiv:2504.11703)
Least-privilege enforcement at tool-call level using symbolic policies. SMT solver (Z3) for deterministic policy comparison. Monotonic Confinement: action space can only shrink without approval. AgentDojo: ASR reduced from 39.9% to 1.0% (97.5% relative reduction) with zero utility degradation (79.4% maintained). ASB benchmark: ASR from 70.3% to 3.9%. Tested across LangChain, OpenAI Agents SDK, OpenHands, and AutoGen (ASR: 56.7% -> 1.2%, 56.7% -> 0.8%, 61.3% -> 1.4%, 40.4% -> 0.8%). All four policy LLM configurations achieve <1.1% ASR. Manual approval mode achieves 0.0% ASR. 94% of policy updates are narrowings (auto-approved); 6% expansions (need human). Z3 SMT solver provides fully deterministic policy comparison -- no ML uncertainty in the enforcement path (2504.11703v3).

### AgentDojo (ETH Zurich, arXiv:2406.13352)
Tool filter defense reduces Targeted ASR from 47.69% to 6.84% (most effective single defense in original benchmark). However, fails when overlapping tools needed. Inverse scaling: smarter models = more vulnerable (Claude 3.5 Sonnet has 33.86% ASR vs Command-R+ 0.95% ASR for the important-message attack). Key findings: 629 total security test cases across 4 environments, 70 tools, 97 user tasks, 27 injection targets. No model exceeds 78% benign utility even without attacks. Claude 4 Sonnet achieves 78.22% as the top model. Repeat-prompt defense achieves highest utility (85.53%) but only 27.82% ASR reduction (2406.13352v3).

### LlamaFirewall (Meta AI, arXiv:2505.03574)
Layered defense-in-depth guardrail pipeline with three scanners orchestrated by a policy engine: (1) PromptGuard 2 -- DeBERTa-based jailbreak classifier (86M or 22M parameters, 19.3ms on CPU for 22M variant, 97.5% recall @ 1% FPR, 4.6x improvement over v1); (2) AlignmentCheck -- few-shot LLM auditor checking agent CoT alignment with original user objective (83.6% ASR reduction when used alone with Llama 4 Maverick); (3) CodeShield -- two-tier Semgrep-based static analysis (60ms regex tier + 300ms full analysis tier, 96% precision, 79% recall). Combined defense: 90.1% ASR reduction on AgentDojo (17.6% -> 1.8%) with 10.6pp utility cost. PromptGuard alone reduces ASR 57% with only 1.5pp utility cost. The policy engine supports conditional remediation (block, flag, rewrite, log) and plug-in architecture for new detectors (2505.03574v1).

### Llama Guard (Meta GenAI, arXiv:2312.06674)
Single instruction-tuned Llama2-7B model classifying both user prompts and agent responses against a pluggable 6-category safety taxonomy. Taxonomy passed as part of model prompt -- zero-shot switching without retraining. First-token probability P("unsafe") provides continuous risk score for threshold tuning. Results: AUPRC 0.945 (prompt) / 0.953 (response) on own test set, outperforming OpenAI Moderation API (0.764/0.769) and Perspective API (0.728/0.699). Few-shot adaptation to new taxonomies: 0.872 AUPRC vs OpenAI 0.856. 20% of domain data matches 100% of prior SOTA. Open weights. The 7B parameter size enables fine-tuning for application-specific safety taxonomies (2312.06674v1).

### NeMo Guardrails (NVIDIA, arXiv:2310.10501)
Runtime dialogue manager with programmable Colang rails. Three-stage proxy pipeline: (1) canonical form generation via few-shot retrieval from vector DB, (2) event-driven Colang interpreter for pre-defined or LLM-generalized flows, (3) bot response generation. Rail types: topical (dialogue flow control), fact-checking (entailment task, 80% accuracy on MSMARCO), hallucination (SelfCheckGPT variant, 65% -> 95% deflection on gpt-3.5-turbo), input moderation (jailbreak), output moderation. Results on text-davinci-003: harmful blocked 24% (no rails) to 97% (both rails). Cost: ~3x latency and ~3x cost overhead vs single LLM call. Explicitly states: "should not be used as a stand-alone solution, especially for safety-specific rails" -- they supplement, not replace, embedded alignment (2310.10501v1).

### ACI-SENTINEL (Zhejiang/Tsinghua/UCLA, arXiv:2604.07775)
Semantic pruning defense: prunes agent context after each step to retain only semantically essential information causally aligned with the original task (Principle of Contextual Least Privilege). Prompt-only -- no model training. Results on ACIARENA benchmark (1,356 test cases, 28 attacks, 6 MAS implementations): AutoGen exfiltration ASR 54.0% -> 0.22% (53.33pp reduction). MetaGPT hijacking ASR 79.44% -> 0.00% (complete neutralization). Key weakness: degrades under adaptive attacks (ASR rebounds from 0% -> 10-37%). 5.6pp utility cost. Traditional defenses like prompt sandwiching can amplify other attack types (+6pp exfiltration on AutoGen). First systematic MAS robustness benchmark (2604.07775v1).

### A-Trust (MSU/Amazon, arXiv:2506.02546)
Attention-based trust scoring for multi-agent communication. Extracts attention weights from a dedicated LLM, trains lightweight logistic regression classifiers (one per Gricean trust dimension: factual accuracy, logical consistency, relevance, bias, clarity, language quality). Six per-dimension scores form the A-Trust score vector. A Trust Management System enforces per-dimension thresholds and maintains agent-level trust records with sliding-window violation tracking. Results: Message Detection Rate >80% across diverse attacks and agent structures. ASR reduction: 94.6% -> 23.5% (AiTM attack, MMLUPhy), 90.1% -> 18.7% (StrategyQA). Agent-level detection rate 100% across all conditions. With agent trust records: AiTM ASR drops to 0.8-2.5%. 28x faster than prompt-based evaluation (0.41s vs 11.71s). Cross-model generalization (Llama, GPT-4o, Qwen2.5, Gemma3). Clean accuracy degradation <2%. Limitation: white-box requirement (needs attention matrix access) -- not applicable to API-only deployments (2506.02546v2).

### Self-Evolution Safety Degradation (Shanghai AI Lab/SJTU/Princeton, arXiv:2509.26354, ICLR 2026)
Formalizes four pathways through which self-evolution degrades safety: (1) Model -- RL self-play causes 4.5-30.7pp safety drops even with benign data; optimization pressure, not data quality, is the primary cause; (2) Memory -- accumulating biased correlations causes agents to optimize for proxy metrics (SE-Agent Qwen3-Coder-480B: RedCode Refusal Rate 99.4% -> 54.4%, -45pp); (3) Tool -- tool creation/reuse without security re-evaluation yields 65.5% overall unsafe rate; (4) Workflow -- MCTS optimization amplifies unsafe outputs (Refusal Rate 36.3% -> 5.6%). Mitigations: DPO only partially restores safety (59.5% -> 62.75% but fails to restore initial levels); "memories are references, not rules" prompt cuts ASR from 20.6% -> 13.1%. None return to pre-evolution baselines (2509.26354v2).

### Book Evidence
- **Agentic Architectural Patterns** (Arsanjani, ch. "Safety by Construction"): Endorses externalized privilege control as superior to prompt-level guardrails. States that safety-by-construction externalizes safety into structural components rather than embedding it in prompts. Directly supports the Progent/CaMeL structural approach.
- **Agentic Enterprise** (Hodjat, ch. 7): "Use safeguard agents for compliance -- externalize safety into a separate agent rather than embedding it in system prompts. This is more effective and auditable." Recommends "wrap every tool in scoped permissions (read vs. write), argument limits, allowlists."
- **Building Reliable AI Systems**: Structures reliability framework around three layers: outputs, agents, and operations. Validates that structural guarantees at the system level matter more than model-level robustness.
- **AI Agents in Action**: Recommends guardrails/evaluation as a mandatory component of any autonomous agent deployment. Endorses the five-level automation approach that LlamaFirewall's policy engine implements.

### BREAKTHROUGH-ARCHITECTURE.md
Permissions in Capability Plane. Deny-first evaluation, auto-gated modes, sandbox integration.

## 3. Proposed Lyra Design

### 3.1 Deny-First Permission Evaluation

```python
@dataclass
class PermissionRule:
    action: Literal["allow", "deny", "ask"]
    tool: str                       # "Bash", "Write", "Read(/secrets/*)"
    user: str | None = None         # Specific user this applies to
    session: str | None = None      # Specific session this applies to
    condition: str | None = None    # Optional permission-rule expression
    priority: int = 0

    def matches(self, tool_name: str, tool_args: dict, context: PermissionContext) -> bool:
        # Tool matching: "Bash" matches any Bash call
        # "Write(/etc/passwd)" matches Write with specific path
        if self.tool == tool_name:
            return True
        if "(" in self.tool:
            name, specifier = self.tool.split("(", 1)
            specifier = specifier.rstrip(")")
            if name == tool_name and fnmatch.fnmatch(tool_args.get("file_path", ""), specifier):
                return True
        return False


class PermissionEngine:
    """Deny-first permission evaluation.

    Evaluation order:
    1. Collect all matching rules for the current tool call
    2. Sort by action order: deny (highest priority) -> ask -> allow
    3. Apply first match

    If no rule matches: default = ask (user prompt).
    """

    def __init__(self):
        self._rules: list[PermissionRule] = []
        self._session_overrides: dict[str, PermissionMode] = {}

    def evaluate(self, tool: str, args: dict, context: PermissionContext) -> PermissionDecision:
        matching = self._get_matching_rules(tool, args, context)

        # Check session override first
        session_mode = self._session_overrides.get(context.session_id)

        # Check for plan mode (read-only)
        if session_mode == "plan":
            if tool in ("Read", "Glob", "Grep", "WebFetch"):
                return PermissionDecision.ALLOW
            return PermissionDecision.DENY

        # Deny -> Ask -> Allow order
        for rule in sorted(matching, key=self._action_priority):
            if rule.action == "deny":
                return PermissionDecision.DENY
            if rule.action == "allow":
                return PermissionDecision.ALLOW
            # "ask" continues to check next rule, but default is ask anyway

        # Default: ask (unless session mode overrides)
        if session_mode == "auto":
            return PermissionDecision.AUTO_ALLOW
        if session_mode == "acceptEdits":
            if tool in ("Edit", "Write", "Read", "Glob", "Grep"):
                return PermissionDecision.AUTO_ALLOW
        if session_mode == "bypass":
            return PermissionDecision.BYPASS

        return PermissionDecision.ASK

    @staticmethod
    def _action_priority(rule: PermissionRule) -> int:
        return {"deny": 0, "ask": 1, "allow": 2}[rule.action]
```

### 3.2 Permission Modes

```python
class PermissionMode(str, Enum):
    DEFAULT = "default"           # Prompt on first use of each tool
    ACCEPT_EDITS = "acceptEdits"  # Auto-approve file edits + common commands
    PLAN = "plan"                 # Read-only: reads, no edits, no writes
    AUTO = "auto"                 # Auto-approve with background safety checks
    DONT_ASK = "dontAsk"          # Auto-deny unless pre-approved
    BYPASS = "bypassPermissions"  # Skip all prompts (with circuit breaker)

# Mode behavior matrix:
# | Mode | File Reads | File Edits | Bash | Web | Subagent |
# |------|-----------|------------|------|-----|----------|
# | default | ask 1st | ask 1st | ask 1st | ask 1st | ask 1st |
# | acceptEdits | auto | auto | auto | ask 1st | ask 1st |
# | plan | auto | deny | deny | deny | deny |
# | auto | auto | auto | auto | auto | auto |
# | dontAsk | deny | deny | deny | deny | deny |
# | bypass | auto | auto | auto | auto | auto |
```

### 3.3 Compound Command Parsing

```python
class CompoundCommandParser:
    """Parse compound shell commands and evaluate each subcommand independently.

    Supports: &&, ||, ;, |, &, newlines, subshells $(), ().
    """

    SPLIT_PATTERNS = [
        r"\|\|",   # OR
        r"&&",      # AND
        r";",      # Sequential
        r"\|",     # Pipe
        r"&",      # Background
    ]

    # Commands to strip before evaluation
    PROCESS_WRAPPERS = ["timeout", "time", "nice", "nohup", "stdbuf", "xargs"]

    @classmethod
    def parse(cls, command: str) -> list[str]:
        """Split compound command into individual subcommands."""
        result = [command]
        for pattern in cls.SPLIT_PATTERNS:
            expanded = []
            for cmd in result:
                expanded.extend(re.split(pattern, cmd))
            result = expanded
        return [cls.strip_wrappers(c.strip()) for c in result if c.strip()]

    @classmethod
    def strip_wrappers(cls, command: str) -> str:
        """Remove process wrappers (timeout, etc.) before matching."""
        parts = shlex.split(command)
        while parts and parts[0] in cls.PROCESS_WRAPPERS:
            parts = parts[1:]
            # Some wrappers take arguments (timeout 30 -> skip 30 too)
            if parts[0].isdigit():
                parts = parts[1:]
        return " ".join(parts)
```

### 3.4 Read-Only Commands

Built-in set that runs without prompt in every mode (including plan):

```python
READ_ONLY_COMMANDS = {
    "ls", "cat", "echo", "pwd", "head", "tail", "wc",
    "which", "type", "command", "file", "stat", "du", "df",
    "env", "printenv", "date", "cal",
    "find", "grep", "rg", "ag", "ack",
    "diff", "cmp", "comm",
    "python3 --version", "node --version", "npm --version",
    "curl --version", "git --version",
    "type", "where", "man", "help",
}

def is_read_only(command: str) -> bool:
    cmd = command.strip().split()[0] if command.strip() else ""
    return cmd in READ_ONLY_COMMANDS
```

### 3.5 Symlink Handling + Path Traversal Prevention

```python
class PathSafety:
    """Path traversal prevention with symlink awareness."""

    def __init__(self, allowed_bases: list[str]):
        self.allowed_bases = [os.path.abspath(p) for p in allowed_bases]

    def is_path_allowed(self, path: str, allow_symlinks_outside: bool = False) -> bool:
        """Check if a path is within allowed bases, considering symlinks.

        Allow rules check BOTH the symlink path AND the resolved target.
        If either is outside allowed bases, the path is NOT allowed.
        """
        resolved = os.path.abspath(os.path.realpath(path))

        # Check resolved path (following symlinks)
        for base in self.allowed_bases:
            if resolved.startswith(base):
                return True

        if not allow_symlinks_outside:
            # Also check the unresolved path (the symlink itself)
            unresolved = os.path.abspath(path)
            for base in self.allowed_bases:
                if unresolved.startswith(base):
                    return True

        return False
```

### 3.6 Per-Session Permission Overrides

```python
class SessionPermissionStore:
    """Per-session permission state, persisted across turns."""

    def __init__(self):
        self._sessions: dict[str, SessionPermissions] = {}

    def get_or_create(self, session_id: str) -> SessionPermissions:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionPermissions(session_id)
        return self._sessions[session_id]

    async def save(self, path: str):
        """Persist session permissions to disk."""
        data = {sid: perms.to_dict() for sid, perms in self._sessions.items()}
        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def load(self, path: str):
        """Load session permissions from disk."""
        try:
            async with aiofiles.open(path) as f:
                data = json.loads(await f.read())
            for sid, perms_data in data.items():
                self._sessions[sid] = SessionPermissions.from_dict(sid, perms_data)
        except FileNotFoundError:
            pass


@dataclass
class SessionPermissions:
    session_id: str
    mode: PermissionMode = PermissionMode.DEFAULT
    remembered_decisions: dict[str, bool] = field(default_factory=dict)
    # "Bash:/usr/bin/git": True  (previously allowed)
    # "Write:/etc/passwd": False (previously denied)
    credential_scopes: list[str] = field(default_factory=list)
    # List of credential names available to this session
```

### 3.7 Credential Scoping

```python
class CredentialScope:
    """Each worktree session gets only its explicitly granted credentials.

    Credential sources:
    - Environment variables (.env files)
    - Credential helpers (git credential, keychain)
    - Secret manager integration

    Scoping:
    - Each session declares which credentials it needs in its worktree config
    - Only declared credentials are injected into the session's environment
    - Different sessions running simultaneously have disjoint credential sets
    """

    def __init__(self, credential_store: dict[str, str]):
        self._store = credential_store  # All available credentials
        self._grants: dict[str, set[str]] = {}  # session_id -> {credential_names}

    def grant(self, session_id: str, credential_names: list[str]):
        """Explicitly grant credentials to a session."""
        if session_id not in self._grants:
            self._grants[session_id] = set()
        self._grants[session_id].update(credential_names)

    def get_environment(self, session_id: str) -> dict[str, str]:
        """Get the environment dict for a session (only granted credentials)."""
        granted = self._grants.get(session_id, set())
        return {name: self._store[name] for name in granted if name in self._store}

    # Principle: a session never sees credentials it hasn't been explicitly granted.
    # This prevents: research agent accessing prod API keys, review agent using deploy tokens.
```

### 3.8 Agent View Security Guardrail

```python
class AgentViewSecurity:
    """Security guardrail for unwatched/background sessions.

    Key principle: background/unwatched sessions cannot use bypass or auto modes
    unless a human has explicitly accepted those modes for that session.
    """

    def can_use_mode(self, session_id: str, mode: PermissionMode,
                     is_background: bool, is_watched: bool) -> bool:
        """Check if a session can use the requested mode."""
        if mode in (PermissionMode.BYPASS, PermissionMode.AUTO):
            # Bypass/auto require explicit human accept
            if is_background and not is_watched:
                return False  # No one watching -> cannot auto-approve self
            if not self._human_accepted(session_id, mode):
                return False  # Human hasn't approved this mode for this session
        return True

    def human_accept(self, session_id: str, mode: PermissionMode):
        """Record human acceptance of a mode for a session."""
        self._acceptances[(session_id, mode)] = datetime.now()

    # This prevents: agent running in background switching to bypass mode
    # and making dangerous tool calls without oversight.
```

### 3.9 Rule Configuration Format

```yaml
# .lyra/permissions.yaml — Permission rules

permissions:
  # Deny rules (evaluated first)
  - action: deny
    tool: "Bash(rm -rf *)"
    reason: "Prevent accidental deletion"

  - action: deny
    tool: "Write(/etc/*)"
    reason: "System files are read-only"

  - action: deny
    tool: "Write"
    condition: "path == '/etc/passwd' || path == '/etc/shadow'"
    reason: "Never write to /etc/passwd or /etc/shadow"

  # Allow rules (evaluated last)
  - action: allow
    tool: "Read"
    condition: "path.startswith(project_dir)"

  - action: allow
    tool: "Bash"
    condition: "is_read_only(command)"

  - action: allow
    tool: "Bash(git *)"
  - action: allow
    tool: "Bash(python3 *)"
  - action: allow
    tool: "Bash(npm *)"

  # Allow specific directories
  - action: allow
    tool: "Write"
    condition: "path.startswith(project_dir + '/src')"
  - action: allow
    tool: "Write"
    condition: "path.startswith(project_dir + '/tests')"
```

### 3.10 Architecture Diagram

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#7c3aed',
  'primaryTextColor': '#e2e8f0',
  'primaryBorderColor': '#a78bfa',
  'lineColor': '#818cf8',
  'secondaryColor': '#1e293b',
  'tertiaryColor': '#0f172a',
  'background': '#0d0d1a',
  'mainBkg': '#1e293b',
  'nodeBorder': '#6366f1',
  'clusterBkg': '#111827',
  'clusterBorder': '#4f46e5',
  'titleColor': '#c084fc',
  'edgeLabelBackground': '#1e293b',
  'nodeTextColor': '#e2e8f0',
  'fontSize': '14px'
}}}%%
graph TB
    subgraph "Tool Call Flow"
        TC[Tool Call<br/>Name + Arguments]
        CC[Compound Command Parser<br/>Split && | ; &]
        PWS[Process Wrapper Stripper<br/>Strip timeout/nice/nohup]
    end

    subgraph "Permission Engine (§4.12)"
        PM[Permission Mode<br/>default/acceptEdits/plan/auto/...]
        RULES[Rule Evaluation<br/>Deny → Ask → Allow]
        ROC[Read-Only Check<br/>Built-in command set]
        PATH[Path Safety<br/>Symlink-aware traversal check]
        CRED[Credential Scope<br/>Session-specific grants]
        AVS[Agent View Security<br/>Background session guard]
    end

    subgraph "Decision"
        ALLOW[ALLOW]
        DENY[DENY]
        ASK[ASK → User Prompt]
        AUTO[Auto-Allow<br/>Background safety check]
    end

    subgraph "Policy Sources"
        CONFIG[permissions.yaml]
        SESSION[Session Override]
        MODE[Mode Selection]
        HISTORY[Previous Decisions<br/>Session Memory]
    end

    TC --> CC
    CC --> PWS
    PWS --> RULES

    CONFIG --> RULES
    SESSION --> PM
    MODE --> PM
    PM --> RULES
    HISTORY --> RULES

    RULES --> ROC
    RULES --> PATH
    RULES --> CRED
    RULES --> AVS

    ROC --> ALLOW
    PATH -->|Blocked| DENY
    CRED -->|Missing| DENY
    AVS -->|Block| DENY

    RULES --> ALLOW
    RULES --> DENY
    RULES --> ASK
    RULES --> AUTO
```

## 4. Data Model

```python
@dataclass
class PermissionRule:
    action: Literal["allow", "deny", "ask"]
    tool: str
    user: str | None = None           # Specific user
    session: str | None = None        # Specific session
    condition: str | None = None      # Permission expression
    priority: int = 0
    reason: str = ""                  # User-facing reason


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"
    AUTO_ALLOW = "auto_allow"          # Background safety check passed
    BYPASS = "bypass"                 # Circuit breaker still applies


@dataclass
class PermissionContext:
    session_id: str
    user_id: str | None = None
    project_dir: str = ""
    is_background: bool = False
    is_watched: bool = True
    mode: PermissionMode = PermissionMode.DEFAULT
```

## 5. Build Outline

### Phase 1a — Permission Engine (Week 1)
- [ ] Implement `PermissionEngine` with deny-first evaluation in `src/permissions/engine.py`
- [ ] Implement `PermissionRule` dataclass with `matches()` method
- [ ] Implement `PermissionMode` enum and mode-to-behavior mapping
- [ ] Implement `PermissionDecision` enum
- [ ] **Dependency:** None

### Phase 1b — Compound Command Parsing (Week 1-2)
- [ ] Implement `CompoundCommandParser` with all split patterns
- [ ] Implement process wrapper stripping (`timeout -> nice -> actual_command`)
- [ ] Implement read-only command set
- [ ] Unit tests: complex compound commands, nested subshells
- [ ] **Dependency:** Phase 1a

### Phase 1c — Path Safety + Symlink Handling (Week 2)
- [ ] Implement `PathSafety` with symlink-aware path checking
- [ ] Allowed base paths from project configuration
- [ ] `additionalDirectories` extension points
- [ ] Unit tests: symlink chains, directory traversal, edge cases
- [ ] **Dependency:** Phase 1a

### Phase 1d — Session Permissions + Credential Scoping (Week 2-3)
- [ ] Implement `SessionPermissionStore` with disk persistence
- [ ] Implement per-session mode override
- [ ] Implement `CredentialScope` for credential isolation per worktree
- [ ] Implement `AgentViewSecurity` guardrail
- [ ] **Dependency:** Phase 1a

### Phase 1e — Configuration + Integration (Week 3-4)
- [ ] Implement YAML config parser for permission rules
- [ ] Implement config merge across scopes (user -> project -> local)
- [ ] Wire permission engine into Tool Registry (§4.6) tool call path
- [ ] Wire into Hook System (§4.10) PermissionRequest/PermissionDenied/PermissionGranted events
- [ ] Write `premission` CLI command for viewing/testing rules
- [ ] Integration tests: full tool call flow with permissions
- [ ] **Dependency:** Phase 1b, 1c, 1d, §4.6 Tools

## 6. Multi-Provider Note

Permissions are harness-level, not provider-level. The permission engine sits BEFORE the provider encoding layer:
- Tool calls are evaluated by the permission engine in Lyra's internal `ToolCall` format
- Only allowed tool calls are encoded into provider-specific formats
- Denied tool calls never reach the provider
- This ensures uniform permission enforcement regardless of whether the backend is Claude, DeepSeek, GPT, or open-weights

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Compound command parser misses edge cases | Medium | High | Aggressive test suite; fall through to `ask` on unparseable |
| Symlink check breaks legitimate symlink use | Medium | Medium | `allow_symlinks_outside` flag for project-aware symlinks |
| Credential scoping too restrictive breaks workflows | High | Medium | Clear error messages; per-credential grant requests |
| Utility degradation from layered defenses | High | Medium | CaMeL shows 12-32% utility loss model-dependent (2503.18813v2); LlamaFirewall shows 10.6pp utility cost for full layered stack (2505.03574v1). Mitigation: use PromptGuard alone (~1.5pp utility cost) as primary gate; invoke deeper checks on sampling schedule |
| Permission rule YAML too complex for users | High | Medium | Provide common rule templates; `--init-permissions` command |
| SMT solver latency on policy updates | Medium | Low | Progent: SMT check takes ~0.5s per policy update (2504.11703v3); only triggered on proposed policy changes, not every tool call. 94% of updates are narrowings (auto-approved, no SMT needed) |
| CaMeL token overhead for capability tracking | Medium | Medium | 2.82x token overhead (2503.18813v2). Mitigation: apply only to high-risk tool calls or use sampling |
| Adaptive attack rebound after deploying defense | Low | High | ACI-SENTINEL degrades from 0% to 10-37% ASR under adaptive attacks (2604.07775v1). No defense in corpus has been evaluated against a fully adaptive adversary. Mitigation: multi-layer defense that attackers cannot jointly predict |

## 8. (A) Parity vs (B) Breakthrough

### (A) Parity — What Claude Code already does
- Deny-first evaluation: deny -> ask -> allow
- Tool-level rules with `ToolName(specifier)` format
- Compound command parsing (&&, ||, ;, |, &, newlines)
- Process wrapper stripping (timeout, time, nice, nohup, stdbuf, xargs)
- Read-only command set
- Symlink-aware path matching (allow checks both, deny blocks either)
- Permission modes: default, acceptEdits, plan, auto, dontAsk, bypass
- Config merge across user/project/local scopes

### (B) Breakthrough — What Lyra adds
- **Credential scoping per worktree session** — Each parallel session gets only explicitly granted credentials. Claude Code has sessions but no cross-session credential isolation.
- **Agent View security guardrail** — Background/unwatched sessions cannot use bypass/auto without prior human accept. Prevents background agent privilege escalation.
- **SMT-based monotonic confinement integration** (Phase 2) — Progent-style initial policy generation + Z3 expansion check (2504.11703v3). Lyra's permission system can auto-generate least-privilege policies from task descriptions. Progent demonstrates 97.5% ASR reduction with zero utility degradation.
- **Layered defense-in-depth architecture** (Phase 2) — Following LlamaFirewall's proven pattern (2505.03574v1): fast lexical gate (PromptGuard 2, 19.3ms on CPU, 97.5% recall @ 1% FPR) + slow semantic auditor (AlignmentCheck-style CoT auditing, 83.6% ASR reduction alone) + CodeShield static analysis for generated code. Combined: 90.1% ASR reduction, though with 10.6pp utility cost.
- **Safety auditor agent** — Structurally separate LLM instance (following CaMeL's dual-LLM pattern, 2503.18813v2, and Hodjat's "externalize safety into a separate agent" principle) that audits agent CoT without seeing raw tool outputs. Can halt execution on detected misalignment.
- **Per-session permission persistence** — Remembered decisions persist across turns and survive session resume. Different sessions have independent decision histories.
- **Continuous safety evaluation against misevolution** (Phase 2) — Following "Your Agent May Misevolve" findings (2509.26354v2, ICLR 2026): safety degrades 4.5-45pp across all evolutionary pathways. Lyra needs continuous safety regression testing that itself evolves as the agent evolves.

## 9. Baseline Delta

| Dimension | Before (Lyra current) | After (with Permissions) |
|-----------|----------------------|--------------------------|
| Evaluation model | None (all allowed) | Deny-first: deny -> ask -> allow |
| Tool-level rules | None | `ToolName(specifier)` with fnmatch |
| Compound commands | None | Full parsing of &&, ||, ;, |, & |
| Read-only commands | None | Built-in set in every mode |
| Path traversal | None | Symlink-aware path checking |
| Credential isolation | None (all shared) | Per-session credential scoping |
| Session overrides | None | Per-session mode + decision history |
| Background security | None | Unwatched -> no bypass/auto without accept |
| Config format | None | YAML with merge across scopes |

## 9a. Trade-off Analysis

### Technique Trade-offs

| Technique | ASR Reduction | Utility Cost | Latency | Complexity | Best For |
|-----------|--------------|-------------|---------|------------|----------|
| **Deny-first evaluation** (Claude Code pattern) | Baseline | 0% (no LLM calls) | ~0ms | Low | Every tool call, always-on |
| **Progent-style SMT gating** | 97.5% relative (39.9% -> 1.0%) | 0% (79.4% maintained) | ~0.5s per policy update | Medium (Z3 + policy LLM) | High-risk tool calls; Phase 2 integration |
| **CaMeL dual-LLM tracking** | 100% on Gemini 2.5 Pro (949 attacks -> 0) | -12 to -32% (model-dependent) | 2.82x token overhead | Very High (custom AST interpreter) | High-security deployments; not for every session |
| **LlamaFirewall PromptGuard 2** | 57% relative (17.6% -> 7.5%) | -1.5pp (47.73% -> 47.01%) | 19ms (22M) / 92ms (86M) | Low (pre-trained classifier) | Input gate for every tool call |
| **LlamaFirewall AlignmentCheck** | 83.6% relative (alone; 17.6% -> 2.9%) | -4.6pp (47.73% -> 43.09%) | 1 LLM call per check | Medium (few-shot prompt) | Sampled deep audit for subtle drift |
| **LlamaFirewall full stack** | 90.1% relative (17.6% -> 1.8%) | -10.6pp (47.73% -> 42.68%) | 19ms + LLM + 300ms | Medium (YAML pipeline) | Defense-in-depth for critical paths |
| **ACI-SENTINEL semantic pruning** | 53.33-79.44pp reduction (AutoGen/MetaGPT) | -5.6pp (57.78 -> 52.22) | 1 LLM call per step | Very Low (prompt-only) | Post-step context cleanup; degrades under adaptive attacks |
| **Llama Guard I/O classifier** | N/A (classification accuracy: 0.945 AUPRC) | N/A (separate model) | 1 LLM forward pass | Low (pre-trained 7B) | Input/output content moderation |
| **NeMo Guardrails pipeline** | 24% -> 97% harmful blocked (text-davinci-003) | -5pp false positives | ~3x latency, ~3x cost | Medium-High (Colang flows) | High-stakes dialogue guardrails |
| **A-Trust attention scoring** | 75.1% relative (94.6% -> 23.5% ASR) | <2% clean accuracy loss | 0.41s per message (28x faster than prompt) | Medium (LR classifiers) | Multi-agent trust scoring; white-box only |
| **"Memories as references" prompt** | 20.6% -> 13.1% ASR (memory misevolution) | ~0% (prompt-only change) | 0 additional latency | Very Low (system prompt line) | Memory subsystem safety (Phase 2) |

### Key Design Decision: Which Layer, When?

Based on the evidence, Lyra should NOT deploy all techniques on every tool call. The recommended layering:

1. **Always-on (0ms-19ms overhead):** Deny-first evaluation (Claude Code pattern) + PromptGuard 2 22M lexical gate. These catch 57% of attacks with only 1.5pp utility cost and negligible latency.
2. **On-sampling or high-risk paths:** AlignmentCheck-style CoT auditor (1 LLM call) + CodeShield static analysis on generated code. These catch the remaining injection types with 10.6pp utility cost.
3. **Per-session init (~0.5s):** Progent-style SMT policy generation from task description. Establishes initial least-privilege boundaries.
4. **Post-step (Phase 2):** ACI-SENTINEL-style semantic context pruning for sessions that process untrusted data. Prompt-only cost.
5. **Continuous (Phase 2):** Safety regression tests against misevolution. Periodic, not per-turn.

This layering is supported by the synthesis convergence that "no single defense suffices" and that multi-layer defense-in-depth is mandatory (LlamaFirewall 2505.03574v1, NeMo Guardrails 2310.10501v1, "Towards Trustworthy Agentic AI" 2605.23989v1).

### Adaptation Risk

All tested defenses degrade under adaptive attack. ACI-SENTINEL rebounds from 0% to 10-37% ASR (2604.07775v1). LlamaFirewall was evaluated against "static attack datasets, not adversaries who adapt to the defenses" (2505.03574v1). Progent's manual approval mode achieves 0.0% ASR but requires human-in-the-loop (2504.11703v3). **Lyra must assume that any single deployed defense will be partially bypassed within months of deployment.** The mitigation is heterogeneity: deploying structurally different defenses (deterministic + ML + prompt-based) so attackers must find multiple independent bypasses simultaneously.

## 10. Expert Review

### Reviewer 1: Security Engineer
"The deny-first model is correct but the default behavior (no matching rule = `ask`) is too permissive for an unattended fleet. I'd add a `defaultAction` config option so operators can set `defaultAction: deny` for production deployments. The compound command parser needs to handle heredocs (`<<EOF`), backticks, and `$(...)` subshells — these are common in CI scripts. The process wrapper stripping is a nice touch: without it, `timeout 30 rm -rf /` wouldn't match the `rm` deny rule."

### Reviewer 2: Systems Architect
"Credential scoping per worktree session is the right design but the implementation is high-risk: if credential isolation leaks (one session reads another's env vars), it's a security incident. I'd implement it at the OS level: use separate env vars per subprocess, not a shared credential store. The `.lyrainclude` file concept from the worktree plan is where credential grants are declared. For the circuit breaker on bypass mode: Claude Code's approach is correct — only block dangerous read/write to `/` and `~`."

### Reviewer 3: User Experience Designer
"The YAML permission rules format is powerful but intimidating. Provide a `lyra init-permissions` command that generates reasonable defaults. The `ask` mode is annoying for frequent operations — make sure remembered decisions persist across turns (per Claude Code: first use prompts, subsequent uses auto-approve within session). The permission modes need clear UI indicators: show `[plan]` or `[bypass]` in the status bar so users always know what mode they're in."

## 11. References

1. Claude Code Permissions — code.claude.com/docs/en/permissions. Deny-first evaluation, compound parsing, symlink handling.
2. Claude Code Sandboxing — code.claude.com/docs/en/sandboxing. OS-level enforcement, dual-layer (permissions + sandbox).
3. Progent — arXiv:2504.11703v3 (UC Berkeley). SMT-based monotonic confinement, 1.0% ASR on AgentDojo, 3.9% on ASB.
4. CaMeL — arXiv:2503.18813v2 (Google DeepMind/ETH). Dual-LLM architecture, capability tracking, 0/949 attacks on Gemini 2.5 Pro.
5. AgentDojo — arXiv:2406.13352v3 (ETH Zurich). Prompt injection benchmark, tool filter 6.84% ASR, inverse scaling.
6. LlamaFirewall — arXiv:2505.03574v1 (Meta AI). Layered defense pipeline, 90.1% ASR reduction, PromptGuard 2.
7. Llama Guard — arXiv:2312.06674v1 (Meta GenAI). LLM-based I/O safeguard, 0.945 AUPRC, open weights.
8. NeMo Guardrails — arXiv:2310.10501v1 (NVIDIA). Programmable Colang rails, 3x cost overhead, 97% harmful blocked.
9. ACI-SENTINEL — arXiv:2604.07775v1 (Zhejiang/Tsinghua/UCLA). Semantic pruning defense, ACIARENA benchmark.
10. A-Trust — arXiv:2506.02546v2 (MSU/Amazon). Attention-based trust scoring, 0.8-2.5% ASR with trust records.
11. "Your Agent May Misevolve" — arXiv:2509.26354v2 (Shanghai AI Lab, ICLR 2026). Self-evolution safety degradation, 4.5-45pp across 4 pathways.
12. Agentic Architectural Patterns (Arsanjani). Safety-by-construction chapter, externalized privilege control.
13. Agentic Enterprise (Hodjat). Ch. 7: safeguard agents, tool scoping, least privilege.
14. Building Reliable AI Systems. Three-layer reliability framework, system-level vs model-level robustness.
15. AI Agents in Action. Guardrails/evaluation as mandatory component, five-level automation.
16. "Towards Trustworthy Agentic AI" — arXiv:2605.23989v1 (CUHK/Fudan). Four-tier assurance stack, recursive trust problem.
17. AgenticEval — arXiv:2509.26100v2 (Fudan/Shanghai AI Lab). Self-evolving safety evaluation, 36pp more failures discovered.
18. BREAKTHROUGH-ARCHITECTURE.md — Permissions in Capability Plane, deny-first evaluation.
19. BASELINE.md — Lyra current state: `none` maturity for §4.12 Permissions.

## 12. Evidence Base

### Paper Notes Consulted
All sources from `notes/papers/` and `notes/books/` directories:

| Source | File | Key Evidence Extracted |
|--------|------|----------------------|
| Progent (2504.11703v3) | notes/papers/2504.11703v3.md | SMT-based monotonic confinement, 97.5% ASR reduction, zero utility degradation, 4 framework integration |
| CaMeL (2503.18813v2) | notes/papers/2503.18813v2.md | Dual-LLM architecture, 0/949 attacks, 12-32% utility cost, PI-SEC formal security game |
| AgentDojo (2406.13352v3) | notes/papers/2406.13352v3.md | Benchmark methodology, inverse scaling, tool filter 6.84% ASR, 629 security test cases |
| LlamaFirewall (2505.03574v1) | notes/papers/2505.03574v1.md | Layered guardrail pipeline, PromptGuard 2 97.5% recall @ 1% FPR, 90.1% ASR reduction, CodeShield |
| Llama Guard (2312.06674v1) | notes/papers/2312.06674v1.md | LLM-based I/O safeguard, 0.945 AUPRC, open weights, zero-shot taxonomy switching |
| NeMo Guardrails (2310.10501v1) | notes/papers/2310.10501v1.md | Colang programmable rails, 3x cost overhead, 97% harmful blocked, "not standalone" |
| ACI-SENTINEL (2604.07775v1) | notes/papers/2604.07775v1.md | Semantic pruning, 1,356 test cases, 79.44% -> 0.00% ASR, adaptive attack rebound |
| A-Trust (2506.02546v2) | notes/papers/2506.02546v2.md | Attention-based trust scoring, 6 Gricean dimensions, 28x faster than prompt, white-box limit |
| Misevolution (2509.26354v2) | notes/papers/2509.26354v2.md | 4 pathways of safety degradation, 4.5-45pp drops, mitigations partially effective |
| Agentic Architectural Patterns | notes/books/agentic-architectural-patterns-arsanjani-chapters.md | Safety-by-construction, externalized privilege control |
| Agentic Enterprise (Hodjat) | notes/books/agentic-enterprise-hodjat-chapters.md | Safeguard agents, tool scoping, least privilege |
| Building Reliable AI Systems | notes/books/building-reliable-ai-systems-chapters.md | Three-layer reliability framework |
| AI Agents in Action | notes/books/ai-agents-in-action-chapters.md | Guardrails/evaluation mandatory, five-level automation |

### Synthesis Source
- `synthesis/safety.md` — Thematic synthesis of 16 papers, 5 books, and 3 web/repo notes on Safety, Guardrails & Security. All 7 recommendations were consulted for the trade-off analysis and layering decisions.

## 13. Changelog
- Run 1: Initial plan — deny-first evaluation, compound command parsing, path safety, credential scoping, agent view security
- Run 2 (2026-06-07): Deep-read evidence update — expanded CaMeL/Progent/AgentDojo citations with benchmark numbers; added LlamaFirewall, Llama Guard, NeMo Guardrails, ACI-SENTINEL, A-Trust, and misevolution evidence; added Trade-off Analysis with technique comparison table; added Evidence Base section; added layered defense-in-depth design; added adaptive attack risk analysis; references expanded from 7 to 19
