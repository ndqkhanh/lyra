# Plan: Permissions & Credentials (§4.12)

**Workstream**: Permission Model & Credential Management  
**Phase**: 1 (Feature Parity)  
**Impact**: 5/5 | **Effort**: 3/5

## 📋 Quick Reference Card
| What | Programmable, context-aware permission system with zero-trust verification and encrypted credential management |
| Why | Agents with unrestricted tool access are dangerous. Permissions define what agents CAN do; credentials give them secure access to what they NEED |
| Key Tech | Claude Code permissions (allow/deny/ask), Progent SMT-based least-privilege, credential store with encryption-at-rest |
| Timeline | 3 weeks | Dependencies: Tools (§4.6), Hooks (§4.10) |

## 🎯 Executive Summary

Every tool an AI agent can use is a potential attack vector. The permission system acts as a gate: before any tool call executes, it checks: "Is this agent allowed to do this? In this context? At this time? With these parameters?"

Lyra's permission model goes beyond simple allow/deny. It supports **context-aware policies**: "Allow file writes, but only within the project directory." **Temporal policies**: "Allow database access, but only during business hours." **Capability-based policies**: "Agent X has the 'deploy' capability — no other agent does."

Credentials (API keys, tokens, passwords) are stored encrypted-at-rest, injected at runtime, and NEVER appear in agent context or logs. Providers are configured once and used everywhere.

The breakthrough: **Progent-style SMT verification** — tool-call policies are formal mathematical statements, not regex patterns. "This agent can write to files matching /project/output/* but NOT /project/secrets/*" is a provable guarantee, not a best-effort filter.

---

## Concrete Example Walkthrough: New Team Member Onboarding to Production Deploy

This walkthrough traces a new team member's journey from zero configuration to a blocked production deployment, illustrating how the permission model, credential management, and policy engine work together across two points in time.

### Actors and Components

| Actor / Component | Role in this Walkthrough |
|---|---|
| **Alex** | New junior engineer, just joined the team |
| **Lyra CLI** (`lyra`) | The harness orchestrator |
| **PermissionManager** | Evaluates allow/deny/confirm rules before every tool call (see Section 3, `checkPermission`) |
| **PolicyEngine** | Evaluates programmable `Policy` objects; bridges context and least-privilege rules |
| **CredentialManager** | Encrypts, stores, retrieves, and refreshes credentials (see Section 3, `CredentialManager` class) |
| **CredentialStore** | Encrypted-at-rest backend (`~/.lyra/credentials.enc`) |
| **ConfirmationUI** | Interactive prompts when a rule has `requireConfirmation` or no explicit match |
| **AuditLogger** | Records every permission decision, credential access, and tool execution |
| **Escalation Mechanism** | Sends a request to senior engineers when a permission check fails with an action requiring elevated role |

---

### Step 1: First Launch -- `lyra --setup`

**Trigger**: Alex clones the team repository and types `lyra --setup` in the terminal.

**What Lyra does**:

1. Lyra detects no credentials file at `~/.lyra/credentials.enc` (the `CredentialStore` reports empty).
2. `CredentialManager` initiates an **interactive setup flow** via `ConfirmationUI`.
3. The UI renders the first prompt.

**What Alex sees**:

```
$ lyra --setup

🔐 Lyra Setup — Credential Configuration

No credentials found. Let's set up your AI providers.

Which AI providers will you use?
  [1] Claude (Anthropic)
  [2] DeepSeek
  [3] GPT (OpenAI)
  [4] All of the above

Enter numbers (comma-separated) [4]: 2
```

**What Lyra does**: Alex selects DeepSeek. `CredentialManager.set()` is called with `type: 'api-key'` and `storage: 'file'`. The key is encrypted using AES-256-GCM before being written to disk. The entry in `CredentialStore` looks like:

```typescript
// Internal representation (never written in plaintext)
{
  id: "deepseek-default",
  name: "DeepSeek API Key",
  type: "api-key",
  storage: "file",          // stored in ~/.lyra/credentials.enc
  environment: "*",          // available across all environments
  createdAt: 1717200000000,
  updatedAt: 1717200000000
}
```

