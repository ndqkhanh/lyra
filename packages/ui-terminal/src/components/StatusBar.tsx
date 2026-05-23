import React from 'react'
import { Box, Text } from 'ink'
import type { SessionState } from '@lyra/ui-core'

interface StatusBarProps {
  session: SessionState
}

export function StatusBar({ session }: StatusBarProps) {
  const messageCount = session.messages.length
  const mode = session.displayMode

  const modeColor = {
    minimal: 'white',
    standard: 'white',
    debug: 'yellow'
  }[mode]

  return (
    <Box borderStyle="single" borderColor="gray" paddingX={1} justifyContent="space-between">
      <Box>
        <Text dimColor>Session: </Text>
        <Text color="cyan">{session.id.slice(0, 8)}</Text>
      </Box>

      <Box>
        <Text dimColor>Messages: </Text>
        <Text>{messageCount}</Text>
      </Box>

      <Box>
        <Text dimColor>Mode: </Text>
        <Text color={modeColor}>{mode}</Text>
      </Box>

      <Box>
        <Text dimColor>Ctrl+\ cycle mode · Ctrl+C exit</Text>
      </Box>
    </Box>
  )
}
