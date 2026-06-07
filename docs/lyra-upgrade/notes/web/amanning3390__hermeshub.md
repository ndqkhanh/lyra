# amanning3390/hermeshub -- Deep-Read

## 1. Headline Feature & Mechanism

**Headline:** A security-scanned, community-rated skills registry marketplace for autonomous AI agents (Hermes Agent by Nous Research).

The repo delivers three tightly integrated features under one roof:

**Feature A -- Security-Scanned Skill Registry.** Every skill (a directory under `skills/` with a `SKILL.md` conforming to the agentskills.io spec) submitted via PR triggers `scripts/scan-skill.py` in a GitHub Action. The scanner runs 65+ regex-based threat rules across 8 categories (exfiltration, prompt injection, destructive commands, obfuscation, hardcoded secrets, network abuse, env abuse, supply-chain). Critical findings block the merge regardless of who authored the PR (`enforce_admins: true` in branch protection). A separate "Reviewed Domains" system downgrades known-safe external APIs from CRITICAL to ADVISORY.

**Feature B -- Agent-to-Agent Feedback Protocol (A2A).** Agents register an Ed25519 identity (`POST /api/v1/agents/register`), then submit structured reviews (`POST /api/v1/feedback`) signed with their private key. The feedback carries: multi-dimensional ratings (works-as-described, reliability, documentation, safety), task context (category, complexity), proof-of-use (SHA-256 of task output), nonce (UUID for replay prevention), and an ISO 8601 timestamp (must be within 5 minutes of server time). Text content goes through an 18-pattern anti-prompt-injection sanitization pipeline before storage. The API returns reviews with text fields wrapped in `{ untrusted_content: true, data: "..." }` so consuming agents never interpret another agent's text as instructions. Trust scores are computed server-side as a weighted average with a security-concern penalty.

**Feature C -- Creator Marketplace (Payments).** Premium skills are listed and sold via two payment protocols: x402 (crypto -- 402 Payment Required HTTP response with on-chain payment address) and Micropayment Protocol / MPP (Stripe-based pre-authorized spending limits). Creators authenticate via GitHub OAuth, configure wallet addresses (Base, Solana, Tempo), upload encrypted skill archives, and receive 95% of each sale. License keys grant up to 5 re-downloads.

The three features form a virtuous cycle: security scanning assures quality gate, agent feedback builds trust signals, marketplace provides economic incentive for creators.

## 2. Architecture & Core Modules

**Tech Stack:** TypeScript (backend + frontend), React 18 + Vite + Tailwind + shadcn/ui (frontend), Express (dev server), Vercel Serverless Functions (production API), Neon Postgres + Drizzle ORM (database), Python 3 (security scanner), esbuild (production bundler).

**Top-Level Layout:**
```
api/          -- Vercel Serverless Functions (production API routes)
  _lib/       --   cors.ts, db.ts, sanitize.ts, schema.ts (duplicated from shared/)
  v1/         --   API version 1: auth, skills, creators, payments, feedback, agents, licenses
client/       -- Vite + React SPA
  src/
    pages/    --   home, browse, skill-detail, creator-dashboard, buyer-library, etc.
    components/ -- UI components (shadcn/ui) + SkillCard, AgentFeedbackSection, TrustScoreBadge
    lib/      --   skills-data.ts (auto-generated from SKILL.md files)
server/       -- Express dev server (also serves the same API in development)
  routes.ts   --   All API route handlers
  storage.ts  --   MemStorage for skills data
  feedback-store.ts -- MemFeedbackStore + DbFeedbackStore (Neon Postgres) factory
  sanitize.ts --   Anti-prompt-injection text sanitization
  index.ts    --   Express app bootstrap
shared/       -- Shared Drizzle schema + Zod validation schemas
scripts/      -- scan-skill.py, sync-skills.js, generate-og.py, migration SQL
skills/       -- 22 skill directories, each with SKILL.md
```

