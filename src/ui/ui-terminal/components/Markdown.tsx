import React from 'react'
import { Box, Text } from 'ink'
import { useThemeColors, symbols } from '@lyra/ui-core'
import { SyntaxHighlight } from './SyntaxHighlight'

interface MarkdownProps {
  content: string
  maxWidth?: number
}

interface ParsedNode {
  type: 'text' | 'heading' | 'code' | 'list' | 'quote' | 'bold' | 'italic' | 'link'
  content: string
  level?: number
  language?: string
  children?: ParsedNode[]
}

// Simple markdown parser
const parseMarkdown = (content: string): ParsedNode[] => {
  const nodes: ParsedNode[] = []
  const lines = content.split('\n')

  let i = 0
  while (i < lines.length) {
    const line = lines[i]

    // Code block
    if (line.startsWith('```')) {
      const language = line.slice(3).trim() || 'text'
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      nodes.push({ type: 'code', content: codeLines.join('\n'), language })
      i++
      continue
    }

    // Heading
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/)
    if (headingMatch) {
      nodes.push({
        type: 'heading',
        level: headingMatch[1].length,
        content: headingMatch[2]
      })
      i++
      continue
    }

    // List item
    if (line.match(/^[\s]*[-*+]\s+/)) {
      nodes.push({
        type: 'list',
        content: line.replace(/^[\s]*[-*+]\s+/, '')
      })
      i++
      continue
    }

    // Quote
    if (line.startsWith('>')) {
      nodes.push({
        type: 'quote',
        content: line.slice(1).trim()
      })
      i++
      continue
    }

    // Regular text with inline formatting
    if (line.trim()) {
      nodes.push({ type: 'text', content: line })
    }

    i++
  }

  return nodes
}

// Parse inline formatting (bold, italic, code, links)
const parseInline = (text: string): Array<{ text: string; format: string }> => {
  const parts: Array<{ text: string; format: string }> = []
  let current = ''
  let i = 0

  while (i < text.length) {
    // Bold **text**
    if (text.slice(i, i + 2) === '**') {
      if (current) parts.push({ text: current, format: 'normal' })
      current = ''
      i += 2
      while (i < text.length && text.slice(i, i + 2) !== '**') {
        current += text[i]
        i++
      }
      if (current) parts.push({ text: current, format: 'bold' })
      current = ''
      i += 2
      continue
    }

    // Italic *text*
    if (text[i] === '*' && text[i + 1] !== '*') {
      if (current) parts.push({ text: current, format: 'normal' })
      current = ''
      i++
      while (i < text.length && text[i] !== '*') {
        current += text[i]
        i++
      }
      if (current) parts.push({ text: current, format: 'italic' })
      current = ''
      i++
      continue
    }

    // Inline code `text`
    if (text[i] === '`') {
      if (current) parts.push({ text: current, format: 'normal' })
      current = ''
      i++
      while (i < text.length && text[i] !== '`') {
        current += text[i]
        i++
      }
      if (current) parts.push({ text: current, format: 'code' })
      current = ''
      i++
      continue
    }

    // Link [text](url)
    if (text[i] === '[') {
      if (current) parts.push({ text: current, format: 'normal' })
      current = ''
      i++
      while (i < text.length && text[i] !== ']') {
        current += text[i]
        i++
      }
      const linkText = current
      current = ''
      i++ // skip ]
      if (text[i] === '(') {
        i++ // skip (
        while (i < text.length && text[i] !== ')') {
          i++
        }
        i++ // skip )
        parts.push({ text: linkText, format: 'link' })
      }
      continue
    }

    current += text[i]
    i++
  }

  if (current) parts.push({ text: current, format: 'normal' })
  return parts
}

export function Markdown({ content }: MarkdownProps) {
  const colors = useThemeColors()
  const nodes = parseMarkdown(content)

  return (
    <Box flexDirection="column">
      {nodes.map((node, idx) => {
        switch (node.type) {
          case 'heading': {
            const headingColor = colors.markdownHeading
            return (
              <Box key={idx} marginY={node.level === 1 ? 1 : 0}>
                <Text bold color={headingColor}>
                  {node.content}
                </Text>
              </Box>
            )
          }

          case 'code':
            return (
              <Box key={idx} marginY={1}>
                <SyntaxHighlight code={node.content} language={node.language} showLineNumbers={false} />
              </Box>
            )

          case 'list':
            return (
              <Box key={idx}>
                <Text color={colors.markdownList}>{symbols.branch} </Text>
                <Box>
                  {parseInline(node.content).map((part, partIdx) => (
                    <Text
                      key={partIdx}
                      bold={part.format === 'bold'}
                      italic={part.format === 'italic'}
                      color={
                        part.format === 'code'
                          ? colors.markdownCode
                          : part.format === 'link'
                          ? colors.markdownLink
                          : part.format === 'bold'
                          ? colors.markdownBold
                          : part.format === 'italic'
                          ? colors.markdownItalic
                          : colors.assistant
                      }
                    >
                      {part.text}
                    </Text>
                  ))}
                </Box>
              </Box>
            )

          case 'quote':
            return (
              <Box key={idx} borderLeft borderColor={colors.collapsibleBorder} paddingLeft={2}>
                <Text color={colors.markdownQuote} italic>
                  {node.content}
                </Text>
              </Box>
            )

          case 'text':
            return (
              <Box key={idx}>
                {parseInline(node.content).map((part, partIdx) => (
                  <Text
                    key={partIdx}
                    bold={part.format === 'bold'}
                    italic={part.format === 'italic'}
                    color={
                      part.format === 'code'
                        ? colors.markdownCode
                        : part.format === 'link'
                        ? colors.markdownLink
                        : part.format === 'bold'
                        ? colors.markdownBold
                        : part.format === 'italic'
                        ? colors.markdownItalic
                        : colors.assistant
                    }
                  >
                    {part.text}
                  </Text>
                ))}
              </Box>
            )

          default:
            return null
        }
      })}
    </Box>
  )
}
