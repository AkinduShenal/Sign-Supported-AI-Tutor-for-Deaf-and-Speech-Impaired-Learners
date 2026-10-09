import type { EquationVariant } from './equationVariants.ts'
import { EASY_VARIANTS, HARD_VARIANTS, MEDIUM_VARIANTS } from './equationVariants.ts'

const MAX_USES_PER_VARIANT = 2
const VARIANTS_PER_TIER = 2

// Fisher-Yates — unbiased, and simple enough to unit-test by eye.
function shuffle<T>(items: T[]): T[] {
  const copy = [...items]
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

// Milestone 3 Step 13: filter out anything already used
// MAX_USES_PER_VARIANT+ times, then shuffle and take what's needed. If the
// filter would leave nothing to choose from (the learner has hit the limit
// on every variant in this tier), fall back to the least-used ones instead
// of crashing — documented fallback, not a silent change of the usual rule.
function pickFromTier(
  tier: EquationVariant[],
  usageCounts: Record<string, number>,
  count: number,
): EquationVariant[] {
  const usesOf = (variant: EquationVariant) => usageCounts[variant.variantId] ?? 0
  const eligible = tier.filter((variant) => usesOf(variant) < MAX_USES_PER_VARIANT)

  if (eligible.length >= count) {
    return shuffle(eligible).slice(0, count)
  }

  const byLeastUsed = [...tier].sort((a, b) => usesOf(a) - usesOf(b))
  return shuffle(byLeastUsed.slice(0, count * 2)).slice(0, count)
}

// Builds one assessment's 6 diagnostic tasks: 2 Easy, 2 Medium, 2 Hard
// (Milestone 3 Steps 12-13), in that tier order, shuffled within each tier,
// respecting prior usage from the backend's /game/variant-usage endpoint.
export function selectAssessmentVariants(
  usageCounts: Record<string, number>,
): EquationVariant[] {
  return [
    ...pickFromTier(EASY_VARIANTS, usageCounts, VARIANTS_PER_TIER),
    ...pickFromTier(MEDIUM_VARIANTS, usageCounts, VARIANTS_PER_TIER),
    ...pickFromTier(HARD_VARIANTS, usageCounts, VARIANTS_PER_TIER),
  ]
}