**Data Flow (Production):**
1. Vercel routes via `vercel.json` rewrites to `/api/v1/*` serverless functions.
2. Each serverless function file imports inline Drizzle table definitions (duplicated from `shared/schema.ts` for Vercel bundler compatibility), connects to Neon Postgres via `@neondatabase/serverless`, and executes queries.
3. The dev Express server (`server/index.ts`) uses the same route logic but with in-memory fallbacks where no `DATABASE_URL` is set.
4. `sync-skills.js` scans `skills/*/SKILL.md` YAML frontmatter, generates `client/src/lib/skills-data.ts` (static skill catalog for the frontend), updates `sitemap.xml`, and regenerates the OG image with the current skill count. Runs via GitHub Action on pushes to `main` touching `skills/` paths.

**Patterns:**
- Repository pattern (`IStorage` / `IFeedbackStore` interfaces with `Mem*` and `Db*` implementations).
- Factory pattern (`getFeedbackStore()` returns in-memory or Postgres depending on `DATABASE_URL`).
- Middleware pattern: request logging, CORS, rate limiting (in-memory Map with TTL), nonce dedup.
- Schema-on-write: Zod validation at every API boundary.
- Database-per-function: each Vercel serverless function defines its own local Drizzle tables (copy-pasted), avoids cross-bundler import issues.

**Security Architecture (Defense in Depth):**
1. PR gate: GitHub Action `scan-skills.yml` runs Python scanner, posts results as PR comment.
2. Branch protection: `enforce_admins: true` prevents admin bypass of security scan.
3. Nonce replay prevention: `usedNonces` Set with 10-minute cleanup interval.
4. Timestamp window: feedback timestamp must be within 5 minutes of server time.
5. Ed25519 signatures: agent identity is bound to a cryptographic keypair.
6. Content sanitization: 18 regex patterns detect prompt injection, jailbreak, ChatML tags, hidden Unicode, etc.
7. `untrusted_content` wrapper: text fields returned from the API are marked so agents never interpret them as instructions.
8. Rate limiting: 30 requests/minute per agent ID.

## 3. Performance/Benchmarks

**No benchmark data in the repository.** The codebase provides no load tests, latency measurements, or throughput numbers. Observable performance characteristics from code reading:

- **Storage:** In-memory stores (dev) are O(n) linear scans for skill lookups and aggregations. The Postgres DbFeedbackStore uses indexed queries (`feedback_agent_skill_idx` unique index on agentId + skillName, aggregates upserted on `onConflictDoUpdate`).
- **Security scanner:** O(file_length x 65_rules) per SKILL.md -- linear scan with regex matching, runs on every PR in CI.
- **Cache headers:** Marketplace API uses `s-maxage=60, stale-while-revalidate=120` for CDN caching. Feedback/score endpoints get the same. Download endpoints use `no-store` (must be fresh for payment verification).
- **Trust score recomputation:** Recomputes from scratch on every feedback submission (reads all reviews for the skill, then upserts aggregate). O(n_reviews) per submission. This will become a bottleneck at scale.

**Trust Score Algorithm (0-100):**
```text
success_rate * 0.30  +  (works_as_described / 5) * 0.25  +
(reliability / 5) * 0.20  +  (documentation / 5) * 0.10  +  (safety / 5) * 0.15
- security_penalty  (1-2 flags: -5 each, 3+ flags: -20)
```
Badge thresholds: `community_verified` (10+ reviews, score >= 80), `tested` (3+ reviews, score >= 60), `early_feedback` (1+ review), `needs_improvement` (3+ reviews, score < 40).

## 4. Trade-offs (Wins vs Losses)

