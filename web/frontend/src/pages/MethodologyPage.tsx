import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Icon } from '../components/Icon'
import methodologyJson from '../data/methodology.json'
import type { MethodologyDoc, MethodologySection } from '../types'

const doc = methodologyJson as MethodologyDoc

function SectionBody({ section }: { section: MethodologySection }) {
  return (
    <section className="space-y-4" id={section.id}>
      <h2 className="text-headline-md text-on-surface flex items-center gap-2">
        <Icon name={section.icon} className="text-pitch-green text-xl" />
        {section.title}
      </h2>

      {section.paragraphs?.map((p) => (
        <p key={p.slice(0, 48)} className="text-body-md text-on-surface-variant leading-relaxed">
          {p}
        </p>
      ))}

      {section.callouts?.map((c) =>
        c.kind === 'notation' ? (
          <div key={c.title} className="bg-surface-container-low border-l-2 border-slate-gray p-4 my-2">
            <h4 className="font-label-caps text-on-surface mb-2">{c.title}</h4>
            <pre className="font-data-mono text-on-surface-variant text-sm bg-surface-container-lowest p-3 border border-outline-variant rounded overflow-x-auto whitespace-pre-wrap">
              {c.body}
            </pre>
          </div>
        ) : (
          <div
            key={c.title}
            className="bg-surface-container-low border-l-2 border-slate-gray p-4 text-body-sm text-on-surface-variant"
          >
            <p className="font-label-caps text-on-surface mb-1">{c.title}</p>
            {c.body}
          </div>
        ),
      )}

      {section.cards && (
        <div className="grid md:grid-cols-2 gap-4 mt-2">
          {section.cards.map((card) => (
            <div
              key={card.title}
              className="bg-surface-container-lowest border border-outline-variant p-4 rounded"
            >
              <h4 className="font-label-caps text-on-surface mb-2">{card.title}</h4>
              <p
                className={
                  card.mono
                    ? 'font-data-mono text-pitch-green'
                    : 'text-body-sm text-on-surface-variant'
                }
              >
                {card.body}
              </p>
            </div>
          ))}
        </div>
      )}

      {section.tables?.map((table) => (
        <div key={table.caption} className="overflow-x-auto space-y-2">
          <table className="w-full border-collapse bg-surface-container-lowest border border-outline-variant rounded text-left">
            <caption className="font-label-caps text-on-surface-variant text-left p-4 border-b border-outline-variant bg-surface-container-low">
              {table.caption}
            </caption>
            <thead>
              <tr>
                {table.columns.map((col) => (
                  <th
                    key={col.key}
                    className={`font-label-caps text-on-surface border-b border-outline-variant px-4 py-3 bg-surface ${
                      col.align === 'right' ? 'text-right' : 'text-left'
                    }`}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="text-body-sm text-on-surface-variant">
              {table.rows.map((row, i) => {
                const highlighted = table.highlightRow === i
                return (
                  <tr
                    key={table.columns.map((c) => row[c.key]).join('|')}
                    className={
                      highlighted
                        ? 'bg-surface-container-low border-l-2 border-pitch-green border-b border-outline-variant'
                        : 'hover:bg-surface-container-highest border-b border-outline-variant'
                    }
                  >
                    {table.columns.map((col, colIdx) => (
                      <td
                        key={col.key}
                        className={`px-4 py-3 ${col.align === 'right' ? 'text-right font-data-mono' : ''} ${
                          highlighted && colIdx === 0
                            ? 'font-bold text-pitch-green'
                            : colIdx === 0
                              ? 'font-medium text-on-surface'
                              : ''
                        } ${highlighted && col.align === 'right' ? 'font-bold text-on-surface' : ''}`}
                      >
                        {highlighted && colIdx === 0 ? (
                          <span className="inline-flex items-center gap-2">
                            <Icon name="check_circle" className="text-sm" />
                            {row[col.key]}
                          </span>
                        ) : (
                          row[col.key]
                        )}
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ))}

      {section.findings && section.findings.length > 0 && (
        <ul className="list-disc pl-5 space-y-2 text-body-md text-on-surface-variant">
          {section.findings.map((f) => (
            <li key={f.slice(0, 48)}>{f}</li>
          ))}
        </ul>
      )}

      {section.commands && (
        <pre className="font-data-mono text-sm text-on-surface-variant bg-surface-container-lowest border border-outline-variant rounded p-4 overflow-x-auto whitespace-pre-wrap">
          {section.commands.join('\n')}
        </pre>
      )}

      {section.footnotes && section.footnotes.length > 0 && (
        <p className="text-body-sm text-on-surface-variant">
          Sources:{' '}
          {section.footnotes.map((fn, i) => (
            <span key={fn.id}>
              {i > 0 && ', '}
              {fn.href ? (
                <a
                  href={fn.href}
                  className="text-pitch-green hover:underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  {fn.text}
                </a>
              ) : (
                fn.text
              )}
            </span>
          ))}
          .
        </p>
      )}

      {section.links && section.links.length > 0 && (
        <p className="text-body-sm text-on-surface-variant">
          {section.links.map((link, i) => (
            <span key={link.to}>
              {i > 0 && ' · '}
              <Link to={link.to} className="text-pitch-green hover:underline">
                {link.label}
              </Link>
            </span>
          ))}
        </p>
      )}
    </section>
  )
}

export function MethodologyPage() {
  const [active, setActive] = useState(doc.sections[0]?.id ?? 'abstract')

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
            {doc.sections.map((s) => (
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
            <h1 className="text-headline-lg text-on-surface mb-2">{doc.title}</h1>
            <p className="text-body-md text-on-surface-variant max-w-3xl">{doc.subtitle}</p>
            <p className="text-body-sm text-on-surface-variant mt-3">
              Source: <code className="font-mono text-pitch-green">{doc.source}</code>
              {' · '}Updated {doc.updated}
            </p>
          </header>

          {doc.sections.map((section) => (
            <SectionBody key={section.id} section={section} />
          ))}
        </article>
      </div>
    </main>
  )
}
