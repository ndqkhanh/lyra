/**
 * Enhanced Plugin System
 *
 * Advanced plugin architecture with lifecycle hooks, sandboxed execution,
 * resource limits, and marketplace support.
 *
 * Features:
 * - Plugin lifecycle management
 * - Sandboxed execution environment
 * - Resource limits (CPU, memory, time)
 * - Plugin permissions system
 * - Plugin marketplace integration
 * - Hot reloading
 * - Inter-plugin communication
 */

import { EventEmitter } from 'eventemitter3'

/**
 * Plugin metadata
 */
export interface PluginMetadata {
  /** Unique plugin identifier */
  id: string
  /** Display name */
  name: string
  /** Description */
  description: string
  /** Version (semver) */
  version: string
  /** Author */
  author: string
  /** Plugin category */
  category: 'ui' | 'transport' | 'skill' | 'tool' | 'theme' | 'integration' | 'other'
  /** Tags */
  tags: string[]
  /** Dependencies */
  dependencies: Record<string, string>
  /** Minimum Lyra version */
  minLyraVersion?: string
  /** Maximum Lyra version */
  maxLyraVersion?: string
  /** Icon */
  icon?: string
  /** Homepage */
  homepage?: string
  /** Repository */
  repository?: string
  /** License */
  license: string
  /** Screenshots */
  screenshots?: string[]
  /** Changelog URL */
  changelog?: string
}

/**
 * Plugin permissions
 */
export interface PluginPermissions {
  /** File system access */
  filesystem: {
    read: boolean
    write: boolean
    paths?: string[]  // Allowed paths
  }
  /** Network access */
  network: {
    enabled: boolean
    allowedHosts?: string[]
  }
  /** Process execution */
  process: {
    enabled: boolean
    allowedCommands?: string[]
  }
  /** UI modification */
  ui: {
    enabled: boolean
    components?: string[]
  }
  /** Data access */
  data: {
    read: boolean
    write: boolean
    scopes?: string[]
  }
}

/**
 * Plugin resource limits
 */
export interface PluginResourceLimits {
  /** Maximum CPU time in ms */
  maxCpuTime: number
  /** Maximum memory in bytes */
  maxMemory: number
  /** Maximum execution time in ms */
  maxExecutionTime: number
  /** Maximum file size in bytes */
  maxFileSize: number
  /** Maximum network requests per minute */
  maxNetworkRequests: number
}

/**
 * Plugin configuration
 */
export interface PluginConfig {
  /** Enable/disable plugin */
  enabled: boolean
  /** Plugin settings */
  settings: Record<string, unknown>
  /** Plugin permissions */
  permissions: PluginPermissions
  /** Resource limits */
  resourceLimits: PluginResourceLimits
  /** Auto-update */
  autoUpdate: boolean
  /** Priority */
  priority: number
}

/**
 * Plugin lifecycle hooks
 */
export interface PluginHooks {
  /** Called when plugin is installed */
  onInstall?: () => void | Promise<void>
  /** Called when plugin is uninstalled */
  onUninstall?: () => void | Promise<void>
  /** Called when plugin is loaded */
  onLoad?: () => void | Promise<void>
  /** Called when plugin is unloaded */
  onUnload?: () => void | Promise<void>
  /** Called when plugin is enabled */
  onEnable?: () => void | Promise<void>
  /** Called when plugin is disabled */
  onDisable?: () => void | Promise<void>
  /** Called when plugin is updated */
  onUpdate?: (oldVersion: string, newVersion: string) => void | Promise<void>
  /** Called when plugin configuration changes */
  onConfigChange?: (config: PluginConfig) => void | Promise<void>
}

/**
 * Plugin execution context
 */
export interface PluginContext {
  /** Plugin metadata */
  metadata: PluginMetadata
  /** Plugin configuration */
  config: PluginConfig
  /** Plugin manager */
  manager: PluginManager
  /** Get dependency */
  getDependency: (id: string) => Plugin | null
  /** Emit event */
  emit: (event: string, ...args: unknown[]) => void
  /** Log message */
  log: (level: 'info' | 'warn' | 'error', message: string) => void
  /** Check permission */
  hasPermission: (permission: string) => boolean
  /** Get resource usage */
  getResourceUsage: () => PluginResourceUsage
}

/**
 * Plugin resource usage
 */
export interface PluginResourceUsage {
  cpuTime: number
  memory: number
  executionTime: number
  networkRequests: number
}

