import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { colors } from '@lyra/ui-core'

interface Theme {
  name: string
  description: string
}

interface ThemePickerProps {
  visible: boolean
  themes: Theme[]
  currentTheme: string
  onSelect: (theme: string) => void
  onClose: () => void
}

const DEFAULT_THEMES: Theme[] = [
  { name: 'dracula', description: 'Purple-tinged dark theme (default)' },
  { name: 'nord', description: 'Cool arctic blue-toned theme' },
  { name: 'solarized-dark', description: 'Warm dark theme, high contrast' },
  { name: 'monokai', description: 'Vibrant syntax-highlighted theme' },
  { name: 'gruvbox-dark', description: 'Retro groove dark theme' },
  { name: 'one-dark', description: 'Atom-inspired dark theme' },
  { name: 'github-dark', description: 'GitHub\'s dark theme' },
  { name: 'tokyo-night', description: 'Neon-inspired night theme' },
]

export function ThemePicker({ visible, themes = DEFAULT_THEMES, currentTheme, onSelect, onClose }: ThemePickerProps) {
  const [selectedIndex, setSelectedIndex] = useState(0)

  useInput((_input, key) => {
    if (!visible) return
    if (key.upArrow) { setSelectedIndex(p => Math.max(0, p - 1)); return }
    if (key.downArrow) { setSelectedIndex(p => Math.min(themes.length - 1, p + 1)); return }
    if (key.return) { onSelect(themes[selectedIndex].name); return }
    if (key.escape) { onClose(); return }
  })

  if (!visible) return null

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} height={16}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={colors.info}>Theme Picker</Text>
        <Text dimColor>↑↓ navigate  Enter select  Esc close</Text>
      </Box>

      <Box marginBottom={1}>
        <Text dimColor>Current: </Text>
        <Text color={colors.success}>{currentTheme}</Text>
      </Box>

      <Box flexDirection="column" flexGrow={1}>
        {themes.map((theme, i) => (
          <Box key={theme.name}>
            <Text color={i === selectedIndex ? colors.userPrompt : colors.timestamp} bold={i === selectedIndex}>
              {i === selectedIndex ? '❯ ' : '  '}
              {theme.name === currentTheme ? '* ' : '  '}
              {theme.name.padEnd(16)}
            </Text>
            <Text dimColor>{theme.description}</Text>
          </Box>
        ))}
      </Box>
    </Box>
  )
}
