import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getModelMeta, getWc2026Fixtures } from '../api/client'
import { ProbabilityBar } from '../components/ProbabilityBar'
import { Icon } from '../components/Icon'
import { TeamLabel } from '../components/TeamFlag'
import { pct } from '../lib/format'
import type { ModelMeta, WcFixture } from '../types'

export function HomePage() {
  const [meta, setMeta] = useState<ModelMeta | null>(null)
  const [featured, setFeatured] = useState<WcFixture[]>([])

  useEffect(() => {
    void getModelMeta().then(setMeta)
    void getWc2026Fixtures('group').then((r) => setFeatured(r.fixtures.slice(18, 21)))
  }, [])

  const xgb = meta?.baselines.production_xgboost
  const elo = meta?.baselines.elo_logistic

  return (
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-12 flex flex-col gap-24">
      {/* Hero — brand + headline + support + CTAs + metric plane */}
      <section className="grid grid-cols-1 md:grid-cols-12 gap-8 items-center pt-4 md:pt-8">
        <div className="md:col-span-7 flex flex-col gap-6 animate-fade-up">
          <p className="font-label-caps text-pitch-green">WC 2026 Predictor</p>
          <h1 className="text-headline-lg font-bold text-primary">
            World Cup 2026: Probabilistic Match Forecasts
          </h1>
          <p className="text-body-lg text-on-surface-variant max-w-2xl">
            Point-in-time W/D/L probabilities for international fixtures from Elo, form, and squad
            value — not hard labels.
          </p>
          <div className="flex flex-wrap gap-4 pt-2">
            <Link
              to="/predict"
              className="bg-deep-navy text-on-primary px-6 py-3 rounded text-label-caps font-label-caps hover:opacity-90 transition-opacity"
            >
              Predict a Match
            </Link>
            <Link
              to="/methodology"
              className="border border-outline px-6 py-3 rounded text-label-caps font-label-caps text-primary hover:bg-surface-variant transition-colors"
            >
              View Methodology
            </Link>
          </div>
        </div>
        <div className="md:col-span-5 grid grid-cols-2 gap-4 animate-fade-in" style={{ animationDelay: '120ms' }}>
          <div className="col-span-2 bg-surface-container-lowest border border-surface-variant rounded p-6 flex flex-col gap-2">
            <span className="font-label-caps text-on-surface-variant">Model Architecture</span>
            <span className="text-headline-md text-pitch-green font-mono">XGBoost softprob</span>
          </div>
          <div className="bg-surface-container-lowest border border-surface-variant rounded p-6 flex flex-col gap-2">
            <span className="font-label-caps text-on-surface-variant">Holdout size</span>
            <span className="text-headline-sm text-primary font-mono">2,245+</span>
            <span className="text-body-sm text-on-surface-variant">Competitive 2023+</span>
          </div>
          <div className="bg-surface-container-lowest border border-surface-variant rounded p-6 flex flex-col gap-2">
            <span className="font-label-caps text-on-surface-variant">Log loss</span>
            <span className="text-headline-sm text-data-pos font-mono">
              {xgb ? xgb.log_loss.toFixed(3) : '—'}
            </span>
            <span className="text-body-sm text-on-surface-variant">
              vs Elo {elo ? elo.log_loss.toFixed(3) : '—'}
            </span>
          </div>
          <div className="col-span-2 bg-surface-container-lowest border border-surface-variant rounded p-4 flex items-center justify-between">
            <span className="text-body-sm text-on-surface-variant flex items-center gap-2">
              <Icon name="check_circle" className="text-pitch-green text-[18px]" />
              Competitive test set (2023+) verified
            </span>
          </div>
        </div>
      </section>

      {/* What we predict */}
      <section className="flex flex-col gap-4 max-w-3xl">
        <h2 className="text-headline-sm text-primary">What we predict</h2>
        <p className="text-body-md text-on-surface-variant">
          A probability vector over Team A win / Draw / Team B win. Argmax is secondary — draws are
          common but rarely the single most likely class. Knockout fixtures use advancement labels
          (ET/penalties); group draws remain possible.{' '}
          <Link to="/methodology" className="text-pitch-green hover:underline">
            Read the methodology
          </Link>
          .
        </p>
      </section>

      {/* Featured fixtures */}
      <section className="flex flex-col gap-6">
        <div className="flex justify-between items-end border-b border-surface-variant pb-2">
          <h2 className="text-headline-sm text-primary">Featured Forecasts</h2>
          <Link to="/predict" className="font-label-caps text-pitch-green hover:underline">
            View All Fixtures
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {featured.map((f, i) => (
            <div
              key={`${f.date}-${f.home_team}-${f.away_team}`}
              className="bg-surface-container-lowest border border-surface-variant rounded p-5 flex flex-col gap-6 hover:border-outline-variant transition-colors"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <div className="flex justify-between items-center text-body-sm text-on-surface-variant">
                <span>
                  {f.group_name || 'Group stage'} · {f.date}
                </span>
                <span className="font-mono bg-surface-container px-2 py-1 rounded text-[10px]">
                  {f.status}
                </span>
              </div>
              <div className="flex justify-between items-center gap-2">
                <TeamLabel
                  name={f.home_team}
                  size="md"
                  className="flex-1 min-w-0"
                  nameClassName="text-body-lg font-semibold"
                />
                <span className="text-headline-md text-slate-gray shrink-0">vs</span>
                <TeamLabel
                  name={f.away_team}
                  size="md"
                  className="flex-1 min-w-0 justify-end"
                  nameClassName="text-body-lg font-semibold text-right"
                />
              </div>
              <ProbabilityBar
                probabilities={{ p_a: f.p_home, p_draw: f.p_draw, p_b: f.p_away }}
                labelA={f.home_team}
                labelB={f.away_team}
              />
            </div>
          ))}
        </div>
      </section>

      {/* Pipeline */}
      <section className="flex flex-col gap-8 pb-4">
        <h2 className="text-headline-sm text-primary text-center">Prediction Pipeline</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
          <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-px bg-outline-variant z-0" />
          {[
            {
              icon: 'database',
              title: 'Data Ingestion',
              body: 'Historical international results and shootouts, point-in-time through the match cutoff.',
            },
            {
              icon: 'hub',
              title: 'Feature Engineering',
              body: 'Elo (tiered K), rolling form, rest days, neutral flag, and squad market-value proxy.',
            },
            {
              icon: 'model_training',
              title: 'XGBoost Inference',
              body: 'multi:softprob with neutral mirror-and-average — calibrated W/D/L probabilities.',
            },
          ].map((step) => (
            <div key={step.title} className="bg-surface flex flex-col items-center text-center gap-4 z-10 p-4">
              <div className="w-24 h-24 bg-surface-container-lowest border border-surface-variant rounded-full flex items-center justify-center">
                <Icon name={step.icon} className="text-4xl text-pitch-green" />
              </div>
              <h3 className="text-body-lg font-bold text-primary">{step.title}</h3>
              <p className="text-body-sm text-on-surface-variant">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA row */}
      <section className="border-t border-surface-variant pt-10 flex flex-col md:flex-row gap-4 justify-center items-center pb-8">
        <Link
          to="/predict"
          className="bg-deep-navy text-on-primary px-6 py-3 rounded font-label-caps hover:opacity-90"
        >
          Predict a match
        </Link>
        <Link
          to="/evaluate"
          className="border border-outline px-6 py-3 rounded font-label-caps hover:bg-surface-variant"
        >
          See where we were wrong
        </Link>
        <Link to="/analysis" className="font-label-caps text-pitch-green hover:underline px-2">
          Model analysis →
        </Link>
      </section>

      {meta && (
        <p className="text-body-sm text-on-surface-variant text-center -mt-16">
          As of cutoff {meta.feature_cutoff} · production log loss {xgb?.log_loss.toFixed(3)} on
          competitive holdout · accuracy {xgb ? pct(xgb.accuracy) : '—'}
        </p>
      )}
    </main>
  )
}
