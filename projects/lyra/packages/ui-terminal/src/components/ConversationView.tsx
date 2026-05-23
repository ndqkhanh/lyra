import React, { useMemo } from 'react'
import { Box, Static } from 'ink'
import { useUIStore, applyDisplayPolicy, partitionRenderItems } from '@lyra/ui-core'
import { RenderItemView } from './RenderItemView'

interface ConversationViewProps {
  sessionId: string
}

export function ConversationView({ sessionId }: ConversationViewProps) {
  const session = useUIStore(state => state.sessions.get(sessionId))

  if (!session) return null

  // Generate render items
  const allItems = useUIStore(state => state.getRenderItems(sessionId))

  // Apply display policy
  const policyItems = useMemo(
    () => applyDisplayPolicy(allItems, session.displayMode),
    [allItems, session.displayMode]
  )

  // Partition into static (committed) and live (preview) zones
  const { staticItems, liveItems } = partitionRenderItems(policyItems)

  return (
    <Box flexDirection="column" flexGrow={1}>
      {/* STATIC ZONE - Written once to scrollback, never redrawn */}
      {staticItems.length > 0 && (
        <Static items={staticItems}>
          {(item) => <RenderItemView key={item.id} item={item} />}
        </Static>
      )}

      {/* LIVE ZONE - Redraws every frame for streaming */}
      <Box flexDirection="column">
        {liveItems.map(item => (
          <RenderItemView key={item.id} item={item} />
        ))}
      </Box>
    </Box>
  )
}
