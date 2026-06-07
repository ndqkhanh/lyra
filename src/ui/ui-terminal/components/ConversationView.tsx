import React, { useMemo, useState, useEffect, useRef } from 'react'
import { Box, Text } from 'ink'
import { useUIStore, applyDisplayPolicy, partitionRenderItems, useThemeColors, symbols } from '@lyra/ui-core'
import { useShallow } from 'zustand/react/shallow'
import { RenderItemView } from './RenderItemView'
import { PhaseTracker } from './PhaseTracker'
import { Header } from './Header'
import { ScrollBox } from './ScrollBox'
import { VirtualScrollBox } from './VirtualScrollBox'
import { QueuedMessages } from './QueuedMessages'

interface ConversationViewProps {
  sessionId: string
}

// ── WelcomePanel — Hermes SessionPanel style ──────────────────────────
function WelcomePanel() {
  const colors = useThemeColors()
  const providers = useUIStore(state => state.providers)
  const currentModel = useUIStore(state => state.currentModel)
  const activeThemeId = useUIStore(state => state.activeThemeId)

  const providerCount = providers.length
  const totalModels = providers.reduce((sum, p) => sum + p.models.length, 0)
  const toolsCount = providers.filter(p => p.supports_tools).length
  const reasoningCount = providers.filter(p => p.supports_reasoning).length

  return (
    <Box borderColor={colors.bronze} borderStyle="round" flexDirection="column" paddingX={2} paddingY={1}>
      <Box justifyContent="center" marginBottom={1}>
        <Text bold color={colors.gold}>
          Lyra {currentModel ? `· ${currentModel}` : ''}
        </Text>
      </Box>

      <Box>
        <Text bold color={colors.amber}>Available Providers</Text>
      </Box>
      <Box>
        <Text color={colors.dim}>
          {providerCount} provider{providerCount !== 1 ? 's' : ''} · {totalModels} model{totalModels !== 1 ? 's' : ''} · {toolsCount} with tools · {reasoningCount} with reasoning
        </Text>
      </Box>

      <Box marginTop={1}>
        <Text bold color={colors.amber}>Quick Start</Text>
      </Box>
      <Box>
        <Text color={colors.shortcutKey}>/model</Text>
        <Text color={colors.dim}>: Switch AI model & provider</Text>
      </Box>
      <Box>
        <Text color={colors.shortcutKey}>/theme</Text>
        <Text color={colors.dim}>: Change theme (current: </Text>
        <Text color={colors.gold}>{activeThemeId}</Text>
        <Text color={colors.dim}>)</Text>
      </Box>
      <Box>
        <Text color={colors.shortcutKey}>/agents</Text>
        <Text color={colors.dim}>: Manage agent teams</Text>
      </Box>
      <Box>
        <Text color={colors.shortcutKey}>/deep-research</Text>
        <Text color={colors.dim}>: Run deep research on a topic</Text>
      </Box>
      <Box marginTop={1}>
        <Text color={colors.dim}>85+ commands · /help for full list</Text>
      </Box>
    </Box>
  )
}

// ── Tips for streaming ────────────────────────────────────────────────
const TIPS = [
  'Use /btw to ask a quick side question without losing context',
  'Type @ to mention files, # for skills, / for commands',
  'Ctrl+R to search your command history',
  'Shift+Enter for multi-line input',
  '/compact to summarize and free up context space',
  'Ctrl+O to toggle the agent tree panel',
  'Tab to cycle between agent, plan, ask, and auto modes',
]

