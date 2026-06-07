"""
Fleet View — terminal UI for managing background agent sessions.

Implements the §4.13 Agent View port: one screen showing every session's
state, grouped by task-state (Working / Needs Input / Completed), with
cheap-model row summaries and steer-by-exception peek/reply.

Uses Ink (React for terminal) — the same framework as Lyra's existing TUI.

References
----------
- Claude Code Agent View: https://code.claude.com/docs/en/agent-view
- Lyra §4.13 Swarm/Fleet Plan: plans/4.13-swarm-fleet.md
"""

import React, { useState, useEffect, useCallback } from 'react'
import { Box, Text, useInput, useApp } from 'ink'

// ---------------------------------------------------------------------------
// Types — mirrors supervisor state model (orthogonal axes)
// ---------------------------------------------------------------------------

type TaskState = 'WORKING' | 'IDLE' | 'NEEDS_INPUT' | 'COMPLETED' | 'FAILED' | 'STOPPED'

type ProcessState = 'ALIVE' | 'EXITED' | 'LOOP_SLEEPING'

interface FleetSession {
  sessionId: string
  name: string
  taskState: TaskState
  processState: ProcessState
  summary: string
  workingDir: string
  modelName: string
  prUrl?: string
  lastActive: string // ISO timestamp
}

interface FleetViewProps {
  sessions: FleetSession[]
  onAttach: (sessionId: string) => void
  onStop: (sessionId: string) => void
  onDispatch: (command: string) => void
  onRefresh: () => void
}

// ---------------------------------------------------------------------------
// State grouping (Agent View groups)
// ---------------------------------------------------------------------------

type SessionGroup = 'needs-input' | 'working' | 'completed'

function groupSessions(sessions: FleetSession[]): Record<SessionGroup, FleetSession[]> {
  const groups: Record<SessionGroup, FleetSession[]> = {
    'needs-input': [],
    'working': [],
    'completed': [],
  }

  for (const s of sessions) {
    if (s.taskState === 'NEEDS_INPUT') {
      groups['needs-input'].push(s)
    } else if (s.taskState === 'COMPLETED' || s.taskState === 'FAILED' || s.taskState === 'STOPPED') {
      groups['completed'].push(s)
    } else {
      groups['working'].push(s)
    }
  }

  return groups
}

// ---------------------------------------------------------------------------
// Process liveness indicator
// ---------------------------------------------------------------------------

interface LivenessDotProps {
  processState: ProcessState
}

function LivenessDot({ processState }: LivenessDotProps): React.ReactElement {
  const colorMap: Record<ProcessState, string> = {
    ALIVE: 'green',
    EXITED: 'red',
    LOOP_SLEEPING: 'yellow',
  }

  const symbolMap: Record<ProcessState, string> = {
    ALIVE: '●',
    EXITED: '○',
    LOOP_SLEEPING: '◐',
  }

  return (
    <Text color={colorMap[processState]}>
      {symbolMap[processState]}
    </Text>
  )
}

// ---------------------------------------------------------------------------
// Session row
// ---------------------------------------------------------------------------

interface SessionRowProps {
  session: FleetSession
  isSelected: boolean
  onSelect: () => void
}

