/**
 * Skills Hub — Desktop component for browsing, installing, creating,
 * and evaluating Lyra skills.
 *
 * Integrates with §4.4 Skills System: browse installed + available
 * skills, install from registry with HermesHub-style security scanning,
 * create new skills via SkillNet-style auto-generation, and view
 * quality scores (5-dim rubric).
 */

import React, { useState, useCallback, useEffect } from 'react'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SkillSummary {
  name: string
  displayName: string
  description: string
  version: string
  category: string
  tags: string[]
  quality: SkillQuality | null
  installed: boolean
  source: 'lyra' | 'ecc' | 'community' | 'custom'
}

interface SkillQuality {
  correctness: number   // 0-1
  completeness: number  // 0-1
  clarity: number       // 0-1
  efficiency: number    // 0-1
  safety: number        // 0-1
  overall: number       // 0-1 weighted average
}

interface SecurityScan {
  passed: boolean
  dataExfiltration: boolean
  promptInjection: boolean
  maliciousPayload: boolean
  declaredPermissions: string[]
  scanDate: string
}

interface SkillsHubProps {
  installedSkills: SkillSummary[]
  availableSkills: SkillSummary[]
  onInstall: (skillName: string) => void
  onUninstall: (skillName: string) => void
  onCreate: (prompt: string) => void
  onRefresh: () => void
}

// ---------------------------------------------------------------------------
// Quality badge
// ---------------------------------------------------------------------------

function QualityBadge({ quality }: { quality: SkillQuality | null }) {
  if (!quality) {
    return (
      <span style={{ color: '#64748b', fontSize: '11px' }}>
        Not evaluated
      </span>
    )
  }

  const color =
    quality.overall >= 0.8 ? '#22c55e' :
    quality.overall >= 0.6 ? '#eab308' :
    '#ef4444'

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        color,
        fontSize: '12px',
        fontWeight: 'bold',
        fontFamily: 'monospace',
      }}
      title={`C:${Math.round(quality.correctness * 100)} Cm:${Math.round(quality.completeness * 100)} Cl:${Math.round(quality.clarity * 100)} E:${Math.round(quality.efficiency * 100)} S:${Math.round(quality.safety * 100)}`}
    >
      {Math.round(quality.overall * 100)}%
    </span>
  )
}

// ---------------------------------------------------------------------------
// Security scan indicator
// ---------------------------------------------------------------------------

