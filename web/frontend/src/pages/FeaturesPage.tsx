import { FEATURE_GLOSSARY } from '../data/features'
import { Icon } from '../components/Icon'

export function FeaturesPage() {
  return (
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-8 md:py-12 flex flex-col gap-10">
      <header className="border-b border-outline-variant pb-6 max-w-3xl">
        <h1 className="text-headline-lg text-primary">Features &amp; Data</h1>
        <p className="text-body-md text-on-surface-variant mt-2">
          Glossary of production inputs without reading <code className="font-mono">feature_engineering.py</code>.
          Everything is point-in-time.
        </p>
      </header>

      <section className="bg-surface-container-low border-l-2 border-slate-gray p-4 max-w-3xl">
        <h2 className="font-label-caps text-on-surface mb-2 flex items-center gap-2">
          <Icon name="info" className="text-[18px]" />
          Squad-value proxy
        </h2>
        <p className="text-body-sm text-on-surface-variant">
          Sum of market values of a citizenship’s top-25 players (Transfermarkt). Dual nationals’
          actual national-team choice is ignored; fringe call-ups are missed; European-league bias
          is known. Pre-2004 rows are often missing; XGBoost handles NaN natively.
        </p>
      </section>

      <section className="overflow-x-auto border border-outline-variant rounded bg-surface-container-lowest">
        <table className="w-full text-left border-collapse min-w-[720px]">
          <thead className="bg-surface-container-low border-b border-outline-variant">
            <tr>
              <th className="py-3 px-4 font-label-caps text-on-surface-variant">Feature</th>
              <th className="py-3 px-4 font-label-caps text-on-surface-variant">Category</th>
              <th className="py-3 px-4 font-label-caps text-on-surface-variant">Definition</th>
              <th className="py-3 px-4 font-label-caps text-on-surface-variant">Point-in-time</th>
              <th className="py-3 px-4 font-label-caps text-on-surface-variant">Missingness</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant text-body-sm">
            {FEATURE_GLOSSARY.map((f) => (
              <tr key={f.name} className="hover:bg-surface-container align-top">
                <td className="py-3 px-4 font-data-mono text-primary whitespace-nowrap">{f.name}</td>
                <td className="py-3 px-4 text-on-surface-variant">{f.category}</td>
                <td className="py-3 px-4 text-on-surface-variant max-w-xs">{f.description}</td>
                <td className="py-3 px-4 text-on-surface-variant max-w-[12rem]">{f.point_in_time}</td>
                <td className="py-3 px-4 text-on-surface-variant max-w-[10rem]">{f.missingness}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  )
}
