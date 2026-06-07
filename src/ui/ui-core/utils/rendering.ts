import type {
  Message,
  RenderItem,
  UserTextItem,
  AssistantTextItem,
  ThinkingItem,
  ToolExecutionItem,
  AssistantMessage,
  DisplayMode
} from '../types'

// Identity cache for O(1) resume performance
const identityCache = new WeakMap<Message, RenderItem[]>()

export function toRenderItems(
  messages: Message[],
  previewMessages: Message[]
): RenderItem[] {
  const items: RenderItem[] = []

  // Process committed messages with caching
  for (const msg of messages) {
    const cached = identityCache.get(msg)
    if (cached) {
      items.push(...cached)
      continue
    }

    const msgItems = messageToRenderItems(msg, true)
    identityCache.set(msg, msgItems)
    items.push(...msgItems)
  }

  // Process preview messages (no caching - mutable)
  for (const msg of previewMessages) {
    items.push(...messageToRenderItems(msg, false))
  }

  return items
}

function messageToRenderItems(msg: Message, committed: boolean): RenderItem[] {
  const items: RenderItem[] = []

  if (msg.role === 'user') {
    items.push({
      kind: 'user-text',
      id: `${msg.id}-text`,
      sourceMessageId: msg.id,
      committed,
      timestamp: msg.timestamp,
      content: msg.content
    } as UserTextItem)
  } else if (msg.role === 'system') {
    // System messages — route to error or system-notice based on content
    const isError = msg.content.toLowerCase().startsWith('error')
    items.push({
      kind: isError ? 'error' : 'system-notice',
      id: `${msg.id}-${isError ? 'error' : 'notice'}`,
      sourceMessageId: msg.id,
      committed,
      timestamp: msg.timestamp,
      message: isError ? msg.content : undefined,
      content: isError ? undefined : msg.content,
      noticeType: isError ? undefined : 'info'
    } as RenderItem)
  } else if (msg.role === 'assistant') {
    const assistantMsg = msg as AssistantMessage

    // Thinking block
    if (assistantMsg.thinking) {
      items.push({
        kind: 'thinking',
        id: `${msg.id}-thinking`,
        sourceMessageId: msg.id,
        committed,
        timestamp: msg.timestamp,
        content: assistantMsg.thinking.content,
        durationSec: assistantMsg.thinking.durationMs
          ? assistantMsg.thinking.durationMs / 1000
          : undefined,
        collapsed: assistantMsg.thinking.collapsed
      } as ThinkingItem)
    }

    // Tool calls
    if (assistantMsg.toolCalls) {
      for (const tool of assistantMsg.toolCalls) {
        items.push({
          kind: 'tool-execution',
          id: `${msg.id}-tool-${tool.id}`,
          sourceMessageId: msg.id,
          committed,
          timestamp: tool.startTime,
          toolName: tool.name,
          args: tool.args,
          result: tool.result,
          status: tool.status
        } as ToolExecutionItem)
      }
    }

    // Assistant text
    if (msg.content) {
      items.push({
        kind: 'assistant-text',
        id: `${msg.id}-text`,
        sourceMessageId: msg.id,
        committed,
        timestamp: msg.timestamp,
        content: msg.content,
        streaming: assistantMsg.streaming ?? false
      } as AssistantTextItem)
    }
  }

  return items
}

export function applyDisplayPolicy(
  items: RenderItem[],
  mode: DisplayMode
): RenderItem[] {
  if (mode === 'debug') return items

  const filtered: RenderItem[] = []

  for (const item of items) {
    if (item.kind === 'thinking') {
      if (mode === 'minimal') continue
      // Standard: collapse to duration badge only
      if (item.durationSec == null) continue
      filtered.push({ ...item, content: '', collapsed: true })
    } else if (item.kind === 'tool-execution') {
      if (mode === 'minimal') {
        // Show only tool name and status
        filtered.push({ ...item, args: {}, result: undefined })
      } else {
        filtered.push(item)
      }
    } else {
      filtered.push(item)
    }
  }

  return filtered
}

export function partitionRenderItems(items: RenderItem[]) {
  const staticItems = items.filter(item => item.committed)
  const liveItems = items.filter(item => !item.committed)
  return { staticItems, liveItems }
}
