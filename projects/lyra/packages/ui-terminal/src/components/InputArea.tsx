import React, { useState } from 'react'
import { Box, Text } from 'ink'
import TextInput from 'ink-text-input'
import { useUIStore } from '@lyra/ui-core'

interface InputAreaProps {
  sessionId: string
}

export function InputArea({ sessionId }: InputAreaProps) {
  const [input, setInput] = useState('')
  const session = useUIStore(state => state.sessions.get(sessionId))
  const transport = useUIStore(state => state.transport)
  const addMessage = useUIStore(state => state.addMessage)

  const handleSubmit = () => {
    if (!input.trim() || !transport) return

    // Add user message
    addMessage(sessionId, {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: Date.now()
    })

    // Send via transport
    transport.sendMessage(input).catch(console.error)

    setInput('')
  }

  if (!session || session.isStreaming) {
    return (
      <Box borderStyle="single" borderColor="gray" paddingX={1}>
        <Text dimColor>Waiting for response...</Text>
      </Box>
    )
  }

  return (
    <Box flexDirection="column">
      <Box>
        <Text dimColor>{'─'.repeat(80)}</Text>
      </Box>
      <Box borderStyle="single" borderColor="cyan" paddingX={1}>
        <Text bold color="cyan">❯ </Text>
        <TextInput
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          placeholder="Type your message..."
        />
      </Box>
    </Box>
  )
}
