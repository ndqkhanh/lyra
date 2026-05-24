import React, { useState, useEffect } from 'react'
import { Box, Text, useInput } from 'ink'
import TextInput from 'ink-text-input'
import { useUIStore, colors, symbols } from '@lyra/ui-core'
import { useHistory } from '../hooks/useHistory'
import { useVim } from '../hooks/useVim'
import { getFileSuggestions, getCurrentMention, type FileSuggestion } from '../utils/fileCompletion'
import { ModelPicker } from './ModelPicker'
import { ReleaseNotesPicker } from './ReleaseNotesPicker'
import { getCommandNames } from '../constants/commands'

interface InputAreaProps {
  sessionId: string
  autocompleteCommands?: string[]
}

// Default command list so autocomplete works even if caller doesn't pass commands
const DEFAULT_COMMANDS = getCommandNames()

export function InputArea({ sessionId, autocompleteCommands = DEFAULT_COMMANDS }: InputAreaProps) {
  const history = useHistory()
  const session = useUIStore(state => state.sessions.get(sessionId))
  const transport = useUIStore(state => state.transport)
  const addMessage = useUIStore(state => state.addMessage)
  const setModelAndProvider = useUIStore(state => state.setModelAndProvider)

  const [suggestions, setSuggestions] = useState<string[]>([])
  const [selectedSuggestion, setSelectedSuggestion] = useState(0)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [suggestionType, setSuggestionType] = useState<'command' | 'file'>('command')
  const [fileSuggestions, setFileSuggestions] = useState<FileSuggestion[]>([])
  const [showModelPicker, setShowModelPicker] = useState(false)
  const [showReleaseNotes, setShowReleaseNotes] = useState(false)
  const { vim, vimActions } = useVim()

  // Track cursor position for vim motions
  const [vimCursor, setVimCursor] = useState(0)

  // Update suggestions when input changes (debounced to prevent infinite loops)
  useEffect(() => {
    const input = history.current

    // Debounce to prevent rapid updates
    const timeoutId = setTimeout(() => {
      // Check for @ file mentions
      const currentMention = getCurrentMention(input, input.length)
      if (currentMention !== null) {
        const files = getFileSuggestions(currentMention)
        setFileSuggestions(files)
        setShowSuggestions(files.length > 0)
        setSuggestionType('file')
        setSelectedSuggestion(0)
        return
      }

      // Check for / commands
      if (input.startsWith('/')) {
        const query = input.slice(1).toLowerCase()
        const matches = autocompleteCommands.filter(cmd =>
          cmd.toLowerCase().startsWith(query)
        )

        setSuggestions(matches)
        setShowSuggestions(matches.length > 0)
        setSuggestionType('command')
        setSelectedSuggestion(0)
        return
      }

      setShowSuggestions(false)
    }, 50) // 50ms debounce

    return () => clearTimeout(timeoutId)
  }, [history.current, autocompleteCommands])

  // Handle keyboard shortcuts
  useInput((input, key) => {
    // Skip keyboard shortcuts when model picker is visible
    if (showModelPicker) return

    // ── Vim Mode ──────────────────────────────────────────
    if (vim.enabled) {
      // Esc to enter NORMAL mode
      if (key.escape) {
        vimActions.enterNormal()
        return
      }

      if (vim.mode === 'normal') {
        if (input === 'i') { vimActions.enterInsert(); return }
        if (input === 'a') { vimActions.enterInsertAfter(); setVimCursor(p => Math.min(history.current.length, p + 1)); return }
        if (input === 'o') { history.setCurrent(history.current + '\n'); vimActions.enterInsert(); return }
        if (input === 'O') { history.setCurrent('\n' + history.current); vimActions.enterInsert(); return }
        if (input === 'h') { setVimCursor(p => vimActions.moveLeft(history.current, p)); return }
        if (input === 'j') { setVimCursor(p => vimActions.moveDown(history.current, p)); return }
        if (input === 'k') { setVimCursor(p => vimActions.moveUp(history.current, p)); return }
        if (input === 'l') { setVimCursor(p => vimActions.moveRight(history.current, p)); return }
        if (input === 'w') { setVimCursor(p => vimActions.wordForward(history.current, p)); return }
        if (input === 'b') { setVimCursor(p => vimActions.wordBack(history.current, p)); return }
        if (input === 'x') { const r = vimActions.deleteChar(history.current, vimCursor); history.setCurrent(r.text); setVimCursor(r.pos); return }
        if (input === 'd') { history.setCurrent(vimActions.deleteLine(history.current, vimCursor)); setVimCursor(p => Math.min(p, history.current.length)); return }
        if (input === '0') { setVimCursor(0); return }
        if (input === '$') { const lineEnd = history.current.indexOf('\n', vimCursor); setVimCursor(lineEnd === -1 ? history.current.length : lineEnd); return }
        if (input === 'u') { return }
        if (key.return) { vimActions.enterInsert(); return }
        return
      }

      if (vim.mode === 'insert') {
        if (key.return && !key.shift) {
          handleSubmit()
          return
        }
      }
    }

    // Shift+Enter to insert newline
    if (key.shift && key.return) {
      history.setCurrent(history.current + '\n')
      return
    }

    // History navigation
    if (key.upArrow && !showSuggestions) {
      history.navigateUp()
      return
    }

    if (key.downArrow && !showSuggestions) {
      history.navigateDown()
      return
    }

    // Autocomplete navigation
    if (showSuggestions) {
      if (key.upArrow) {
        setSelectedSuggestion(prev => Math.max(0, prev - 1))
        return
      }

      if (key.downArrow) {
        const maxIndex = suggestionType === 'file' ? fileSuggestions.length - 1 : suggestions.length - 1
        setSelectedSuggestion(prev => Math.min(maxIndex, prev + 1))
        return
      }

      // Tab to accept suggestion (Enter always submits buffer)
      if (key.tab) {
        if (suggestionType === 'command') {
          history.setCurrent(`/${suggestions[selectedSuggestion]}`)
        } else {
          const input = history.current
          const currentMention = getCurrentMention(input, input.length)
          if (currentMention !== null) {
            const lastAtIndex = input.lastIndexOf('@')
            const before = input.slice(0, lastAtIndex + 1)
            const after = input.slice(lastAtIndex + 1 + currentMention.length)
            history.setCurrent(before + fileSuggestions[selectedSuggestion].path + after)
          }
        }
        setShowSuggestions(false)
        return
      }

      // Escape to close suggestions
      if (key.escape) {
        setShowSuggestions(false)
        return
      }
    }

    // Ctrl+C to clear input (like Claude Code)
    if (key.ctrl && input === 'c') {
      history.setCurrent('')
      setShowSuggestions(false)
      return
    }

    // Ctrl+U to clear input (alternative - Unix standard)
    if (key.ctrl && input === 'u') {
      history.setCurrent('')
      setShowSuggestions(false)
      return
    }
  })

  const handleModelSelect = (providerKey: string, modelSlug: string) => {
    setModelAndProvider(modelSlug, providerKey)
    setShowModelPicker(false)
    history.setCurrent('')
    // Also send the /model command so backend knows
    if (transport) {
      transport.sendMessage(`/model ${providerKey}:${modelSlug}`).catch(() => {})
    }
  }

  const handleModelCancel = () => {
    setShowModelPicker(false)
    history.setCurrent('')
  }

  const handleNeedKey = (_providerKey: string) => {
    // Key was saved, proceed with model selection
    // ModelPicker already handles showing the key prompt inline
  }

  const handleSubmit = () => {
    if (!history.current.trim() || !transport) return

    const input = history.current.trim()

    // Intercept /model to open model picker
    if (input === '/model' || input.startsWith('/model ')) {
      setShowModelPicker(true)
      return
    }

    // Intercept /vim to toggle vim mode
    if (input === '/vim' || input === '/vim on') {
      vimActions.enable()
      history.setCurrent('')
      return
    }
    if (input === '/vim off') {
      vimActions.disable()
      history.setCurrent('')
      return
    }

    // Intercept /release-notes to open release picker
    if (input === '/release-notes' || input.startsWith('/release-notes ')) {
      setShowReleaseNotes(true)
      return
    }

    // Add to history
    history.addToHistory(history.current)

    // Add user message
    addMessage(sessionId, {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: history.current,
      timestamp: Date.now()
    })

    // Send via transport
    transport.sendMessage(history.current).catch(console.error)

    history.setCurrent('')
    setShowSuggestions(false)
  }

  if (!session || session.isStreaming) {
    return (
      <Box paddingX={2}>
        <Text color={colors.timestamp} dimColor>
          {symbols.spinner[0]} Waiting for response...
        </Text>
      </Box>
    )
  }

  return (
    <Box flexDirection="column">
      {/* Autocomplete suggestions */}
      {showSuggestions && (
        <Box
          flexDirection="column"
          paddingX={2}
          marginBottom={1}
        >
          <Text color={colors.timestamp} dimColor>
            {suggestionType === 'command'
              ? 'Commands (↑/↓ to navigate, Tab to select):'
              : 'Files (↑/↓ to navigate, Tab to select):'}
          </Text>
          {suggestionType === 'command' ? (
            suggestions.slice(0, 5).map((suggestion, i) => (
              <Box key={suggestion} paddingLeft={2}>
                <Text
                  color={i === selectedSuggestion ? colors.userPrompt : colors.timestamp}
                  bold={i === selectedSuggestion}
                >
                  {i === selectedSuggestion ? symbols.rightArrow : ' '} /{suggestion}
                </Text>
              </Box>
            ))
          ) : (
            fileSuggestions.slice(0, 5).map((file, i) => (
              <Box key={file.path} paddingLeft={2}>
                <Text
                  color={i === selectedSuggestion ? colors.userPrompt : colors.timestamp}
                  bold={i === selectedSuggestion}
                >
                  {i === selectedSuggestion ? symbols.rightArrow : ' '}
                  {file.isDirectory ? '📁 ' : '📄 '}
                  {file.displayName}
                </Text>
              </Box>
            ))
          )}
        </Box>
      )}

      {/* Model picker dropdown */}
      <ModelPicker
        visible={showModelPicker}
        onSelect={handleModelSelect}
        onCancel={handleModelCancel}
        onNeedKey={handleNeedKey}
      />

      {/* Release notes picker */}
      <ReleaseNotesPicker
        visible={showReleaseNotes}
        onSelect={() => {
          setShowReleaseNotes(false)
          history.setCurrent('')
        }}
        onClose={() => {
          setShowReleaseNotes(false)
          history.setCurrent('')
        }}
      />

      {/* Input prompt - Claude Code style */}
      <Box paddingX={2}>
        {vim.enabled && (
          <Text color={vim.mode === 'normal' ? colors.warning : colors.info}>
            [{vim.mode === 'normal' ? 'NORMAL' : 'INSERT'}]{' '}
          </Text>
        )}
        <Text bold color={colors.userPrompt}>❯ </Text>
        <Box flexGrow={1}>
          <TextInput
            value={history.current}
            onChange={history.setCurrent}
            onSubmit={handleSubmit}
            placeholder=""
          />
        </Box>
      </Box>
    </Box>
  )
}
