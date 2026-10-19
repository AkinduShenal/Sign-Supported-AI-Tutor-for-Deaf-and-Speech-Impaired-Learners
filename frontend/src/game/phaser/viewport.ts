import type Phaser from 'phaser'
import { GAME_THEME, renderPixelRatio } from './theme/gameTheme'

// Every scene lays itself out in a fixed design space (wide desktop /
// compact phone) and the camera zooms to fit whatever size the canvas is,
// so the whole screen is always visible and grows on large displays.
export const DESIGN = {
  wide: { width: 960, height: 840 },
  compact: { width: 420, height: 1120 },
}

const COMPACT_BREAKPOINT = 620

export function isCompactScreen(scene: Phaser.Scene): boolean {
  return scene.scale.displaySize.width < COMPACT_BREAKPOINT
}

export function designSize(compact: boolean): { width: number; height: number } {
  return compact ? DESIGN.compact : DESIGN.wide
}

export function fitCameraToDesign(scene: Phaser.Scene, compact: boolean): void {
  const { width, height } = designSize(compact)
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