function SessionRow({ session, isSelected, onSelect }: SessionRowProps): React.ReactElement {
  const highlight = isSelected ? { inverse: true } : {}

  const stateColorMap: Record<TaskState, string> = {
    WORKING: 'blue',
    IDLE: 'gray',
    NEEDS_INPUT: 'yellow',
    COMPLETED: 'green',
    FAILED: 'red',
    STOPPED: 'gray',
  }

  return (
    <Box flexDirection="row" {...highlight}>
      <Box width={2}>
        <LivenessDot processState={session.processState} />
      </Box>
      <Box width={3}>
        <Text color={stateColorMap[session.taskState]}>
          {session.taskState.slice(0, 3)}
        </Text>
      </Box>
      <Box width={20}>
        <Text>{session.name.slice(0, 19)}</Text>
      </Box>
      <Box width={10}>
        <Text dimColor>{session.modelName.slice(0, 9)}</Text>
      </Box>
      <Box flexGrow={1}>
        <Text>{session.summary.slice(0, 60)}</Text>
      </Box>
      <Box width={12}>
        <Text dimColor>
          {formatRelativeTime(session.lastActive)}
        </Text>
      </Box>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Session group section
// ---------------------------------------------------------------------------

interface SessionGroupSectionProps {
  title: string
  sessions: FleetSession[]
  selectedId: string | null
  onSelect: (sessionId: string) => void
}

function SessionGroupSection({
  title,
  sessions,
  selectedId,
  onSelect,
}: SessionGroupSectionProps): React.ReactElement | null {
  if (sessions.length === 0) {
    return null
  }

  return (
    <Box flexDirection="column" marginY={1}>
      <Box>
        <Text bold underline>
          {title} ({sessions.length})
        </Text>
      </Box>
      {sessions.map((s) => (
        <SessionRow
          key={s.sessionId}
          session={s}
          isSelected={selectedId === s.sessionId}
          onSelect={() => onSelect(s.sessionId)}
        />
      ))}
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Fleet view header
// ---------------------------------------------------------------------------

interface FleetHeaderProps {
  sessionCount: number
  workingCount: number
  needsInputCount: number
  modelName: string
}

function FleetHeader({
  sessionCount,
  workingCount,
  needsInputCount,
  modelName,
}: FleetHeaderProps): React.ReactElement {
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Box>
        <Text bold>🚀 Lyra Fleet</Text>
        <Text dimColor> — {sessionCount} sessions</Text>
        <Text dimColor> · {modelName}</Text>
      </Box>
      <Box>
        <Text dimColor>
          {workingCount} working · {needsInputCount} needs input ·{' '}
          {sessionCount - workingCount - needsInputCount} completed
        </Text>
      </Box>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Dispatch input
// ---------------------------------------------------------------------------

interface DispatchInputProps {
  onDispatch: (command: string) => void
}

function DispatchInput({ onDispatch }: DispatchInputProps): React.ReactElement {
  const [value, setValue] = useState('')

  const handleSubmit = useCallback(() => {
    if (value.trim()) {
      onDispatch(value.trim())
      setValue('')
    }
  }, [value, onDispatch])

  useInput((input, key) => {
    if (key.return) {
      handleSubmit()
    }
  })

  return (
    <Box marginTop={1}>
      <Text dimColor>▸ </Text>
      <Text>{value || 'Dispatch a new task...'}</Text>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Fleet view footer (keyboard hints)
// ---------------------------------------------------------------------------

function FleetFooter(): React.ReactElement {
  return (
    <Box marginTop={1}>
      <Text dimColor>
        ↑↓ select · Enter attach · s stop · r refresh · d dispatch · q quit
      </Text>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Peek panel (shown when a session is selected)
// ---------------------------------------------------------------------------

interface PeekPanelProps {
  session: FleetSession
  onAttach: () => void
  onStop: () => void
  onDismiss: () => void
}

function PeekPanel({
  session,
  onAttach,
  onStop,
  onDismiss,
}: PeekPanelProps): React.ReactElement {
  return (
    <Box
      flexDirection="column"
      borderStyle="single"
      padding={1}
      marginTop={1}
    >
      <Box>
        <Text bold>{session.name}</Text>
        <Text dimColor> — {session.taskState}</Text>
      </Box>
      <Box marginY={1}>
        <Text>{session.summary}</Text>
      </Box>
      <Box>
        <Text dimColor>Working dir: {session.workingDir}</Text>
      </Box>
      <Box>
        <Text dimColor>Model: {session.modelName}</Text>
      </Box>
      <Box>
        <Text dimColor>Last active: {session.lastActive}</Text>
      </Box>
      {session.prUrl && (
        <Box>
          <Text dimColor>PR: {session.prUrl}</Text>
        </Box>
      )}
      <Box marginTop={1} flexDirection="row">
        <Text color="green">[Enter] Attach </Text>
        <Text color="red">[s] Stop </Text>
        <Text dimColor>[Esc] Dismiss</Text>
      </Box>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Main Fleet View component
// ---------------------------------------------------------------------------

export function FleetView({
  sessions,
  onAttach,
  onStop,
  onDispatch,
  onRefresh,
}: FleetViewProps): React.ReactElement {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [peekSessionId, setPeekSessionId] = useState<string | null>(null)
  const { exit } = useApp()

  const groups = groupSessions(sessions)
  const workingCount =
    groups['working'].length + groups['needs-input'].length
  const needsInputCount = groups['needs-input'].length

  // Keyboard navigation
  useInput((input, key) => {
    if (key.escape) {
      if (peekSessionId) {
        setPeekSessionId(null)
      } else {
        exit()
      }
      return
    }

    if (key.return) {
      if (peekSessionId) {
        onAttach(peekSessionId)
      } else if (selectedId) {
        setPeekSessionId(selectedId)
      }
      return
    }

    if (input === 'q' && !peekSessionId) {
      exit()
      return
    }

    if (input === 'r') {
      onRefresh()
      return
    }

    if (input === 's') {
      if (peekSessionId) {
        onStop(peekSessionId)
        setPeekSessionId(null)
      } else if (selectedId) {
        onStop(selectedId)
      }
      return
    }

    if (input === 'd' && !peekSessionId) {
      // Focus dispatch — handled by DispatchInput
      return
    }

    if (key.upArrow || key.downArrow) {
      const allSessions = [
        ...groups['needs-input'],
        ...groups['working'],
        ...groups['completed'],
      ]

      if (allSessions.length === 0) {
        return
      }

      const currentIndex = selectedId
        ? allSessions.findIndex((s) => s.sessionId === selectedId)
        : -1

      let nextIndex: number
      if (key.upArrow) {
        nextIndex =
          currentIndex <= 0
            ? allSessions.length - 1
            : currentIndex - 1
      } else {
        nextIndex =
          currentIndex >= allSessions.length - 1
            ? 0
            : currentIndex + 1
      }

      setSelectedId(allSessions[nextIndex].sessionId)
      setPeekSessionId(null)
    }
  })

  const peekSession = peekSessionId
    ? sessions.find((s) => s.sessionId === peekSessionId)
    : null

  return (
    <Box flexDirection="column" padding={1}>
      <FleetHeader
        sessionCount={sessions.length}
        workingCount={workingCount}
        needsInputCount={needsInputCount}
        modelName={sessions[0]?.modelName ?? 'unknown'}
      />

      <SessionGroupSection
        title="⚠ Needs Input"
        sessions={groups['needs-input']}
        selectedId={selectedId}
        onSelect={setSelectedId}
      />

      <SessionGroupSection
        title="⚙ Working"
        sessions={groups['working']}
        selectedId={selectedId}
        onSelect={setSelectedId}
      />

      <SessionGroupSection
        title="✓ Completed"
        sessions={groups['completed']}
        selectedId={selectedId}
        onSelect={setSelectedId}
      />

      {peekSession && (
        <PeekPanel
          session={peekSession}
          onAttach={() => onAttach(peekSession.sessionId)}
          onStop={() => {
            onStop(peekSession.sessionId)
            setPeekSessionId(null)
          }}
          onDismiss={() => setPeekSessionId(null)}
        />
      )}

      {!peekSession && <DispatchInput onDispatch={onDispatch} />}

      <FleetFooter />
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  const now = Date.now()
  const diffMs = now - then

  if (diffMs < 60000) {
    return 'just now'
  }
  if (diffMs < 3600000) {
    return `${Math.floor(diffMs / 60000)}m ago`
  }
  if (diffMs < 86400000) {
    return `${Math.floor(diffMs / 3600000)}h ago`
  }
  return `${Math.floor(diffMs / 86400000)}d ago`
}

export type { FleetSession, FleetViewProps, TaskState, ProcessState }
