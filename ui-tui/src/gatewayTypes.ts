import type { SessionInfo, SlashCategory, SubagentStatus, Usage } from './types.js'

export interface GatewaySkin {
  banner_hero?: string
  banner_logo?: string
  branding?: Record<string, string>
  colors?: Record<string, string>
  help_header?: string
  tool_prefix?: string
}

export interface GatewayCompletionItem {
  display: string
  meta?: string
  text: string
}

export interface GatewayTranscriptMessage {
  context?: string
  name?: string
  role: 'assistant' | 'system' | 'tool' | 'user'
  text?: string
}

// ── Commands / completion ────────────────────────────────────────────

export interface CommandsCatalogResponse {
  canon?: Record<string, string>
  categories?: SlashCategory[]
  pairs?: [string, string][]
  skill_count?: number
  sub?: Record<string, string[]>
  warning?: string
}

export interface CompletionResponse {
  items?: GatewayCompletionItem[]
  replace_from?: number
}

export interface SlashExecResponse {
  output?: string
  warning?: string
}

export type CommandDispatchResponse =
  | { output?: string; type: 'exec' | 'plugin' }
  | { target: string; type: 'alias' }
  | { message?: string; name: string; type: 'skill' }
  | { message: string; notice?: string; type: 'send' }

// ── Config ───────────────────────────────────────────────────────────

export interface ConfigDisplayConfig {
  bell_on_complete?: boolean
  busy_input_mode?: string
  details_mode?: string
  inline_diffs?: boolean
  mouse_tracking?: boolean | null | number | string
  sections?: Record<string, string>
  show_cost?: boolean
  show_reasoning?: boolean
  streaming?: boolean
  thinking_mode?: string
  tui_auto_resume_recent?: boolean
  tui_compact?: boolean
  tui_mouse?: boolean | null | number | string
  tui_status_indicator?: string
  tui_statusbar?: 'bottom' | 'off' | 'on' | 'top' | boolean
}

export interface ConfigVoiceConfig {
  record_key?: unknown
}

export interface ConfigFullResponse {
  config?: { display?: ConfigDisplayConfig; voice?: ConfigVoiceConfig }
}

export interface ConfigMtimeResponse {
  mtime?: number
}

export interface ConfigGetValueResponse {
  display?: string
  home?: string
  value?: string
}

export interface ConfigSetResponse {
  credential_warning?: string
  history_reset?: boolean
  info?: SessionInfo
  value?: string
  warning?: string
}

export interface SetupStatusResponse {
  provider_configured?: boolean
}

// ── Session lifecycle ────────────────────────────────────────────────

export interface SessionCreateResponse {
  info?: SessionInfo & { config_warning?: string; credential_warning?: string }
  session_id: string
}

export interface SessionResumeResponse {
  info?: SessionInfo
  message_count?: number
  messages: GatewayTranscriptMessage[]
  resumed?: string
  session_id: string
}

export interface SessionListItem {
  id: string
  message_count: number
  preview: string
  source?: string
  started_at: number
  title: string
}

export interface SessionListResponse {
  sessions?: SessionListItem[]
}

export interface SessionDeleteResponse {
  deleted: string
}

export interface SessionMostRecentResponse {
  session_id?: null | string
  source?: string
  started_at?: number
  title?: string
}

export interface SessionTitleResponse {
  pending?: boolean
  session_key?: string
  title?: string
}

export interface SessionSaveResponse {
  file?: string
}

export interface SessionUndoResponse {
  removed?: number
}

export interface SessionUsageResponse {
  cache_read?: number
  cache_write?: number
  calls?: number
  compressions?: number
  context_max?: number
  context_percent?: number
  context_used?: number
  cost_status?: 'estimated' | 'exact'
  cost_usd?: number
  input?: number
  model?: string
  output?: number
  total?: number
}

export interface SessionStatusResponse {
  output?: string
}

export interface SessionCompressResponse {
  after_messages?: number
  after_tokens?: number
  before_messages?: number
  before_tokens?: number
  info?: SessionInfo
  messages?: GatewayTranscriptMessage[]
  removed?: number
  summary?: {
    headline?: string
    noop?: boolean
    note?: null | string
    token_line?: string
  }
  usage?: Usage
}

export interface SessionBranchResponse {
  session_id?: string
  title?: string
}

export interface SessionCloseResponse {
  ok?: boolean
}

export interface SessionInterruptResponse {
  ok?: boolean
}

export interface SessionSteerResponse {
  status?: 'queued' | 'rejected'
  text?: string
}

// ── Prompt / submission ──────────────────────────────────────────────

