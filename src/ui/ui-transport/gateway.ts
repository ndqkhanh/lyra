/**
 * Multi-Channel Gateway
 *
 * Unified gateway for handling multiple communication channels (WebSocket, HTTP, IPC)
 * simultaneously with intelligent routing, failover, and priority queuing.
 *
 * Based on Hermes Agent's multi-channel architecture.
 *
 * Features:
 * - Multiple transport support (WebSocket, HTTP, IPC)
 * - Automatic failover
 * - Priority-based message routing
 * - Connection health monitoring
 * - Message queuing and retry
 * - Channel-specific optimizations
 */

import { EventEmitter } from 'eventemitter3'
import type {
  Transport,
  ConnectionStatus,
  StreamChunk,
  StreamEvent,
  Message,
  Attachment
} from '@lyra/ui-core'

/**
 * Channel types supported by the gateway
 */
export type ChannelType = 'websocket' | 'http' | 'ipc' | 'custom'

/**
 * Channel priority for routing decisions
 */
export type ChannelPriority = 'high' | 'medium' | 'low'

/**
 * Channel configuration
 */
export interface ChannelConfig {
  /** Channel identifier */
  id: string
  /** Channel type */
  type: ChannelType
  /** Transport implementation */
  transport: Transport
  /** Priority for routing (higher = preferred) */
  priority: ChannelPriority
  /** Enable automatic failover to this channel */
  failover: boolean
  /** Maximum retry attempts */
  maxRetries: number
  /** Retry delay in ms */
  retryDelay: number
  /** Health check interval in ms (0 = disabled) */
  healthCheckInterval: number
}

/**
 * Message routing strategy
 */
export type RoutingStrategy =
  | 'priority'      // Use highest priority available channel
  | 'round-robin'   // Distribute across channels
  | 'broadcast'     // Send to all channels
  | 'failover'      // Try primary, fallback on failure

/**
 * Gateway configuration
 */
export interface GatewayConfig {
  /** Routing strategy */
  strategy: RoutingStrategy
  /** Enable automatic reconnection */
  autoReconnect: boolean
  /** Reconnection delay in ms */
  reconnectDelay: number
  /** Maximum reconnection attempts */
  maxReconnectAttempts: number
  /** Enable message queuing when disconnected */
  queueMessages: boolean
  /** Maximum queue size */
  maxQueueSize: number
}

/**
 * Channel health status
 */
export interface ChannelHealth {
  channelId: string
  status: ConnectionStatus
  latency: number
  lastMessageTime: number
  errorCount: number
  successCount: number
}

/**
 * Gateway statistics
 */
export interface GatewayStats {
  totalMessages: number
  totalErrors: number
  channelStats: Map<string, ChannelHealth>
  activeChannels: number
  queuedMessages: number
}

/**
 * Queued message with metadata
 */
interface QueuedMessage {
  id: string
  content: string
  attachments?: Attachment[]
  model?: string
  timestamp: number
  retries: number
  channelId?: string  // Preferred channel
}

/**
 * Multi-channel gateway for unified transport management
 */
export class MultiChannelGateway extends EventEmitter implements Transport {
  private channels = new Map<string, ChannelConfig>()
  private channelHealth = new Map<string, ChannelHealth>()
  private config: GatewayConfig
  private messageQueue: QueuedMessage[] = []
  private stats = {
    totalMessages: 0,
    totalErrors: 0
  }
  private sessionId: string | null = null
  private reconnectAttempts = 0
  private reconnectTimer: NodeJS.Timeout | null = null
  private healthCheckTimers = new Map<string, NodeJS.Timeout>()
  private roundRobinIndex = 0

  constructor(config: Partial<GatewayConfig> = {}) {
    super()
    this.config = {
      strategy: config.strategy ?? 'priority',
      autoReconnect: config.autoReconnect ?? true,
      reconnectDelay: config.reconnectDelay ?? 1000,
      maxReconnectAttempts: config.maxReconnectAttempts ?? 5,
      queueMessages: config.queueMessages ?? true,
      maxQueueSize: config.maxQueueSize ?? 100
    }
  }

