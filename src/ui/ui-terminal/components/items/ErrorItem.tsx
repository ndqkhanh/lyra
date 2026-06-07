import React from 'react'
import { Box, Text } from 'ink'
import type { ErrorItem as ErrorItemType } from '@lyra/ui-core'
import { useThemeColors, symbols } from '@lyra/ui-core'

interface Props {
  item: ErrorItemType
}

export function ErrorItem({ item }: Props) {
  const colors = useThemeColors()
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text color={colors.error} bold>{symbols.error} Error</Text>
      </Box>
      <Box marginLeft={2}>
        <Text color={colors.error}>{item.message}</Text>
      </Box>
      {item.stack && (
        <Box marginLeft={2}>
          <Text color={colors.muted} dimColor>{item.stack}</Text>
        </Box>
      )}
    </Box>
  )
}
