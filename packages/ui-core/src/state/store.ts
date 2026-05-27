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
import { observability, type ObservabilityEventType } from '../observability'
import { IndicatorStateMachine } from '../stateMachine'
import { getThemePreset, getDefaultTheme, type ThemePalette } from '../theme/presets'
import { buildSkinFromPreset, type SkinConfig } from '../theme/skin'
import { LYRA_BRAND } from '../theme/theme'
import { createStreamingDebouncer, type StreamingDebouncer } from '../streaming'

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

// Streaming debouncer for 60 FPS updates
let streamingDebouncer: StreamingDebouncer | null = null

export interface UIStore {
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

  // Queue management actions
  enqueueMessage: (sessionId: string, message: Message) => void
  dequeueMessage: (sessionId: string) => Message | null
  clearQueue: (sessionId: string) => void

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

  // Theme actions
  activeThemeId: string
  _skinCache: SkinConfig | null
  setActiveTheme: (themeId: string) => void
  getActiveThemeColors: () => ThemePalette
  getActiveSkin: () => SkinConfig

  // Selectors
  getActiveSession: () => SessionState | null
  getRenderItems: (sessionId: string) => RenderItem[]
  getMetrics: (sessionId: string) => PerformanceMetrics | null

  // Session lifecycle
  destroySession: (sessionId: string) => void

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
    activeThemeId: 'dracula',
    _skinCache: null as SkinConfig | null,

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
          queuedMessages: [],
          isStreaming: false,
          isThinking: false,
          activeTools: [],
          phases: [],
          displayMode: 'standard',
          displayConfig: DISPLAY_MODE_PRESETS.standard,
          permissionMode: 'ask',  // Default to ask mode for security
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
      // Initialize debouncer on first use
      if (!streamingDebouncer) {
        streamingDebouncer = createStreamingDebouncer((update) => {
          // This callback runs at 60 FPS with accumulated content
          set((state) => {
            const session = state.sessions.get(update.sessionId)
            if (!session) return

            session.isStreaming = true

            if (session.previewMessages.length === 0) {
              // Create new streaming message
              const newMsg: AssistantMessage = {
                id: `preview-${Date.now()}`,
                role: 'assistant',
                content: update.content,
                timestamp: update.timestamp,
                streaming: true
              }
              session.previewMessages.push(newMsg)

              // Emit stream start event
              observability.emit({
                type: 'stream_start',
                timestamp: update.timestamp,
                sessionId: update.sessionId,
                data: { messageId: newMsg.id }
              })
            } else {
              // Replace content with accumulated buffer
              const lastMsg = session.previewMessages[session.previewMessages.length - 1]
              if (lastMsg.role === 'assistant') {
                lastMsg.content = update.content

                // Emit stream chunk event
                observability.emit({
                  type: 'stream_chunk',
                  timestamp: update.timestamp,
                  sessionId: update.sessionId,
                  data: { content: update.content }
                })
              }
            }
          })
        }, {
          targetFPS: 60,
          quantize: true,
          quantizeBinSize: 10
        })
      }

      // Push chunk to debouncer (will batch at 60 FPS)
      streamingDebouncer.push(sessionId, chunk)
    },

    commitStreamingMessage: (sessionId) => {
      // Flush any remaining buffered content
      if (streamingDebouncer) {
        streamingDebouncer.flush(sessionId)
      }

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

      // Clean up debouncer state
      if (streamingDebouncer) {
        streamingDebouncer.cleanup(sessionId)
      }

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

    // Queue management actions

    enqueueMessage: (sessionId, message) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          session.queuedMessages.push(message)
        }
      })
      observability.emit({
        type: 'message_queued',
        timestamp: Date.now(),
        sessionId,
        data: { messageId: message.id },
      })
    },

    dequeueMessage: (sessionId) => {
      let messageId: string | undefined = undefined
      let messageContent: string | undefined = undefined

      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session && session.queuedMessages.length > 0) {
          const msg = session.queuedMessages[0]
          if (msg) {
            messageId = msg.id
            messageContent = msg.content
          }
          session.queuedMessages.shift()
        }
      })

      if (messageId && messageContent !== undefined) {
        observability.emit({
          type: 'message_dequeued',
          timestamp: Date.now(),
          sessionId,
          data: { messageId },
        })

        // Reconstruct the message from stored values
        return {
          id: messageId,
          role: 'user' as const,
          content: messageContent,
          timestamp: Date.now(),
        }
      }

      return null
    },

    clearQueue: (sessionId) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session) {
          session.queuedMessages = []
        }
      })
      observability.emit({
        type: 'queue_cleared',
        timestamp: Date.now(),
        sessionId,
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
        type: type as ObservabilityEventType,
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
        return []
      }
      const items = toRenderItems(session.messages, session.previewMessages)
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
    },

    // Theme actions
    setActiveTheme: (themeId) => {
      set((state) => {
        state.activeThemeId = themeId
        // Rebuild skin cache so getActiveSkin() returns stable reference
        const preset = getThemePreset(themeId) ?? getDefaultTheme()
        state._skinCache = buildSkinFromPreset(preset, {
          agentName: LYRA_BRAND.name,
          welcome: LYRA_BRAND.welcome,
          goodbye: LYRA_BRAND.goodbye,
          promptSymbol: LYRA_BRAND.prompt,
          helpHeader: LYRA_BRAND.helpHeader,
        })
      })
    },

    getActiveThemeColors: () => {
      const themeId = get().activeThemeId
      const preset = getThemePreset(themeId) ?? getDefaultTheme()
      return preset.palette
    },

    getActiveSkin: () => {
      const state = get()
      if (state._skinCache) return state._skinCache
      // Lazy init: build and cache on first access
      const preset = getThemePreset(state.activeThemeId) ?? getDefaultTheme()
      const skin = buildSkinFromPreset(preset, {
        agentName: LYRA_BRAND.name,
        welcome: LYRA_BRAND.welcome,
        goodbye: LYRA_BRAND.goodbye,
        promptSymbol: LYRA_BRAND.prompt,
        helpHeader: LYRA_BRAND.helpHeader,
      })
      set((s) => { s._skinCache = skin })
      return skin
    },

    // Session lifecycle
    destroySession: (sessionId) => {
      const machine = stateMachines.get(sessionId)
      if (machine) {
        machine.reset()
        stateMachines.delete(sessionId)
      }
      set((state) => {
        state.sessions.delete(sessionId)
        state.metrics.delete(sessionId)
        if (state.activeSessionId === sessionId) {
          state.activeSessionId = null
        }
      })
    },
  }))
)
