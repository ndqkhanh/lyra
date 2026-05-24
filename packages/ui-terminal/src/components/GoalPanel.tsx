import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'
import TextInput from 'ink-text-input'
import { colors } from '@lyra/ui-core'

interface GoalPanelProps {
  visible: boolean
  currentGoal: string | null
  onSetGoal: (goal: string) => void
  onClearGoal: () => void
  onClose: () => void
}

export function GoalPanel({ visible, currentGoal, onSetGoal, onClearGoal: _onClearGoal, onClose }: GoalPanelProps) {
  const [input, setInput] = useState('')

  useInput((_input, key) => {
    if (!visible) return
    if (key.escape) { onClose(); setInput(''); return }
  })

  const handleSubmit = () => {
    if (input.trim()) {
      onSetGoal(input.trim())
    }
    setInput('')
  }

  if (!visible) return null

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.info} padding={1} marginBottom={1}>
      <Text bold color={colors.info}>Goal Setting</Text>
      <Text dimColor>Set a completion condition. After each turn, the model checks if it's met.</Text>

      {currentGoal && (
        <Box marginY={1}>
          <Text color={colors.thinking}>Current goal: </Text>
          <Text color={colors.userPrompt}>{currentGoal}</Text>
        </Box>
      )}

      <Box marginTop={1}>
        <Text color={colors.userPrompt}>❯ </Text>
        <TextInput
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          placeholder={currentGoal ? 'Enter new goal or /goal clear to remove...' : 'Enter goal condition...'}
        />
      </Box>

      <Box marginTop={1}>
        <Text dimColor>/goal clear to remove  Esc to close</Text>
      </Box>
    </Box>
  )
}
