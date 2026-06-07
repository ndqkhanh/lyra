import React, { useState, useMemo } from 'react'
import { Box, Text, useInput } from 'ink'
import { useThemeColors } from '@lyra/ui-core'

interface Task {
  id: string
  subject: string
  status: 'pending' | 'in_progress' | 'completed'
}

interface TaskPanelProps {
  visible: boolean
  tasks: Task[]
  onClose: () => void
}

export function TaskPanel({ visible, tasks, onClose }: TaskPanelProps) {
  const colors = useThemeColors()
  const [selectedIndex, setSelectedIndex] = useState(0)

  const activeTasks = useMemo(
    () => tasks.filter(t => t.status !== 'completed').slice(0, 5),
    [tasks]
  )

  const completedCount = tasks.filter(t => t.status === 'completed').length
  const progress = tasks.length > 0 ? Math.round((completedCount / tasks.length) * 100) : 0

  useInput((_input, key) => {
    if (!visible) return
    if (key.escape) { onClose(); return }
    if (key.upArrow) { setSelectedIndex(p => Math.max(0, p - 1)); return }
    if (key.downArrow) { setSelectedIndex(p => Math.min(activeTasks.length - 1, p + 1)); return }
  })

  if (!visible) return null

  const statusIcon: Record<string, string> = {
    pending: '◯',
    in_progress: '◉',
    completed: '✓',
  }

  const statusColor: Record<string, string> = {
    pending: colors.timestamp,
    in_progress: colors.statusActive,
    completed: colors.success,
  }

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} height={14}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={colors.info}>Tasks ({tasks.length})</Text>
        <Text dimColor>Ctrl+T to toggle  Esc close</Text>
      </Box>

      <Box marginBottom={1}>
        <Text color={colors.info}>Progress: </Text>
        <Text color={progress === 100 ? colors.success : colors.warning}>
          {progress}% ({completedCount}/{tasks.length})
        </Text>
        <Text dimColor> {progress === 100 ? 'Done' : 'In progress'}</Text>
      </Box>

      <Box flexDirection="column" flexGrow={1}>
        {activeTasks.length === 0 && (
          <Text color={colors.muted}>No active tasks</Text>
        )}
        {activeTasks.map((task, i) => (
          <Box key={task.id}>
            <Text color={i === selectedIndex ? colors.userPrompt : colors.timestamp} bold={i === selectedIndex}>
              {i === selectedIndex ? '❯ ' : '  '}
            </Text>
            <Text color={statusColor[task.status]}>
              {statusIcon[task.status]}
            </Text>
            <Text> {task.subject}</Text>
          </Box>
        ))}
      </Box>
    </Box>
  )
}
