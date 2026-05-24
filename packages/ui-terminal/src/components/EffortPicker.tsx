import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { colors } from '@lyra/ui-core'

interface EffortPickerProps {
  visible: boolean
  onSelect: (level: string) => void
  onClose: () => void
}

const LEVELS = [
  { name: 'low', label: 'Low', desc: 'Quick answer, minimal analysis' },
  { name: 'medium', label: 'Medium', desc: 'Balanced speed & depth' },
  { name: 'high', label: 'High', desc: 'Thorough analysis' },
  { name: 'xhigh', label: 'Extra High', desc: 'Deep reasoning, multiple passes' },
  { name: 'max', label: 'Maximum', desc: 'Full depth, all tools enabled' },
]

export function EffortPicker({ visible, onSelect, onClose }: EffortPickerProps) {
  const [selectedIndex, setSelectedIndex] = useState(2)

  useInput((_input, key) => {
    if (!visible) return
    if (key.leftArrow || key.upArrow) { setSelectedIndex(p => Math.max(0, p - 1)); return }
    if (key.rightArrow || key.downArrow) { setSelectedIndex(p => Math.min(LEVELS.length - 1, p + 1)); return }
    if (key.return) { onSelect(LEVELS[selectedIndex].name); return }
    if (key.escape) { onClose(); return }
  })

  if (!visible) return null

  const barWidth = 30
  const ratio = selectedIndex / (LEVELS.length - 1)
  const filled = Math.round(ratio * barWidth)
  const empty = barWidth - filled

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} marginBottom={1}>
      <Text bold color={colors.info}>Effort Level</Text>
      <Text dimColor>← → to adjust  Enter to confirm  Esc to cancel</Text>

      <Box marginY={1}>
        <Text color={colors.timestamp}>Speed </Text>
        <Text color={colors.success}>{'▓'.repeat(filled)}</Text>
        <Text color={colors.timestamp}>{'░'.repeat(empty)}</Text>
        <Text color={colors.timestamp}> Intelligence</Text>
      </Box>

      <Box flexDirection="column">
        {LEVELS.map((level, i) => (
          <Box key={level.name}>
            <Text color={i === selectedIndex ? colors.userPrompt : colors.timestamp} bold={i === selectedIndex}>
              {i === selectedIndex ? '❯ ' : '  '}
              {level.label.padEnd(12)}
            </Text>
            <Text dimColor>{level.desc}</Text>
          </Box>
        ))}
      </Box>
    </Box>
  )
}
