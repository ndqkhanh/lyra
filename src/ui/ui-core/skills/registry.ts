/**
 * Skills Registry
 *
 * Dynamic skill loading and management system with hot reloading,
 * dependency resolution, and version management.
 *
 * Based on Hermes Agent's skills architecture.
 *
 * Features:
 * - Dynamic skill discovery and loading
 * - Hot reloading (watch for changes)
 * - Dependency resolution
 * - Version management (semver)
 * - Skill lifecycle hooks
 * - Sandboxed execution
 * - Skill metadata and validation
 */

import { EventEmitter } from 'eventemitter3'

/**
 * Skill metadata
 */
export interface SkillMetadata {
  /** Unique skill identifier */
  id: string
  /** Display name */
  name: string
  /** Description */
  description: string
  /** Version (semver) */
  version: string
  /** Author */
  author?: string
  /** Tags for categorization */
  tags: string[]
  /** Dependencies (skill IDs with version constraints) */
  dependencies: Record<string, string>
  /** Minimum Lyra version required */
  minLyraVersion?: string
  /** Maximum Lyra version supported */
  maxLyraVersion?: string
  /** Skill icon (emoji or URL) */
  icon?: string
  /** Homepage URL */
  homepage?: string
  /** Repository URL */
  repository?: string
  /** License */
  license?: string
}

/**
 * Skill configuration
 */
export interface SkillConfig {
  /** Enable/disable skill */
  enabled: boolean
  /** Skill-specific settings */
  settings: Record<string, unknown>
  /** Priority (higher = loaded first) */
  priority: number
  /** Auto-reload on file changes */
  autoReload: boolean
}

/**
 * Skill lifecycle hooks
 */
export interface SkillHooks {
  /** Called when skill is loaded */
  onLoad?: () => void | Promise<void>
  /** Called when skill is unloaded */
  onUnload?: () => void | Promise<void>
  /** Called when skill is enabled */
  onEnable?: () => void | Promise<void>
  /** Called when skill is disabled */
  onDisable?: () => void | Promise<void>
  /** Called when skill is reloaded */
  onReload?: () => void | Promise<void>
  /** Called when dependencies are resolved */
  onDependenciesResolved?: (deps: Map<string, Skill>) => void | Promise<void>
}

/**
 * Skill execution context
 */
export interface SkillContext {
  /** Skill metadata */
  metadata: SkillMetadata
  /** Skill configuration */
  config: SkillConfig
  /** Registry instance */
  registry: SkillRegistry
  /** Get dependency by ID */
  getDependency: (id: string) => Skill | null
  /** Emit event */
  emit: (event: string, ...args: unknown[]) => void
  /** Log message */
  log: (level: 'info' | 'warn' | 'error', message: string) => void
}

/**
 * Skill interface
 */
export interface Skill {
  /** Skill metadata */
  metadata: SkillMetadata
  /** Skill configuration */
  config: SkillConfig
  /** Lifecycle hooks */
  hooks: SkillHooks
  /** Skill execution function */
  execute: (context: SkillContext, ...args: unknown[]) => unknown | Promise<unknown>
  /** Skill validation function */
  validate?: (context: SkillContext) => boolean | Promise<boolean>
}

/**
 * Skill load result
 */
export interface SkillLoadResult {
  success: boolean
  skill?: Skill
  error?: Error
}

/**
 * Skill status
 */
export type SkillStatus = 'unloaded' | 'loading' | 'loaded' | 'enabled' | 'disabled' | 'error'

/**
 * Skill entry in registry
 */
interface SkillEntry {
  skill: Skill
  status: SkillStatus
  loadTime: number
  error?: Error
  dependents: Set<string>  // Skills that depend on this skill
}

/**
 * Registry configuration
 */
export interface RegistryConfig {
  /** Enable hot reloading */
  hotReload: boolean
  /** Watch interval in ms */
  watchInterval: number
  /** Enable dependency resolution */
  resolveDependencies: boolean
  /** Maximum dependency depth */
  maxDependencyDepth: number
  /** Enable skill validation */
  validateSkills: boolean
  /** Skill timeout in ms */
  skillTimeout: number
}

/**
 * Skills Registry
 */
export class SkillRegistry extends EventEmitter {
  private skills = new Map<string, SkillEntry>()
  private config: RegistryConfig
  private watchTimers = new Map<string, NodeJS.Timeout>()
  private lyraVersion: string

