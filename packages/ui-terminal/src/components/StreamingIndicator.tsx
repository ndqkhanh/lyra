import React, { useState, useEffect } from 'react'
import { Box, Text } from 'ink'
import { colors, symbols } from '@lyra/ui-core'

interface StreamingIndicatorProps {
  type: 'thinking' | 'tool' | 'flowing'
  duration?: number
  label?: string
}

export function StreamingIndicator({ type, duration, label }: StreamingIndicatorProps) {
  const [frame, setFrame] = useState(0)

  useEffect(() => {
    const frames = type === 'flowing' ? symbols.thinkingFrames : symbols.spinner
    const interval = setInterval(() => {
      setFrame(prev => (prev + 1) % frames.length)
    }, type === 'flowing' ? 60 : 80)

    return () => clearInterval(interval)
  }, [type])

  const frames = type === 'flowing' ? symbols.thinkingFrames : symbols.spinner
  const currentFrame = frames[frame]

  const color = {
    thinking: colors.thinking,
    tool: colors.userPrompt,
    flowing: colors.userPrompt
  }[type]

  const formatDuration = (ms?: number) => {
    if (!ms) return ''
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`
    }
    return `${seconds}s`
  }

  return (
    <Box>
      <Text color={color}>{currentFrame} </Text>
      {label && <Text>{label}</Text>}
      {duration && <Text color={colors.timestamp}> ({formatDuration(duration)})</Text>}
    </Box>
  )
}
