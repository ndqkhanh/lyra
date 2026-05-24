import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { colors } from '@lyra/ui-core'

interface ScrollSpeedPickerProps {
  visible: boolean
  onSelect: (speed: number) => void
  onClose: () => void
}

const SPEEDS = [
  { label: 'Slow', value: 8, desc: '8 lines/sec' },
  { label: 'Medium', value: 16, desc: '16 lines/sec' },
  { label: 'Fast', value: 32, desc: '32 lines/sec' },
  { label: 'Very Fast', value: 64, desc: '64 lines/sec' },
  { label: 'Instant', value: 999, desc: 'No animation' },
]

export function ScrollSpeedPicker({ visible, onSelect, onClose }: ScrollSpeedPickerProps) {
  const [selectedIndex, setSelectedIndex] = useState(2)

  useInput((_input, key) => {
    if (!visible) return

    if (key.upArrow || key.leftArrow) {
      setSelectedIndex(prev => Math.max(0, prev - 1))
    } else if (key.downArrow || key.rightArrow) {
      setSelectedIndex(prev => Math.min(SPEEDS.length - 1, prev + 1))
    } else if (key.return) {
      onSelect(SPEEDS[selectedIndex].value)
    } else if (key.escape) {
      onClose()
    }
  })

  if (!visible) return null

  const barWidth = 40
  const ratio = (selectedIndex) / (SPEEDS.length - 1)
  const filled = Math.round(ratio * (barWidth - 2))
  const empty = barWidth - 2 - filled

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} marginBottom={1}>
      <Text bold color={colors.info}>Scroll Speed</Text>
      <Text dimColor>← → or ↑↓ to adjust  Enter to confirm  Esc to cancel</Text>

      <Box marginY={1}>
        <Text color={colors.timestamp}>Speed: </Text>
        <Box width={16}>
          <Text color={colors.statusIdle}>{'▓'.repeat(Math.max(0, filled / 8))}</Text>
          <Text color={colors.timestamp}>{'░'.repeat(Math.max(0, empty / 8))}</Text>
        </Box>
        <Text color={colors.timestamp}> </Text>
        <Text color={colors.thinking}>{'▶'.repeat(Math.max(1, selectedIndex + 1))}</Text>
      </Box>

      <Box flexDirection="column">
        {SPEEDS.map((speed, i) => (
          <Box key={speed.label}>
            <Text color={i === selectedIndex ? colors.userPrompt : colors.timestamp} bold={i === selectedIndex}>
              {i === selectedIndex ? '❯ ' : '  '}
              {speed.label.padEnd(12)}
            </Text>
            <Text dimColor>{speed.desc}</Text>
          </Box>
        ))}
      </Box>

      <Box marginTop={1}>
        <Text color={colors.timestamp}>Left: Speed</Text>
        <Box width={Math.floor(barWidth / 2) - 6}>
          <Text> </Text>
        </Box>
        <Text color={colors.timestamp}>Right: Intelligence</Text>
      </Box>
    </Box>
  )
}
