import React, { useState, useMemo } from 'react'
import { Box, Text, useInput } from 'ink'
import { useUIStore, useThemeColors } from '@lyra/ui-core'

interface SessionDashboardProps {
  visible: boolean
  activeSessionId: string
  onSelect: (sessionId: string) => void
  onClose: () => void
}

interface SessionSummary {
  id: string
  messageCount: number
  status: 'running' | 'blocked' | 'completed' | 'idle'
  preview: string
  model: string
}

export function SessionDashboard({ visible, activeSessionId, onSelect, onClose }: SessionDashboardProps) {
  const colors = useThemeColors()
  const sessions = useUIStore(state => state.sessions)
  const [selectedIndex, setSelectedIndex] = useState(0)

  const sessionList: SessionSummary[] = useMemo(() => {
    const result: SessionSummary[] = []
    sessions.forEach((s, id) => {
      const lastMsg = s.messages[s.messages.length - 1]
      result.push({
        id,
        messageCount: s.messages.length,
        status: s.isStreaming ? 'running' : s.messages.length > 0 ? 'idle' : 'completed',
        preview: lastMsg ? lastMsg.content.slice(0, 50) + (lastMsg.content.length > 50 ? '...' : '') : '(empty)',
        model: s.currentModel || 'default',
      })
    })
    return result
  }, [sessions])

  useInput((_input, key) => {
    if (!visible) return
    if (key.escape) { onClose(); return }
    if (key.upArrow) { setSelectedIndex(p => Math.max(0, p - 1)); return }
    if (key.downArrow) { setSelectedIndex(p => Math.min(sessionList.length - 1, p + 1)); return }
    if (key.return) {
      const session = sessionList[selectedIndex]
      if (session) onSelect(session.id)
    }
  })

  if (!visible) return null

  const statusColor: Record<string, string> = {
    running: colors.statusActive,
    blocked: colors.warning,
    completed: colors.statusIdle,
    idle: colors.info,
  }

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} height={18}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={colors.info}>Sessions ({sessionList.length})</Text>
        <Text dimColor>↑↓ navigate  Enter attach  Esc close</Text>
      </Box>

      <Box flexDirection="column" flexGrow={1}>
        {sessionList.length === 0 && (
          <Text color={colors.muted}>No active sessions</Text>
        )}
        {sessionList.map((s, i) => (
          <Box key={s.id}>
            <Text color={i === selectedIndex ? colors.userPrompt : colors.timestamp} bold={i === selectedIndex}>
              {i === selectedIndex ? '❯ ' : '  '}
            </Text>
            <Text color={s.id === activeSessionId ? colors.success : undefined}>
              {s.id === activeSessionId ? '* ' : '  '}
            </Text>
            <Text color={statusColor[s.status]}>
              [{s.status.slice(0, 4).padEnd(4)}]
            </Text>
            <Text> {s.id.slice(0, 16)}</Text>
            <Text dimColor> · {s.messageCount} msgs</Text>
            <Text dimColor> · {s.model}</Text>
          </Box>
        ))}
      </Box>
    </Box>
  )
}