**What Alex sees**:

```
DeepSeek — enter your API key: ****************************************
✅ DeepSeek API key encrypted and stored in ~/.lyra/credentials.enc

Setup complete! You're ready to use Lyra.
Type 'lyra --help' to see available commands.
```

**How this is better**: Before this system, Alex would manually edit a `.env` file, potentially committing it. With `CredentialManager`, the key is encrypted-at-rest, injected at runtime only, and **never appears in agent context or logs** (per Section 3 design). The `SecretScanner` (Section 3) also actively prevents the file from being committed.

---

### Step 2: First Task -- "Deploy to Staging"

**Trigger**: Alex types `lyra run "Deploy to staging"` one hour after setup.

**What Lyra does** -- the `PermissionManager.checkPermission()` pipeline fires (see Section 3, "Permission Evaluation"):

**Check 1: Does this user have deploy permission?**

```
PermissionManager.checkPermission("Bash", { command: "deploy-staging.sh" })
```

The `PolicyEngine` evaluates the built-in `rbac-deploy` policy:

```typescript
// Built-in policy from Phase 2, Section 4
@policy
function rbacDeployPolicy(tool: string, args: any, context: Context): boolean {
  if (tool === "Bash" && args.command.startsWith("deploy")) {
    const userRole = getUserRole(context.user);   // returns "junior-engineer"
    const targetEnv = extractEnvironment(args);    // returns "staging"
    const allowedRoles = getDeployRoles(targetEnv); // returns ["junior-engineer", "senior-engineer"]

    return allowedRoles.includes(userRole);
  }
  return true; // not a deploy command, other rules apply
}
```

- Alex has `junior-engineer` role.
- Staging deploy allows `junior-engineer`.
- **Result: PASS.**

**Check 2: Is the staging environment in Alex's allowed scope?**

The `Context` object (Section 3 data model) carries `environment: "staging"`. The `scope-policy` evaluates:

```typescript
@policy
function scopePolicy(tool: string, args: any, context: Context): boolean {
  // Junior engineers can only target dev and staging
  const userScope = getUserScope(context.user); // ["dev", "staging"]
  return userScope.includes(context.environment);
}
```

- **Result: PASS.** Staging is in Alex's scope.

**Check 3: Are AWS credentials available at the required clearance level?**

`CredentialManager.get("aws", "staging")` is called. The `CredentialStore` retrieves the encrypted credential, decrypts it in-memory, checks it is not expired, and returns it. The credential carries metadata:

```typescript
{
  id: "aws-staging",
  type: "access-key",
  environment: "staging",
  scope: ["deploy", "read-logs", "read-metrics"],
  clearanceLevel: "standard"   // staging uses standard clearance
}
```

The deploy command requires `scope: ["deploy"]` and `clearanceLevel: "standard"`. Both match.

**Result: ALL CHECKS PASS.**

`AuditLogger` records:

```
[2026-05-31 10:23:45] ALLOW Bash:deploy-staging.sh | user=alex | role=junior-engineer | env=staging | policy=rbac-deploy,scope-policy | cred=aws-staging
```

**What Alex sees**:

```
$ lyra run "Deploy to staging"

🔍 Checking permissions...
  ✅ Deploy permission (role: junior-engineer → staging: allowed)
  ✅ Environment scope (staging: in ["dev", "staging"])
  ✅ AWS credentials (staging, clearance: standard, scope: deploy)

🚀 Deploying to staging...
   Building artifacts... done
   Uploading to S3... done
   Updating ECS service... done

✅ Deploy to staging complete (2m 34s)
```

**How this is better**: Before this system, Alex could accidentally deploy to any environment with no guardrails. The `PermissionManager` + `PolicyEngine` combination means every tool call is checked against role, scope, and credential clearance **before execution** -- not after the fact. The `AuditLogger` creates a tamper-evident record.

---

### Step 3: One Week Later -- "Deploy to Production" (Blocked)

**Trigger**: Alex gains confidence and types `lyra run "Deploy to production"`.

