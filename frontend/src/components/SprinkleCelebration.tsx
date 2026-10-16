import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { SPRINKLE_EVENT, type SprinkleEventDetail, type SprinkleMoment } from './sprinkleEvent'
import './SprinkleCelebration.css'

const COLORS = ['#6254ec', '#21bba9', '#ffc34f', '#ff7189', '#4e9cf5']
const SIDES = ['left', 'right'] as const

const PIECES = Array.from({ length: 30 }, (_, index) => ({
  distance: 11 + (index % 8) * 4.5,
  height: 25 + ((index * 7) % 13) * 3.2,
  delay: (index % 5) * 24,
  spin: (index % 2 ? -1 : 1) * (150 + (index % 5) * 35),
  color: COLORS[index % COLORS.length],
  shape: index % 5 === 0 ? 'dot' : 'sprinkle',
}))

interface Burst {
  id: number
  moment: SprinkleMoment
}

export function SprinkleCelebration() {
  const [burst, setBurst] = useState<Burst | null>(null)
  const nextId = useRef(0)
  const seenWins = useRef(new Set<string>())

  useEffect(() => {
    let clearTimer: number | undefined
    const onSprinkle = (event: Event) => {
      const { moment, sourceId } = (event as CustomEvent<SprinkleEventDetail>).detail
      if (moment !== 'answer' && moment !== 'win') return
      if (moment === 'win' && sourceId) {
        if (seenWins.current.has(sourceId)) return
        seenWins.current.add(sourceId)
      }
      window.clearTimeout(clearTimer)
      nextId.current += 1
      setBurst({ id: nextId.current, moment })
      clearTimer = window.setTimeout(() => setBurst(null), moment === 'win' ? 1900 : 1350)
    }
    window.addEventListener(SPRINKLE_EVENT, onSprinkle)
    return () => {
      window.removeEventListener(SPRINKLE_EVENT, onSprinkle)
      window.clearTimeout(clearTimer)
    }
  }, [])

  if (!burst) return null

  return <div className={`sprinkle-celebration sprinkle-celebration--${burst.moment}`} aria-hidden="true" key={burst.id}>
    {SIDES.map((side) => <svg className={`sprinkle-burst sprinkle-burst--${side}`} viewBox="0 0 24 24" focusable="false" role="presentation" key={side}>
      <path className="sprinkle-flash" d="M12 2v5M12 17v5M2 12h5M17 12h5M4.9 4.9l3.5 3.5M15.6 15.6l3.5 3.5M19.1 4.9l-3.5 3.5M8.4 15.6l-3.5 3.5" fill="none" stroke="#ffc34f" strokeWidth="2" strokeLinecap="round" />
      {PIECES.map((piece, index) => {
        const direction = side === 'left' ? 1 : -1
        const distance = piece.distance * (burst.moment === 'win' ? 1.3 : 1)
        const style = {
          '--mid-x': `${direction * distance * 0.56}vw`,
          '--mid-y': `${-piece.height * 0.85}vh`,
          '--end-x': `${direction * distance}vw`,
          '--end-y': `${-piece.height * 0.45}vh`,
          '--delay': `${piece.delay + (side === 'right' ? 45 : 0)}ms`,
          '--mid-spin': `${piece.spin * 0.55}deg`,
          '--spin': `${piece.spin}deg`,
        } as CSSProperties
        return <g key={index} style={style}>
          {piece.shape === 'dot' ? (
            <circle className="sprinkle-piece" cx="12" cy="12" r="3.5" fill={piece.color} />
          ) : (
            <rect className="sprinkle-piece" x="9" y="6" width="6" height="12" rx="2.5" fill={piece.color} />
          )}
        </g>
      })}
    </svg>)}
  </div>
}
