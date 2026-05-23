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
export type DisplayMode = 'minimal' | 'standard' | 'debug'

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
}

// Session State
export interface SessionState {
  id: string
  messages: Message[]
  previewMessages: Message[]  // Streaming zone
  isStreaming: boolean
  displayMode: DisplayMode
  displayConfig: DisplayConfig
}

// Transport Interface
export interface Transport {
  connect(): Promise<void>
  disconnect(): Promise<void>
  sendMessage(content: string, attachments?: Attachment[]): Promise<void>
  onMessage(handler: (message: Message) => void): () => void
  onStreamChunk(handler: (chunk: StreamChunk) => void): () => void
  onError(handler: (error: Error) => void): () => void
  onStatusChange(handler: (status: ConnectionStatus) => void): () => void
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

export interface StreamChunk {
  type: 'text' | 'thinking' | 'tool-call' | 'tool-result'
  content: string
  metadata?: Record<string, unknown>
}
