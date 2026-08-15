import { useEffect, useState } from 'react'
import { getModelMeta } from '../api/client'
import { Icon } from '../components/Icon'
import { ProbabilityBar } from '../components/ProbabilityBar'
import { formatCi, pct } from '../lib/format'
import { TeamLabel } from '../components/TeamFlag'
import type {
  CalibrationBin,
  ErrorSlice,
  ModelMeta,
  SamplePrediction,
} from '../types'

const OUTCOME_LABELS = ['home_win', 'draw', 'away_win'] as const
const OUTCOME_TITLES: Record<(typeof OUTCOME_LABELS)[number], string> = {
  home_win: 'Home win',
  draw: 'Draw',
  away_win: 'Away win',
}

const SLICE_LABELS: Record<string, string> = {
  elo_gap_lt_50: 'Elo gap < 50',
  elo_gap_50_150: 'Elo gap 50–150',
  elo_gap_150_300: 'Elo gap 150–300',
  elo_gap_gt_300: 'Elo gap > 300',
  neutral: 'Neutral venues',
  non_neutral: 'Non-neutral venues',
  true_home_win: 'True home win',
  true_draw: 'True draw',
  true_away_win: 'True away win',
}

function sliceLabel(key: string): string {
  return SLICE_LABELS[key] ?? key.replace(/_/g, ' ')
}

function gainList(meta: ModelMeta): { feature: string; gain: number }[] {
  const fi = meta.feature_importance
  return fi.gain_production_model ?? fi.gain_experiment_model ?? fi.gain ?? []
}

function ImportanceBars({
  rows,
  formatValue,
}: {
  rows: { feature: string; value: number; sub?: string }[]
  formatValue: (v: number) => string
}) {
  const max = Math.max(...rows.map((r) => r.value), 0.001)
  return (
    <ul className="flex flex-col gap-3">
      {rows.map((r, i) => (
        <li key={r.feature} className="flex flex-col gap-1">
          <div className="flex justify-between text-body-sm gap-2">
            <span className="font-medium text-primary font-data-mono text-[12px]">{r.feature}</span>
            <span className="font-data-mono text-slate-gray shrink-0">
              {formatValue(r.value)}
              {r.sub ? ` ${r.sub}` : ''}
            </span>
          </div>
          <div className="h-2 bg-surface-variant rounded overflow-hidden">
            <div
              className="h-full bg-pitch-green origin-left animate-bar-grow"
              style={{
                width: `${(r.value / max) * 100}%`,
                animationDelay: `${i * 40}ms`,
              }}
            />
          </div>
        </li>
      ))}
    </ul>
  )
}