export interface PromptSubmitResponse {
  ok?: boolean
}

export interface BackgroundStartResponse {
  task_id?: string
}

export interface ClarifyRespondResponse {
  ok?: boolean
}

export interface ApprovalRespondResponse {
  ok?: boolean
}

export interface SudoRespondResponse {
  ok?: boolean
}

export interface SecretRespondResponse {
  ok?: boolean
}

// ── Shell / clipboard / input ────────────────────────────────────────

export interface ShellExecResponse {
  code: number
  stderr?: string
  stdout?: string
}

export interface ClipboardPasteResponse {
  attached?: boolean
  count?: number
  height?: number
  message?: string
  token_estimate?: number
  width?: number
}

export interface InputDetectDropResponse {
  height?: number
  is_image?: boolean
  matched?: boolean
  name?: string
  text?: string
  token_estimate?: number
  width?: number
}

export interface TerminalResizeResponse {
  ok?: boolean
}

// ── Image attach ─────────────────────────────────────────────────────

export interface ImageAttachResponse {
  height?: number
  name?: string
  remainder?: string
  token_estimate?: number
  width?: number
}

// ── Voice ────────────────────────────────────────────────────────────

export interface VoiceToggleResponse {
  audio_available?: boolean
  available?: boolean
  details?: string
  enabled?: boolean
  record_key?: string
  stt_available?: boolean
  tts?: boolean
}

export interface VoiceRecordResponse {
  status?: 'busy' | 'recording' | 'stopped'
  text?: string
}

// ── Tools ────────────────────────────────────────────────────────────

export interface ToolsConfigureResponse {
  changed?: string[]
  enabled_toolsets?: string[]
  info?: SessionInfo
  missing_servers?: string[]
  reset?: boolean
  unknown?: string[]
}

// ── Model picker ─────────────────────────────────────────────────────

export interface ModelOptionProvider {
  auth_type?: string
  authenticated?: boolean
  is_current?: boolean
  key_env?: string
  models?: string[]
  name: string
  slug: string
  total_models?: number
  warning?: string
}

export interface ModelOptionsResponse {
  model?: string
  provider?: string
  providers?: ModelOptionProvider[]
}

// ── MCP ──────────────────────────────────────────────────────────────

export interface ReloadMcpResponse {
  status?: string
  message?: string
}

export interface ReloadEnvResponse {
  updated?: number
}

export interface ProcessStopResponse {
  killed?: number
}

export interface BrowserManageResponse {
  connected?: boolean
  messages?: string[]
  url?: string
}

export interface RollbackCheckpoint {
  hash: string
  message?: string
  timestamp?: string
}

export interface RollbackListResponse {
  checkpoints?: RollbackCheckpoint[]
  enabled?: boolean
}

export interface RollbackDiffResponse {
  diff?: string
  rendered?: string
  stat?: string
}

export interface RollbackRestoreResponse {
  error?: string
  history_removed?: number
  message?: string
  reason?: string
  restored_to?: string
  success?: boolean
}

// ── Subagent events ──────────────────────────────────────────────────

export interface SubagentEventPayload {
  api_calls?: number
  cost_usd?: number
  depth?: number
  duration_seconds?: number
  files_read?: string[]
  files_written?: string[]
  goal: string
  input_tokens?: number
  iteration?: number
  model?: string
  output_tail?: { is_error?: boolean; preview?: string; tool?: string }[]
  output_tokens?: number
  parent_id?: null | string
  reasoning_tokens?: number
  status?: SubagentStatus
  subagent_id?: string
  summary?: string
  task_count?: number
  task_index: number
  text?: string
  tool_count?: number
  tool_name?: string
  tool_preview?: string
  toolsets?: string[]
}

// ── Delegation control RPCs ──────────────────────────────────────────

export interface DelegationStatusResponse {
  active?: {
    depth?: number
    goal?: string
    model?: null | string
    parent_id?: null | string
    started_at?: number
    status?: string
    subagent_id?: string
    tool_count?: number
  }[]
  max_concurrent_children?: number
  max_spawn_depth?: number
  paused?: boolean
}

export interface DelegationPauseResponse {
  paused?: boolean
}

export interface SubagentInterruptResponse {
  found?: boolean
  subagent_id?: string
}

// ── Spawn-tree snapshots ─────────────────────────────────────────────

export interface SpawnTreeListEntry {
  count: number
  finished_at?: number
  label?: string
  path: string
  session_id?: string
  started_at?: number | null
}

export interface SpawnTreeListResponse {
  entries?: SpawnTreeListEntry[]
}

