import { Link } from 'react-router-dom'

export function AboutPage() {
  return (
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8 md:py-12">
      <article className="max-w-2xl flex flex-col gap-8 animate-fade-up">
        <header className="border-b border-outline-variant pb-6">
          <h1 className="text-headline-lg text-primary">About</h1>
          <p className="text-body-md text-on-surface-variant mt-2">
            WC 2026 Predictor is an open research project that forecasts international match
            outcomes as calibrated probability vectors from point-in-time features.
          </p>
        </header>

        <section className="space-y-3">
          <h2 className="text-headline-sm text-primary">Data credits</h2>
          <ul className="list-disc pl-5 text-body-md text-on-surface-variant space-y-2">
            <li>
              <a
                className="text-pitch-green hover:underline"
                href="https://github.com/martj42/international_results"
                target="_blank"
                rel="noreferrer"
              >
                martj42/international_results
              </a>{' '}
              — match history &amp; shootouts
            </li>
            <li>
              <a
                className="text-pitch-green hover:underline"
                href="https://github.com/transfermarkt-datasets"
                target="_blank"
                rel="noreferrer"
              >
                transfermarkt-datasets
              </a>{' '}
              — squad market values
            </li>
            <li>eloratings.net-style tiered K for Elo updates</li>
            <li>Official FIFA three-letter codes</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-headline-sm text-primary">Stack</h2>
          <p className="text-body-md text-on-surface-variant">
            Python pipeline (download → features → XGBoost → predict), SQLite feature store. This
            site: React + Vite + Tailwind. Predict/evaluate APIs will wrap{' '}
            <code className="font-mono">pipeline/</code> under <code className="font-mono">web/api/</code>.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-headline-sm text-primary">Disclaimer</h2>
          <p className="text-body-md text-on-surface-variant">
            Probabilities are for research and education. They are not betting advice. See{' '}
            <Link to="/limitations" className="text-pitch-green hover:underline">
              Limitations
            </Link>
            .
          </p>
        </section>
      </article>
    </main>
  )
}