function CalibrationChart({ bins, title }: { bins: CalibrationBin[]; title: string }) {
  const size = 160
  const pad = 18
  const inner = size - pad * 2
  const pts = bins.map((b) => ({
    x: pad + b.mean_predicted * inner,
    y: pad + (1 - b.empirical) * inner,
    n: b.n,
    label: b.bin,
  }))

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded p-4 flex flex-col gap-3">
      <h3 className="font-label-caps text-on-surface-variant">{title}</h3>
      <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[200px] mx-auto" aria-hidden>
        <line
          x1={pad}
          y1={pad + inner}
          x2={pad + inner}
          y2={pad}
          stroke="var(--color-outline-variant)"
          strokeDasharray="4 3"
        />
        <rect
          x={pad}
          y={pad}
          width={inner}
          height={inner}
          fill="none"
          stroke="var(--color-outline-variant)"
        />
        {pts.map((p) => (
          <circle
            key={p.label}
            cx={p.x}
            cy={p.y}
            r={Math.max(3, Math.min(7, 2 + Math.sqrt(p.n) / 4))}
            fill="var(--color-pitch-green)"
            opacity={0.85}
          >
            <title>
              {p.label}: pred {bins.find((b) => b.bin === p.label)?.mean_predicted.toFixed(3)}, emp{' '}
              {bins.find((b) => b.bin === p.label)?.empirical.toFixed(3)} (n={p.n})
            </title>
          </circle>
        ))}
        <text x={pad} y={size - 4} className="fill-[var(--color-slate-gray)]" fontSize="8">
          predicted →
        </text>
        <text
          x={6}
          y={pad + inner / 2}
          className="fill-[var(--color-slate-gray)]"
          fontSize="8"
          transform={`rotate(-90 6 ${pad + inner / 2})`}
        >
          empirical →
        </text>
      </svg>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[11px] font-data-mono">
          <thead>
            <tr className="text-on-surface-variant">
              <th className="py-1 pr-2 font-label-caps font-normal">Bin</th>
              <th className="py-1 pr-2 text-right font-label-caps font-normal">n</th>
              <th className="py-1 pr-2 text-right font-label-caps font-normal">Pred</th>
              <th className="py-1 text-right font-label-caps font-normal">Emp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant">
            {bins.map((b) => (
              <tr key={b.bin}>
                <td className="py-1 pr-2">{b.bin}</td>
                <td className="py-1 pr-2 text-right">{b.n}</td>
                <td className="py-1 pr-2 text-right">{b.mean_predicted.toFixed(3)}</td>
                <td className="py-1 text-right">{b.empirical.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ErrorSlicesTable({ rows }: { rows: ErrorSlice[] }) {
  return (
    <div className="overflow-x-auto border border-outline-variant rounded bg-surface-container-lowest">
      <table className="w-full text-left border-collapse min-w-[640px]">
        <thead className="bg-surface-container-low border-b border-outline-variant">
          <tr>
            <th className="py-3 px-4 font-label-caps text-on-surface-variant">Slice</th>
            <th className="py-3 px-4 font-label-caps text-on-surface-variant text-right">n</th>
            <th className="py-3 px-4 font-label-caps text-on-surface-variant text-right">Log loss</th>
            <th className="py-3 px-4 font-label-caps text-on-surface-variant text-right">Accuracy</th>
            <th className="py-3 px-4 font-label-caps text-on-surface-variant text-right">Mean p(draw)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant text-body-sm">
          {rows.map((r) => (
            <tr key={r.slice} className="hover:bg-surface-container">
              <td className="py-2.5 px-4 font-medium text-primary">{sliceLabel(r.slice)}</td>
              <td className="py-2.5 px-4 text-right font-data-mono">{r.n.toLocaleString()}</td>
              <td className="py-2.5 px-4 text-right font-data-mono">{r.log_loss.toFixed(3)}</td>
              <td className="py-2.5 px-4 text-right font-data-mono">{pct(r.accuracy)}</td>
              <td className="py-2.5 px-4 text-right font-data-mono">{r.mean_predicted_draw.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SampleCards({ samples }: { samples: SamplePrediction[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-gutter">
      {samples.map((s) => {
        const actual =
          s.actual_outcome === null || s.actual_outcome === undefined
            ? null
            : OUTCOME_LABELS[s.actual_outcome] ?? null
        return (
          <article
            key={`${s.category}-${s.date}-${s.team_a}-${s.team_b}`}
            className="bg-surface-container-lowest border border-outline-variant rounded p-5 flex flex-col gap-3"
          >
            <div className="flex justify-between items-start gap-2">
              <h3 className="font-label-caps text-pitch-green">{s.category.replace(/_/g, ' ')}</h3>
              {s.date && (
                <span className="font-data-mono text-[11px] text-slate-gray">{s.date}</span>
              )}
            </div>
            <p className="text-body-md text-primary font-medium flex items-center gap-2 flex-wrap">
              <TeamLabel name={s.team_a} size="md" nameClassName="font-medium" />
              <span className="text-slate-gray">vs</span>
              <TeamLabel name={s.team_b} size="md" nameClassName="font-medium" />
              {s.neutral ? (
                <span className="ml-1 font-label-caps text-slate-gray">neutral</span>
              ) : null}
            </p>
            <ProbabilityBar
              probabilities={{ p_a: s.team_a_win, p_draw: s.draw, p_b: s.team_b_win }}
              labelA={s.team_a}
              labelB={s.team_b}
              tall
            />
            <dl className="flex flex-wrap gap-x-4 gap-y-1 text-body-sm text-on-surface-variant">
              {s.elo_diff != null && (
                <div>
                  <dt className="inline text-slate-gray">Elo Δ </dt>
                  <dd className="inline font-data-mono">{s.elo_diff.toFixed(1)}</dd>
                </div>
              )}
              {actual && (
                <div>
                  <dt className="inline text-slate-gray">Actual </dt>
                  <dd className="inline font-data-mono">{OUTCOME_TITLES[actual]}</dd>
                </div>
              )}
            </dl>
            <p className="text-body-sm text-on-surface-variant">{s.comment}</p>
          </article>
        )
      })}
    </div>
  )
}

export function ModelAnalysisPage() {
  const [meta, setMeta] = useState<ModelMeta | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    void getModelMeta()
      .then((m) => {
        if (!cancelled) setMeta(m)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (error) {
    return (
      <main className="flex-grow max-w-container-max mx-auto px-margin-desktop py-12 text-on-surface-variant">
        Failed to load model metadata: {error}
      </main>
    )
  }

  if (!meta) {
    return (
      <main className="flex-grow max-w-container-max mx-auto px-margin-desktop py-12 text-on-surface-variant">
        Loading model metadata…
      </main>
    )
  }

  const { baselines, bootstrap_ci, feature_importance, experiments } = meta
  const selected = experiments.find((e) => e.label === meta.selected_config)
  const nTest = selected?.n_test
  const deltaCi = bootstrap_ci.xgboost_minus_elo
  const gains = gainList(meta).slice(0, 12)
  const perm = feature_importance.permutation.slice(0, 12)

  return (
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8 md:py-12 flex flex-col gap-12">
      <header className="border-b border-outline-variant pb-6 animate-fade-up">
        <h1 className="text-headline-lg text-primary">Model Analysis</h1>
        <p className="text-body-md text-on-surface-variant mt-2 max-w-2xl">
          Competitive holdout from {meta.train_cutoff} onward
          {nTest != null ? ` (${nTest.toLocaleString()} matches)` : ''}: baselines, ablations,
          calibration, and error slices from training metadata.
        </p>
        <p className="font-label-caps text-slate-gray mt-3">
          As of cutoff {meta.feature_cutoff} · config {meta.selected_config} · refit on{' '}
          {meta.production_fit_rows.toLocaleString()} rows through {meta.production_fit_through}
        </p>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-gutter">
        {(
          [
            ['Constant prior', baselines.constant_prior, bootstrap_ci.constant_prior],
            ['Elo logistic', baselines.elo_logistic, bootstrap_ci.elo_baseline],
            ['Production XGBoost', baselines.production_xgboost, bootstrap_ci.production_xgboost],
          ] as const
        ).map(([label, m, ci], i) => (
          <div
            key={label}
            className={`bg-surface-container-lowest border rounded p-5 ${
              i === 2 ? 'border-pitch-green border-l-4' : 'border-outline-variant'
            }`}
          >
            <h3 className="font-label-caps text-on-surface-variant mb-3">{label}</h3>
            <div className="text-headline-md font-data-mono text-primary">{m.log_loss.toFixed(3)}</div>
            <p className="text-body-sm text-on-surface-variant mt-1">Log loss</p>
            <dl className="mt-4 space-y-1 text-body-sm">
              <div className="flex justify-between">
                <dt className="text-slate-gray">Accuracy</dt>
                <dd className="font-data-mono">{pct(m.accuracy)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-gray">Brier</dt>
                <dd className="font-data-mono">{m.brier_score.toFixed(3)}</dd>
              </div>
              {ci && (
                <div className="flex justify-between gap-2">
                  <dt className="text-slate-gray shrink-0">95% CI</dt>
                  <dd className="font-data-mono text-right text-[11px]">
                    {formatCi(ci.point, ci.ci_low, ci.ci_high)}
                  </dd>
                </div>
              )}
            </dl>
          </div>
        ))}
      </section>

      {deltaCi && (
        <section className="bg-surface-container-low border-l-2 border-slate-gray p-4 max-w-3xl">
          <h2 className="font-label-caps text-on-surface mb-2 flex items-center gap-2">
            <Icon name="balance" className="text-[18px]" />
            XGBoost − Elo (log loss)
          </h2>
          <p className="text-body-sm text-on-surface-variant">
            Point estimate{' '}
            <span className="font-data-mono text-primary">{deltaCi.point.toFixed(4)}</span>
            {' · '}
            95% CI{' '}
            <span className="font-data-mono">
              [{deltaCi.ci_low.toFixed(4)}, {deltaCi.ci_high.toFixed(4)}]
            </span>
            {deltaCi.ci_low < 0 && deltaCi.ci_high > 0
              ? '. The interval includes zero; the edge over Elo is real but marginal.'
              : '.'}{' '}
            Bootstrap n={deltaCi.n_bootstrap.toLocaleString()}.
          </p>
        </section>
      )}

      <section className="flex flex-col gap-4">
        <h2 className="text-headline-sm text-primary flex items-center gap-2">
          <Icon name="science" className="text-pitch-green" />
          Ablation grid
        </h2>
        <div className="overflow-x-auto border border-outline-variant rounded bg-surface-container-lowest">
          <table className="w-full text-left border-collapse min-w-[720px]">
            <thead className="bg-surface-container-low border-b border-outline-variant">
              <tr>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant">Config</th>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant text-right">Features</th>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant text-right">Train n</th>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant text-right">XGB log loss</th>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant text-right">XGB acc</th>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant text-right">Elo log loss</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant text-body-sm">
              {experiments.map((e) => (
                <tr
                  key={e.label}
                  className={
                    e.label === meta.selected_config
                      ? 'bg-surface-container-low border-l-2 border-pitch-green'
                      : 'hover:bg-surface-container'
                  }
                >
                  <td className="py-2.5 px-4 font-medium text-primary">
                    {e.label}
                    {e.label === meta.selected_config && (
                      <span className="ml-2 font-label-caps text-pitch-green">production</span>
                    )}
                  </td>
                  <td className="py-2.5 px-4 text-right font-data-mono">{e.n_features}</td>
                  <td className="py-2.5 px-4 text-right font-data-mono">{e.n_train.toLocaleString()}</td>
                  <td className="py-2.5 px-4 text-right font-data-mono">{e.xgb_metrics.log_loss.toFixed(4)}</td>
                  <td className="py-2.5 px-4 text-right font-data-mono">{pct(e.xgb_metrics.accuracy)}</td>
                  <td className="py-2.5 px-4 text-right font-data-mono">
                    {e.baseline_metrics.log_loss.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <div className="flex flex-col gap-4">
          <h2 className="text-headline-sm text-primary flex items-center gap-2">
            <Icon name="bar_chart" className="text-pitch-green" />
            Permutation importance
          </h2>
          <p className="text-body-sm text-on-surface-variant -mt-2">
            Mean Δ log loss when the feature is shuffled on the test set.
          </p>
          <ImportanceBars
            rows={perm.map((f) => ({
              feature: f.feature,
              value: f.delta_log_loss_mean,
              sub: `± ${f.delta_log_loss_std.toFixed(4)}`,
            }))}
            formatValue={(v) => `+${v.toFixed(4)}`}
          />
        </div>
        <div className="flex flex-col gap-4">
          <h2 className="text-headline-sm text-primary flex items-center gap-2">
            <Icon name="account_tree" className="text-pitch-green" />
            XGBoost gain (production)
          </h2>
          <p className="text-body-sm text-on-surface-variant -mt-2">
            Split gain from the refit production model weights.
          </p>
          <ImportanceBars
            rows={gains.map((f) => ({ feature: f.feature, value: f.gain }))}
            formatValue={(v) => v.toFixed(4)}
          />
        </div>
      </section>

      {meta.calibration && (
        <section className="flex flex-col gap-4">
          <h2 className="text-headline-sm text-primary flex items-center gap-2">
            <Icon name="ssid_chart" className="text-pitch-green" />
            Calibration
          </h2>
          <p className="text-body-sm text-on-surface-variant max-w-2xl">
            Reliability by outcome class on the competitive holdout. Points on the diagonal are
            well calibrated; draw mass never exceeds ~0.40.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter">
            {OUTCOME_LABELS.map((key) => {
              const bins = meta.calibration?.[key]
              if (!bins?.length) return null
              return <CalibrationChart key={key} bins={bins} title={OUTCOME_TITLES[key]} />
            })}
          </div>
        </section>
      )}

      {meta.error_analysis && meta.error_analysis.length > 0 && (
        <section className="flex flex-col gap-4">
          <h2 className="text-headline-sm text-primary flex items-center gap-2">
            <Icon name="filter_alt" className="text-pitch-green" />
            Error slices
          </h2>
          <p className="text-body-sm text-on-surface-variant max-w-2xl">
            Close Elo matches drive most of the loss; draws are calibrated in probability but rarely
            the argmax class.
          </p>
          <ErrorSlicesTable rows={meta.error_analysis} />
        </section>
      )}

      {meta.sample_predictions && meta.sample_predictions.length > 0 && (
        <section className="flex flex-col gap-4">
          <h2 className="text-headline-sm text-primary flex items-center gap-2">
            <Icon name="sports_soccer" className="text-pitch-green" />
            Sample predictions
          </h2>
          <p className="text-body-sm text-on-surface-variant max-w-2xl">
            Curated examples from the holdout (plus live symmetry checks where present).
          </p>
          <SampleCards samples={meta.sample_predictions} />
        </section>
      )}
    </main>
  )
}
