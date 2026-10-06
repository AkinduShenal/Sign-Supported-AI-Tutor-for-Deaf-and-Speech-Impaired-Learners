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

    const game = new Phaser.Game(createGameConfig(containerRef.current))
    gameRef.current = game

    // React's StrictMode runs effects twice in development (mount, cleanup,
    // mount again) to help catch bugs. Destroying the game in this cleanup
    // function is what stops that from leaving two Phaser instances running.
    return () => {
      game.destroy(true)
      gameRef.current = null
    }
  }, [])

  return <div ref={containerRef} className="phaser-game-container" />
}
