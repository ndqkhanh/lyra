/**
 * Production Monitoring System
 *
 * Enterprise-grade monitoring, error handling, and observability.
 *
 * Features:
 * - Error tracking and reporting
 * - Performance monitoring
 * - Health checks
 * - Metrics collection
 * - Alerting system
 * - Circuit breaker pattern
 * - Retry logic with exponential backoff
 */

import { EventEmitter } from 'eventemitter3'

/**
 * Error severity
 */
export type ErrorSeverity = 'critical' | 'error' | 'warning' | 'info'

/**
 * Health status
 */
export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy'

/**
 * Metric type
 */
export type MetricType = 'counter' | 'gauge' | 'histogram' | 'summary'

/**
 * Error entry
 */
export interface ErrorEntry {
  id: string
  timestamp: number
  severity: ErrorSeverity
  message: string
  error: Error
  context?: Record<string, unknown>
  stackTrace?: string
}

/**
 * Metric entry
 */
export interface MetricEntry {
  name: string
  type: MetricType
  value: number
  timestamp: number
  labels?: Record<string, string>
}

/**
 * Health check result
 */
export interface HealthCheckResult {
  name: string
  status: HealthStatus
  message?: string
  timestamp: number
  duration: number
  metadata?: Record<string, unknown>
}

/**
 * Circuit breaker state
 */
export type CircuitState = 'closed' | 'open' | 'half-open'

/**
 * Circuit breaker configuration
 */
export interface CircuitBreakerConfig {
  /** Failure threshold before opening */
  failureThreshold: number
  /** Success threshold before closing */
  successThreshold: number
  /** Timeout in ms before trying half-open */
  timeout: number
  /** Rolling window size */
  windowSize: number
}

/**
 * Retry configuration
 */
export interface RetryConfig {
  /** Maximum retry attempts */
  maxAttempts: number
  /** Initial delay in ms */
  initialDelay: number
  /** Maximum delay in ms */
  maxDelay: number
  /** Backoff multiplier */
  backoffMultiplier: number
  /** Enable jitter */
  jitter: boolean
}

/**
 * Monitor configuration
 */
export interface MonitorConfig {
  /** Enable error tracking */
  errorTracking: boolean
  /** Enable performance monitoring */
  performanceMonitoring: boolean
  /** Enable health checks */
  healthChecks: boolean
  /** Enable metrics collection */
  metricsCollection: boolean
  /** Health check interval in ms */
  healthCheckInterval: number
  /** Metrics flush interval in ms */
  metricsFlushInterval: number
  /** Error retention in ms */
  errorRetention: number
  /** Metric retention in ms */
  metricRetention: number
}

/**
 * Circuit Breaker
 */
export class CircuitBreaker {
  private state: CircuitState = 'closed'
  private failures: number[] = []
  private successes: number[] = []
  private lastFailureTime: number = 0
  private config: CircuitBreakerConfig

  constructor(config: Partial<CircuitBreakerConfig> = {}) {
    this.config = {
      failureThreshold: config.failureThreshold ?? 5,
      successThreshold: config.successThreshold ?? 2,
      timeout: config.timeout ?? 60000,
      windowSize: config.windowSize ?? 10
    }
  }

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'open') {
      if (Date.now() - this.lastFailureTime >= this.config.timeout) {
        this.state = 'half-open'
      } else {
        throw new Error('Circuit breaker is open')
      }
    }

    try {
      const result = await fn()
      this.onSuccess()
      return result
    } catch (error) {
      this.onFailure()
      throw error
    }
  }

  private onSuccess(): void {
    this.successes.push(Date.now())
    this.trimWindow(this.successes)

    if (this.state === 'half-open') {
      if (this.successes.length >= this.config.successThreshold) {
        this.state = 'closed'
        this.failures = []
        this.successes = []
      }
    }
  }

  private onFailure(): void {
    this.failures.push(Date.now())
    this.lastFailureTime = Date.now()
    this.trimWindow(this.failures)

    if (this.failures.length >= this.config.failureThreshold) {
      this.state = 'open'
    }
  }

  private trimWindow(arr: number[]): void {
    const cutoff = Date.now() - 60000 // 1 minute window
    while (arr.length > 0 && arr[0]! < cutoff) {
      arr.shift()
    }
    if (arr.length > this.config.windowSize) {
      arr.splice(0, arr.length - this.config.windowSize)
    }
  }

  getState(): CircuitState {
    return this.state
  }

  reset(): void {
    this.state = 'closed'
    this.failures = []
    this.successes = []
  }
}

/**
 * Retry handler
 */
export class RetryHandler {
  private config: RetryConfig

