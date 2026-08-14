import { useEffect, useState } from 'react'
import { getWc2026Fixtures } from '../api/client'
import { ProbabilityBar } from '../components/ProbabilityBar'
import { Icon } from '../components/Icon'
import { outcomeLabel } from '../lib/format'
import type { WcFixture } from '../types'

export function Wc2026Page() {
  const [fixtures, setFixtures] = useState<WcFixture[]>([])
  const [refreshed, setRefreshed] = useState('')
  const [stage, setStage] = useState('all')
  const [group, setGroup] = useState('all')

  useEffect(() => {
    void getWc2026Fixtures().then((r) => {
      setFixtures(r.fixtures)
      setRefreshed(r.refreshed_at)
    })
  }, [])

  const groups = [
    'all',
    ...Array.from(new Set(fixtures.map((f) => f.group_name).filter(Boolean) as string[])).sort(),
  ]

  const filtered = fixtures.filter((f) => {
    if (stage !== 'all' && f.stage !== stage) return false
    if (group !== 'all' && f.group_name !== group) return false
    return true
  })

  const played = filtered.filter((f) => f.status === 'final')
  const correct = played.filter((f) => f.correct).length

  return (
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8 md:py-12 flex flex-col gap-8">
      <header className="border-b border-outline-variant pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-headline-lg text-primary">World Cup 2026</h1>
          <p className="text-body-md text-on-surface-variant mt-2 max-w-2xl">
            Schedule predictions from the backtest artifact. Probabilities first; correctness when
            results exist.
          </p>
        </div>
        <p className="font-label-caps text-slate-gray">Schedule last refreshed · {refreshed}</p>
      </header>

      <section className="flex flex-wrap items-center gap-3 bg-surface-container-lowest border border-outline-variant rounded p-3">
        <span className="font-label-caps text-on-surface-variant">Stage</span>
        {['all', 'group', 'knockout'].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStage(s)}
            className={`px-3 py-1.5 rounded font-label-caps border transition-colors ${
              stage === s
                ? 'bg-deep-navy text-on-primary border-deep-navy'
                : 'border-outline-variant text-on-surface-variant hover:border-pitch-green'
            }`}
          >
            {s === 'all' ? 'All' : s}
          </button>
        ))}
        <select
          className="ml-auto bg-surface border border-outline-variant text-body-sm px-3 py-1.5 rounded"
          value={group}
          onChange={(e) => setGroup(e.target.value)}
        >
          {groups.map((g) => (
            <option key={g} value={g}>
              {g === 'all' ? 'All groups' : g}
            </option>
          ))}
        </select>
      </section>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-gutter">
        <div className="bg-surface-container-lowest border border-outline-variant rounded p-4">
          <div className="font-label-caps text-on-surface-variant">Fixtures</div>
          <div className="text-headline-md font-data-mono mt-1">{filtered.length}</div>
        </div>
        <div className="bg-surface-container-lowest border border-outline-variant rounded p-4">
          <div className="font-label-caps text-on-surface-variant">Played</div>
          <div className="text-headline-md font-data-mono mt-1">{played.length}</div>
        </div>
        <div className="bg-surface-container-lowest border border-outline-variant rounded p-4">
          <div className="font-label-caps text-on-surface-variant">Argmax correct</div>
          <div className="text-headline-md font-data-mono mt-1 text-data-pos">
            {played.length ? `${correct}/${played.length}` : '—'}
          </div>
        </div>
        <div className="bg-surface-container-lowest border border-outline-variant rounded p-4">
          <div className="font-label-caps text-on-surface-variant">Accuracy</div>
          <div className="text-headline-md font-data-mono mt-1">
            {played.length ? `${((correct / played.length) * 100).toFixed(0)}%` : '—'}
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        {filtered.map((f) => (
          <article
            key={`${f.date}-${f.home_team}-${f.away_team}`}
            className="bg-surface-container-lowest border border-outline-variant rounded p-4 md:p-5 grid grid-cols-1 md:grid-cols-12 gap-4 items-center hover:border-outline transition-colors"
          >
            <div className="md:col-span-2 text-body-sm text-on-surface-variant">
              <div className="font-data-mono">{f.date}</div>
              <div className="font-label-caps mt-1">{f.group_name || f.stage}</div>
            </div>
            <div className="md:col-span-4 flex items-center justify-between gap-2">
              <span className="font-semibold text-primary">{f.home_team}</span>
              <span className="text-slate-gray font-data-mono text-sm">
                {f.home_score != null ? `${f.home_score}–${f.away_score}` : 'vs'}
              </span>
              <span className="font-semibold text-primary text-right">{f.away_team}</span>
            </div>
            <div className="md:col-span-4">
              <ProbabilityBar
                probabilities={{ p_a: f.p_home, p_draw: f.p_draw, p_b: f.p_away }}
                labelA={f.home_team}
                labelB={f.away_team}
              />
            </div>
            <div className="md:col-span-2 flex md:justify-end">
              {f.status === 'final' ? (
                f.correct ? (
                  <span className="inline-flex items-center gap-1 bg-secondary-container text-on-secondary-container px-2 py-1 rounded font-label-caps">
                    <Icon name="check" className="text-[14px]" />
                    {outcomeLabel(f.actual_outcome!, f.home_team, f.away_team)}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 bg-error-container text-on-error-container px-2 py-1 rounded font-label-caps">
                    <Icon name="close" className="text-[14px]" /> Miss
                  </span>
                )
              ) : (
                <span className="font-label-caps text-slate-gray border border-outline-variant px-2 py-1 rounded">
                  Upcoming
                </span>
              )}
            </div>
          </article>
        ))}
      </section>
    </main>
  )
}
