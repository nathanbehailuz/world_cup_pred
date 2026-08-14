import teamsJson from '../data/teams.json'
import { flagEmojiFromFifa } from '../lib/fifaFlags'
import type { Team } from '../types'

const teams = teamsJson as Team[]

const byCode = new Map(teams.map((t) => [t.code.toUpperCase(), t]))
const byName = new Map(teams.map((t) => [t.name.toLowerCase(), t]))

/** Resolve FIFA code or full team name to { code, name }. */
export function resolveTeam(codeOrName: string | null | undefined): Team | null {
  if (!codeOrName?.trim()) return null
  const raw = codeOrName.trim()
  const byC = byCode.get(raw.toUpperCase())
  if (byC) return byC
  const byN = byName.get(raw.toLowerCase())
  if (byN) return byN
  if (/^[A-Z]{3}$/i.test(raw)) return { code: raw.toUpperCase(), name: raw }
  return null
}

const SIZE = {
  sm: 'text-[14px] leading-none',
  md: 'text-[20px] leading-none',
  lg: 'text-[28px] leading-none',
} as const

export function TeamFlag({
  code,
  name,
  size = 'md',
  className = '',
  title,
}: {
  code?: string | null
  name?: string | null
  size?: keyof typeof SIZE
  className?: string
  title?: string
}) {
  const team = resolveTeam(code) ?? resolveTeam(name)
  const fifa = (code?.trim() || team?.code || '').toUpperCase() || null
  const emoji = flagEmojiFromFifa(fifa) ?? (team ? flagEmojiFromFifa(team.code) : null)
  const label = title ?? team?.name ?? name ?? fifa ?? 'Team'

  if (!emoji) {
    return (
      <span
        className={`inline-flex items-center justify-center rounded-sm bg-surface-variant px-0.5 text-[9px] font-data-mono text-on-surface-variant shrink-0 ${SIZE[size]} ${className}`}
        title={label}
        aria-hidden
      >
        {fifa?.slice(0, 2) ?? '?'}
      </span>
    )
  }

  return (
    <span
      className={`inline-flex items-center justify-center shrink-0 ${SIZE[size]} ${className}`}
      title={label}
      role="img"
      aria-label={label}
    >
      {emoji}
    </span>
  )
}

/** Flag + team name (optionally FIFA code). */
export function TeamLabel({
  code,
  name,
  size = 'md',
  showCode = false,
  className = '',
  nameClassName = '',
}: {
  code?: string | null
  name?: string | null
  size?: keyof typeof SIZE
  showCode?: boolean
  className?: string
  nameClassName?: string
}) {
  const team = resolveTeam(code) ?? resolveTeam(name)
  const displayName = name ?? team?.name ?? code ?? '—'
  const displayCode = code ?? team?.code

  return (
    <span className={`inline-flex items-center gap-2 min-w-0 ${className}`}>
      <TeamFlag code={displayCode} name={displayName} size={size} />
      <span className={`truncate ${nameClassName}`}>{displayName}</span>
      {showCode && displayCode && (
        <span className="font-data-mono text-slate-gray shrink-0 text-[11px]">{displayCode}</span>
      )}
    </span>
  )
}
