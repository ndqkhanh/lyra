/**
 * Enhanced Plugin System
 *
 * Advanced plugin architecture with lifecycle hooks, sandboxed execution,
 * resource limits, and marketplace support.
 */

export {
  PluginManager,
  createPluginManager,
  type PluginMetadata,
  type PluginPermissions,
  type PluginResourceLimits,
  type PluginConfig,
  type PluginHooks,
  type PluginContext,
  type PluginResourceUsage,
  type Plugin,
  type PluginStatus,
  type PluginManagerConfig
} from './manager'

export {
  PluginBuilder,
  plugin,
  createPlugin,
  DEFAULT_RESOURCE_LIMITS,
  DEFAULT_PERMISSIONS
} from './builder'
