import React from 'react'
import { Box, Text } from 'ink'
import type { SessionState } from '@lyra/ui-core'
import { colors, symbols } from '@lyra/ui-core'

interface StatusBarProps {
  session: SessionState
}

export function StatusBar({ session }: StatusBarProps) {
  const messageCount = session.messages.length
  const mode = session.displayMode

  const modeColor = {
    minimal: colors.code,
    standard: colors.code,
    debug: colors.thinking
  }[mode]

  return (
    <Box borderStyle="single" borderColor={colors.border} paddingX={1} justifyContent="space-between">
      <Box>
        <Text color={colors.timestamp}>Session: </Text>
        <Text color={colors.userPrompt}>{session.id.slice(0, 8)}</Text>
      </Box>

      <Box>
        <Text color={colors.timestamp}>Messages: </Text>
        <Text>{messageCount}</Text>
      </Box>

      <Box>
        <Text color={colors.timestamp}>Mode: </Text>
        <Text color={modeColor}>{mode}</Text>
      </Box>

      <Box>
        <Text color={colors.timestamp}>Ctrl+\ cycle mode {symbols.separator} Ctrl+C exit</Text>
      </Box>
    </Box>
  )
}
