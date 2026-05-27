import React from 'react'
import { Box, Text } from 'ink'
import { useThemeColors } from '@lyra/ui-core'
import { logger } from '../utils/logger'

interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ReactNode
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

/**
 * ErrorBoundary - Catches React component errors and displays fallback UI
 *
 * Prevents component errors from crashing the entire TUI. Logs errors
 * and displays user-friendly error messages.
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary>
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: undefined }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    logger.error('ErrorBoundary', 'Component error:', error.message, errorInfo.componentStack)
    this.props.onError?.(error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return <DefaultErrorFallback error={this.state.error} />
    }

    return this.props.children
  }
}

/**
 * Default error fallback UI
 */
function DefaultErrorFallback({ error }: { error?: Error }) {
  const colors = useThemeColors()

  return (
    <Box flexDirection="column" padding={1} borderStyle="round" borderColor={colors.error}>
      <Text bold color={colors.error}>
        ⚠ Component Error
      </Text>
      <Box marginTop={1}>
        <Text color={colors.errorHigh}>
          {error?.message || 'An unexpected error occurred'}
        </Text>
      </Box>
      <Box marginTop={1}>
        <Text color={colors.dim}>
          The application is still running. Press Ctrl+D to exit.
        </Text>
      </Box>
    </Box>
  )
}

/**
 * Lightweight error boundary for individual render items
 */
export function ItemErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary
      fallback={
        <Box>
          <Text color="red">⚠ Error rendering item</Text>
        </Box>
      }
    >
      {children}
    </ErrorBoundary>
  )
}