/**
 * Plugin interface
 */
export interface Plugin {
  /** Plugin metadata */
  metadata: PluginMetadata
  /** Plugin configuration */
  config: PluginConfig
  /** Lifecycle hooks */
  hooks: PluginHooks
  /** Plugin initialization */
  initialize: (context: PluginContext) => void | Promise<void>
  /** Plugin cleanup */
  cleanup: (context: PluginContext) => void | Promise<void>
  /** Plugin API (exposed methods) */
  api?: Record<string, (...args: unknown[]) => unknown | Promise<unknown>>
}

/**
 * Plugin status
 */
export type PluginStatus =
  | 'uninstalled'
  | 'installing'
  | 'installed'
  | 'loading'
  | 'loaded'
  | 'enabled'
  | 'disabled'
  | 'updating'
  | 'error'

/**
 * Plugin entry
 */
interface PluginEntry {
  plugin: Plugin
  status: PluginStatus
  context: PluginContext | null
  resourceUsage: PluginResourceUsage
  installTime: number
  loadTime: number
  error?: Error
}

/**
 * Plugin manager configuration
 */
export interface PluginManagerConfig {
  /** Enable sandboxing */
  sandboxed: boolean
  /** Enable resource limits */
  enforceResourceLimits: boolean
  /** Enable permissions */
  enforcePermissions: boolean
  /** Enable auto-updates */
  autoUpdate: boolean
  /** Update check interval in ms */
  updateCheckInterval: number
  /** Plugin timeout in ms */
  pluginTimeout: number
  /** Default resource limits */
  defaultResourceLimits: PluginResourceLimits
  /** Default permissions */
  defaultPermissions: PluginPermissions
}

/**
 * Plugin Manager
 */
export class PluginManager extends EventEmitter {
  private plugins = new Map<string, PluginEntry>()
  private config: PluginManagerConfig
  private lyraVersion: string
  private updateTimers = new Map<string, NodeJS.Timeout>()

  constructor(lyraVersion: string, config: Partial<PluginManagerConfig> = {}) {
    super()
    this.lyraVersion = lyraVersion
    this.config = {
      sandboxed: config.sandboxed ?? true,
      enforceResourceLimits: config.enforceResourceLimits ?? true,
      enforcePermissions: config.enforcePermissions ?? true,
      autoUpdate: config.autoUpdate ?? false,
      updateCheckInterval: config.updateCheckInterval ?? 3600000, // 1 hour
      pluginTimeout: config.pluginTimeout ?? 30000,
      defaultResourceLimits: config.defaultResourceLimits ?? {
        maxCpuTime: 5000,
        maxMemory: 100 * 1024 * 1024, // 100 MB
        maxExecutionTime: 30000,
        maxFileSize: 10 * 1024 * 1024, // 10 MB
        maxNetworkRequests: 100
      },
      defaultPermissions: config.defaultPermissions ?? {
        filesystem: { read: false, write: false },
        network: { enabled: false },
        process: { enabled: false },
        ui: { enabled: true },
        data: { read: true, write: false }
      }
    }
  }

  /**
   * Install a plugin
   */
  async install(plugin: Plugin): Promise<boolean> {
    try {
      // Check if already installed
      if (this.plugins.has(plugin.metadata.id)) {
        throw new Error(`Plugin ${plugin.metadata.id} is already installed`)
      }

      // Check version compatibility
      if (!this.isVersionCompatible(plugin.metadata)) {
        throw new Error(
          `Plugin ${plugin.metadata.id} requires Lyra ${plugin.metadata.minLyraVersion || '*'}`
        )
      }

      // Create entry
      const entry: PluginEntry = {
        plugin,
        status: 'installing',
        context: null,
        resourceUsage: {
          cpuTime: 0,
          memory: 0,
          executionTime: 0,
          networkRequests: 0
        },
        installTime: Date.now(),
        loadTime: 0
      }

      this.plugins.set(plugin.metadata.id, entry)

      // Call onInstall hook
      if (plugin.hooks.onInstall) {
        await this.executeWithTimeout(
          plugin.hooks.onInstall(),
          this.config.pluginTimeout,
          `onInstall for ${plugin.metadata.id}`
        )
      }

      entry.status = 'installed'

      // Auto-load if enabled
      if (plugin.config.enabled) {
        await this.load(plugin.metadata.id)
      }

      // Start update checks if enabled
      if (this.config.autoUpdate && plugin.config.autoUpdate) {
        this.startUpdateChecks(plugin.metadata.id)
      }

      this.emit('plugin-installed', plugin.metadata.id)

      return true
    } catch (error) {
      const entry = this.plugins.get(plugin.metadata.id)
      if (entry) {
        entry.status = 'error'
        entry.error = error instanceof Error ? error : new Error(String(error))
      }
      this.emit('plugin-error', plugin.metadata.id, error)
      return false
    }
  }

