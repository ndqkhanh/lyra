import React from 'react'
import { Box, Text } from 'ink'
import { colors, symbols } from '@lyra/ui-core'

interface HeaderProps {
  version?: string
  model?: string
  mode?: string
  directory?: string
}

export function Header({
  version = '1.0.0',
  model = 'Opus 4.7 (1M context)',
  mode = 'Deep Research Mode',
  directory
}: HeaderProps) {
  const cwd = directory || process.cwd().replace(process.env.HOME || '', '~')

  return (
    <Box flexDirection="column" marginBottom={1}>
      {/* Logo + Version */}
      <Box>
        <Box flexDirection="column" marginRight={2}>
          {symbols.logo.map((line, i) => (
            <Text key={i} color={colors.userPrompt}>{line}</Text>
          ))}
        </Box>
        <Box flexDirection="column" justifyContent="center">
          <Text bold>Lyra v{version}</Text>
          <Text color={colors.timestamp}>
            {model} {symbols.separator} {mode}
          </Text>
          <Text color={colors.timestamp}>
            {cwd}
          </Text>
        </Box>
      </Box>

      {/* Separator */}
      <Box marginTop={1}>
        <Text color={colors.separator}>
          {symbols.horizontalLine.repeat(80)}
        </Text>
      </Box>
    </Box>
  )
}
