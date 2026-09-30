import { useEffect, useRef, useState } from 'react'
import type { ModelViewerElement } from '@google/model-viewer'

interface TutorAvatarProps {
  signActions: string[]
}

export function TutorAvatar({ signActions }: TutorAvatarProps) {
  const modelViewerRef = useRef<ModelViewerElement>(null)
  const [modelState, setModelState] = useState<'loading' | 'ready' | 'error'>(
    'loading',
  )

  useEffect(() => {
    const modelViewer = modelViewerRef.current
    if (!modelViewer) return
    let isActive = true

    const showModel = () => setModelState('ready')
    const showError = () => setModelState('error')

    modelViewer.addEventListener('load', showModel)
    modelViewer.addEventListener('error', showError)

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
    }
  }, [])

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
            <span className="sign-chip" key={sign}>
              <span>{index + 1}</span>
              {sign.replaceAll('_', ' ')}
            </span>
          ))}
        </div>
      </div>

      <p className="avatar-note">
        Louise is ready. The validated mathematics sign animations will be
        connected to each lesson step next.
      </p>
    </aside>
  )
}
