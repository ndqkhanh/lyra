/**
 * Agent Orchestration System
 *
 * Coordinates multiple agents working together on complex tasks.
 *
 * Features:
 * - Agent coordinator with task distribution
 * - Task queue with priority scheduling
 * - Result aggregation and merging
 * - Error recovery and retry logic
 * - Agent lifecycle management
 * - Inter-agent communication
 * - Resource allocation
 */

import { EventEmitter } from 'eventemitter3'

/**
 * Agent status
 */
export type AgentStatus = 'idle' | 'busy' | 'paused' | 'error' | 'stopped'

/**
 * Task priority
 */
export type TaskPriority = 'critical' | 'high' | 'normal' | 'low'

/**
 * Task status
 */
export type TaskStatus = 'pending' | 'assigned' | 'running' | 'completed' | 'failed' | 'cancelled'

/**
 * Agent metadata
 */
export interface AgentMetadata {
  id: string
  name: string
  type: string
  capabilities: string[]
  maxConcurrentTasks: number
  priority: number
}

/**
 * Agent interface
 */
export interface Agent {
  metadata: AgentMetadata
  status: AgentStatus
  currentTasks: Set<string>
  execute: (task: Task) => Promise<TaskResult>
  pause: () => Promise<void>
  resume: () => Promise<void>
  stop: () => Promise<void>
}

/**
 * Task definition
 */
export interface Task {
  id: string
  type: string
  priority: TaskPriority
  payload: unknown
  requiredCapabilities: string[]
  timeout?: number
  retries?: number
  dependencies?: string[]
  metadata?: Record<string, unknown>
}

/**
 * Task result
 */
export interface TaskResult {
  taskId: string
  agentId: string
  status: 'success' | 'failure'
  result?: unknown
  error?: Error
  duration: number
  metadata?: Record<string, unknown>
}

/**
 * Task entry
 */
interface TaskEntry {
  task: Task
  status: TaskStatus
  assignedAgent?: string
  result?: TaskResult
  attempts: number
  createdAt: number
  startedAt?: number
  completedAt?: number
}

/**
 * Orchestrator configuration
 */
export interface OrchestratorConfig {
  /** Maximum concurrent tasks across all agents */
  maxConcurrentTasks: number
  /** Task timeout in ms */
  defaultTaskTimeout: number
  /** Maximum retry attempts */
  maxRetries: number
  /** Retry delay in ms */
  retryDelay: number
  /** Enable task dependencies */
  enableDependencies: boolean
  /** Enable result aggregation */
  enableAggregation: boolean
  /** Scheduling strategy */
  schedulingStrategy: 'priority' | 'round-robin' | 'least-loaded' | 'capability-match'
}

/**
 * Orchestration statistics
 */
export interface OrchestratorStats {
  totalAgents: number
  activeAgents: number
  idleAgents: number
  totalTasks: number
  pendingTasks: number
  runningTasks: number
  completedTasks: number
  failedTasks: number
  averageTaskDuration: number
  successRate: number
}

/**
 * Agent Orchestrator
 */
export class AgentOrchestrator extends EventEmitter {
  private agents = new Map<string, Agent>()
  private tasks = new Map<string, TaskEntry>()
  private config: OrchestratorConfig
  private taskQueue: string[] = []
  private runningTasks = new Set<string>()
  private completedTasks: TaskResult[] = []
  private schedulerTimer: NodeJS.Timeout | null = null

  constructor(config: Partial<OrchestratorConfig> = {}) {
    super()
    this.config = {
      maxConcurrentTasks: config.maxConcurrentTasks ?? 10,
      defaultTaskTimeout: config.defaultTaskTimeout ?? 300000, // 5 minutes
      maxRetries: config.maxRetries ?? 3,
      retryDelay: config.retryDelay ?? 1000,
      enableDependencies: config.enableDependencies ?? true,
      enableAggregation: config.enableAggregation ?? true,
      schedulingStrategy: config.schedulingStrategy ?? 'capability-match'
    }
  }

