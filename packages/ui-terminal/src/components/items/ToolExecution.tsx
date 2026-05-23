import React from 'react'
import { Box, Text } from 'ink'
import type { ToolExecutionItem } from '@lyra/ui-core'
import { colors, symbols } from '@lyra/ui-core'
import { CollapsibleText } from '../Collapsible'
import { StreamingIndicator } from '../StreamingIndicator'

interface Props {
  item: ToolExecutionItem
}

export function ToolExecution({ item }: Props) {
  const statusIcon = {
    pending: '⏳',
    running: '⚙️',
    success: '✅',
    error: '❌'
  }[item.status]

  const statusColor = {
    pending: colors.warning,
    running: colors.userPrompt,
    success: colors.success,
    error: colors.error
  }[item.status]

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text color={colors.assistant}>{symbols.assistant} </Text>
        {item.status === 'running' ? (
          <StreamingIndicator type="tool" label={item.toolName} />
        ) : (
          <>
            <Text color={statusColor}>{statusIcon} </Text>
            <Text bold color={colors.filePath}>{item.toolName}</Text>
          </>
        )}
        <Text color={colors.timestamp}>({JSON.stringify(item.args)})</Text>
      </Box>

      {item.result && (
        <Box marginLeft={2} flexDirection="column">
          <Text color={colors.lineNumber}>  {symbols.branch}  </Text>
          {item.result.output.split('\n').length > 10 ? (
            <CollapsibleText content={item.result.output} maxLines={10} />
          ) : (
            <Text>{item.result.output}</Text>
          )}
          {item.result.error && (
            <Text color={colors.error}>Error: {item.result.error}</Text>
          )}
        </Box>
      )}
    </Box>
  )
}
