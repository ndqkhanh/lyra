import { create } from 'zustand'
import { immer } from 'zustand/middleware/immer'
import { enableMapSet } from 'immer'
import type {
  SessionState,
  Message,
  DisplayMode,
  PermissionMode,
  RenderItem,
  Transport,
  AssistantMessage,
  ProviderInfo,
  ToolCallInfo,
  PhaseInfo
} from '../types'
import { DISPLAY_MODE_PRESETS } from '../types'
import { toRenderItems } from '../utils/rendering'
import { observability } from '../observability'
import { IndicatorStateMachine } from '../stateMachine'

// Enable Immer MapSet plugin
enableMapSet()

// Performance monitoring
interface PerformanceMetrics {
  renderCount: number
  lastRenderTime: number
  averageRenderTime: number
  peakMemoryUsage: number
  messageCount: number
}

// State machine registry
const stateMachines = new Map<string, IndicatorStateMachine>()

interface UIStore {
  // Session state
  sessions: Map<string, SessionState>
  activeSessionId: string | null
  transport: Transport | null

  // Model & Provider state
  providers: ProviderInfo[]
  currentModel: string
  currentProvider: string

  // Performance metrics
  metrics: Map<string, PerformanceMetrics>

  // Actions
  setTransport: (transport: Transport) => void
  createSession: (id: string) => void
  setActiveSession: (id: string) => void
  addMessage: (sessionId: string, message: Message) => void
  beginStreaming: (sessionId: string) => void
  updateStreamingMessage: (sessionId: string, chunk: string) => void
  commitStreamingMessage: (sessionId: string) => void
  cancelStreaming: (sessionId: string) => void
  setDisplayMode: (sessionId: string, mode: DisplayMode) => void
  setPermissionMode: (sessionId: string, mode: PermissionMode) => void

  // Thinking / Tool lifecycle actions
  startThinking: (sessionId: string) => void
  endThinking: (sessionId: string) => void
  addToolCall: (sessionId: string, tool: ToolCallInfo) => void
  updateToolCall: (sessionId: string, toolId: string, status: ToolCallInfo['status']) => void

  // Phase tracking actions
  setPhases: (sessionId: string, phases: PhaseInfo[]) => void
  updatePhase: (sessionId: string, phaseId: string, status: PhaseInfo['status']) => void

  // Model & Provider actions
  setProviders: (providers: ProviderInfo[]) => void
  setCurrentModel: (model: string) => void
  setCurrentProvider: (provider: string) => void
  setModelAndProvider: (model: string, provider: string) => void

  // Observability actions
  emitEvent: (sessionId: string, type: string, data?: any) => void
  getStateMachine: (sessionId: string) => IndicatorStateMachine | null

  // Selectors
  getActiveSession: () => SessionState | null
  getRenderItems: (sessionId: string) => RenderItem[]
  getMetrics: (sessionId: string) => PerformanceMetrics | null

  // Performance monitoring
  recordRender: (sessionId: string, duration: number) => void
  updateMemoryUsage: (sessionId: string, usage: number) => void
}

