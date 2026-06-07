/**
 * Logger utility for ui-core
 * Provides consistent logging across the application
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

export interface Logger {
  debug(component: string, ...args: unknown[]): void
  info(component: string, ...args: unknown[]): void
  warn(component: string, ...args: unknown[]): void
  error(component: string, ...args: unknown[]): void
}

class LoggerImpl implements Logger {
  private enabled = true
  private minLevel: LogLevel = 'info'

  setEnabled(enabled: boolean): void {
    this.enabled = enabled
  }

  setMinLevel(level: LogLevel): void {
    this.minLevel = level
  }

  private shouldLog(level: LogLevel): boolean {
    if (!this.enabled) return false

    const levels: LogLevel[] = ['debug', 'info', 'warn', 'error']
    const currentIndex = levels.indexOf(this.minLevel)
    const messageIndex = levels.indexOf(level)

    return messageIndex >= currentIndex
  }

  debug(_component: string, ..._args: unknown[]): void {
    if (this.shouldLog('debug')) {
      // In production, this would go to a logging service
      // For now, we suppress console output
    }
  }

  info(_component: string, ..._args: unknown[]): void {
    if (this.shouldLog('info')) {
      // In production, this would go to a logging service
    }
  }

  warn(_component: string, ..._args: unknown[]): void {
    if (this.shouldLog('warn')) {
      // In production, this would go to a logging service
    }
  }

  error(component: string, ...args: unknown[]): void {
    if (this.shouldLog('error')) {
      // In production, this would go to a logging service
      // For critical errors, we might still want to log to stderr
      if (process.env.NODE_ENV === 'development') {
        console.error(`[${component}]`, ...args)
      }
    }
  }
}

export const logger: Logger = new LoggerImpl()
