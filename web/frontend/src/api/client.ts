import teamsJson from '../data/teams.json'
import modelMetaJson from '../data/model_meta.json'
import wcFixturesJson from '../data/wc2026_fixtures.json'
import { HOLDOUT_ARTIFACT, HOLDOUT_MATCHES } from '../data/holdout'
import type {
  HoldoutFilters,
  HoldoutMatch,
  HoldoutSummary,
  ModelMeta,
  PredictRequest,
  SimMatch,
  SimSummary,
  Team,
  WcFixture,
  WcScheduleFixture,
} from '../types'

/**
 * API base: VITE_API_BASE, or `/api` (Vite proxy → uvicorn) in dev.
 * Predict / WC simulate require a live backend — no mock fallback.
 */
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api'
export const USING_MOCK = false

const teams = teamsJson as Team[]
const modelMeta = modelMetaJson as ModelMeta
const wcFixtures = wcFixturesJson as WcFixture[]

const DISCLAIMER =
  'Probabilities are research outputs, not betting advice. Knockout labels use advancement (ET/penalties); group draws remain possible.'

function delay(ms = 280): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function apiError(res: Response): Promise<never> {
  let detail = res.statusText
  try {
    const body = await res.json()
    detail = body.detail ?? JSON.stringify(body)
  } catch {
    try {
      detail = await res.text()
    } catch {
      /* ignore */
    }
  }
  throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
}

export async function listTeams(search = ''): Promise<Team[]> {
  await delay(80)
  const q = search.trim().toLowerCase()
  if (!q) return teams.slice(0, 40)
  return teams
    .filter((t) => t.name.toLowerCase().includes(q) || t.code.toLowerCase().includes(q))
    .slice(0, 40)
}

export async function getModelMeta(): Promise<ModelMeta> {
  await delay(100)
  return modelMeta
}

export async function checkApiHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2500) })
    return res.ok
  } catch {
    return false
  }
}

/** Live model prediction for a WC 2026 scheduled pairing (venue inferred). */
export async function predictMatch(req: PredictRequest): Promise<SimMatch> {
  const res = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ team_a: req.team_a, team_b: req.team_b }),
  })
  if (!res.ok) await apiError(res)
  return res.json()
}

/** Run production model on every resolved WC 2026 fixture. */
export async function simulateAllWc2026(): Promise<{ matches: SimMatch[]; summary: SimSummary }> {
  const res = await fetch(`${API_BASE}/wc2026/simulate`, { method: 'POST' })
  if (!res.ok) await apiError(res)
  return res.json()
}

export async function listWcSchedule(): Promise<WcScheduleFixture[]> {
  const res = await fetch(`${API_BASE}/wc2026/fixtures`)
  if (!res.ok) await apiError(res)
  const data = await res.json()
  return data.fixtures as WcScheduleFixture[]
}

function maxProb(m: HoldoutMatch): number {
  return Math.max(m.probabilities.p_a, m.probabilities.p_draw, m.probabilities.p_b)
}

export function getHoldoutTournaments(): string[] {
  return ['All Tournaments', ...HOLDOUT_ARTIFACT.meta.tournaments]
}

export async function getHoldoutMatches(filters: HoldoutFilters = {}): Promise<{
  matches: HoldoutMatch[]
  summary: HoldoutSummary
  total: number
}> {
  await delay(160)

  let matches = [...HOLDOUT_MATCHES]
  if (filters.tournament && filters.tournament !== 'All Tournaments') {
    matches = matches.filter((m) => m.tournament === filters.tournament)
  }
  if (filters.confidence === 'high') matches = matches.filter((m) => maxProb(m) > 0.7)
  if (filters.confidence === 'medium') matches = matches.filter((m) => maxProb(m) >= 0.5 && maxProb(m) <= 0.7)
  if (filters.confidence === 'low') matches = matches.filter((m) => maxProb(m) < 0.5)
  if (filters.correctness === 'correct') matches = matches.filter((m) => m.correct)
  if (filters.correctness === 'incorrect') matches = matches.filter((m) => !m.correct)
  if (filters.search) {
    const q = filters.search.toLowerCase()
    matches = matches.filter(
      (m) =>
        m.team_a.toLowerCase().includes(q) ||
        m.team_b.toLowerCase().includes(q) ||
        m.tournament.toLowerCase().includes(q),
    )
  }

  const n = matches.length || 1
  const accuracy = matches.filter((m) => m.correct).length / n
  const mean_log_loss = matches.reduce((s, m) => s + m.log_loss, 0) / n
  const labels: Array<'home_win' | 'draw' | 'away_win'> = ['home_win', 'draw', 'away_win']
  const confusion = labels.map((pred) =>
    labels.map((act) => matches.filter((m) => m.predicted === pred && m.actual === act).length),
  )
  const baseline = HOLDOUT_ARTIFACT.meta.baseline_accuracy

  return {
    matches,
    total: HOLDOUT_ARTIFACT.meta.n_matches,
    summary: {
      n: matches.length,
      accuracy,
      mean_log_loss,
      vs_baseline_accuracy_delta: accuracy - baseline,
      confusion,
    },
  }
}

export async function getWc2026Fixtures(stage?: string): Promise<{
  fixtures: WcFixture[]
  refreshed_at: string
}> {
  await delay(120)
  const fixtures = stage && stage !== 'all' ? wcFixtures.filter((f) => f.stage === stage) : wcFixtures
  return { fixtures, refreshed_at: '2026-06-17 (mock / backtest artifact)' }
}

export { teams, DISCLAIMER, API_BASE }
