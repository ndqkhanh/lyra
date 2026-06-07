import { useCallback, useEffect, useRef, useState } from 'react'
import { theme } from './styles/theme'
import { ChatView } from './components/ChatView'
import { Sidebar } from './components/Sidebar'
import { InputBar } from './components/InputBar'
import { StatusBar } from './components/StatusBar'
import { FleetView } from './components/FleetView'
import { SkillsHub } from './components/SkillsHub'
import { useLyraAPI, type StreamChunk } from './hooks/useLyraAPI'
import { useSessions } from './hooks/useSessions'

type AppTab = 'chat' | 'fleet' | 'skills'

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
  const [activeTab, setActiveTab] = useState<AppTab>('chat')
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

      try {
        // Use the IPC proxy via connectSSE instead of direct fetch.
        // The main process handles TLS and proxy settings.
        await sendMessage(
          activeId,
          text,
          (chunk: StreamChunk) => {
            if (chunk.content) {
              currentChunkRef.current += chunk.content
            }
            setMessages((prev) => {
              const last = prev[prev.length - 1]
              if (last && last.isStreaming) {
                return prev.map((m) =>
                  m.id === last.id ? { ...m, content: currentChunkRef.current } : m,
                )
              }
              return prev
            })
          },
          model,
          provider,
        )

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
    [activeId, sendMessage],
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
            {/* Tab navigation */}
            <div style={{ display: 'flex', gap: 4, marginRight: 16 }}>
              {(['chat', 'fleet', 'skills'] as AppTab[]).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  style={{
                    padding: '4px 16px',
                    fontSize: theme.fontSize.sm,
                    fontWeight: activeTab === tab ? 'bold' : 'normal',
                    color: activeTab === tab ? theme.colors.fg : theme.colors.fgMuted,
                    backgroundColor: activeTab === tab ? theme.colors.surface : 'transparent',
                    border: `1px solid ${activeTab === tab ? theme.colors.accent : 'transparent'}`,
                    borderRadius: 4,
                    cursor: 'pointer',
                  }}
                >
                  {tab === 'chat' ? '💬 Chat' : tab === 'fleet' ? '🚀 Fleet' : '🧩 Skills'}
                </button>
              ))}
            </div>

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
          {activeTab === 'chat' && (
            <ChatView messages={messages} sessionId={activeId} />
          )}
          {activeTab === 'fleet' && (
            <FleetView
              sessions={sessions.map((s) => ({
                sessionId: s.id,
                name: s.name || s.id.slice(0, 8),
                taskState: (s.taskState as any) || 'IDLE',
                processState: (s.processAlive ? 'ALIVE' : 'EXITED') as any,
                summary: s.summary || '',
                workingDir: s.workingDir || '',
                modelName: s.modelName || '',
                lastActive: s.lastActive || new Date().toISOString(),
              }))}
              onAttach={(id) => switchSession(id)}
              onStop={(id) => deleteSession(id)}
              onDispatch={async (cmd) => {
                const newId = await createSession(cmd)
                if (newId) switchSession(newId)
              }}
              onRefresh={checkConnection}
            />
          )}
          {activeTab === 'skills' && (
            <SkillsHub
              installedSkills={[]}
              availableSkills={[]}
              onInstall={() => {}}
              onUninstall={() => {}}
              onCreate={() => {}}
              onRefresh={() => {}}
            />
          )}

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
