import { useEffect, useRef } from 'react'
import Phaser from 'phaser'
import { createGameConfig } from './GameConfig'
import { DESIGN } from './viewport'
import { renderPixelRatio } from './theme/gameTheme'
import { CollectionGate } from '../CollectionGate'

// Mounts a Phaser game into a plain <div>. Phaser manages everything inside
// that div itself (it inserts its own <canvas>) — React never re-renders
// into it, it just creates the Phaser.Game once and destroys it on cleanup.
export function PhaserGame() {
  return <CollectionGate><GameCanvas /></CollectionGate>
}

function GameCanvas() {
  const containerRef = useRef<HTMLDivElement>(null)
  const gameRef = useRef<Phaser.Game | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    let game: Phaser.Game | undefined
    // Phones scroll the page rather than shrink a tall game to the height
    // left below navigation. This preserves readable text and >=44px keys.
    const fitToViewport = () => {
      if (container.clientWidth >= 620) {
        container.style.height = ''
      } else {
        const width = container.clientWidth
        container.style.height = `${Math.ceil(width * DESIGN.compact.height / DESIGN.compact.width)}px`
      }
      if (game?.isBooted) {
        const ratio = renderPixelRatio(window.devicePixelRatio)
        const width = Math.round(container.clientWidth * ratio)
        const height = Math.round(container.clientHeight * ratio)
        // Do not restart scenes on scroll/browser-bar changes with no size change.
        if (game.scale.width !== width || game.scale.height !== height || game.scale.zoom !== 1 / ratio) {
          game.scale.zoom = 1 / ratio
          game.scale.resize(width, height)
        }
      }
    }
    fitToViewport()
    game = new Phaser.Game(createGameConfig(container))
    gameRef.current = game
    const frame = requestAnimationFrame(fitToViewport)
    const observer = new ResizeObserver(fitToViewport)
    observer.observe(container)
    window.addEventListener('resize', fitToViewport)
    window.addEventListener('orientationchange', fitToViewport)
    window.visualViewport?.addEventListener('resize', fitToViewport)
    const stop = () => { game?.destroy(true); game = undefined }
    window.addEventListener('game-collection-stop', stop)

    // React's StrictMode runs effects twice in development (mount, cleanup,
    // mount again) to help catch bugs. Destroying the game in this cleanup
    // function is what stops that from leaving two Phaser instances running.
    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
      window.removeEventListener('resize', fitToViewport)
      window.removeEventListener('orientationchange', fitToViewport)
      window.visualViewport?.removeEventListener('resize', fitToViewport)
      window.removeEventListener('game-collection-stop', stop)
      game?.destroy(true)
      gameRef.current = null
    }
  }, [])

  return <div ref={containerRef} className="phaser-game-container" />
}
