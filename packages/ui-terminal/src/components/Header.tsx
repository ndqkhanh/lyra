import React from 'react'
import { Box, Text } from 'ink'
import { useThemeColors } from '@lyra/ui-core'

interface HeaderProps {
  width: number
  model?: string
}

function formatModel(model: string): string {
  if (model.startsWith('deepseek-')) return model.replace('deepseek-', 'DeepSeek ').toUpperCase()
  if (model.startsWith('claude-')) return model.replace('claude-', 'Claude ').replace(/-/g, ' ')
  if (model.startsWith('gpt-')) return model.toUpperCase().replace('-', ' ')
  return model
}

// Hermes Banner — ASCII art with gold/amber/bronze gradient + tagline
export const Header = React.memo(function Header({
  width,
  model = 'Lyra',
}: HeaderProps) {
  const colors = useThemeColors()
  const displayModel = formatModel(model)
  const narrow = width < 50

  return (
    <Box flexDirection="column" marginBottom={1}>
      {narrow ? (
        <Text bold color={colors.thinking}>LYRA</Text>
      ) : (
        <Box flexDirection="column">
          <Box>
            <Text color={colors.thinking}>▐</Text>
            <Text color={colors.warning}>▛</Text>
            <Text color={colors.thinking}>▛</Text>
            <Text color={colors.warning}>███</Text>
            <Text color={colors.thinking}>▜▌</Text>
            <Text>   </Text>
            <Text bold color={colors.thinking}>LYRA</Text>
            <Text color={colors.muted}> v1.0.0</Text>
          </Box>
          <Box>
            <Text color={colors.warning}>▝</Text>
            <Text color={colors.thinking}>▜</Text>
            <Text color={colors.thinking}>▜</Text>
            <Text color={colors.warning}>█████</Text>
            <Text color={colors.thinking}>▛▘</Text>
            <Text>  </Text>
            <Text bold color={colors.info}>{displayModel}</Text>
            <Text color={colors.muted}> · 200K context</Text>
          </Box>
        </Box>
      )}

      {/* Tagline — matches Hermes "⚕ Nous Research · Messenger of the Digital Gods" */}
      <Text color={colors.muted}>⚕ Lyra · Harness AI Research</Text>
    </Box>
  )
})
