import {
  partitionForRendering,
  shouldRerender,
  optimizeRenderItems,
  type RenderPartition,
} from '../utils/renderingPipeline'
import type { RenderItem, UserTextItem, AssistantTextItem } from '../types'

function makeItem(
  kind: string,
  id: string,
  content: string,
  committed = true,
  streaming = false,
): RenderItem {
  if (kind === 'user-text') {
    return {
      kind: 'user-text',
      id,
      sourceMessageId: `msg-${id}`,
      committed,
      timestamp: Date.now(),
      content,
    } as UserTextItem
  }
  return {
    kind: 'assistant-text',
    id,
    sourceMessageId: `msg-${id}`,
    committed,
    timestamp: Date.now(),
    content,
    streaming,
  } as AssistantTextItem
}

describe('partitionForRendering', () => {
  it('splits static and live items', () => {
    const items: RenderItem[] = [
      makeItem('user-text', '1', 'Hello', true),
      makeItem('assistant-text', '2', 'Streaming...', false, true),
    ]
    const result = partitionForRendering(items)
    expect(result.static).toHaveLength(1)
    expect(result.live).toHaveLength(1)
    expect(result.static[0]!.committed).toBe(true)
    expect((result.live[0] as any).streaming).toBe(true)
  })

  it('places streaming items in live zone', () => {
    const items: RenderItem[] = [
      makeItem('assistant-text', '1', 'Done', true, false),
      makeItem('assistant-text', '2', 'Streaming', true, true),
    ]
    const result = partitionForRendering(items)
    expect(result.live).toHaveLength(1)
    expect((result.live[0] as any).streaming).toBe(true)
  })

  it('filters items before resume boundary', () => {
    const oldItem = makeItem('user-text', '1', 'Old', true)
    const newItem = makeItem('user-text', '2', 'New', true)
    // Set old item timestamp to 0
    ;(oldItem as any).timestamp = 1000
    ;(newItem as any).timestamp = 5000

    const result = partitionForRendering([oldItem, newItem], {
      resumeBoundary: 3000,
    })
    expect(result.static).toHaveLength(1)
    expect((result.static[0] as any).content).toBe('New')
  })

  it('puts active streaming message in live zone', () => {
    const items: RenderItem[] = [
      makeItem('assistant-text', 'msg-1', 'Done', true),
      makeItem('assistant-text', 'msg-2', 'Active', true),
    ]
    const result = partitionForRendering(items, {
      streamingMessageId: 'msg-2',
    })
    expect(result.live).toHaveLength(1)
    expect((result.live[0] as any).content).toBe('Active')
  })

  it('handles empty input', () => {
    const result = partitionForRendering([])
    expect(result.static).toHaveLength(0)
    expect(result.live).toHaveLength(0)
  })

  it('includes resumeBoundary in result', () => {
    const result = partitionForRendering([], { resumeBoundary: 5000 })
    expect(result.resumeBoundary).toBe(5000)
  })
})

describe('shouldRerender', () => {
  function makePartition(staticLen: number, liveLen: number, boundary?: number): RenderPartition {
    return {
      static: Array.from({ length: staticLen }, (_, i) =>
        makeItem('user-text', `s${i}`, `static-${i}`),
      ),
      live: Array.from({ length: liveLen }, (_, i) =>
        makeItem('assistant-text', `l${i}`, `live-${i}`, false),
      ),
      resumeBoundary: boundary,
    }
  }

  it('detects static change', () => {
    const prev = makePartition(3, 1)
    const next = makePartition(4, 1)
    const result = shouldRerender(prev, next)
    expect(result.staticChanged).toBe(true)
    expect(result.liveChanged).toBe(false)
  })

  it('detects live change', () => {
    const prev = makePartition(3, 1)
    const next = makePartition(3, 2)
    const result = shouldRerender(prev, next)
    expect(result.staticChanged).toBe(false)
    expect(result.liveChanged).toBe(true)
  })

  it('detects content change in live items', () => {
    const prev = makePartition(3, 1)
    const next: RenderPartition = {
      static: prev.static,
      live: [makeItem('assistant-text', 'l0', 'updated content', false)],
    }
    const result = shouldRerender(prev, next)
    expect(result.liveChanged).toBe(true)
  })

  it('detects full rerender on boundary change', () => {
    const prev = makePartition(3, 1, 1000)
    const next = makePartition(3, 1, 2000)
    const result = shouldRerender(prev, next)
    expect(result.needsFullRerender).toBe(true)
  })

  it('returns false for unchanged partitions', () => {
    const prev = makePartition(3, 1)
    const next = makePartition(3, 1)
    const result = shouldRerender(prev, next)
    expect(result.staticChanged).toBe(false)
    expect(result.liveChanged).toBe(false)
    expect(result.needsFullRerender).toBe(false)
  })

  it('detects change when prev has no boundary but next does', () => {
    const prev = makePartition(1, 0)
    const next = makePartition(1, 0, 5000)
    const result = shouldRerender(prev, next)
    expect(result.needsFullRerender).toBe(true)
  })
})

describe('optimizeRenderItems', () => {
  it('removes duplicate consecutive items', () => {
    const item1 = makeItem('user-text', '1', 'Hello')
    const item2 = makeItem('user-text', '1', 'Hello')
    const item3 = makeItem('user-text', '2', 'World')
    const result = optimizeRenderItems([item1, item2, item3])
    expect(result).toHaveLength(2)
  })

  it('keeps non-duplicate items', () => {
    const items = [
      makeItem('user-text', '1', 'A'),
      makeItem('user-text', '2', 'B'),
      makeItem('user-text', '3', 'C'),
    ]
    const result = optimizeRenderItems(items)
    expect(result).toHaveLength(3)
  })

  it('handles empty array', () => {
    const result = optimizeRenderItems([])
    expect(result).toHaveLength(0)
  })

  it('removes items with same id and content regardless of role', () => {
    const items = [
      makeItem('user-text', '1', 'Same content'),
      { ...makeItem('assistant-text', '1', 'Same content'), role: 'assistant' },
    ] as RenderItem[]
    // Same id + same content = duplicate, even with different roles
    const result = optimizeRenderItems(items)
    expect(result.length).toBe(1)
  })
})
