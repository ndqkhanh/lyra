import React, { useState, useEffect } from 'react'
import { Box, Text } from 'ink'
import { colors, symbols } from '@lyra/ui-core'
import { useTips, useWhatsNew } from '../hooks/useContent'

interface HeaderProps {
  version?: string
  model?: string
  mode?: string
  directory?: string
}

interface LayoutProps {
  version: string
  model: string
  mode: string
  cwd: string
  width: number
}

/**
 * Enhanced header with Claude Code style rounded borders
 * Responsive layout: wide (>120), standard (80-120), compact (<80)
 */

function truncatePath(cwd: string, maxWidth: number): string {
  if (cwd.length <= maxWidth) return cwd
  const keepStart = Math.floor(maxWidth * 0.45)
  const keepEnd = Math.floor(maxWidth * 0.40)
  return cwd.slice(0, keepStart) + '...' + cwd.slice(-keepEnd)
}

export function Header({
  version = '1.0.0',
  model = 'Opus 4.7 (1M context)',
  mode = 'Deep Research Mode',
  directory
}: HeaderProps) {
  const cwd = directory || process.cwd().replace(process.env.HOME || '', '~')
  const [terminalWidth, setTerminalWidth] = useState(process.stdout.columns || 120)

  useEffect(() => {
    const handleResize = () => {
      setTerminalWidth(process.stdout.columns || 120)
    }
    process.stdout.on('resize', handleResize)
    return () => {
      process.stdout.off('resize', handleResize)
    }
  }, [])

  // Determine layout based on terminal width
  if (terminalWidth > 120) {
    return <WideHeader version={version} model={model} mode={mode} cwd={cwd} width={terminalWidth} />
  } else if (terminalWidth > 80) {
    return <StandardHeader version={version} model={model} mode={mode} cwd={cwd} width={terminalWidth} />
  } else {
    return <CompactHeader version={version} model={model} mode={mode} cwd={cwd} width={terminalWidth} />
  }
}

/**
 * Wide layout (>120 cols): Two-column with tips sidebar
 */
function WideHeader({ model, mode, cwd, width }: LayoutProps) {
  const { currentTip } = useTips(25_000)
  const { entries: changelog } = useWhatsNew()
  const contentWidth = Math.min(width - 4, 120)
  const topBorder = '╭─' + '─'.repeat(contentWidth - 2) + '╮'
  const bottomBorder = '╰─' + '─'.repeat(contentWidth - 2) + '╯'
  const emptyLine = '│' + ' '.repeat(contentWidth - 2) + '│'

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text color={colors.separator}>{topBorder}</Text>
      <Text color={colors.separator}>{emptyLine}</Text>

      {/* Main content area */}
      <Box>
        <Text color={colors.separator}>{'│'} </Text>
        <Box flexDirection="column" width={Math.floor(contentWidth * 0.6)}>
          <Text bold color={colors.success}>                Welcome back!</Text>
          <Box marginTop={1} flexDirection="column">
            {symbols.logo.map((line, i) => (
              <Text key={i} color={colors.userPrompt}>                  {line}</Text>
            ))}
          </Box>
          <Box marginTop={1}>
            <Text bold color={colors.info}>{model}</Text>
            <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
            <Text bold color={colors.thinking}>{mode}</Text>
          </Box>
          <Text color={colors.filePath}>  {truncatePath(cwd, Math.floor(contentWidth * 0.55))}</Text>
        </Box>

        {/* Tips sidebar — dynamic */}
        <Box flexDirection="column" width={Math.floor(contentWidth * 0.35)} paddingLeft={2}>
          <Text bold color={colors.info}>Tips for getting started</Text>
          <Text color={colors.muted}>{currentTip.description}</Text>
          <Text color={colors.separator}>{'─'.repeat(25)}</Text>
          <Text bold color={colors.info}>What&apos;s new</Text>
          {changelog.slice(0, 2).map((entry, i) => (
            <Text key={i} color={colors.muted}>
              {entry.version} — {entry.highlights[0] ?? ''}
            </Text>
          ))}
          <Text color={colors.muted}>/release-notes for more</Text>
        </Box>

        <Text color={colors.separator}> {'│'}</Text>
      </Box>

      <Text color={colors.separator}>{emptyLine}</Text>
      <Text color={colors.separator}>{bottomBorder}</Text>
    </Box>
  )
}

/**
 * Standard layout (80-120 cols): Single column
 */
function StandardHeader({ model, mode, cwd, width }: LayoutProps) {
  const contentWidth = Math.min(width - 4, 80)
  const topBorder = '╭─' + '─'.repeat(contentWidth - 2) + '╮'
  const bottomBorder = '╰─' + '─'.repeat(contentWidth - 2) + '╯'
  const emptyLine = '│' + ' '.repeat(contentWidth - 2) + '│'

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text color={colors.separator}>{topBorder}</Text>
      <Text color={colors.separator}>{emptyLine}</Text>

      <Box>
        <Text color={colors.separator}>│ </Text>
        <Box flexDirection="column" width={contentWidth - 4}>
          <Text bold color={colors.success}>                    Welcome back!</Text>
          <Box marginTop={1} flexDirection="column">
            {symbols.logo.map((line, i) => (
              <Text key={i} color={colors.userPrompt}>                      {line}</Text>
            ))}
          </Box>
          <Box marginTop={1}>
            <Text bold color={colors.info}>{model}</Text>
            <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
            <Text bold color={colors.thinking}>{mode}</Text>
          </Box>
          <Text color={colors.filePath}>  {truncatePath(cwd, contentWidth - 8)}</Text>
        </Box>
        <Text color={colors.separator}> │</Text>
      </Box>

      <Text color={colors.separator}>{emptyLine}</Text>
      <Text color={colors.separator}>{bottomBorder}</Text>
    </Box>
  )
}

/**
 * Compact layout (<80 cols): Minimal version
 */
function CompactHeader({ version, model, cwd, width }: LayoutProps) {
  const contentWidth = Math.min(width - 4, 60)
  const topBorder = '╭─' + '─'.repeat(contentWidth - 2) + '╮'
  const bottomBorder = '╰─' + '─'.repeat(contentWidth - 2) + '╯'

  // Truncate long strings for compact view
  const truncatedModel = model.length > contentWidth - 6 ? model.slice(0, contentWidth - 9) + '...' : model
  const truncatedCwd = cwd.length > contentWidth - 6 ? '...' + cwd.slice(-(contentWidth - 9)) : cwd

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text color={colors.separator}>{topBorder}</Text>

      <Box>
        <Text color={colors.separator}>│ </Text>
        <Box flexDirection="column" width={contentWidth - 4}>
          <Text bold color={colors.success}>Lyra v{version}</Text>
          <Text bold color={colors.info}>{truncatedModel}</Text>
          <Text color={colors.filePath}>{truncatedCwd}</Text>
        </Box>
        <Text color={colors.separator}> │</Text>
      </Box>

      <Text color={colors.separator}>{bottomBorder}</Text>
    </Box>
  )
}
