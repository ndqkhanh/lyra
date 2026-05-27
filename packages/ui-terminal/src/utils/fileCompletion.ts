import { readdirSync } from 'fs'
import { join, relative } from 'path'

export interface FileSuggestion {
  path: string
  isDirectory: boolean
  displayName: string
}

/**
 * Get file and folder suggestions for @ mentions
 * Supports fuzzy matching and relative paths
 */
export function getFileSuggestions(
  query: string,
  baseDir: string = process.cwd(),
  maxResults: number = 10
): FileSuggestion[] {
  try {
    // Handle relative paths (../, ./, etc)
    let searchDir = baseDir
    let searchQuery = query

    if (query.includes('/')) {
      const lastSlash = query.lastIndexOf('/')
      const dirPath = query.slice(0, lastSlash + 1)
      searchQuery = query.slice(lastSlash + 1)

      // Resolve relative path
      if (dirPath.startsWith('./') || dirPath.startsWith('../')) {
        searchDir = join(baseDir, dirPath)
      } else {
        searchDir = join(baseDir, dirPath)
      }
    }

    // Read directory contents
    const entries = readdirSync(searchDir, { withFileTypes: true })

    // Filter and map to suggestions
    const suggestions: FileSuggestion[] = entries
      .filter(entry => {
        // Skip hidden files unless query starts with .
        if (entry.name.startsWith('.') && !searchQuery.startsWith('.')) {
          return false
        }

        // Fuzzy match
        return fuzzyMatch(entry.name.toLowerCase(), searchQuery.toLowerCase())
      })
      .map(entry => {
        const fullPath = join(searchDir, entry.name)
        const isDirectory = entry.isDirectory()

        return {
          path: relative(baseDir, fullPath),
          isDirectory,
          displayName: entry.name + (isDirectory ? '/' : '')
        }
      })
      .slice(0, maxResults)

    return suggestions
  } catch (error) {
    // Directory doesn't exist or permission denied
    return []
  }
}

/**
 * Simple fuzzy matching algorithm
 * Returns true if all characters in query appear in target in order
 */
function fuzzyMatch(target: string, query: string): boolean {
  if (query.length === 0) return true
  if (target.length === 0) return false

  let queryIndex = 0
  let targetIndex = 0

  while (targetIndex < target.length && queryIndex < query.length) {
    if (target[targetIndex] === query[queryIndex]) {
      queryIndex++
    }
    targetIndex++
  }

  return queryIndex === query.length
}

/**
 * Extract @ mentions from input text
 * Returns array of { start, end, path } for each mention
 */
export function extractMentions(text: string): Array<{ start: number; end: number; path: string }> {
  const mentions: Array<{ start: number; end: number; path: string }> = []
  const regex = /@([^\s]+)/g
  let match

  while ((match = regex.exec(text)) !== null) {
    mentions.push({
      start: match.index,
      end: match.index + match[0].length,
      path: match[1]
    })
  }

  return mentions
}

/**
 * Get the current @ mention being typed
 * Returns null if cursor is not in a mention
 */
export function getCurrentMention(text: string, cursorPosition: number): string | null {
  // Find the last @ before cursor
  const beforeCursor = text.slice(0, cursorPosition)
  const lastAtIndex = beforeCursor.lastIndexOf('@')

  if (lastAtIndex === -1) return null

  // Check if there's a space between @ and cursor
  const afterAt = beforeCursor.slice(lastAtIndex + 1)
  if (afterAt.includes(' ')) return null

  return afterAt
}