**What Lyra does** -- the same `checkPermission` pipeline fires:

**Check 1: Does this user have deploy permission?**

The `rbacDeployPolicy` fires again:

```typescript
getUserRole("alex")           // → "junior-engineer"
getDeployRoles("production")  // → ["senior-engineer"] ← STAGING allows junior, PROD does NOT
allowedRoles.includes("junior-engineer") // → false
```

**Result: DENIED.** `PermissionManager` returns `{ allowed: false, reason: "Policy 'rbac-deploy' denied: production deploy requires senior-engineer role" }`.

**What Lyra does next**: The `ConfirmationUI` does NOT prompt Alex (there is no "ask" path for a hard policy denial -- the policy says "deny," so it is denied). Instead, the **Escalation Mechanism** triggers:

1. A structured escalation request is created with the `AuditLogger` record, Alex's identity, the denied operation, and the required role.
2. The request is sent to the `#deploy-approvals` Slack channel and/or creates a ticket.

**What Alex sees**:

```
$ lyra run "Deploy to production"

🔍 Checking permissions...
  ❌ Deploy permission (role: junior-engineer → production: DENIED)

⛔ Permission denied: Production deployment requires role "senior-engineer"

Your escalation request has been sent to the senior engineering team.
Reference: ESC-2026-05-31-0042
Estimated response time: < 2 hours during business hours

💡 Tip: Ask your team lead to grant temporary deploy capability with:
   lyra permission grant --user alex --capability deploy:production --ttl 4h
```

**What the senior engineer sees** (Slack / ticket):

```
🔺 Escalation: Production Deploy Request
   From: Alex (junior-engineer)
   Action: Bash:deploy-production.sh
   When: 2026-05-31 14:52:10
   Reference: ESC-2026-05-31-0042

   Approve: lyra escalate approve ESC-2026-05-31-0042
   Deny:    lyra escalate deny ESC-2026-05-31-0042
   Grant temp capability: lyra permission grant --user alex --capability deploy:production --ttl 4h
```

**How this is better**: Before this system, Alex would either (a) have unrestricted access and potentially break production, or (b) be fully locked out and unable to do any deploy, with no clear path to unblock. The `PolicyEngine` + `Escalation Mechanism` combination provides a **structured, auditable path to elevated access**. The `Capability tokens` from Progent-style design (Section 2) mean a senior engineer can grant a time-limited, single-use token rather than permanently changing Alex's role.

---

### What Each Component Did

| Component | Step 1 (Setup) | Step 2 (Staging Deploy) | Step 3 (Production Deploy) |
|---|---|---|---|
| **CredentialManager** | Interactive setup, encrypted storage | Retrieved AWS creds, validated scope + clearance | Not reached (blocked earlier) |
| **PermissionManager** | N/A (setup is privileged) | Evaluated 3 rules, returned ALLOW | Evaluated 1 rule, returned DENY |
| **PolicyEngine** | N/A | Evaluated `rbac-deploy`, `scope-policy` | Evaluated `rbac-deploy` -- failed |
| **ConfirmationUI** | Rendered provider selection prompt | Not triggered (rules matched ALLOW) | Not triggered (hard DENY, no ask path) |
| **AuditLogger** | Recorded credential setup event | Recorded ALLOW decision + tool execution | Recorded DENY decision + escalation creation |
| **Escalation Mechanism** | N/A | N/A | Created ESC ticket, notified senior engineers |
| **SecretScanner** | Verified key written to encrypted store only | Scanned deploy output for leaked secrets | N/A |

---

## 1. Problem

Lyra needs a robust permission and credential system to:
- **Control tool access** — Allow/deny tools per project/user
- **Manage secrets** — Store API keys, tokens, passwords securely
- **Audit actions** — Track what tools were used and when
- **Prevent accidents** — Confirm destructive operations
- **Multi-environment** — Different credentials per environment (dev/staging/prod)

Without this, users risk accidental destructive actions and insecure credential storage.

---

## 2. Evidence Synthesis

### Claude Code Permissions
**Source**: https://code.claude.com/docs/en/permissions

