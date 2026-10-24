export type SprinkleMoment = 'answer' | 'win'

export const SPRINKLE_EVENT = 'sign-and-learn:sprinkle'

export interface SprinkleEventDetail {
  moment: SprinkleMoment
  sourceId?: string
}

export function showSprinkles(moment: SprinkleMoment, sourceId?: string): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent<SprinkleEventDetail>(SPRINKLE_EVENT, {
    detail: { moment, sourceId },
  }))
}
