import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { colors } from '@lyra/ui-core'

interface OutputStylePickerProps {
  visible: boolean
  currentStyle: string
  onSelect: (style: string) => void
  onClose: () => void
}

const STYLES = [
  { name: 'default', label: 'Default', desc: 'Balanced, concise responses' },
  { name: 'proactive', label: 'Proactive', desc: 'Anticipates needs, suggests improvements' },
  { name: 'explanatory', label: 'Explanatory', desc: 'Detailed explanations, educational tone' },
  { name: 'learning', label: 'Learning', desc: 'Adapts to feedback, asks clarifying questions' },
]

export function OutputStylePicker({ visible, currentStyle, onSelect, onClose }: OutputStylePickerProps) {
  const [selectedIndex, setSelectedIndex] = useState(0)

  useInput((_input, key) => {
    if (!visible) return
    if (key.upArrow) { setSelectedIndex(p => Math.max(0, p - 1)); return }
    if (key.downArrow) { setSelectedIndex(p => Math.min(STYLES.length - 1, p + 1)); return }
    if (key.return) { onSelect(STYLES[selectedIndex].name); return }
    if (key.escape) { onClose(); return }
  })

  if (!visible) return null

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} marginBottom={1}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={colors.info}>Output Style</Text>
        <Text dimColor>↑↓ navigate  Enter select  Esc close</Text>
      </Box>

      <Box marginBottom={1}>
        <Text dimColor>Current: </Text>
        <Text color={colors.success}>{currentStyle}</Text>
        <Text dimColor> (takes effect on next /clear or new session)</Text>
      </Box>

      <Box flexDirection="column">
        {STYLES.map((style, i) => (
          <Box key={style.name}>
            <Text color={i === selectedIndex ? colors.userPrompt : colors.timestamp} bold={i === selectedIndex}>
              {i === selectedIndex ? '❯ ' : '  '}
              {style.name === currentStyle ? '* ' : '  '}
              {style.label.padEnd(14)}
            </Text>
            <Text dimColor>{style.desc}</Text>
          </Box>
        ))}
      </Box>
    </Box>
  )
}
