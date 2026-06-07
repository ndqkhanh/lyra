import React, { useState, useMemo, useCallback } from 'react'
import { Box, Text, useInput } from 'ink'
import { useUIStore, useThemeColors } from '@lyra/ui-core'

interface TranscriptViewerProps {
  sessionId: string
  visible: boolean
  onClose: () => void
}

export function TranscriptViewer({ sessionId, visible, onClose }: TranscriptViewerProps) {
  const colors = useThemeColors()
  const session = useUIStore(state => state.sessions.get(sessionId))
  const [searchQuery, setSearchQuery] = useState('')
  const [searchMode, setSearchMode] = useState(false)
  const [searchMatchIdx, setSearchMatchIdx] = useState(0)
  const [scrollLine, setScrollLine] = useState(0)

  const messages = session?.messages ?? []

  const searchMatches = useMemo(() => {
    if (!searchQuery) return []
    return messages
      .map((m, i) => {
        const idx = m.content.toLowerCase().indexOf(searchQuery.toLowerCase())
        return idx !== -1 ? { msgIdx: i, contentIdx: idx } : null
      })
      .filter((m): m is { msgIdx: number; contentIdx: number } => m !== null)
  }, [messages, searchQuery])

  const currentMatch = searchMatches[searchMatchIdx] ?? null

  const formattedLines = useMemo(() => {
    if (searchMode && searchMatches.length > 0) {
      const match = searchMatches[searchMatchIdx]
      if (!match) return []
      const msg = messages[match.msgIdx]
      const role = msg.role === 'user' ? 'You' : msg.role === 'assistant' ? 'Lyra' : 'System'
      return [`[${role}] ${msg.content.slice(0, 120)}${msg.content.length > 120 ? '...' : ''}`]
    }

    const lines: string[] = []
    for (const msg of messages) {
      const role = msg.role === 'user' ? 'You' : msg.role === 'assistant' ? 'Lyra' : 'System'
      const prefix = `[${role}] `
      const content = msg.content
      lines.push(`${prefix}${content}`)
    }
    return lines
  }, [messages, searchMode, searchMatches, searchMatchIdx])

  const navigateMatch = useCallback((direction: 1 | -1) => {
    setSearchMatchIdx(prev => {
      if (searchMatches.length === 0) return 0
      return (prev + direction + searchMatches.length) % searchMatches.length
    })
  }, [searchMatches.length])

  useInput((input, key) => {
    if (!visible) return

    if (searchMode) {
      if (key.escape) { setSearchMode(false); setSearchQuery(''); return }
      if (key.return) { setSearchMode(false); return }
      if (input === 'n') { navigateMatch(1); return }
      if (input === 'N') { navigateMatch(-1); return }
      if (key.backspace || key.delete) { setSearchQuery(p => p.slice(0, -1)); return }
      if (input && !key.ctrl && !key.meta) { setSearchQuery(p => p + input); return }
      return
    }

    if (key.escape || input === 'q') { onClose(); return }
    if (input === '/') { setSearchMode(true); setSearchQuery(''); setSearchMatchIdx(0); return }
    if (input === 'j' || key.downArrow) { setScrollLine(p => Math.min(formattedLines.length - 1, p + 1)); return }
    if (input === 'k' || key.upArrow) { setScrollLine(p => Math.max(0, p - 1)); return }
    if (input === 'g') { setScrollLine(0); return }
    if (input === 'G') { setScrollLine(Math.max(0, formattedLines.length - 1)); return }
  })

  if (!visible || !session) return null

  const visibleLines = formattedLines.slice(scrollLine, scrollLine + 20)

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.separator} padding={1} height={24}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color={colors.info}>
          Transcript — {messages.length} messages
        </Text>
        <Text dimColor>/ search  j/k scroll  g/G top/bottom  q/Esc close</Text>
      </Box>

      {searchMode && (
        <Box marginBottom={1}>
          <Text color={colors.userPrompt}>/</Text>
          <Text color={colors.thinking}>{searchQuery || ''}</Text>
          <Text dimColor>▏</Text>
          {searchMatches.length > 0 && (
            <Text color={colors.timestamp}> ({searchMatchIdx + 1}/{searchMatches.length} matches)</Text>
          )}
        </Box>
      )}

      <Box flexDirection="column" flexGrow={1}>
        {visibleLines.map((line, i) => {
          const globalIdx = scrollLine + i
          const isSearchHit = currentMatch && !searchMode && searchMatches.length > 0 &&
            searchMatches.some(m => m.msgIdx === globalIdx)

          return (
            <Box key={globalIdx}>
              <Text color={colors.timestamp} dimColor>
                {String(globalIdx + 1).padStart(3)} │{' '}
              </Text>
              <Text color={isSearchHit ? colors.userPrompt : undefined}>
                {line.slice(0, 100)}{line.length > 100 ? '...' : ''}
              </Text>
            </Box>
          )
        })}
      </Box>

      <Box marginTop={1}>
        <Text dimColor>
          {scrollLine + 1}-{Math.min(scrollLine + 20, formattedLines.length)} of {formattedLines.length}
        </Text>
      </Box>
    </Box>
  )
}