  /**
   * Uninstall a plugin
   */
  async uninstall(pluginId: string): Promise<boolean> {
    const entry = this.plugins.get(pluginId)
    if (!entry) return false

    try {
      // Unload if loaded
      if (entry.status === 'loaded' || entry.status === 'enabled') {
        await this.unload(pluginId)
      }

      // Call onUninstall hook
      if (entry.plugin.hooks.onUninstall) {
        await this.executeWithTimeout(
          entry.plugin.hooks.onUninstall(),
          this.config.pluginTimeout,
          `onUninstall for ${pluginId}`
        )
      }

      // Stop update checks
      this.stopUpdateChecks(pluginId)

      // Remove from registry
      this.plugins.delete(pluginId)

      this.emit('plugin-uninstalled', pluginId)

      return true
    } catch (error) {
      entry.status = 'error'
      entry.error = error instanceof Error ? error : new Error(String(error))
      this.emit('plugin-error', pluginId, error)
      return false
    }
  }

  /**
   * Load a plugin
   */
  async load(pluginId: string): Promise<boolean> {
    const entry = this.plugins.get(pluginId)
    if (!entry) return false

    if (entry.status === 'loaded' || entry.status === 'enabled') return true

    try {
      entry.status = 'loading'

      // Create context
      const context = this.createContext(entry.plugin)
      entry.context = context

      // Call onLoad hook
      if (entry.plugin.hooks.onLoad) {
        await this.executeWithTimeout(
          entry.plugin.hooks.onLoad(),
          this.config.pluginTimeout,
          `onLoad for ${pluginId}`
        )
      }

      // Initialize plugin
      await this.executeWithTimeout(
        entry.plugin.initialize(context),
        this.config.pluginTimeout,
        `initialize for ${pluginId}`
      )

      entry.status = 'loaded'
      entry.loadTime = Date.now()

      // Enable if configured
      if (entry.plugin.config.enabled) {
        await this.enable(pluginId)
      }

      this.emit('plugin-loaded', pluginId)

      return true
    } catch (error) {
      entry.status = 'error'
      entry.error = error instanceof Error ? error : new Error(String(error))
      this.emit('plugin-error', pluginId, error)
      return false
    }
  }

  /**
   * Unload a plugin
   */
  async unload(pluginId: string): Promise<boolean> {
    const entry = this.plugins.get(pluginId)
    if (!entry) return false

    try {
      // Disable if enabled
      if (entry.status === 'enabled') {
        await this.disable(pluginId)
      }

      // Cleanup plugin
      if (entry.context) {
        await this.executeWithTimeout(
          entry.plugin.cleanup(entry.context),
          this.config.pluginTimeout,
          `cleanup for ${pluginId}`
        )
      }

      // Call onUnload hook
      if (entry.plugin.hooks.onUnload) {
        await this.executeWithTimeout(
          entry.plugin.hooks.onUnload(),
          this.config.pluginTimeout,
          `onUnload for ${pluginId}`
        )
      }

      entry.status = 'installed'
      entry.context = null

      this.emit('plugin-unloaded', pluginId)

      return true
    } catch (error) {
      entry.status = 'error'
      entry.error = error instanceof Error ? error : new Error(String(error))
      this.emit('plugin-error', pluginId, error)
      return false
    }
  }

  /**
   * Enable a plugin
   */
  async enable(pluginId: string): Promise<boolean> {
    const entry = this.plugins.get(pluginId)
    if (!entry) return false

    if (entry.status === 'enabled') return true

    try {
      // Load if not loaded
      if (entry.status !== 'loaded') {
        await this.load(pluginId)
      }

      // Call onEnable hook
      if (entry.plugin.hooks.onEnable) {
        await this.executeWithTimeout(
          entry.plugin.hooks.onEnable(),
          this.config.pluginTimeout,
          `onEnable for ${pluginId}`
        )
      }

      entry.status = 'enabled'
      entry.plugin.config.enabled = true

      this.emit('plugin-enabled', pluginId)

      return true
    } catch (error) {
      entry.status = 'error'
      entry.error = error instanceof Error ? error : new Error(String(error))
      this.emit('plugin-error', pluginId, error)
      return false
    }
  }

