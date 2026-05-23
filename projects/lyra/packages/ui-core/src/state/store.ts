import { create } from 'zustand'
import { immer } from 'zustand/middleware/immer'
import type {
  SessionState,
  Message,
  DisplayMode,
  RenderItem,
  Transport,
  AssistantMessage
} from '../types'
import { DISPLAY_MODE_PRESETS } from '../types'
import { toRenderItems } from '../utils/rendering'

interface UIStore {
  // Session state
  sessions: Map<string, SessionState>
  activeSessionId: string | null
  transport: Transport | null

  // Actions
  setTransport: (transport: Transport) => void
  createSession: (id: string) => void
  setActiveSession: (id: string) => void
  addMessage: (sessionId: string, message: Message) => void
  updateStreamingMessage: (sessionId: string, chunk: string) => void
  commitStreamingMessage: (sessionId: string) => void
  setDisplayMode: (sessionId: string, mode: DisplayMode) => void

  // Selectors
  getActiveSession: () => SessionState | null
  getRenderItems: (sessionId: string) => RenderItem[]
}

export const useUIStore = create<UIStore>()(
  immer((set, get) => ({
    sessions: new Map(),
    activeSessionId: null,
    transport: null,

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
          displayMode: 'standard',
          displayConfig: DISPLAY_MODE_PRESETS.standard
        })
        if (!state.activeSessionId) {
          state.activeSessionId = id
        }
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
        } else {
          // Append to existing streaming message
          const lastMsg = session.previewMessages[session.previewMessages.length - 1]
          if (lastMsg.role === 'assistant') {
            lastMsg.content += chunk
          }
        }
      })
    },

    commitStreamingMessage: (sessionId) => {
      set((state) => {
        const session = state.sessions.get(sessionId)
        if (session && session.previewMessages.length > 0) {
          const msg = session.previewMessages.pop()!
          const committedMsg: AssistantMessage = {
            ...msg as AssistantMessage,
            streaming: false
          }
          session.messages.push(committedMsg)
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

    getActiveSession: () => {
      const { sessions, activeSessionId } = get()
      return activeSessionId ? sessions.get(activeSessionId) ?? null : null
    },

    getRenderItems: (sessionId) => {
      const session = get().sessions.get(sessionId)
      if (!session) return []
      return toRenderItems(session.messages, session.previewMessages)
    }
  }))
)
