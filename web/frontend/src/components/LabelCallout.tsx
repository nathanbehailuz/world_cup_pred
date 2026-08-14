export function LabelCallout({ className = '' }: { className?: string }) {
  return (
    <div
      className={`bg-surface-container-low border-l-2 border-slate-gray p-4 text-body-sm text-on-surface-variant ${className}`}
    >
      <p className="font-label-caps text-on-surface mb-1">Label clarity</p>
      Group-stage draws are possible; knockout fixtures use an advancement label (extra time /
      penalties). The draw class is structurally unavailable in knockouts.
    </div>
  )
}
