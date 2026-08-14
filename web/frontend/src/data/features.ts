import type { FeatureGlossaryItem } from '../types'

export const FEATURE_GLOSSARY: FeatureGlossaryItem[] = [
  {
    name: 'elo_diff',
    category: 'Team strength',
    description: 'Home Elo minus away Elo before kickoff (tiered K, +100 home offset on non-neutral).',
    point_in_time: 'Uses only matches strictly before the fixture date.',
    missingness: 'Always present after Elo warm-up.',
  },
  {
    name: 'home_elo / away_elo',
    category: 'Team strength',
    description: 'Absolute Elo ratings for each side.',
    point_in_time: 'Updated after every prior match; shootouts count as draws for ratings.',
    missingness: 'None for teams with history.',
  },
  {
    name: 'form_*_diff (5 / 10)',
    category: 'Momentum',
    description: 'Differences in points, GD, GF, GA over last 5 and last 10 matches.',
    point_in_time: 'Rolling windows end at the prior match.',
    missingness: 'Sparse early careers; XGBoost handles NaN.',
  },
  {
    name: 'home_days_since_last / away_days_since_last',
    category: 'Rest',
    description: 'Days of rest / inactivity before the match.',
    point_in_time: 'Computed from previous fixture dates only.',
    missingness: 'NaN for first known match.',
  },
  {
    name: 'neutral',
    category: 'Context',
    description: '1 if neutral venue; triggers mirror-and-average at inference.',
    point_in_time: 'Known from schedule / venue metadata.',
    missingness: 'None.',
  },
  {
    name: 'squad_value_log_*',
    category: 'Economic proxy',
    description: 'log1p of top-25 citizenship market-value sum (Transfermarkt proxy).',
    point_in_time: 'Latest valuation within prior 18 months as of match date.',
    missingness: 'Pre-2004 and some smaller nations; dual-national bias known.',
  },
  {
    name: 'market_implied_*',
    category: 'Market (optional)',
    description: 'Bookmaker-implied W/D/L probabilities when present in production config.',
    point_in_time: 'Prematch odds as of cutoff.',
    missingness: 'Often missing outside major tournaments.',
  },
]
