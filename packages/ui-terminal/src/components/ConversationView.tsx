import React, { useMemo, useState, useEffect, useRef } from 'react'
import { Box, Text } from 'ink'
import { useUIStore, applyDisplayPolicy, partitionRenderItems, colors, symbols } from '@lyra/ui-core'
import { RenderItemView } from './RenderItemView'
import { PhaseTracker } from './PhaseTracker'

interface ConversationViewProps {
  sessionId: string
}

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 5) return 'Burning the midnight oil?'
  if (hour < 12) return 'Good morning! Ready to build?'
  if (hour < 17) return "Good afternoon! Let's make something great."
  if (hour < 22) return 'Good evening! The stars are out.'
  return "Late night coding session? Let's go."
}

const QUICK_START = [
  { cmd: '/help', desc: 'Browse all 85+ commands' },
  { cmd: '/model', desc: 'Switch AI model & provider' },
  { cmd: 'Ctrl+K', desc: 'Open command palette' },
  { cmd: '/agents', desc: 'Manage agent teams' },
] as const

function EmptyState() {
  const greeting = getGreeting()
  return (
    <Box flexDirection="column" marginY={1} paddingX={2}>
      <Box marginBottom={1}>
        <Text color={colors.thinking}>{symbols.thinking} </Text>
        <Text color={colors.muted}>{greeting}</Text>
      </Box>

      <Box flexDirection="column" marginBottom={1}>
        <Text bold color={colors.muted} dimColor>Quick Start</Text>
        {QUICK_START.map(({ cmd, desc }) => (
          <Box key={cmd}>
            <Text color={colors.shortcutKey}>{cmd}</Text>
            <Text color={colors.separator}>  </Text>
            <Text color={colors.muted} dimColor>{desc}</Text>
          </Box>
        ))}
      </Box>

      <Box>
        <Text color={colors.muted} dimColor>Type a message below to begin</Text>
      </Box>
    </Box>
  )
}

const TIPS = [
  'Use /btw to ask a quick side question without losing context',
  'Type @ to mention files, # for skills, / for commands',
  'Ctrl+R to search your command history',
  'Shift+Enter for multi-line input',
  '/compact to summarize and free up context space',
  'Ctrl+O to toggle the agent tree panel',
  'Tab to cycle between agent, plan, ask, and auto modes',
]

function getVerb(elapsedSec: number, isThinking: boolean): string {
  if (isThinking && elapsedSec < 10) return 'Puzzling'
  if (isThinking) return 'Cogitating'
  if (elapsedSec < 15) return 'Noodling'
  if (elapsedSec < 60) return 'Flowing'
  return 'Skedaddling'
}

function StreamingStatus({ sessionId }: { sessionId: string }) {
  const session = useUIStore(state => state.sessions.get(sessionId))
  const stateMachine = useUIStore(state => state.getStateMachine(sessionId))
  const [indicatorState, setIndicatorState] = useState<string>('idle')
  const [spinnerFrame, setSpinnerFrame] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [tipIndex, setTipIndex] = useState(0)
  const startTimeRef = useRef<number | null>(null)

  useEffect(() => {
    if (!stateMachine) return
    const unsub = stateMachine.subscribe(ctx => {
      const s = ctx.state
      setIndicatorState(s)
      if (s === 'streaming' || s === 'thinking') {
        if (!startTimeRef.current) {
          startTimeRef.current = Date.now()
        }
      } else {
        startTimeRef.current = null
        setElapsed(0)
      }
    })
    return unsub
  }, [stateMachine])

  // Spinner + elapsed timer
  useEffect(() => {
    if (!startTimeRef.current && indicatorState !== 'streaming' && indicatorState !== 'thinking') return
    const interval = setInterval(() => {
      if (startTimeRef.current) {
        setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000))
        setSpinnerFrame(prev => (prev + 1) % 5)
      }
    }, 250)
    return () => clearInterval(interval)
  }, [indicatorState])

  // Rotate tips every 30s
  useEffect(() => {
    if (indicatorState !== 'streaming' && indicatorState !== 'thinking') return
    const interval = setInterval(() => {
      setTipIndex(prev => (prev + 1) % TIPS.length)
    }, 30000)
    return () => clearInterval(interval)
  }, [indicatorState])

  if (!session?.isStreaming) return null

  const frames = symbols.progressFrames
  const spinner = frames[spinnerFrame % frames.length]

  const tokensIn = Math.ceil(
    session.messages
      .filter(m => m.role === 'user')
      .reduce((sum, m) => sum + m.content.length / 4, 0)
  )
  const tokensOut = Math.ceil(
    session.previewMessages.reduce((sum, m) => sum + m.content.length / 4, 0)
  )

  const verb = getVerb(elapsed, indicatorState === 'thinking')
  const mins = Math.floor(elapsed / 60)
  const secs = elapsed % 60
  const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`

  const formatTokens = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)

  return (
    <Box flexDirection="column" paddingX={2} marginBottom={1}>
      {/* Main progress line: ✢ Noodling… (36s · ↓ 762 tokens) */}
      <Box>
        <Text color={colors.thinking}>{spinner} </Text>
        <Text color={colors.thinking} bold>{verb}…</Text>
        <Text color={colors.muted} dimColor> ({timeStr}</Text>
        {tokensOut > 0 && (
          <>
            <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
            <Text color={colors.success}>↓ {formatTokens(tokensOut)} tokens</Text>
          </>
        )}
        {tokensIn > 0 && tokensOut > 0 && (
          <>
            <Text color={colors.shortcutSeparator}> {symbols.separator} </Text>
            <Text color={colors.info}>↑ {formatTokens(tokensIn)}</Text>
          </>
        )}
        <Text color={colors.muted} dimColor>)</Text>
      </Box>

      {/* Rotating tip */}
      <Box marginTop={0}>
        <Text color={colors.shortcutKey}>{symbols.branch}  </Text>
        <Text color={colors.muted} dimColor>Tip: {TIPS[tipIndex]}</Text>
      </Box>

      {/* Phase checkboxes */}
      <PhaseTracker sessionId={sessionId} />
    </Box>
  )
}

export function ConversationView({ sessionId }: ConversationViewProps) {
  const session = useUIStore(state => state.sessions.get(sessionId))
  const allItems = useUIStore(state => state.getRenderItems(sessionId))

  if (!session) {
    return (
      <Box marginY={1} paddingX={2}>
        <Text color={colors.error}>{symbols.error} </Text>
        <Text color={colors.error}>Session not found: {sessionId}</Text>
      </Box>
    )
  }

  const policyItems = useMemo(
    () => applyDisplayPolicy(allItems, session.displayMode),
    [allItems, session.displayMode]
  )

  const { staticItems, liveItems } = partitionRenderItems(policyItems)
  const hasMessages = session.messages.length > 0

  return (
    <Box flexDirection="column" paddingX={2}>
      {!hasMessages && !session.isStreaming && <EmptyState />}

      {/* Committed messages */}
      {staticItems.map(item => (
        <Box key={item.id} marginBottom={1}>
          <RenderItemView item={item} />
        </Box>
      ))}

      {/* Live streaming items — these update dynamically */}
      {liveItems.map(item => (
        <Box key={item.id} marginBottom={1}>
          <RenderItemView item={item} />
        </Box>
      ))}

      <StreamingStatus sessionId={sessionId} />
    </Box>
  )
}
