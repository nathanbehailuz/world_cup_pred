import { Link } from 'react-router-dom'

export function Footer() {
  return (
    <footer className="bg-surface-container-lowest border-t border-outline-variant mt-auto">
      <div className="flex flex-col items-center gap-4 py-8 px-margin-mobile md:px-margin-desktop w-full max-w-container-max mx-auto">
        <div className="text-body-lg font-semibold text-on-surface">WC 2026 Predictor</div>
        <div className="flex flex-wrap justify-center gap-6">
          <Link className="font-label-caps text-on-surface-variant hover:text-primary transition-all" to="/about">
            Data Sources
          </Link>
          <Link className="font-label-caps text-on-surface-variant hover:text-primary transition-all" to="/limitations">
            Limitations
          </Link>
          <Link className="font-label-caps text-on-surface-variant hover:text-primary transition-all" to="/features">
            Features
          </Link>
          <Link className="font-label-caps text-on-surface-variant hover:text-primary transition-all" to="/methodology">
            Methodology
          </Link>
        </div>
        <p className="text-body-sm text-on-surface-variant text-center max-w-xl mt-2">
          © 2026 World Cup Predictor. Probabilities are for research purposes and do not constitute
          betting advice. Probabilities ≠ bets.
        </p>
        <p className="text-body-sm text-on-surface-variant text-center">
          Built with love by{' '}
          <a
            href="https://nathanbehailu.vercel.app/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-pitch-green hover:underline"
          >
            Nathan
          </a>
        </p>
      </div>
    </footer>
  )
}
