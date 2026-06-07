import React from 'react'
import { Box, Text, useInput } from 'ink'
import { useThemeColors, symbols } from '@lyra/ui-core'

interface ShortcutsHelpProps {
  visible: boolean
  onClose: () => void
}

interface ShortcutSection {
  title: string
  shortcuts: Array<{ key: string; description: string }>
}

const SHORTCUTS: ShortcutSection[] = [
  {
    title: 'Navigation',
    shortcuts: [
      { key: '↑/↓', description: 'Navigate command history' },
      { key: 'Ctrl+K', description: 'Open command palette' },
      { key: 'Ctrl+O', description: 'Toggle agent tree' },
      { key: 'Ctrl+L', description: 'Clear screen' },
    ],
  },
  {
    title: 'Input',
    shortcuts: [
      { key: 'Enter', description: 'Submit message' },
      { key: 'Shift+Enter', description: 'Insert newline' },
      { key: 'Tab', description: 'Accept autocomplete suggestion' },
      { key: 'Ctrl+C', description: 'Clear input' },
      { key: 'Ctrl+U', description: 'Clear input (Unix)' },
      { key: 'Esc', description: 'Close suggestions/dialogs' },
    ],
  },
  {
    title: 'Display',
    shortcuts: [
      { key: 'Ctrl+\\', description: 'Cycle display mode (minimal/standard/debug)' },
      { key: 'Shift+Tab', description: 'Cycle permission mode (ask/allow/deny)' },
    ],
  },
  {
    title: 'Vim Mode',
    shortcuts: [
      { key: '/vim', description: 'Enable Vim mode' },
      { key: 'Esc', description: 'Enter NORMAL mode' },
      { key: 'i/a/o/O', description: 'Enter INSERT mode' },
      { key: 'h/j/k/l', description: 'Navigate (NORMAL mode)' },
      { key: 'w/b', description: 'Word forward/back' },
      { key: 'x/d', description: 'Delete char/line' },
      { key: '0/$', description: 'Line start/end' },
    ],
  },
  {
    title: 'Commands',
    shortcuts: [
      { key: '/model', description: 'Switch AI model' },
      { key: '/theme', description: 'Change theme' },
      { key: '/effort', description: 'Set effort level' },
      { key: '/goal', description: 'Set session goal' },
      { key: '/help', description: 'Show this help' },
    ],
  },
  {
    title: 'System',
    shortcuts: [
      { key: 'Ctrl+D', description: 'Exit application' },
    ],
  },
]

/**
 * ShortcutsHelp - Display keyboard shortcuts reference
 *
 * Shows comprehensive list of keyboard shortcuts organized by category.
 * Helps users discover features and improve productivity.
 */
export function ShortcutsHelp({ visible, onClose }: ShortcutsHelpProps) {
  const colors = useThemeColors()

  // Handle Esc to close
  useInput((_input, key) => {
    if (!visible) return
    if (key.escape) {
      onClose()
    }
  })

  if (!visible) return null

  const terminalWidth = process.stdout.columns || 100
  const boxWidth = Math.min(80, terminalWidth - 4)

  return (
    <Box
      flexDirection="column"
      paddingX={2}
      marginBottom={1}
      borderStyle="round"
      borderColor={colors.info}
    >
      <Text color={colors.separator}>
        {symbols.horizontalLine.repeat(boxWidth)}
      </Text>

      {/* Title */}
      <Box flexDirection="column" paddingY={1}>
        <Text bold color={colors.info}>
          ⌨️  Keyboard Shortcuts
        </Text>
        <Text color={colors.muted}>
          Quick reference for all keyboard shortcuts and commands
        </Text>
      </Box>

      {/* Shortcuts by section */}
      <Box flexDirection="column">
        {SHORTCUTS.map((section, idx) => (
          <Box key={section.title} flexDirection="column" marginTop={idx > 0 ? 1 : 0}>
            <Text bold color={colors.amber}>
              {section.title}
            </Text>
            {section.shortcuts.map((shortcut) => (
              <Box key={shortcut.key} paddingLeft={2}>
                <Text color={colors.shortcutKey} bold>
                  {shortcut.key.padEnd(20)}
                </Text>
                <Text color={colors.shortcutDescription}>
                  {shortcut.description}
                </Text>
              </Box>
            ))}
          </Box>
        ))}
      </Box>

      {/* Footer */}
      <Box marginTop={1}>
        <Text color={colors.separator}>
          {symbols.horizontalLine.repeat(boxWidth)}
        </Text>
      </Box>
      <Box>
        <Text color={colors.shortcutKey}>Esc</Text>
        <Text color={colors.shortcutDescription}> to close · </Text>
        <Text color={colors.muted}>Type /help to show this again</Text>
      </Box>
    </Box>
  )
}
