import { useEffect, useRef, useState } from 'react'

/**
 * Hook for handling streaming text updates
 */
export function useStreamingText(_sessionId: string, _messageId: string) {
  const [text, setText] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const bufferRef = useRef<string[]>([])
  const timeoutRef = useRef<NodeJS.Timeout>()

  const appendText = (chunk: string) => {
    bufferRef.current.push(chunk)

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    timeoutRef.current = setTimeout(() => {
      const fullText = bufferRef.current.join('')
      setText(fullText)
      bufferRef.current = []
    }, 16) // ~60fps
  }

  const startStreaming = () => {
    setIsStreaming(true)
  }

  const stopStreaming = () => {
    setIsStreaming(false)
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    // Flush remaining buffer
    if (bufferRef.current.length > 0) {
      const fullText = bufferRef.current.join('')
      setText(fullText)
      bufferRef.current = []
    }
  }

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  return {
    text,
    isStreaming,
    appendText,
    startStreaming,
    stopStreaming
  }
}

/**
 * Hook for handling real-time updates
 */
export function useRealtimeUpdates(sessionId: string) {
  const [updateCount, setUpdateCount] = useState(0)

  const triggerUpdate = () => {
    setUpdateCount(prev => prev + 1)
  }

  useEffect(() => {
    // Subscribe to external updates (e.g., from WebSocket)
    // In a real implementation, this would subscribe to a WebSocket or EventSource
    // For now, we'll just set up the infrastructure

    return () => {
      // Cleanup subscription
    }
  }, [sessionId])

  return {
    updateCount,
    triggerUpdate
  }
}

/**
 * Hook for handling keyboard shortcuts
 * Note: This is for terminal/CLI context, not browser DOM
 */
export function useKeyboardShortcuts(_handlers: Record<string, () => void>) {
  // In Ink/terminal context, keyboard handling is done via useInput hook
  // This is a placeholder for future browser-based implementation
  useEffect(() => {
    // No-op in terminal context
    return () => {
      // Cleanup
    }
  }, [])
}

/**
 * Hook for auto-scrolling to bottom
 * Note: This is simplified for terminal context
 */
export function useAutoScroll(_enabled: boolean = true) {
  const [isAtBottom, setIsAtBottom] = useState(true)

  const scrollToBottom = () => {
    setIsAtBottom(true)
  }

  const handleScroll = () => {
    // No-op in terminal context
  }

  return {
    scrollRef: { current: null },
    isAtBottom,
    scrollToBottom,
    handleScroll
  }
}
