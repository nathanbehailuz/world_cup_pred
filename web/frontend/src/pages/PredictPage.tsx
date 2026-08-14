import { useState } from 'react'
import { predictMatch } from '../api/client'
import { TeamPicker } from '../components/TeamPicker'
import { ProbabilityBar } from '../components/ProbabilityBar'
import { LabelCallout } from '../components/LabelCallout'
import { Icon } from '../components/Icon'
import { pct } from '../lib/format'
import type { PredictResponse, VenueMode } from '../types'

const VENUES: { id: VenueMode; label: string }[] = [
  { id: 'neutral', label: 'Neutral' },
  { id: 'home_a', label: 'Home A' },
  { id: 'wc_venue', label: 'WC Venue' },
]

export function PredictPage() {
  const [teamA, setTeamA] = useState('Argentina')
  const [teamB, setTeamB] = useState('France')
  const [venue, setVenue] = useState<VenueMode>('neutral')
  const [asOf, setAsOf] = useState('2026-06-15')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PredictResponse | null>(null)

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const res = await predictMatch({ team_a: teamA, team_b: teamB, venue, as_of: asOf })
      setResult(res)
    } catch (e) {
      setResult(null)
      setError(e instanceof Error ? e.message : 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  const favoriteName =
    result == null
      ? ''
      : result.favorite === 'A'
        ? result.team_a.name
        : result.favorite === 'B'
          ? result.team_b.name
          : 'Draw'

  return (
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8 md:py-12 flex flex-col gap-8 bg-grid-pattern">
      <div className="flex flex-col gap-2 animate-fade-up">
        <h1 className="text-headline-lg text-primary">Match Simulation Engine</h1>
        <p className="text-body-md text-on-surface-variant max-w-2xl">
          Configure two teams and venue to run the point-in-time probabilistic model. Outputs a full
          W/D/L vector with a feature snapshot as of the cutoff date.
        </p>
      </div>

      <section className="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        <div className="md:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col gap-6">
          <div className="flex items-center gap-2 border-b border-surface-variant pb-3">
            <Icon name="sports_soccer" className="text-slate-gray" />
            <h2 className="text-headline-sm text-primary">Select Teams</h2>
          </div>
          <div className="flex flex-col md:flex-row items-center gap-4 md:gap-8 justify-between w-full mt-2">
            <TeamPicker label="Team A (Home)" value={teamA} onChange={setTeamA} />
            <div className="flex-shrink-0 w-12 h-12 rounded-full bg-surface-container-high border border-outline-variant flex items-center justify-center font-label-caps text-on-surface-variant mt-6 md:mt-0">
              VS
            </div>
            <TeamPicker label="Team B (Away)" value={teamB} onChange={setTeamB} />
          </div>
        </div>

        <div className="md:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col gap-6 justify-between">
          <div>
            <div className="flex items-center gap-2 border-b border-surface-variant pb-3 mb-4">
              <Icon name="tune" className="text-slate-gray" />
              <h2 className="text-headline-sm text-primary">Parameters</h2>
            </div>
            <div className="flex flex-col gap-5">
              <div className="flex flex-col gap-2">
                <label className="font-label-caps text-slate-gray">Venue Constraints</label>
                <div className="flex bg-surface-container rounded p-1 border border-outline-variant">
                  {VENUES.map((v) => (
                    <button
                      key={v.id}
                      type="button"
                      onClick={() => setVenue(v.id)}
                      className={`flex-1 py-1.5 px-2 font-label-caps rounded transition-colors ${
                        venue === v.id
                          ? 'bg-surface-container-lowest shadow text-primary font-bold'
                          : 'text-on-surface-variant hover:text-primary'
                      }`}
                    >
                      {v.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <label className="font-label-caps text-slate-gray">Simulation Date</label>
                <div className="relative flex items-center">
                  <Icon name="calendar_month" className="absolute left-3 text-outline text-[20px]" />
                  <input
                    className="w-full bg-surface-container pl-10 pr-4 py-2 rounded border border-outline-variant text-body-md text-primary focus:outline-none focus:border-pitch-green"
                    type="date"
                    value={asOf}
                    onChange={(e) => setAsOf(e.target.value)}
                  />
                </div>
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void run()}
            disabled={loading}
            className="w-full bg-deep-navy text-on-primary font-label-caps py-3 rounded mt-4 hover:bg-primary transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
          >
            <Icon name="play_arrow" className="text-[18px]" />
            {loading ? 'Running…' : 'Run Simulation'}
          </button>
        </div>
      </section>

      {error && (
        <div className="bg-error-container text-on-error-container border border-error/20 rounded p-4 text-body-sm">
          {error}
        </div>
      )}

      {result && (
        <section className="flex flex-col gap-6 animate-fade-up">
          <div className="flex justify-between items-end flex-wrap gap-2">
            <h2 className="text-headline-md text-primary flex items-center gap-2">
              <Icon name="bar_chart" className="text-pitch-green" filled />
              Simulation Output
            </h2>
            <span className="font-label-caps text-slate-gray bg-surface-container px-2 py-1 rounded border border-outline-variant">
              As of {result.feature_cutoff} · {result.source}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-12 gap-gutter">
            <div className="md:col-span-8 flex flex-col gap-6">
              <div className="bg-surface-container-lowest border-l-4 border-pitch-green rounded-r-xl border-y border-r border-outline-variant p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <span className="font-label-caps text-slate-gray">Statistical Favorite</span>
                  <div className="text-headline-lg text-primary tracking-tight">
                    {favoriteName}{' '}
                    <span className="text-pitch-green font-normal ml-2">{pct(result.confidence)}</span>
                  </div>
                  <span className="text-body-sm text-on-surface-variant flex items-center gap-1 mt-1">
                    <Icon name="check_circle" className="text-[16px] text-data-pos" />
                    Max probability {pct(result.confidence)} — not betting advice.
                  </span>
                </div>
                <div className="h-16 w-16 rounded-full border-4 border-surface-container flex items-center justify-center bg-pitch-green text-on-primary text-body-lg font-bold">
                  {result.favorite === 'Draw' ? 'D' : 'Win'}
                </div>
              </div>

              <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col gap-4">
                <div className="flex justify-between items-center font-label-caps text-primary">
                  <span>{result.team_a.name} (A)</span>
                  <span className="text-slate-gray">Draw</span>
                  <span>{result.team_b.name} (B)</span>
                </div>
                <ProbabilityBar
                  probabilities={result.probabilities}
                  labelA={result.team_a.name}
                  labelB={result.team_b.name}
                  tall
                  showLabels={false}
                />
              </div>

              <LabelCallout />
              <p className="text-body-sm text-on-surface-variant">{result.disclaimer}</p>
            </div>

            <div className="md:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden flex flex-col">
              <div className="p-4 border-b border-surface-variant bg-surface-container-low flex justify-between items-center">
                <h3 className="font-label-caps text-primary">Feature Snapshot</h3>
                <Icon name="dataset" className="text-slate-gray text-[18px]" />
              </div>
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface border-b border-outline-variant font-label-caps text-slate-gray">
                    <th className="py-3 px-4 font-normal">Metric</th>
                    <th className="py-3 px-4 text-right font-normal">Team A</th>
                    <th className="py-3 px-4 text-right font-normal">Team B</th>
                  </tr>
                </thead>
                <tbody className="text-body-sm text-primary">
                  {result.features.map((row) => (
                    <tr key={row.metric} className="border-b border-surface-variant hover:bg-surface-container">
                      <td className="py-3 px-4 font-medium text-slate-gray">{row.metric}</td>
                      <td className="py-3 px-4 text-right font-data-mono">{row.team_a}</td>
                      <td className="py-3 px-4 text-right font-data-mono">{row.team_b}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="p-4 border-t border-surface-variant">
                <h4 className="font-label-caps text-slate-gray mb-2">Global importance (top)</h4>
                <ul className="flex flex-col gap-2 text-body-sm">
                  {result.top_importance.map((f) => (
                    <li key={f.feature} className="flex justify-between border-b border-outline-variant pb-1">
                      <span>{f.feature}</span>
                      <span className="font-data-mono text-outline">+{f.value.toFixed(3)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>
      )}
    </main>
  )
}