export const useUIStore = create<UIStore>()(
  immer((set, get) => ({
    sessions: new Map(),
    activeSessionId: null,
    transport: null,
    providers: [],
    currentModel: '',
    currentProvider: '',
    metrics: new Map(),

    setTransport: (transport) => {
      set((state) => {
        state.transport = transport
      })
    },

    createSession: (id) => {
      set((state) => {
        state.sessions.set(id, {
          id,
          messages: [],
          previewMessages: [],
          isStreaming: false,
          isThinking: false,
          activeTools: [],
          phases: [],
          displayMode: 'standard',
          displayConfig: DISPLAY_MODE_PRESETS.standard,
          permissionMode: 'allow',  // Default to bypass/allow mode
          currentModel: state.currentModel,
          currentProvider: state.currentProvider,
        })

        // Initialize metrics
        state.metrics.set(id, {
          renderCount: 0,
          lastRenderTime: 0,
          averageRenderTime: 0,
          peakMemoryUsage: 0,
          messageCount: 0
        })

        if (!state.activeSessionId) {
          state.activeSessionId = id
        }
      })

      // Create state machine for this session
      const stateMachine = new IndicatorStateMachine(id)
      stateMachines.set(id, stateMachine)

      // Emit session start event
      observability.emit({
        type: 'session_start',
        timestamp: Date.now(),
        sessionId: id
      })
    },

    setActiveSession: (id) => {
      set((state) => {
        if (state.sessions.has(id)) {
          state.activeSessionId = id
        }
      })
    },

    addMessage: (sessionId, message) => {
      console.error(`[Store] addMessage: session=${sessionId}, role=${message.role}, content="${String(message.content).slice(0, 50)}"`)
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          session.messages.push(message)

          // Update message count metric
          const metrics = state.metrics.get(sessionId)
          if (metrics) {
            metrics.messageCount = session.messages.length
          }
        }
      })

      // Emit message commit event
      observability.emit({
        type: 'message_commit',
        timestamp: Date.now(),
        sessionId,
        data: { messageId: message.id }
      })
    },

    beginStreaming: (sessionId) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          session.isStreaming = true
        }
      })
    },

    updateStreamingMessage: (sessionId, chunk) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (!session) return

        session.isStreaming = true

        if (session.previewMessages.length === 0) {
          // Create new streaming message
          const newMsg: AssistantMessage = {
            id: `preview-${Date.now()}`,
            role: 'assistant',
            content: chunk,
            timestamp: Date.now(),
            streaming: true
          }
          session.previewMessages.push(newMsg)

          // Emit stream start event
          observability.emit({
            type: 'stream_start',
            timestamp: Date.now(),
            sessionId,
            data: { messageId: newMsg.id }
          })
        } else {
          // Append chunk to existing content (accumulate tokens)
          const lastMsg = session.previewMessages[session.previewMessages.length - 1]
          if (lastMsg.role === 'assistant') {
            lastMsg.content += chunk  // Append instead of replace

            // Emit stream chunk event
            observability.emit({
              type: 'stream_chunk',
              timestamp: Date.now(),
              sessionId,
              data: { content: chunk }
            })
          }
        }
      })
    },

    commitStreamingMessage: (sessionId) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session && session.previewMessages.length > 0) {
          const msg = session.previewMessages.pop()!

          // CRITICAL FIX: Clear ALL preview messages to prevent duplication
          // This ensures the committed message doesn't appear in both
          // staticItems (committed) and liveItems (preview) arrays
          session.previewMessages = []

          const committedMsg: AssistantMessage = {
            ...msg as AssistantMessage,
            streaming: false
          }
          session.messages.push(committedMsg)
          session.isStreaming = false

          // Update message count
          const metrics = state.metrics.get(sessionId)
          if (metrics) {
            metrics.messageCount = session.messages.length
          }

          // Emit stream end event to transition state machine back to idle
          observability.emit({
            type: 'stream_end',
            timestamp: Date.now(),
            sessionId,
            data: { messageId: committedMsg.id }
          })
        }
      })

      // Emit stream end event
      observability.emit({
        type: 'stream_end',
        timestamp: Date.now(),
        sessionId
      })
    },

    cancelStreaming: (sessionId) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          session.previewMessages = []
          session.isStreaming = false
        }
      })
    },

    setDisplayMode: (sessionId, mode) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          session.displayMode = mode
          session.displayConfig = DISPLAY_MODE_PRESETS[mode]
        }
      })
    },

    setPermissionMode: (sessionId, mode) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          session.permissionMode = mode
        }
      })

      // Emit permission mode change event
      observability.emit({
        type: 'permission_mode_change',
        timestamp: Date.now(),
        sessionId,
        data: { mode }
      })
    },

    // Thinking / Tool lifecycle actions

    startThinking: (sessionId) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          session.isThinking = true
        }
      })
      observability.emit({
        type: 'thinking_start',
        timestamp: Date.now(),
        sessionId,
      })
    },

    endThinking: (sessionId) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          session.isThinking = false
        }
      })
      observability.emit({
        type: 'thinking_end',
        timestamp: Date.now(),
        sessionId,
      })
    },

    addToolCall: (sessionId, tool) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          session.activeTools.push(tool)
        }
      })
      observability.emit({
        type: 'tool_start',
        timestamp: Date.now(),
        sessionId,
        data: { toolName: tool.name },
      })
    },

    updateToolCall: (sessionId, toolId, status) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          const tool = session.activeTools.find(t => t.id === toolId)
          if (tool) {
            tool.status = status
          }
        }
      })
      observability.emit({
        type: 'tool_end',
        timestamp: Date.now(),
        sessionId,
        data: { toolId, status },
      })
    },

    // Phase tracking actions

    setPhases: (sessionId, phases) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          session.phases = phases
        }
      })
    },

    updatePhase: (sessionId, phaseId, status) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          const phase = session.phases.find(p => p.id === phaseId)
          if (phase) {
            phase.status = status
          }
        }
      })
    },

    // Model & Provider actions
    setProviders: (providers) => {
      set((state) => {
        state.providers = providers
      })
    },

    setCurrentModel: (model) => {
      set((state) => {
        state.currentModel = model
      })
    },

    setCurrentProvider: (provider) => {
      set((state) => {
        state.currentProvider = provider
      })
    },

    setModelAndProvider: (model, provider) => {
      set((state) => {
        state.currentModel = model
        state.currentProvider = provider
        const session = state.sessions.get(state.activeSessionId || '')
        if (session) {
          session.currentModel = model
          session.currentProvider = provider
        }
      })
    },

    // Observability actions
    emitEvent: (sessionId, type, data) => {
      observability.emit({
        type: type as any,
        timestamp: Date.now(),
        sessionId,
        data
      })
    },

    getStateMachine: (sessionId) => {
      return stateMachines.get(sessionId) ?? null
    },

    // Selectors
    getActiveSession: () => {
      const { sessions, activeSessionId } = get()
      return activeSessionId ? sessions.get(activeSessionId) ?? null : null
    },

    getRenderItems: (sessionId) => {
      const session = get().sessions.get(sessionId)
      if (!session) {
        console.error(`[Store] getRenderItems: session ${sessionId} NOT FOUND`)
        return []
      }
      const items = toRenderItems(session.messages, session.previewMessages)
      if (items.length > 0) {
        console.error(`[Store] getRenderItems: ${items.length} items, msgs=${session.messages.length}, preview=${session.previewMessages.length}`)
      }
      return items
    },

    getMetrics: (sessionId) => {
      return get().metrics.get(sessionId) ?? null
    },

    // Performance monitoring
    recordRender: (sessionId, duration) => {
      set((state) => {
        const metrics = state.metrics.get(sessionId)
        if (metrics) {
          metrics.renderCount++
          metrics.lastRenderTime = duration
          // Calculate rolling average
          metrics.averageRenderTime =
            (metrics.averageRenderTime * (metrics.renderCount - 1) + duration) /
            metrics.renderCount
        }
      })
    },

    updateMemoryUsage: (sessionId, usage) => {
      set((state) => {
        const metrics = state.metrics.get(sessionId)
        if (metrics) {
          metrics.peakMemoryUsage = Math.max(metrics.peakMemoryUsage, usage)
        }
      })
    }
  }))
)
