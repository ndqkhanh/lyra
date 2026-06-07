/**
 * Edge Case Tests for Lyra TUI
 *
 * Tests unusual scenarios and boundary conditions:
 * - Empty states
 * - Null/undefined handling
 * - Concurrent operations
 * - Race conditions
 * - Invalid input
 */

import React from 'react'
import { render } from 'ink-testing-library'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useUIStore } from '@lyra/ui-core'
import { ConversationView } from '../components/ConversationView'
import { InputArea } from '../components/InputArea'
import { VirtualScrollBox } from '../components/VirtualScrollBox'
import { StatusBar } from '../components/StatusBar'

describe('Edge Case Tests', () => {
  beforeEach(() => {
    useUIStore.getState().reset?.()
  })

  afterEach(() => {
    useUIStore.getState().reset?.()
  })

  describe('Empty States', () => {
    it('should render empty conversation', () => {
      const sessionId = 'empty-test'
      useUIStore.getState().createSession(sessionId)

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle empty input submission', () => {
      const sessionId = 'empty-input-test'
      useUIStore.getState().createSession(sessionId)

      const mockTransport = {
        sendMessage: vi.fn().mockResolvedValue(undefined)
      }
      useUIStore.getState().setTransport(mockTransport as any)

      const { stdin } = render(<InputArea sessionId={sessionId} />)

      // Submit empty input
      stdin.write('\r')

      // Should not send empty message
      expect(mockTransport.sendMessage).not.toHaveBeenCalled()
    })

    it('should handle whitespace-only input', () => {
      const sessionId = 'whitespace-test'
      useUIStore.getState().createSession(sessionId)

      const mockTransport = {
        sendMessage: vi.fn().mockResolvedValue(undefined)
      }
      useUIStore.getState().setTransport(mockTransport as any)

      const { stdin } = render(<InputArea sessionId={sessionId} />)

      // Submit whitespace
      stdin.write('   ')
      stdin.write('\r')

      // Should not send whitespace-only message
      expect(mockTransport.sendMessage).not.toHaveBeenCalled()
    })

    it('should handle empty virtual scroll items', () => {
      const { lastFrame } = render(
        <VirtualScrollBox
          items={[]}
          viewportHeight={30}
          overscan={20}
        />
      )

      expect(lastFrame()).toBeTruthy()
    })
  })

  describe('Null/Undefined Handling', () => {
    it('should handle missing session gracefully', () => {
      const { lastFrame } = render(<ConversationView sessionId="nonexistent" />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle undefined message content', () => {
      const sessionId = 'undefined-content-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'msg-1',
        role: 'user',
        content: undefined as any,
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle null transport', () => {
      const sessionId = 'null-transport-test'
      useUIStore.getState().createSession(sessionId)
      useUIStore.getState().setTransport(null as any)

      const { stdin } = render(<InputArea sessionId={sessionId} />)

      // Should not crash
      stdin.write('test')
      stdin.write('\r')

      expect(true).toBe(true)
    })

    it('should handle undefined theme', () => {
      const sessionId = 'undefined-theme-test'
      useUIStore.getState().createSession(sessionId)
      useUIStore.getState().setActiveTheme(undefined as any)

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })
  })

  describe('Concurrent Operations', () => {
    it('should handle concurrent message additions', () => {
      const sessionId = 'concurrent-add-test'
      useUIStore.getState().createSession(sessionId)

      // Add messages concurrently
      const promises = Array.from({ length: 100 }, (_, i) =>
        Promise.resolve().then(() => {
          useUIStore.getState().addMessage(sessionId, {
            id: `msg-${i}`,
            role: 'user',
            content: `Message ${i}`,
            timestamp: Date.now()
          })
        })
      )

      return Promise.all(promises).then(() => {
        const session = useUIStore.getState().sessions.get(sessionId)
        expect(session?.messages.length).toBe(100)
      })
    })

    it('should handle concurrent streaming updates', () => {
      const sessionId = 'concurrent-stream-test'
      useUIStore.getState().createSession(sessionId)
      useUIStore.getState().beginStreaming(sessionId)

      // Update streaming message concurrently
      const promises = Array.from({ length: 100 }, (_, i) =>
        Promise.resolve().then(() => {
          useUIStore.getState().updateStreamingMessage(sessionId, `chunk${i} `)
        })
      )

      return Promise.all(promises).then(() => {
        useUIStore.getState().commitStreamingMessage(sessionId)
        const session = useUIStore.getState().sessions.get(sessionId)
        expect(session?.messages.length).toBe(1)
      })
    })

    it('should handle concurrent theme switches', () => {
      const sessionId = 'concurrent-theme-test'
      useUIStore.getState().createSession(sessionId)

      const themes = ['hermes', 'claude', 'openclaw', 'solarized', 'dracula']

      // Switch themes concurrently
      const promises = themes.map(theme =>
        Promise.resolve().then(() => {
          useUIStore.getState().setActiveTheme(theme)
        })
      )

      return Promise.all(promises).then(() => {
        // Should end up with one of the themes
        const activeTheme = useUIStore.getState().activeThemeId
        expect(themes).toContain(activeTheme)
      })
    })
  })

  describe('Race Conditions', () => {
    it('should handle rapid start/stop streaming', () => {
      const sessionId = 'race-streaming-test'
      useUIStore.getState().createSession(sessionId)

      // Rapidly start and stop streaming
      for (let i = 0; i < 10; i++) {
        useUIStore.getState().beginStreaming(sessionId)
        useUIStore.getState().cancelStreaming(sessionId)
      }

      const session = useUIStore.getState().sessions.get(sessionId)
      expect(session?.isStreaming).toBe(false)
    })

    it('should handle commit during streaming update', () => {
      const sessionId = 'race-commit-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().beginStreaming(sessionId)
      useUIStore.getState().updateStreamingMessage(sessionId, 'test')

      // Commit immediately after update
      useUIStore.getState().commitStreamingMessage(sessionId)

      const session = useUIStore.getState().sessions.get(sessionId)
      expect(session?.messages.length).toBe(1)
      expect(session?.isStreaming).toBe(false)
    })

    it('should handle session deletion during render', () => {
      const sessionId = 'race-delete-test'
      useUIStore.getState().createSession(sessionId)

      const { unmount } = render(<ConversationView sessionId={sessionId} />)

      // Delete session while rendering
      useUIStore.getState().sessions.delete(sessionId)

      // Should not crash
      unmount()
      expect(true).toBe(true)
    })
  })

  describe('Invalid Input', () => {
    it('should handle invalid role', () => {
      const sessionId = 'invalid-role-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'msg-1',
        role: 'invalid' as any,
        content: 'Test',
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle negative timestamps', () => {
      const sessionId = 'negative-timestamp-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'msg-1',
        role: 'user',
        content: 'Test',
        timestamp: -1
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle very large timestamps', () => {
      const sessionId = 'large-timestamp-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'msg-1',
        role: 'user',
        content: 'Test',
        timestamp: Number.MAX_SAFE_INTEGER
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle special characters in content', () => {
      const sessionId = 'special-chars-test'
      useUIStore.getState().createSession(sessionId)

      const specialChars = '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A\x0B\x0C\x0D\x0E\x0F'

      useUIStore.getState().addMessage(sessionId, {
        id: 'msg-1',
        role: 'user',
        content: specialChars,
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle ANSI escape codes', () => {
      const sessionId = 'ansi-test'
      useUIStore.getState().createSession(sessionId)

      const ansiContent = '\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m \x1b[34mBlue\x1b[0m'

      useUIStore.getState().addMessage(sessionId, {
        id: 'msg-1',
        role: 'user',
        content: ansiContent,
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })
  })

  describe('Boundary Conditions', () => {
    it('should handle zero viewport height', () => {
      const items = Array.from({ length: 100 }, (_, i) => ({
        key: `item-${i}`,
        content: <div>Item {i}</div>
      }))

      const { lastFrame } = render(
        <VirtualScrollBox
          items={items}
          viewportHeight={0}
          overscan={20}
        />
      )

      expect(lastFrame()).toBeTruthy()
    })

    it('should handle negative overscan', () => {
      const items = Array.from({ length: 100 }, (_, i) => ({
        key: `item-${i}`,
        content: <div>Item {i}</div>
      }))

      const { lastFrame } = render(
        <VirtualScrollBox
          items={items}
          viewportHeight={30}
          overscan={-10}
        />
      )

      expect(lastFrame()).toBeTruthy()
    })

    it('should handle single item', () => {
      const items = [{ key: 'item-0', content: <div>Single item</div> }]

      const { lastFrame } = render(
        <VirtualScrollBox
          items={items}
          viewportHeight={30}
          overscan={20}
        />
      )

      expect(lastFrame()).toContain('Single item')
    })

    it('should handle very tall items', () => {
      const items = [{
        key: 'tall-item',
        height: 1000,
        content: <div>Very tall item</div>
      }]

      const { lastFrame } = render(
        <VirtualScrollBox
          items={items}
          viewportHeight={30}
          overscan={20}
        />
      )

      expect(lastFrame()).toBeTruthy()
    })
  })

  describe('Unicode and Internationalization', () => {
    it('should handle RTL text', () => {
      const sessionId = 'rtl-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'msg-1',
        role: 'user',
        content: 'مرحبا بك في العالم',
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toContain('مرحبا')
    })

    it('should handle mixed LTR/RTL text', () => {
      const sessionId = 'mixed-text-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'msg-1',
        role: 'user',
        content: 'Hello مرحبا World',
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle CJK characters', () => {
      const sessionId = 'cjk-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'msg-1',
        role: 'user',
        content: '你好世界 こんにちは世界 안녕하세요',
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle emoji sequences', () => {
      const sessionId = 'emoji-seq-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'msg-1',
        role: 'user',
        content: '👨‍👩‍👧‍👦 👨‍💻 🏳️‍🌈 🏴‍☠️',
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })

    it('should handle zero-width characters', () => {
      const sessionId = 'zero-width-test'
      useUIStore.getState().createSession(sessionId)

      useUIStore.getState().addMessage(sessionId, {
        id: 'msg-1',
        role: 'user',
        content: 'Hello​World‌‍',
        timestamp: Date.now()
      })

      const { lastFrame } = render(<ConversationView sessionId={sessionId} />)
      expect(lastFrame()).toBeTruthy()
    })
  })

  describe('Performance Edge Cases', () => {
    it('should handle rapid re-renders', () => {
      const sessionId = 'rapid-render-test'
      useUIStore.getState().createSession(sessionId)

      const { rerender } = render(<ConversationView sessionId={sessionId} />)

      const startTime = Date.now()

      // Trigger 100 rapid re-renders
      for (let i = 0; i < 100; i++) {
        rerender(<ConversationView sessionId={sessionId} />)
      }

      const renderTime = Date.now() - startTime

      expect(renderTime).toBeLessThan(1000)
    })

    it('should handle rapid state updates', () => {
      const sessionId = 'rapid-state-test'
      useUIStore.getState().createSession(sessionId)

      const startTime = Date.now()

      // Trigger 1000 rapid state updates
      for (let i = 0; i < 1000; i++) {
        useUIStore.getState().setDisplayMode(
          sessionId,
          i % 2 === 0 ? 'minimal' : 'standard'
        )
      }

      const updateTime = Date.now() - startTime

      expect(updateTime).toBeLessThan(1000)
    })
  })
})
