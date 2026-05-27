import React, { useState, useEffect } from 'react'
import { Box, Text } from 'ink'
import { useUIStore, useThemeColors, symbols } from '@lyra/ui-core'

export interface AgentInfo {
  id: string
  name: string
  description?: string
  status: 'pending' | 'running' | 'completed' | 'error'
  tokens?: number
  startTime?: number
}

interface AgentTreeProps {
  sessionId: string
  visible: boolean
}

export function AgentTree({ sessionId, visible }: AgentTreeProps) {
  const colors = useThemeColors()
  const session = useUIStore(state => state.sessions.get(sessionId))
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [elapsedMap, setElapsedMap] = useState<Record<string, number>>({})
  const [globalElapsed, setGlobalElapsed] = useState(0)
  const [firstAgentTime, setFirstAgentTime] = useState<number | null>(null)

  // Derive agents from preview messages with tool calls
  useEffect(() => {
    if (!session) return
    const activeAgents: AgentInfo[] = []

    for (const msg of session.previewMessages) {
      if (msg.metadata?.toolCalls) {
        const calls = msg.metadata.toolCalls as Array<{
          id: string; name: string; description?: string; status: string
        }>
        for (const tc of calls) {
          activeAgents.push({
            id: tc.id,
            name: tc.name,
            description: tc.description,
            status: 'running',
            startTime: msg.timestamp,
            tokens: Math.ceil(msg.content.length / 4)
          })
        }
      }
    }

    // Also check for tool-execution render items from the store
    if (activeAgents.length === 0 && session.isStreaming) {
      const renderItems = useUIStore.getState().getRenderItems(sessionId)
      const runningTools = renderItems.filter(
        item => item.kind === 'tool-execution' && 'status' in item && item.status === 'running'
      )
      for (const tool of runningTools) {
        activeAgents.push({
          id: tool.id,
          name: 'toolName' in tool ? String(tool.toolName) : 'agent',
          status: 'running',
          startTime: 'timestamp' in tool ? Number(tool.timestamp) : Date.now()
        })
      }
    }

    if (activeAgents.length > 0 && !firstAgentTime && activeAgents[0].startTime) {
      setFirstAgentTime(activeAgents[0].startTime)
    }
    if (activeAgents.length === 0) {
      setFirstAgentTime(null)
      setGlobalElapsed(0)
    }

    setAgents(activeAgents)
  }, [session, sessionId, firstAgentTime])

  // Update elapsed times every second
  useEffect(() => {
    if (agents.length === 0) return
    const interval = setInterval(() => {
      const now = Date.now()
      const updates: Record<string, number> = {}
      agents.forEach(a => {
        if (a.startTime) updates[a.id] = Math.floor((now - a.startTime) / 1000)
      })
      setElapsedMap(updates)
      if (firstAgentTime) {
        setGlobalElapsed(Math.floor((now - firstAgentTime) / 1000))
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [agents, firstAgentTime])

  if (!visible || agents.length === 0) return null

  const formatTime = (s: number) => {
    if (s >= 60) return `${Math.floor(s / 60)}m ${s % 60}s`
    return `${s}s`
  }
  const formatTokens = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)

  const doneCount = agents.filter(a => a.status === 'completed').length
  const inProgressCount = agents.filter(a => a.status === 'running').length
  const openCount = agents.filter(a => a.status === 'pending').length
  const totalCount = agents.length

  return (
    <Box flexDirection="column" paddingX={2} marginTop={1}>
      {/* Progress summary: ✻ Crunched for 5m 9s · 3 local agents still running */}
      {(globalElapsed > 0 || agents.length > 0) && (
        <Box marginBottom={1}>
          <Text color={colors.thinking}>{symbols.thinkingFrames[globalElapsed % 4]} </Text>
          <Text color={colors.thinking} bold>Crunched for {formatTime(globalElapsed)}</Text>
          <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
          <Text color={colors.statusRunning}>{agents.length} local agent{agents.length !== 1 ? 's' : ''} still running</Text>
        </Box>
      )}

      {/* Task counts */}
      <Box marginBottom={1}>
        <Text>  </Text>
        <Text color={colors.muted}>{totalCount} tasks </Text>
        <Text color={colors.muted} dimColor>(</Text>
        <Text color={colors.statusSuccess}>{doneCount} done</Text>
        <Text color={colors.muted} dimColor>, </Text>
        <Text color={colors.statusRunning}>{inProgressCount} in progress</Text>
        <Text color={colors.muted} dimColor>, </Text>
        <Text color={colors.muted}>{openCount} open</Text>
        <Text color={colors.muted} dimColor>)</Text>
      </Box>

      {/* Phase checkboxes */}
      {agents.slice(0, 5).map((agent) => (
        <Box key={agent.id}>
          <Text>  </Text>
          <Text color={colors.statusRunning}>{symbols.checkboxChecked} </Text>
          <Text color={colors.toolName}>{agent.name}</Text>
          {agent.description && (
            <>
              <Text>: </Text>
              <Text color={colors.muted}>{agent.description}</Text>
            </>
          )}
        </Box>
      ))}
      {agents.length > 5 && (
        <Box>
          <Text>  </Text>
          <Text color={colors.muted} dimColor>… +{agents.length - 5} pending</Text>
        </Box>
      )}

      {/* Separator before agent tree */}
      <Box marginY={1}>
        <Text color={colors.shortcutKey}>{symbols.horizontalLine.repeat(8)} </Text>
        <Text color={colors.muted} dimColor>↑/↓ to select · Enter to view agents</Text>
      </Box>

      {/* Main agent line */}
      <Box>
        <Text color={colors.success}>{symbols.assistant} </Text>
        <Text bold color={colors.info}>main</Text>
        <Text color={colors.muted} dimColor>                                    ↑/↓ to select · Enter to view</Text>
      </Box>

      {/* Individual agent entries */}
      {agents.map((agent) => {
        const elapsed = elapsedMap[agent.id] || 0
        return (
          <Box key={agent.id}>
            <Text>  </Text>
            <Text color={colors.statusRunning}>{symbols.backgroundTask} </Text>
            <Text color={colors.toolName}>{agent.name}</Text>
            {agent.description && (
              <>
                <Text>  </Text>
                <Text color={colors.muted}>{agent.description}</Text>
              </>
            )}
            <Text color={colors.muted} dimColor>  {formatTime(elapsed)}</Text>
            {agent.tokens && agent.tokens > 0 && (
              <>
                <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
                <Text color={colors.success}>↓ {formatTokens(agent.tokens)} tokens</Text>
              </>
            )}
          </Box>
        )
      })}
    </Box>
  )
}
