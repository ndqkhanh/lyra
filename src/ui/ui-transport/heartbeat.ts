/**
 * Heartbeat System
 *
 * Connection health monitoring with ping/pong protocol, auto-reconnect,
 * connection quality metrics, and graceful degradation.
 *
 * Features:
 * - Ping/pong protocol
 * - Connection quality metrics (latency, packet loss, jitter)
 * - Automatic reconnection with exponential backoff
 * - Graceful degradation
 * - Connection state machine
 * - Health scoring
 */

import { EventEmitter } from 'eventemitter3'

/**
 * Connection state
 */
export type ConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'degraded'
  | 'reconnecting'
  | 'failed'

/**
 * Connection quality
 */
export type ConnectionQuality = 'excellent' | 'good' | 'fair' | 'poor' | 'critical'

/**
 * Heartbeat configuration
 */
export interface HeartbeatConfig {
  /** Ping interval in ms */
  pingInterval: number
  /** Pong timeout in ms */
  pongTimeout: number
  /** Max missed pongs before reconnect */
  maxMissedPongs: number
  /** Enable auto-reconnect */
  autoReconnect: boolean
  /** Initial reconnect delay in ms */
  reconnectDelay: number
  /** Max reconnect delay in ms */
  maxReconnectDelay: number
  /** Reconnect backoff multiplier */
  reconnectBackoff: number
  /** Max reconnect attempts (0 = infinite) */
  maxReconnectAttempts: number
  /** Enable quality metrics */
  trackQuality: boolean
  /** Quality check interval in ms */
  qualityCheckInterval: number
  /** Enable graceful degradation */
  gracefulDegradation: boolean
}

/**
 * Connection metrics
 */
export interface ConnectionMetrics {
  /** Average latency in ms */
  latency: number
  /** Latency jitter in ms */
  jitter: number
  /** Packet loss percentage (0-100) */
  packetLoss: number
  /** Total pings sent */
  pingsSent: number
  /** Total pongs received */
  pongsReceived: number
  /** Total missed pongs */
  missedPongs: number
  /** Connection uptime in ms */
  uptime: number
  /** Last ping time */
  lastPingTime: number
  /** Last pong time */
  lastPongTime: number
  /** Connection quality */
  quality: ConnectionQuality
  /** Health score (0-100) */
  healthScore: number
}

/**
 * Ping message
 */
export interface PingMessage {
  type: 'ping'
  id: string
  timestamp: number
}

/**
 * Pong message
 */
export interface PongMessage {
  type: 'pong'
  id: string
  timestamp: number
  serverTime?: number
}

/**
 * Heartbeat monitor
 */
export class HeartbeatMonitor extends EventEmitter {
  private config: HeartbeatConfig
  private state: ConnectionState = 'disconnected'
  private metrics: ConnectionMetrics = {
    latency: 0,
    jitter: 0,
    packetLoss: 0,
    pingsSent: 0,
    pongsReceived: 0,
    missedPongs: 0,
    uptime: 0,
    lastPingTime: 0,
    lastPongTime: 0,
    quality: 'excellent',
    healthScore: 100
  }

  private pingTimer: NodeJS.Timeout | null = null
  private pongTimer: NodeJS.Timeout | null = null
  private qualityTimer: NodeJS.Timeout | null = null
  private reconnectTimer: NodeJS.Timeout | null = null

  private pendingPings = new Map<string, number>()
  private latencyHistory: number[] = []
  private connectTime: number = 0
  private reconnectAttempts: number = 0
  private currentReconnectDelay: number = 0

  private sendPing: (ping: PingMessage) => void
  private reconnect: () => Promise<void>

  constructor(
    sendPing: (ping: PingMessage) => void,
    reconnect: () => Promise<void>,
    config: Partial<HeartbeatConfig> = {}
  ) {
    super()
    this.sendPing = sendPing
    this.reconnect = reconnect
    this.config = {
      pingInterval: config.pingInterval ?? 5000,
      pongTimeout: config.pongTimeout ?? 10000,
      maxMissedPongs: config.maxMissedPongs ?? 3,
      autoReconnect: config.autoReconnect ?? true,
      reconnectDelay: config.reconnectDelay ?? 1000,
      maxReconnectDelay: config.maxReconnectDelay ?? 30000,
      reconnectBackoff: config.reconnectBackoff ?? 2,
      maxReconnectAttempts: config.maxReconnectAttempts ?? 0,
      trackQuality: config.trackQuality ?? true,
      qualityCheckInterval: config.qualityCheckInterval ?? 10000,
      gracefulDegradation: config.gracefulDegradation ?? true
    }
    this.currentReconnectDelay = this.config.reconnectDelay
  }

  /**
   * Start heartbeat monitoring
   */
  start(): void {
    if (this.state !== 'disconnected') return

    this.state = 'connected'
    this.connectTime = Date.now()
    this.reconnectAttempts = 0
    this.currentReconnectDelay = this.config.reconnectDelay

    // Start ping timer
    this.startPingTimer()

    // Start quality monitoring
    if (this.config.trackQuality) {
      this.startQualityTimer()
    }

    this.emit('state-change', this.state)
    this.emit('connected')
  }