  /**
   * Register an agent
   */
  registerAgent(agent: Agent): void {
    if (this.agents.has(agent.metadata.id)) {
      throw new Error(`Agent ${agent.metadata.id} is already registered`)
    }

    this.agents.set(agent.metadata.id, agent)
    this.emit('agent-registered', agent.metadata.id)

    // Start scheduler if not running
    if (!this.schedulerTimer) {
      this.startScheduler()
    }
  }

  /**
   * Unregister an agent
   */
  async unregisterAgent(agentId: string): Promise<void> {
    const agent = this.agents.get(agentId)
    if (!agent) return

    // Stop agent
    await agent.stop()

    // Reassign tasks
    for (const taskId of agent.currentTasks) {
      const entry = this.tasks.get(taskId)
      if (entry && entry.status === 'running') {
        entry.status = 'pending'
        entry.assignedAgent = undefined
        this.taskQueue.push(taskId)
      }
    }

    this.agents.delete(agentId)
    this.emit('agent-unregistered', agentId)

    // Stop scheduler if no agents
    if (this.agents.size === 0 && this.schedulerTimer) {
      this.stopScheduler()
    }
  }

  /**
   * Submit a task
   */
  submitTask(task: Task): string {
    // Validate task
    if (this.tasks.has(task.id)) {
      throw new Error(`Task ${task.id} already exists`)
    }

    // Check dependencies
    if (this.config.enableDependencies && task.dependencies) {
      for (const depId of task.dependencies) {
        const depEntry = this.tasks.get(depId)
        if (!depEntry) {
          throw new Error(`Dependency ${depId} not found for task ${task.id}`)
        }
        if (depEntry.status !== 'completed') {
          throw new Error(`Dependency ${depId} not completed for task ${task.id}`)
        }
      }
    }

    // Create entry
    const entry: TaskEntry = {
      task,
      status: 'pending',
      attempts: 0,
      createdAt: Date.now()
    }

    this.tasks.set(task.id, entry)

    // Add to queue
    this.enqueueTask(task.id)

    this.emit('task-submitted', task.id)

    return task.id
  }

  /**
   * Cancel a task
   */
  cancelTask(taskId: string): boolean {
    const entry = this.tasks.get(taskId)
    if (!entry) return false

    if (entry.status === 'completed' || entry.status === 'failed') {
      return false
    }

    if (entry.status === 'running' && entry.assignedAgent) {
      // Remove from agent
      const agent = this.agents.get(entry.assignedAgent)
      if (agent) {
        agent.currentTasks.delete(taskId)
      }
      this.runningTasks.delete(taskId)
    }

    if (entry.status === 'pending') {
      // Remove from queue
      const index = this.taskQueue.indexOf(taskId)
      if (index !== -1) {
        this.taskQueue.splice(index, 1)
      }
    }

    entry.status = 'cancelled'
    this.emit('task-cancelled', taskId)

    return true
  }

  /**
   * Get task status
   */
  getTaskStatus(taskId: string): TaskStatus | null {
    return this.tasks.get(taskId)?.status ?? null
  }

  /**
   * Get task result
   */
  getTaskResult(taskId: string): TaskResult | null {
    return this.tasks.get(taskId)?.result ?? null
  }

  /**
   * Get agent status
   */
  getAgentStatus(agentId: string): AgentStatus | null {
    return this.agents.get(agentId)?.status ?? null
  }

  /**
   * Get statistics
   */
  getStats(): OrchestratorStats {
    const entries = Array.from(this.tasks.values())
    const agents = Array.from(this.agents.values())

    const completedEntries = entries.filter(e => e.status === 'completed')
    const totalDuration = completedEntries.reduce((sum, e) => {
      return sum + (e.result?.duration ?? 0)
    }, 0)

    return {
      totalAgents: agents.length,
      activeAgents: agents.filter(a => a.status === 'busy').length,
      idleAgents: agents.filter(a => a.status === 'idle').length,
      totalTasks: entries.length,
      pendingTasks: entries.filter(e => e.status === 'pending').length,
      runningTasks: entries.filter(e => e.status === 'running').length,
      completedTasks: entries.filter(e => e.status === 'completed').length,
      failedTasks: entries.filter(e => e.status === 'failed').length,
      averageTaskDuration: completedEntries.length > 0 ? totalDuration / completedEntries.length : 0,
      successRate: entries.length > 0
        ? (entries.filter(e => e.status === 'completed').length / entries.length) * 100
        : 0
    }
  }

