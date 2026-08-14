/** Shared domain types — mirror expected API contracts from docs/WEBSITE.md */

export type Outcome = 'home_win' | 'draw' | 'away_win'
export type VenueMode = 'neutral' | 'home_a' | 'wc_venue'
export type MatchStatus = 'upcoming' | 'final'

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
}

export interface FeatureSnapshot {
  metric: string
  team_a: string | number | null
  team_b: string | number | null
}

/** Live WC simulation row — same fields as Evaluate, plus venue/status. */
export interface SimMatch {
  id: string
  match_number?: number
  date: string
  location?: string
  team_a: string
  team_b: string
  team_a_code: string
  team_b_code: string
  tournament: string
  group_name?: string | null
  round?: string | null
  competitive: boolean
  neutral?: boolean
  venue_label?: string
  probabilities: ProbabilityVector
  predicted: Outcome
  actual: Outcome | null
  actual_label: string | null
  correct: boolean | null
  log_loss: number | null
  elo_gap: number
  score?: string | null
  status: MatchStatus
  narrative?: string
  features?: FeatureSnapshot[]
  disclaimer?: string
  source?: 'mock' | 'api'
}

export interface SimSummary {
  n: number
  n_played: number
  accuracy: number
  mean_log_loss: number
  confusion: number[][]
}

export interface WcScheduleFixture {
  match_number: number
  date: string
  location: string
  home_team: string
  away_team: string
  home_code: string
  away_code: string
  round: string | null
  group_name: string | null
  home_score: number | null
  away_score: number | null
  status: MatchStatus
  neutral: boolean
  venue_label: string
}

/** @deprecated Prefer SimMatch for Predict; kept for Evaluate holdout. */
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

export interface HoldoutArtifactMeta {
  train_cutoff: string
  n_matches: number
  feature_columns: string[]
  selected_config: string
  metrics: { log_loss: number; brier_score: number; accuracy: number }
  baseline_accuracy: number
  tournaments: string[]
}

export interface HoldoutArtifact {
  meta: HoldoutArtifactMeta
  matches: HoldoutMatch[]
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

export interface CalibrationBin {
  bin: string
  n: number
  mean_predicted: number
  empirical: number
}

export interface ErrorSlice {
  slice: string
  n: number
  log_loss: number
  brier_score: number
  accuracy: number
  mean_predicted_draw: number
}

export interface SamplePrediction {
  category: string
  date: string | null
  team_a: string
  team_b: string
  neutral: boolean
  elo_diff: number | null
  team_a_win: number
  draw: number
  team_b_win: number
  actual_outcome: number | null
  comment: string
}

export interface ModelMeta {
  feature_cutoff: string
  train_cutoff: string
  min_match_date: string
  selected_config: string
  competitive_only?: boolean
  production_fit_rows: number
  production_fit_through: string
  baselines: ModelBaselines
  bootstrap_ci: Record<
    string,
    { point: number; ci_low: number; ci_high: number; n_bootstrap: number }
  >
  feature_importance: {
    permutation: { feature: string; delta_log_loss_mean: number; delta_log_loss_std: number }[]
    /** @deprecated older frontend exports used a single `gain` list */
    gain?: { feature: string; gain: number }[]
    gain_experiment_model?: { feature: string; gain: number }[]
    gain_production_model?: { feature: string; gain: number }[]
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
  calibration?: Record<string, CalibrationBin[]>
  error_analysis?: ErrorSlice[]
  sample_predictions?: SamplePrediction[]
  outcome_labels?: string[]
}

export interface FeatureGlossaryItem {
  name: string
  category: string
  description: string
  point_in_time: string
  missingness: string
}

export interface MethodologyCallout {
  kind: 'label' | 'notation' | 'note'
  title: string
  body: string
}

export interface MethodologyTableColumn {
  key: string
  label: string
  align?: 'left' | 'right'
}

export interface MethodologyTable {
  caption: string
  columns: MethodologyTableColumn[]
  rows: Record<string, string>[]
  highlightRow?: number
}

export interface MethodologyCard {
  title: string
  body: string
  mono?: boolean
}

export interface MethodologyLink {
  label: string
  to: string
}

export interface MethodologyFootnote {
  id: string
  text: string
  href?: string
}

export interface MethodologySection {
  id: string
  label: string
  title: string
  icon: string
  paragraphs?: string[]
  callouts?: MethodologyCallout[]
  cards?: MethodologyCard[]
  tables?: MethodologyTable[]
  findings?: string[]
  links?: MethodologyLink[]
  commands?: string[]
  footnotes?: MethodologyFootnote[]
}

export interface MethodologyDoc {
  title: string
  subtitle: string
  source: string
  updated: string
  sections: MethodologySection[]
}
