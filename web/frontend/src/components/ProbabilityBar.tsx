import { pct } from '../lib/format'
import type { ProbabilityVector } from '../types'

export function ProbabilityBar({
  probabilities,
  labelA = 'A',
  labelB = 'B',
  tall = false,
  showLabels = true,
}: {
  probabilities: ProbabilityVector
  labelA?: string
  labelB?: string
  tall?: boolean
  showLabels?: boolean
}) {
  const { p_a, p_draw, p_b } = probabilities
  const h = tall ? 'h-8' : 'h-2'

  return (
    <div className="flex flex-col gap-1 w-full">
      {showLabels && (
        <div className="flex justify-between font-label-caps text-on-surface-variant mb-1">
          <span title={labelA}>{pct(p_a)}</span>
          <span>Draw {pct(p_draw)}</span>
          <span title={labelB}>{pct(p_b)}</span>
        </div>
      )}
      <div className={`w-full ${h} rounded overflow-hidden flex origin-left animate-bar-grow`}>
        <div
          className="bg-pitch-green h-full flex items-center pl-2 text-on-primary font-data-mono font-bold transition-all duration-500"
          style={{ width: pct(p_a, 2) }}
          title={`${labelA} win`}
        >
          {tall && p_a >= 0.12 ? pct(p_a) : null}
        </div>
        <div
          className="bg-surface-variant h-full border-x border-surface-container-lowest flex items-center justify-center text-on-surface-variant font-data-mono transition-all duration-500"
          style={{ width: pct(p_draw, 2) }}
          title="Draw"
        >
          {tall && p_draw >= 0.12 ? pct(p_draw) : null}
        </div>
        <div
          className="bg-slate-gray h-full flex items-center justify-end pr-2 text-on-primary font-data-mono transition-all duration-500"
          style={{ width: pct(p_b, 2) }}
          title={`${labelB} win`}
        >
          {tall && p_b >= 0.12 ? pct(p_b) : null}
        </div>
      </div>
    </div>
  )
}