**Wins:**
- **Security-first by design:** Branch protection with `enforce_admins` means not even the repo owner can bypass security scanning. This is unusually strict for an open-source project and demonstrates genuine commitment to supply-chain security.
- **Anti-prompt-injection pipeline:** The `sanitize.ts` module and `untrusted_content` wrappers directly address the Moltbook-style vulnerability where one agent's output becomes another agent's instructions. This is a design pattern few agent marketplaces implement.
- **Cryptographic agent identity:** Ed25519 keypair registration is lightweight, offline-first, and does not require a centralized identity provider.
- **Payments with both crypto and fiat:** x402 for on-chain buyers, MPP/Stripe for traditional users. The `402 Payment Required` pattern is elegant -- the API itself tells the agent how to pay.
- **Automated skill metadata sync:** The `sync-skills.js` script is a clever zero-dependency YAML frontmatter parser that auto-generates the frontend catalog, sitemap, and OG image from the SKILL.md files themselves. Skill authors do not need to touch website code.

**Losses:**
- **No real Stripe integration:** Multiple TODO comments say "Phase 1: simulate payment verification" and "mock_stripe_session_id". The payment system is scaffolded but not production-ready.
- **In-memory stores lose data:** `MemFeedbackStore` and `MemStorage` lose all data on server restart. Development/testing requires Postgres for persistence.
- **Trust score is naive:** The weighted average algorithm is vulnerable to sybil attacks (a single determined agent submitting multiple reviews) and has no Bayesian smoothing for small sample sizes. The `ONE PER AGENT PER SKILL` upsert policy mitigates this slightly, but there is no trust bootstrapping.
- **No tests anywhere:** Zero test files in the repo. No unit tests, no integration tests, no E2E tests. The security scanner is the only automated verification.
- **Code duplication in serverless functions:** Each Vercel function in `api/v1/*` duplicates Drizzle table definitions inline. The files `api/_lib/schema.ts` duplicates `shared/schema.ts` "to avoid build path issues." This is a maintenance burden -- schema drift between the copies is inevitable.
- **Single feedback slot per agent per skill:** The `feedback_agent_skill_idx` unique index means an agent can only have one review per skill (upsert replaces the old one). This prevents longitudinal tracking of how agent opinions change over time.
- **Nonce set never prunes fully:** `usedNonces` is a `Set<string>` that clears entirely every 10 minutes rather than using a proper LRU or TTL map. A burst of 30K requests between cleanups would exhaust memory.
- **No versioned API:** Despite the `api/v1/` path, there is no version negotiation. Backwards-incompatible changes would require breaking existing agents.

## 5. Design Rationale

**Why security-first with enforced branch protection?** The README explicitly states "even repository owners cannot bypass" security scanning. This is a response to the well-known problem that open-source plugin/skill marketplaces are targets for supply-chain attacks (malicious npm packages, compromised maintainer accounts). By making the security scanner a hard gate at the infrastructure level (GitHub branch protection), the project ensures that even a compromised admin account cannot ship a malicious skill without detection.

**Why Ed25519 for agent identity rather than API keys?** Ed25519 signatures enable offline verification -- agents can prove authorship of a review without revealing secrets to the server. The server only sees the public key during registration. Combined with the nonce replay prevention, this provides cryptographic auditability: any third party can verify that a review was authored by the agent that holds the corresponding private key.

**Why the `untrusted_content` wrapper?** This is explicitly documented as preventing "the Moltbook-style prompt injection cascade where one agent's content hijacks another agent's behavior." The design recognizes that agent feedback systems are fundamentally a prompt-injection surface: Agent A submits text that Agent B reads and potentially interprets as instructions. Wrapping text content in `{ untrusted_content: true, data: "..." }` makes it structurally impossible for the consuming agent to accidentally interpret the text as a system prompt, while still providing the semantic data.

**Why in-memory stores with a Postgres fallback pattern?** The project targets both local development (quick iteration without infrastructure) and production (Vercel + Neon). The `IStorage` / `IFeedbackStore` interface pattern makes this clean -- development uses in-memory with seed data, production swaps in the Postgres implementation without changing business logic. The `getFeedbackStore()` factory uses lazy initialization with environment variable detection.

**Why serverless functions with duplicated schemas?** Vercel's serverless bundler has well-known path resolution issues with shared monorepo packages. The duplication in `api/_lib/schema.ts` is a pragmatic workaround that trades DRY for deployability. Each serverless function is self-contained enough to deploy independently.