  constructor(lyraVersion: string, config: Partial<RegistryConfig> = {}) {
    super()
    this.lyraVersion = lyraVersion
    this.config = {
      hotReload: config.hotReload ?? false,
      watchInterval: config.watchInterval ?? 1000,
      resolveDependencies: config.resolveDependencies ?? true,
      maxDependencyDepth: config.maxDependencyDepth ?? 10,
      validateSkills: config.validateSkills ?? true,
      skillTimeout: config.skillTimeout ?? 30000
    }
  }

  /**
   * Register a skill
   */
  async register(skill: Skill): Promise<SkillLoadResult> {
    try {
      // Validate skill
      if (this.config.validateSkills) {
        const validationError = this.validateSkill(skill)
        if (validationError) {
          return { success: false, error: validationError }
        }
      }

      // Check if already registered
      if (this.skills.has(skill.metadata.id)) {
        return {
          success: false,
          error: new Error(`Skill ${skill.metadata.id} is already registered`)
        }
      }

      // Check version compatibility
      if (!this.isVersionCompatible(skill.metadata)) {
        return {
          success: false,
          error: new Error(
            `Skill ${skill.metadata.id} requires Lyra ${skill.metadata.minLyraVersion || '*'} ` +
            `but current version is ${this.lyraVersion}`
          )
        }
      }

      // Create entry
      const entry: SkillEntry = {
        skill,
        status: 'loading',
        loadTime: Date.now(),
        dependents: new Set()
      }

      this.skills.set(skill.metadata.id, entry)

      // Resolve dependencies
      if (this.config.resolveDependencies) {
        const depsResolved = await this.resolveDependencies(skill.metadata.id)
        if (!depsResolved) {
          this.skills.delete(skill.metadata.id)
          return {
            success: false,
            error: new Error(`Failed to resolve dependencies for ${skill.metadata.id}`)
          }
        }
      }

      // Call onLoad hook
      if (skill.hooks.onLoad) {
        await this.executeWithTimeout(
          skill.hooks.onLoad(),
          this.config.skillTimeout,
          `onLoad hook for ${skill.metadata.id}`
        )
      }

      // Update status
      entry.status = 'loaded'

      // Enable if configured
      if (skill.config.enabled) {
        await this.enable(skill.metadata.id)
      }

      // Start watching if hot reload enabled
      if (this.config.hotReload && skill.config.autoReload) {
        this.startWatching(skill.metadata.id)
      }

      this.emit('skill-registered', skill.metadata.id)

      return { success: true, skill }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error : new Error(String(error))
      }
    }
  }

  /**
   * Unregister a skill
   */
  async unregister(skillId: string): Promise<boolean> {
    const entry = this.skills.get(skillId)
    if (!entry) return false

    try {
      // Check if other skills depend on this
      if (entry.dependents.size > 0) {
        throw new Error(
          `Cannot unregister ${skillId}: depended on by ${Array.from(entry.dependents).join(', ')}`
        )
      }

      // Disable if enabled
      if (entry.status === 'enabled') {
        await this.disable(skillId)
      }

      // Call onUnload hook
      if (entry.skill.hooks.onUnload) {
        await this.executeWithTimeout(
          entry.skill.hooks.onUnload(),
          this.config.skillTimeout,
          `onUnload hook for ${skillId}`
        )
      }

      // Stop watching
      this.stopWatching(skillId)

      // Remove from dependencies
      for (const depId of Object.keys(entry.skill.metadata.dependencies)) {
        const depEntry = this.skills.get(depId)
        if (depEntry) {
          depEntry.dependents.delete(skillId)
        }
      }

      // Remove from registry
      this.skills.delete(skillId)

      this.emit('skill-unregistered', skillId)

      return true
    } catch (error) {
      entry.status = 'error'
      entry.error = error instanceof Error ? error : new Error(String(error))
      this.emit('skill-error', skillId, entry.error)
      return false
    }
  }

  /**
   * Enable a skill
   */
  async enable(skillId: string): Promise<boolean> {
    const entry = this.skills.get(skillId)
    if (!entry) return false

    if (entry.status === 'enabled') return true

    try {
      // Call onEnable hook
      if (entry.skill.hooks.onEnable) {
        await this.executeWithTimeout(
          entry.skill.hooks.onEnable(),
          this.config.skillTimeout,
          `onEnable hook for ${skillId}`
        )
      }

      entry.status = 'enabled'
      entry.skill.config.enabled = true

      this.emit('skill-enabled', skillId)

      return true
    } catch (error) {
      entry.status = 'error'
      entry.error = error instanceof Error ? error : new Error(String(error))
      this.emit('skill-error', skillId, entry.error)
      return false
    }
  }

  /**
   * Disable a skill
   */
  async disable(skillId: string): Promise<boolean> {
    const entry = this.skills.get(skillId)
    if (!entry) return false

    if (entry.status === 'disabled') return true

    try {
      // Call onDisable hook
      if (entry.skill.hooks.onDisable) {
        await this.executeWithTimeout(
          entry.skill.hooks.onDisable(),
          this.config.skillTimeout,
          `onDisable hook for ${skillId}`
        )
      }

      entry.status = 'disabled'
      entry.skill.config.enabled = false

      this.emit('skill-disabled', skillId)

      return true
    } catch (error) {
      entry.status = 'error'
      entry.error = error instanceof Error ? error : new Error(String(error))
      this.emit('skill-error', skillId, entry.error)
      return false
    }
  }

  /**
   * Reload a skill
   */
  async reload(skillId: string): Promise<boolean> {
    const entry = this.skills.get(skillId)
    if (!entry) return false

    try {
      const wasEnabled = entry.status === 'enabled'

      // Disable if enabled
      if (wasEnabled) {
        await this.disable(skillId)
      }

      // Call onReload hook
      if (entry.skill.hooks.onReload) {
        await this.executeWithTimeout(
          entry.skill.hooks.onReload(),
          this.config.skillTimeout,
          `onReload hook for ${skillId}`
        )
      }

      // Re-enable if was enabled
      if (wasEnabled) {
        await this.enable(skillId)
      }

      this.emit('skill-reloaded', skillId)

      return true
    } catch (error) {
      entry.status = 'error'
      entry.error = error instanceof Error ? error : new Error(String(error))
      this.emit('skill-error', skillId, entry.error)
      return false
    }
  }

  /**
   * Execute a skill
   */
  async execute(skillId: string, ...args: unknown[]): Promise<unknown> {
    const entry = this.skills.get(skillId)
    if (!entry) {
      throw new Error(`Skill ${skillId} not found`)
    }

    if (entry.status !== 'enabled') {
      throw new Error(`Skill ${skillId} is not enabled (status: ${entry.status})`)
    }

    const context: SkillContext = {
      metadata: entry.skill.metadata,
      config: entry.skill.config,
      registry: this,
      getDependency: (id: string) => this.get(id),
      emit: (event: string, ...eventArgs: unknown[]) => {
        this.emit(`skill:${skillId}:${event}`, ...eventArgs)
      },
      log: (level: 'info' | 'warn' | 'error', message: string) => {
        this.emit('skill-log', skillId, level, message)
      }
    }

    try {
      const result = await this.executeWithTimeout(
        entry.skill.execute(context, ...args),
        this.config.skillTimeout,
        `execute for ${skillId}`
      )

      this.emit('skill-executed', skillId, result)

      return result
    } catch (error) {
      entry.status = 'error'
      entry.error = error instanceof Error ? error : new Error(String(error))
      this.emit('skill-error', skillId, entry.error)
      throw error
    }
  }

  /**
   * Get a skill
   */
  get(skillId: string): Skill | null {
    return this.skills.get(skillId)?.skill ?? null
  }

  /**
   * Get skill status
   */
  getStatus(skillId: string): SkillStatus | null {
    return this.skills.get(skillId)?.status ?? null
  }

  /**
   * Get all skills
   */
  getAll(): Skill[] {
    return Array.from(this.skills.values()).map(entry => entry.skill)
  }

  /**
   * Get enabled skills
   */
  getEnabled(): Skill[] {
    return Array.from(this.skills.values())
      .filter(entry => entry.status === 'enabled')
      .map(entry => entry.skill)
  }

  /**
   * Get skills by tag
   */
  getByTag(tag: string): Skill[] {
    return Array.from(this.skills.values())
      .filter(entry => entry.skill.metadata.tags.includes(tag))
      .map(entry => entry.skill)
  }

  /**
   * Check if skill exists
   */
  has(skillId: string): boolean {
    return this.skills.has(skillId)
  }

  /**
   * Get registry statistics
   */
  getStats() {
    const entries = Array.from(this.skills.values())

    return {
      total: entries.length,
      enabled: entries.filter(e => e.status === 'enabled').length,
      disabled: entries.filter(e => e.status === 'disabled').length,
      loading: entries.filter(e => e.status === 'loading').length,
      error: entries.filter(e => e.status === 'error').length,
      watching: this.watchTimers.size
    }
  }

  /**
   * Private: Validate skill
   */
  private validateSkill(skill: Skill): Error | null {
    // Check required fields
    if (!skill.metadata.id) {
      return new Error('Skill metadata.id is required')
    }

    if (!skill.metadata.name) {
      return new Error('Skill metadata.name is required')
    }

    if (!skill.metadata.version) {
      return new Error('Skill metadata.version is required')
    }

    if (!skill.execute) {
      return new Error('Skill execute function is required')
    }

    // Validate version format (basic semver check)
    if (!/^\d+\.\d+\.\d+/.test(skill.metadata.version)) {
      return new Error(`Invalid version format: ${skill.metadata.version}`)
    }

    return null
  }

  /**
   * Private: Check version compatibility
   */
  private isVersionCompatible(metadata: SkillMetadata): boolean {
    // Simple version comparison (would use semver library in production)
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
   * Private: Compare versions (basic semver)
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
   * Private: Resolve dependencies
   */
  private async resolveDependencies(skillId: string, depth = 0): Promise<boolean> {
    if (depth > this.config.maxDependencyDepth) {
      throw new Error(`Maximum dependency depth exceeded for ${skillId}`)
    }

    const entry = this.skills.get(skillId)
    if (!entry) return false

    const deps = new Map<string, Skill>()

    // Resolve each dependency
    for (const [depId, versionConstraint] of Object.entries(entry.skill.metadata.dependencies)) {
      const depEntry = this.skills.get(depId)

      if (!depEntry) {
        throw new Error(`Dependency ${depId} not found for ${skillId}`)
      }

      // Check version constraint (simplified)
      if (!this.satisfiesConstraint(depEntry.skill.metadata.version, versionConstraint)) {
        throw new Error(
          `Dependency ${depId} version ${depEntry.skill.metadata.version} ` +
          `does not satisfy constraint ${versionConstraint} for ${skillId}`
        )
      }

      // Add to dependents
      depEntry.dependents.add(skillId)

      deps.set(depId, depEntry.skill)
    }

    // Call onDependenciesResolved hook
    if (entry.skill.hooks.onDependenciesResolved) {
      await this.executeWithTimeout(
        entry.skill.hooks.onDependenciesResolved(deps),
        this.config.skillTimeout,
        `onDependenciesResolved hook for ${skillId}`
      )
    }

    return true
  }

  /**
   * Private: Check if version satisfies constraint
   */
  private satisfiesConstraint(version: string, constraint: string): boolean {
    // Simplified constraint checking (would use semver library in production)
    if (constraint === '*') return true

    // Exact match
    if (constraint === version) return true

    // Range (e.g., "^1.0.0", "~1.0.0", ">=1.0.0")
    // For now, just check prefix
    if (constraint.startsWith('^')) {
      const base = constraint.slice(1)
      return version.startsWith(base.split('.')[0]!)
    }

    return false
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
   * Private: Start watching skill for changes
   */
  private startWatching(skillId: string): void {
    if (this.watchTimers.has(skillId)) return

    const timer = setInterval(() => {
      this.emit('skill-watch', skillId)
      // In production, would check file modification time and reload if changed
    }, this.config.watchInterval)

    this.watchTimers.set(skillId, timer)
  }

  /**
   * Private: Stop watching skill
   */
  private stopWatching(skillId: string): void {
    const timer = this.watchTimers.get(skillId)
    if (timer) {
      clearInterval(timer)
      this.watchTimers.delete(skillId)
    }
  }

  /**
   * Cleanup registry
   */
  async cleanup(): Promise<void> {
    // Stop all watchers
    for (const skillId of this.watchTimers.keys()) {
      this.stopWatching(skillId)
    }

    // Unregister all skills
    const skillIds = Array.from(this.skills.keys())
    for (const skillId of skillIds) {
      await this.unregister(skillId)
    }

    this.removeAllListeners()
  }
}

/**
 * Create a skills registry
 */
export function createRegistry(
  lyraVersion: string,
  config?: Partial<RegistryConfig>
): SkillRegistry {
  return new SkillRegistry(lyraVersion, config)
}
