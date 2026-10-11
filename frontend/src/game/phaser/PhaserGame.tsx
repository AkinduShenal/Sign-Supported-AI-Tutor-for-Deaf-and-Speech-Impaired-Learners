import { useEffect, useRef } from 'react'
import Phaser from 'phaser'
import { createGameConfig } from './GameConfig'

// Mounts a Phaser game into a plain <div>. Phaser manages everything inside
// that div itself (it inserts its own <canvas>) — React never re-renders
// into it, it just creates the Phaser.Game once and destroys it on cleanup.
export function PhaserGame() {
  const containerRef = useRef<HTMLDivElement>(null)
  const gameRef = useRef<Phaser.Game | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    const game = new Phaser.Game(createGameConfig(container))
    gameRef.current = game

    // On phones the page header (title plus two rows of nav buttons) takes
    // a variable amount of height, so a fixed CSS height can push the
    // bottom of the game (the Next button) below the visible area. Size the
    // container to whatever is actually left under the header; the scene's
    // camera zooms the game to fit it.
    const fitToViewport = () => {
      if (window.innerWidth >= 620) {
        container.style.height = ''
      } else {
        const top = container.getBoundingClientRect().top + window.scrollY
        // visualViewport excludes browser bars that can overlay the page.
        const viewportHeight = window.visualViewport?.height ?? window.innerHeight
        const available = viewportHeight - top - 8
        container.style.height = `${Math.max(380, Math.floor(available))}px`
      }
      if (game.isBooted) game.scale.refresh()
    }
    fitToViewport()
    const frame = requestAnimationFrame(fitToViewport)
    window.addEventListener('resize', fitToViewport)
    window.addEventListener('orientationchange', fitToViewport)
    window.visualViewport?.addEventListener('resize', fitToViewport)

    // React's StrictMode runs effects twice in development (mount, cleanup,
    // mount again) to help catch bugs. Destroying the game in this cleanup
    // function is what stops that from leaving two Phaser instances running.
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('resize', fitToViewport)
      window.removeEventListener('orientationchange', fitToViewport)
      window.visualViewport?.removeEventListener('resize', fitToViewport)
      game.destroy(true)
      gameRef.current = null
    }
  }, [])

  return <div ref={containerRef} className="phaser-game-container" />
}
