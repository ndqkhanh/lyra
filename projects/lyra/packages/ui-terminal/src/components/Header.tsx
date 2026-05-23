import React from 'react'
import { Box, Text } from 'ink'

export function Header() {
  const cwd = process.cwd().replace(process.env.HOME || '', '~')

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text color="cyan"> ▐▛███▜▌   </Text>
        <Text bold>Lyra v1.0.0</Text>
      </Box>
      <Box>
        <Text color="magenta">▝▜█████▛▘  </Text>
        <Text dimColor>Opus 4.7 (1M context) with xhigh effort · API Usage Billing</Text>
      </Box>
      <Box>
        <Text>  ▘▘ ▝▝    </Text>
        <Text color="cyan">{cwd}</Text>
      </Box>
      <Box marginTop={1}>
        <Text dimColor>{'─'.repeat(80)}</Text>
      </Box>
    </Box>
  )
}