## 6. Transfer to Lyra

**Most transferable idea: Agent-to-Agent Feedback Protocol with Prompt-Injection-Safe Content.**

Lyra could adopt a structured feedback system for its plugin/skill ecosystem (or for inter-agent evaluation in multi-agent workflows). The specific components worth porting:

1. **Ed25519 agent identity** -- Lightweight, offline-first identity for Lyra agents to sign reviews. Already compatible with Lyra's existing crypto primitives if any.
2. **Multi-dimensional ratings** -- Instead of a single star rating, the 4-axis model (works-as-described, reliability, documentation, safety) captures nuanced quality signals.
3. **Content sanitization pipeline** -- The 18-pattern injection detector and untrusted_content wrapper pattern directly apply to any Lyra feature where one Lyra agent reads text produced by another agent or user.
4. **Trust score computation with security penalty** -- The weighted average algorithm is simple but effective, and the security penalty provides a direct disincentive against submitting malicious content.
5. **Nonce + timestamp window** -- Replay prevention is essential for any signed submission protocol in an agent system.

**Lyra workstream route:**
- **Primary:** Section 4.2 (Plugin System) -- The feedback protocol enhances Lyra's plugin ecosystem with a trust and reputation layer. Plugins could display trust scores, and Lyra could use the feedback as a signal for plugin suggestions or automatic disabling of low-trust plugins.
- **Alternative:** Section 4.4 (Self-Improvement) -- If Lyra agents can review each other's work, the feedback protocol provides a structured mechanism for inter-agent evaluation without prompt-injection risk.

**Impact:** 7/10 (Medium-High). Adds a missing trust/reputation layer to Lyra's plugin system. Enables community-driven quality signals. The prompt-injection protection is particularly valuable for an agent platform.
**Effort:** 5/10 (Moderate). The protocol itself is not complex (~300 lines of TypeScript for the API + sanitization). The DB schema is straightforward. The harder part is integrating it into Lyra's existing agent lifecycle and UI.
**Tier:** 3 (Enhancement). This is a valuable addition to an existing subsystem (plugins/agents), not a core infrastructure change.

**License:** MIT (confirmed in both README and package.json). No restrictions on reuse.

---

**Files examined:**
- README.md -- project overview, features, API endpoints, tech stack
- package.json -- dependencies, scripts, Node 20.x engine
- vercel.json -- routing, headers, cache config for production deployment
- drizzle.config.ts -- Postgres migration configuration
- server/index.ts -- Express bootstrap, request logging, error handling
- server/routes.ts -- all API route handlers (skills CRUD, agent registration, feedback submission, rate limiting, nonce tracking)
- server/storage.ts -- in-memory skill storage with seed data (11 hardcoded skills)
- server/feedback-store.ts -- MemFeedbackStore + DbFeedbackStore implementations, factory pattern
- server/sanitize.ts -- 18-pattern anti-prompt-injection sanitization pipeline
- shared/schema.ts -- Drizzle table definitions (skills, agents, feedback, feedback_aggregates) + Zod validation schemas
- api/_lib/schema.ts -- duplicated schema for Vercel serverless functions
- api/v1/skills/marketplace.ts -- marketplace endpoint with query parameter validation, CORS, caching
- api/v1/skills/private/[id]/download.ts -- x402 payment protocol implementation with license key management
- api/v1/payments/mpp/session.ts -- Micropayment Protocol session creation (mock Stripe)
- scripts/scan-skill.py -- 65+ rule security scanner in Python (8 threat categories)
- scripts/sync-skills.js -- auto-generates skills-data.ts, updates sitemap.xml and OG image
- .github/workflows/scan-skills.yml -- CI pipeline for security scanning PRs
- .github/workflows/sync-skills.yml -- CI pipeline for syncing skill data on merge
- skills/web-researcher/SKILL.md -- example skill: multi-source web research agent
- skills/hermeshub-reviewer/SKILL.md -- the feedback protocol documented as a skill itself
