import { useEffect, useRef, useState } from 'react'
import {
  API_BASE,
  checkApiHealth,
  predictMatch,
  simulateAllWc2026,
} from '../api/client'
import { TeamPicker } from '../components/TeamPicker'
import { ProbabilityBar } from '../components/ProbabilityBar'
import { ConfusionMatrix, runningConfusion } from '../components/ConfusionMatrix'
import { LabelCallout } from '../components/LabelCallout'
import { Icon } from '../components/Icon'
import { TeamFlag, TeamLabel } from '../components/TeamFlag'
import { pct } from '../lib/format'
import type { SimMatch, SimSummary } from '../types'

type Mode = 'single' | 'batch'

const REVEAL_MS = 90

function favoriteOf(m: SimMatch): { name: string; confidence: number } {
  const { p_a, p_draw, p_b } = m.probabilities
  if (p_a >= p_draw && p_a >= p_b) return { name: m.team_a, confidence: p_a }
  if (p_b >= p_draw && p_b >= p_a) return { name: m.team_b, confidence: p_b }
  return { name: 'Draw', confidence: p_draw }
}

function summaryFromVisible(rows: SimMatch[]): SimSummary {
  const played = rows.filter((m) => m.status === 'final' && m.log_loss != null)
  const n_played = played.length
  return {
    n: rows.length,
    n_played,
    accuracy: n_played ? played.filter((m) => m.correct).length / n_played : 0,
    mean_log_loss: n_played
      ? played.reduce((s, m) => s + (m.log_loss ?? 0), 0) / n_played
      : 0,
    confusion: runningConfusion(rows),
  }
}