  /**
   * Get current connection status (aggregate of all channels)
   */
  get status(): ConnectionStatus {
    const channels = Array.from(this.channels.values())

    if (channels.length === 0) {
      return 'disconnected'
    }

    // If any channel is connected, gateway is connected
    if (channels.some(ch => ch.transport.status === 'connected')) {
      return 'connected'
    }

    // If any channel is connecting, gateway is connecting
    if (channels.some(ch => ch.transport.status === 'connecting')) {
      return 'connecting'
    }

    // If all channels have errors, gateway has error
    if (channels.every(ch => ch.transport.status === 'error')) {
      return 'error'
    }

    return 'disconnected'
  }

  /**
   * Add a channel to the gateway
   */
  addChannel(config: ChannelConfig): void {
    // Initialize health tracking
    this.channelHealth.set(config.id, {
      channelId: config.id,
      status: config.transport.status,
      latency: 0,
      lastMessageTime: 0,
      errorCount: 0,
      successCount: 0
    })

    // Set up event listeners
    this.setupChannelListeners(config)

    // Store channel
    this.channels.set(config.id, config)

    // Start health checks if enabled
    if (config.healthCheckInterval > 0) {
      this.startHealthCheck(config.id)
    }

    this.emit('channel-added', config.id)
  }

  /**
   * Remove a channel from the gateway
   */
  async removeChannel(channelId: string): Promise<void> {
    const config = this.channels.get(channelId)
    if (!config) return

    // Stop health checks
    this.stopHealthCheck(channelId)

    // Disconnect transport
    await config.transport.disconnect()

    // Clean up
    this.channels.delete(channelId)
    this.channelHealth.delete(channelId)

    this.emit('channel-removed', channelId)
  }

  /**
   * Set session ID for all channels
   */
  setSessionId(id: string): void {
    this.sessionId = id
    for (const config of this.channels.values()) {
      config.transport.setSessionId(id)
    }
  }

  /**
   * Get current session ID
   */
  getSessionId(): string | null {
    return this.sessionId
  }

  /**
   * Connect all channels
   */
  async connect(): Promise<void> {
    const promises = Array.from(this.channels.values()).map(async (config) => {
      try {
        await config.transport.connect()
        this.updateChannelHealth(config.id, { status: 'connected' })
      } catch (error) {
        this.updateChannelHealth(config.id, { status: 'error' })
        this.emit('error', error instanceof Error ? error : new Error(String(error)))
      }
    })

    await Promise.allSettled(promises)

    // Flush queued messages if any channel is connected
    if (this.status === 'connected') {
      await this.flushQueue()
    }

    this.emit('status', this.status)
  }

  /**
   * Disconnect all channels
   */
  async disconnect(): Promise<void> {
    // Stop reconnection attempts
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    // Stop all health checks
    for (const channelId of this.channels.keys()) {
      this.stopHealthCheck(channelId)
    }

    // Disconnect all channels
    const promises = Array.from(this.channels.values()).map(config =>
      config.transport.disconnect()
    )

    await Promise.allSettled(promises)

    this.emit('status', this.status)
  }

