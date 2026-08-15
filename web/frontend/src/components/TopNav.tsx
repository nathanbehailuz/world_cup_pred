import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { Icon } from './Icon'
import { USING_MOCK } from '../api/client'

const NAV = [
  { to: '/', label: 'Home', end: true },
  { to: '/methodology', label: 'Methodology' },
  { to: '/predict', label: 'Predict' },
  { to: '/evaluate', label: 'Evaluate' },
  { to: '/analysis', label: 'Model Analysis' },
]

const MORE_LINKS = [
  { to: '/about', label: 'About' },
  { to: '/features', label: 'Features' },
  { to: '/limitations', label: 'Limitations' },
]

const MORE_PATHS = MORE_LINKS.map((l) => l.to)

function BrandMark({ className = 'h-7 w-7' }: { className?: string }) {
  return (
    <img
      src="/favicon.svg"
      alt=""
      width={28}
      height={28}
      className={className}
      aria-hidden
    />
  )
}

export function TopNav() {
  const [open, setOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const [mobileMoreOpen, setMobileMoreOpen] = useState(false)
  const moreRef = useRef<HTMLDivElement>(null)
  const location = useLocation()

  const moreActive = MORE_PATHS.some((p) => location.pathname === p)

  useEffect(() => {
    setMoreOpen(false)
    setOpen(false)
    setMobileMoreOpen(MORE_PATHS.some((p) => location.pathname === p))
  }, [location.pathname])

  useEffect(() => {
    if (!moreOpen) return
    const onPointer = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setMoreOpen(false)
      }
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMoreOpen(false)
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [moreOpen])

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    [
      'h-full flex items-center font-label-caps py-5 border-b-2 transition-all duration-200',
      isActive
        ? 'text-primary border-pitch-green font-bold opacity-80'
        : 'text-on-surface-variant border-transparent hover:text-pitch-green',
    ].join(' ')

  const moreButtonClass = [
    'h-full flex items-center gap-1 font-label-caps py-5 border-b-2 transition-all duration-200',
    moreActive || moreOpen
      ? 'text-primary border-pitch-green font-bold opacity-80'
      : 'text-on-surface-variant border-transparent hover:text-pitch-green',
  ].join(' ')

  return (
    <header className="bg-surface/90 border-b border-outline-variant sticky top-0 z-50 backdrop-blur-md">
      <div className="flex justify-between items-center w-full px-margin-mobile md:px-margin-desktop max-w-container-max mx-auto h-16">
        <div className="flex items-center gap-4 md:gap-8">
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <BrandMark />
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
            <div className="relative h-full flex items-center" ref={moreRef}>
              <button
                type="button"
                className={moreButtonClass}
                aria-expanded={moreOpen}
                aria-haspopup="menu"
                onClick={() => setMoreOpen((v) => !v)}
              >
                More
                <Icon
                  name="expand_more"
                  className={`text-[18px] transition-transform ${moreOpen ? 'rotate-180' : ''}`}
                />
              </button>
              {moreOpen && (
                <div
                  role="menu"
                  className="absolute top-full left-0 mt-0 min-w-[10rem] bg-surface border border-outline-variant rounded shadow-sm py-1 animate-fade-in"
                >
                  {MORE_LINKS.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      role="menuitem"
                      onClick={() => setMoreOpen(false)}
                      className={({ isActive }) =>
                        `block font-label-caps px-4 py-2.5 ${
                          isActive
                            ? 'text-pitch-green bg-surface-container-lowest'
                            : 'text-on-surface-variant hover:text-pitch-green hover:bg-surface-container-lowest'
                        }`
                      }
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
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
          <button
            type="button"
            className={`font-label-caps py-2 px-2 flex items-center justify-between text-left ${
              moreActive ? 'text-pitch-green' : 'text-on-surface-variant'
            }`}
            aria-expanded={mobileMoreOpen}
            onClick={() => setMobileMoreOpen((v) => !v)}
          >
            More
            <Icon
              name="expand_more"
              className={`text-[18px] transition-transform ${mobileMoreOpen ? 'rotate-180' : ''}`}
            />
          </button>
          {mobileMoreOpen && (
            <div className="flex flex-col pl-3 border-l border-outline-variant ml-2 gap-1">
              {MORE_LINKS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `font-label-caps py-2 px-2 ${isActive ? 'text-pitch-green' : 'text-on-surface-variant'}`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          )}
        </nav>
      )}
    </header>
  )
}
