import holdoutJson from './holdout.json'
import type { HoldoutArtifact } from '../types'

/** Precomputed temporal holdout (train < 2023, competitive 2023+). Regenerate via `python -m pipeline.export_holdout`. */
export const HOLDOUT_ARTIFACT = holdoutJson as HoldoutArtifact
export const HOLDOUT_MATCHES = HOLDOUT_ARTIFACT.matches