export interface SpawnTreeLoadResponse {
  finished_at?: number
  label?: string
  session_id?: string
  started_at?: null | number
  subagents?: unknown[]
}

// ── Safety (Parallax COS) RPCs ────────────────────────────────────────

export interface SafetyStatusResponse {
  action_count: number
  blocked_flows: number
  containment_active: boolean
  escape_signals: number
  governance_tier: string
  quarantine_active: boolean
  self_modify_attempts: number
  tainted_count: number
  trust_score: number
  violation_count: number
}

export interface SafetyReviewResponse {
  decision: string
  governance_tier: string
  layer: string
  trust_score: number
}

export interface SafetyContainmentResponse {
  escape_signals: number
  integrity_violations: number
  quarantine_active: boolean
  self_modify_attempts: number
}

export interface SafetyAuditLogResponse {
  containment_audit: { action: string; result: string; timestamp: string }[]
  review_log: { action: string; decision: string; layer: string }[]
}

// ── Routing (Model Cascade) RPCs ─────────────────────────────────────

export interface RoutingStatusResponse {
  strategy: string
  model_count: number
  decision_count: number
  turn_count: number
  router_snapshot: {
    total_decisions: number
    decisions_by_tier: Record<string, number>
    total_cost: number
    total_tokens: number
    avg_confidence: number
    fallback_rate: number
  }
}

export interface RoutingCostSummaryResponse {
  total_calls: number
  total_cost_usd: number
  by_model: Record<string, {
    calls: number
    cost: number
    avg_latency_ms: number
  }>
}

export interface RoutingSnapshotResponse {
  strategy: string
  router: {
    total_decisions: number
    decisions_by_tier: Record<string, number>
    total_cost: number
    total_tokens: number
    avg_confidence: number
    fallback_rate: number
  }
  costs: RoutingCostSummaryResponse
}

// ── Unified Memory RPCs ─────────────────────────────────────────────

export interface MemoryStatsResponse {
  working_entries: number
  working_tokens: number
  episodic_events: number
  semantic_facts: number
  procedural_count: number
  kg_nodes: number
  kg_edges: number
  token_index_docs: number
  total_memories: number
  active_memories: number
  dormant_memories: number
  last_consolidation: number
  budget_status: string
}

export interface MemoryQueryResult {
  tier: string
  content: string
  score: number
  metadata: Record<string, unknown>
}

export interface MemoryQueryResponse {
  query: string
  results: MemoryQueryResult[]
}

export interface MemoryConsolidateResponse {
  deep: boolean
  actions: string[]
  ultra?: { consolidated: number; pruned: number }
}

export interface MemorySnapshotResponse {
  initialized: boolean
  db_path: string
  queries: number
  writes: number
  stats: MemoryStatsResponse
}

// ── Agent Fleet RPCs ────────────────────────────────────────────────

export interface FleetStatusResponse {
  active_agents: number
  idle_agents: number
  total_agents: number
  pending_tasks: number
  running_tasks: number
  completed_tasks: number
  failed_tasks: number
  squads: number
  throughput: number
  state: string
}

export interface FleetAgent {
  id: string
  role: string
  description: string
  status: string
  tools: string[]
  task_count: number
}

export interface FleetSquad {
  id: string
  name: string
  leader: string
  members: string[]
}

export interface FleetSnapshotResponse {
  fleet: FleetStatusResponse
  agents: Record<string, { role: string; status: string; task_count: number; tools: string[] }>
  squads: Record<string, { leader: string; members: string[]; task_count: number }>
  task_ids: string[]
}

// ── Self-Evolution RPCs ──────────────────────────────────────────────

export interface EvolutionStatusResponse {
  meta_level: string
  trust_score: number
  cycles_completed: number
  total_improvement: number
  current_fitness: number
  mutation_count: number
  active_goals: number
  pending_goals: number
  claims_count: number
  snapshots_available: number
  safe_mode: boolean
}

export interface EvolutionGoal {
  id: string
  description: string
  status: string
}

export interface EvolutionCycle {
  id: string
  improvement: number
  council_decision: string
  duration_ms: number
}

export interface EvolutionSnapshotResponse {
  status: EvolutionStatusResponse
  goals: EvolutionGoal[]
  recent_cycles: EvolutionCycle[]
  claims: { claim: string; evidence: string; status: string }[]
}

export interface EvolutionSetGoalResponse {
  id: string
  description: string
  status: string
}

export interface EvolutionRunCycleResponse {
  id: string
  mutations_applied: number
  improvement: number
  council_decision: string
  duration_ms: number
}

