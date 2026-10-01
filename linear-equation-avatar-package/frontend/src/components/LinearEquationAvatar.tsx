import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ModelViewerElement } from '@google/model-viewer'

const MODEL_URL = '/models/louise_signs_master.glb?v=linear-equation-v1'
const SETTLE_MS = 90

type Props = {
  signActions: string[]
  className?: string
}

export function LinearEquationAvatar({ signActions, className = '' }: Props) {
  const modelRef = useRef<ModelViewerElement>(null)
  const queueRef = useRef<string[]>([])
  const indexRef = useRef(0)
  const [available, setAvailable] = useState<string[]>([])
  const [active, setActive] = useState<string | null>(null)

  const playable = useMemo(
    () => Array.from(new Set(signActions)).filter((name) => available.includes(name)),
    [signActions, available],
  )

  const play = useCallback((name: string, repetitions = 1) => {
    const viewer = modelRef.current
    if (!viewer) return
    viewer.pause()
    viewer.animationName = name
    viewer.currentTime = 0
    viewer.play({ repetitions, pingpong: false })
  }, [])

  const idle = useCallback(() => {
    setActive(null)
    if (available.includes('IDLE')) play('IDLE', Infinity)
  }, [available, play])

  const begin = useCallback(() => {
    if (!playable.length) {
      idle()
      return
    }
    queueRef.current = playable
    indexRef.current = 0
    setActive(playable[0])
    play(playable[0])
  }, [playable, play, idle])

  const advance = useCallback(() => {
    const next = indexRef.current + 1
    if (next >= queueRef.current.length) {
      idle()
      return
    }
    indexRef.current = next
    const name = queueRef.current[next]
    window.setTimeout(() => {
      setActive(name)
      play(name)
    }, SETTLE_MS)
  }, [idle, play])

  useEffect(() => {
    void import('@google/model-viewer')
    const viewer = modelRef.current
    if (!viewer) return
    const onLoad = () => setAvailable([...viewer.availableAnimations])
    const onFinished = () => advance()
    viewer.addEventListener('load', onLoad)
    viewer.addEventListener('finished', onFinished)
    return () => {
      viewer.removeEventListener('load', onLoad)
      viewer.removeEventListener('finished', onFinished)
    }
  }, [advance])

  useEffect(() => {
    if (available.length) begin()
  }, [available, begin])

  return (
    <div className={className}>
      <model-viewer
        ref={modelRef}
        src={MODEL_URL}
        alt="Linear equation tutor avatar"
        camera-controls
        disable-pan
        interaction-prompt="none"
        camera-target="0m 1.15m 0m"
        camera-orbit="0deg 82deg 3.2m"
        field-of-view="28deg"
      />
      <div aria-live="polite">
        {active ? `Gesture: ${active.replaceAll('_', ' ')}` : 'Ready'}
      </div>
      <button type="button" onClick={begin} disabled={!playable.length}>
        Replay
      </button>
    </div>
  )
}
