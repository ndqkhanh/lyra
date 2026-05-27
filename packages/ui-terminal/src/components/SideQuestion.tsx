import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'
import TextInput from 'ink-text-input'
import { useThemeColors } from '@lyra/ui-core'

interface SideQuestionProps {
  visible: boolean
  onSubmit: (question: string) => void
  onClose: () => void
}

export function SideQuestion({ visible, onSubmit, onClose }: SideQuestionProps) {
  const colors = useThemeColors()
  const [question, setQuestion] = useState('')
  const [submitted, setSubmitted] = useState(false)

  useInput((_input, key) => {
    if (!visible || submitted) return
    if (key.escape) { onClose(); setQuestion(''); setSubmitted(false); return }
  })

  const handleSubmit = () => {
    if (!question.trim()) return
    onSubmit(question.trim())
    setSubmitted(true)
  }

  if (!visible) return null

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.info} padding={1} marginBottom={1}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={colors.info}>Side Question</Text>
        <Text dimColor>Ephemeral — no history bloat  Esc to close</Text>
      </Box>

      {!submitted ? (
        <Box>
          <Text color={colors.userPrompt}>❯ </Text>
          <TextInput
            value={question}
            onChange={setQuestion}
            onSubmit={handleSubmit}
            placeholder="Ask a quick question..."
          />
        </Box>
      ) : (
        <Box flexDirection="column">
          <Text color={colors.userPrompt}>Q: {question}</Text>
          <Text color={colors.muted}>Side question sent. Response will appear inline.</Text>
        </Box>
      )}
    </Box>
  )
}
