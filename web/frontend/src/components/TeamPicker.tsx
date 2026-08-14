import { useEffect, useRef, useState } from 'react'
import type { Team } from '../types'
import { listTeams } from '../api/client'
import { Icon } from './Icon'

export function TeamPicker({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (name: string) => void
}) {
  const [query, setQuery] = useState(value)
  const [open, setOpen] = useState(false)
  const [options, setOptions] = useState<Team[]>([])
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setQuery(value)
  }, [value])

  useEffect(() => {
    let cancelled = false
    void listTeams(query).then((teams) => {
      if (!cancelled) setOptions(teams)
    })
    return () => {
      cancelled = true
    }
  }, [query])

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  return (
    <div className="flex-1 w-full relative" ref={wrapRef}>
      <label className="block font-label-caps text-slate-gray mb-2">{label}</label>
      <div className="relative flex items-center w-full">
        <Icon name="search" className="absolute left-3 text-outline text-[20px]" />
        <input
          className="w-full bg-surface-container pl-10 pr-4 py-3 rounded border border-outline-variant text-body-md text-primary focus:outline-none focus:border-pitch-green focus:ring-1 focus:ring-pitch-green transition-all"
          placeholder="Search FIFA team..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
        />
      </div>
      {open && options.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full max-h-56 overflow-auto bg-surface-container-lowest border border-outline-variant rounded shadow-sm animate-fade-in">
          {options.map((t) => (
            <li key={t.code}>
              <button
                type="button"
                className="w-full text-left px-3 py-2 text-body-sm hover:bg-surface-container transition-colors flex justify-between"
                onClick={() => {
                  onChange(t.name)
                  setQuery(t.name)
                  setOpen(false)
                }}
              >
                <span>{t.name}</span>
                <span className="font-data-mono text-slate-gray">{t.code}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