export interface EvolutionAdjustTrustResponse {
  trust_score: number
  level: string
}

// ── Lyra-specific RPCs ───────────────────────────────────────────────

export interface LyraStatsResponse {
  knowledge_graph_nodes?: number
  memories_count?: number
  skills_count?: number
  total_sessions?: number
  uptime_seconds?: number
}

export interface LyraDeepResearchResponse {
  research_id?: string
  status?: string
}

export interface LyraKnowledgeGraphResponse {
  nodes?: number
  query_result?: unknown
}

export interface LyraMemorySearchResponse {
  matches?: { content: string; score: number; id: string }[]
  total?: number
}

export interface LyraSkillInvokeResponse {
  output?: string
  skill_name?: string
}

export type GatewayEvent =
  | { payload?: { skin?: GatewaySkin }; session_id?: string; type: 'gateway.ready' }
  | { payload?: GatewaySkin; session_id?: string; type: 'skin.changed' }
  | { payload: SessionInfo; session_id?: string; type: 'session.info' }
  | { payload?: { text?: string }; session_id?: string; type: 'thinking.delta' }
  | { payload?: undefined; session_id?: string; type: 'message.start' }
  | { payload?: { kind?: string; text?: string }; session_id?: string; type: 'status.update' }
  | { payload?: { state?: 'idle' | 'listening' | 'transcribing' }; session_id?: string; type: 'voice.status' }
  | { payload?: { no_speech_limit?: boolean; text?: string }; session_id?: string; type: 'voice.transcript' }
  | { payload: { line: string }; session_id?: string; type: 'gateway.stderr' }
  | {
      payload?: { level?: 'info' | 'warn' | 'error'; message?: string }
      session_id?: string
      type: 'browser.progress'
    }
  | {
      payload?: { cwd?: string; python?: string; stderr_tail?: string }
      session_id?: string
      type: 'gateway.start_timeout'
    }
  | { payload?: { preview?: string }; session_id?: string; type: 'gateway.protocol_error' }
  | { payload?: { text?: string; verbose?: boolean }; session_id?: string; type: 'reasoning.delta' | 'reasoning.available' }
  | { payload: { name?: string; preview?: string }; session_id?: string; type: 'tool.progress' }
  | { payload: { name?: string }; session_id?: string; type: 'tool.generating' }
  | {
      payload: { args_text?: string; context?: string; name?: string; tool_id: string; todos?: unknown[] }
      session_id?: string
      type: 'tool.start'
    }
  | {
      payload: {
        duration_s?: number
        error?: string
        inline_diff?: string
        name?: string
        result_text?: string
        summary?: string
        tool_id: string
        todos?: unknown[]
      }
      session_id?: string
      type: 'tool.complete'
    }
  | {
      payload: { choices: string[] | null; question: string; request_id: string }
      session_id?: string
      type: 'clarify.request'
    }
  | { payload: { command: string; description: string }; session_id?: string; type: 'approval.request' }
  | { payload: { request_id: string }; session_id?: string; type: 'sudo.request' }
  | { payload: { env_var: string; prompt: string; request_id: string }; session_id?: string; type: 'secret.request' }
  | { payload: { task_id: string; text: string }; session_id?: string; type: 'background.complete' }
  | { payload?: { text?: string }; session_id?: string; type: 'review.summary' }
  | { payload: SubagentEventPayload; session_id?: string; type: 'subagent.spawn_requested' }
  | { payload: SubagentEventPayload; session_id?: string; type: 'subagent.start' }
  | { payload: SubagentEventPayload; session_id?: string; type: 'subagent.thinking' }
  | { payload: SubagentEventPayload; session_id?: string; type: 'subagent.tool' }
  | { payload: SubagentEventPayload; session_id?: string; type: 'subagent.progress' }
  | { payload: SubagentEventPayload; session_id?: string; type: 'subagent.complete' }
  | { payload: { rendered?: string; text?: string }; session_id?: string; type: 'message.delta' }
  | {
      payload?: { reasoning?: string; rendered?: string; text?: string; usage?: Usage }
      session_id?: string
      type: 'message.complete'
    }
  | { payload?: { message?: string }; session_id?: string; type: 'error' }
  | { payload: SafetyStatusResponse; session_id?: string; type: 'safety.status' }
  | { payload: { decision: string; layer: string }; session_id?: string; type: 'safety.review' }
  | { payload: EvolutionStatusResponse; session_id?: string; type: 'evolution.status' }
  | { payload: EvolutionSnapshotResponse; session_id?: string; type: 'evolution.snapshot' }
