import React from 'react'
import { Box, Text } from 'ink'
import type { UserImageItem } from '@lyra/ui-core'
import { useThemeColors } from '@lyra/ui-core'

interface Props {
  item: UserImageItem
}

export function UserImageMessage({ item }: Props) {
  const colors = useThemeColors()
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text bold color={colors.userPrompt}>Image </Text>
        <Text color={colors.muted} dimColor>({item.mimeType})</Text>
      </Box>
      <Box marginLeft={2}>
        <Text color={colors.muted} dimColor>[{Math.ceil(item.data.length / 1024)} KB image data]</Text>
      </Box>
    </Box>
  )
}
