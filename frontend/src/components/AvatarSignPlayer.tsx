import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ModelViewerElement } from '@google/model-viewer'

const MASTER_AVATAR_URL =
  '/models/louise_signs_master.glb?v=avatar-sign-package-v1'
const BETWEEN_CLIP_DELAY_MS = 120

export interface AvatarSignPlayerProps {
  signActions: string[]
  validatedSignIds?: string[]
}

interface QueuedSign {
  name: string
  sourceIndex: number
}

export function AvatarSignPlayer({
  signActions,
  validatedSignIds = [],
}: AvatarSignPlayerProps) {
  const modelViewerRef = useRef<ModelViewerElement>(null)
  const playbackQueueRef = useRef<QueuedSign[]>([])
  const playbackIndexRef = useRef(0)
  const advanceSequenceRef = useRef<() => void>(() => undefined)
  const transitionTimerRef = useRef<number | null>(null)
  const [modelState, setModelState] = useState<'loading' | 'ready' | 'error'>(
    'loading',
  )
  const [availableAnimations, setAvailableAnimations] = useState<string[]>([])
  const [activeSignIndex, setActiveSignIndex] = useState<number | null>(null)

  const validatedSet = useMemo(
    () => new Set(validatedSignIds),
    [validatedSignIds],
  )

  const requestedSigns = useMemo(() => {
    const seen = new Set<string>()
    return signActions
      .map((name, sourceIndex) => ({ name, sourceIndex }))
      .filter(({ name }) => {
        if (seen.has(name)) return false
        seen.add(name)
        return true
      })
  }, [signActions])

  const playableSigns = useMemo(
    () =>
      requestedSigns.filter(
        ({ name }) =>
          validatedSet.has(name) && availableAnimations.includes(name),
      ),
    [availableAnimations, requestedSigns, validatedSet],
  )

  const unavailableSigns = useMemo(
    () =>
      requestedSigns
        .filter(
          ({ name }) =>
            !validatedSet.has(name) ||
            (modelState !== 'loading' && !availableAnimations.includes(name)),
        )
        .map(({ name }) => name),
    [availableAnimations, modelState, requestedSigns, validatedSet],
  )

  const activeSign =
    activeSignIndex === null ? null : signActions[activeSignIndex]

  const clearTransitionTimer = useCallback(() => {
    if (transitionTimerRef.current !== null) {
      window.clearTimeout(transitionTimerRef.current)
      transitionTimerRef.current = null
    }
  }, [])

  const playClip = useCallback(
    (animationName: string, repetitions = 1, forceRestart = false) => {
      const modelViewer = modelViewerRef.current
      if (!modelViewer) return

      if (forceRestart) modelViewer.pause()
      modelViewer.animationName = animationName
      modelViewer.currentTime = 0
      modelViewer.play({ repetitions, pingpong: false })
    },
    [],
  )

  const returnToIdle = useCallback(() => {
    clearTransitionTimer()
    playbackQueueRef.current = []
    playbackIndexRef.current = 0
    setActiveSignIndex(null)

    if (availableAnimations.includes('IDLE')) {
      playClip('IDLE', Infinity)
    }
  }, [availableAnimations, clearTransitionTimer, playClip])

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
    clearTransitionTimer()

    if (playableSigns.length === 0) {
      returnToIdle()
      return
    }

    modelViewerRef.current?.pause()
    playbackQueueRef.current = [...playableSigns]
    playbackIndexRef.current = 0
    setActiveSignIndex(playableSigns[0].sourceIndex)
    playClip(playableSigns[0].name, 1, true)
  }, [clearTransitionTimer, playClip, playableSigns, returnToIdle])

  useEffect(() => {
    const modelViewer = modelViewerRef.current
    if (!modelViewer) return
    let isActive = true

    const showModel = () => {
      if (!isActive) return
      setModelState('ready')
      setAvailableAnimations([...modelViewer.availableAnimations])
    }
    const showError = () => {
      if (!isActive) return
      setModelState('error')
      setAvailableAnimations([])
      if (import.meta.env.DEV) {
        console.warn(
          `[AvatarSignPlayer] Master avatar is unavailable at ${MASTER_AVATAR_URL}. Requested actions will use text/visual fallback: ${signActions.join(', ') || 'none'}`,
        )
      }
    }
    const playNextClip = () => {
      if (playbackQueueRef.current.length === 0) return
      clearTransitionTimer()
      transitionTimerRef.current = window.setTimeout(() => {
        transitionTimerRef.current = null
        advanceSequenceRef.current()
      }, BETWEEN_CLIP_DELAY_MS)
    }

    modelViewer.addEventListener('load', showModel)
    modelViewer.addEventListener('error', showError)
    modelViewer.addEventListener('finished', playNextClip)

    window.ModelViewerElement ??= {}
    window.ModelViewerElement.dracoDecoderLocation = '/draco/'

    void import('@google/model-viewer')
      .then(() => {
        if (isActive && modelViewer.loaded) showModel()
      })
      .catch(showError)

    return () => {
      isActive = false
      clearTransitionTimer()
      modelViewer.removeEventListener('load', showModel)
      modelViewer.removeEventListener('error', showError)
      modelViewer.removeEventListener('finished', playNextClip)
    }
  }, [clearTransitionTimer, signActions])

  useEffect(() => {
    if (modelState === 'ready') playSequence()
  }, [modelState, playSequence])

  useEffect(() => {
    if (!import.meta.env.DEV || requestedSigns.length === 0) return

    const unvalidated = requestedSigns
      .map(({ name }) => name)
      .filter((name) => !validatedSet.has(name))
    const missing =
      modelState === 'ready'
        ? requestedSigns
            .map(({ name }) => name)
            .filter(
              (name) =>
                validatedSet.has(name) && !availableAnimations.includes(name),
            )
        : []

    if (unvalidated.length > 0) {
      console.warn(
        `[AvatarSignPlayer] Unvalidated actions skipped: ${unvalidated.join(', ')}`,
      )
    }
    if (missing.length > 0) {
      console.warn(
        `[AvatarSignPlayer] Validated actions missing from master GLB: ${missing.join(', ')}`,
      )
    }
  }, [availableAnimations, modelState, requestedSigns, validatedSet])

  return (
    <aside className="avatar-panel" aria-labelledby="avatar-title">
      <div className="avatar-heading">
        <div>
          <span className="eyebrow">Sign support</span>
          <h2 id="avatar-title">Tutor Avatar</h2>
        </div>
        <span className="prototype-badge">Validated clips</span>
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
            <strong>Validated avatar clips are not available yet</strong>
            <span>Continue with the lesson text and equation visuals.</span>
          </div>
        )}

        <model-viewer
          ref={modelViewerRef}
          className={`tutor-model ${modelState === 'ready' ? 'is-ready' : ''}`}
          src={MASTER_AVATAR_URL}
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
          {signActions.map((sign, index) => {
            const isPlayable =
              validatedSet.has(sign) && availableAnimations.includes(sign)
            return (
              <span
                className={`sign-chip ${isPlayable ? 'is-animated' : 'is-unavailable'} ${activeSignIndex === index ? 'is-active' : ''}`}
                key={`${sign}-${index}`}
                title={
                  isPlayable
                    ? 'Validated animation available'
                    : 'Using text/visual fallback'
                }
              >
                <span>{index + 1}</span>
                {sign.replaceAll('_', ' ')}
              </span>
            )
          })}
        </div>

        {unavailableSigns.length > 0 && (
          <div className="sign-fallback" role="status">
            <strong>Text/visual support active</strong>
            <span>
              Unvalidated or missing clips are not played. Follow the written
              instruction and equation.
            </span>
          </div>
        )}

        {playableSigns.length > 0 && (
          <button
            className="secondary-button replay-sign-button"
            onClick={playSequence}
            type="button"
          >
            Replay validated signs ({playableSigns.length})
          </button>
        )}
      </div>

      <p className="avatar-note">
        {activeSign
          ? `Signing validated action ${activeSign.replaceAll('_', ' ')}.`
          : playableSigns.length > 0
            ? 'The validated sequence is complete. Use replay to watch it again.'
            : 'No validated animation is available for this step. The lesson remains available as text and visual mathematics support.'}
      </p>
    </aside>
  )
}