function SecurityIndicator({ scan }: { scan: SecurityScan | null }) {
  if (!scan) {
    return (
      <span style={{ color: '#eab308', fontSize: '10px' }} title="Not yet scanned">
        ⚠ Unscanned
      </span>
    )
  }

  if (scan.passed) {
    return (
      <span style={{ color: '#22c55e', fontSize: '10px' }} title={`Scanned ${scan.scanDate}. Permissions: ${scan.declaredPermissions.join(', ') || 'none'}`}>
        ✓ Scanned clean
      </span>
    )
  }

  const issues: string[] = []
  if (scan.dataExfiltration) issues.push('data exfiltration')
  if (scan.promptInjection) issues.push('prompt injection')
  if (scan.maliciousPayload) issues.push('malicious payload')

  return (
    <span style={{ color: '#ef4444', fontSize: '10px' }} title={issues.join(', ')}>
      ✗ {issues.length} issue{issues.length > 1 ? 's' : ''}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Skill card
// ---------------------------------------------------------------------------

function SkillCard({
  skill,
  isInstalled,
  onInstall,
  onUninstall,
  securityScan,
}: {
  skill: SkillSummary
  isInstalled: boolean
  onInstall: () => void
  onUninstall: () => void
  securityScan: SecurityScan | null
}) {
  return (
    <div
      style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: 8,
        padding: 12,
        marginBottom: 8,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
        <div>
          <strong style={{ color: '#e2e8f0', fontSize: '14px' }}>
            {skill.displayName}
          </strong>
          <span style={{ color: '#64748b', fontSize: '11px', marginLeft: 8 }}>
            v{skill.version}
          </span>
        </div>
        <QualityBadge quality={skill.quality} />
      </div>

      <p style={{ color: '#94a3b8', fontSize: '12px', margin: '4px 0 8px' }}>
        {skill.description}
      </p>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 8 }}>
        {skill.tags.map((tag) => (
          <span
            key={tag}
            style={{
              backgroundColor: '#0f172a',
              color: '#8b5cf6',
              padding: '1px 8px',
              borderRadius: 12,
              fontSize: '10px',
              fontFamily: 'monospace',
            }}
          >
            {tag}
          </span>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <SecurityIndicator scan={securityScan} />

        {isInstalled ? (
          <button
            onClick={onUninstall}
            style={{
              backgroundColor: 'transparent',
              color: '#ef4444',
              border: '1px solid #ef4444',
              borderRadius: 4,
              padding: '4px 12px',
              cursor: 'pointer',
              fontSize: '11px',
            }}
          >
            Uninstall
          </button>
        ) : (
          <button
            onClick={onInstall}
            style={{
              backgroundColor: '#8b5cf6',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              padding: '4px 12px',
              cursor: 'pointer',
              fontSize: '11px',
              fontWeight: 'bold',
            }}
          >
            Install
          </button>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Create skill panel
// ---------------------------------------------------------------------------

function CreateSkillPanel({ onCreate }: { onCreate: (prompt: string) => void }) {
  const [prompt, setPrompt] = useState('')
  const [mode, setMode] = useState<'prompt' | 'repo' | 'pdf'>('prompt')

  const handleCreate = useCallback(() => {
    if (prompt.trim()) {
      onCreate(
        mode === 'repo'
          ? `Generate a skill from GitHub repo: ${prompt}`
          : mode === 'pdf'
          ? `Generate a skill from PDF: ${prompt}`
          : prompt
      )
      setPrompt('')
    }
  }, [prompt, mode, onCreate])

  return (
    <div
      style={{
        backgroundColor: '#1e293b',
        border: '1px solid #334155',
        borderRadius: 8,
        padding: 16,
        marginBottom: 16,
      }}
    >
      <h3 style={{ color: '#e2e8f0', margin: '0 0 12px', fontSize: '15px' }}>
        ✨ Create New Skill
      </h3>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        {(['prompt', 'repo', 'pdf'] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            style={{
              backgroundColor: mode === m ? '#8b5cf6' : 'transparent',
              color: mode === m ? 'white' : '#64748b',
              border: `1px solid ${mode === m ? '#8b5cf6' : '#334155'}`,
              borderRadius: 4,
              padding: '4px 12px',
              cursor: 'pointer',
              fontSize: '11px',
            }}
          >
            {m === 'prompt' ? 'From Prompt' : m === 'repo' ? 'From Repo' : 'From PDF'}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
          placeholder={
            mode === 'repo'
              ? 'GitHub URL (e.g. https://github.com/user/repo)'
              : mode === 'pdf'
              ? 'Path to PDF or arXiv ID'
              : 'Describe what the skill should do...'
          }
          style={{
            flex: 1,
            backgroundColor: '#0f172a',
            color: '#e2e8f0',
            border: '1px solid #334155',
            borderRadius: 4,
            padding: '8px 12px',
            fontSize: '13px',
            fontFamily: 'monospace',
          }}
        />
        <button
          onClick={handleCreate}
          disabled={!prompt.trim()}
          style={{
            backgroundColor: prompt.trim() ? '#22c55e' : '#334155',
            color: 'white',
            border: 'none',
            borderRadius: 4,
            padding: '8px 20px',
            cursor: prompt.trim() ? 'pointer' : 'default',
            fontWeight: 'bold',
            fontSize: '12px',
          }}
        >
          Generate
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main SkillsHub component
// ---------------------------------------------------------------------------

export function SkillsHub({
  installedSkills,
  availableSkills,
  onInstall,
  onUninstall,
  onCreate,
  onRefresh,
}: SkillsHubProps) {
  const [tab, setTab] = useState<'installed' | 'available' | 'create'>('installed')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredInstalled = installedSkills.filter(
    (s) =>
      !searchQuery ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const filteredAvailable = availableSkills.filter(
    (s) =>
      !searchQuery ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  return (
    <div style={{ padding: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ color: '#e2e8f0', margin: 0, fontSize: '18px' }}>
          🧩 Skills Hub
        </h2>
        <button
          onClick={onRefresh}
          style={{
            backgroundColor: 'transparent',
            color: '#64748b',
            border: '1px solid #334155',
            borderRadius: 4,
            padding: '4px 12px',
            cursor: 'pointer',
            fontSize: '11px',
          }}
        >
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
        {(['installed', 'available', 'create'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              backgroundColor: tab === t ? '#8b5cf6' : '#1e293b',
              color: tab === t ? 'white' : '#94a3b8',
              border: 'none',
              borderRadius: 4,
              padding: '8px 20px',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: tab === t ? 'bold' : 'normal',
            }}
          >
            {t === 'installed'
              ? `Installed (${installedSkills.length})`
              : t === 'available'
              ? `Available (${availableSkills.length})`
              : 'Create'}
          </button>
        ))}

        {/* Search */}
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search skills..."
          style={{
            flex: 1,
            backgroundColor: '#0f172a',
            color: '#e2e8f0',
            border: '1px solid #334155',
            borderRadius: 4,
            padding: '8px 12px',
            fontSize: '13px',
            fontFamily: 'monospace',
            marginLeft: 12,
          }}
        />
      </div>

      {/* Content */}
      {tab === 'installed' && (
        <div>
          {filteredInstalled.length === 0 ? (
            <p style={{ color: '#64748b', textAlign: 'center', padding: 32 }}>
              {searchQuery ? 'No matching skills found.' : 'No skills installed yet. Browse available skills or create one!'}
            </p>
          ) : (
            filteredInstalled.map((skill) => (
              <SkillCard
                key={skill.name}
                skill={skill}
                isInstalled={true}
                onInstall={() => onInstall(skill.name)}
                onUninstall={() => onUninstall(skill.name)}
                securityScan={null}
              />
            ))
          )}
        </div>
      )}

      {tab === 'available' && (
        <div>
          {filteredAvailable.length === 0 ? (
            <p style={{ color: '#64748b', textAlign: 'center', padding: 32 }}>
              {searchQuery ? 'No matching skills found.' : 'No available skills. Check your registry connection.'}
            </p>
          ) : (
            filteredAvailable.map((skill) => (
              <SkillCard
                key={skill.name}
                skill={skill}
                isInstalled={false}
                onInstall={() => onInstall(skill.name)}
                onUninstall={() => onUninstall(skill.name)}
                securityScan={null}
              />
            ))
          )}
        </div>
      )}

      {tab === 'create' && <CreateSkillPanel onCreate={onCreate} />}

      {/* Stats footer */}
      <div
        style={{
          marginTop: 24,
          padding: '12px 16px',
          backgroundColor: '#0f172a',
          borderRadius: 8,
          display: 'flex',
          justifyContent: 'space-around',
          fontSize: '12px',
          color: '#64748b',
        }}
      >
        <span>{installedSkills.length} installed</span>
        <span>
          {installedSkills.filter((s) => s.quality && s.quality.overall >= 0.8).length}{' '}
          high-quality (80%+)
        </span>
        <span>{availableSkills.length} available</span>
        <span>
          {installedSkills.filter((s) => s.source === 'lyra').length} Lyra ·{' '}
          {installedSkills.filter((s) => s.source === 'ecc').length} ECC ·{' '}
          {installedSkills.filter((s) => s.source === 'community').length} Community
        </span>
      </div>
    </div>
  )
}

export type { SkillSummary, SkillQuality, SecurityScan, SkillsHubProps }
