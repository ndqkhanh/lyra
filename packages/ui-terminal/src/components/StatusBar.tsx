import React, { useState, useEffect, useRef } from 'react'
import { Box, Text } from 'ink'
import { colors, symbols, useUIStore } from '@lyra/ui-core'

interface StatusBarProps {
  sessionId: string
  width?: number
}

export const StatusBar = React.memo(function StatusBar({
  sessionId,
  width = 120,
}: StatusBarProps) {
  const session = useUIStore(state => state.sessions.get(sessionId))
  const isStreaming = session?.isStreaming ?? false
  const permissionMode = session?.permissionMode || 'allow'

  const agentCount = session?.previewMessages.filter(
    m => m.metadata?.toolCalls
  ).length ?? 0

  const [tokensIn, setTokensIn] = useState(0)
  const [tokensOut, setTokensOut] = useState(0)
  const [totalTokens, setTotalTokens] = useState(0)
  const [cost, setCost] = useState(0)
  const [completed, setCompleted] = useState(0)

  const streamStartRef = useRef<number | null>(null)

  // Track streaming start time, capture completion when streaming ends
  useEffect(() => {
    if (isStreaming) {
      if (!streamStartRef.current) {
        streamStartRef.current = Date.now()
        setCompleted(0)
      }
    } else if (streamStartRef.current) {
      const final = Math.floor((Date.now() - streamStartRef.current) / 1000)
      setCompleted(final)
      streamStartRef.current = null
    }
  }, [isStreaming])

  // Calculate tokens
  useEffect(() => {
    if (!session) return
    let totalIn = 0
    let totalOut = 0
    session.messages.forEach(msg => {
      const tokenCount = Math.ceil(msg.content.length / 4)
      if (msg.role === 'user') totalIn += tokenCount
      else if (msg.role === 'assistant') totalOut += tokenCount
    })
    setTokensIn(totalIn)
    setTokensOut(totalOut)
    setTotalTokens(totalIn + totalOut)

    const costIn = (totalIn / 1000000) * 15
    const costOut = (totalOut / 1000000) * 75
    setCost(costIn + costOut)
  }, [session?.messages])

  const CONTEXT_WINDOW = 200_000

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}k`
    return num.toString()
  }

  const barUsageRatio = totalTokens / CONTEXT_WINDOW
  const barColor = barUsageRatio > 0.8 ? colors.statusError
    : barUsageRatio > 0.5 ? colors.warning
    : colors.statusIdle

  const permissionDisplay = {
    ask:   { text: `${symbols.system} ask`,          color: colors.warning },
    allow: { text: `${symbols.system} bypass`,        color: colors.error },
    deny:  { text: `${symbols.system} deny`,          color: colors.success },
  }[permissionMode]

  const isCompact = width < 100

  if (!session) return null

  const verb = completed < 10 ? 'Baked' : completed < 60 ? 'Cooked' : 'Synthesized'

  return (
    <Box flexDirection="column">
      {/* Completion status — only visible after streaming ends */}
      {!isStreaming && completed > 0 && (
        <Box paddingX={2}>
          <Text color={colors.success}>{symbols.progressFrames[0]} </Text>
          <Text color={colors.success} bold>{verb}</Text>
          <Text color={colors.muted}> for </Text>
          <Text color={colors.timestamp}>
            {Math.floor(completed / 60)}m {completed % 60}s
          </Text>
          {tokensOut > 0 && (
            <>
              <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
              <Text color={colors.success}>↓ {formatNumber(tokensOut)} tokens</Text>
            </>
          )}
        </Box>
      )}

      {/* Bottom status bar */}
      <Box paddingX={2}>
        {/* Permission mode */}
        <Text color={permissionDisplay.color} bold>{permissionDisplay.text}</Text>

        {/* Agent count */}
        {agentCount > 0 && (
          <>
            <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
            <Text color={colors.statusRunning}>{agentCount} agent{agentCount !== 1 ? 's' : ''}</Text>
          </>
        )}

        <Text>  </Text>

        {/* Context usage */}
        <Text color={barColor}>
          {formatNumber(totalTokens)}/{formatNumber(CONTEXT_WINDOW)}
        </Text>

        {/* Token counters — compact mode: omit */}
        {!isCompact && (
          <>
            {tokensIn > 0 && (
              <>
                <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
                <Text color={colors.info}>↑{formatNumber(tokensIn)}</Text>
              </>
            )}
            {tokensOut > 0 && (
              <>
                <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
                <Text color={colors.success}>↓{formatNumber(tokensOut)}</Text>
              </>
            )}
            {cost > 0.01 && (
              <>
                <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
                <Text color={colors.timestamp}>${cost.toFixed(2)}</Text>
              </>
            )}
          </>
        )}

        {/* Keyboard hints */}
        <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
        {isCompact ? (
          <>
            <Text color={colors.shortcutKey}>esc</Text>
            <Text color={colors.shortcutDescription}> stop</Text>
          </>
        ) : (
          <>
            <Text color={colors.shortcutKey}>esc</Text>
            <Text color={colors.shortcutDescription}> stop</Text>
            <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
            <Text color={colors.shortcutKey}>ctrl+o</Text>
            <Text color={colors.shortcutDescription}> agents</Text>
            <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
            <Text color={colors.shortcutKey}>ctrl+k</Text>
            <Text color={colors.shortcutDescription}> commands</Text>
          </>
        )}
      </Box>
    </Box>
  )
})
