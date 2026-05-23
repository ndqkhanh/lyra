import React from 'react'
import { Box, Text, useInput } from 'ink'
import TextInput from 'ink-text-input'
import { useUIStore, colors, symbols } from '@lyra/ui-core'
import { useHistory } from '../hooks/useHistory'

interface InputAreaProps {
  sessionId: string
}

export function InputArea({ sessionId }: InputAreaProps) {
  const history = useHistory()
  const session = useUIStore(state => state.sessions.get(sessionId))
  const transport = useUIStore(state => state.transport)
  const addMessage = useUIStore(state => state.addMessage)

  // Handle arrow key navigation
  useInput((_input, key) => {
    if (key.upArrow) {
      history.navigateUp()
    } else if (key.downArrow) {
      history.navigateDown()
    }
  })

  const handleSubmit = () => {
    if (!history.current.trim() || !transport) return

    // Add to history
    history.addToHistory(history.current)

    // Add user message
    addMessage(sessionId, {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: history.current,
      timestamp: Date.now()
    })

    // Send via transport
    transport.sendMessage(history.current).catch(console.error)

    history.setCurrent('')
  }

  if (!session || session.isStreaming) {
    return (
      <Box borderStyle="single" borderColor={colors.border} paddingX={1}>
        <Text color={colors.timestamp}>Waiting for response...</Text>
      </Box>
    )
  }

  return (
    <Box flexDirection="column">
      <Box>
        <Text color={colors.separator}>{symbols.horizontalLine.repeat(80)}</Text>
      </Box>
      <Box borderStyle="single" borderColor={colors.userPrompt} paddingX={1}>
        <Text bold color={colors.userPrompt}>{symbols.userPrompt} </Text>
        <TextInput
          value={history.current}
          onChange={history.setCurrent}
          onSubmit={handleSubmit}
          placeholder="Type your message... (↑/↓ for history)"
        />
      </Box>
    </Box>
  )
}