function MatchResultCanvas({ match }: { match: SimMatch }) {
  const fav = favoriteOf(match)
  return (
    <section className="flex flex-col gap-6 animate-fade-up">
      <div className="flex justify-between items-end flex-wrap gap-2">
        <h2 className="text-headline-md text-primary flex items-center gap-2">
          <Icon name="bar_chart" className="text-pitch-green" filled />
          Match result
        </h2>
        <span className="font-label-caps text-slate-gray bg-surface-container px-2 py-1 rounded border border-outline-variant">
          {match.date} · {match.venue_label ?? 'Venue inferred'}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        <div className="md:col-span-8 flex flex-col gap-6">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-8 text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-grid-pattern opacity-40 pointer-events-none" />
            <div className="relative font-label-caps text-on-surface-variant mb-4">
              {match.tournament}
              {match.group_name ? ` · ${match.group_name}` : ''}
            </div>
            <div className="relative flex justify-center items-center gap-6 md:gap-10">
              <div className="flex flex-col items-center gap-2 min-w-[5rem]">
                <TeamFlag code={match.team_a_code} name={match.team_a} size="lg" />
                <span className="text-headline-lg text-primary tracking-tight">{match.team_a_code}</span>
                <span className="text-body-sm text-on-surface-variant">{match.team_a}</span>
              </div>
              <div className="flex flex-col items-center gap-1">
                <span className="text-headline-md text-outline font-data-mono">
                  {match.score ?? 'vs'}
                </span>
                {match.status === 'final' ? (
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-caps text-[11px] ${
                      match.correct
                        ? 'bg-secondary-container text-on-secondary-container'
                        : 'bg-error-container text-on-error-container'
                    }`}
                  >
                    <Icon name={match.correct ? 'check' : 'close'} className="text-[14px]" />
                    {match.correct ? 'Correct' : 'Incorrect'}
                  </span>
                ) : (
                  <span className="font-label-caps text-outline text-[11px]">Upcoming</span>
                )}
              </div>
              <div className="flex flex-col items-center gap-2 min-w-[5rem]">
                <TeamFlag code={match.team_b_code} name={match.team_b} size="lg" />
                <span className="text-headline-lg text-pitch-green tracking-tight">{match.team_b_code}</span>
                <span className="text-body-sm text-on-surface-variant">{match.team_b}</span>
              </div>
            </div>
            <div className="relative mt-6 text-body-sm text-on-surface-variant flex items-center justify-center gap-2 flex-wrap">
              Favorite{' '}
              {fav.name === 'Draw' ? (
                <span className="text-primary font-semibold">{fav.name}</span>
              ) : (
                <TeamLabel
                  name={fav.name}
                  size="sm"
                  nameClassName="text-primary font-semibold"
                />
              )}{' '}
              <span className="font-data-mono text-pitch-green">{pct(fav.confidence)}</span>
            </div>
          </div>

          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col gap-4">
            <div className="flex justify-between items-center font-label-caps text-primary gap-2">
              <TeamLabel name={match.team_a} code={match.team_a_code} size="sm" nameClassName="font-label-caps" />
              <span className="text-slate-gray shrink-0">Draw</span>
              <TeamLabel
                name={match.team_b}
                code={match.team_b_code}
                size="sm"
                className="justify-end"
                nameClassName="font-label-caps"
              />
            </div>
            <ProbabilityBar
              probabilities={match.probabilities}
              labelA={match.team_a}
              labelB={match.team_b}
              tall
              showLabels={false}
            />
          </div>

          {match.narrative && (
            <p className="text-body-md text-on-surface-variant border-l-2 border-pitch-green pl-4">
              {match.narrative}
            </p>
          )}
          <LabelCallout />
        </div>

        <div className="md:col-span-4 flex flex-col gap-4">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5 grid grid-cols-2 gap-3">
            <div>
              <div className="font-label-caps text-outline mb-1">Log loss</div>
              <div
                className={`text-headline-sm font-data-mono ${
                  match.log_loss != null && match.log_loss > 1.2
                    ? 'text-data-neg'
                    : 'text-primary'
                }`}
              >
                {match.log_loss != null ? match.log_loss.toFixed(3) : '—'}
              </div>
            </div>
            <div>
              <div className="font-label-caps text-outline mb-1">Elo gap</div>
              <div className="text-headline-sm font-data-mono text-primary">
                {match.elo_gap.toFixed(0)}
              </div>
            </div>
            <div className="col-span-2">
              <div className="font-label-caps text-outline mb-1">Actual</div>
              <div className="text-body-md text-primary">
                {match.actual_label ?? 'Not played yet'}
                {match.score ? ` (${match.score})` : ''}
              </div>
            </div>
            <div className="col-span-2">
              <div className="font-label-caps text-outline mb-1">Predicted</div>
              <div className="text-body-md text-primary capitalize">
                {match.predicted.replace('_', ' ')}
              </div>
            </div>
          </div>

          {match.features && match.features.length > 0 && (
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
              <div className="p-3 border-b border-outline-variant bg-surface-container-low">
                <h3 className="font-label-caps text-primary">Feature snapshot</h3>
              </div>
              <table className="w-full text-left text-body-sm">
                <thead>
                  <tr className="border-b border-outline-variant font-label-caps text-slate-gray">
                    <th className="py-2 px-3 font-normal">Metric</th>
                    <th className="py-2 px-3 text-right font-normal">
                      <span className="inline-flex items-center justify-end gap-1.5">
                        <TeamFlag code={match.team_a_code} name={match.team_a} size="sm" />
                        {match.team_a_code}
                      </span>
                    </th>
                    <th className="py-2 px-3 text-right font-normal">
                      <span className="inline-flex items-center justify-end gap-1.5">
                        <TeamFlag code={match.team_b_code} name={match.team_b} size="sm" />
                        {match.team_b_code}
                      </span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {match.features.map((row) => (
                    <tr key={row.metric} className="border-b border-surface-variant">
                      <td className="py-2 px-3 text-slate-gray">{row.metric}</td>
                      <td className="py-2 px-3 text-right font-data-mono">
                        {row.team_a ?? '—'}
                      </td>
                      <td className="py-2 px-3 text-right font-data-mono">
                        {row.team_b ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
      {match.disclaimer && (
        <p className="text-body-sm text-on-surface-variant">{match.disclaimer}</p>
      )}
    </section>
  )
}

export function PredictPage() {
  const [mode, setMode] = useState<Mode>('single')
  const [apiOk, setApiOk] = useState<boolean | null>(null)
  const [teamA, setTeamA] = useState('Mexico')
  const [teamB, setTeamB] = useState('South Africa')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [single, setSingle] = useState<SimMatch | null>(null)

  const [batchAll, setBatchAll] = useState<SimMatch[]>([])
  const [visibleCount, setVisibleCount] = useState(0)
  const [batchRunning, setBatchRunning] = useState(false)
  const revealTimer = useRef<number | null>(null)

  useEffect(() => {
    void checkApiHealth().then(setApiOk)
    return () => {
      if (revealTimer.current) window.clearInterval(revealTimer.current)
    }
  }, [])

  const visibleRows = batchAll.slice(0, visibleCount)
  const liveSummary = summaryFromVisible(visibleRows)

  async function runSingle() {
    setLoading(true)
    setError(null)
    try {
      const res = await predictMatch({ team_a: teamA, team_b: teamB })
      setSingle(res)
    } catch (e) {
      setSingle(null)
      setError(e instanceof Error ? e.message : 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  async function runBatch() {
    setBatchRunning(true)
    setError(null)
    setBatchAll([])
    setVisibleCount(0)
    if (revealTimer.current) window.clearInterval(revealTimer.current)
    try {
      const { matches } = await simulateAllWc2026()
      setBatchAll(matches)
      if (matches.length === 0) {
        setBatchRunning(false)
        return
      }
      let i = 0
      revealTimer.current = window.setInterval(() => {
        i += 1
        setVisibleCount(i)
        if (i >= matches.length && revealTimer.current) {
          window.clearInterval(revealTimer.current)
          revealTimer.current = null
          setBatchRunning(false)
        }
      }, REVEAL_MS)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Batch simulation failed')
      setBatchRunning(false)
    }
  }

  return (
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8 md:py-12 flex flex-col gap-8 bg-grid-pattern">
      <div className="flex flex-col gap-2 animate-fade-up">
        <h1 className="text-headline-lg text-primary">WC 2026 Simulator</h1>
        <p className="text-body-md text-on-surface-variant max-w-2xl">
          Run the production model on FIFA World Cup 2026 fixtures. Venue and home/away slots are
          inferred from the schedule and host country; you only pick the two nations.
        </p>
      </div>

      {apiOk === false && (
        <div className="bg-error-container text-on-error-container border border-error/20 rounded p-4 text-body-sm">
          API not reachable at <code className="font-mono">{API_BASE}</code>. Start it from the repo
          root:
          <pre className="mt-2 font-data-mono text-xs bg-surface-container-lowest/40 p-3 rounded overflow-x-auto">
            {`.venv/bin/uvicorn web.api.main:app --reload --port 8000`}
          </pre>
        </div>
      )}

      <div className="flex gap-2 border-b border-outline-variant">
        {(
          [
            { id: 'single' as const, label: 'Single match' },
            { id: 'batch' as const, label: 'Run all WC 2026' },
          ] as const
        ).map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setMode(tab.id)}
            className={`px-4 py-2 font-label-caps transition-colors border-b-2 -mb-px ${
              mode === tab.id
                ? 'border-pitch-green text-pitch-green'
                : 'border-transparent text-on-surface-variant hover:text-primary'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {mode === 'single' && (
        <>
          <section className="grid grid-cols-1 md:grid-cols-12 gap-gutter">
            <div className="md:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col gap-6">
              <div className="flex items-center gap-2 border-b border-surface-variant pb-3">
                <Icon name="sports_soccer" className="text-slate-gray" />
                <h2 className="text-headline-sm text-primary">Select nations</h2>
              </div>
              <div className="flex flex-col md:flex-row items-center gap-4 md:gap-8 justify-between w-full">
                <TeamPicker label="Nation" value={teamA} onChange={setTeamA} />
                <div className="flex-shrink-0 w-12 h-12 rounded-full bg-surface-container-high border border-outline-variant flex items-center justify-center font-label-caps text-on-surface-variant mt-6 md:mt-0">
                  VS
                </div>
                <TeamPicker label="Opponent" value={teamB} onChange={setTeamB} />
              </div>
              {single?.venue_label && (
                <div className="flex items-center gap-2 text-body-sm text-on-surface-variant bg-surface-container-low border border-outline-variant rounded px-3 py-2">
                  <Icon name="stadium" className="text-pitch-green text-[18px]" />
                  <span>
                    Venue resolved from schedule:{' '}
                    <span className="text-primary font-medium">{single.venue_label}</span>
                    {single.location ? ` · ${single.location}` : ''}
                  </span>
                </div>
              )}
            </div>

            <div className="md:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col justify-end">
              <button
                type="button"
                onClick={() => void runSingle()}
                disabled={loading || apiOk === false}
                className="w-full bg-deep-navy text-on-primary font-label-caps py-3 rounded hover:bg-primary transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
              >
                <Icon name="play_arrow" className="text-[18px]" />
                {loading ? 'Running model…' : 'Run model'}
              </button>
            </div>
          </section>

          {error && (
            <div className="bg-error-container text-on-error-container border border-error/20 rounded p-4 text-body-sm">
              {error}
            </div>
          )}

          {single && <MatchResultCanvas match={single} />}
        </>
      )}

      {mode === 'batch' && (
        <>
          <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-headline-sm text-primary mb-1">Full tournament pass</h2>
              <p className="text-body-sm text-on-surface-variant max-w-xl">
                Scores every resolved WC 2026 fixture with the live production model (not the
                holdout file). Rows reveal one-by-one; metrics update for played matches only.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void runBatch()}
              disabled={batchRunning || apiOk === false}
              className="shrink-0 bg-deep-navy text-on-primary font-label-caps px-6 py-3 rounded hover:bg-primary transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
            >
              <Icon name={batchRunning ? 'hourglass_top' : 'playlist_play'} className="text-[18px]" />
              {batchRunning
                ? `Scoring… ${visibleCount}/${batchAll.length || '…'}`
                : 'Run all matches'}
            </button>
          </section>

          {error && (
            <div className="bg-error-container text-on-error-container border border-error/20 rounded p-4 text-body-sm">
              {error}
            </div>
          )}

          {(visibleCount > 0 || batchRunning) && (
            <section className="grid grid-cols-1 md:grid-cols-3 gap-gutter animate-fade-in">
              <div className="bg-surface-container-lowest border border-outline-variant rounded p-5">
                <h3 className="font-label-caps text-on-surface-variant mb-3">Accuracy (played)</h3>
                <div className="text-headline-lg text-primary">
                  {(liveSummary.accuracy * 100).toFixed(1)}
                  <span className="text-body-sm text-on-surface-variant"> %</span>
                </div>
                <p className="text-body-sm text-on-surface-variant mt-1">
                  {liveSummary.n_played} played · {liveSummary.n} revealed
                </p>
              </div>
              <div className="bg-surface-container-lowest border border-outline-variant rounded p-5">
                <h3 className="font-label-caps text-on-surface-variant mb-3">Mean log loss</h3>
                <div className="text-headline-lg text-primary">
                  {liveSummary.n_played ? liveSummary.mean_log_loss.toFixed(3) : '—'}
                </div>
              </div>
              <div className="bg-surface-container-lowest border border-outline-variant rounded p-5">
                <h3 className="font-label-caps text-on-surface-variant mb-3">
                  Confusion (pred × actual)
                </h3>
                <ConfusionMatrix matrix={liveSummary.confusion} />
              </div>
            </section>
          )}

          {visibleRows.length > 0 && (
            <section className="bg-surface-container-lowest border border-outline-variant rounded overflow-hidden">
              <div className="overflow-x-auto max-h-[28rem]">
                <table className="w-full text-left border-collapse whitespace-nowrap">
                  <thead className="bg-surface-container-low border-b border-outline-variant sticky top-0">
                    <tr>
                      <th className="py-3 px-4 font-label-caps text-on-surface-variant">Date</th>
                      <th className="py-3 px-4 font-label-caps text-on-surface-variant">Fixture</th>
                      <th className="py-3 px-4 font-label-caps text-on-surface-variant w-56">
                        Probs (A/D/B)
                      </th>
                      <th className="py-3 px-4 font-label-caps text-on-surface-variant">Actual</th>
                      <th className="py-3 px-4 font-label-caps text-on-surface-variant">Status</th>
                      <th className="py-3 px-4 font-label-caps text-on-surface-variant text-right">
                        Log loss
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant">
                    {visibleRows.map((m) => (
                      <tr key={m.id} className="animate-fade-in">
                        <td className="py-2.5 px-4 font-data-mono text-on-surface-variant">
                          {m.date}
                        </td>
                        <td className="py-2.5 px-4">
                          <div className="flex flex-col gap-0.5">
                            <span className="text-body-sm font-semibold text-primary inline-flex items-center gap-1.5 flex-wrap">
                              <TeamFlag code={m.team_a_code} name={m.team_a} size="sm" />
                              {m.team_a}
                              <span className="text-outline font-normal">vs</span>
                              <TeamFlag code={m.team_b_code} name={m.team_b} size="sm" />
                              {m.team_b}
                            </span>
                            <span className="font-label-caps text-outline">
                              {m.venue_label}
                              {m.group_name ? ` · ${m.group_name}` : ''}
                            </span>
                          </div>
                        </td>
                        <td className="py-2.5 px-4">
                          <div className="max-w-[200px]">
                            <ProbabilityBar probabilities={m.probabilities} showLabels />
                          </div>
                        </td>
                        <td className="py-2.5 px-4 text-body-sm text-primary">
                          {m.actual_label ?? '—'}
                          {m.score ? (
                            <span className="text-outline font-data-mono ml-1">{m.score}</span>
                          ) : null}
                        </td>
                        <td className="py-2.5 px-4">
                          {m.status === 'upcoming' ? (
                            <span className="font-label-caps text-outline">Upcoming</span>
                          ) : m.correct ? (
                            <span className="inline-flex items-center gap-1 bg-secondary-container text-on-secondary-container px-2 py-0.5 rounded font-label-caps">
                              <Icon name="check" className="text-[14px]" /> Correct
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 bg-error-container text-on-error-container px-2 py-0.5 rounded font-label-caps">
                              <Icon name="close" className="text-[14px]" /> Incorrect
                            </span>
                          )}
                        </td>
                        <td
                          className={`py-2.5 px-4 font-data-mono text-right ${
                            m.log_loss != null && m.log_loss > 1.2
                              ? 'text-data-neg'
                              : 'text-on-surface-variant'
                          }`}
                        >
                          {m.log_loss != null ? m.log_loss.toFixed(3) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}
    </main>
  )
}
