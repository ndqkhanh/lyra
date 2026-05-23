import React from 'react'
import type { RenderItem } from '@lyra/ui-core'
import { UserTextMessage } from './items/UserTextMessage'
import { AssistantTextMessage } from './items/AssistantTextMessage'
import { ThinkingBlock } from './items/ThinkingBlock'
import { ToolExecution } from './items/ToolExecution'

interface RenderItemViewProps {
  item: RenderItem
}

export function RenderItemView({ item }: RenderItemViewProps) {
  switch (item.kind) {
    case 'user-text':
      return <UserTextMessage item={item} />
    case 'assistant-text':
      return <AssistantTextMessage item={item} />
    case 'thinking':
      return <ThinkingBlock item={item} />
    case 'tool-execution':
      return <ToolExecution item={item} />
    default:
      return null
  }
}
