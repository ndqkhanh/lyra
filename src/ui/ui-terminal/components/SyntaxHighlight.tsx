import React from 'react'
import { Box, Text } from 'ink'
import { useThemeColors } from '@lyra/ui-core'

interface SyntaxHighlightProps {
  code: string
  language?: string
  showLineNumbers?: boolean
  startLine?: number
}

// Simple syntax highlighting for common languages
const tokenize = (code: string, language: string): Array<{ text: string; type: string }> => {
  const tokens: Array<{ text: string; type: string }> = []

  // Keywords by language
  const keywords: Record<string, string[]> = {
    typescript: ['const', 'let', 'var', 'function', 'class', 'interface', 'type', 'import', 'export', 'from', 'return', 'if', 'else', 'for', 'while', 'async', 'await', 'try', 'catch', 'throw', 'new'],
    javascript: ['const', 'let', 'var', 'function', 'class', 'import', 'export', 'from', 'return', 'if', 'else', 'for', 'while', 'async', 'await', 'try', 'catch', 'throw', 'new'],
    python: ['def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif', 'for', 'while', 'async', 'await', 'with', 'as', 'try', 'except', 'finally', 'raise'],
    rust: ['fn', 'let', 'mut', 'struct', 'enum', 'impl', 'trait', 'use', 'pub', 'return', 'if', 'else', 'for', 'while', 'match', 'Some', 'None', 'Ok', 'Err'],
    go: ['func', 'var', 'const', 'type', 'struct', 'interface', 'import', 'return', 'if', 'else', 'for', 'range', 'go', 'defer', 'select', 'case'],
    bash: ['cd', 'ls', 'git', 'npm', 'yarn', 'pnpm', 'cat', 'grep', 'find', 'echo', 'export', 'source', 'chmod', 'mkdir', 'rm', 'cp', 'mv', 'sudo', 'docker', 'kubectl', 'if', 'then', 'else', 'fi', 'for', 'do', 'done']
  }

  const langKeywords = keywords[language] || []

  // Simple tokenization
  const regex = /(".*?"|'.*?'|`.*?`|\/\/.*|\/\*[\s\S]*?\*\/|\b\d+\b|\b[a-zA-Z_]\w*\b|[{}()\[\];,.])/g
  let lastIndex = 0

  code.replace(regex, (match, offset) => {
    // Add whitespace before match
    if (offset > lastIndex) {
      tokens.push({ text: code.slice(lastIndex, offset), type: 'whitespace' })
    }

    // Classify token
    let type = 'text'
    if (match.startsWith('"') || match.startsWith("'") || match.startsWith('`')) {
      type = 'string'
    } else if (match.startsWith('//') || match.startsWith('/*')) {
      type = 'comment'
    } else if (/^\d+$/.test(match)) {
      type = 'number'
    } else if (langKeywords.includes(match)) {
      type = 'keyword'
    } else if (/^[{}()\[\];,.]$/.test(match)) {
      type = 'punctuation'
    }

    tokens.push({ text: match, type })
    lastIndex = offset + match.length
    return match
  })

  // Add remaining text
  if (lastIndex < code.length) {
    tokens.push({ text: code.slice(lastIndex), type: 'whitespace' })
  }

  return tokens
}

export function SyntaxHighlight({
  code,
  language = 'typescript',
  showLineNumbers = true,
  startLine = 1
}: SyntaxHighlightProps) {
  const colors = useThemeColors()
  const getTokenColor = (type: string): string => {
    switch (type) {
      case 'keyword':
        return colors.codeKeyword
      case 'string':
        return colors.codeString
      case 'number':
        return colors.codeNumber
      case 'comment':
        return colors.codeComment
      case 'punctuation':
        return colors.codeOperator
      default:
        return colors.codeVariable
    }
  }

  const lines = code.split('\n')

  return (
    <Box flexDirection="column">
      {lines.map((line, idx) => {
        const lineNumber = startLine + idx
        const tokens = tokenize(line, language)

        return (
          <Box key={idx}>
            {showLineNumbers && (
              <Box width={4} marginRight={1}>
                <Text color={colors.lineNumber} dimColor>
                  {lineNumber.toString().padStart(3, ' ')}
                </Text>
              </Box>
            )}
            <Box>
              {tokens.map((token, tokenIdx) => (
                <Text key={tokenIdx} color={getTokenColor(token.type)}>
                  {token.text}
                </Text>
              ))}
            </Box>
          </Box>
        )
      })}
    </Box>
  )
}

interface CodeBlockProps {
  code: string
  language?: string
  title?: string
  showLineNumbers?: boolean
}

export function CodeBlock({ code, language = 'typescript', title, showLineNumbers = true }: CodeBlockProps) {
  const colors = useThemeColors()
  return (
    <Box flexDirection="column" borderStyle="single" borderColor={colors.border} paddingX={1}>
      {title && (
        <Box borderBottom borderColor={colors.border} paddingBottom={0} marginBottom={1}>
          <Text bold color={colors.filePath}>{title}</Text>
          {language && (
            <Text color={colors.timestamp} dimColor>
              {' '}
              ({language})
            </Text>
          )}
        </Box>
      )}
      <SyntaxHighlight code={code} language={language} showLineNumbers={showLineNumbers} />
    </Box>
  )
}
