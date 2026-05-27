/**
 * Fast-Echo Text Input Component
 *
 * Achieves <10ms input latency by writing directly to stdout for ASCII characters,
 * bypassing React's render cycle. Based on Hermes Agent's TextInput implementation.
 *
 * Key Features:
 * - Fast-echo for ASCII printable characters (instant feedback)
 * - Grapheme-aware cursor movement (proper emoji handling)
 * - 16ms batched React updates
 * - Fallback to slow path for emoji, IME, multi-line
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Box, Text, useInput, useStdout } from 'ink'

interface FastTextInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit?: () => void
  placeholder?: string
  focus?: boolean
}

const ASCII_PRINTABLE_RE = /^[\x20-\x7e]+$/
const FRAME_BATCH_MS = 16  // 60fps

// Grapheme segmentation for proper Unicode handling
let _seg: Intl.Segmenter | null = null
const seg = () => (_seg ??= new Intl.Segmenter(undefined, { granularity: 'grapheme' }))

const STOP_CACHE_MAX = 32
const stopCache = new Map<string, number[]>()

function graphemeStops(s: string): number[] {
  const hit = stopCache.get(s)
  if (hit) return hit

  const stops = [0]

  for (const { index } of seg().segment(s)) {
    if (index > 0) stops.push(index)
  }

  if (stops.at(-1) !== s.length) {
    stops.push(s.length)
  }

  stopCache.set(s, stops)

  // LRU eviction
  if (stopCache.size > STOP_CACHE_MAX) {
    const oldest = stopCache.keys().next().value
    if (oldest !== undefined) stopCache.delete(oldest)
  }

  return stops
}

function snapPos(s: string, p: number): number {
  const pos = Math.max(0, Math.min(p, s.length))
  let last = 0

  for (const stop of graphemeStops(s)) {
    if (stop > pos) break
    last = stop
  }

  return last
}

function prevPos(s: string, p: number): number {
  const pos = snapPos(s, p)
  let prev = 0

  for (const stop of graphemeStops(s)) {
    if (stop >= pos) return prev
    prev = stop
  }

  return prev
}

function nextPos(s: string, p: number): number {
  const pos = snapPos(s, p)

  for (const stop of graphemeStops(s)) {
    if (stop > pos) return stop
  }

  return s.length
}

// Simple string width calculation (ASCII = 1, others = 2)
function stringWidth(s: string): number {
  let width = 0
  for (let i = 0; i < s.length; i++) {
    const code = s.charCodeAt(i)
    // ASCII printable = 1 cell, everything else = 2 cells (rough estimate)
    width += (code >= 0x20 && code <= 0x7e) ? 1 : 2
  }
  return width
}

export function FastTextInput({
  value,
  onChange,
  onSubmit,
  placeholder = '',
  focus = true
}: FastTextInputProps) {
  const { stdout } = useStdout()
  const [cursor, setCursor] = useState(value.length)

  // Refs for fast-echo (bypass React state)
  const valueRef = useRef(value)
  const cursorRef = useRef(cursor)
  const lineWidthRef = useRef(stringWidth(value))

  // Batching timers
  const updateTimer = useRef<NodeJS.Timeout | null>(null)
  const pendingValue = useRef<string | null>(null)
  const pendingCursor = useRef<number | null>(null)

  // Update refs when props change
  useEffect(() => {
    valueRef.current = value
    cursorRef.current = cursor
    lineWidthRef.current = stringWidth(value)
  }, [value, cursor])

  // Sync cursor when value changes externally
  useEffect(() => {
    setCursor(value.length)
  }, [value])

  // Cleanup timers
  useEffect(() => {
    return () => {
      if (updateTimer.current) {
        clearTimeout(updateTimer.current)
      }
    }
  }, [])

  // Schedule batched React update
  const scheduleStateUpdate = useCallback((nextValue: string, nextCursor: number) => {
    pendingValue.current = nextValue
    pendingCursor.current = nextCursor

    if (updateTimer.current) {
      return  // Already scheduled
    }

    updateTimer.current = setTimeout(() => {
      updateTimer.current = null

      if (pendingValue.current !== null) {
        onChange(pendingValue.current)
        setCursor(pendingCursor.current!)
        pendingValue.current = null
        pendingCursor.current = null
      }
    }, FRAME_BATCH_MS)
  }, [onChange])

  // Fast-echo preconditions
  const canFastEchoBase = useCallback(() => {
    return (
      focus &&
      stdout?.isTTY &&
      process.env.TERM_PROGRAM !== 'Apple_Terminal'  // Terminal.app has artifacts
    )
  }, [focus, stdout])

  const canFastAppend = useCallback((text: string) => {
    return (
      canFastEchoBase() &&
      cursorRef.current === valueRef.current.length &&  // At end
      valueRef.current.length > 0 &&                    // Has content
      !valueRef.current.includes('\n') &&               // Single line
      ASCII_PRINTABLE_RE.test(text) &&                  // ASCII only
      lineWidthRef.current + text.length < 80           // Won't wrap (assume 80 cols)
    )
  }, [canFastEchoBase])

  const canFastBackspace = useCallback(() => {
    const c = cursorRef.current
    const v = valueRef.current

    return (
      canFastEchoBase() &&
      c === v.length &&           // At end
      c > 0 &&                    // Has content
      !v.includes('\n') &&        // Single line
      ASCII_PRINTABLE_RE.test(v[c - 1] || '')  // Deleting ASCII
    )
  }, [canFastEchoBase])

  // Handle character input
  const handleCharacter = useCallback((char: string) => {
    if (canFastAppend(char)) {
      // FAST PATH: Write immediately to stdout
      stdout!.write(char)

      // Update refs immediately
      valueRef.current = valueRef.current + char
      cursorRef.current = cursorRef.current + char.length
      lineWidthRef.current += char.length

      // Schedule batched React update
      scheduleStateUpdate(valueRef.current, cursorRef.current)
      return
    }

    // SLOW PATH: Normal React update (emoji, IME, etc.)
    const newValue = value.slice(0, cursor) + char + value.slice(cursor)
    onChange(newValue)
    setCursor(cursor + char.length)
  }, [canFastAppend, stdout, value, cursor, onChange, scheduleStateUpdate])

  // Handle backspace
  const handleBackspace = useCallback(() => {
    if (canFastBackspace()) {
      // FAST PATH: Write immediately
      stdout!.write('\b \b')  // Backspace, space, backspace

      // Update refs immediately
      valueRef.current = valueRef.current.slice(0, -1)
      cursorRef.current = cursorRef.current - 1
      lineWidthRef.current -= 1

      // Schedule batched update
      scheduleStateUpdate(valueRef.current, cursorRef.current)
      return
    }

    // SLOW PATH: Normal React update
    if (cursor > 0) {
      const prev = prevPos(value, cursor)
      const newValue = value.slice(0, prev) + value.slice(cursor)
      onChange(newValue)
      setCursor(prev)
    }
  }, [canFastBackspace, stdout, value, cursor, onChange, scheduleStateUpdate])

  // Handle delete
  const handleDelete = useCallback(() => {
    if (cursor < value.length) {
      const next = nextPos(value, cursor)
      const newValue = value.slice(0, cursor) + value.slice(next)
      onChange(newValue)
    }
  }, [value, cursor, onChange])

  // Handle arrow keys
  const handleLeftArrow = useCallback(() => {
    if (cursor > 0) {
      setCursor(prevPos(value, cursor))
    }
  }, [value, cursor])

  const handleRightArrow = useCallback(() => {
    if (cursor < value.length) {
      setCursor(nextPos(value, cursor))
    }
  }, [value, cursor])

  const handleHome = useCallback(() => {
    setCursor(0)
  }, [])

  const handleEnd = useCallback(() => {
    setCursor(value.length)
  }, [value])

  // Input handler
  useInput((input, key) => {
    if (!focus) return

    // Submit on Enter
    if (key.return) {
      onSubmit?.()
      return
    }

    // Backspace
    if (key.backspace || key.delete) {
      if (key.delete) {
        handleDelete()
      } else {
        handleBackspace()
      }
      return
    }

    // Arrow keys
    if (key.leftArrow) {
      handleLeftArrow()
      return
    }

    if (key.rightArrow) {
      handleRightArrow()
      return
    }

    // Ctrl+A (Home)
    if (key.ctrl && input === 'a') {
      handleHome()
      return
    }

    // Ctrl+E (End)
    if (key.ctrl && input === 'e') {
      handleEnd()
      return
    }

    // Ctrl+U (clear line)
    if (key.ctrl && input === 'u') {
      onChange('')
      setCursor(0)
      return
    }

    // Regular character input
    if (input && !key.ctrl && !key.meta) {
      handleCharacter(input)
    }
  }, { isActive: focus })

  // Render
  const displayValue = value || placeholder
  const showCursor = focus && cursor >= 0

  return (
    <Box>
      <Text>
        {displayValue.slice(0, cursor)}
        {showCursor && <Text inverse>{displayValue[cursor] || ' '}</Text>}
        {displayValue.slice(cursor + 1)}
      </Text>
    </Box>
  )
}
