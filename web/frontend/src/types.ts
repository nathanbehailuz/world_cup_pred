/** Shared domain types — mirror expected API contracts from docs/WEBSITE.md */

export type Outcome = 'home_win' | 'draw' | 'away_win'
export type VenueMode = 'neutral' | 'home_a' | 'wc_venue'

export interface Team {
  code: string
  name: string
}

export interface ProbabilityVector {
  p_a: number
  p_draw: number
  p_b: number
}

export interface PredictRequest {
  team_a: string
  team_b: string
  venue: VenueMode
  as_of: string
}

export interface FeatureSnapshot {
  metric: string
  team_a: string | number
  team_b: string | number
}

export interface PredictResponse {
  team_a: Team
  team_b: Team
  venue: VenueMode
  as_of: string
  feature_cutoff: string
  probabilities: ProbabilityVector
  favorite: 'A' | 'Draw' | 'B'
  confidence: number
  features: FeatureSnapshot[]
  top_importance: { feature: string; value: number }[]
  disclaimer: string
  source: 'mock' | 'api'
}

export interface HoldoutMatch {
  id: string
  date: string
  team_a: string
  team_b: string
  team_a_code: string
  team_b_code: string
  tournament: string
  competitive: boolean
  probabilities: ProbabilityVector
  predicted: Outcome
  actual: Outcome
  actual_label: string
  correct: boolean
  log_loss: number
  elo_gap: number
  score?: string
  narrative?: string
}

export interface HoldoutFilters {
  tournament?: string
  confidence?: 'any' | 'high' | 'medium' | 'low'
  correctness?: 'all' | 'correct' | 'incorrect'
  search?: string
}

export interface HoldoutSummary {
  n: number
  accuracy: number
  mean_log_loss: number
  vs_baseline_accuracy_delta: number
  confusion: number[][]
}

export interface WcFixture {
  date: string
  home_team: string
  away_team: string
  home_advantage: string
  round: string | null
  group_name: string | null
  stage: string
  home_score: number | null
  away_score: number | null
  actual_outcome: Outcome | null
  p_home: number
  p_draw: number
  p_away: number
  predicted_outcome: Outcome
  correct: boolean | null
  status: 'upcoming' | 'final'
}

export interface ModelBaselines {
  constant_prior: { log_loss: number; brier_score: number; accuracy: number }
  elo_logistic: { log_loss: number; brier_score: number; accuracy: number }
  production_xgboost: { log_loss: number; brier_score: number; accuracy: number }
}

export interface ModelMeta {
  feature_cutoff: string
  train_cutoff: string
  min_match_date: string
  selected_config: string
  production_fit_rows: number
  production_fit_through: string
  baselines: ModelBaselines
  bootstrap_ci: Record<
    string,
    { point: number; ci_low: number; ci_high: number; n_bootstrap: number }
  >
  feature_importance: {
    permutation: { feature: string; delta_log_loss_mean: number; delta_log_loss_std: number }[]
    gain: { feature: string; gain: number }[]
  }
  experiments: {
    label: string
    competitive_only: boolean
    n_features: number
    n_train: number
    n_test: number
    baseline_metrics: { log_loss: number; brier_score: number; accuracy: number }
    xgb_metrics: { log_loss: number; brier_score: number; accuracy: number }
  }[]
  feature_columns: string[]
}

export interface FeatureGlossaryItem {
  name: string
  category: string
  description: string
  point_in_time: string
  missingness: string
}
