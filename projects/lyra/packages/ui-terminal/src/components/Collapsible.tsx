import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'

interface CollapsibleProps {
  children: React.ReactNode
  collapsed?: boolean
  collapsedHeight?: number
  expandHint?: string
}

export function Collapsible({
  children,
  collapsed: initialCollapsed = false,
  collapsedHeight = 3,
  expandHint = 'ctrl+o to expand'
}: CollapsibleProps) {
  const [collapsed, setCollapsed] = useState(initialCollapsed)

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

  return (
    <Box flexDirection="column">
      {preview}
      {remaining > 0 && (
        <Box>
          <Text dimColor>… +{remaining} lines ({expandHint})</Text>
        </Box>
      )}
    </Box>
  )
}

interface CollapsibleTextProps {
  content: string
  maxLines?: number
  expandHint?: string
}

export function CollapsibleText({
  content,
  maxLines = 10,
  expandHint = 'ctrl+o to expand'
}: CollapsibleTextProps) {
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
        <Text dimColor>… +{remaining} lines ({expandHint})</Text>
      </Box>
    </Box>
  )
}
