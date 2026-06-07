import { useState, useCallback } from 'react'

export type VimMode = 'normal' | 'insert'

interface VimState {
  mode: VimMode
  enabled: boolean
}

interface VimActions {
  toggle: () => void
  enable: () => void
  disable: () => void
  enterInsert: () => void
  enterInsertAfter: () => void
  enterNormal: () => void
  openBelow: () => string
  openAbove: () => string
  moveLeft: (text: string, pos: number) => number
  moveDown: (text: string, pos: number) => number
  moveUp: (text: string, pos: number) => number
  moveRight: (text: string, pos: number) => number
  wordForward: (text: string, pos: number) => number
  wordBack: (text: string, pos: number) => number
  deleteLine: (text: string, pos: number) => string
  deleteChar: (text: string, pos: number) => { text: string; pos: number }
}

export function useVim(): { vim: VimState; vimActions: VimActions } {
  const [mode, setMode] = useState<VimMode>('insert')
  const [enabled, setEnabled] = useState(false)

  const toggle = useCallback(() => {
    setEnabled(prev => !prev)
    setMode('insert')
  }, [])

  const enable = useCallback(() => setEnabled(true), [])
  const disable = useCallback(() => { setEnabled(false); setMode('insert') }, [])
  const enterInsert = useCallback(() => setMode('insert'), [])
  const enterInsertAfter = useCallback(() => setMode('insert'), [])
  const enterNormal = useCallback(() => setMode('normal'), [])

  const openBelow = useCallback((): string => {
    setMode('insert')
    return '\n'
  }, [])

  const openAbove = useCallback((): string => {
    setMode('insert')
    return '\n'
  }, [])

  const moveLeft = useCallback((_text: string, pos: number): number => {
    return Math.max(0, pos - 1)
  }, [])

  const moveDown = useCallback((text: string, pos: number): number => {
    const lines = text.split('\n')
    const lineIdx = text.slice(0, pos).split('\n').length - 1
    if (lineIdx >= lines.length - 1) return pos
    const col = pos - (text.lastIndexOf('\n', pos - 1) + 1)
    const nextLineStart = text.indexOf('\n', pos) + 1
    if (nextLineStart === 0) return pos
    const nextLineEnd = text.indexOf('\n', nextLineStart)
    const nextLineLen = nextLineEnd === -1 ? text.length - nextLineStart : nextLineEnd - nextLineStart
    return nextLineStart + Math.min(col, nextLineLen)
  }, [])

  const moveUp = useCallback((text: string, pos: number): number => {
    const prevNewline = text.lastIndexOf('\n', pos - 1)
    if (prevNewline === -1) return pos
    const col = pos - (text.lastIndexOf('\n', pos - 1) + 1)
    const prevPrevNewline = text.lastIndexOf('\n', prevNewline - 1)
    const prevLineStart = prevPrevNewline + 1
    const prevLineLen = prevNewline - prevLineStart
    return prevLineStart + Math.min(col, prevLineLen)
  }, [])

  const moveRight = useCallback((text: string, pos: number): number => {
    return Math.min(text.length, pos + 1)
  }, [])

  const wordForward = useCallback((text: string, pos: number): number => {
    let i = pos
    while (i < text.length && /\w/.test(text[i])) i++
    while (i < text.length && !/\w/.test(text[i])) i++
    return i
  }, [])

  const wordBack = useCallback((text: string, pos: number): number => {
    let i = pos - 1
    while (i > 0 && !/\w/.test(text[i])) i--
    while (i > 0 && /\w/.test(text[i])) i--
    return i > 0 ? i + 1 : 0
  }, [])

  const deleteLine = useCallback((text: string, pos: number): string => {
    const lineStart = text.lastIndexOf('\n', pos - 1) + 1
    const lineEnd = text.indexOf('\n', pos)
    if (lineEnd === -1) return text.slice(0, lineStart).replace(/\n$/, '')
    return text.slice(0, lineStart) + text.slice(lineEnd + 1)
  }, [])

  const deleteChar = useCallback((text: string, pos: number): { text: string; pos: number } => {
    if (pos >= text.length) return { text, pos }
    return { text: text.slice(0, pos) + text.slice(pos + 1), pos }
  }, [])

  return {
    vim: { mode, enabled },
    vimActions: {
      toggle, enable, disable, enterInsert, enterInsertAfter, enterNormal,
      openBelow, openAbove, moveLeft, moveDown, moveUp, moveRight,
      wordForward, wordBack, deleteLine, deleteChar,
    },
  }
}
