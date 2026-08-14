import { useEffect, useState } from 'react'
import { getModelMeta } from '../api/client'
import { Icon } from '../components/Icon'
import { formatCi, pct } from '../lib/format'
import type { ModelMeta } from '../types'

export function ResultsPage() {
  const [meta, setMeta] = useState<ModelMeta | null>(null)

  useEffect(() => {
    void getModelMeta().then(setMeta)
  }, [])

  if (!meta) {
    return (
      <main className="flex-grow max-w-container-max mx-auto px-margin-desktop py-12 text-on-surface-variant">
        Loading model metadata…
      </main>
    )
  }

  const { baselines, bootstrap_ci, feature_importance, experiments } = meta
  const maxPerm = Math.max(...feature_importance.permutation.map((f) => f.delta_log_loss_mean), 0.001)

  return (
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8 md:py-12 flex flex-col gap-12">
      <header className="border-b border-outline-variant pb-6 animate-fade-up">
        <h1 className="text-headline-lg text-primary">Model Performance</h1>
        <p className="text-body-md text-on-surface-variant mt-2 max-w-2xl">
          Numbers from <code className="font-mono">model_meta.json</code> — competitive 2023+ holdout.
          Methodology stays prose-first; this page is the scoreboard.
        </p>
        <p className="font-label-caps text-slate-gray mt-3">
          As of cutoff {meta.feature_cutoff} · config {meta.selected_config}
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

      <section className="flex flex-col gap-4">
        <h2 className="text-headline-sm text-primary flex items-center gap-2">
          <Icon name="science" className="text-pitch-green" />
          Ablation grid
        </h2>
        <div className="overflow-x-auto border border-outline-variant rounded bg-surface-container-lowest">
          <table className="w-full text-left border-collapse min-w-[640px]">
            <thead className="bg-surface-container-low border-b border-outline-variant">
              <tr>
                <th className="py-3 px-4 font-label-caps text-on-surface-variant">Config</th>
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
                  <td className="py-2.5 px-4 text-right font-data-mono">{e.n_train.toLocaleString()}</td>
                  <td className="py-2.5 px-4 text-right font-data-mono">{e.xgb_metrics.log_loss.toFixed(4)}</td>
                  <td className="py-2.5 px-4 text-right font-data-mono">{pct(e.xgb_metrics.accuracy)}</td>
                  <td className="py-2.5 px-4 text-right font-data-mono">{e.baseline_metrics.log_loss.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-headline-sm text-primary flex items-center gap-2">
          <Icon name="bar_chart" className="text-pitch-green" />
          Permutation importance (Δ log loss)
        </h2>
        <ul className="flex flex-col gap-3 max-w-2xl">
          {feature_importance.permutation.slice(0, 10).map((f, i) => (
            <li key={f.feature} className="flex flex-col gap-1">
              <div className="flex justify-between text-body-sm">
                <span className="font-medium text-primary">{f.feature}</span>
                <span className="font-data-mono text-slate-gray">
                  +{f.delta_log_loss_mean.toFixed(4)} ± {f.delta_log_loss_std.toFixed(4)}
                </span>
              </div>
              <div className="h-2 bg-surface-variant rounded overflow-hidden">
                <div
                  className="h-full bg-pitch-green origin-left animate-bar-grow"
                  style={{
                    width: `${(f.delta_log_loss_mean / maxPerm) * 100}%`,
                    animationDelay: `${i * 40}ms`,
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}
