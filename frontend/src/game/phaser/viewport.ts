import type Phaser from 'phaser'

// Every scene lays itself out in a fixed design space (wide desktop /
// compact phone) and the camera zooms to fit whatever size the canvas is,
// so the whole screen is always visible and grows on large displays.
export const DESIGN = {
  wide: { width: 800, height: 640 },
  compact: { width: 420, height: 770 },
}

const COMPACT_BREAKPOINT = 620

export function isCompactScreen(scene: Phaser.Scene): boolean {
  return scene.scale.width < COMPACT_BREAKPOINT
}

export function designSize(compact: boolean): { width: number; height: number } {
  return compact ? DESIGN.compact : DESIGN.wide
}

export function fitCameraToDesign(scene: Phaser.Scene, compact: boolean): void {
  const { width, height } = designSize(compact)
  const zoom = Math.min(scene.scale.width / width, scene.scale.height / height)
  const camera = scene.cameras.main
  camera.setZoom(compact ? Math.min(zoom, 1.3) : zoom)
  camera.centerOn(width / 2, height / 2)
}

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
  )
}