**Permission modes** (3 levels):
1. **Ask** (default) — Prompt for each tool use
2. **Allow** — Auto-approve specific tools
3. **Deny** — Block specific tools

**Permission scopes**:
- **Global** — All projects (`~/.claude/settings.json`)
- **Project** — Current project (`.claude/settings.json`)
- **Session** — Current session only (in-memory)

**Permission format**:
```json
{
  "permissions": {
    "allowedTools": [
      "Read",
      "Write:src/**",
      "Bash:npm test",
      "Bash:git status"
    ],
    "deniedTools": [
      "Bash:rm -rf",
      "Write:.env"
    ],
    "requireConfirmation": [
      "Bash:git push",
      "Write:package.json"
    ]
  }
}
```

**Pattern matching**:
- **Exact match** — `Read` (tool name only)
- **Path pattern** — `Write:src/**/*.ts` (tool + glob)
- **Command pattern** — `Bash:npm test` (tool + command prefix)
- **Regex** — `Bash:/^git (push|pull)/` (tool + regex)

**Confirmation prompts**:
```
⚠️  Lyra wants to run: git push origin main
   This will push 5 commits to remote
   
   [A]llow once  [D]eny  [Always allow]  [Never allow]
```

### Claude Code Env Vars & Credentials
**Source**: https://code.claude.com/docs/en/env-vars

**Credential storage**:
- **Environment variables** — `~/.claude/settings.json` → `env` field
- **Credential files** — `~/.claude/credentials/` (encrypted)
- **System keychain** — macOS Keychain, Windows Credential Manager, Linux Secret Service

**Credential types**:
1. **API keys** — OpenAI, Anthropic, GitHub, etc.
2. **OAuth tokens** — Google, Microsoft, Slack, etc.
3. **Database credentials** — PostgreSQL, MongoDB, Redis, etc.
4. **SSH keys** — Git, servers, etc.

**Credential format**:
```json
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-ant-...",
    "OPENAI_API_KEY": "sk-...",
    "GITHUB_TOKEN": "ghp_...",
    "DATABASE_URL": "postgresql://user:pass@host:5432/db"
  },
  "credentials": {
    "github": {
      "type": "oauth2",
      "accessToken": "gho_...",
      "refreshToken": "ghr_...",
      "expiresAt": 1735689600
    },
    "aws": {
      "type": "access-key",
      "accessKeyId": "AKIA...",
      "secretAccessKey": "..."
    }
  }
}
```

**Credential helpers**:
- **Dynamic credentials** — Script to fetch credentials on-demand
- **Credential rotation** — Auto-refresh OAuth tokens
- **Credential validation** — Test credentials before use

### Claude Code Security
**Source**: https://code.claude.com/docs/en/security

**Security features**:
1. **Sandboxing** — Isolate tool execution (Docker, VM, chroot)
2. **Audit logging** — Log all tool executions
3. **Secret scanning** — Detect secrets in code
4. **Rate limiting** — Prevent abuse
5. **Network isolation** — Block network access for sensitive tools

**Sandbox environments**:
- **Docker** — Run tools in containers
- **Firecracker** — Lightweight VMs
- **gVisor** — Sandboxed Linux runtime
- **WebAssembly** — Sandboxed code execution

### Progent Least-Privilege Tool Control
**Source**: https://github.com/sunblaze-ucb/progent  
**Paper**: https://arxiv.org/abs/2504.11703

**Key insight**: Programmable tool-call control with least privilege
- Define **policies** for tool access (who, what, when, where)
- **Capability-based** — Grant minimal permissions needed
- **Temporal** — Permissions expire after time/use
- **Contextual** — Permissions depend on state (e.g., "allow Write only after tests pass")

**Example policy**:
```python
# Allow Write to src/ only after tests pass
@policy
def write_after_tests(tool: str, args: dict) -> bool:
    if tool == "Write" and args["file_path"].startswith("src/"):
        return test_status() == "passed"
    return True
```

**Progent architecture**:
1. **Policy engine** — Evaluate policies before tool execution
2. **Capability tokens** — Time-limited, single-use permissions
3. **Audit log** — Record all policy decisions

