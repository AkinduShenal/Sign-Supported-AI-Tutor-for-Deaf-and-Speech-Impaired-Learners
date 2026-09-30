import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ModelViewerElement } from '@google/model-viewer'

interface TutorAvatarProps {
  signActions: string[]
}

interface QueuedSign {
  name: string
  sourceIndex: number
}

export function TutorAvatar({ signActions }: TutorAvatarProps) {
  const modelViewerRef = useRef<ModelViewerElement>(null)
  const playbackQueueRef = useRef<QueuedSign[]>([])
  const playbackIndexRef = useRef(0)
  const advanceSequenceRef = useRef<() => void>(() => undefined)
  const [modelState, setModelState] = useState<'loading' | 'ready' | 'error'>(
    'loading',
  )
  const [availableAnimations, setAvailableAnimations] = useState<string[]>([])
  const [activeSignIndex, setActiveSignIndex] = useState<number | null>(null)

  const playableSigns = useMemo(
    () =>
      signActions
        .map((name, sourceIndex) => ({ name, sourceIndex }))
        .filter(({ name }) => availableAnimations.includes(name)),
    [availableAnimations, signActions],
  )
  const activeSign =
    activeSignIndex === null ? null : signActions[activeSignIndex]

  const playClip = useCallback((animationName: string) => {
    const modelViewer = modelViewerRef.current
    if (!modelViewer) return

    modelViewer.pause()
    modelViewer.animationName = animationName
    modelViewer.currentTime = 0
    modelViewer.play({ repetitions: 1, pingpong: false })
  }, [])

  const returnToIdle = useCallback(() => {
    playbackQueueRef.current = []
    playbackIndexRef.current = 0
    setActiveSignIndex(null)

    if (availableAnimations.includes('IDLE')) playClip('IDLE')
  }, [availableAnimations, playClip])

  const advanceSequence = useCallback(() => {
    if (playbackQueueRef.current.length === 0) return

    const nextIndex = playbackIndexRef.current + 1
    if (nextIndex >= playbackQueueRef.current.length) {
      returnToIdle()
      return
    }

    playbackIndexRef.current = nextIndex
    const nextSign = playbackQueueRef.current[nextIndex]
    setActiveSignIndex(nextSign.sourceIndex)
    playClip(nextSign.name)
  }, [playClip, returnToIdle])

  advanceSequenceRef.current = advanceSequence

  const playSequence = useCallback(() => {
    if (playableSigns.length === 0) {
      returnToIdle()
      return
    }

    playbackQueueRef.current = [...playableSigns]
    playbackIndexRef.current = 0
    setActiveSignIndex(playableSigns[0].sourceIndex)
    playClip(playableSigns[0].name)
  }, [playClip, playableSigns, returnToIdle])

  useEffect(() => {
    const modelViewer = modelViewerRef.current
    if (!modelViewer) return
    let isActive = true

    const showModel = () => {
      setModelState('ready')
      setAvailableAnimations([...modelViewer.availableAnimations])
    }
    const showError = () => setModelState('error')
    const playNextClip = () => advanceSequenceRef.current()

    modelViewer.addEventListener('load', showModel)
    modelViewer.addEventListener('error', showError)
    modelViewer.addEventListener('finished', playNextClip)

    window.ModelViewerElement ??= {}
    window.ModelViewerElement.dracoDecoderLocation = '/draco/'

    void import('@google/model-viewer')
      .then(() => {
        if (isActive && modelViewer.loaded) showModel()
      })
      .catch(() => {
        if (isActive) showError()
      })

    return () => {
      isActive = false
      modelViewer.removeEventListener('load', showModel)
      modelViewer.removeEventListener('error', showError)
      modelViewer.removeEventListener('finished', playNextClip)
    }
  }, [])

  useEffect(() => {
    if (modelState === 'ready') playSequence()
  }, [modelState, playSequence])

  return (
    <aside className="avatar-panel" aria-labelledby="avatar-title">
      <div className="avatar-heading">
        <div>
          <span className="eyebrow">Sign support</span>
          <h2 id="avatar-title">Tutor Avatar</h2>
        </div>
        <span className="prototype-badge">3D preview</span>
      </div>

      <div className="avatar-stage">
        <div className="avatar-glow" aria-hidden="true" />

        {modelState === 'loading' && (
          <div className="avatar-model-status" aria-live="polite">
            <span className="avatar-loader" />
            Loading Louise…
          </div>
        )}

        {modelState === 'error' && (
          <div className="avatar-model-status avatar-model-error" role="alert">
            <strong>Avatar unavailable</strong>
            <span>The lesson content is still available.</span>
          </div>
        )}

        <model-viewer
          ref={modelViewerRef}
          className={`tutor-model ${modelState === 'ready' ? 'is-ready' : ''}`}
          src="/models/louise_tutor.glb"
          alt="Louise, the three-dimensional sign-supported mathematics tutor"
          loading="eager"
          reveal="auto"
          camera-controls
          disable-pan
          interaction-prompt="none"
          camera-target="0m 1.2m 0m"
          camera-orbit="0deg 82deg 3.2m"
          min-camera-orbit="-20deg 72deg 2.7m"
          max-camera-orbit="20deg 92deg 3.8m"
          field-of-view="28deg"
          min-field-of-view="25deg"
          max-field-of-view="32deg"
          shadow-intensity="0.65"
          shadow-softness="0.8"
          exposure="1.05"
          tone-mapping="commerce"
          aria-label="Interactive 3D view of Louise, the tutor avatar"
        />

        {modelState === 'ready' && (
          <span className="avatar-control-hint">Drag to turn the tutor</span>
        )}
      </div>

      <div className="sign-status" aria-live="polite">
        <span>Signs for this step</span>
        <div className="sign-list">
          {signActions.map((sign, index) => (
            <span
              className={`sign-chip ${availableAnimations.includes(sign) ? 'is-animated' : ''} ${activeSignIndex === index ? 'is-active' : ''}`}
              key={`${sign}-${index}`}
            >
              <span>{index + 1}</span>
              {sign.replaceAll('_', ' ')}
            </span>
          ))}
        </div>

        {playableSigns.length > 0 && (
          <button
            className="secondary-button replay-sign-button"
            onClick={playSequence}
            type="button"
          >
            Replay this step ({playableSigns.length} signs)
          </button>
        )}
      </div>

      <p className="avatar-note">
        {activeSign
          ? `Signing ${activeSign.replaceAll('_', ' ')}. Each clip is an approximate animation generated from the mathematics sign reference.`
          : playableSigns.length > 0
            ? 'This step is complete. Use replay to watch the full sign sequence again.'
            : 'Louise is ready. Animations for the remaining mathematics signs will be added next.'}
      </p>
    </aside>
  )
}
