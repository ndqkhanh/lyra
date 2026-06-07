import React, { useCallback, useEffect, useRef, useState } from 'react'
import { theme } from './styles/theme'
import { ChatView } from './components/ChatView'
import { Sidebar } from './components/Sidebar'
import { InputBar } from './components/InputBar'
import { StatusBar } from './components/StatusBar'
import { useLyraAPI, type StreamChunk } from './hooks/useLyraAPI'
import { useSessions } from './hooks/useSessions'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  isStreaming?: boolean
}

export function App() {
  const {
    connected,
    providers,
    usage,
    sendMessage,
    cancelStream,
    checkConnection,
  } = useLyraAPI()

  const {
    sessions,
    activeId,
    switchSession,
    createSession,
    deleteSession,
  } = useSessions()

  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [sidebarVisible, setSidebarVisible] = useState(true)
  const [currentChunk, setCurrentChunk] = useState('')
  const currentChunkRef = useRef('')

  // Add a system message explaining connection status
  useEffect(() => {
    if (!connected) {
      setMessages((prev) => {
        const existing = prev.find((m) => m.id === 'conn-status')
        if (existing) {
          return prev.map((m) =>
            m.id === 'conn-status' ? { ...m, content: 'Disconnected from Lyra agent core' } : m,
          )
        }
        return [
          {
            id: 'conn-status',
            role: 'system',
            content: 'Connecting to Lyra agent core at 127.0.0.1:8580...',
            timestamp: Date.now(),
          },
          ...prev,
        ]
      })
    } else {
      setMessages((prev) => {
        const existing = prev.find((m) => m.id === 'conn-status')
        if (existing && existing.content.includes('Disconnected')) {
          return prev.map((m) =>
            m.id === 'conn-status' ? { ...m, content: 'Connected to Lyra agent core', timestamp: Date.now() } : m,
          )
        }
        // Remove the stale connection message
        if (existing && existing.content.includes('Connecting')) {
          return prev.filter((m) => m.id !== 'conn-status')
        }
        return prev
      })
    }
  }, [connected])

  // Re-check connection periodically
  useEffect(() => {
    const interval = setInterval(checkConnection, 10000)
    return () => clearInterval(interval)
  }, [checkConnection])

  const handleSend = useCallback(
    async (text: string, model?: string, provider?: string) => {
      if (!activeId) return

      // Reset current chunk
      currentChunkRef.current = ''

      const userMsg: Message = {
        id: `msg-${Date.now()}`,
        role: 'user',
        content: text,
        timestamp: Date.now(),
      }

      const assistantMsg: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
        isStreaming: true,
      }

      setMessages((prev) => [...prev, userMsg, assistantMsg])
      setIsStreaming(true)

      // Create a simple streaming simulation via the hook's sendMessage
      // In production, the main process SSE handler pushes chunks
      // For now, we use a direct fetch approach:
      try {
        const apiUrl = await window.lyraAPI.getApiUrl()
        const resp = await fetch(`${apiUrl}/chat/${activeId}/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            model: model || undefined,
            provider: provider || undefined,
          }),
        })

        if (!resp.ok) {
          throw new Error(`HTTP ${resp.status}`)
        }

        const reader = resp.body?.getReader()
        if (!reader) throw new Error('No response body')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              try {
                const chunk = JSON.parse(data) as StreamChunk
                if (chunk.content) {
                  currentChunkRef.current += chunk.content
                  setMessages((prev) => {
                    const last = prev[prev.length - 1]
                    if (last && last.isStreaming) {
                      return prev.map((m) =>
                        m.id === last.id ? { ...m, content: currentChunkRef.current } : m,
                      )
                    }
                    return prev
                  })
                }
                if (chunk.done) {
                  break
                }
              } catch {
                currentChunkRef.current += line
              }
            }
          }
        }

        // Finalize the assistant message
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last && last.isStreaming) {
            return prev.map((m) =>
              m.id === last.id ? { ...m, isStreaming: false, content: currentChunkRef.current } : m,
            )
          }
          return prev
        })
      } catch (error) {
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last && last.isStreaming) {
            return prev.map((m) =>
              m.id === last.id
                ? { ...m, isStreaming: false, content: `Error: ${(error as Error).message}` }
                : m,
            )
          }
          return prev
        })
      } finally {
        setIsStreaming(false)
        currentChunkRef.current = ''
      }
    },
    [activeId],
  )

  const handleCancel = useCallback(() => {
    cancelStream()
    setIsStreaming(false)
    setMessages((prev) => {
      const last = prev[prev.length - 1]
      if (last && last.isStreaming) {
        return prev.map((m) =>
          m.id === last.id ? { ...m, isStreaming: false, content: m.content + '\n\n_Cancelled_' } : m,
        )
      }
      return prev
    })
  }, [cancelStream])

  const toggleSidebar = useCallback(() => {
    setSidebarVisible((v) => !v)
  }, [])

  // Compute total usage across messages
  const totalTokensIn = messages.reduce((acc, m) => {
    if (m.role === 'user') return acc + Math.ceil(m.content.length / 4)
    return acc
  }, 0)

  const totalTokensOut = messages.reduce((acc, m) => {
    if (m.role === 'assistant') return acc + Math.ceil(m.content.length / 4)
    return acc
  }, 0)

  const totalCost = (totalTokensIn / 1_000_000) * 3.0 + (totalTokensOut / 1_000_000) * 15.0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: theme.colors.bg }}>
      {/* Main area: sidebar + chat */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar
          sessions={sessions}
          activeId={activeId}
          providers={providers}
          onSelectSession={switchSession}
          onCreateSession={createSession}
          onDeleteSession={deleteSession}
          visible={sidebarVisible}
        />

        {/* Chat area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Toggle sidebar button */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: `${theme.spacing.sm}px ${theme.spacing.lg}px`,
              borderBottom: `1px solid ${theme.colors.border}`,
              flexShrink: 0,
            }}
          >
            <button
              onClick={toggleSidebar}
              style={{
                fontSize: theme.fontSize.xs,
                color: theme.colors.fgMuted,
                padding: '2px 8px',
                borderRadius: theme.radius.sm,
                border: `1px solid ${theme.colors.borderLight}`,
              }}
            >
              {sidebarVisible ? 'Hide Sidebar' : 'Show Sidebar'}
            </button>
          </div>

          {/* Messages */}
          <ChatView messages={messages} sessionId={activeId} />

          {/* Input bar */}
          <InputBar
            onSend={handleSend}
            onCancel={handleCancel}
            isStreaming={isStreaming}
            providers={providers}
            disabled={!activeId}
          />
        </div>
      </div>

      {/* Status bar */}
      <StatusBar
        connected={connected}
        tokensIn={usage.tokensIn + totalTokensIn}
        tokensOut={usage.tokensOut + totalTokensOut}
        cost={usage.cost + totalCost}
        sessionCount={sessions.length}
        activeSessionId={activeId}
        isStreaming={isStreaming}
      />
    </div>
  )
}
