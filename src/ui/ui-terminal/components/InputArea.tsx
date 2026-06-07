import React, { useState, useEffect, useCallback } from 'react'
import { Box, Text, useInput } from 'ink'
import { FastTextInput } from './FastTextInput'
import { useUIStore, useThemeColors, symbols, THEME_ORDER, getThemePreset } from '@lyra/ui-core'

// Hermes-style GoodVibesHeart — flashes a ♥ on every keystroke
const HEART_COLORS = ['#ff5fa2', '#ff4d6d']
function GoodVibesHeart({ tick, thinkingColor }: { tick: number; thinkingColor: string }) {
  const [active, setActive] = useState(false)
  const [color, setColor] = useState<string>(thinkingColor)

  useEffect(() => {
    if (tick <= 0) return
    const palette = [...HEART_COLORS, thinkingColor]
    setColor(palette[Math.floor(Math.random() * palette.length)]!)
    setActive(true)
    const id = setTimeout(() => setActive(false), 650)
    return () => clearTimeout(id)
  }, [tick, thinkingColor])

  if (!active) return null
  return <Text color={color}>♥</Text>
}
import { useHistory } from '../hooks/useHistory'
import { useVim } from '../hooks/useVim'
import { getFileSuggestions, getCurrentMention, type FileSuggestion } from '../utils/fileCompletion'
import { ModelPicker } from './ModelPicker'
import { EffortPicker } from './EffortPicker'
import { ThemePicker } from './ThemePicker'
import { OutputStylePicker } from './OutputStylePicker'
import { GoalPanel } from './GoalPanel'
import { ReleaseNotesPicker } from './ReleaseNotesPicker'
import { ShortcutsHelp } from './ShortcutsHelp'
import { getCommandNames } from '../constants/commands'
import { logger } from '../utils/logger'

interface InputAreaProps {
  sessionId: string
  autocompleteCommands?: string[]
}

// Default command list so autocomplete works even if caller doesn't pass commands
const DEFAULT_COMMANDS = getCommandNames()

