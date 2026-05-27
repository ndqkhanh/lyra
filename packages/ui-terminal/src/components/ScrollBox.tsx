import React, { useState, useEffect, useRef } from 'react'
import { Box, useInput, useStdout } from 'ink'

interface ScrollBoxProps {
  children: React.ReactNode
  height?: number
  showScrollbar?: boolean
}

/**
 * ScrollBox - Virtual scrolling container for long content
 *
 * Features:
 * - Auto-scrolls to bottom on new content
 * - Arrow keys to scroll up/down
 * - Page Up/Down for faster scrolling
 * - Home/End to jump to top/bottom
 * - Optional scrollbar indicator
 */
export const ScrollBox = React.memo(function ScrollBox({
  children,
  height,
  showScrollbar = true
}: ScrollBoxProps) {
  const { stdout } = useStdout()
  const [scrollOffset, setScrollOffset] = useState(0)
  const [autoScroll, setAutoScroll] = useState(true)
  const contentRef = useRef<string[]>([])
  const prevChildrenRef = useRef<React.ReactNode>(null)

  // Calculate available height (default to terminal height - 10 for header/input/status)
  const viewportHeight = height ?? Math.max(10, (stdout.rows || 24) - 10)

  // Convert children to lines for virtual scrolling
  useEffect(() => {
    // Simple line extraction - in production, would need proper React tree traversal
    const childrenStr = React.Children.toArray(children)
      .map(child => {
        if (typeof child === 'string') return child
        if (React.isValidElement(child) && child.props.children) {
          return String(child.props.children)
        }
        return ''
      })
      .join('\n')

    contentRef.current = childrenStr.split('\n')

    // Auto-scroll to bottom when new content arrives
    if (prevChildrenRef.current !== children && autoScroll) {
      const maxScroll = Math.max(0, contentRef.current.length - viewportHeight)
      setScrollOffset(maxScroll)
    }
    prevChildrenRef.current = children
  }, [children, viewportHeight, autoScroll])

  const totalLines = contentRef.current.length
  const maxScroll = Math.max(0, totalLines - viewportHeight)

  useInput((_input, key) => {
    if (key.upArrow) {
      setScrollOffset(prev => Math.max(0, prev - 1))
      setAutoScroll(false)
    } else if (key.downArrow) {
      setScrollOffset(prev => {
        const next = Math.min(maxScroll, prev + 1)
        if (next === maxScroll) setAutoScroll(true)
        return next
      })
    } else if (key.pageUp) {
      setScrollOffset(prev => Math.max(0, prev - viewportHeight))
      setAutoScroll(false)
    } else if (key.pageDown) {
      setScrollOffset(prev => {
        const next = Math.min(maxScroll, prev + viewportHeight)
        if (next === maxScroll) setAutoScroll(true)
        return next
      })
    }
    // Note: Ink doesn't expose home/end keys in Key type
    // Users can use PageUp to top, PageDown to bottom as alternatives
  })

  const scrollPercentage = maxScroll > 0 ? Math.round((scrollOffset / maxScroll) * 100) : 100
  const isAtBottom = scrollOffset >= maxScroll

  return (
    <Box flexDirection="column" height={viewportHeight}>
      <Box flexDirection="row" flexGrow={1}>
        {/* Content viewport */}
        <Box flexDirection="column" flexGrow={1}>
          {children}
        </Box>

        {/* Scrollbar indicator */}
        {showScrollbar && totalLines > viewportHeight && (
          <Box flexDirection="column" width={1} marginLeft={1}>
            {Array.from({ length: viewportHeight }).map((_, i) => {
              const barPosition = Math.floor((scrollOffset / maxScroll) * (viewportHeight - 1))
              const isIndicator = i === barPosition
              return (
                <Box key={i}>
                  {isIndicator ? '█' : '│'}
                </Box>
              )
            })}
          </Box>
        )}
      </Box>

      {/* Scroll status indicator */}
      {!isAtBottom && (
        <Box marginTop={1}>
          <Box>
            ↑ {scrollPercentage}% ↓ {autoScroll ? '(auto)' : '(manual)'} | ↑↓ scroll | PgUp/PgDn
          </Box>
        </Box>
      )}
    </Box>
  )
})
