import React, { useState, useMemo } from 'react'
import { Box, Text, useInput } from 'ink'
import { useUIStore, useThemeColors } from '@lyra/ui-core'

interface RewindMenuProps {
  sessionId: string
  visible: boolean
  onClose: () => void
}

interface Checkpoint {
  index: number
  role: string
  preview: string
  timestamp: number
}

export function RewindMenu({ sessionId, visible, onClose }: RewindMenuProps) {
  const colors = useThemeColors()
  const session = useUIStore(state => state.sessions.get(sessionId))
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [showActions, setShowActions] = useState(false)

  const checkpoints: Checkpoint[] = useMemo(() => {
    if (!session) return []
    return session.messages
      .filter(m => m.role === 'user')
      .map((m, i) => ({
        index: i,
        role: m.role,
        preview: m.content.slice(0, 60) + (m.content.length > 60 ? '...' : ''),
        timestamp: m.timestamp,
      }))
  }, [session])

  const selectedCheckpoint = checkpoints[selectedIndex]

  useInput((_input, key) => {
    if (!visible) return
    if (key.escape) {
      if (showActions) { setShowActions(false); return }
      onClose()
      return
    }
    if (showActions) return

    if (key.upArrow) { setSelectedIndex(p => Math.max(0, p - 1)); return }
    if (key.downArrow) { setSelectedIndex(p => Math.min(checkpoints.length - 1, p + 1)); return }
    if (key.return) { setShowActions(true); return }
  })

  if (!visible || !session) return null

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} height={20}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={colors.info}>Rewind — {checkpoints.length} turns</Text>
        <Text dimColor>↑↓ navigate  Enter actions  Esc close</Text>
      </Box>

      {!showActions ? (
        <Box flexDirection="column" flexGrow={1}>
          {checkpoints.slice(-20).map((cp, i) => {
            const displayIdx = Math.max(0, checkpoints.length - 20) + i
            return (
              <Box key={cp.timestamp}>
                <Text color={displayIdx === selectedIndex ? colors.userPrompt : colors.timestamp} bold={displayIdx === selectedIndex}>
                  {displayIdx === selectedIndex ? '❯ ' : '  '}
                  Turn {displayIdx + 1}:
                </Text>
                <Text dimColor> {cp.preview}</Text>
              </Box>
            )
          })}
        </Box>
      ) : (
        <Box flexDirection="column" flexGrow={1}>
          <Text bold color={colors.thinking}>Actions for Turn {selectedIndex + 1}:</Text>
          <Text dimColor>{selectedCheckpoint?.preview}</Text>
          <Box flexDirection="column" marginTop={1}>
            <Text color={colors.userPrompt}>1. Restore code + conversation</Text>
            <Text color={colors.timestamp}>2. Restore conversation only</Text>
            <Text color={colors.timestamp}>3. Restore code only</Text>
            <Text color={colors.info}>4. Summarize from here</Text>
            <Text color={colors.muted}>5. Summarize up to here</Text>
          </Box>
          <Box marginTop={1}>
            <Text dimColor>Press 1-5 to select, Esc to go back</Text>
          </Box>
        </Box>
      )}
    </Box>
  )
}
