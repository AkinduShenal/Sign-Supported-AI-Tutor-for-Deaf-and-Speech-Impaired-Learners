import { useCallback, useEffect, useRef, useState } from 'react'
import Phaser from 'phaser'
import { createGameConfig } from './GameConfig'
import { loadGameFonts } from './gameFonts'
import { DESIGN } from './viewport'
import { renderPixelRatio } from './theme/gameTheme'
import { CollectionGate } from '../CollectionGate'
import { GameLanguageToggle } from '../GameLanguageToggle'
import './PhaserGame.css'

// Mounts a Phaser game into a plain <div>. Phaser manages everything inside
// that div itself (it inserts its own <canvas>) — React never re-renders
// into it, it just creates the Phaser.Game once and destroys it on cleanup.
export function PhaserGame({ onContinue }: { onContinue?: () => void }) {
  return <CollectionGate onContinue={onContinue}><GameCanvas /></CollectionGate>
}

function GameCanvas() {
  const stageRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const gameRef = useRef<Phaser.Game | null>(null)
  const [expanded, setExpanded] = useState(false)

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
    // Boot once the bundled game fonts are ready (see gameFonts.ts).
    let cancelled = false
    void loadGameFonts().then(() => {
      if (cancelled) return
      game = new Phaser.Game(createGameConfig(container))
      gameRef.current = game
      fitToViewport()
    })
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
      cancelled = true
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

  // Full screen: the stage always expands to cover the window (CSS), and
  // also asks the browser for real full screen where that is supported
  // (iPhone Safari is not, so the CSS overlay is the fallback). Leaving
  // browser full screen (Esc) or pressing Esc in the overlay exits both.
  const exit = useCallback(() => {
    setExpanded(false)
    if (document.fullscreenElement) void document.exitFullscreen().catch(() => {})
  }, [])

  const toggle = useCallback(() => {
    if (expanded) { exit(); return }
    setExpanded(true)
    const stage = stageRef.current
    if (stage?.requestFullscreen && document.fullscreenEnabled) {
      void stage.requestFullscreen().catch(() => {})
    }
  }, [expanded, exit])

  useEffect(() => {
    if (!expanded) return
    const onFullscreenChange = () => { if (!document.fullscreenElement) setExpanded(false) }
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') exit() }
    document.addEventListener('fullscreenchange', onFullscreenChange)
    window.addEventListener('keydown', onKey)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('fullscreenchange', onFullscreenChange)
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
    }
  }, [expanded, exit])

  const label = expanded ? 'Exit full screen · සම්පූර්ණ තිරයෙන් ඉවත් වන්න' : 'Full screen · සම්පූර්ණ තිරය'

  return (
    <div ref={stageRef} className={`game-stage${expanded ? ' game-stage--expanded' : ''}`}>
      {expanded && (
        <div className="game-stage__bar">
          <GameLanguageToggle />
        </div>
      )}
      <div className="game-stage__frame">
        <div ref={containerRef} className="phaser-game-container" />
        <button type="button" className="game-stage__fullscreen" onClick={toggle}
          aria-pressed={expanded} aria-label={label} title={label}>
          {expanded ? (
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5" /></svg>
          ) : (
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" /></svg>
          )}
        </button>
      </div>
    </div>
  )
}