  /**
   * Aggregate results
   */
  aggregateResults(taskIds: string[]): unknown[] {
    if (!this.config.enableAggregation) {
      throw new Error('Result aggregation is disabled')
    }

    const results: unknown[] = []

    for (const taskId of taskIds) {
      const entry = this.tasks.get(taskId)
      if (entry?.result?.status === 'success') {
        results.push(entry.result.result)
      }
    }

    return results
  }

  /**
   * Private: Enqueue task
   */
  private enqueueTask(taskId: string): void {
    const entry = this.tasks.get(taskId)
    if (!entry) return

    // Insert based on priority
    const priority = this.getPriorityValue(entry.task.priority)
    let insertIndex = this.taskQueue.length

    for (let i = 0; i < this.taskQueue.length; i++) {
      const queuedEntry = this.tasks.get(this.taskQueue[i]!)
      if (queuedEntry) {
        const queuedPriority = this.getPriorityValue(queuedEntry.task.priority)
        if (priority > queuedPriority) {
          insertIndex = i
          break
        }
      }
    }

    this.taskQueue.splice(insertIndex, 0, taskId)
  }

  /**
   * Private: Get priority value
   */
  private getPriorityValue(priority: TaskPriority): number {
    switch (priority) {
      case 'critical': return 4
      case 'high': return 3
      case 'normal': return 2
      case 'low': return 1
      default: return 0
    }
  }

  /**
   * Private: Start scheduler
   */
  private startScheduler(): void {
    if (this.schedulerTimer) return

    this.schedulerTimer = setInterval(() => {
      this.scheduleTasks()
    }, 100) // Check every 100ms
  }

  /**
   * Private: Stop scheduler
   */
  private stopScheduler(): void {
    if (this.schedulerTimer) {
      clearInterval(this.schedulerTimer)
      this.schedulerTimer = null
    }
  }

  /**
   * Private: Schedule tasks
   */
  private scheduleTasks(): void {
    // Check if we can schedule more tasks
    if (this.runningTasks.size >= this.config.maxConcurrentTasks) {
      return
    }

    // Get next task from queue
    while (this.taskQueue.length > 0 && this.runningTasks.size < this.config.maxConcurrentTasks) {
      const taskId = this.taskQueue.shift()
      if (!taskId) continue

      const entry = this.tasks.get(taskId)
      if (!entry || entry.status !== 'pending') continue

      // Find suitable agent
      const agent = this.findAgent(entry.task)
      if (!agent) {
        // No suitable agent, put back in queue
        this.taskQueue.unshift(taskId)
        break
      }

      // Assign task to agent
      this.assignTask(taskId, agent)
    }
  }

  /**
   * Private: Find suitable agent
   */
  private findAgent(task: Task): Agent | null {
    const availableAgents = Array.from(this.agents.values()).filter(agent => {
      // Check status
      if (agent.status !== 'idle' && agent.status !== 'busy') return false

      // Check capacity
      if (agent.currentTasks.size >= agent.metadata.maxConcurrentTasks) return false

      // Check capabilities
      if (task.requiredCapabilities.length > 0) {
        const hasCapabilities = task.requiredCapabilities.every(cap =>
          agent.metadata.capabilities.includes(cap)
        )
        if (!hasCapabilities) return false
      }

      return true
    })

    if (availableAgents.length === 0) return null

    // Select agent based on strategy
    switch (this.config.schedulingStrategy) {
      case 'priority':
        return availableAgents.sort((a, b) => b.metadata.priority - a.metadata.priority)[0]!

      case 'round-robin':
        return availableAgents[0]!

      case 'least-loaded':
        return availableAgents.sort((a, b) => a.currentTasks.size - b.currentTasks.size)[0]!

      case 'capability-match':
        // Prefer agents with exact capability match
        const exactMatch = availableAgents.find(agent =>
          task.requiredCapabilities.every(cap => agent.metadata.capabilities.includes(cap)) &&
          agent.metadata.capabilities.length === task.requiredCapabilities.length
        )
        return exactMatch ?? availableAgents[0]!

      default:
        return availableAgents[0]!
    }
  }