export function InputArea({ sessionId, autocompleteCommands = DEFAULT_COMMANDS }: InputAreaProps) {
  const colors = useThemeColors()
  const history = useHistory()
  const session = useUIStore(state => state.sessions.get(sessionId))
  const transport = useUIStore(state => state.transport)
  const currentModel = useUIStore(state => state.currentModel)
  const activeThemeId = useUIStore(state => state.activeThemeId)
  const addMessage = useUIStore(state => state.addMessage)
  const setModelAndProvider = useUIStore(state => state.setModelAndProvider)

  const [suggestions, setSuggestions] = useState<string[]>([])
  const [selectedSuggestion, setSelectedSuggestion] = useState(0)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [suggestionType, setSuggestionType] = useState<'command' | 'file'>('command')
  const [fileSuggestions, setFileSuggestions] = useState<FileSuggestion[]>([])
  const [showModelPicker, setShowModelPicker] = useState(false)
  const [showReleaseNotes, setShowReleaseNotes] = useState(false)
  const [showEffortPicker, setShowEffortPicker] = useState(false)
  const [showThemePicker, setShowThemePicker] = useState(false)
  const [showOutputStylePicker, setShowOutputStylePicker] = useState(false)
  const [showGoalPanel, setShowGoalPanel] = useState(false)
  const [showShortcutsHelp, setShowShortcutsHelp] = useState(false)
  const [currentGoal, setCurrentGoal] = useState<string | null>(null)
  const [goodVibesTick, setGoodVibesTick] = useState(0)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { vim, vimActions } = useVim()

  // Hermes-style heart tick on every keystroke
  const handleChange = useCallback((value: string) => {
    history.setCurrent(value)
    setGoodVibesTick(t => t + 1)
  }, [history])

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
    if (showModelPicker || showShortcutsHelp) return

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

    // Enter to submit (belt-and-suspenders with TextInput's onSubmit)
    if (key.return && !key.shift) {
      handleSubmit()
      return
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

  const handleSubmit = useCallback(() => {
    // Prevent double-submission
    if (isSubmitting) {
      logger.debug('InputArea', 'Submit already in progress')
      return
    }

    if (!history.current.trim() || !transport) return

    const input = history.current.trim()

    logger.debug('InputArea', 'Submit:', input.slice(0, 80))

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

    // Intercept /effort to open effort picker
    if (input === '/effort' || input.startsWith('/effort ')) {
      setShowEffortPicker(true)
      return
    }

    // Intercept /theme to open theme picker
    if (input === '/theme' || input.startsWith('/theme ')) {
      setShowThemePicker(true)
      return
    }

    // Intercept /output-style to open style picker
    if (input === '/output-style' || input.startsWith('/output-style ')) {
      setShowOutputStylePicker(true)
      return
    }

    // Intercept /goal to open goal panel
    if (input === '/goal' || input.startsWith('/goal ')) {
      const goalArg = input.slice(5).trim()
      if (goalArg === 'clear') {
        setCurrentGoal(null)
        history.setCurrent('')
        return
      }
      if (goalArg) {
        setCurrentGoal(goalArg)
        history.setCurrent('')
        return
      }
      setShowGoalPanel(true)
      return
    }

    // Intercept /help or /shortcuts to show keyboard shortcuts
    if (input === '/help' || input === '/shortcuts') {
      setShowShortcutsHelp(true)
      return
    }

    // Guard against submission during streaming
    if (session?.isStreaming) return

    // Set submitting state
    setIsSubmitting(true)

    // Add to history
    history.addToHistory(history.current)

    // Add user message
    addMessage(sessionId, {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: history.current,
      timestamp: Date.now()
    })

    // Immediately show streaming state for instant feedback
    useUIStore.getState().beginStreaming(sessionId)

    // Send via transport with model
    transport.sendMessage(history.current, undefined, currentModel || undefined)
      .then(() => {
        // Reset submitting state on success
        setIsSubmitting(false)
      })
      .catch((err) => {
        addMessage(sessionId, {
          id: `error-${Date.now()}`,
          role: 'system',
          content: `Error: ${err.message}`,
          timestamp: Date.now()
        })
        // Reset streaming state on error (no content to commit)
        useUIStore.getState().cancelStreaming(sessionId)
        // Reset submitting state on error
        setIsSubmitting(false)
      })

    history.setCurrent('')
    setShowSuggestions(false)
  }, [isSubmitting, history, transport, session, sessionId, addMessage, currentModel, vimActions])

  if (!session) {
    return (
      <Box paddingX={2}>
        <Text color={colors.thinking}>{symbols.thinkingFrames[0]}</Text>
      </Box>
    )
  }

  return (
    <Box flexDirection="column">

      {/* Streaming indicator — shown inline above prompt during AI response */}
      {session?.isStreaming && (
        <Box paddingX={1}>
          <Text color={colors.thinking}>{symbols.thinkingFrames[0]} AI is responding...</Text>
        </Box>
      )}

      {/* Completions overlay — Hermes FloatingOverlays */}
      {showSuggestions && (
        <Box flexDirection="column" paddingX={1} marginBottom={1}>
          {suggestionType === 'command' ? (
            suggestions.slice(0, 8).map((suggestion, i) => (
              <Box key={suggestion}>
                <Text
                  color={i === selectedSuggestion ? colors.amber : colors.dim}
                  bold={i === selectedSuggestion}
                  backgroundColor={i === selectedSuggestion ? colors.selectionBg : undefined}
                >
                  {i === selectedSuggestion ? '▸' : ' '} /{suggestion}
                </Text>
              </Box>
            ))
          ) : (
            fileSuggestions.slice(0, 8).map((file, i) => (
              <Box key={file.path}>
                <Text
                  color={i === selectedSuggestion ? colors.amber : colors.dim}
                  bold={i === selectedSuggestion}
                  backgroundColor={i === selectedSuggestion ? colors.selectionBg : undefined}
                >
                  {i === selectedSuggestion ? '▸' : ' '}
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

      {/* Effort picker */}
      <EffortPicker
        visible={showEffortPicker}
        onSelect={(level) => {
          setShowEffortPicker(false)
          history.setCurrent('')
          if (transport) transport.sendMessage(`/effort ${level}`).catch(() => {})
        }}
        onClose={() => {
          setShowEffortPicker(false)
          history.setCurrent('')
        }}
      />

      {/* Theme picker */}
      <ThemePicker
        visible={showThemePicker}
        themes={THEME_ORDER.map(id => {
          const preset = getThemePreset(id)
          return { name: id, description: preset?.name ?? id }
        })}
        currentTheme={activeThemeId}
        onSelect={(themeId) => {
          useUIStore.getState().setActiveTheme(themeId)
          setShowThemePicker(false)
          history.setCurrent('')
          if (transport) transport.sendMessage(`/theme ${themeId}`).catch(() => {})
        }}
        onClose={() => {
          setShowThemePicker(false)
          history.setCurrent('')
        }}
      />

      {/* Output style picker */}
      <OutputStylePicker
        visible={showOutputStylePicker}
        currentStyle="default"
        onSelect={(style) => {
          setShowOutputStylePicker(false)
          history.setCurrent('')
          if (transport) transport.sendMessage(`/output-style ${style}`).catch(() => {})
        }}
        onClose={() => {
          setShowOutputStylePicker(false)
          history.setCurrent('')
        }}
      />

      {/* Goal panel */}
      <GoalPanel
        visible={showGoalPanel}
        currentGoal={currentGoal}
        onSetGoal={(goal) => {
          setCurrentGoal(goal)
          setShowGoalPanel(false)
          history.setCurrent('')
        }}
        onClearGoal={() => {
          setCurrentGoal(null)
          setShowGoalPanel(false)
          history.setCurrent('')
        }}
        onClose={() => {
          setShowGoalPanel(false)
          history.setCurrent('')
        }}
      />

      {/* Shortcuts help */}
      <ShortcutsHelp
        visible={showShortcutsHelp}
        onClose={() => {
          setShowShortcutsHelp(false)
          history.setCurrent('')
        }}
      />

      {/* Prompt line — Hermes ComposerPane style */}
      <Box paddingX={1}>
        {vim.enabled && (
          <Text color={vim.mode === 'normal' ? colors.warning : colors.info}>
            [{vim.mode === 'normal' ? 'NORMAL' : 'INSERT'}]{' '}
          </Text>
        )}
        <Text bold color={colors.cornsilk}>{symbols.userPrompt} </Text>
        <Box flexGrow={1}>
          <FastTextInput
            value={history.current}
            onChange={handleChange}
            onSubmit={handleSubmit}
            placeholder=""
            focus={!showModelPicker && !showReleaseNotes && !showEffortPicker && !showThemePicker && !showOutputStylePicker && !showGoalPanel && !showShortcutsHelp}
          />
        </Box>
        <GoodVibesHeart tick={goodVibesTick} thinkingColor={colors.thinking} />
      </Box>
    </Box>
  )
}
