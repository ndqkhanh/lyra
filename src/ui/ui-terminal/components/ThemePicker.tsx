import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { useThemeColors } from '@lyra/ui-core'

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
  { name: 'catppuccin_mocha', description: 'Soft pastel dark theme' },
  { name: 'tokyo_night_storm', description: 'Neon-inspired night theme' },
  { name: 'nord', description: 'Cool arctic blue-toned theme' },
  { name: 'dracula', description: 'Purple-tinged dark theme (default)' },
  { name: 'one_dark', description: 'Atom-inspired dark theme' },
  { name: 'gruvbox_dark_medium', description: 'Retro groove dark theme' },
  { name: 'selenized_dark', description: 'Warm dark, high contrast' },
  { name: 'everforest_dark', description: 'Nature-inspired low contrast' },
  { name: 'ayu_dark', description: 'Minimalist dark theme' },
  { name: 'rose_pine_moon', description: 'Dreamy moonlit theme' },
  { name: 'silk_circuit_neon', description: 'Cyberpunk neon circuit' },
  { name: 'sentry_sentinel_dark', description: 'Industrial security theme' },
]

export function ThemePicker({ visible, themes = DEFAULT_THEMES, currentTheme, onSelect, onClose }: ThemePickerProps) {
  const colors = useThemeColors()
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
