import {
  toRenderItems,
  applyDisplayPolicy,
  partitionRenderItems,
} from '../utils/rendering'
import type { Message, UserTextItem, AssistantTextItem } from '../types'

function makeUserMsg(id: string, content: string): Message {
  return { id, role: 'user', content, timestamp: Date.now() }
}

function makeAssistantMsg(id: string, content: string): Message {
  return { id, role: 'assistant', content, timestamp: Date.now() }
}

function makeAssistantWithThinking(
  id: string,
  content: string,
  thinkingContent: string,
  durationMs = 1000,
): Message {
  return {
    id,
    role: 'assistant',
    content,
    timestamp: Date.now(),
    thinking: { content: thinkingContent, durationMs, collapsed: false },
  }
}

function makeAssistantWithToolCalls(
  id: string,
  content: string,
  toolCalls: Array<{
    id: string
    name: string
    args: Record<string, unknown>
    status: 'running' | 'completed' | 'error'
  }>,
): Message {
  return {
    id,
    role: 'assistant',
    content,
    timestamp: Date.now(),
    toolCalls: toolCalls.map((tc) => ({
      ...tc,
      startTime: Date.now(),
    })),
  } as Message
}

describe('toRenderItems', () => {
  it('converts user message to user-text item', () => {
    const msg = makeUserMsg('u1', 'Hello')
    const items = toRenderItems([msg], [])
    expect(items).toHaveLength(1)
    expect(items[0]!.kind).toBe('user-text')
    expect((items[0] as UserTextItem).content).toBe('Hello')
    expect(items[0]!.committed).toBe(true)
  })

  it('converts assistant message to assistant-text item', () => {
    const msg = makeAssistantMsg('a1', 'Hi there')
    const items = toRenderItems([msg], [])
    expect(items).toHaveLength(1)
    expect(items[0]!.kind).toBe('assistant-text')
    expect((items[0] as AssistantTextItem).content).toBe('Hi there')
  })

  it('includes thinking block when present', () => {
    const msg = makeAssistantWithThinking('a1', 'response', 'Let me think...', 2000)
    const items = toRenderItems([msg], [])
    const thinking = items.find((i) => i.kind === 'thinking')
    expect(thinking).toBeDefined()
    expect((thinking as any).content).toBe('Let me think...')
    expect((thinking as any).durationSec).toBe(2)
  })

  it('includes tool execution items', () => {
    const msg = makeAssistantWithToolCalls('a1', 'Done', [
      { id: 't1', name: 'read_file', args: { path: '/f' }, status: 'completed' },
    ])
    const items = toRenderItems([msg], [])
    const tools = items.filter((i) => i.kind === 'tool-execution')
    expect(tools).toHaveLength(1)
    expect((tools[0] as any).toolName).toBe('read_file')
    expect((tools[0] as any).status).toBe('completed')
  })

  it('handles system messages as errors', () => {
    const msg = { id: 's1', role: 'system', content: 'Error: something went wrong', timestamp: Date.now() }
    const items = toRenderItems([msg as Message], [])
    expect(items).toHaveLength(1)
    expect(items[0]!.kind).toBe('error')
  })

  it('handles system messages as notices', () => {
    const msg = { id: 's1', role: 'system', content: 'Process completed', timestamp: Date.now() }
    const items = toRenderItems([msg as Message], [])
    expect(items).toHaveLength(1)
    expect(items[0]!.kind).toBe('system-notice')
  })

  it('marks committed items as committed=true', () => {
    const msg = makeUserMsg('u1', 'Hello')
    const items = toRenderItems([msg], [])
    for (const item of items) {
      expect(item.committed).toBe(true)
    }
  })

  it('marks preview items as committed=false', () => {
    const msg = makeAssistantMsg('a1', 'streaming...')
    const items = toRenderItems([], [msg])
    for (const item of items) {
      expect(item.committed).toBe(false)
    }
  })

  it('caches committed message conversions', () => {
    const msg = makeUserMsg('u1', 'Hello')
    const items1 = toRenderItems([msg], [])
    const items2 = toRenderItems([msg], [])
    // Same references from WeakMap cache
    expect(items1[0]).toBe(items2[0])
  })

  it('handles empty arrays', () => {
    const items = toRenderItems([], [])
    expect(items).toHaveLength(0)
  })

  it('handles multiple messages', () => {
    const msgs = [makeUserMsg('u1', 'Q'), makeAssistantMsg('a1', 'A')]
    const items = toRenderItems(msgs, [])
    expect(items.length).toBeGreaterThanOrEqual(2)
  })

  it('marks streaming assistant as streaming=true', () => {
    const msg: Message = {
      id: 'a1',
      role: 'assistant',
      content: 'partial...',
      timestamp: Date.now(),
      streaming: true,
    }
    const items = toRenderItems([], [msg])
    const textItem = items.find((i) => i.kind === 'assistant-text') as AssistantTextItem
    expect(textItem.streaming).toBe(true)
  })
})

describe('applyDisplayPolicy', () => {
  const items = toRenderItems(
    [
      makeUserMsg('u1', 'Hello'),
      makeAssistantWithThinking('a1', 'Response', 'Thinking...'),
      makeAssistantWithToolCalls('a2', 'Done', [
        { id: 't1', name: 'grep', args: { pattern: 'x' }, status: 'completed' },
      ]),
    ],
    [],
  )

  it('returns all items in debug mode', () => {
    const result = applyDisplayPolicy(items, 'debug')
    expect(result.length).toBe(items.length)
  })

  it('filters thinking in minimal mode', () => {
    const result = applyDisplayPolicy(items, 'minimal')
    const thinking = result.filter((i) => i.kind === 'thinking')
    expect(thinking).toHaveLength(0)
  })

  it('collapses thinking in standard mode', () => {
    const result = applyDisplayPolicy(items, 'standard')
    const thinking = result.filter((i) => i.kind === 'thinking')
    for (const t of thinking) {
      expect(t.collapsed).toBe(true)
    }
  })

  it('strips tool args in minimal mode', () => {
    const result = applyDisplayPolicy(items, 'minimal')
    const tools = result.filter((i) => i.kind === 'tool-execution')
    for (const t of tools) {
      expect((t as any).args).toEqual({})
      expect((t as any).result).toBeUndefined()
    }
  })

  it('handles focus mode (same as standard)', () => {
    const result = applyDisplayPolicy(items, 'focus')
    expect(result.length).toBeGreaterThan(0)
  })
})

describe('partitionRenderItems', () => {
  it('splits by committed flag', () => {
    const committed = toRenderItems([makeUserMsg('u1', 'Hello')], [])
    const uncommitted = toRenderItems([], [makeAssistantMsg('a1', 'streaming...')])
    const all = [...committed, ...uncommitted]

    const { staticItems, liveItems } = partitionRenderItems(all)
    expect(staticItems).toHaveLength(committed.length)
    expect(liveItems).toHaveLength(uncommitted.length)
  })

  it('returns empty arrays for empty input', () => {
    const { staticItems, liveItems } = partitionRenderItems([])
    expect(staticItems).toHaveLength(0)
    expect(liveItems).toHaveLength(0)
  })
})
