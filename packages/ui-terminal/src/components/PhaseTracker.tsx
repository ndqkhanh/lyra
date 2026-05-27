import React from 'react'
import { Box, Text } from 'ink'
import { useUIStore, colors, symbols } from '@lyra/ui-core'

interface PhaseTrackerProps {
  sessionId: string
  maxVisible?: number
}

export function PhaseTracker({ sessionId, maxVisible = 5 }: PhaseTrackerProps) {
  const session = useUIStore(state => state.sessions.get(sessionId))
  const phases = session?.phases ?? []

  if (phases.length === 0) return null

  const visible = phases.slice(0, maxVisible)
  const overflow = phases.length - maxVisible

  return (
    <Box flexDirection="column" paddingX={2} marginBottom={0}>
      {visible.map(phase => (
        <Box key={phase.id}>
          <Text>  </Text>
          <Text color={colors.shortcutKey}>{symbols.branch} </Text>
          <Text color={
            phase.status === 'completed' ? colors.statusSuccess
            : phase.status === 'active' ? colors.statusRunning
            : colors.muted
          }>
            {phase.status === 'completed' ? symbols.checkboxChecked
              : phase.status === 'active' ? symbols.checkboxChecked
              : symbols.checkbox}
          </Text>
          <Text> </Text>
          <Text color={
            phase.status === 'completed' ? colors.success
            : phase.status === 'active' ? colors.info
            : colors.muted
          } bold={phase.status === 'active'}>
            {phase.label}
          </Text>
        </Box>
      ))}
      {overflow > 0 && (
        <Box>
          <Text>  </Text>
          <Text color={colors.shortcutKey}>{symbols.branch} </Text>
          <Text color={colors.muted} dimColor>… +{overflow} pending</Text>
        </Box>
      )}
    </Box>
  )
}
