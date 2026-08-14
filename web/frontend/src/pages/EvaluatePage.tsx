import { useEffect, useState } from 'react'
import { getHoldoutMatches, getHoldoutTournaments } from '../api/client'
import { ProbabilityBar } from '../components/ProbabilityBar'
import { Icon } from '../components/Icon'
import { pct } from '../lib/format'
import type { HoldoutFilters, HoldoutMatch, HoldoutSummary } from '../types'

const PAGE_SIZE = 50
const CONFUSION_LABELS = ['A', 'D', 'B'] as const

function ConfusionMatrix({ matrix }: { matrix: number[][] }) {
  const maxCell = Math.max(1, ...matrix.flat())
  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-left">
        <thead>
          <tr>
            <th className="p-0.5" />
            <th
              colSpan={3}
              className="font-label-caps text-[10px] text-on-surface-variant text-center pb-1 font-normal"
            >
              Actual
            </th>
          </tr>
          <tr>
            <th className="font-label-caps text-[10px] text-on-surface-variant pr-2 font-normal align-bottom">
              Pred
            </th>
            {CONFUSION_LABELS.map((lab) => (
              <th
                key={lab}
                className="font-data-mono text-[10px] text-on-surface-variant text-center px-0.5 pb-1 font-normal w-8"
              >
                {lab}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, ri) => (
            <tr key={CONFUSION_LABELS[ri]}>
              <th
                scope="row"
                className="font-data-mono text-[10px] text-on-surface-variant pr-2 font-normal text-right"
              >
                {CONFUSION_LABELS[ri]}
              </th>
              {row.map((n, ci) => (
                <td key={`${CONFUSION_LABELS[ri]}-${CONFUSION_LABELS[ci]}`} className="p-0.5">
                  <div
                    className="rounded-[2px] w-8 h-8 flex items-center justify-center text-[10px] font-data-mono"
                    style={{
                      background:
                        n === 0
                          ? 'var(--color-surface-variant)'
                          : `color-mix(in srgb, var(--color-pitch-green) ${Math.min(100, (n / maxCell) * 100)}%, var(--color-surface-variant))`,
                    }}
                    title={`Pred ${CONFUSION_LABELS[ri]} · Actual ${CONFUSION_LABELS[ci]}: ${n}`}
                  >
                    {n}
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function EvaluatePage() {
  const [filters, setFilters] = useState<HoldoutFilters>({
    tournament: 'All Tournaments',
    confidence: 'any',
    correctness: 'all',
    search: '',
  })
  const [matches, setMatches] = useState<HoldoutMatch[]>([])
  const [summary, setSummary] = useState<HoldoutSummary | null>(null)
  const [totalHoldout, setTotalHoldout] = useState(0)
  const [selected, setSelected] = useState<HoldoutMatch | null>(null)
  const [page, setPage] = useState(1)
  const tournaments = getHoldoutTournaments()

  useEffect(() => {
    let cancelled = false
    void getHoldoutMatches(filters).then((r) => {
      if (cancelled) return
      setMatches(r.matches)
      setSummary(r.summary)
      setTotalHoldout(r.total)
      setPage(1)
    })
    return () => {
      cancelled = true
    }
  }, [filters])

  const pageCount = Math.max(1, Math.ceil(matches.length / PAGE_SIZE))
  const safePage = Math.min(page, pageCount)
  const pageStart = (safePage - 1) * PAGE_SIZE
  const pageMatches = matches.slice(pageStart, pageStart + PAGE_SIZE)
  const showingFrom = matches.length === 0 ? 0 : pageStart + 1
  const showingTo = Math.min(pageStart + PAGE_SIZE, matches.length)

  return (
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8 flex flex-col gap-8 relative overflow-x-hidden">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-outline-variant pb-6">
        <div>
          <h1 className="text-headline-lg text-primary tracking-tight">Holdout Explorer</h1>
          <p className="text-body-md text-on-surface-variant mt-1 max-w-2xl">
            Precomputed predictions on the 2023+ test set — browse hits, misses, and surprise
            (log loss contribution).
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="flex items-center gap-2 bg-surface-container-lowest border border-outline-variant px-3 py-1.5 rounded hover:bg-surface-container transition-colors"
            onClick={() => {
              const blob = new Blob([JSON.stringify(matches, null, 2)], { type: 'application/json' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = 'holdout-export.json'
              a.click()
              URL.revokeObjectURL(url)
            }}
          >
            <Icon name="download" className="text-[20px]" />
            <span className="font-label-caps">Export</span>
          </button>
        </div>
      </header>

      {summary && (
        <section className="grid grid-cols-1 md:grid-cols-3 gap-gutter animate-fade-in">
          <div className="bg-surface-container-lowest border border-outline-variant rounded p-5 hover:border-pitch-green transition-colors">
            <div className="flex justify-between items-start mb-4">
              <h3 className="font-label-caps text-on-surface-variant">Filtered Accuracy</h3>
              <Icon name="check_circle" className="text-pitch-green" />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-headline-lg text-primary">{(summary.accuracy * 100).toFixed(1)}</span>
              <span className="text-body-sm text-on-surface-variant">%</span>
            </div>
            <div className="mt-2 flex items-center gap-1 text-data-pos font-label-caps">
              <Icon name="trending_up" className="text-[14px]" />
              <span>
                {summary.vs_baseline_accuracy_delta >= 0 ? '+' : ''}
                {(summary.vs_baseline_accuracy_delta * 100).toFixed(1)}% vs baseline (ref)
              </span>
            </div>
          </div>
          <div className="bg-surface-container-lowest border border-outline-variant rounded p-5 hover:border-pitch-green transition-colors">
            <div className="flex justify-between items-start mb-4">
              <h3 className="font-label-caps text-on-surface-variant">Mean Log Loss</h3>
              <Icon name="functions" className="text-outline" />
            </div>
            <span className="text-headline-lg text-primary">{summary.mean_log_loss.toFixed(3)}</span>
          </div>
          <div className="bg-surface-container-lowest border border-outline-variant rounded p-5 hover:border-pitch-green transition-colors">
            <div className="flex justify-between items-start mb-3">
              <h3 className="font-label-caps text-on-surface-variant">Confusion (pred × actual)</h3>
              <Icon name="grid_on" className="text-outline" />
            </div>
            <ConfusionMatrix matrix={summary.confusion} />
          </div>
        </section>
      )}

      <section className="flex flex-wrap items-center gap-4 bg-surface-container-lowest p-3 border border-outline-variant rounded">
        <div className="flex items-center gap-2 text-on-surface-variant border-r border-outline-variant pr-4 mr-2">
          <Icon name="filter_list" className="text-[20px]" />
          <span className="font-label-caps font-bold">Filters</span>
        </div>
        <select
          className="bg-surface border border-outline-variant text-body-sm px-3 py-1.5 rounded focus:outline-none focus:border-pitch-green max-w-[220px]"
          value={filters.tournament}
          onChange={(e) => setFilters((f) => ({ ...f, tournament: e.target.value }))}
        >
          {tournaments.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          className="bg-surface border border-outline-variant text-body-sm px-3 py-1.5 rounded focus:outline-none focus:border-pitch-green"
          value={filters.confidence}
          onChange={(e) =>
            setFilters((f) => ({
              ...f,
              confidence: e.target.value as HoldoutFilters['confidence'],
            }))
          }
        >
          <option value="any">Any Confidence</option>
          <option value="high">High (&gt;70%)</option>
          <option value="medium">Medium (50-70%)</option>
          <option value="low">Low (&lt;50%)</option>
        </select>
        <select
          className="bg-surface border border-outline-variant text-body-sm px-3 py-1.5 rounded focus:outline-none focus:border-pitch-green"
          value={filters.correctness}
          onChange={(e) =>
            setFilters((f) => ({
              ...f,
              correctness: e.target.value as HoldoutFilters['correctness'],
            }))
          }
        >
          <option value="all">All Results</option>
          <option value="correct">Correct Predictions</option>
          <option value="incorrect">Incorrect Predictions</option>
        </select>
        <input
          className="bg-surface border border-outline-variant text-body-sm px-3 py-1.5 rounded focus:outline-none focus:border-pitch-green min-w-[160px]"
          placeholder="Search matches…"
          value={filters.search}
          onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
        />
        <span className="ml-auto font-data-mono text-on-surface-variant">
          {summary?.n ?? 0} records
        </span>
      </section>

      <section className="bg-surface-container-lowest border border-outline-variant rounded overflow-hidden flex-grow flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse whitespace-nowrap">
            <thead className="bg-surface-container-low border-b border-outline-variant">
              <tr>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant w-32">Date</th>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant">Match Fixture</th>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant w-64">Predicted Probs (A/D/B)</th>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant w-32">Actual</th>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant w-32">Status</th>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant text-right w-24">Log Loss</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant">
              {pageMatches.map((m) => (
                <tr
                  key={m.id}
                  className="hover:bg-surface-container transition-colors cursor-pointer"
                  onClick={() => setSelected(m)}
                >
                  <td className="py-2.5 px-4 font-data-mono text-on-surface-variant">{m.date}</td>
                  <td className="py-2.5 px-4">
                    <div className="flex flex-col">
                      <span className="text-body-sm font-semibold text-primary">
                        {m.team_a} vs {m.team_b}
                      </span>
                      <span className="font-label-caps text-outline">{m.tournament}</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-4">
                    <div className="max-w-[200px]">
                      <ProbabilityBar probabilities={m.probabilities} showLabels />
                    </div>
                  </td>
                  <td className="py-2.5 px-4 text-body-sm text-primary">{m.actual_label}</td>
                  <td className="py-2.5 px-4">
                    {m.correct ? (
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
                      m.log_loss > 1.2 ? 'text-data-neg' : 'text-on-surface-variant'
                    }`}
                  >
                    {m.log_loss.toFixed(3)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-3 border-t border-outline-variant bg-surface text-body-sm text-on-surface-variant flex flex-wrap items-center justify-between gap-3">
          <span>
            Showing {showingFrom}–{showingTo} of {matches.length} filtered
            {totalHoldout > 0 ? ` (${totalHoldout} holdout matches)` : ''}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="px-3 py-1 border border-outline-variant rounded disabled:opacity-40 hover:bg-surface-container"
              disabled={safePage <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </button>
            <span className="font-data-mono">
              {safePage} / {pageCount}
            </span>
            <button
              type="button"
              className="px-3 py-1 border border-outline-variant rounded disabled:opacity-40 hover:bg-surface-container"
              disabled={safePage >= pageCount}
              onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            >
              Next
            </button>
          </div>
        </div>
      </section>

      {/* Detail drawer */}
      <div
        className={`fixed inset-0 bg-primary/20 backdrop-blur-sm z-40 transition-opacity ${
          selected ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setSelected(null)}
      />
      <aside
        className={`fixed inset-y-0 right-0 w-full md:w-[400px] bg-surface-container-lowest border-l border-outline-variant z-50 flex flex-col transition-transform duration-300 ${
          selected ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {selected && (
          <>
            <div className="flex justify-between items-center p-4 border-b border-outline-variant bg-surface">
              <h2 className="text-headline-sm text-primary">Match Evaluation</h2>
              <button type="button" className="text-outline hover:text-primary p-1" onClick={() => setSelected(null)}>
                <Icon name="close" />
              </button>
            </div>
            <div className="flex-grow overflow-y-auto p-6 flex flex-col gap-6">
              <div className="text-center pb-6 border-b border-outline-variant">
                <div className="font-label-caps text-on-surface-variant mb-2">
                  {selected.tournament} · {selected.date}
                </div>
                <div className="flex justify-center items-center gap-4">
                  <span className="text-headline-md text-primary">{selected.team_a_code}</span>
                  <span className="text-body-lg text-outline">{selected.score ?? '—'}</span>
                  <span className="text-headline-md text-pitch-green">{selected.team_b_code}</span>
                </div>
                <div
                  className={`mt-4 inline-flex items-center gap-1 px-3 py-1 rounded font-label-caps ${
                    selected.correct
                      ? 'bg-secondary-container text-on-secondary-container'
                      : 'bg-error-container text-on-error-container'
                  }`}
                >
                  <Icon name={selected.correct ? 'check' : 'close'} className="text-[16px]" />
                  Prediction {selected.correct ? 'correct' : 'incorrect'}
                </div>
              </div>
              <div>
                <h3 className="font-label-caps text-on-surface-variant uppercase mb-3">
                  Model Output Probabilities
                </h3>
                <ProbabilityBar
                  probabilities={selected.probabilities}
                  labelA={selected.team_a}
                  labelB={selected.team_b}
                  tall
                />
              </div>
              <div>
                <h3 className="font-label-caps text-on-surface-variant uppercase mb-3">Error Metrics</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-surface p-3 rounded border border-outline-variant">
                    <div className="font-label-caps text-outline mb-1">Log Loss Contrib.</div>
                    <div className="text-headline-sm font-data-mono text-data-neg">
                      {selected.log_loss.toFixed(3)}
                    </div>
                  </div>
                  <div className="bg-surface p-3 rounded border border-outline-variant">
                    <div className="font-label-caps text-outline mb-1">Elo gap</div>
                    <div className="text-headline-sm font-data-mono text-primary">{selected.elo_gap}</div>
                  </div>
                </div>
              </div>
              {selected.narrative && (
                <p className="text-body-sm text-on-surface-variant border-t border-outline-variant pt-4">
                  {selected.narrative}
                </p>
              )}
              <p className="text-body-sm text-outline">
                Max confidence {pct(Math.max(selected.probabilities.p_a, selected.probabilities.p_draw, selected.probabilities.p_b))}
              </p>
            </div>
          </>
        )}
      </aside>
    </main>
  )
}
