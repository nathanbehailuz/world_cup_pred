import { Link } from 'react-router-dom'
import { Icon } from '../components/Icon'

const ITEMS = [
  {
    title: 'Label mixture',
    body: 'Targets mix 90-minute results with ET/penalty advancement. Knockouts cannot draw; the same on-field level score is labeled differently by format.',
  },
  {
    title: 'Squad value proxy',
    body: 'Citizenship top-25 market values ignore dual-national choices and undervalue some defensive roles; smaller nations may have stale data.',
  },
  {
    title: 'Untuned hyperparameters',
    body: 'XGBoost uses sensible defaults (depth 4, 300 trees). Hyperparameter search is deferred.',
  },
  {
    title: 'Holdout reuse',
    body: 'The competitive 2023+ set is used for both model selection ablations and reported metrics. Confidence intervals help, but selection bias remains.',
  },
  {
    title: 'No in-match context',
    body: 'No injuries, lineups, travel, or weather. Strength is encoded only through historical features.',
  },
  {
    title: 'Deferred work',
    body: 'Poisson goals, per-match SHAP, rolling CV, and confederation slices are on the research backlog.',
  },
]

export function LimitationsPage() {
  return (
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8 md:py-12 flex flex-col gap-10">
      <header className="border-b border-outline-variant pb-6 max-w-3xl">
        <h1 className="text-headline-lg text-primary">Limitations &amp; Future Work</h1>
        <p className="text-body-md text-on-surface-variant mt-2">
          Honest research framing. Prefer “log loss on competitive 2023+ holdout” over “we predict
          the World Cup.”
        </p>
      </header>

      <ul className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl">
        {ITEMS.map((item) => (
          <li key={item.title} className="border-t border-outline-variant pt-4">
            <h2 className="text-headline-sm text-primary flex items-center gap-2 mb-2">
              <Icon name="report" className="text-slate-gray text-[20px]" />
              {item.title}
            </h2>
            <p className="text-body-md text-on-surface-variant">{item.body}</p>
          </li>
        ))}
      </ul>

      <p className="text-body-sm text-on-surface-variant">
        Methodology write-up:{' '}
        <Link to="/methodology" className="text-pitch-green hover:underline">
          /methodology
        </Link>
      </p>
    </main>
  )
}
