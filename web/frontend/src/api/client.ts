import teamsJson from '../data/teams.json'
import modelMetaJson from '../data/model_meta.json'
import wcFixturesJson from '../data/wc2026_fixtures.json'
import { HOLDOUT_MATCHES } from '../data/holdout'
import type {
  HoldoutFilters,
  HoldoutMatch,
  HoldoutSummary,
  ModelMeta,
  PredictRequest,
  PredictResponse,
  Team,
  VenueMode,
  WcFixture,
} from '../types'

/**
 * Mock API layer. Swap implementations to hit `web/api` later without changing pages.
 * Set VITE_API_BASE to a real backend when ready.
 */
const API_BASE = import.meta.env.VITE_API_BASE as string | undefined
export const USING_MOCK = !API_BASE

const teams = teamsJson as Team[]
const modelMeta = modelMetaJson as ModelMeta
const wcFixtures = wcFixturesJson as WcFixture[]

const DISCLAIMER =
  'Probabilities are research outputs, not betting advice. Knockout labels use advancement (ET/penalties); group draws remain possible.'

function delay(ms = 280): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function findTeam(query: string): Team | undefined {
  const q = query.trim().toLowerCase()
  return teams.find(
    (t) => t.code.toLowerCase() === q || t.name.toLowerCase() === q || t.name.toLowerCase().includes(q),
  )
}

function hashSeed(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return h
}

function mockProbabilities(teamA: Team, teamB: Team, venue: VenueMode) {
  const seed = hashSeed(`${teamA.code}-${teamB.code}-${venue}`)
  const eloA = 1500 + (seed % 700)
  const eloB = 1500 + ((seed >> 3) % 700)
  const venueBoost = venue === 'home_a' ? 80 : venue === 'wc_venue' ? 40 : 0
  const diff = eloA + venueBoost - eloB
  const pA = 1 / (1 + Math.exp(-diff / 180))
  const pDraw = Math.max(0.12, 0.28 - Math.abs(diff) / 1200)
  let a = pA * (1 - pDraw)
  let b = (1 - pA) * (1 - pDraw)
  let d = pDraw
  const sum = a + b + d
  a /= sum
  b /= sum
  d /= sum
  return {
    probabilities: { p_a: a, p_draw: d, p_b: b },
    eloA,
    eloB,
    squadA: 80 + (seed % 900),
    squadB: 60 + ((seed >> 5) % 900),
  }
}

function favoriteFrom(p: { p_a: number; p_draw: number; p_b: number }): {
  favorite: 'A' | 'Draw' | 'B'
  confidence: number
} {
  if (p.p_a >= p.p_draw && p.p_a >= p.p_b) return { favorite: 'A', confidence: p.p_a }
  if (p.p_b >= p.p_draw && p.p_b >= p.p_a) return { favorite: 'B', confidence: p.p_b }
  return { favorite: 'Draw', confidence: p.p_draw }
}

export async function listTeams(search = ''): Promise<Team[]> {
  await delay(80)
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/teams?q=${encodeURIComponent(search)}`)
    return res.json()
  }
  const q = search.trim().toLowerCase()
  if (!q) return teams.slice(0, 40)
  return teams
    .filter((t) => t.name.toLowerCase().includes(q) || t.code.toLowerCase().includes(q))
    .slice(0, 40)
}

export async function getModelMeta(): Promise<ModelMeta> {
  await delay(100)
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/model/meta`)
    return res.json()
  }
  return modelMeta
}

export async function predictMatch(req: PredictRequest): Promise<PredictResponse> {
  await delay(420)
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  }

  const teamA = findTeam(req.team_a)
  const teamB = findTeam(req.team_b)
  if (!teamA) throw new Error(`Unknown team: ${req.team_a}`)
  if (!teamB) throw new Error(`Unknown team: ${req.team_b}`)
  if (teamA.code === teamB.code) throw new Error('Select two different teams')

  const mock = mockProbabilities(teamA, teamB, req.venue)
  const { favorite, confidence } = favoriteFrom(mock.probabilities)

  return {
    team_a: teamA,
    team_b: teamB,
    venue: req.venue,
    as_of: req.as_of,
    feature_cutoff: req.as_of,
    probabilities: mock.probabilities,
    favorite,
    confidence,
    features: [
      { metric: 'Current Elo', team_a: mock.eloA.toFixed(1), team_b: mock.eloB.toFixed(1) },
      { metric: 'Form (L5 pts)', team_a: String(7 + (hashSeed(teamA.code) % 9)), team_b: String(5 + (hashSeed(teamB.code) % 9)) },
      { metric: 'Squad Value', team_a: `€${mock.squadA}M`, team_b: `€${mock.squadB}M` },
      { metric: 'Days since last', team_a: 4 + (hashSeed(teamA.code) % 20), team_b: 3 + (hashSeed(teamB.code) % 18) },
    ],
    top_importance: modelMeta.feature_importance.permutation.slice(0, 5).map((f) => ({
      feature: f.feature,
      value: f.delta_log_loss_mean,
    })),
    disclaimer: DISCLAIMER,
    source: 'mock',
  }
}

function maxProb(m: HoldoutMatch): number {
  return Math.max(m.probabilities.p_a, m.probabilities.p_draw, m.probabilities.p_b)
}

export async function getHoldoutMatches(filters: HoldoutFilters = {}): Promise<{
  matches: HoldoutMatch[]
  summary: HoldoutSummary
}> {
  await delay(160)
  if (API_BASE) {
    const params = new URLSearchParams(filters as Record<string, string>)
    const res = await fetch(`${API_BASE}/evaluate/holdout?${params}`)
    return res.json()
  }

  let matches = [...HOLDOUT_MATCHES]
  if (filters.tournament && filters.tournament !== 'All Tournaments') {
    if (filters.tournament === 'Competitive Only') matches = matches.filter((m) => m.competitive)
    else if (filters.tournament === 'Friendlies') matches = matches.filter((m) => !m.competitive)
    else matches = matches.filter((m) => m.tournament.includes(filters.tournament!.replace(' Cups', '')))
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

  return {
    matches,
    summary: {
      n: matches.length,
      accuracy,
      mean_log_loss,
      vs_baseline_accuracy_delta: 0.021,
      confusion,
    },
  }
}

export async function getWc2026Fixtures(stage?: string): Promise<{
  fixtures: WcFixture[]
  refreshed_at: string
}> {
  await delay(120)
  if (API_BASE) {
    const res = await fetch(`${API_BASE}/wc2026/fixtures${stage ? `?stage=${stage}` : ''}`)
    return res.json()
  }
  const fixtures = stage && stage !== 'all' ? wcFixtures.filter((f) => f.stage === stage) : wcFixtures
  return { fixtures, refreshed_at: '2026-06-17 (mock / backtest artifact)' }
}

export { teams, DISCLAIMER }
