import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ModelViewerElement } from '@google/model-viewer'
import { selectPlayback } from './playbackPolicy'

const MASTER_AVATAR_URL =
  '/models/louise_signs_master.glb?v=linear-equation-avatar-v1'
const BETWEEN_CLIP_DELAY_MS = 120
const EMPTY_SIGNS: string[] = []

export interface AvatarSignPlayerProps {
  signActions: string[]
  validatedSignIds?: string[]
  prototypeSignIds?: string[]
  allowPrototype?: boolean
  caption?: string
  onInteraction?: (action: string) => void
}

interface QueuedSign {
  name: string
  sourceIndex: number
}

export function AvatarSignPlayer({
  signActions,
  validatedSignIds = EMPTY_SIGNS,
  prototypeSignIds = EMPTY_SIGNS,
  allowPrototype = false,
  caption,
  onInteraction,
}: AvatarSignPlayerProps) {
  const modelViewerRef = useRef<ModelViewerElement>(null)
  const playbackQueueRef = useRef<QueuedSign[]>([])
  const playbackIndexRef = useRef(0)
  const advanceSequenceRef = useRef<() => void>(() => undefined)
  const transitionTimerRef = useRef<number | null>(null)
  const playbackRevision = useRef(0)
  const clipStarted = useRef(false)
  const [modelState, setModelState] = useState<'loading' | 'ready' | 'error'>(
    'loading',
  )
  const [availableAnimations, setAvailableAnimations] = useState<string[]>([])
  const [activeSignIndex, setActiveSignIndex] = useState<number | null>(null)
  const [paused, setPaused] = useState(false)
  const pausedRef = useRef(false)
  const pendingAdvance = useRef(false)
  const [speed, setSpeed] = useState(0.75)
  const speedRef = useRef(speed)
  const [autoPlay, setAutoPlay] = useState(() => !window.matchMedia('(prefers-reduced-motion: reduce)').matches)

  const validatedSet = useMemo(
    () => new Set(validatedSignIds),
    [validatedSignIds],
  )
  const prototypeSet = useMemo(
    () => new Set(prototypeSignIds),
    [prototypeSignIds],
  )
  const approvedForPlaybackSet = useMemo(
    () => new Set([...validatedSignIds, ...(allowPrototype ? prototypeSignIds : [])]),
    [allowPrototype, prototypeSignIds, validatedSignIds],
  )

  const requestedSigns = useMemo(() => signActions.map((name, sourceIndex) => ({ name, sourceIndex })), [signActions])

  const playableSigns = useMemo(
    () =>
      selectPlayback(signActions, availableAnimations, validatedSignIds, prototypeSignIds, allowPrototype),
    [signActions, availableAnimations, validatedSignIds, prototypeSignIds, allowPrototype],
  )

  const unavailableSigns = useMemo(
    () =>
      requestedSigns
        .filter(
          ({ name }) =>
            !approvedForPlaybackSet.has(name) ||
            (modelState !== 'loading' && !availableAnimations.includes(name)),
        )
        .map(({ name }) => name),
    [approvedForPlaybackSet, availableAnimations, modelState, requestedSigns],
  )

  const activeSign =
    activeSignIndex === null ? null : signActions[activeSignIndex]

  const clearTransitionTimer = useCallback(() => {
    if (transitionTimerRef.current !== null) {
      window.clearTimeout(transitionTimerRef.current)
      transitionTimerRef.current = null
    }
  }, [])

  const cancelPendingPlayback = useCallback(() => {
    playbackRevision.current++
  }, [])

  const playClip = useCallback(
    (animationName: string, repetitions = 1) => {
      const modelViewer = modelViewerRef.current
      if (!modelViewer) return
      const revision = ++playbackRevision.current
      clipStarted.current = false
      modelViewer.pause()
      // Blend existing tracks only; never rotate/re-target the skeleton at runtime.
      modelViewer.animationCrossfadeDuration = 200
      modelViewer.animationName = animationName
      // animationName updates asynchronously and resets loop options. Wait for
      // that update BEFORE setting time and repetitions, or the sequence loops.
      void modelViewer.updateComplete.then(() => {
        if (revision !== playbackRevision.current || modelViewer !== modelViewerRef.current) return
        modelViewer.timeScale = speedRef.current
        modelViewer.currentTime = 0
        modelViewer.play({ repetitions, pingpong: false })
        clipStarted.current = true
        if (pausedRef.current) modelViewer.pause()
      })
    },
    [],
  )

  const returnToIdle = useCallback(() => {
    clearTransitionTimer()
    playbackQueueRef.current = []
    playbackIndexRef.current = 0
    setActiveSignIndex(null)

    if (availableAnimations.includes('IDLE')) {
      playClip('IDLE', 1)
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
    pendingAdvance.current = false
    pausedRef.current = false
    setPaused(false)

    if (playableSigns.length === 0) {
      returnToIdle()
      return
    }

    modelViewerRef.current?.pause()
    playbackQueueRef.current = [...playableSigns]
    playbackIndexRef.current = 0
    setActiveSignIndex(playableSigns[0].sourceIndex)
    playClip(playableSigns[0].name, 1)
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
          `[AvatarSignPlayer] Master avatar is unavailable. Using text/visual fallback.`,
        )
      }
    }
    const playNextClip = () => {
      if (playbackQueueRef.current.length === 0 || !clipStarted.current) return
      clipStarted.current = false
      if (pausedRef.current) { pendingAdvance.current = true; return }
      clearTransitionTimer()
      transitionTimerRef.current = window.setTimeout(() => {
        transitionTimerRef.current = null
        if (pausedRef.current) pendingAdvance.current = true
        else advanceSequenceRef.current()
      }, BETWEEN_CLIP_DELAY_MS)
    }

    modelViewer.addEventListener('load', showModel)
    modelViewer.addEventListener('error', showError)
    modelViewer.addEventListener('finished', playNextClip)
    // Some model-viewer releases do not forward finished events from mixers
    // created after load. Observe actual playback time as a fallback, never a
    // wall-clock timeout (which would skip slow, paused or offscreen clips).
    const completionWatch = window.setInterval(() => {
      if (pausedRef.current || !clipStarted.current || playbackQueueRef.current.length === 0) return
      const clip = playbackQueueRef.current[playbackIndexRef.current]
      if (modelViewer.animationName === clip?.name && modelViewer.duration > 0 && modelViewer.currentTime >= modelViewer.duration - 0.005) playNextClip()
    }, 100)

    window.ModelViewerElement ??= {}
    window.ModelViewerElement.dracoDecoderLocation = '/draco/'

    void import('@google/model-viewer')
      .then(() => {
        if (isActive && modelViewer.loaded) showModel()
      })
      .catch(showError)

    return () => {
      isActive = false
      cancelPendingPlayback()
      window.clearInterval(completionWatch)
      clearTransitionTimer()
      modelViewer.removeEventListener('load', showModel)
      modelViewer.removeEventListener('error', showError)
      modelViewer.removeEventListener('finished', playNextClip)
    }
  }, [clearTransitionTimer, cancelPendingPlayback])

  useEffect(() => {
    if (modelState !== 'ready') return
    if (autoPlay) playSequence()
    else {
      playbackRevision.current++
      clearTransitionTimer()
      playbackQueueRef.current = []
      setActiveSignIndex(null)
      pausedRef.current = false
      setPaused(false)
      const viewer = modelViewerRef.current
      if (viewer) {
        viewer.pause()
        if (availableAnimations.includes('IDLE')) {
          const revision = playbackRevision.current
          viewer.animationName = 'IDLE'
          void viewer.updateComplete.then(() => {
            if (revision === playbackRevision.current) {
              // Apply the neutral clip without allowing a frame of motion.
              viewer.play({ repetitions: 1, pingpong: false })
              viewer.pause()
              viewer.currentTime = 0
            }
          })
        }
      }
    }
    return () => { cancelPendingPlayback(); clearTransitionTimer() }
  }, [modelState, playSequence, autoPlay, clearTransitionTimer, availableAnimations, cancelPendingPlayback])

  function togglePause() {
    const next = !pausedRef.current
    pausedRef.current = next
    setPaused(next)
    onInteraction?.(next ? 'avatar_pause' : 'avatar_resume')
    if (next) modelViewerRef.current?.pause()
    else if (pendingAdvance.current) {
      pendingAdvance.current = false
      advanceSequenceRef.current()
    } else modelViewerRef.current?.play({ repetitions: 1, pingpong: false })
  }

  useEffect(() => {
    if (!import.meta.env.DEV || requestedSigns.length === 0) return

    const unavailable = requestedSigns
      .map(({ name }) => name)
      .filter((name) => !approvedForPlaybackSet.has(name))
    const missing =
      modelState === 'ready'
        ? requestedSigns
            .map(({ name }) => name)
            .filter(
              (name) =>
                approvedForPlaybackSet.has(name) &&
                !availableAnimations.includes(name),
            )
        : []

    if (unavailable.length > 0) {
      console.warn(
        `[AvatarSignPlayer] Actions without an approved clip were skipped: ${unavailable.join(', ')}`,
      )
    }
    if (missing.length > 0) {
      console.warn(
        `[AvatarSignPlayer] Approved actions missing from master GLB: ${missing.join(', ')}`,
      )
    }
  }, [approvedForPlaybackSet, availableAnimations, modelState, requestedSigns])

  return (
    <aside className="avatar-panel" aria-labelledby="avatar-title">
      <div className="avatar-heading">
        <div>
          <span className="eyebrow">Sign support</span>
          <h2 id="avatar-title">Tutor Avatar</h2>
        </div>
        <span className="prototype-badge">{allowPrototype ? 'Prototype preview' : 'Validated clips only'}</span>
      </div>

      {caption && <p className="avatar-caption">{caption}</p>}
      <div className="avatar-playback-controls">
        <label>Speed <select aria-label="Avatar playback speed" value={speed} onChange={(event) => {
          const value = Number(event.target.value)
          setSpeed(value)
          speedRef.current = value
          if (modelViewerRef.current) modelViewerRef.current.timeScale = value
          onInteraction?.(`avatar_speed_${value}`)
        }}><option value={0.5}>0.5×</option><option value={0.75}>0.75×</option><option value={1}>1×</option></select></label>
        <label><input type="checkbox" checked={autoPlay} onChange={(event) => setAutoPlay(event.target.checked)} /> Auto-play</label>
        <button type="button" className="secondary-button" disabled={activeSignIndex === null} onClick={togglePause}>{paused ? 'Resume' : 'Pause'}</button>
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
            <strong>Avatar gesture clips are not available</strong>
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
              approvedForPlaybackSet.has(sign) &&
              availableAnimations.includes(sign)
            const isValidated = validatedSet.has(sign)
            const isPrototype = prototypeSet.has(sign)
            return (
              <span
                className={`sign-chip ${isPlayable ? 'is-animated' : 'is-unavailable'} ${activeSignIndex === index ? 'is-active' : ''}`}
                key={`${sign}-${index}`}
                title={
                  isPlayable
                    ? isValidated
                      ? 'Validated animation available'
                      : isPrototype
                        ? 'Prototype educational gesture available'
                        : 'Animation available'
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
              Missing or unavailable clips are not fabricated. Follow the
              written instruction and equation.
            </span>
          </div>
        )}

        {playableSigns.length > 0 && (
          <button
            className="secondary-button replay-sign-button"
            onClick={() => { onInteraction?.('avatar_replay'); playSequence() }}
            type="button"
          >
            Replay gestures ({playableSigns.length})
          </button>
        )}
      </div>

      <p className="avatar-note">
        {activeSign
          ? `Playing ${activeSign.replaceAll('_', ' ')} educational gesture.`
          : playableSigns.length > 0
            ? 'The gesture sequence is complete. Use replay to watch it again.'
            : 'No animation is available for this step. The lesson remains available as text and visual mathematics support.'}
      </p>
      <p className="avatar-language-notice">
        {allowPrototype ? 'Prototype educational gestures — not validated Sri Lankan Sign Language. They support key terms, not full sentence translation.' : 'Only human-validated signs are enabled. Unvalidated or missing signs use the written lesson and equations.'}
      </p>
    </aside>
  )
}
