import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { colors } from '@lyra/ui-core'
import { COMMANDS, type Command } from '../constants/commands'

interface CommandPaletteProps {
  visible: boolean
  onSelect: (command: string) => void
  onClose: () => void
}

export function CommandPalette({ visible, onSelect, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)

  // Fuzzy search commands
  const filteredCommands = query
    ? COMMANDS.filter(cmd =>
        cmd.name.toLowerCase().includes(query.toLowerCase()) ||
        cmd.description.toLowerCase().includes(query.toLowerCase())
      )
    : COMMANDS

  // Group by category
  const groupedCommands = filteredCommands.reduce((acc, cmd) => {
    if (!acc[cmd.category]) {
      acc[cmd.category] = []
    }
    acc[cmd.category].push(cmd)
    return acc
  }, {} as Record<string, Command[]>)

  // Handle keyboard input
  useInput((input, key) => {
    if (!visible) return

    if (key.escape) {
      onClose()
      return
    }

    if (key.upArrow) {
      setSelectedIndex(prev => Math.max(0, prev - 1))
      return
    }

    if (key.downArrow) {
      setSelectedIndex(prev => Math.min(filteredCommands.length - 1, prev + 1))
      return
    }

    if (key.return) {
      if (filteredCommands[selectedIndex]) {
        onSelect(filteredCommands[selectedIndex].name)
        onClose()
      }
      return
    }

    if (key.backspace || key.delete) {
      setQuery(prev => prev.slice(0, -1))
      setSelectedIndex(0)
      return
    }

    if (input && !key.ctrl && !key.meta) {
      setQuery(prev => prev + input)
      setSelectedIndex(0)
    }
  })

  if (!visible) return null

  const width = 70
  const height = 20

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={colors.info}
      width={width}
      height={height}
      paddingX={1}
    >
      {/* Header */}
      <Box justifyContent="space-between" marginBottom={1}>
        <Text color={colors.info}>
          🔍 Search commands... <Text dimColor>{query || '(type to search)'}</Text>
        </Text>
        <Text color={colors.error} dimColor>[Esc]</Text>
      </Box>

      <Box borderStyle="single" borderColor={colors.separator} marginBottom={1} />

      {/* Results */}
      <Box flexDirection="column" flexGrow={1} overflow="hidden">
        {filteredCommands.length === 0 ? (
          <Text color={colors.timestamp} dimColor>No commands found</Text>
        ) : (
          Object.entries(groupedCommands).map(([category, commands]) => (
            <Box key={category} flexDirection="column" marginBottom={1}>
              <Text bold color={colors.info}>{category}</Text>
              {commands.map((cmd) => {
                const globalIndex = filteredCommands.indexOf(cmd)
                const isSelected = globalIndex === selectedIndex

                return (
                  <Box key={cmd.name}>
                    <Text color={isSelected ? colors.success : colors.userPrompt}>
                      {isSelected ? '▶' : ' '} {cmd.name.padEnd(20)}
                    </Text>
                    <Text color={colors.timestamp} dimColor>{cmd.description}</Text>
                  </Box>
                )
              })}
            </Box>
          ))
        )}
      </Box>

      {/* Footer */}
      <Box borderStyle="single" borderColor={colors.separator} marginTop={1} />
      <Box justifyContent="space-between">
        <Text color={colors.timestamp} dimColor>[↑↓ navigate]</Text>
        <Text color={colors.timestamp} dimColor>[Enter select]</Text>
        <Text color={colors.timestamp} dimColor>[Esc close]</Text>
      </Box>
    </Box>
  )
}