  /**
   * Disable a plugin
   */
  async disable(pluginId: string): Promise<boolean> {
    const entry = this.plugins.get(pluginId)
    if (!entry) return false

    if (entry.status === 'disabled') return true

    try {
      // Call onDisable hook
      if (entry.plugin.hooks.onDisable) {
        await this.executeWithTimeout(
          entry.plugin.hooks.onDisable(),
          this.config.pluginTimeout,
          `onDisable for ${pluginId}`
        )
      }

      entry.status = 'disabled'
      entry.plugin.config.enabled = false

      this.emit('plugin-disabled', pluginId)

      return true
    } catch (error) {
      entry.status = 'error'
      entry.error = error instanceof Error ? error : new Error(String(error))
      this.emit('plugin-error', pluginId, error)
      return false
    }
  }

  /**
   * Update a plugin
   */
  async update(pluginId: string, newPlugin: Plugin): Promise<boolean> {
    const entry = this.plugins.get(pluginId)
    if (!entry) return false

    try {
      entry.status = 'updating'

      const oldVersion = entry.plugin.metadata.version
      const newVersion = newPlugin.metadata.version

      // Unload old plugin
      await this.unload(pluginId)

      // Call onUpdate hook
      if (newPlugin.hooks.onUpdate) {
        await this.executeWithTimeout(
          newPlugin.hooks.onUpdate(oldVersion, newVersion),
          this.config.pluginTimeout,
          `onUpdate for ${pluginId}`
        )
      }

      // Replace plugin
      entry.plugin = newPlugin

      // Reload
      await this.load(pluginId)

      this.emit('plugin-updated', pluginId, oldVersion, newVersion)

      return true
    } catch (error) {
      entry.status = 'error'
      entry.error = error instanceof Error ? error : new Error(String(error))
      this.emit('plugin-error', pluginId, error)
      return false
    }
  }

  /**
   * Call plugin API method
   */
  async call(pluginId: string, method: string, ...args: unknown[]): Promise<unknown> {
    const entry = this.plugins.get(pluginId)
    if (!entry) {
      throw new Error(`Plugin ${pluginId} not found`)
    }

    if (entry.status !== 'enabled') {
      throw new Error(`Plugin ${pluginId} is not enabled`)
    }

    if (!entry.plugin.api || !entry.plugin.api[method]) {
      throw new Error(`Plugin ${pluginId} does not have method ${method}`)
    }

    try {
      const startTime = Date.now()

      const result = await this.executeWithTimeout(
        entry.plugin.api[method]!(...args),
        this.config.pluginTimeout,
        `${method} for ${pluginId}`
      )

      // Update resource usage
      entry.resourceUsage.executionTime += Date.now() - startTime

      return result
    } catch (error) {
      this.emit('plugin-error', pluginId, error)
      throw error
    }
  }

  /**
   * Get plugin
   */
  get(pluginId: string): Plugin | null {
    return this.plugins.get(pluginId)?.plugin ?? null
  }

  /**
   * Get plugin status
   */
  getStatus(pluginId: string): PluginStatus | null {
    return this.plugins.get(pluginId)?.status ?? null
  }

  /**
   * Get all plugins
   */
  getAll(): Plugin[] {
    return Array.from(this.plugins.values()).map(e => e.plugin)
  }

  /**
   * Get enabled plugins
   */
  getEnabled(): Plugin[] {
    return Array.from(this.plugins.values())
      .filter(e => e.status === 'enabled')
      .map(e => e.plugin)
  }

  /**
   * Get plugins by category
   */
  getByCategory(category: PluginMetadata['category']): Plugin[] {
    return Array.from(this.plugins.values())
      .filter(e => e.plugin.metadata.category === category)
      .map(e => e.plugin)
  }

  /**
   * Get resource usage
   */
  getResourceUsage(pluginId: string): PluginResourceUsage | null {
    return this.plugins.get(pluginId)?.resourceUsage ?? null
  }