  /**
   * Stop heartbeat monitoring
   */
  stop(): void {
    this.stopPingTimer()
    this.stopPongTimer()
    this.stopQualityTimer()
    this.stopReconnectTimer()

    this.state = 'disconnected'
    this.pendingPings.clear()

    this.emit('state-change', this.state)
    this.emit('disconnected')
  }

  /**
   * Handle received pong
   */
  handlePong(pong: PongMessage): void {
    const sendTime = this.pendingPings.get(pong.id)
    if (!sendTime) return

    // Calculate latency
    const latency = Date.now() - sendTime
    this.pendingPings.delete(pong.id)

    // Update metrics
    this.metrics.pongsReceived++
    this.metrics.lastPongTime = Date.now()
    this.updateLatency(latency)

    // Reset missed pongs counter
    this.metrics.missedPongs = 0

    // Stop pong timeout
    this.stopPongTimer()

    // Emit pong event
    this.emit('pong', { latency, pong })

    // Check if we should upgrade from degraded state
    if (this.state === 'degraded' && this.metrics.healthScore > 70) {
      this.state = 'connected'
      this.emit('state-change', this.state)
      this.emit('connection-restored')
    }
  }

  /**
   * Get current state
   */
  getState(): ConnectionState {
    return this.state
  }

  /**
   * Get current metrics
   */
  getMetrics(): ConnectionMetrics {
    // Update uptime
    if (this.state === 'connected' || this.state === 'degraded') {
      this.metrics.uptime = Date.now() - this.connectTime
    }

    return { ...this.metrics }
  }

  /**
   * Get connection quality
   */
  getQuality(): ConnectionQuality {
    return this.metrics.quality
  }

  /**
   * Get health score
   */
  getHealthScore(): number {
    return this.metrics.healthScore
  }

  /**
   * Force reconnect
   */
  async forceReconnect(): Promise<void> {
    this.stop()
    await this.attemptReconnect()
  }

  /**
   * Private: Start ping timer
   */
  private startPingTimer(): void {
    if (this.pingTimer) return

    this.pingTimer = setInterval(() => {
      this.sendPingMessage()
    }, this.config.pingInterval)

    // Send first ping immediately
    this.sendPingMessage()
  }

  /**
   * Private: Stop ping timer
   */
  private stopPingTimer(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
  }

  /**
   * Private: Send ping message
   */
  private sendPingMessage(): void {
    const ping: PingMessage = {
      type: 'ping',
      id: `ping-${Date.now()}-${Math.random()}`,
      timestamp: Date.now()
    }

    // Store pending ping
    this.pendingPings.set(ping.id, Date.now())

    // Update metrics
    this.metrics.pingsSent++
    this.metrics.lastPingTime = Date.now()

    // Send ping
    try {
      this.sendPing(ping)
      this.emit('ping', ping)

      // Start pong timeout
      this.startPongTimer(ping.id)
    } catch (error) {
      this.handlePingError(error)
    }
  }

  /**
   * Private: Start pong timeout
   */
  private startPongTimer(pingId: string): void {
    this.stopPongTimer()

    this.pongTimer = setTimeout(() => {
      this.handleMissedPong(pingId)
    }, this.config.pongTimeout)
  }

  /**
   * Private: Stop pong timeout
   */
  private stopPongTimer(): void {
    if (this.pongTimer) {
      clearTimeout(this.pongTimer)
      this.pongTimer = null
    }
  }

  /**
   * Private: Handle missed pong
   */
  private handleMissedPong(pingId: string): void {
    this.pendingPings.delete(pingId)
    this.metrics.missedPongs++

    this.emit('missed-pong', { pingId, missedCount: this.metrics.missedPongs })

    // Update health score
    this.updateHealthScore()

    // Check if we should degrade or reconnect
    if (this.metrics.missedPongs >= this.config.maxMissedPongs) {
      this.handleConnectionLoss()
    } else if (this.config.gracefulDegradation && this.metrics.healthScore < 50) {
      this.degradeConnection()
    }
  }

  /**
   * Private: Handle ping error
   */
  private handlePingError(error: unknown): void {
    this.emit('ping-error', error)
    this.handleConnectionLoss()
  }

  /**
   * Private: Handle connection loss
   */
  private handleConnectionLoss(): void {
    this.stopPingTimer()
    this.stopPongTimer()

    if (this.config.autoReconnect) {
      this.state = 'reconnecting'
      this.emit('state-change', this.state)
      this.emit('connection-lost')
      this.scheduleReconnect()
    } else {
      this.state = 'failed'
      this.emit('state-change', this.state)
      this.emit('connection-failed')
    }
  }

  /**
   * Private: Degrade connection
   */
  private degradeConnection(): void {
    if (this.state === 'degraded') return

    this.state = 'degraded'
    this.emit('state-change', this.state)
    this.emit('connection-degraded', {
      quality: this.metrics.quality,
      healthScore: this.metrics.healthScore
    })
  }