  /**
   * Private: Assign task to agent
   */
  private async assignTask(taskId: string, agent: Agent): Promise<void> {
    const entry = this.tasks.get(taskId)
    if (!entry) return

    entry.status = 'assigned'
    entry.assignedAgent = agent.metadata.id
    entry.startedAt = Date.now()

    agent.currentTasks.add(taskId)
    this.runningTasks.add(taskId)

    this.emit('task-assigned', taskId, agent.metadata.id)

    // Execute task
    this.executeTask(taskId, agent)
  }

  /**
   * Private: Execute task
   */
  private async executeTask(taskId: string, agent: Agent): Promise<void> {
    const entry = this.tasks.get(taskId)
    if (!entry) return

    entry.status = 'running'
    this.emit('task-started', taskId, agent.metadata.id)

    try {
      // Execute with timeout
      const timeout = entry.task.timeout ?? this.config.defaultTaskTimeout
      const result = await this.executeWithTimeout(
        agent.execute(entry.task),
        timeout,
        `Task ${taskId}`
      )

      // Task completed successfully
      entry.status = 'completed'
      entry.result = result
      entry.completedAt = Date.now()

      this.completedTasks.push(result)

      this.emit('task-completed', taskId, result)
    } catch (error) {
      // Task failed
      entry.attempts++

      const shouldRetry = entry.attempts < (entry.task.retries ?? this.config.maxRetries)

      if (shouldRetry) {
        // Retry task
        entry.status = 'pending'
        entry.assignedAgent = undefined

        setTimeout(() => {
          this.enqueueTask(taskId)
        }, this.config.retryDelay)

        this.emit('task-retry', taskId, entry.attempts)
      } else {
        // Task failed permanently
        entry.status = 'failed'
        entry.result = {
          taskId,
          agentId: agent.metadata.id,
          status: 'failure',
          error: error instanceof Error ? error : new Error(String(error)),
          duration: Date.now() - entry.startedAt!
        }
        entry.completedAt = Date.now()

        this.emit('task-failed', taskId, error)
      }
    } finally {
      // Cleanup
      agent.currentTasks.delete(taskId)
      this.runningTasks.delete(taskId)

      // Update agent status
      if (agent.currentTasks.size === 0) {
        agent.status = 'idle'
      }
    }
  }

  /**
   * Private: Execute with timeout
   */
  private async executeWithTimeout<T>(
    promise: Promise<T>,
    timeout: number,
    operation: string
  ): Promise<T> {
    return Promise.race([
      promise,
      new Promise<T>((_, reject) =>
        setTimeout(() => reject(new Error(`Timeout: ${operation}`)), timeout)
      )
    ])
  }

  /**
   * Cleanup orchestrator
   */
  async cleanup(): Promise<void> {
    this.stopScheduler()

    // Stop all agents
    const stopPromises = Array.from(this.agents.values()).map(agent => agent.stop())
    await Promise.all(stopPromises)

    this.agents.clear()
    this.tasks.clear()
    this.taskQueue = []
    this.runningTasks.clear()
    this.completedTasks = []

    this.removeAllListeners()
  }
}

/**
 * Create an orchestrator
 */
export function createOrchestrator(config?: Partial<OrchestratorConfig>): AgentOrchestrator {
  return new AgentOrchestrator(config)
}
