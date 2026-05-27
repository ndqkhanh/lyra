import React, { useState, useEffect, useRef } from 'react'
import { Box, Text } from 'ink'
import { useThemeColors, useUIStore } from '@lyra/ui-core'
import { useShallow } from 'zustand/react/shallow'
import { usePersonality } from '../hooks/usePersonality'

interface StatusBarProps {
  sessionId: string
  width?: number
}

const FACES = ['◉', '◎', '◍', '◌']

function fmtK(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

function ctxBar(pct: number, w = 10): string {
  const filled = Math.round((Math.max(0, Math.min(100, pct)) / 100) * w)
  return '█'.repeat(filled) + '░'.repeat(w - filled)
}

function ctxBarColor(pct: number, colors: { statusCritical: string; statusBad: string; statusWarn: string; statusGood: string }): string {
  if (pct >= 95) return colors.statusCritical
  if (pct > 80) return colors.statusBad
  if (pct >= 50) return colors.statusWarn
  return colors.statusGood
}

function fmtDuration(ms: number): string {
  const s = Math.floor(ms / 1000)
  const m = Math.floor(s / 60)
  const h = Math.floor(m / 60)
  if (h > 0) return `${h}h ${m % 60}m`
  if (m > 0) return `${m}m ${s % 60}s`
  return `${s}s`
}

export const StatusBar = React.memo(function StatusBar({
  sessionId,
  width = 120,
}: StatusBarProps) {
  const colors = useThemeColors()
  const session = useUIStore(state => state.sessions.get(sessionId))
  const transport = useUIStore(state => state.transport)
  const isStreaming = session?.isStreaming ?? false
  const permissionMode = session?.permissionMode || 'ask'
  const model = useUIStore(useShallow((state) => state.currentModel)) || 'Lyra'
  const { currentFace, currentVerb, tick } = usePersonality()

  const [faceIdx, setFaceIdx] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const streamStartRef = useRef<number | null>(null)
  const sessionStartRef = useRef<number>(Date.now())
  const [sessionDuration, setSessionDuration] = useState(0)

  // Face/verb ticker (Hermes FACE_TICK_MS = 2500)
  useEffect(() => {
    if (!isStreaming) return
    const id = setInterval(() => {
      setFaceIdx(n => (n + 1) % FACES.length)
      tick()
    }, 2500)
    return () => clearInterval(id)
  }, [isStreaming]) // eslint-disable-line react-hooks/exhaustive-deps

  // Elapsed timer during streaming
  useEffect(() => {
    if (isStreaming) {
      if (!streamStartRef.current) streamStartRef.current = Date.now()
      const id = setInterval(() => {
        if (streamStartRef.current) setElapsed(Date.now() - streamStartRef.current)
      }, 1000)
      return () => clearInterval(id)
    }
    streamStartRef.current = null
    setElapsed(0)
    return
  }, [isStreaming])

  // Session duration (Hermes SessionDuration)
  useEffect(() => {
    const id = setInterval(() => {
      setSessionDuration(Date.now() - sessionStartRef.current)
    }, 1000)
    return () => clearInterval(id)
  }, [])

  // Token usage
  let tokensIn = 0
  let tokensOut = 0
  if (session) {
    for (const msg of session.messages) {
      const n = Math.ceil(msg.content.length / 4)
      if (msg.role === 'user') tokensIn += n
      else if (msg.role === 'assistant') tokensOut += n
    }
  }
  const totalTokens = tokensIn + tokensOut
  const CONTEXT_WINDOW = 200_000
  const pct = totalTokens > 0 ? Math.round((totalTokens / CONTEXT_WINDOW) * 100) : 0

  const permLabel = { ask: 'ask', allow: 'allow', deny: 'deny' }[permissionMode] || permissionMode
  const permColor = { ask: colors.amber, allow: colors.statusGood, deny: colors.statusCritical }[permissionMode] || colors.dim

  const cwd = process.cwd().replace(process.env.HOME || '', '~')
  const cwdMax = Math.max(12, Math.floor(width * 0.25))
  const cwdLabel = cwd.length > cwdMax ? `…${cwd.slice(-cwdMax + 1)}` : cwd

  const statusColor = isStreaming ? colors.gold : colors.statusFg
  const statusText = isStreaming
    ? `${currentFace || FACES[faceIdx]} ${currentVerb}…`
    : transport?.status === 'disconnected'
      ? 'disconnected'
      : transport?.status === 'connecting'
        ? 'connecting…'
        : 'idle'

  const connColor = transport?.status === 'disconnected' ? colors.statusCritical
    : transport?.status === 'connecting' ? colors.statusWarn
    : colors.statusGood

  const barColor = totalTokens > 0 ? ctxBarColor(pct, { statusCritical: colors.statusCritical, statusBad: colors.statusBad, statusWarn: colors.statusWarn, statusGood: colors.statusGood }) : colors.dim

  return (
    <Box height={1}>
      <Box flexShrink={1} width={Math.max(12, width - cwdLabel.length - 3)}>
        <Text color={colors.bronze} wrap="truncate-end">
          {'─ '}
          <Text color={connColor}>● </Text>
          <Text color={statusColor}>{statusText}</Text>
          <Text color={colors.dim}> │ </Text>
          <Text color={permColor}>{permLabel}</Text>
          <Text color={colors.dim}> │ </Text>
          <Text color={colors.label}>{model}</Text>
          {totalTokens > 0 ? (
            <>
              <Text color={colors.dim}> │ </Text>
              <Text color={colors.dim}>{fmtK(totalTokens)}/{fmtK(CONTEXT_WINDOW)}</Text>
              <Text color={colors.dim}> [</Text>
              <Text color={barColor}>{ctxBar(pct)}</Text>
              <Text color={colors.dim}>] </Text>
              <Text color={barColor}>{pct}%</Text>
            </>
          ) : (
            <>
              <Text color={colors.dim}> │ </Text>
              <Text color={colors.dim}>0/200k</Text>
            </>
          )}
          {isStreaming && elapsed > 0 ? (
            <>
              <Text color={colors.dim}> │ </Text>
              <Text color={colors.dim}>{fmtDuration(elapsed)}</Text>
            </>
          ) : null}
          <Text color={colors.dim}> │ </Text>
          <Text color={colors.dim}>{fmtDuration(sessionDuration)}</Text>
        </Text>
      </Box>
      <Text color={colors.bronze}> ─ </Text>
      <Text color={colors.label}>{cwdLabel}</Text>
    </Box>
  )
})
