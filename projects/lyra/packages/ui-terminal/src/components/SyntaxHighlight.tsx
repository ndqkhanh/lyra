import React from 'react'
import { Text } from 'ink'
import chalk from 'chalk'

interface SyntaxHighlightProps {
  code: string
  language?: string
}

// Simple syntax highlighting for common languages
export function SyntaxHighlight({ code, language }: SyntaxHighlightProps) {
  if (!language) {
    return <Text>{code}</Text>
  }

  const lines = code.split('\n')

  return (
    <>
      {lines.map((line, idx) => (
        <Text key={idx}>{highlightLine(line, language)}</Text>
      ))}
    </>
  )
}

function highlightLine(line: string, language: string): string {
  switch (language) {
    case 'javascript':
    case 'typescript':
    case 'tsx':
      return highlightJavaScript(line)
    case 'python':
      return highlightPython(line)
    default:
      return line
  }
}

function highlightJavaScript(line: string): string {
  // Keywords
  const keywords = /\b(const|let|var|function|return|if|else|for|while|class|import|export|from|async|await|try|catch|throw|new|this|super|extends|implements|interface|type|enum)\b/g
  line = line.replace(keywords, chalk.magenta('$1'))

  // Strings
  const strings = /(["'`])((?:\\.|(?!\1).)*?)\1/g
  line = line.replace(strings, chalk.green('$1$2$1'))

  // Comments
  const comments = /(\/\/.*$|\/\*[\s\S]*?\*\/)/g
  line = line.replace(comments, chalk.gray('$1'))

  // Functions
  const functions = /\b([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(/g
  line = line.replace(functions, chalk.cyan('$1') + '(')

  // Numbers
  const numbers = /\b(\d+\.?\d*)\b/g
  line = line.replace(numbers, chalk.yellow('$1'))

  return line
}

function highlightPython(line: string): string {
  // Keywords
  const keywords = /\b(def|class|return|if|elif|else|for|while|import|from|as|try|except|finally|raise|with|lambda|yield|async|await|pass|break|continue|global|nonlocal)\b/g
  line = line.replace(keywords, chalk.magenta('$1'))

  // Strings
  const strings = /(["'])((?:\\.|(?!\1).)*?)\1/g
  line = line.replace(strings, chalk.green('$1$2$1'))

  // Comments
  const comments = /(#.*$)/g
  line = line.replace(comments, chalk.gray('$1'))

  // Functions
  const functions = /\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)/g
  line = line.replace(functions, 'def ' + chalk.cyan('$1'))

  // Built-ins
  const builtins = /\b(print|len|range|str|int|float|list|dict|set|tuple|open|input|type|isinstance|hasattr|getattr|setattr)\b/g
  line = line.replace(builtins, chalk.yellow('$1'))

  return line
}
