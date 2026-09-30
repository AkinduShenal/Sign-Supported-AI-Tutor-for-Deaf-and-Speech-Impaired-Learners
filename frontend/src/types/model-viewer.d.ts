import type { ModelViewerElement } from '@google/model-viewer'
import type { DetailedHTMLProps, HTMLAttributes } from 'react'

declare module 'react' {
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': DetailedHTMLProps<
        HTMLAttributes<ModelViewerElement>,
        ModelViewerElement
      > & {
        src?: string
        alt?: string
        loading?: 'auto' | 'lazy' | 'eager'
        reveal?: 'auto' | 'manual'
        'camera-controls'?: boolean
        'disable-pan'?: boolean
        'interaction-prompt'?: 'auto' | 'none'
        'camera-target'?: string
        'camera-orbit'?: string
        'min-camera-orbit'?: string
        'max-camera-orbit'?: string
        'field-of-view'?: string
        'min-field-of-view'?: string
        'max-field-of-view'?: string
        'shadow-intensity'?: string
        'shadow-softness'?: string
        exposure?: string
        'tone-mapping'?: string
      }
    }
  }
}

declare global {
  interface Window {
    ModelViewerElement?: {
      dracoDecoderLocation?: string
    }
  }
}

export {}