  /**
   * Send message through the gateway
   */
  async sendMessage(content: string, attachments?: Attachment[], model?: string): Promise<void> {
    // Select channel based on strategy
    const channel = this.selectChannel()

    if (!channel) {
      // No available channels - queue if enabled
      if (this.config.queueMessages) {
        this.queueMessage(content, attachments, model)
        return
      }
      throw new Error('No available channels')
    }

    try {
      const startTime = Date.now()
      await channel.transport.sendMessage(content, attachments, model)

      // Update stats
      const latency = Date.now() - startTime
      this.stats.totalMessages++
      this.updateChannelHealth(channel.id, {
        latency,
        lastMessageTime: Date.now(),
        successCount: (this.channelHealth.get(channel.id)?.successCount ?? 0) + 1
      })
    } catch (error) {
      // Update error stats
      this.stats.totalErrors++
      this.updateChannelHealth(channel.id, {
        errorCount: (this.channelHealth.get(channel.id)?.errorCount ?? 0) + 1
      })

      // Try failover if enabled
      if (this.config.strategy === 'failover') {
        const failoverChannel = this.selectFailoverChannel(channel.id)
        if (failoverChannel) {
          try {
            await failoverChannel.transport.sendMessage(content, attachments, model)
            return
          } catch (failoverError) {
            // Failover also failed
          }
        }
      }

      // Queue message for retry if enabled
      if (this.config.queueMessages) {
        this.queueMessage(content, attachments, model, channel.id)
      }

      throw error
    }
  }

  /**
   * Event handlers
   */
  onMessage(handler: (message: Message) => void): () => void {
    this.on('message', handler)
    return () => this.off('message', handler)
  }

  onStreamChunk(handler: (chunk: StreamChunk) => void): () => void {
    this.on('stream-chunk', handler)
    return () => this.off('stream-chunk', handler)
  }

  onStreamEvent(handler: (event: StreamEvent) => void): () => void {
    this.on('stream-event', handler)
    return () => this.off('stream-event', handler)
  }

  onError(handler: (error: Error) => void): () => void {
    this.on('error', handler)
    return () => this.off('error', handler)
  }

  onStatusChange(handler: (status: ConnectionStatus) => void): () => void {
    this.on('status', handler)
    return () => this.off('status', handler)
  }

  /**
   * Get gateway statistics
   */
  getStats(): GatewayStats {
    return {
      totalMessages: this.stats.totalMessages,
      totalErrors: this.stats.totalErrors,
      channelStats: new Map(this.channelHealth),
      activeChannels: Array.from(this.channels.values())
        .filter(ch => ch.transport.status === 'connected').length,
      queuedMessages: this.messageQueue.length
    }
  }

  /**
   * Get channel health
   */
  getChannelHealth(channelId: string): ChannelHealth | null {
    return this.channelHealth.get(channelId) ?? null
  }

  /**
   * Private: Set up event listeners for a channel
   */
  private setupChannelListeners(config: ChannelConfig): void {
    const { transport, id } = config

    // Forward events from channel to gateway
    transport.onMessage((message) => {
      this.emit('message', message)
    })

    transport.onStreamChunk((chunk) => {
      this.emit('stream-chunk', chunk)
    })

    transport.onStreamEvent((event) => {
      this.emit('stream-event', event)
    })

    transport.onError((error) => {
      this.updateChannelHealth(id, {
        status: 'error',
        errorCount: (this.channelHealth.get(id)?.errorCount ?? 0) + 1
      })
      this.emit('error', error)

      // Attempt reconnection if enabled
      if (this.config.autoReconnect) {
        this.scheduleReconnect(id)
      }
    })

    transport.onStatusChange((status) => {
      this.updateChannelHealth(id, { status })
      this.emit('status', this.status)
    })
  }

  /**
   * Private: Select channel based on routing strategy
   */
  private selectChannel(): ChannelConfig | null {
    const availableChannels = Array.from(this.channels.values())
      .filter(ch => ch.transport.status === 'connected')

    if (availableChannels.length === 0) {
      return null
    }

    switch (this.config.strategy) {
      case 'priority':
        return this.selectByPriority(availableChannels)

      case 'round-robin':
        return this.selectRoundRobin(availableChannels)

      case 'failover':
        return this.selectByPriority(availableChannels)

      case 'broadcast':
        // For broadcast, return first channel (will send to all in sendMessage)
        return availableChannels[0] ?? null

      default:
        return availableChannels[0] ?? null
    }
  }

  /**
   * Private: Select channel by priority
   */
  private selectByPriority(channels: ChannelConfig[]): ChannelConfig | null {
    const priorityMap = { high: 3, medium: 2, low: 1 }

    return channels.sort((a, b) =>
      priorityMap[b.priority] - priorityMap[a.priority]
    )[0] ?? null
  }

