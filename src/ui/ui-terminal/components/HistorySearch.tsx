import React, { useState, useMemo } from 'react'
import { Box, Text, useInput } from 'ink'
import { useThemeColors } from '@lyra/ui-core'

interface HistoryEntry {
  input: string
  timestamp: number
}

interface HistorySearchProps {
  visible: boolean
  history: HistoryEntry[]
  onSelect: (entry: string) => void
  onClose: () => void
}

export function HistorySearch({ visible, history, onSelect, onClose }: HistorySearchProps) {
  const colors = useThemeColors()
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)

  const filtered = useMemo(() => {
    if (!query.trim()) return history
    const q = query.toLowerCase()
    return history.filter(e => e.input.toLowerCase().includes(q))
  }, [history, query])

  useInput((input, key) => {
    if (!visible) return

    if (key.escape) { onClose(); return }
    if (key.upArrow || (key.ctrl && input === 'p')) {
      setSelectedIndex(p => Math.max(0, p - 1))
      return
    }
    if (key.downArrow || (key.ctrl && input === 'n')) {
      setSelectedIndex(p => Math.min(filtered.length - 1, p + 1))
      return
    }
    if (key.return) {
      if (filtered[selectedIndex]) {
        onSelect(filtered[selectedIndex].input)
      }
      return
    }
    if (key.backspace || key.delete) {
      setQuery(p => p.slice(0, -1))
      setSelectedIndex(0)
      return
    }
    if (input && !key.ctrl && !key.meta) {
      setQuery(p => p + input)
      setSelectedIndex(0)
    }
  })

  if (!visible) return null

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} height={16}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={colors.info}>History Search</Text>
        <Text dimColor>↑↓ navigate  Enter select  Esc close</Text>
      </Box>

      <Box marginBottom={1}>
        <Text color={colors.userPrompt}>search: </Text>
        <Text color={colors.thinking}>{query || ''}</Text>
        <Text dimColor>▏</Text>
      </Box>

      <Box flexDirection="column" flexGrow={1}>
        {filtered.length === 0 && (
          <Text color={colors.muted}>No matching history entries</Text>
        )}
        {filtered.slice(0, 12).map((entry, i) => (
          <Box key={`${entry.timestamp}-${i}`}>
            <Text color={i === selectedIndex ? colors.userPrompt : colors.timestamp} bold={i === selectedIndex}>
              {i === selectedIndex ? '❯ ' : '  '}
              {entry.input.slice(0, 80)}{entry.input.length > 80 ? '...' : ''}
            </Text>
          </Box>
        ))}
      </Box>

      <Box marginTop={1}>
        <Text dimColor>{filtered.length} entries</Text>
      </Box>
    </Box>
  )
}