---

## 3. Proposed Lyra Design

### Architecture

```mermaid
graph TB
    subgraph "Permission System"
        PermissionManager[Permission Manager]
        PolicyEngine[Policy Engine]
        ConfirmationUI[Confirmation UI]
        AuditLogger[Audit Logger]
    end
    
    subgraph "Credential System"
        CredentialManager[Credential Manager]
        CredentialStore[Credential Store]
        CredentialHelper[Credential Helper]
        TokenRefresher[Token Refresher]
    end
    
    subgraph "Security"
        SecretScanner[Secret Scanner]
        Sandbox[Sandbox Manager]
        RateLimiter[Rate Limiter]
        NetworkIsolation[Network Isolation]
    end
    
    subgraph "Storage"
        ConfigFiles[Config Files<br/>settings.json]
        EncryptedStore[Encrypted Store<br/>credentials/]
        SystemKeychain[System Keychain<br/>OS-native]
    end
    
    ToolExecutor[Tool Executor] --> PermissionManager
    PermissionManager --> PolicyEngine
    PolicyEngine --> ConfirmationUI
    PermissionManager --> AuditLogger
    
    ToolExecutor --> CredentialManager
    CredentialManager --> CredentialStore
    CredentialManager --> CredentialHelper
    CredentialManager --> TokenRefresher
    
    CredentialStore --> ConfigFiles
    CredentialStore --> EncryptedStore
    CredentialStore --> SystemKeychain
    
    ToolExecutor --> SecretScanner
    ToolExecutor --> Sandbox
    ToolExecutor --> RateLimiter
    ToolExecutor --> NetworkIsolation
```

### Permission Data Model

```typescript
interface PermissionConfig {
  // Allowed tools (auto-approve)
  allowedTools: PermissionRule[];
  
  // Denied tools (auto-deny)
  deniedTools: PermissionRule[];
  
  // Require confirmation
  requireConfirmation: PermissionRule[];
  
  // Policies (programmable)
  policies: Policy[];
  
  // Audit
  auditLog: boolean;
  auditPath?: string;
}

interface PermissionRule {
  tool: string; // Tool name or pattern
  pattern?: string; // Glob or regex for args
  scope?: 'global' | 'project' | 'session';
  expiresAt?: number; // Timestamp
  maxUses?: number; // Use limit
}

interface Policy {
  name: string;
  description: string;
  evaluate: (tool: string, args: any, context: Context) => boolean | Promise<boolean>;
}

interface Context {
  workingDirectory: string;
  session: Session;
  user: string;
  environment: string; // dev, staging, prod
  state: any; // Custom state
}
```

### Permission Evaluation

```typescript
async function checkPermission(tool: string, args: any): Promise<PermissionDecision> {
  const context = getCurrentContext();
  
  // 1. Check denied tools (highest priority)
  if (matchesRule(tool, args, config.deniedTools)) {
    return { allowed: false, reason: 'Tool is denied' };
  }
  
  // 2. Check allowed tools
  if (matchesRule(tool, args, config.allowedTools)) {
    return { allowed: true, reason: 'Tool is allowed' };
  }
  
  // 3. Evaluate policies
  for (const policy of config.policies) {
    const result = await policy.evaluate(tool, args, context);
    if (!result) {
      return { allowed: false, reason: `Policy '${policy.name}' denied` };
    }
  }
  
  // 4. Check confirmation rules
  if (matchesRule(tool, args, config.requireConfirmation)) {
    const confirmed = await promptConfirmation(tool, args);
    return { allowed: confirmed, reason: confirmed ? 'User confirmed' : 'User denied' };
  }
  
  // 5. Default: ask user
  const confirmed = await promptConfirmation(tool, args);
  return { allowed: confirmed, reason: confirmed ? 'User confirmed' : 'User denied' };
}

function matchesRule(tool: string, args: any, rules: PermissionRule[]): boolean {
  for (const rule of rules) {
    // Check tool name
    if (rule.tool !== '*' && rule.tool !== tool) continue;
    
    // Check pattern
    if (rule.pattern) {
      const argString = JSON.stringify(args);
      if (rule.pattern.startsWith('/')) {
        // Regex
        const regex = new RegExp(rule.pattern.slice(1, -1));
        if (!regex.test(argString)) continue;
      } else {
        // Glob
        if (!minimatch(argString, rule.pattern)) continue;
      }
    }
    
    // Check expiration
    if (rule.expiresAt && Date.now() > rule.expiresAt) continue;
    
    // Check use limit
    if (rule.maxUses !== undefined) {
      const uses = getUseCount(rule);
      if (uses >= rule.maxUses) continue;
    }
    
    return true;
  }
  
  return false;
}
```

