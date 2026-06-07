import React, { useState, useEffect } from 'react'
import { Box, Text, useInput } from 'ink'
import { useThemeColors, symbols } from '@lyra/ui-core'

interface CollapsibleProps {
  children: React.ReactNode
  collapsed?: boolean
  collapsedHeight?: number
  expandHint?: string
  animated?: boolean
}

export function Collapsible({
  children,
  collapsed: initialCollapsed = false,
  collapsedHeight = 3,
  expandHint = 'ctrl+o to expand',
  animated = true
}: CollapsibleProps) {
  const colors = useThemeColors()
  const [collapsed, setCollapsed] = useState(initialCollapsed)
  const [animationFrame, setAnimationFrame] = useState(0)

  // Animate expansion/collapse
  useEffect(() => {
    if (!animated) return

    const interval = setInterval(() => {
      setAnimationFrame(prev => (prev + 1) % 4)
    }, 200)

    return () => clearInterval(interval)
  }, [animated])

  useInput((input, key) => {
    if (key.ctrl && input === 'o') {
      setCollapsed(prev => !prev)
    }
  })

  if (!collapsed) {
    return <Box flexDirection="column">{children}</Box>
  }

  // Show preview lines
  const childArray = React.Children.toArray(children)
  const preview = childArray.slice(0, collapsedHeight)
  const remaining = childArray.length - collapsedHeight

  const animationSymbol = animated ? symbols.spinner[animationFrame] : symbols.ellipsis

  return (
    <Box flexDirection="column">
      {preview}
      {remaining > 0 && (
        <Box>
          <Text color={colors.collapsibleCollapsed}>
            {animationSymbol} +{remaining} lines
          </Text>
          <Text color={colors.shortcutSeparator}> · </Text>
          <Text color={colors.shortcutKey}>{expandHint}</Text>
        </Box>
      )}
    </Box>
  )
}

interface CollapsibleTextProps {
  content: string
  maxLines?: number
  expandHint?: string
  animated?: boolean
}

export function CollapsibleText({
  content,
  maxLines = 10,
  expandHint = 'ctrl+o to expand',
  animated: _animated = false
}: CollapsibleTextProps) {
  const colors = useThemeColors()
  const [collapsed, setCollapsed] = useState(true)

  useInput((input, key) => {
    if (key.ctrl && input === 'o') {
      setCollapsed(prev => !prev)
    }
  })

  const lines = content.split('\n')

  if (!collapsed || lines.length <= maxLines) {
    return (
      <Box flexDirection="column">
        {lines.map((line, idx) => (
          <Text key={idx}>{line}</Text>
        ))}
      </Box>
    )
  }

  const preview = lines.slice(0, maxLines)
  const remaining = lines.length - maxLines

  return (
    <Box flexDirection="column">
      {preview.map((line, idx) => (
        <Text key={idx}>{line}</Text>
      ))}
      <Box>
        <Text color={colors.collapsibleCollapsed}>
          {symbols.ellipsis} +{remaining} lines
        </Text>
        <Text color={colors.shortcutSeparator}> · </Text>
        <Text color={colors.shortcutKey}>{expandHint}</Text>
      </Box>
    </Box>
  )
}
