import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { Icon } from './Icon'
import { USING_MOCK } from '../api/client'

const NAV = [
  { to: '/', label: 'Home', end: true },
  { to: '/methodology', label: 'Methodology' },
  { to: '/predict', label: 'Predict' },
  { to: '/evaluate', label: 'Evaluate' },
  { to: '/results', label: 'Results' },
  { to: '/wc2026', label: 'WC 2026' },
]

export function TopNav() {
  const [open, setOpen] = useState(false)

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    [
      'h-full flex items-center font-label-caps py-5 border-b-2 transition-all duration-200',
      isActive
        ? 'text-primary border-pitch-green font-bold opacity-80'
        : 'text-on-surface-variant border-transparent hover:text-pitch-green',
    ].join(' ')

  return (
    <header className="bg-surface/90 border-b border-outline-variant sticky top-0 z-50 backdrop-blur-md">
      <div className="flex justify-between items-center w-full px-margin-mobile md:px-margin-desktop max-w-container-max mx-auto h-16">
        <div className="flex items-center gap-4 md:gap-8">
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <Icon name="query_stats" className="text-pitch-green text-[22px]" />
            <span className="text-headline-md font-black text-deep-navy tracking-tight">
              WC 2026 Predictor
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-6 h-full">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3">
          {USING_MOCK && (
            <span className="hidden sm:inline font-label-caps text-slate-gray border border-outline-variant px-2 py-1 rounded">
              Mock data
            </span>
          )}
          <button
            type="button"
            className="md:hidden text-on-surface-variant"
            aria-label="Menu"
            onClick={() => setOpen((v) => !v)}
          >
            <Icon name={open ? 'close' : 'menu'} />
          </button>
        </div>
      </div>
      {open && (
        <nav className="md:hidden border-t border-outline-variant bg-surface px-margin-mobile py-3 flex flex-col gap-1 animate-fade-in">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `font-label-caps py-2 px-2 ${isActive ? 'text-pitch-green' : 'text-on-surface-variant'}`
              }
            >
              {item.label}
            </NavLink>
          ))}
          <Link to="/about" onClick={() => setOpen(false)} className="font-label-caps py-2 px-2 text-on-surface-variant">
            About
          </Link>
          <Link to="/features" onClick={() => setOpen(false)} className="font-label-caps py-2 px-2 text-on-surface-variant">
            Features
          </Link>
          <Link to="/limitations" onClick={() => setOpen(false)} className="font-label-caps py-2 px-2 text-on-surface-variant">
            Limitations
          </Link>
        </nav>
      )}
    </header>
  )
}
