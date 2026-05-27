import React, { useState, useEffect } from 'react'
import { Box, Text, useInput } from 'ink'
import { useThemeColors } from '@lyra/ui-core'

interface ChangelogEntry {
  version: string
  date: string
  highlights: string[]
}

interface ReleaseNotesPickerProps {
  visible: boolean
  onSelect: (version: string) => void
  onClose: () => void
}

const SERVER_URL = 'http://localhost:3737'

export function ReleaseNotesPicker({ visible, onSelect, onClose }: ReleaseNotesPickerProps) {
  const colors = useThemeColors()
  const [entries, setEntries] = useState<ChangelogEntry[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)

  useEffect(() => {
    if (!visible) return
    let cancelled = false
    fetch(`${SERVER_URL}/whats-new`)
      .then(r => r.json() as Promise<{ entries?: ChangelogEntry[] }>)
      .then(data => {
        if (!cancelled && data.entries?.length) setEntries(data.entries)
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [visible])

  useInput((_input, key) => {
    if (!visible) return
    if (key.upArrow) {
      setSelectedIndex(prev => Math.max(0, prev - 1))
    } else if (key.downArrow) {
      setSelectedIndex(prev => Math.min(entries.length - 1, prev + 1))
    } else if (key.return && entries.length > 0) {
      onSelect(entries[selectedIndex].version)
    } else if (key.escape) {
      onClose()
    }
  })

  if (!visible) return null

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} marginBottom={1}>
      <Text bold color={colors.info}>Release Notes — /release-notes</Text>
      <Text dimColor>↑↓ to navigate  Enter to select  Esc to close</Text>
      <Box flexDirection="column" marginTop={1}>
        {entries.length === 0 && (
          <Text color={colors.muted}>Loading changelog...</Text>
        )}
        {entries.map((entry, i) => (
          <Box key={entry.version} paddingLeft={1}>
            <Text color={i === selectedIndex ? colors.userPrompt : colors.timestamp} bold={i === selectedIndex}>
              {i === selectedIndex ? '❯ ' : '  '}
              [{entry.version}] — {entry.date}
            </Text>
          </Box>
        ))}
      </Box>
      {entries[selectedIndex] && (
        <Box flexDirection="column" marginTop={1} paddingLeft={2}>
          <Text bold color={colors.thinking}>Highlights for {entries[selectedIndex].version}:</Text>
          {entries[selectedIndex].highlights.map((h, i) => (
            <Text key={i} color={colors.muted}>  • {h}</Text>
          ))}
        </Box>
      )}
    </Box>
  )
}
