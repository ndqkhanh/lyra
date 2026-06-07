import { useState, useCallback } from 'react'

export interface HistoryManager {
  current: string
  setCurrent: (value: string) => void
  navigateUp: () => void
  navigateDown: () => void
  addToHistory: (value: string) => void
  clear: () => void
}

export function useHistory(maxSize: number = 100): HistoryManager {
  const [history, setHistory] = useState<string[]>([])
  const [currentIndex, setCurrentIndex] = useState<number>(-1)
  const [current, setCurrent] = useState<string>('')
  const [tempInput, setTempInput] = useState<string>('')

  const navigateUp = useCallback(() => {
    if (history.length === 0) return

    if (currentIndex === -1) {
      // Save current input before navigating
      setTempInput(current)
      setCurrentIndex(history.length - 1)
      setCurrent(history[history.length - 1])
    } else if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
      setCurrent(history[currentIndex - 1])
    }
  }, [history, currentIndex, current])

  const navigateDown = useCallback(() => {
    if (currentIndex === -1) return

    if (currentIndex === history.length - 1) {
      // Restore temp input
      setCurrentIndex(-1)
      setCurrent(tempInput)
      setTempInput('')
    } else {
      setCurrentIndex(currentIndex + 1)
      setCurrent(history[currentIndex + 1])
    }
  }, [history, currentIndex, tempInput])

  const addToHistory = useCallback((value: string) => {
    if (!value.trim()) return

    setHistory(prev => {
      // Don't add duplicates of the last entry
      if (prev.length > 0 && prev[prev.length - 1] === value) {
        return prev
      }

      const newHistory = [...prev, value]
      // Keep only last maxSize entries
      if (newHistory.length > maxSize) {
        return newHistory.slice(-maxSize)
      }
      return newHistory
    })

    // Reset navigation state
    setCurrentIndex(-1)
    setTempInput('')
  }, [maxSize])

  const clear = useCallback(() => {
    setHistory([])
    setCurrentIndex(-1)
    setCurrent('')
    setTempInput('')
  }, [])

  return {
    current,
    setCurrent,
    navigateUp,
    navigateDown,
    addToHistory,
    clear
  }
}
