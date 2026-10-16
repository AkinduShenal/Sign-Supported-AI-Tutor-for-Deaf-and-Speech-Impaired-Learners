import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ModelViewerElement } from '@google/model-viewer'
import { selectPlayback } from './playbackPolicy'
import { SinhalaText } from './SinhalaText'
import { AvatarMeaningBoard } from './AvatarMeaningBoard'
import { motionBeatIndex } from './motionTiming'
import type { AvatarTeachingSegment, SignReference } from '../types/tutor'

const MASTER_AVATAR_URL =
  '/models/louise_signs_master.glb?v=meaning-flows-v7'
const BETWEEN_CLIP_DELAY_MS = 120
const EMPTY_SIGNS: string[] = []
const EMPTY_SEGMENTS: AvatarTeachingSegment[] = []

export interface AvatarSignPlayerProps {
  signActions: string[]
  validatedSignIds?: string[]
  prototypeSignIds?: string[]
  reviewSignIds?: string[]
  allowPrototype?: boolean
  caption?: string
  expression?: string
  compact?: boolean
  onEnablePrototype?: () => void
  onInteraction?: (action: string) => void
  teachingSegments?: AvatarTeachingSegment[]
  teachingKey?: string
  teachingApproach?: string
  initialPlaybackSpeed?: number
  signReferences?: SignReference[]
}

interface QueuedSign {
  name: string
  sourceIndex: number
}