  /**
   * Private: Select channel using round-robin
   */
  private selectRoundRobin(channels: ChannelConfig[]): ChannelConfig | null {
    if (channels.length === 0) return null

    const channel = channels[this.roundRobinIndex % channels.length]
    this.roundRobinIndex++

    return channel ?? null
  }

  /**
   * Private: Select failover channel (exclude failed channel)
   */
  private selectFailoverChannel(excludeId: string): ChannelConfig | null {
    const availableChannels = Array.from(this.channels.values())
      .filter(ch =>
        ch.id !== excludeId &&
        ch.transport.status === 'connected' &&
        ch.failover
      )

    return this.selectByPriority(availableChannels)
  }

  /**
   * Private: Queue message for later delivery
   */
  private queueMessage(
    content: string,
    attachments?: Attachment[],
    model?: string,
    channelId?: string
  ): void {
    if (this.messageQueue.length >= this.config.maxQueueSize) {
      // Remove oldest message
      this.messageQueue.shift()
    }

    this.messageQueue.push({
      id: `msg-${Date.now()}-${Math.random()}`,
      content,
      attachments,
      model,
      timestamp: Date.now(),
      retries: 0,
      channelId
    })

    this.emit('message-queued', this.messageQueue.length)
  }

  /**
   * Private: Flush queued messages
   */
  private async flushQueue(): Promise<void> {
    while (this.messageQueue.length > 0 && this.status === 'connected') {
      const msg = this.messageQueue.shift()!

      try {
        await this.sendMessage(msg.content, msg.attachments, msg.model)
      } catch (error) {
        // Re-queue if retries available
        if (msg.retries < 3) {
          msg.retries++
          this.messageQueue.unshift(msg)
        }
        break
      }
    }
  }

  /**
   * Private: Update channel health
   */
  private updateChannelHealth(channelId: string, updates: Partial<ChannelHealth>): void {
    const current = this.channelHealth.get(channelId)
    if (!current) return

    this.channelHealth.set(channelId, {
      ...current,
      ...updates
    })

    this.emit('channel-health', channelId, this.channelHealth.get(channelId))
  }

  /**
   * Private: Schedule reconnection attempt
   */
  private scheduleReconnect(channelId: string): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      return
    }

    if (this.reconnectTimer) {
      return  // Already scheduled
    }

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null
      this.reconnectAttempts++

      const config = this.channels.get(channelId)
      if (!config) return

      try {
        await config.transport.connect()
        this.reconnectAttempts = 0  // Reset on success
        await this.flushQueue()
      } catch (error) {
        // Will retry on next error
      }
    }, this.config.reconnectDelay)
  }

  /**
   * Private: Start health check for a channel
   */
  private startHealthCheck(channelId: string): void {
    const config = this.channels.get(channelId)
    if (!config || config.healthCheckInterval <= 0) return

    const timer = setInterval(() => {
      const health = this.channelHealth.get(channelId)
      if (!health) return

      // Check if channel is stale (no messages in 2x health check interval)
      const now = Date.now()
      const staleThreshold = config.healthCheckInterval * 2

      if (health.lastMessageTime > 0 && now - health.lastMessageTime > staleThreshold) {
        this.emit('channel-stale', channelId)
      }
    }, config.healthCheckInterval)

    this.healthCheckTimers.set(channelId, timer)
  }

  /**
   * Private: Stop health check for a channel
   */
  private stopHealthCheck(channelId: string): void {
    const timer = this.healthCheckTimers.get(channelId)
    if (timer) {
      clearInterval(timer)
      this.healthCheckTimers.delete(channelId)
    }
  }
}

/**
 * Create a multi-channel gateway with default configuration
 */
export function createGateway(config?: Partial<GatewayConfig>): MultiChannelGateway {
  return new MultiChannelGateway(config)
}
