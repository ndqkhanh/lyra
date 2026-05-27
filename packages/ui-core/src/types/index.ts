// Message Types
export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  metadata?: Record<string, unknown>
}

export interface UserMessage extends Message {
  role: 'user'
  attachments?: Attachment[]
}

export interface AssistantMessage extends Message {
  role: 'assistant'
  thinking?: ThinkingBlock
  toolCalls?: ToolCall[]
  streaming?: boolean
}

export interface ThinkingBlock {
  content: string
  durationMs?: number
  collapsed: boolean
}

export interface ToolCall {
  id: string
  name: string
  args: Record<string, unknown>
  result?: ToolResult
  status: 'pending' | 'running' | 'success' | 'error'
  startTime: number
  endTime?: number
}

export interface ToolResult {
  output: string
  error?: string
  metadata?: Record<string, unknown>
}

export interface Attachment {
  type: 'image' | 'file'
  data: string | Buffer
  mimeType: string
  filename?: string
}

// Render Item Types (flat rendering pipeline)
export type RenderItem =
  | UserTextItem
  | UserImageItem
  | AssistantTextItem
  | ThinkingItem
  | ToolExecutionItem
  | ErrorItem
  | SystemNoticeItem

export interface BaseRenderItem {
  id: string
  sourceMessageId: string
  committed: boolean  // Static vs Live zone
  timestamp: number
}

export interface UserTextItem extends BaseRenderItem {
  kind: 'user-text'
  content: string
}

export interface UserImageItem extends BaseRenderItem {
  kind: 'user-image'
  data: string
  mimeType: string
}

export interface AssistantTextItem extends BaseRenderItem {
  kind: 'assistant-text'
  content: string
  streaming: boolean
}

export interface ThinkingItem extends BaseRenderItem {
  kind: 'thinking'
  content: string
  durationSec?: number
  collapsed: boolean
}

export interface ToolExecutionItem extends BaseRenderItem {
  kind: 'tool-execution'
  toolName: string
  args: Record<string, unknown>
  result?: ToolResult
  status: ToolCall['status']
}

export interface ErrorItem extends BaseRenderItem {
  kind: 'error'
  message: string
  stack?: string
}

export interface SystemNoticeItem extends BaseRenderItem {
  kind: 'system-notice'
  content: string
  noticeType: 'info' | 'warning' | 'success'
}

// Display Configuration
export type DisplayMode = 'minimal' | 'standard' | 'debug' | 'focus'
export type PermissionMode = 'ask' | 'allow' | 'deny'

export interface DisplayConfig {
  showThinking: boolean
  showCosts: boolean
  showToolArgs: boolean
  toolOutput: 'hidden' | 'standard' | 'expanded'
  showTraces: boolean
  showStatusBar: boolean
}

export const DISPLAY_MODE_PRESETS: Record<DisplayMode, DisplayConfig> = {
  minimal: {
    showThinking: false,
    showCosts: false,
    showToolArgs: false,
    toolOutput: 'hidden',
    showTraces: false,
    showStatusBar: false,
  },
  standard: {
    showThinking: true,
    showCosts: true,
    showToolArgs: true,
    toolOutput: 'standard',
    showTraces: false,
    showStatusBar: true,
  },
  debug: {
    showThinking: true,
    showCosts: true,
    showToolArgs: true,
    toolOutput: 'expanded',
    showTraces: true,
    showStatusBar: true,
  },
  focus: {
    showThinking: false,
    showCosts: true,
    showToolArgs: false,
    toolOutput: 'hidden',
    showTraces: false,
    showStatusBar: true,
  },
}

// Model & Provider Types
export interface ModelInfo {
  slug: string
  display_name: string
  description: string
  tags: string[]
  context_window: number
  max_output_tokens: number
}

export interface ProviderInfo {
  key: string
  display_name: string
  icon: string
  website: string
  api_key_url: string
  notes: string
  default_model: string
  context_window: number
  supports_tools: boolean
  supports_reasoning: boolean
  supports_vision: boolean
  env_vars: string[]
  models: ModelInfo[]
}

// Session State
export interface SessionState {
  id: string
  messages: Message[]
  previewMessages: Message[]  // Streaming zone
  isStreaming: boolean
  isThinking: boolean
  activeTools: ToolCallInfo[]
  phases: PhaseInfo[]
  displayMode: DisplayMode
  displayConfig: DisplayConfig
  permissionMode: PermissionMode
  currentModel: string
  currentProvider: string
}

/** Lightweight tool-call tracking for inline UI rendering. */
export interface ToolCallInfo {
  id: string
  name: string
  args?: string
  status: 'running' | 'success' | 'error'
  startTime: number
}

/** A tracked phase/task with checkbox state. */
export interface PhaseInfo {
  id: string
  label: string
  status: 'pending' | 'active' | 'completed'
}

// Transport Interface
export interface Transport {
  connect(): Promise<void>
  disconnect(): Promise<void>
  sendMessage(content: string, attachments?: Attachment[], model?: string): Promise<void>
  onMessage(handler: (message: Message) => void): () => void
  onStreamChunk(handler: (chunk: StreamChunk) => void): () => void
  onStreamEvent(handler: (event: StreamEvent) => void): () => void
  onError(handler: (error: Error) => void): () => void
  onStatusChange(handler: (status: ConnectionStatus) => void): () => void
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

export interface StreamChunk {
  type: 'text' | 'thinking' | 'tool-call' | 'tool-result'
  content: string
  done?: boolean
  metadata?: Record<string, unknown>
}

/** Rich event emitted by the transport layer for thinking / tool lifecycle. */
export interface StreamEvent {
  kind: 'thinking_start' | 'thinking_end' | 'tool_start' | 'tool_end'
  payload: string
  metadata?: Record<string, unknown>
}
