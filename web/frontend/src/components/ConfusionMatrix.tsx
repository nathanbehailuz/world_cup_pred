import type { ProbabilityVector } from '../types'

const CONFUSION_LABELS = ['A', 'D', 'B'] as const

export function ConfusionMatrix({ matrix }: { matrix: number[][] }) {
  const maxCell = Math.max(1, ...matrix.flat())
  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-left">
        <thead>
          <tr>
            <th className="p-0.5" />
            <th
              colSpan={3}
              className="font-label-caps text-[10px] text-on-surface-variant text-center pb-1 font-normal"
            >
              Actual
            </th>
          </tr>
          <tr>
            <th className="font-label-caps text-[10px] text-on-surface-variant pr-2 font-normal align-bottom">
              Pred
            </th>
            {CONFUSION_LABELS.map((lab) => (
              <th
                key={lab}
                className="font-data-mono text-[10px] text-on-surface-variant text-center px-0.5 pb-1 font-normal w-8"
              >
                {lab}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, ri) => (
            <tr key={CONFUSION_LABELS[ri]}>
              <th
                scope="row"
                className="font-data-mono text-[10px] text-on-surface-variant pr-2 font-normal text-right"
              >
                {CONFUSION_LABELS[ri]}
              </th>
              {row.map((n, ci) => (
                <td key={`${CONFUSION_LABELS[ri]}-${CONFUSION_LABELS[ci]}`} className="p-0.5">
                  <div
                    className="rounded-[2px] w-8 h-8 flex items-center justify-center text-[10px] font-data-mono"
                    style={{
                      background:
                        n === 0
                          ? 'var(--color-surface-variant)'
                          : `color-mix(in srgb, var(--color-pitch-green) ${Math.min(100, (n / maxCell) * 100)}%, var(--color-surface-variant))`,
                    }}
                    title={`Pred ${CONFUSION_LABELS[ri]} · Actual ${CONFUSION_LABELS[ci]}: ${n}`}
                  >
                    {n}
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function runningConfusion(matches: { predicted: string; actual: string | null; status: string }[]) {
  const labels = ['home_win', 'draw', 'away_win'] as const
  const played = matches.filter((m) => m.status === 'final' && m.actual)
  return labels.map((pred) =>
    labels.map((act) => played.filter((m) => m.predicted === pred && m.actual === act).length),
  )
}

export type { ProbabilityVector }
