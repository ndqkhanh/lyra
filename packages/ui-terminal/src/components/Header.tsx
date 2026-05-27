import React from 'react'
import { Box, Text } from 'ink'
import { colors, symbols } from '@lyra/ui-core'

interface HeaderProps {
  width: number
  version?: string
  model?: string
  directory?: string
}

function formatModel(model: string): string {
  if (model.startsWith('deepseek-')) return model.replace('deepseek-', 'DeepSeek ').toUpperCase()
  if (model.startsWith('claude-')) return model.replace('claude-', 'Claude ').replace(/-/g, ' ')
  if (model.startsWith('gpt-')) return model.toUpperCase().replace('-', ' ')
  return model
}

function truncatePath(cwd: string, maxWidth: number): string {
  if (cwd.length <= maxWidth) return cwd
  const keepStart = Math.floor(maxWidth * 0.4)
  const keepEnd = Math.floor(maxWidth * 0.45)
  return cwd.slice(0, keepStart) + symbols.ellipsis + cwd.slice(-keepEnd)
}

function BlockBanner({ model, directory, width }: {
  model: string
  directory: string
  width: number
}) {
  const displayModel = formatModel(model)
  const cwd = truncatePath(directory, Math.min(width - 10, 80))

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text color={colors.keyword}>▐</Text>
        <Text color={colors.warning}>▛</Text>
        <Text color={colors.userPrompt}>███</Text>
        <Text color={colors.success}>▜▌</Text>
        <Text>   </Text>
        <Text bold color={colors.info}>LYRA</Text>
        <Text color={colors.muted}> v1.0.0</Text>
      </Box>
      <Box>
        <Text color={colors.keyword}>▝</Text>
        <Text color={colors.warning}>▜</Text>
        <Text color={colors.userPrompt}>█████</Text>
        <Text color={colors.success}>▛▘</Text>
        <Text>  </Text>
        <Text bold color={colors.info}>{displayModel}</Text>
        <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
        <Text color={colors.success}>200K context</Text>
        <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
        <Text color={colors.toolName}>Anthropic API</Text>
      </Box>
      <Box>
        <Text>  </Text>
        <Text color={colors.warning}>▘▘</Text>
        <Text> </Text>
        <Text color={colors.success}>▝▝</Text>
        <Text>    </Text>
        <Text color={colors.userPrompt}>{symbols.rightArrow} </Text>
        <Text color={colors.filePath}>{cwd}</Text>
      </Box>
    </Box>
  )
}

function CompactBanner({ model, directory, width }: {
  model: string
  directory: string
  width: number
}) {
  const displayModel = formatModel(model)
  const cwd = truncatePath(directory, Math.min(width - 6, 60))

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text color={colors.keyword}>▐▛</Text>
        <Text color={colors.userPrompt}>██</Text>
        <Text color={colors.success}>▜▌</Text>
        <Text>  </Text>
        <Text bold color={colors.info}>LYRA</Text>
      </Box>
      <Box>
        <Text color={colors.userPrompt}>{symbols.rightArrow} </Text>
        <Text bold color={colors.info}>{displayModel}</Text>
      </Box>
      <Box>
        <Text color={colors.userPrompt}>{symbols.rightArrow} </Text>
        <Text color={colors.filePath}>{cwd}</Text>
      </Box>
    </Box>
  )
}

// Pure stateless component — no useState/useEffect to avoid Ink re-render artifacts
export const Header = React.memo(function Header({
  width,
  model = 'Lyra',
  directory
}: HeaderProps) {
  const cwd = directory || process.cwd().replace(process.env.HOME || '', '~')

  if (width >= 50) {
    return <BlockBanner model={model} directory={cwd} width={width} />
  }
  return <CompactBanner model={model} directory={cwd} width={width} />
})

// Frozen variant — never re-renders after initial mount, preventing Ink output duplication
export const FrozenHeader = React.memo(
  function FrozenHeader({ width }: { width: number }) {
    return <Header width={width} />
  },
  () => true
)
