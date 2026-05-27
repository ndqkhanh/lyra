import React, { useState, useEffect } from 'react'
import { Box, Text } from 'ink'
import { useThemeColors, symbols } from '@lyra/ui-core'

interface StreamingIndicatorProps {
  type: 'thinking' | 'tool' | 'flowing' | 'completed'
  duration?: number
  label?: string
  tokensIn?: number
  tokensOut?: number
  phase?: string
}

/**
 * Enhanced streaming indicator with time tracking, token counters, and phase display
 */
export function StreamingIndicator({
  type,
  duration,
  label,
  tokensIn = 0,
  tokensOut = 0,
  phase
}: StreamingIndicatorProps) {
  const colors = useThemeColors()
  const [frame, setFrame] = useState(0)
  const [elapsedTime, setElapsedTime] = useState(0)

  // Animate spinner
  useEffect(() => {
    if (type === 'completed') return

    const frames = type === 'flowing' ? symbols.thinkingFrames : symbols.spinner
    const interval = setInterval(() => {
      setFrame(prev => (prev + 1) % frames.length)
    }, type === 'flowing' ? 60 : 80)

    return () => clearInterval(interval)
  }, [type])

  // Track elapsed time
  useEffect(() => {
    if (type === 'completed') return

    const startTime = Date.now()
    const interval = setInterval(() => {
      setElapsedTime(Date.now() - startTime)
    }, 100)

    return () => clearInterval(interval)
  }, [type])

  const frames = type === 'flowing' ? symbols.thinkingFrames : symbols.spinner
  const currentFrame = frames[frame]

  const color = {
    thinking: colors.agentThinking,
    tool: colors.agentToolRunning,
    flowing: colors.agentStreaming,
    completed: colors.statusSuccess
  }[type]

  const icon = {
    thinking: currentFrame,
    tool: currentFrame,
    flowing: currentFrame,
    completed: '✳'
  }[type]

  // Format duration (ms → "5m 24s" or "2.3s")
  const formatDuration = (ms: number) => {
    const seconds = ms / 1000
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.floor(seconds % 60)

    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`
    } else if (seconds >= 1) {
      return `${seconds.toFixed(1)}s`
    } else {
      return `${(seconds * 1000).toFixed(0)}ms`
    }
  }

  // Format large numbers (9700 → 9.7k, 1200000 → 1.2M)
  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}k`
    }
    return num.toString()
  }

  const displayDuration = duration || elapsedTime

  return (
    <Box>
      <Text color={color}>{icon} </Text>

      {/* Phase or label */}
      {phase && <Text color={color}>{phase}</Text>}
      {!phase && label && <Text>{label}</Text>}

      {/* Duration */}
      {displayDuration > 0 && (
        <Text color={colors.timestamp}> ({formatDuration(displayDuration)})</Text>
      )}

      {/* Token counters (only show during streaming or when completed) */}
      {(type === 'flowing' || type === 'completed') && (tokensIn > 0 || tokensOut > 0) && (
        <>
          {tokensIn > 0 && (
            <>
              <Text color={colors.shortcutSeparator}> · </Text>
              <Text color={colors.info}>↑ {formatNumber(tokensIn)}</Text>
            </>
          )}
          {tokensOut > 0 && (
            <>
              <Text color={colors.shortcutSeparator}> · </Text>
              <Text color={colors.success}>↓ {formatNumber(tokensOut)}</Text>
            </>
          )}
        </>
      )}
    </Box>
  )
}

/**
 * Phase-aware streaming indicator that shows current operation
 */
export function PhaseIndicator({
  phase,
  duration
}: {
  phase: 'thinking' | 'tool' | 'streaming' | 'completed'
  duration?: number
}) {
  const phaseConfig = {
    thinking: {
      type: 'thinking' as const,
      label: 'Thinking...'
    },
    tool: {
      type: 'tool' as const,
      label: 'Running tool...'
    },
    streaming: {
      type: 'flowing' as const,
      label: 'Streaming response...'
    },
    completed: {
      type: 'completed' as const,
      label: 'Completed'
    }
  }[phase]

  return (
    <StreamingIndicator
      type={phaseConfig.type}
      label={phaseConfig.label}
      duration={duration}
    />
  )
}