export function AvatarSignPlayer({
  signActions,
  validatedSignIds = EMPTY_SIGNS,
  prototypeSignIds = EMPTY_SIGNS,
  reviewSignIds = EMPTY_SIGNS,
  allowPrototype = false,
  caption: fallbackCaption,
  expression: fallbackExpression,
  compact = false,
  onEnablePrototype,
  onInteraction,
  teachingSegments = EMPTY_SEGMENTS,
  teachingKey = '',
  teachingApproach,
  initialPlaybackSpeed = 1,
  signReferences = [],
}: AvatarSignPlayerProps) {
  // Derive part zero immediately when the lesson/step/hint changes, so an old
  // caption or solution cannot leak into the new context for a render.
  const contextKey = teachingKey || teachingSegments.map(segment => `${segment.text}:${segment.expression ?? ''}`).join('\0')
  const [teachingPosition, setTeachingPosition] = useState({ key: contextKey, index: 0 })
  const teachingIndex = teachingPosition.key === contextKey ? teachingPosition.index : 0
  const currentSegment = teachingSegments[teachingIndex]
  const expressionTokens = currentSegment?.expression_tokens ?? []
  const caption = currentSegment?.text ?? fallbackCaption
  const captionSi = currentSegment?.text_si
  const expression = currentSegment?.expression ?? fallbackExpression
  const lessonSignActions = currentSegment?.sign_actions ?? signActions
  const modelViewerRef = useRef<ModelViewerElement>(null)
  const playbackQueueRef = useRef<QueuedSign[]>([])
  const playbackIndexRef = useRef(0)
  const advanceSequenceRef = useRef<() => void>(() => undefined)
  const finishTeachingPartRef = useRef<() => void>(() => undefined)
  const singleReplayRef = useRef(false)
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
  const [speed, setSpeed] = useState(initialPlaybackSpeed)
  const speedRef = useRef(speed)
  const [autoPlay, setAutoPlay] = useState(() => !window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  const [reviewSign, setReviewSign] = useState('')
  const [closeView, setCloseView] = useState(false)
  const signActionsKey = `${contextKey}:${teachingIndex}:${lessonSignActions.join('\0')}`
  const [playbackClock, setPlaybackClock] = useState({ key: signActionsKey, time: 0 })
  const clockKeyRef = useRef(signActionsKey)
  const clipTime = playbackClock.key === signActionsKey ? playbackClock.time : 0
  const motion = !reviewSign ? currentSegment?.motion : undefined
  const beatIndex = motion ? motionBeatIndex(motion.beats, clipTime) : -1
  const effectiveSignActions = useMemo(
    () => (reviewSign ? [reviewSign] : lessonSignActions),
    [reviewSign, lessonSignActions],
  )

  const selectTeachingPart = useCallback((index: number) => {
    setTeachingPosition({ key: contextKey, index })
    onInteraction?.(`avatar_explanation_part_${index + 1}`)
  }, [contextKey, onInteraction])

  useEffect(() => {
    setTeachingPosition({ key: contextKey, index: 0 })
  }, [contextKey])

  useEffect(() => {
    finishTeachingPartRef.current = () => {
      const complete = !currentSegment?.unsupported_tokens?.length && lessonSignActions.every(name =>
        availableAnimations.includes(name) && (validatedSignIds.includes(name) || (allowPrototype && prototypeSignIds.includes(name))))
      // Leave a completed substitution on its original → replacement diagram;
      // the learner chooses when to read the resulting expression.
      const holdResult = currentSegment?.motion?.kind.startsWith('substitute')
      if (complete && !holdResult && !singleReplayRef.current && autoPlay && !reviewSign && teachingIndex + 1 < teachingSegments.length) {
        selectTeachingPart(teachingIndex + 1)
      }
    }
  }, [autoPlay, reviewSign, teachingIndex, teachingSegments.length, selectTeachingPart, currentSegment, lessonSignActions, availableAnimations, validatedSignIds, allowPrototype, prototypeSignIds])

  useEffect(() => {
    clockKeyRef.current = signActionsKey
    setReviewSign('')
  }, [signActionsKey])

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

  const requestedSigns = useMemo(() => effectiveSignActions.map((name, sourceIndex) => ({ name, sourceIndex })), [effectiveSignActions])

  const playableSigns = useMemo(
    () =>
      selectPlayback(effectiveSignActions, availableAnimations, validatedSignIds, prototypeSignIds, allowPrototype),
    [effectiveSignActions, availableAnimations, validatedSignIds, prototypeSignIds, allowPrototype],
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
    activeSignIndex === null ? null : effectiveSignActions[activeSignIndex]
  const relevantReferences = signReferences.filter(reference => effectiveSignActions.includes(reference.sign_id) && reference.reference_videos?.length)

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
      // Advance only after actual clip completion, never a guessed duration.
      // Empty/missing/unvalidated sequences remain on their written explanation.
      finishTeachingPartRef.current()
      return
    }

    playbackIndexRef.current = nextIndex
    const nextSign = playbackQueueRef.current[nextIndex]
    setActiveSignIndex(nextSign.sourceIndex)
    playClip(nextSign.name)
  }, [playClip, returnToIdle])

  advanceSequenceRef.current = advanceSequence

  const playSequence = useCallback((sourceIndex = 0, single = false) => {
    clearTransitionTimer()
    pendingAdvance.current = false
    pausedRef.current = false
    setPaused(false)
    singleReplayRef.current = single
    setPlaybackClock({ key: signActionsKey, time: 0 })

    if (playableSigns.length === 0) {
      returnToIdle()
      return
    }

    modelViewerRef.current?.pause()
    const queue = single ? playableSigns.filter(sign => sign.sourceIndex === sourceIndex) : playableSigns.filter(sign => sign.sourceIndex >= sourceIndex)
    if (!queue.length) { returnToIdle(); return }
    // A token replay should remain on this part after it completes.
    playbackQueueRef.current = queue
    playbackIndexRef.current = 0
    setActiveSignIndex(queue[0].sourceIndex)
    playClip(queue[0].name, 1)
  }, [clearTransitionTimer, playClip, playableSigns, returnToIdle, signActionsKey])

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
      if (modelViewer.animationName === clip?.name) setPlaybackClock({ key: clockKeyRef.current, time: modelViewer.currentTime })
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
  }, [modelState, playSequence, autoPlay, clearTransitionTimer, availableAnimations, cancelPendingPlayback, signActionsKey])

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

  function seekMeaningBeat(time: number) {
    const viewer = modelViewerRef.current
    if (!viewer || !motion || !playableSigns.some(sign => sign.name === motion.clip)) return
    playSequence(0, true)
    const revision = playbackRevision.current
    void viewer.updateComplete.then(() => {
      if (revision !== playbackRevision.current) return
      viewer.currentTime = time
      setPlaybackClock({ key: signActionsKey, time })
      onInteraction?.(`avatar_phrase_${motionBeatIndex(motion.beats, time) + 1}`)
    })
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
    <aside className={`avatar-panel ${compact ? 'avatar-compact' : ''}`} aria-labelledby="avatar-title">
      <div className="avatar-heading">
        <div>
          {!compact && <span className="eyebrow">Sign support</span>}
          <h2 id="avatar-title">{compact ? 'Avatar' : 'Tutor Avatar'}</h2>
        </div>
      </div>

      {teachingSegments.length > 0 && !reviewSign && <div className="avatar-teaching" aria-live="polite">
        <div className="avatar-teaching-heading"><strong>{teachingApproach ?? 'Explanation'}</strong><span>{teachingIndex + 1} / {teachingSegments.length}</span></div>
        {caption && <p className="avatar-caption" lang="en">{caption}</p>}
        {captionSi ? <p className="sinhala-text" lang="si">{captionSi}</p> : caption && <SinhalaText text={caption} />}
        {motion && <AvatarMeaningBoard motion={motion} beatIndex={beatIndex} expression={expression} clipTime={clipTime}
          onSeek={modelState === 'ready' && playableSigns.some(sign => sign.name === motion.clip) ? seekMeaningBeat : undefined} />}
        {!motion && expression && <p className="avatar-expression" aria-label={`Current equation: ${expression}`}>
          {expressionTokens.length > 0 ? expressionTokens.map((token, index) => {
            const playable = token.action_index !== null && playableSigns.some(sign => sign.sourceIndex === token.action_index)
            return <span key={`${token.start}-${index}`}>
              {index > 0 && expression.slice(expressionTokens[index - 1].end, token.start)}
              <button type="button" className={`equation-token ${activeSignIndex !== null && token.action_index === activeSignIndex ? 'is-active' : ''}`}
                disabled={!playable} aria-label={`Replay ${token.text}`} aria-current={activeSignIndex !== null && token.action_index === activeSignIndex ? 'step' : undefined}
                title={playable ? `Replay ${token.text}` : 'Read this symbol in the equation'}
                onClick={() => { onInteraction?.(`avatar_token_${index}`); playSequence(token.action_index!, true) }}>{token.text}</button>
            </span>
          }) : expression}
        </p>}
        {!!currentSegment?.unsupported_tokens?.length && <p className="avatar-token-fallback" role="status">Read these in the equation / සමීකරණයෙන් කියවන්න: {currentSegment.unsupported_tokens.join(', ')}</p>}
        <div className="avatar-part-controls">
          <button type="button" className="secondary-button" disabled={teachingIndex === 0} onClick={() => selectTeachingPart(teachingIndex - 1)}>Previous part / පෙර කොටස</button>
          <button type="button" className="secondary-button" disabled={teachingIndex + 1 >= teachingSegments.length} onClick={() => selectTeachingPart(teachingIndex + 1)}>Next part / ඊළඟ කොටස</button>
        </div>
      </div>}

      {!compact && teachingSegments.length === 0 && caption && <p className="avatar-caption" lang="en">{caption}</p>}
      {!compact && teachingSegments.length === 0 && caption && <SinhalaText text={caption} />}
      {!compact && teachingSegments.length === 0 && expression && <p className="avatar-expression" aria-label={`Current equation: ${expression}`}>{expression}</p>}

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
          camera-target={closeView ? '0m 1.38m 0.10m' : '0m 1.28m 0.05m'}
          camera-orbit="0deg 88deg 2.2m"
          min-camera-orbit="-20deg 78deg 2.2m"
          max-camera-orbit="20deg 92deg 2.8m"
          field-of-view={closeView ? '21deg' : '26deg'}
          min-field-of-view="21deg"
          max-field-of-view="30deg"
          shadow-intensity="0.65"
          shadow-softness="0.8"
          exposure="1.05"
          tone-mapping="commerce"
          aria-label="Interactive 3D view of Louise, the tutor avatar"
        />

        {!compact && modelState === 'ready' && (
          <span className="avatar-control-hint">Drag to turn the tutor</span>
        )}
      </div>

      {compact && !allowPrototype && prototypeSignIds.length > 0 && playableSigns.length === 0 && modelState === 'ready' && (
        <div className="avatar-preview-prompt">
          <button type="button" className="primary-button" onClick={onEnablePrototype}>Preview gestures</button>
        </div>
      )}
      {playableSigns.length > 0 && modelState === 'ready' && (
        <div className="avatar-main-controls">
          <button className="secondary-button replay-sign-button" onClick={() => { onInteraction?.('avatar_replay'); playSequence() }} type="button">{compact ? 'Replay' : `Replay gestures (${playableSigns.length})`}</button>
          <button type="button" className="secondary-button" disabled={activeSignIndex === null} onClick={togglePause}>{paused ? 'Resume' : 'Pause'}</button>
        </div>
      )}
      {compact && allowPrototype && <p className="avatar-preview-note">Demo gestures · not yet validated sign language.</p>}
      {compact && activeSign && <p className="avatar-current-token" role="status">{motion ? motion.beats[beatIndex]?.text_si : expressionTokens.find(token => token.action_index === activeSignIndex)?.text ?? activeSign.replaceAll('_', ' ')} <span>· {motion ? `${beatIndex + 1} / ${motion.beats.length}` : `${(activeSignIndex ?? 0) + 1} / ${effectiveSignActions.length}`}</span></p>}
      <label className="avatar-close-view"><input type="checkbox" checked={closeView} onChange={event => setCloseView(event.target.checked)} /> Closer view of hands / අත් සමීපව බලන්න</label>
      {relevantReferences.length > 0 && <details className="avatar-source-references">
        <summary>Watch SLSL references / මූලාශ්‍ර සංඥා බලන්න</summary>
        <p>Compare the human sign demonstrations. Avatar clips still need SLSL review.</p>
        {relevantReferences.map(reference => <div key={reference.sign_id}>
          <strong>{reference.label}</strong>
          {reference.reference_videos?.map(video => <a key={video.url} href={video.url} target="_blank" rel="noreferrer">{video.source} · {video.title}</a>)}
        </div>)}
      </details>}
      {compact && modelState === 'ready' && playableSigns.length === 0 && (allowPrototype || prototypeSignIds.length === 0) && <p className="avatar-preview-note" role="status">No gesture for this step. Follow the written hint.</p>}

      <details className="avatar-options" open={compact ? undefined : true}>
        <summary>Playback settings & sign details</summary>
        {compact && reviewSignIds.length > 0 && (
          <label className="animation-review-picker">
            <span>
              <strong>New animation examples</strong>
              <small>Choose one of the new review-only prototype actions.</small>
            </span>
            <select
              aria-label="New animation example"
              value={reviewSign}
              onChange={(event) => {
                const nextSign = event.target.value
                setReviewSign(nextSign)
                onInteraction?.(nextSign ? `avatar_review_${nextSign}` : 'avatar_review_lesson')
                if (nextSign && !allowPrototype) onEnablePrototype?.()
              }}
            >
              <option value="">Current lesson signs</option>
              {reviewSignIds.map((sign) => (
                <option key={sign} value={sign}>{sign.replaceAll('_', ' ')}</option>
              ))}
            </select>
          </label>
        )}
        <div className="avatar-playback-controls">
          <label>Speed <select aria-label="Avatar playback speed" value={speed} onChange={(event) => {
            const value = Number(event.target.value)
            setSpeed(value)
            speedRef.current = value
            if (modelViewerRef.current) modelViewerRef.current.timeScale = value
            onInteraction?.(`avatar_speed_${value}`)
          }}><option value={0.5}>0.5×</option><option value={0.75}>0.75×</option><option value={1}>1×</option></select></label>
          <label><input type="checkbox" checked={autoPlay} onChange={(event) => setAutoPlay(event.target.checked)} /> Auto-play</label>
        </div>
        {reviewSign ? (
          <div className="animation-review-note" role="status">
            <strong>Previewing: {reviewSign.replaceAll('_', ' ')}</strong>
            <span>This is an unvalidated educational gesture for technical review.</span>
          </div>
        ) : (
          <>
            {compact && teachingSegments.length === 0 && caption && <p className="avatar-caption" lang="en">{caption}</p>}
            {compact && teachingSegments.length === 0 && caption && <SinhalaText text={caption} />}
            {compact && teachingSegments.length === 0 && expression && <p className="avatar-expression">{expression}</p>}
          </>
        )}
      <div className="sign-status" aria-live="polite">
        <span>{reviewSign ? 'Selected animation example' : teachingSegments.length > 0 ? `Gestures for explanation part ${teachingIndex + 1}` : 'Signs for this step'}</span>
        <div className="sign-list">
          {effectiveSignActions.map((sign, index) => {
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

      </div>

      <p className="avatar-note">
        {activeSign
          ? `Playing ${activeSign.replaceAll('_', ' ')} educational gesture.`
          : playableSigns.length > 0
            ? teachingSegments.length > 0 && teachingIndex + 1 < teachingSegments.length
              ? 'Replay this part or continue to the next explanation part.'
              : 'The gesture sequence is complete. Use replay to watch it again.'
            : 'No animation is available for this step. The lesson remains available as text and visual mathematics support.'}
      </p>
      <p className="avatar-language-notice">
        {allowPrototype ? 'Prototype educational gestures — not validated Sri Lankan Sign Language. They support key terms, not full sentence translation.' : 'Only human-validated signs are enabled. Unvalidated or missing signs use the written lesson and equations.'}
      </p>
      </details>
    </aside>
  )
}
