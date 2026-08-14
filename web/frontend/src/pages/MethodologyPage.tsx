import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Icon } from '../components/Icon'
import { LabelCallout } from '../components/LabelCallout'

const SECTIONS = [
  { id: 'abstract', label: 'Abstract' },
  { id: 'problem-formulation', label: 'Problem Formulation' },
  { id: 'data', label: 'Data Acquisition' },
  { id: 'feature-engineering', label: 'Feature Engineering' },
  { id: 'model', label: 'Model Architecture' },
  { id: 'evaluation', label: 'Evaluation Metrics' },
  { id: 'limitations', label: 'Limitations' },
  { id: 'reproducibility', label: 'Reproducibility' },
]

export function MethodologyPage() {
  const [active, setActive] = useState('abstract')

  useEffect(() => {
    const sections = document.querySelectorAll('article section[id]')
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActive(entry.target.id)
        })
      },
      { rootMargin: '-20% 0px -80% 0px', threshold: 0 },
    )
    sections.forEach((s) => observer.observe(s))
    return () => observer.disconnect()
  }, [])

  return (
    <main className="w-full px-margin-mobile md:px-margin-desktop max-w-container-max mx-auto py-8 lg:py-12">
      <div className="grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-gutter relative">
        <aside className="hidden lg:block lg:col-span-3 relative">
          <nav className="sticky top-24 flex flex-col gap-2 border-l border-outline-variant py-2 pl-4" id="section-nav">
            <span className="font-label-caps text-on-surface-variant mb-2 px-2">Contents</span>
            {SECTIONS.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className={
                  active === s.id
                    ? 'font-body-sm text-body-sm text-pitch-green font-bold border-l-2 border-pitch-green -ml-[17px] pl-[15px] py-1 bg-surface-container-lowest'
                    : 'font-body-sm text-body-sm text-on-surface-variant hover:text-primary transition-colors py-1 px-2'
                }
              >
                {s.label}
              </a>
            ))}
          </nav>
        </aside>

        <article className="col-span-4 md:col-span-8 lg:col-span-9 space-y-16">
          <header className="border-b border-outline-variant pb-8 animate-fade-up">
            <h1 className="text-headline-lg text-on-surface mb-2">Research Methodology</h1>
            <p className="text-body-md text-on-surface-variant max-w-3xl">
              A rigorous approach to international football outcomes, prioritizing continuous
              probability distributions over hard classification.
            </p>
          </header>

          <section className="space-y-4" id="abstract">
            <h2 className="text-headline-md text-on-surface flex items-center gap-2">
              <Icon name="description" className="text-pitch-green text-xl" />
              Abstract
            </h2>
            <div className="bg-surface-container-lowest border border-outline-variant rounded p-6">
              <p className="text-body-md text-on-surface-variant leading-relaxed">
                We forecast three-way match outcomes (Team A win / Draw / Team B win) as a
                probability vector from point-in-time features: Elo ratings, rolling form, rest,
                venue, and a squad market-value proxy. An XGBoost <code className="font-mono text-pitch-green">multi:softprob</code>{' '}
                model is trained on international results from 1990 onward and evaluated on a
                temporal holdout of competitive matches from 2023+. Primary metric is log loss versus
                constant-prior and Elo-logistic baselines. Neutral venues are mirror-averaged for
                slot symmetry.
              </p>
            </div>
          </section>

          <section className="space-y-4" id="problem-formulation">
            <h2 className="text-headline-md text-on-surface flex items-center gap-2">
              <Icon name="function" className="text-pitch-green text-xl" />
              Problem Formulation
            </h2>
            <p className="text-body-md text-on-surface-variant leading-relaxed">
              Map a feature vector for two national teams and venue to p = (p<sub>A</sub>, p<sub>D</sub>, p<sub>B</sub>).
              We reject hard labels in favor of soft probabilities — draws occur often but are rarely
              the argmax. A single global model encodes strength via features, not team identity.
            </p>
            <LabelCallout />
            <div className="bg-surface-container-low border-l-2 border-slate-gray p-4 my-6">
              <h4 className="font-label-caps text-on-surface mb-2">Notation &amp; Objective</h4>
              <p className="font-data-mono text-on-surface-variant text-sm bg-surface-container-lowest p-3 border border-outline-variant rounded overflow-x-auto">
                Let x_i ∈ ℝ^d be features for match i.
                <br />
                Let y_i be the one-hot outcome; f(x_i; θ) outputs p_i with Σ p = 1.
                <br />
                <br />
                Minimize L(θ) = −(1/N) Σ [ y^H log p^H + y^D log p^D + y^A log p^A ]
              </p>
            </div>
          </section>

          <section className="space-y-4" id="data">
            <h2 className="text-headline-md text-on-surface flex items-center gap-2">
              <Icon name="dataset" className="text-pitch-green text-xl" />
              Data Acquisition
            </h2>
            <p className="text-body-md text-on-surface-variant leading-relaxed">
              Primary source: martj42 international results + shootouts. Cleaning drops unplayed
              fixtures, normalizes aliases, deduplicates, and joins shootout winners. Model fitting
              uses 1990+; Elo consumes the full history. Squad values come from transfermarkt-datasets
              quarterly snapshots (top-25 citizenship proxy).
            </p>
          </section>

          <section className="space-y-6" id="feature-engineering">
            <h2 className="text-headline-md text-on-surface flex items-center gap-2">
              <Icon name="manufacturing" className="text-pitch-green text-xl" />
              Feature Engineering
            </h2>
            <p className="text-body-md text-on-surface-variant leading-relaxed">
              All features are point-in-time: only matches strictly before each fixture date.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse bg-surface-container-lowest border border-outline-variant rounded text-left">
                <caption className="font-label-caps text-on-surface-variant text-left p-4 border-b border-outline-variant bg-surface-container-low">
                  Table 1: Primary Feature Families
                </caption>
                <thead>
                  <tr>
                    <th className="font-label-caps text-on-surface border-b border-outline-variant px-4 py-3 bg-surface">Feature</th>
                    <th className="font-label-caps text-on-surface border-b border-outline-variant px-4 py-3 bg-surface">Category</th>
                    <th className="font-label-caps text-on-surface border-b border-outline-variant px-4 py-3 bg-surface">Description</th>
                  </tr>
                </thead>
                <tbody className="text-body-sm text-on-surface-variant">
                  {[
                    ['Elo Rating Diff', 'Strength', 'Tiered K Elo difference; +100 home offset off neutral.'],
                    ['Rolling Form (5/10)', 'Momentum', 'Points, GD, GF, GA differences over recent windows.'],
                    ['Squad Value (log)', 'Economic', 'log1p top-25 market-value proxy (Transfermarkt).'],
                    ['Rest days', 'Context', 'Days since each side’s previous match.'],
                    ['Neutral / venue', 'Context', 'Neutral flag; WC host inference for USA/MEX/CAN.'],
                  ].map(([a, b, c]) => (
                    <tr key={a} className="hover:bg-surface-container-highest border-b border-outline-variant">
                      <td className="px-4 py-3 font-medium text-on-surface">{a}</td>
                      <td className="px-4 py-3">{b}</td>
                      <td className="px-4 py-3">{c}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-body-sm text-on-surface-variant">
              Full glossary:{' '}
              <Link to="/features" className="text-pitch-green hover:underline">
                Features &amp; data
              </Link>
              .
            </p>
          </section>

          <section className="space-y-4" id="model">
            <h2 className="text-headline-md text-on-surface flex items-center gap-2">
              <Icon name="model_training" className="text-pitch-green text-xl" />
              Model Architecture
            </h2>
            <p className="text-body-md text-on-surface-variant leading-relaxed">
              Baselines: constant prior and Elo multinomial logistic. Production: XGBoost
              multi:softprob (untuned defaults). On neutral ground, predictions are computed for both
              slot orderings and averaged after swapping win probabilities.
            </p>
            <div className="grid md:grid-cols-2 gap-4 mt-4">
              <div className="bg-surface-container-lowest border border-outline-variant p-4 rounded">
                <h4 className="font-label-caps text-on-surface mb-2">Algorithm</h4>
                <p className="font-data-mono text-pitch-green">XGBoost · multi:softprob</p>
              </div>
              <div className="bg-surface-container-lowest border border-outline-variant p-4 rounded">
                <h4 className="font-label-caps text-on-surface mb-2">Symmetrization</h4>
                <p className="text-body-sm text-on-surface-variant">
                  Neutral mirror-and-average removes arbitrary home/away slot assignment.
                </p>
              </div>
            </div>
          </section>

          <section className="space-y-6" id="evaluation">
            <h2 className="text-headline-md text-on-surface flex items-center gap-2">
              <Icon name="analytics" className="text-pitch-green text-xl" />
              Evaluation Metrics
            </h2>
            <p className="text-body-md text-on-surface-variant leading-relaxed">
              Temporal split: train ≤2022, test 2023+. Shared competitive test set. Primary metric:
              log loss; also Brier and accuracy, with bootstrap CIs. Charts and ablation tables live
              on the{' '}
              <Link to="/results" className="text-pitch-green hover:underline">
                Results
              </Link>{' '}
              page.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse bg-surface-container-lowest border border-outline-variant rounded text-left">
                <caption className="font-label-caps text-on-surface-variant text-left p-4 border-b border-outline-variant bg-surface-container-low">
                  Table 2: Baseline comparison (competitive 2023+ holdout)
                </caption>
                <thead>
                  <tr>
                    <th className="font-label-caps border-b border-outline-variant px-4 py-3 bg-surface">Model</th>
                    <th className="font-label-caps border-b border-outline-variant px-4 py-3 bg-surface text-right">Log Loss ↓</th>
                    <th className="font-label-caps border-b border-outline-variant px-4 py-3 bg-surface text-right">Accuracy</th>
                  </tr>
                </thead>
                <tbody className="font-data-mono text-on-surface-variant">
                  <tr className="border-b border-outline-variant">
                    <td className="px-4 py-3 font-sans text-body-sm text-on-surface">Constant prior</td>
                    <td className="px-4 py-3 text-right">1.047</td>
                    <td className="px-4 py-3 text-right">47.3%</td>
                  </tr>
                  <tr className="border-b border-outline-variant">
                    <td className="px-4 py-3 font-sans text-body-sm text-on-surface">Elo logistic</td>
                    <td className="px-4 py-3 text-right">0.838</td>
                    <td className="px-4 py-3 text-right">62.6%</td>
                  </tr>
                  <tr className="bg-surface-container-low border-l-2 border-pitch-green">
                    <td className="px-4 py-3 font-sans text-body-sm font-bold text-pitch-green flex items-center gap-2">
                      <Icon name="check_circle" className="text-sm" />
                      Production XGBoost
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-on-surface">0.832</td>
                    <td className="px-4 py-3 text-right font-bold text-on-surface">63.4%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="space-y-4" id="limitations">
            <h2 className="text-headline-md text-on-surface flex items-center gap-2">
              <Icon name="warning" className="text-pitch-green text-xl" />
              Limitations
            </h2>
            <p className="text-body-md text-on-surface-variant leading-relaxed">
              Label mixture (90′ vs ET/penalties), squad-value dual-national bias, untuned
              hyperparameters, and holdout reuse for model selection. Full caveats:{' '}
              <Link to="/limitations" className="text-pitch-green hover:underline">
                Limitations
              </Link>
              .
            </p>
          </section>

          <section className="space-y-4" id="reproducibility">
            <h2 className="text-headline-md text-on-surface flex items-center gap-2">
              <Icon name="terminal" className="text-pitch-green text-xl" />
              Reproducibility
            </h2>
            <p className="text-body-md text-on-surface-variant leading-relaxed">
              Pipeline stages live under <code className="font-mono">pipeline/</code>: download →
              features → train → predict. Cutoffs and seed are recorded in{' '}
              <code className="font-mono">models/model_meta.json</code>. See the repo README for
              commands.
            </p>
          </section>
        </article>
      </div>
    </main>
  )
}
