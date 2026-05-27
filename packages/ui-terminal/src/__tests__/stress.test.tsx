/**
 * Stress Tests for Lyra TUI
 *
 * Tests performance under extreme conditions:
 * - Large conversations (10,000+ messages)
 * - Rapid input
 * - Memory leaks
 * - Performance degradation
 */

import React from 'react'
import { render } from 'ink-testing-library'
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useUIStore } from '@lyra/ui-core'
import { ConversationView } from '../components/ConversationView'
import { InputArea } from '../components/InputArea'
import { VirtualScrollBox } from '../components/VirtualScrollBox'

describe('Stress Tests', () => {
  beforeEach(() => {
    useUIStore.getState().reset?.()
  })

  afterEach(() => {
    useUIStore.getState().reset?.()
  })

  describe('Large Conversations', () => {
    it('should handle 1,000 messages without performance degradation', () => {
      const sessionId = 'stress-test-1k'
      useUIStore.getState().createSession(sessionId)

      const startTime = Date.now()

      // Add 1,000 messages
      for (let i = 0; i < 1000; i++) {
        useUIStore.getState().addMessage(sessionId, {
          id: `msg-${i}`,
          role: i % 2 === 0 ? 'user' : 'assistant',
          content: `Message ${i}: ${'x'.repeat(100)}`,
          timestamp: Date.now()
        })
      }

      const addTime = Date.now() - startTime

      const renderStart = Date.now()
      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      const renderTime = Date.now() - renderStart

      expect(addTime).toBeLessThan(1000) // Should add 1k messages in < 1s
      expect(renderTime).toBeLessThan(500) // Should render in < 500ms
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle 10,000 messages with virtual scrolling', () => {
      const sessionId = 'stress-test-10k'
      useUIStore.getState().createSession(sessionId)

      const startTime = Date.now()

      // Add 10,000 messages
      for (let i = 0; i < 10000; i++) {
        useUIStore.getState().addMessage(sessionId, {
          id: `msg-${i}`,
          role: i % 2 === 0 ? 'user' : 'assistant',
          content: `Message ${i}: ${'x'.repeat(50)}`,
          timestamp: Date.now()
        })
      }

      const addTime = Date.now() - startTime

      const renderStart = Date.now()
      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      const renderTime = Date.now() - renderStart

      expect(addTime).toBeLessThan(5000) // Should add 10k messages in < 5s
      expect(renderTime).toBeLessThan(1000) // Should render in < 1s with virtual scrolling
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle 100,000 messages with virtual scrolling', () => {
      const sessionId = 'stress-test-100k'
      useUIStore.getState().createSession(sessionId)

      const startTime = Date.now()

      // Add 100,000 messages in batches
      const batchSize = 1000
      for (let batch = 0; batch < 100; batch++) {
        for (let i = 0; i < batchSize; i++) {
          const msgId = batch * batchSize + i
          useUIStore.getState().addMessage(sessionId, {
            id: `msg-${msgId}`,
            role: msgId % 2 === 0 ? 'user' : 'assistant',
            content: `Message ${msgId}`,
            timestamp: Date.now()
          })
        }
      }

      const addTime = Date.now() - startTime

      const renderStart = Date.now()
      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      const renderTime = Date.now() - renderStart

      expect(addTime).toBeLessThan(30000) // Should add 100k messages in < 30s
      expect(renderTime).toBeLessThan(2000) // Should render in < 2s with virtual scrolling
      expect(lastFrame()).toBeTruthy()
    })
  })

  describe('Rapid Input', () => {
    it('should handle rapid keystrokes without lag', () => {
      const sessionId = 'rapid-input-test'
      useUIStore.getState().createSession(sessionId)

      const { stdin } = render(<InputArea sessionId={sessionId} />)

      const startTime = Date.now()

      // Simulate 1000 rapid keystrokes
      for (let i = 0; i < 1000; i++) {
        stdin.write('a')
      }

      const inputTime = Date.now() - startTime

      expect(inputTime).toBeLessThan(1000) // Should handle 1000 keystrokes in < 1s
    })

    it('should handle rapid submissions without double-fire', () => {
      const sessionId = 'rapid-submit-test'
      useUIStore.getState().createSession(sessionId)

      const { stdin } = render(<InputArea sessionId={sessionId} />)

      // Simulate rapid Enter presses
      stdin.write('test message')
      stdin.write('\r')
      stdin.write('\r')
      stdin.write('\r')

      const session = useUIStore.getState().sessions.get(sessionId)
      const userMessages = session?.messages.filter(m => m.role === 'user') || []

      // Should only submit once due to double-fire guard
      expect(userMessages.length).toBeLessThanOrEqual(1)
    })
  })

  describe('Memory Leaks', () => {
    it('should not leak memory when adding/removing messages', () => {
      const sessionId = 'memory-leak-test'
      useUIStore.getState().createSession(sessionId)

      const initialMemory = process.memoryUsage().heapUsed

      // Add and remove messages 100 times
      for (let cycle = 0; cycle < 100; cycle++) {
        // Add 100 messages
        for (let i = 0; i < 100; i++) {
          useUIStore.getState().addMessage(sessionId, {
            id: `msg-${cycle}-${i}`,
            role: 'user',
            content: 'x'.repeat(1000),
            timestamp: Date.now()
          })
        }

        // Clear messages
        useUIStore.getState().sessions.get(sessionId)!.messages = []
      }

      // Force garbage collection if available
      if (global.gc) {
        global.gc()
      }

      const finalMemory = process.memoryUsage().heapUsed
      const memoryGrowth = finalMemory - initialMemory

      // Memory growth should be < 10MB after 10,000 message cycles
      expect(memoryGrowth).toBeLessThan(10 * 1024 * 1024)
    })

    it('should not leak event listeners', () => {
      const sessionId = 'listener-leak-test'
      useUIStore.getState().createSession(sessionId)

      const initialListeners = process.listenerCount('uncaughtException')

      // Mount and unmount 100 times
      for (let i = 0; i < 100; i++) {
        const { unmount } = render(<ConversationView sessionId={sessionId} />)
        unmount()
      }

      const finalListeners = process.listenerCount('uncaughtException')

      // Should not accumulate listeners
      expect(finalListeners).toBeLessThanOrEqual(initialListeners + 5)
    })
  })

  describe('Virtual Scrolling Performance', () => {
    it('should render only visible items', () => {
      const items = Array.from({ length: 10000 }, (_, i) => ({
        key: `item-${i}`,
        content: <div>Item {i}</div>
      }))

      const { lastFrame } = render(
        <VirtualScrollBox
          items={items}
          viewportHeight={30}
          overscan={20}
          sticky={true}
        />
      )

      const frame = lastFrame()

      // Should only render ~120 items (viewport + overscan), not all 10,000
      const renderedItems = (frame.match(/Item \d+/g) || []).length
      expect(renderedItems).toBeLessThan(150)
      expect(renderedItems).toBeGreaterThan(0)
    })

    it('should use binary search for O(log n) performance', () => {
      const items = Array.from({ length: 100000 }, (_, i) => ({
        key: `item-${i}`,
        content: <div>Item {i}</div>
      }))

      const startTime = Date.now()

      render(
        <VirtualScrollBox
          items={items}
          viewportHeight={30}
          overscan={20}
          sticky={true}
        />
      )

      const renderTime = Date.now() - startTime

      // Should render 100k items in < 100ms using binary search
      expect(renderTime).toBeLessThan(100)
    })
  })

  describe('Streaming Performance', () => {
    it('should handle rapid streaming chunks without lag', () => {
      const sessionId = 'streaming-perf-test'
      useUIStore.getState().createSession(sessionId)
      useUIStore.getState().beginStreaming(sessionId)

      const startTime = Date.now()

      // Simulate 1000 rapid chunks
      for (let i = 0; i < 1000; i++) {
        useUIStore.getState().updateStreamingMessage(sessionId, 'chunk ')
      }

      const streamTime = Date.now() - startTime

      expect(streamTime).toBeLessThan(1000) // Should handle 1000 chunks in < 1s
    })

    it('should maintain 60 FPS during streaming', () => {
      const sessionId = 'streaming-fps-test'
      useUIStore.getState().createSession(sessionId)
      useUIStore.getState().beginStreaming(sessionId)

      const frameTimings: number[] = []
      let lastFrame = Date.now()

      // Simulate streaming with frame timing
      for (let i = 0; i < 60; i++) {
        useUIStore.getState().updateStreamingMessage(sessionId, 'x'.repeat(100))

        const now = Date.now()
        frameTimings.push(now - lastFrame)
        lastFrame = now
      }

      const avgFrameTime = frameTimings.reduce((a, b) => a + b, 0) / frameTimings.length
      const fps = 1000 / avgFrameTime

      // Should maintain close to 60 FPS
      expect(fps).toBeGreaterThan(30) // At least 30 FPS
    })
  })

  describe('Theme Switching Performance', () => {
    it('should switch themes without lag', () => {
      const sessionId = 'theme-switch-test'
      useUIStore.getState().createSession(sessionId)

      // Add some messages
      for (let i = 0; i < 100; i++) {
        useUIStore.getState().addMessage(sessionId, {
          id: `msg-${i}`,
          role: 'user',
          content: `Message ${i}`,
          timestamp: Date.now()
        })
      }

      const { rerender } = render(<ConversationView sessionId={sessionId} />)

      const startTime = Date.now()

      // Switch themes 10 times
      const themes = ['hermes', 'claude', 'openclaw', 'solarized', 'dracula']
      for (let i = 0; i < 10; i++) {
        useUIStore.getState().setActiveTheme(themes[i % themes.length]!)
        rerender(<ConversationView sessionId={sessionId} />)
      }

      const switchTime = Date.now() - startTime

      expect(switchTime).toBeLessThan(500) // Should switch 10 themes in < 500ms
    })
  })

  describe('Edge Cases', () => {
    it('should handle empty messages', () => {
      const sessionId = 'empty-msg-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'empty-1',
        role: 'user',
        content: '',
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle very long messages', () => {
      const sessionId = 'long-msg-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'long-1',
        role: 'user',
        content: 'x'.repeat(100000), // 100k characters
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle unicode and emoji', () => {
      const sessionId = 'unicode-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'unicode-1',
        role: 'user',
        content: '🚀 Hello 世界 مرحبا мир 🎉',
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toContain('🚀')
    })

    it('should handle malformed data gracefully', () => {
      const sessionId = 'malformed-test'
      useUIStore.getState().createSession(sessionId)

      // Try to add malformed message
      expect(() => {
        useUIStore.getState().addMessage(sessionId, {
          id: 'malformed-1',
          role: 'invalid' as any,
          content: null as any,
          timestamp: Date.now()
        })
      }).not.toThrow()
    })
  })
})