  /**
   * Private: Schedule reconnect
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) return

    // Check max attempts
    if (
      this.config.maxReconnectAttempts > 0 &&
      this.reconnectAttempts >= this.config.maxReconnectAttempts
    ) {
      this.state = 'failed'
      this.emit('state-change', this.state)
      this.emit('reconnect-failed', { attempts: this.reconnectAttempts })
      return
    }

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null
      await this.attemptReconnect()
    }, this.currentReconnectDelay)

    this.emit('reconnect-scheduled', {
      attempt: this.reconnectAttempts + 1,
      delay: this.currentReconnectDelay
    })

    // Increase delay for next attempt (exponential backoff)
    this.currentReconnectDelay = Math.min(
      this.currentReconnectDelay * this.config.reconnectBackoff,
      this.config.maxReconnectDelay
    )
  }

  /**
   * Private: Stop reconnect timer
   */
  private stopReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  /**
   * Private: Attempt reconnect
   */
  private async attemptReconnect(): Promise<void> {
    this.reconnectAttempts++

    this.emit('reconnect-attempt', { attempt: this.reconnectAttempts })

    try {
      await this.reconnect()

      // Reset reconnect state
      this.reconnectAttempts = 0
      this.currentReconnectDelay = this.config.reconnectDelay

      // Restart heartbeat
      this.start()

      this.emit('reconnected', { attempts: this.reconnectAttempts })
    } catch (error) {
      this.emit('reconnect-error', { attempt: this.reconnectAttempts, error })
      this.scheduleReconnect()
    }
  }

  /**
   * Private: Update latency
   */
  private updateLatency(latency: number): void {
    // Add to history
    this.latencyHistory.push(latency)

    // Keep last 10 samples
    if (this.latencyHistory.length > 10) {
      this.latencyHistory.shift()
    }

    // Calculate average latency
    this.metrics.latency =
      this.latencyHistory.reduce((sum, l) => sum + l, 0) / this.latencyHistory.length

    // Calculate jitter (standard deviation)
    const mean = this.metrics.latency
    const variance =
      this.latencyHistory.reduce((sum, l) => sum + Math.pow(l - mean, 2), 0) /
      this.latencyHistory.length
    this.metrics.jitter = Math.sqrt(variance)

    // Calculate packet loss
    this.metrics.packetLoss =
      this.metrics.pingsSent > 0
        ? ((this.metrics.pingsSent - this.metrics.pongsReceived) / this.metrics.pingsSent) * 100
        : 0

    // Update quality
    this.updateQuality()

    // Update health score
    this.updateHealthScore()
  }

  /**
   * Private: Update connection quality
   */
  private updateQuality(): void {
    const { latency, jitter, packetLoss } = this.metrics

    // Determine quality based on metrics
    if (latency < 50 && jitter < 10 && packetLoss < 1) {
      this.metrics.quality = 'excellent'
    } else if (latency < 100 && jitter < 20 && packetLoss < 3) {
      this.metrics.quality = 'good'
    } else if (latency < 200 && jitter < 50 && packetLoss < 5) {
      this.metrics.quality = 'fair'
    } else if (latency < 500 && jitter < 100 && packetLoss < 10) {
      this.metrics.quality = 'poor'
    } else {
      this.metrics.quality = 'critical'
    }
  }

  /**
   * Private: Update health score
   */
  private updateHealthScore(): void {
    const { latency, jitter, packetLoss, missedPongs } = this.metrics

    // Calculate component scores (0-100)
    const latencyScore = Math.max(0, 100 - latency / 5)
    const jitterScore = Math.max(0, 100 - jitter / 2)
    const packetLossScore = Math.max(0, 100 - packetLoss * 10)
    const missedPongsScore = Math.max(0, 100 - missedPongs * 20)

    // Weighted average
    this.metrics.healthScore = Math.round(
      latencyScore * 0.3 +
      jitterScore * 0.2 +
      packetLossScore * 0.3 +
      missedPongsScore * 0.2
    )

    this.emit('health-score-updated', this.metrics.healthScore)
  }

  /**
   * Private: Start quality timer
   */
  private startQualityTimer(): void {
    if (this.qualityTimer) return

    this.qualityTimer = setInterval(() => {
      this.emit('quality-check', {
        quality: this.metrics.quality,
        healthScore: this.metrics.healthScore,
        metrics: this.getMetrics()
      })
    }, this.config.qualityCheckInterval)
  }

  /**
   * Private: Stop quality timer
   */
  private stopQualityTimer(): void {
    if (this.qualityTimer) {
      clearInterval(this.qualityTimer)
      this.qualityTimer = null
    }
  }

  /**
   * Cleanup
   */
  cleanup(): void {
    this.stop()
    this.removeAllListeners()
  }
}

/**
 * Create a heartbeat monitor
 */
export function createHeartbeat(
  sendPing: (ping: PingMessage) => void,
  reconnect: () => Promise<void>,
  config?: Partial<HeartbeatConfig>
): HeartbeatMonitor {
  return new HeartbeatMonitor(sendPing, reconnect, config)
}