// ── StreamingStatus — Hermes StreamingAssistant ──────────────────────
function StreamingStatus({ sessionId }: { sessionId: string }) {
  const colors = useThemeColors()
  const session = useUIStore(state => state.sessions.get(sessionId))
  const stateMachine = useUIStore(state => state.getStateMachine(sessionId))
  const [spinnerFrame, setSpinnerFrame] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [tipIndex, setTipIndex] = useState(0)
  const startTimeRef = useRef<number | null>(null)

  const [indicatorState, setIndicatorState] = useState<string>('idle')
  useEffect(() => {
    if (!stateMachine) return
    const unsub = stateMachine.subscribe((ctx: { state: string }) => {
      setIndicatorState(ctx.state)
      if (ctx.state === 'streaming' || ctx.state === 'thinking') {
        if (!startTimeRef.current) startTimeRef.current = Date.now()
      } else {
        startTimeRef.current = null
        setElapsed(0)
      }
    })
    return unsub
  }, [stateMachine])

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

  useEffect(() => {
    if (indicatorState !== 'streaming' && indicatorState !== 'thinking') return
    const interval = setInterval(() => {
      setTipIndex(prev => (prev + 1) % TIPS.length)
    }, 30000)
    return () => clearInterval(interval)
  }, [indicatorState])

  if (!session?.isStreaming) return null

  const frames = symbols.progressFrames as readonly string[]
  const spinner = frames[spinnerFrame % frames.length]

  const tokensOut = Math.ceil(
    session.previewMessages.reduce((sum: number, m: { content: string }) => sum + m.content.length / 4, 0)
  )

  const mins = Math.floor(elapsed / 60)
  const secs = elapsed % 60
  const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
  const formatTokens = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)

  return (
    <Box flexDirection="column" paddingX={1} marginBottom={1}>
      <Box>
        <Text color={colors.thinking}>{spinner} </Text>
        <Text color={colors.thinking} bold>Processing…</Text>
        <Text color={colors.dim}> ({timeStr}</Text>
        {tokensOut > 0 && (
          <>
            <Text color={colors.dim}> · </Text>
            <Text color={colors.success}>↓ {formatTokens(tokensOut)} tokens</Text>
          </>
        )}
        <Text color={colors.dim}>)</Text>
      </Box>

      <Box marginTop={0}>
        <Text color={colors.dim}>Tip: {TIPS[tipIndex]}</Text>
      </Box>

      <PhaseTracker sessionId={sessionId} />
    </Box>
  )
}

// ── ConversationView — Hermes TranscriptPane ─────────────────────────
export const ConversationView = React.memo(function ConversationView({ sessionId }: ConversationViewProps) {
  // Stable selectors — prevent re-renders on unrelated store changes
  const messages = useUIStore(useShallow((state) => {
    const session = state.sessions.get(sessionId)
    return session?.messages ?? []
  }))

  const displayMode = useUIStore(useShallow((state) => {
    const session = state.sessions.get(sessionId)
    return session?.displayMode ?? 'standard'
  }))

  const isStreaming = useUIStore((state) => {
    const session = state.sessions.get(sessionId)
    return session?.isStreaming ?? false
  })

  const hasMessages = messages.length > 0

  // Show intro panel when no messages have arrived yet
  const showIntro = !hasMessages && !isStreaming

  const allItems = useUIStore(useShallow((state) => state.getRenderItems(sessionId)))
  const policyItems = useMemo(
    () => applyDisplayPolicy(allItems, displayMode),
    [allItems, displayMode]
  )

  const { staticItems, liveItems } = partitionRenderItems(policyItems)

  // Use virtual scrolling for large conversations (>100 items)
  const useVirtualScrolling = staticItems.length + liveItems.length > 100

  // Use basic scrolling for medium conversations (>20 items)
  const useScrolling = !useVirtualScrolling && staticItems.length + liveItems.length > 20

  return (
    <Box flexDirection="column" paddingX={1}>
      {/* Hermes intro: Banner + SessionPanel — only before any messages */}
      {showIntro && (
        <Box flexDirection="column" paddingTop={1}>
          <Header width={process.stdout.columns || 120} />
          <WelcomePanel />
        </Box>
      )}

      {/* Queued messages indicator */}
      <QueuedMessages sessionId={sessionId} />

      {/* Messages with virtual scrolling for large conversations */}
      {useVirtualScrolling ? (
        <VirtualScrollBox
          items={[...staticItems, ...liveItems].map(item => ({
            key: item.id,
            content: (
              <Box marginBottom={1}>
                <RenderItemView item={item} />
              </Box>
            )
          }))}
          viewportHeight={30}
          overscan={20}
          sticky={true}
        />
      ) : useScrolling ? (
        <ScrollBox>
          <Box flexDirection="column">
            {staticItems.map(item => (
              <Box key={item.id} marginBottom={1}>
                <RenderItemView item={item} />
              </Box>
            ))}

            {liveItems.map(item => (
              <Box key={item.id} marginBottom={1}>
                <RenderItemView item={item} />
              </Box>
            ))}

            <StreamingStatus sessionId={sessionId} />
          </Box>
        </ScrollBox>
      ) : (
        <>
          {/* Messages — Hermes MessageLine */}
          {staticItems.map(item => (
            <Box key={item.id} marginBottom={1}>
              <RenderItemView item={item} />
            </Box>
          ))}

          {/* Live streaming items */}
          {liveItems.map(item => (
            <Box key={item.id} marginBottom={1}>
              <RenderItemView item={item} />
            </Box>
          ))}

          {/* Streaming status — Hermes StreamingAssistant */}
          <StreamingStatus sessionId={sessionId} />
        </>
      )}
    </Box>
  )
})
