import test from 'node:test'
import assert from 'node:assert/strict'
import { selectAssessmentVariants } from '../src/game/data/variantSelection.ts'
import { EASY_VARIANTS, HARD_VARIANTS, MEDIUM_VARIANTS } from '../src/game/data/equationVariants.ts'

test('a fresh student gets 2 easy, 2 medium, 2 hard in that order', () => {
  const selected = selectAssessmentVariants({})
  assert.equal(selected.length, 6)
  assert.deepEqual(
    selected.map((variant) => variant.difficulty),
    ['easy', 'easy', 'medium', 'medium', 'hard', 'hard'],
  )
})

test('every selected variant_id is unique within one assessment', () => {
  const selected = selectAssessmentVariants({})
  const ids = selected.map((variant) => variant.variantId)
  assert.equal(new Set(ids).size, ids.length)
})

test('a variant used twice already is excluded from selection', () => {
  const maxedOut = EASY_VARIANTS[0].variantId
  const usageCounts = { [maxedOut]: 2 }

  // Run several times since selection shuffles — the excluded variant must
  // never appear, not just usually avoided.
  for (let i = 0; i < 20; i += 1) {
    const selected = selectAssessmentVariants(usageCounts)
    assert.ok(!selected.some((variant) => variant.variantId === maxedOut))
  }
})

test('does not crash when every variant in a tier is maxed out, and falls back to least-used', () => {
  const usageCounts: Record<string, number> = {}
  for (const variant of EASY_VARIANTS) usageCounts[variant.variantId] = 2
  // One easy variant used less than the rest should be preferred by the fallback.
  usageCounts[EASY_VARIANTS[0].variantId] = 5

  const selected = selectAssessmentVariants(usageCounts)
  const easyPicked = selected.filter((variant) => variant.difficulty === 'easy')
  assert.equal(easyPicked.length, 2)
  assert.ok(!easyPicked.some((variant) => variant.variantId === EASY_VARIANTS[0].variantId))
})

test('medium and hard tiers are independent of easy', () => {
  const selected = selectAssessmentVariants({})
  const mediumIds = new Set(MEDIUM_VARIANTS.map((v) => v.variantId))
  const hardIds = new Set(HARD_VARIANTS.map((v) => v.variantId))
  assert.ok(selected.slice(2, 4).every((variant) => mediumIds.has(variant.variantId)))
  assert.ok(selected.slice(4, 6).every((variant) => hardIds.has(variant.variantId)))
})
