import type Phaser from 'phaser'
import { GAME_THEME, renderPixelRatio } from './theme/gameTheme'

// Every scene lays itself out in a design space (wide desktop / compact
// phone) and the camera zooms to fit whatever size the canvas is, so the
// whole screen is always visible and grows on large displays.
export const DESIGN = {
  wide: { width: 960, height: 840 },
  compact: { width: 420, height: 1120 },
}

// Wide screens (and full screen) are usually wider than 960:840. Rather
// than letterboxing a fixed 960-wide layout, the wide design grows sideways
// up to this width so scenes can spread their panels into the extra room.
const MAX_WIDE_WIDTH = 1360

const COMPACT_BREAKPOINT = 620

export interface DesignSize { width: number; height: number }

export function isCompactScreen(scene: Phaser.Scene): boolean {
  return scene.scale.displaySize.width < COMPACT_BREAKPOINT
}

export function designSize(compact: boolean): DesignSize {
  return compact ? DESIGN.compact : DESIGN.wide
}

// The design size for this scene's current canvas: the compact size is
// fixed (the page scrolls on phones), the wide height is fixed and its width
// follows the canvas aspect ratio. Scenes read this once in create() and
// keep it, so a later resize only refits the camera (see fitCameraToDesign).
export function fitDesignSize(scene: Phaser.Scene, compact: boolean): DesignSize {
  if (compact) return DESIGN.compact
  const { width, height } = scene.scale
  const aspect = width > 0 && height > 0 ? width / height : DESIGN.wide.width / DESIGN.wide.height
  const fitted = Math.round(DESIGN.wide.height * aspect)
  return { width: Math.max(DESIGN.wide.width, Math.min(MAX_WIDE_WIDTH, fitted)), height: DESIGN.wide.height }
}

export function fitCameraToDesign(scene: Phaser.Scene, compact: boolean, size: DesignSize = designSize(compact)): void {
  const { width, height } = size
  const zoom = Math.min(scene.scale.width / width, scene.scale.height / height)
  const camera = scene.cameras.main
  const ratio = renderPixelRatio(window.devicePixelRatio)
  // Zoom includes backing pixels. Display enlargement stays restrained.
  camera.setZoom(Math.min(zoom, ratio * (compact ? 1.3 : GAME_THEME.render.maxDesktopZoom)))
  camera.roundPixels = true
  camera.centerOn(width / 2, height / 2)
}

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
  )
}