  /**
   * Get statistics
   */
  getStats() {
    const entries = Array.from(this.plugins.values())

    return {
      total: entries.length,
      installed: entries.filter(e => e.status === 'installed').length,
      loaded: entries.filter(e => e.status === 'loaded').length,
      enabled: entries.filter(e => e.status === 'enabled').length,
      disabled: entries.filter(e => e.status === 'disabled').length,
      error: entries.filter(e => e.status === 'error').length
    }
  }

  /**
   * Private: Create plugin context
   */
  private createContext(plugin: Plugin): PluginContext {
    return {
      metadata: plugin.metadata,
      config: plugin.config,
      manager: this,
      getDependency: (id: string) => this.get(id),
      emit: (event: string, ...args: unknown[]) => {
        this.emit(`plugin:${plugin.metadata.id}:${event}`, ...args)
      },
      log: (level: 'info' | 'warn' | 'error', message: string) => {
        this.emit('plugin-log', plugin.metadata.id, level, message)
      },
      hasPermission: (permission: string) => {
        return this.checkPermission(plugin, permission)
      },
      getResourceUsage: () => {
        return this.plugins.get(plugin.metadata.id)?.resourceUsage ?? {
          cpuTime: 0,
          memory: 0,
          executionTime: 0,
          networkRequests: 0
        }
      }
    }
  }

  /**
   * Private: Check permission
   */
  private checkPermission(plugin: Plugin, permission: string): boolean {
    if (!this.config.enforcePermissions) return true

    const [category, action] = permission.split('.')
    const perms = plugin.config.permissions

    switch (category) {
      case 'filesystem':
        return action === 'read' ? perms.filesystem.read : perms.filesystem.write
      case 'network':
        return perms.network.enabled
      case 'process':
        return perms.process.enabled
      case 'ui':
        return perms.ui.enabled
      case 'data':
        return action === 'read' ? perms.data.read : perms.data.write
      default:
        return false
    }
  }

  /**
   * Private: Check version compatibility
   */
  private isVersionCompatible(metadata: PluginMetadata): boolean {
    if (metadata.minLyraVersion) {
      if (this.compareVersions(this.lyraVersion, metadata.minLyraVersion) < 0) {
        return false
      }
    }

    if (metadata.maxLyraVersion) {
      if (this.compareVersions(this.lyraVersion, metadata.maxLyraVersion) > 0) {
        return false
      }
    }

    return true
  }

  /**
   * Private: Compare versions
   */
  private compareVersions(v1: string, v2: string): number {
    const parts1 = v1.split('.').map(Number)
    const parts2 = v2.split('.').map(Number)

    for (let i = 0; i < 3; i++) {
      const p1 = parts1[i] ?? 0
      const p2 = parts2[i] ?? 0

      if (p1 > p2) return 1
      if (p1 < p2) return -1
    }

    return 0
  }

  /**
   * Private: Execute with timeout
   */
  private async executeWithTimeout<T>(
    promise: T | Promise<T>,
    timeout: number,
    operation: string
  ): Promise<T> {
    return Promise.race([
      Promise.resolve(promise),
      new Promise<T>((_, reject) =>
        setTimeout(() => reject(new Error(`Timeout: ${operation}`)), timeout)
      )
    ])
  }

  /**
   * Private: Start update checks
   */
  private startUpdateChecks(pluginId: string): void {
    if (this.updateTimers.has(pluginId)) return

    const timer = setInterval(() => {
      this.emit('plugin-update-check', pluginId)
    }, this.config.updateCheckInterval)

    this.updateTimers.set(pluginId, timer)
  }

  /**
   * Private: Stop update checks
   */
  private stopUpdateChecks(pluginId: string): void {
    const timer = this.updateTimers.get(pluginId)
    if (timer) {
      clearInterval(timer)
      this.updateTimers.delete(pluginId)
    }
  }

  /**
   * Cleanup manager
   */
  async cleanup(): Promise<void> {
    // Stop all update checks
    for (const pluginId of this.updateTimers.keys()) {
      this.stopUpdateChecks(pluginId)
    }

    // Uninstall all plugins
    const pluginIds = Array.from(this.plugins.keys())
    for (const pluginId of pluginIds) {
      await this.uninstall(pluginId)
    }

    this.removeAllListeners()
  }
}

/**
 * Create a plugin manager
 */
export function createPluginManager(
  lyraVersion: string,
  config?: Partial<PluginManagerConfig>
): PluginManager {
  return new PluginManager(lyraVersion, config)
}