### Confirmation UI

```typescript
async function promptConfirmation(tool: string, args: any): Promise<boolean> {
  // Format tool call
  const description = formatToolCall(tool, args);
  
  // Show prompt
  console.log(`\n⚠️  Lyra wants to ${description}`);
  
  // Show impact
  const impact = analyzeImpact(tool, args);
  if (impact.destructive) {
    console.log(`   ⚠️  This is a destructive operation`);
  }
  if (impact.affectedFiles.length > 0) {
    console.log(`   Affected files: ${impact.affectedFiles.join(', ')}`);
  }
  
  // Prompt user
  const answer = await readline.question('\n   [A]llow once  [D]eny  [Always allow]  [Never allow]: ');
  
  switch (answer.toLowerCase()) {
    case 'a':
      return true;
    case 'd':
      return false;
    case 'always allow':
      addPermissionRule(tool, args, 'allowed');
      return true;
    case 'never allow':
      addPermissionRule(tool, args, 'denied');
      return false;
    default:
      return false;
  }
}
```

### Credential Management

```typescript
interface Credential {
  id: string;
  name: string;
  type: 'api-key' | 'oauth2' | 'username-password' | 'ssh-key' | 'certificate';
  
  // Storage
  storage: 'env' | 'file' | 'keychain';
  
  // OAuth2
  oauth2?: {
    accessToken: string;
    refreshToken?: string;
    expiresAt?: number;
    tokenUrl?: string;
  };
  
  // API Key
  apiKey?: string;
  
  // Username/Password
  username?: string;
  password?: string;
  
  // SSH Key
  privateKey?: string;
  publicKey?: string;
  passphrase?: string;
  
  // Metadata
  environment?: string; // dev, staging, prod
  scope?: string[]; // Permissions
  createdAt: number;
  updatedAt: number;
}

class CredentialManager {
  async get(name: string, environment?: string): Promise<Credential | null> {
    // 1. Check environment-specific credential
    if (environment) {
      const envCred = await this.store.get(`${name}:${environment}`);
      if (envCred) return envCred;
    }
    
    // 2. Check default credential
    const cred = await this.store.get(name);
    if (!cred) return null;
    
    // 3. Refresh if needed
    if (cred.type === 'oauth2' && this.isExpired(cred)) {
      await this.refresh(cred);
    }
    
    return cred;
  }
  
  async set(name: string, credential: Credential): Promise<void> {
    // Validate
    this.validate(credential);
    
    // Encrypt sensitive fields
    const encrypted = await this.encrypt(credential);
    
    // Store
    await this.store.set(name, encrypted);
  }
  
  async refresh(credential: Credential): Promise<void> {
    if (credential.type !== 'oauth2') return;
    if (!credential.oauth2?.refreshToken) return;
    
    // Refresh token
    const response = await fetch(credential.oauth2.tokenUrl!, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: credential.oauth2.refreshToken
      })
    });
    
    const data = await response.json();
    
    // Update credential
    credential.oauth2.accessToken = data.access_token;
    credential.oauth2.expiresAt = Date.now() + data.expires_in * 1000;
    credential.updatedAt = Date.now();
    
    // Save
    await this.set(credential.id, credential);
  }
  
  private isExpired(credential: Credential): boolean {
    if (credential.type !== 'oauth2') return false;
    if (!credential.oauth2?.expiresAt) return false;
    return Date.now() > credential.oauth2.expiresAt - 60000; // 1 min buffer
  }
}
```

