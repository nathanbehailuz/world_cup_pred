import katex from 'katex'

type MathProps = {
  tex: string
  display?: boolean
  className?: string
}

/** Render a LaTeX string via KaTeX (display or inline). */
export function MathBlock({ tex, display = true, className }: MathProps) {
  const html = katex.renderToString(tex.trim(), {
    displayMode: display,
    throwOnError: false,
    strict: 'ignore',
  })
  return (
    <span
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

/** Split text on `$...$` and render math segments inline; plain text otherwise. */
export function RichText({ text, className }: { text: string; className?: string }) {
  const parts = text.split(/(\$[^$]+\$)/g)
  return (
    <span className={className}>
      {parts.map((part, i) => {
        if (part.startsWith('$') && part.endsWith('$') && part.length > 2) {
          return <MathBlock key={i} tex={part.slice(1, -1)} display={false} />
        }
        return <span key={i}>{part}</span>
      })}
    </span>
  )
}
