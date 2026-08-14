import type { Outcome, ProbabilityVector } from '../types'

export function pct(p: number, digits = 1): string {
  return `${(p * 100).toFixed(digits)}%`
}

export function outcomeLabel(o: Outcome, a = 'A', b = 'B'): string {
  if (o === 'home_win') return a
  if (o === 'away_win') return b
  return 'Draw'
}

export function argmaxOutcome(p: ProbabilityVector): Outcome {
  if (p.p_a >= p.p_draw && p.p_a >= p.p_b) return 'home_win'
  if (p.p_b >= p.p_draw && p.p_b >= p.p_a) return 'away_win'
  return 'draw'
}

export function formatCi(point: number, low: number, high: number, digits = 3): string {
  return `${point.toFixed(digits)} [${low.toFixed(digits)}, ${high.toFixed(digits)}]`
}