### Secret Scanning

```typescript
interface SecretPattern {
  name: string;
  pattern: RegExp;
  severity: 'critical' | 'high' | 'medium' | 'low';
}

const SECRET_PATTERNS: SecretPattern[] = [
  {
    name: 'Anthropic API Key',
    pattern: /sk-ant-[a-zA-Z0-9-_]{95}/,
    severity: 'critical'
  },
  {
    name: 'OpenAI API Key',
    pattern: /sk-[a-zA-Z0-9]{48}/,
    severity: 'critical'
  },
  {
    name: 'GitHub Token',
    pattern: /gh[pousr]_[a-zA-Z0-9]{36}/,
    severity: 'critical'
  },
  {
    name: 'AWS Access Key',
    pattern: /AKIA[0-9A-Z]{16}/,
    severity: 'critical'
  },
  {
    name: 'Private Key',
    pattern: /-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----/,
    severity: 'high'
  },
  {
    name: 'Generic API Key',
    pattern: /api[_-]?key[_-]?=?['\"]?[a-zA-Z0-9]{32,}/i,
    severity: 'medium'
  }
];

async function scanForSecrets(content: string): Promise<SecretMatch[]> {
  const matches: SecretMatch[] = [];
  
  for (const pattern of SECRET_PATTERNS) {
    const regex = new RegExp(pattern.pattern, 'g');
    let match;
    
    while ((match = regex.exec(content)) !== null) {
      matches.push({
        name: pattern.name,
        severity: pattern.severity,
        value: match[0],
        position: match.index,
        line: content.substring(0, match.index).split('\n').length
      });
    }
  }
  
  return matches;
}

async function preventSecretCommit(filePath: string, content: string): Promise<void> {
  const secrets = await scanForSecrets(content);
  
  if (secrets.length > 0) {
    console.error(`\n⚠️  Detected ${secrets.length} potential secret(s) in ${filePath}:`);
    
    for (const secret of secrets) {
      console.error(`   Line ${secret.line}: ${secret.name} (${secret.severity})`);
    }
    
    const confirmed = await confirm({
      message: 'Continue anyway?',
      default: false,
      destructive: true
    });
    
    if (!confirmed) {
      throw new Error('Aborted due to detected secrets');
    }
  }
}
```

---

## 4. Implementation Outline

### Phase 1: Permission System (Week 1)

**Tasks**:
1. **Permission data model** — Define interfaces
2. **Permission evaluation** — Check allowed/denied/confirm
3. **Pattern matching** — Glob and regex support
4. **Confirmation UI** — Interactive prompts

**Acceptance criteria**:
- Permissions evaluate correctly
- Patterns match correctly
- UI is clear and intuitive

### Phase 2: Policies (Week 1-2)

**Tasks**:
5. **Policy engine** — Evaluate programmable policies
6. **Built-in policies** — Common policies (e.g., "write after tests")
7. **Custom policies** — User-defined policies
8. **Policy testing** — Dry-run mode

**Acceptance criteria**:
- Policies evaluate correctly
- Built-in policies work
- Custom policies are easy to write

### Phase 3: Credential Management (Week 2)

**Tasks**:
9. **Credential data model** — Define interfaces
10. **Credential storage** — Encrypted file + keychain
11. **OAuth2 flow** — Token refresh
12. **Credential helpers** — Dynamic credentials

**Acceptance criteria**:
- Credentials store securely
- OAuth tokens refresh automatically
- Helpers fetch credentials on-demand

### Phase 4: Secret Scanning (Week 2-3)

**Tasks**:
13. **Secret patterns** — Define regex patterns
14. **Scan on write** — Detect secrets before write
15. **Scan on commit** — Detect secrets before commit
16. **Secret redaction** — Redact secrets in logs

**Acceptance criteria**:
- Secrets detected accurately
- False positives are low
- Redaction works correctly

### Phase 5: Audit Logging (Week 3)

