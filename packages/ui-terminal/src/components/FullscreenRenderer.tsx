import React, { useState, useMemo, useEffect } from 'react'
import { Box, Text, useInput } from 'ink'
import { useUIStore, applyDisplayPolicy, partitionRenderItems, colors } from '@lyra/ui-core'
import { RenderItemView } from './RenderItemView'

interface FullscreenRendererProps {
  sessionId: string
  enabled: boolean
}

export function FullscreenRenderer({ sessionId, enabled }: FullscreenRendererProps) {
  const session = useUIStore(state => state.sessions.get(sessionId))
  const [scrollOffset, setScrollOffset] = useState(0)
  const [autoFollow, setAutoFollow] = useState(true)
  const [viewportHeight, setViewportHeight] = useState(process.stdout.rows || 40)

  const allItems = useUIStore(state => state.getRenderItems(sessionId))
  const policyItems = useMemo(
    () => (session ? applyDisplayPolicy(allItems, session.displayMode) : allItems),
    [allItems, session]
  )
  const { staticItems, liveItems } = partitionRenderItems(policyItems)
  const allVisible = [...staticItems, ...liveItems]

  useEffect(() => {
    const onResize = () => setViewportHeight(process.stdout.rows || 40)
    process.stdout.on('resize', onResize)
    return () => { process.stdout.off('resize', onResize) }
  }, [])

  useEffect(() => {
    if (autoFollow) setScrollOffset(0)
  }, [allVisible.length, autoFollow])

  const maxOffset = Math.max(0, allVisible.length - viewportHeight + 8)

  useInput((input, key) => {
    if (!enabled) return

    if (key.upArrow) {
      setScrollOffset(prev => {
        const next = Math.min(maxOffset, prev + 1)
        if (next > 0) setAutoFollow(false)
        return next
      })
      return
    }
    if (key.downArrow) {
      setScrollOffset(prev => {
        const next = Math.max(0, prev - 1)
        if (next === 0) setAutoFollow(true)
        return next
      })
      return
    }
    if (key.pageUp) {
      setScrollOffset(prev => {
        const next = Math.min(maxOffset, prev + Math.floor(viewportHeight / 2))
        if (next > 0) setAutoFollow(false)
        return next
      })
      return
    }
    if (key.pageDown) {
      setScrollOffset(prev => {
        const next = Math.max(0, prev - Math.floor(viewportHeight / 2))
        if (next === 0) setAutoFollow(true)
        return next
      })
      return
    }
    if (input === 'G' && !key.ctrl) {
      setScrollOffset(maxOffset)
      setAutoFollow(false)
      return
    }
    if (key.return && key.ctrl) {
      setScrollOffset(0)
      setAutoFollow(true)
      return
    }
  })

  if (!session || !enabled) return null

  const visibleItems = allVisible.slice(scrollOffset, scrollOffset + viewportHeight - 8)

  return (
    <Box flexDirection="column" flexGrow={1}>
      {scrollOffset > 0 && (
        <Box paddingX={2}>
          <Text color={colors.timestamp} dimColor>
            ↑ {scrollOffset} messages above (PgUp/PgDn to scroll, Ctrl+Enter to follow)
          </Text>
        </Box>
      )}

      <Box flexDirection="column" flexGrow={1} paddingX={2}>
        {visibleItems.length === 0 && (
          <Box marginY={1}>
            <Text color={colors.emptyState}>No messages yet. Type a message below to start.</Text>
          </Box>
        )}

        {visibleItems.map(item => (
          <Box key={item.id} marginBottom={1}>
            <RenderItemView item={item} />
          </Box>
        ))}
      </Box>

      {!autoFollow && scrollOffset > 0 && (
        <Box paddingX={2} marginBottom={1}>
          <Text color={colors.info} dimColor>
            Auto-scroll paused — Ctrl+Enter or scroll down to follow
          </Text>
        </Box>
      )}
    </Box>
  )
}
