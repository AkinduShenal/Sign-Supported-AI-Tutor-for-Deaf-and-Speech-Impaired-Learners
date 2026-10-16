import type { ExplanationMotion } from '../types/tutor'

interface Props {
  motion: ExplanationMotion
  beatIndex: number
  expression?: string
  onSeek?: (time: number) => void
  clipTime?: number
}

export function AvatarMeaningBoard({ motion, beatIndex, expression, onSeek, clipTime = 0 }: Props) {
  const beat = motion.beats[beatIndex]
  const role = beat?.role ?? 'reference'
  const substitute = motion.kind.startsWith('substitute')
  const original = motion.original_expression ?? expression
  const current = substitute ? original : motion.current_expression ?? expression ?? original
  const replaced = role === 'replaced'
  const placement = role === 'place' && beat ? Math.max(0, Math.min(1, (clipTime - beat.start) / (beat.end - beat.start))) : 0
  const sides = current?.split('=')
  return <section className={`avatar-meaning-board meaning-${role}`} aria-label="Meaning of the explanation">
    {substitute ? <>
      <div className="meaning-equation-label" lang="si">මුල් සමීකරණය</div>
      <div className="meaning-original-equation">{original?.split(/(x)/).map((part, index) => part === 'x'
        ? <mark key={index} className={['variable', 'place', 'replaced'].includes(role) ? 'meaning-focus' : ''}>x</mark>
        : <span key={index}>{part}</span>) ?? 'x'}</div>
      <div className={`meaning-replacement ${replaced ? 'is-placed' : ''}`} aria-label={`Replace x with ${motion.value ?? 'the answer'}`}>
        <span className={role === 'value' ? 'meaning-focus' : ''} style={role === 'place' ? { transform: `translateX(${placement * 38}px)`, opacity: 1 - placement * .6 } : undefined}>{motion.value ?? 'පිළිතුර'}</span>
        <span aria-hidden="true">↓</span>
        <span className="meaning-x-slot">{replaced ? motion.value ?? 'පිළිතුර' : 'x'}</span>
      </div>
      {motion.substituted_expression && <div className={`meaning-result ${replaced ? 'is-visible' : ''}`} aria-hidden={!replaced}>
        <small lang="si">ආදේශ කළ පසු</small><strong>{replaced ? motion.substituted_expression : '\u00a0'}</strong>
      </div>}
    </> : current ? <>
      <div className="meaning-equation-label" lang="si">මේ පැහැදිලි කිරීමේ සමීකරණය</div>
      {sides?.length === 2 ? <div className={`meaning-equation-sides ${motion.kind === 'unbalanced' && role === 'one_side' ? 'is-unbalanced' : ''}`}>
        <span className={['left', 'both', 'balanced', 'equal', 'compare'].includes(role) ? 'meaning-focus' : ''}>{sides[0]}</span>
        <b>=</b>
        <span className={['right', 'both', 'balanced', 'equal', 'compare'].includes(role) ? 'meaning-focus' : ''}>{sides[1]}</span>
      </div> : <div className="meaning-original-equation">{current}</div>}
      {motion.kind === 'variable_not_multiply' && <div className="meaning-symbol-comparison">x <span>≠</span> ×</div>}
    </> : <div className="meaning-concept-symbol" aria-hidden="true">{
      motion.kind.includes('substitute') ? 'x → a' : motion.kind.includes('isolate') || motion.kind.includes('variable') ? 'x = ?'
      : motion.kind.includes('add') ? '+ ↔ −' : motion.kind.includes('subtract') ? '− ↔ +'
      : motion.kind.includes('divide') || motion.kind.includes('multiply') ? '× ↔ ÷'
      : motion.kind.includes('step') || motion.kind.includes('practice') ? '1 → 2 → 3' : 'වම් පස = දකුණු පස'
    }</div>}
    <div className="meaning-live-cue" role="status"><strong lang="si">{beat?.text_si}</strong><small lang="en">{beat?.text}</small></div>
    <ol className="meaning-beat-progress" aria-label="Explanation phrases">{motion.beats.map((part, index) =>
      <li key={`${part.role}-${index}`} className={index === beatIndex ? 'is-active' : index < beatIndex ? 'is-complete' : ''} aria-current={index === beatIndex ? 'step' : undefined} title={part.text_si}>
        <button type="button" disabled={!onSeek} onClick={() => onSeek?.(part.start)} aria-label={`Replay phrase ${index + 1}: ${part.text}`}><span>{index + 1}</span></button>
      </li>)}
    </ol>
  </section>
}