**Tasks**:
17. **Audit log format** — Define log structure
18. **Log all tool uses** — Record tool + args + result
19. **Log permission decisions** — Record allow/deny
20. **Log viewer** — Browse audit logs

**Acceptance criteria**:
- All actions logged
- Logs are searchable
- Viewer is intuitive

### Phase 6: Sandboxing (Week 3)

**Tasks**:
21. **Sandbox manager** — Abstract sandbox interface
22. **Docker sandbox** — Run tools in containers
23. **Network isolation** — Block network access
24. **Resource limits** — CPU, memory, disk limits

**Acceptance criteria**:
- Sandboxes isolate correctly
- Network isolation works
- Resource limits enforce

---

## 5. Multi-Provider Notes

Permissions and credentials are **provider-agnostic** at the harness level.

**Provider-specific credentials**:
- Each provider has its own API key
- Stored separately in credential manager
- Auto-selected based on active provider

---

## 6. Risks & Open Questions

### Risks

1. **Credential leakage** — Credentials may leak in logs/errors
   - **Mitigation**: Redact secrets, encrypt logs

2. **Permission bypass** — Users may bypass permissions
   - **Mitigation**: Enforce at harness level, not prompt level

3. **Sandbox escape** — Tools may escape sandbox
   - **Mitigation**: Use battle-tested sandboxes (Docker, gVisor)

### Open Questions

1. **Credential sharing** — Share credentials with team?
   - **Recommendation**: Yes, with encryption + access control

2. **Permission inheritance** — Inherit permissions from parent?
   - **Recommendation**: Yes, with override capability

3. **Audit retention** — How long to keep audit logs?
   - **Recommendation**: 90 days default, configurable

---

## 7. Impact × Effort Assessment

### (A) Parity Tier

**Port from Claude Code + Progent**:
- Allow/deny/confirm permissions
- Pattern matching (glob, regex)
- Credential storage (encrypted + keychain)
- OAuth2 token refresh
- Secret scanning
- Audit logging

**Impact**: 5/5 — Critical for security  
**Effort**: 3/5 — 3 weeks, moderate complexity

### (B) Breakthrough Tier

> **Architecture Slice**: This breakthrough implements [§5: AVP Middleware](../BREAKTHROUGH-ARCHITECTURE.md) and [§4.2 Safety Gates](../BREAKTHROUGH-ARCHITECTURE.md) of [BREAKTHROUGH-ARCHITECTURE.md](../BREAKTHROUGH-ARCHITECTURE.md) — specifically the AVP-aware permission system with graduated trust levels.

**Beyond any single source**:

1. **Programmable Policies** — Progent-style least-privilege control
   - Contextual permissions (e.g., "allow Write after tests pass")
   - Temporal permissions (expire after time/use)
   - Capability tokens (single-use permissions)
   - No other harness has this

2. **Credential Marketplace** — Pre-configured credential templates
   - One-click setup for common services (GitHub, AWS, Stripe)
   - OAuth flow automation
   - Credential validation

3. **Permission Analytics** — Insights from permission usage
   - Most-used tools
   - Most-denied tools
   - Permission optimization recommendations

**Impact**: 5/5 — Best-in-class security  
**Effort**: 4/5 — 2 weeks additional

**Combined Impact × Effort**: 5 × 3 = 15 (parity), 5 × 4 = 20 (breakthrough)

---

## 8. References

### Documentation
- [Claude Code Permissions](https://code.claude.com/docs/en/permissions)
- [Claude Code Env Vars](https://code.claude.com/docs/en/env-vars)
- [Claude Code Security](https://code.claude.com/docs/en/security)

### Papers
- [Progent](https://arxiv.org/abs/2504.11703) — Least-privilege tool control

### Repositories
- [Progent](https://github.com/sunblaze-ucb/progent)

---

## 9. Changelog

**2026-05-31 — Run 3**: Linked to unified BREAKTHROUGH-ARCHITECTURE.md. This plan's (B) tier implements §5: AVP Middleware + §4.2 Safety Gates of the architecture.

**Run 13**: Added concrete step-by-step walkthrough example

---

**END OF PLAN: Permissions & Credentials (§4.12)**