  constructor(config: Partial<RetryConfig> = {}) {
    this.config = {
      maxAttempts: config.maxAttempts ?? 3,
      initialDelay: config.initialDelay ?? 1000,
      maxDelay: config.maxDelay ?? 30000,
      backoffMultiplier: config.backoffMultiplier ?? 2,
      jitter: config.jitter ?? true
    }
  }

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    let lastError: Error | undefined

    for (let attempt = 0; attempt < this.config.maxAttempts; attempt++) {
      try {
        return await fn()
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error))

        if (attempt < this.config.maxAttempts - 1) {
          const delay = this.calculateDelay(attempt)
          await this.sleep(delay)
        }
      }
    }

    throw lastError
  }

  private calculateDelay(attempt: number): number {
    let delay = this.config.initialDelay * Math.pow(this.config.backoffMultiplier, attempt)
    delay = Math.min(delay, this.config.maxDelay)

    if (this.config.jitter) {
      delay = delay * (0.5 + Math.random() * 0.5)
    }

    return delay
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}

/**
 * Production Monitor
 */
export class ProductionMonitor extends EventEmitter {
  private config: MonitorConfig
  private errors: ErrorEntry[] = []
  private metrics: MetricEntry[] = []
  private healthChecks = new Map<string, () => Promise<HealthCheckResult>>()
  private healthCheckTimer: NodeJS.Timeout | null = null
  private metricsFlushTimer: NodeJS.Timeout | null = null
  private circuitBreakers = new Map<string, CircuitBreaker>()
  private retryHandlers = new Map<string, RetryHandler>()

  constructor(config: Partial<MonitorConfig> = {}) {
    super()
    this.config = {
      errorTracking: config.errorTracking ?? true,
      performanceMonitoring: config.performanceMonitoring ?? true,
      healthChecks: config.healthChecks ?? true,
      metricsCollection: config.metricsCollection ?? true,
      healthCheckInterval: config.healthCheckInterval ?? 30000,
      metricsFlushInterval: config.metricsFlushInterval ?? 60000,
      errorRetention: config.errorRetention ?? 86400000, // 24 hours
      metricRetention: config.metricRetention ?? 3600000 // 1 hour
    }

    if (this.config.healthChecks) {
      this.startHealthChecks()
    }

    if (this.config.metricsCollection) {
      this.startMetricsFlush()
    }
  }

  /**
   * Track an error
   */
  trackError(error: Error, severity: ErrorSeverity = 'error', context?: Record<string, unknown>): void {
    if (!this.config.errorTracking) return

    const entry: ErrorEntry = {
      id: `error-${Date.now()}-${Math.random()}`,
      timestamp: Date.now(),
      severity,
      message: error.message,
      error,
      context,
      stackTrace: error.stack
    }

    this.errors.push(entry)
    this.trimErrors()

    this.emit('error', entry)

    // Log to console based on severity
    if (severity === 'critical' || severity === 'error') {
      console.error(`[${severity.toUpperCase()}]`, error.message, context)
    } else if (severity === 'warning') {
      console.warn(`[WARNING]`, error.message, context)
    }
  }

  /**
   * Record a metric
   */
  recordMetric(name: string, value: number, type: MetricType = 'gauge', labels?: Record<string, string>): void {
    if (!this.config.metricsCollection) return

    const entry: MetricEntry = {
      name,
      type,
      value,
      timestamp: Date.now(),
      labels
    }

    this.metrics.push(entry)
    this.trimMetrics()

    this.emit('metric', entry)
  }

  /**
   * Increment a counter
   */
  incrementCounter(name: string, value: number = 1, labels?: Record<string, string>): void {
    this.recordMetric(name, value, 'counter', labels)
  }

  /**
   * Set a gauge
   */
  setGauge(name: string, value: number, labels?: Record<string, string>): void {
    this.recordMetric(name, value, 'gauge', labels)
  }

  /**
   * Record a histogram value
   */
  recordHistogram(name: string, value: number, labels?: Record<string, string>): void {
    this.recordMetric(name, value, 'histogram', labels)
  }

  /**
   * Time an operation
   */
  async timeOperation<T>(name: string, fn: () => Promise<T>): Promise<T> {
    const start = Date.now()
    try {
      const result = await fn()
      const duration = Date.now() - start
      this.recordHistogram(`${name}.duration`, duration)
      this.incrementCounter(`${name}.success`)
      return result
    } catch (error) {
      const duration = Date.now() - start
      this.recordHistogram(`${name}.duration`, duration)
      this.incrementCounter(`${name}.error`)
      throw error
    }
  }

