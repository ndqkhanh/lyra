import React, { useMemo } from 'react'
import { Box, Text } from 'ink'
import { useUIStore, useThemeColors } from '@lyra/ui-core'
import { RenderItemView } from './RenderItemView'

interface FocusModeProps {
  sessionId: string
  enabled: boolean
}

export function FocusMode({ sessionId, enabled }: FocusModeProps) {
  const colors = useThemeColors()
  const session = useUIStore(state => state.sessions.get(sessionId))
  const allItems = useUIStore(state => state.getRenderItems(sessionId))

  const focusItems = useMemo(() => {
    if (!enabled) return null

    const msgs = session?.messages ?? []
    if (msgs.length === 0) return []

    const lastUserIdx = [...msgs].reverse().findIndex(m => m.role === 'user')
    if (lastUserIdx === -1) return []

    const startIdx = msgs.length - 1 - lastUserIdx
    const focusMsgs = msgs.slice(startIdx)

    return allItems.filter(item =>
      focusMsgs.some(m => m.id === item.id || item.id.startsWith(m.id))
    )
  }, [allItems, session?.messages, enabled])

  if (!session || !enabled || !focusItems) return null

  return (
    <Box flexDirection="column" flexGrow={1} paddingX={2}>
      <Box marginBottom={1}>
        <Text color={colors.info} dimColor>Focus mode — showing last turn only</Text>
      </Box>

      {focusItems.length === 0 ? (
        <Text color={colors.emptyState}>No messages in this turn.</Text>
      ) : (
        focusItems.map(item => (
          <Box key={item.id} marginBottom={1}>
            <RenderItemView item={item} />
          </Box>
        ))
      )}
    </Box>
  )
}
