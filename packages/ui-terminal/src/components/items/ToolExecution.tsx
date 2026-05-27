import React, { useEffect } from 'react'
import { Box, Text } from 'ink'
import type { ToolExecutionItem } from '@lyra/ui-core'
import { useThemeColors, symbols, observability } from '@lyra/ui-core'
import { CollapsibleText } from '../Collapsible'
import { StreamingIndicator } from '../StreamingIndicator'
import { SyntaxHighlight } from '../SyntaxHighlight'

interface Props {
  item: ToolExecutionItem
  sessionId?: string
}

export const ToolExecution = React.memo(function ToolExecution({ item, sessionId }: Props) {
  const colors = useThemeColors()
  useEffect(() => {
    if (!sessionId) return
    if (item.status === 'running') {
      observability.emit({
        type: 'tool_start',
        timestamp: Date.now(),
        sessionId,
        data: { toolName: item.toolName, toolId: item.id }
      })
    } else if (item.status === 'success' || item.status === 'error') {
      observability.emit({
        type: 'tool_end',
        timestamp: Date.now(),
        sessionId,
        data: {
          toolName: item.toolName,
          toolId: item.id,
          error: item.status === 'error' ? item.result?.error : undefined
        }
      })
    }
  }, [item.status, item.toolName, item.id, sessionId])

  const statusIcon = {
    pending: symbols.pending,
    running: symbols.spinner[0],
    success: symbols.success,
    error: symbols.error
  }[item.status]

  const statusColor = {
    pending: colors.statusPending,
    running: colors.statusRunning,
    success: colors.statusSuccess,
    error: colors.error
  }[item.status]

  const isWriteTool = item.toolName === 'Write' || item.toolName === 'write'
  const isBashTool = item.toolName === 'Bash' || item.toolName === 'bash'
  const toolEmoji = {
    Write: '📝', write: '📝',
    Bash: '💻', bash: '💻',
    Read: '📖', read: '📖',
    Edit: '✏️', edit: '✏️',
    Grep: '🔍', grep: '🔍',
    WebFetch: '🌐', webfetch: '🌐',
    WebSearch: '🔎', websearch: '🔎',
  }[item.toolName] ?? '🔧'
  const outputLines = item.result?.output ? item.result.output.split('\n') : []

  return (
    <Box flexDirection="column" marginBottom={1}>
      {/* Tool header with Hermes-style emoji prefix */}
      <Box>
        <Text color={colors.success}>{toolEmoji} </Text>
        {item.status === 'running' ? (
          <StreamingIndicator type="tool" label={item.toolName} />
        ) : (
          <>
            <Text color={statusColor}>{statusIcon} </Text>
            <Text bold color={colors.toolName}>{item.toolName}</Text>
          </>
        )}
        {item.args && Object.keys(item.args).length > 0 && (
          <Text color={colors.muted} dimColor>
            ({Object.entries(item.args).map(([k, v]) =>
              k === 'filePath' || k === 'path' ? String(v) : `${k}=${JSON.stringify(v)}`
            ).join(', ')})
          </Text>
        )}
      </Box>

      {/* Tool output with tree branches */}
      {item.result && item.status !== 'running' && (
        <Box flexDirection="column" marginLeft={2}>
          {/* Result summary line: ⎿  Wrote 13 lines to path/to/file.py */}
          {isWriteTool && item.status === 'success' && (
            <Box>
              <Text color={colors.border}>  {symbols.branch}  </Text>
              <Text color={colors.success}>
                Wrote {outputLines.length} line{outputLines.length !== 1 ? 's' : ''} to{' '}
              </Text>
              <Text color={colors.filePath}>{String(item.args?.filePath || item.args?.path || '')}</Text>
            </Box>
          )}

          {/* Output preview with line numbers (first 5 lines) */}
          {outputLines.length > 0 && item.status === 'success' && (
            <Box flexDirection="column">
              {outputLines.slice(0, 5).map((line, i) => (
                <Box key={i}>
                  <Text color={colors.lineNumber} dimColor>
                    {String(i + 1).padStart(6)}  {' '}
                  </Text>
                  <Text color={colors.code}>{line}</Text>
                </Box>
              ))}
              {outputLines.length > 5 && (
                <Box>
                  <Text color={colors.muted} dimColor>       … </Text>
                  <Text color={colors.muted} dimColor>+{outputLines.length - 5} lines (ctrl+o to expand)</Text>
                </Box>
              )}
            </Box>
          )}

          {/* Bash output */}
          {isBashTool && outputLines.length > 0 && (
            <Box flexDirection="column">
              {outputLines.length > 10 ? (
                <CollapsibleText content={item.result.output} maxLines={10} />
              ) : (
                <SyntaxHighlight code={item.result.output} language="bash" showLineNumbers={false} />
              )}
            </Box>
          )}

          {/* Non-write, non-bash output */}
          {!isWriteTool && !isBashTool && outputLines.length > 0 && (
            <Box flexDirection="column">
              <Box>
                <Text color={colors.border}>  {symbols.branch}  </Text>
              </Box>
              {outputLines.length > 10 ? (
                <CollapsibleText content={item.result.output} maxLines={10} />
              ) : (
                <Text color={colors.code}>{item.result.output}</Text>
              )}
            </Box>
          )}

          {/* Error output */}
          {item.result.error && (
            <Box marginTop={1}>
              <Text color={colors.errorHigh} bold>
                {symbols.error} Error: {item.result.error}
              </Text>
            </Box>
          )}

        </Box>
      )}
    </Box>
  )
})