  /**
   * Register a health check
   */
  registerHealthCheck(name: string, check: () => Promise<HealthCheckResult>): void {
    this.healthChecks.set(name, check)
  }

  /**
   * Run all health checks
   */
  async runHealthChecks(): Promise<HealthCheckResult[]> {
    const results: HealthCheckResult[] = []

    for (const [name, check] of this.healthChecks) {
      try {
        const result = await check()
        results.push(result)
      } catch (error) {
        results.push({
          name,
          status: 'unhealthy',
          message: error instanceof Error ? error.message : String(error),
          timestamp: Date.now(),
          duration: 0
        })
      }
    }

    return results
  }

  /**
   * Get overall health status
   */
  async getHealthStatus(): Promise<{ status: HealthStatus; checks: HealthCheckResult[] }> {
    const checks = await this.runHealthChecks()

    let status: HealthStatus = 'healthy'
    if (checks.some(c => c.status === 'unhealthy')) {
      status = 'unhealthy'
    } else if (checks.some(c => c.status === 'degraded')) {
      status = 'degraded'
    }

    return { status, checks }
  }

  /**
   * Get or create circuit breaker
   */
  getCircuitBreaker(name: string, config?: Partial<CircuitBreakerConfig>): CircuitBreaker {
    if (!this.circuitBreakers.has(name)) {
      this.circuitBreakers.set(name, new CircuitBreaker(config))
    }
    return this.circuitBreakers.get(name)!
  }

  /**
   * Get or create retry handler
   */
  getRetryHandler(name: string, config?: Partial<RetryConfig>): RetryHandler {
    if (!this.retryHandlers.has(name)) {
      this.retryHandlers.set(name, new RetryHandler(config))
    }
    return this.retryHandlers.get(name)!
  }

  /**
   * Get errors
   */
  getErrors(severity?: ErrorSeverity): ErrorEntry[] {
    if (severity) {
      return this.errors.filter(e => e.severity === severity)
    }
    return [...this.errors]
  }

  /**
   * Get metrics
   */
  getMetrics(name?: string): MetricEntry[] {
    if (name) {
      return this.metrics.filter(m => m.name === name)
    }
    return [...this.metrics]
  }

  /**
   * Get statistics
   */
  getStats() {
    return {
      errors: {
        total: this.errors.length,
        critical: this.errors.filter(e => e.severity === 'critical').length,
        error: this.errors.filter(e => e.severity === 'error').length,
        warning: this.errors.filter(e => e.severity === 'warning').length,
        info: this.errors.filter(e => e.severity === 'info').length
      },
      metrics: {
        total: this.metrics.length,
        counters: this.metrics.filter(m => m.type === 'counter').length,
        gauges: this.metrics.filter(m => m.type === 'gauge').length,
        histograms: this.metrics.filter(m => m.type === 'histogram').length
      },
      healthChecks: this.healthChecks.size,
      circuitBreakers: this.circuitBreakers.size
    }
  }

  /**
   * Private: Start health checks
   */
  private startHealthChecks(): void {
    if (this.healthCheckTimer) return

    this.healthCheckTimer = setInterval(async () => {
      const results = await this.runHealthChecks()
      this.emit('health-check', results)
    }, this.config.healthCheckInterval)
  }

  /**
   * Private: Start metrics flush
   */
  private startMetricsFlush(): void {
    if (this.metricsFlushTimer) return

    this.metricsFlushTimer = setInterval(() => {
      this.emit('metrics-flush', this.getMetrics())
    }, this.config.metricsFlushInterval)
  }

  /**
   * Private: Trim old errors
   */
  private trimErrors(): void {
    const cutoff = Date.now() - this.config.errorRetention
    this.errors = this.errors.filter(e => e.timestamp > cutoff)
  }

  /**
   * Private: Trim old metrics
   */
  private trimMetrics(): void {
    const cutoff = Date.now() - this.config.metricRetention
    this.metrics = this.metrics.filter(m => m.timestamp > cutoff)
  }

  /**
   * Cleanup
   */
  cleanup(): void {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer)
      this.healthCheckTimer = null
    }

    if (this.metricsFlushTimer) {
      clearInterval(this.metricsFlushTimer)
      this.metricsFlushTimer = null
    }

    this.errors = []
    this.metrics = []
    this.healthChecks.clear()
    this.circuitBreakers.clear()
    this.retryHandlers.clear()

    this.removeAllListeners()
  }
}

/**
 * Create a production monitor
 */
export function createMonitor(config?: Partial<MonitorConfig>): ProductionMonitor {
  return new ProductionMonitor(config)
}

/**
 * Global monitor instance
 */
export const monitor = createMonitor()
