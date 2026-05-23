import React from 'react'
import { Box, Text } from 'ink'
import type { ToolExecutionItem } from '@lyra/ui-core'
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
    pending: 'yellow',
    running: 'cyan',
    success: 'green',
    error: 'red'
  }[item.status]

  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text color="green">⏺ </Text>
        {item.status === 'running' ? (
          <StreamingIndicator type="tool" label={item.toolName} />
        ) : (
          <>
            <Text color={statusColor}>{statusIcon} </Text>
            <Text bold color="cyan">{item.toolName}</Text>
          </>
        )}
        <Text dimColor>({JSON.stringify(item.args)})</Text>
      </Box>

      {item.result && (
        <Box marginLeft={2} flexDirection="column">
          <Text dimColor>  ⎿  </Text>
          {item.result.output.split('\n').length > 10 ? (
            <CollapsibleText content={item.result.output} maxLines={10} />
          ) : (
            <Text>{item.result.output}</Text>
          )}
          {item.result.error && (
            <Text color="red">Error: {item.result.error}</Text>
          )}
        </Box>
      )}
    </Box>
  )
}
