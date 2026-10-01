import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ModelViewerElement } from '@google/model-viewer'

const MASTER_AVATAR_URL = '/models/louise_signs_master.glb?v=avatar-sign-package-v1'
const BETWEEN_CLIPS_MS = 120

interface AvatarSignPlayerProps {
  signActions: string[]
  className?: string
}

export function AvatarSignPlayer({
  signActions,
  className = '',
}: AvatarSignPlayerProps) {
  const ref = useRef<ModelViewerElement>(null)
  const queueRef = useRef<string[]>([])
  const indexRef = useRef(0)
  const [availableAnimations, setAvailableAnimations] = useState<string[]>([])
  const [activeSign, setActiveSign] = useState<string | null>(null)

  const playable = useMemo(
    () =>
      Array.from(new Set(signActions)).filter((name) =>
        availableAnimations.includes(name),
      ),
    [availableAnimations, signActions],
  )

  const playClip = useCallback((name: string, repetitions = 1) => {
    const viewer = ref.current
    if (!viewer) return
    viewer.animationName = name
    viewer.currentTime = 0
    viewer.play({ repetitions, pingpong: false })
  }, [])

  const playIdle = useCallback(() => {
    setActiveSign(null)
    if (availableAnimations.includes('IDLE')) {
      playClip('IDLE', Infinity)
    }
  }, [availableAnimations, playClip])

  const advance = useCallback(() => {
    const nextIndex = indexRef.current + 1
    if (nextIndex >= queueRef.current.length) {
      playIdle()
      return
    }

    indexRef.current = nextIndex
    const next = queueRef.current[nextIndex]
    setTimeout(() => {
      setActiveSign(next)
      playClip(next, 1)
    }, BETWEEN_CLIPS_MS)
  }, [playClip, playIdle])

  const playSequence = useCallback(() => {
    if (!playable.length) {
      playIdle()
      return
    }
    queueRef.current = playable
    indexRef.current = 0
    setActiveSign(playable[0])
    playClip(playable[0], 1)
  }, [playable, playClip, playIdle])

  useEffect(() => {
    const viewer = ref.current
    if (!viewer) return

    const onLoad = () => {
      setAvailableAnimations([...viewer.availableAnimations])
    }
    const onFinished = () => advance()

    viewer.addEventListener('load', onLoad)
    viewer.addEventListener('finished', onFinished)

    void import('@google/model-viewer')

    return () => {
      viewer.removeEventListener('load', onLoad)
      viewer.removeEventListener('finished', onFinished)
    }
  }, [advance])

  useEffect(() => {
    if (availableAnimations.length) playSequence()
  }, [availableAnimations, playSequence])

  return (
    <div className={`avatar-sign-player ${className}`}>
      <model-viewer
        ref={ref}
        src={MASTER_AVATAR_URL}
        alt="3D sign-supported mathematics tutor avatar"
        camera-controls
        disable-pan
        interaction-prompt="none"
        camera-target="0m 1.2m 0m"
        camera-orbit="0deg 82deg 3.2m"
        field-of-view="28deg"
      />
      <div className="avatar-sign-status" aria-live="polite">
        {activeSign ? `Signing: ${activeSign.replaceAll('_', ' ')}` : 'Ready'}
      </div>
      <button type="button" onClick={playSequence} disabled={!playable.length}>
        Replay signs
      </button>
    </div>
  )
}
