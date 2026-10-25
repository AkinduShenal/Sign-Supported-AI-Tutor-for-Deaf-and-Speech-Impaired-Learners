import { useRef } from 'react'
import type { QuizLanguage } from './types'
import './BodmasReference.css'

type Operation = 'brackets' | 'orders' | 'division' | 'multiplication' | 'addition' | 'subtraction'

const steps: Array<{ letter: string; en: string; si: string; operation: Operation; rank: number }> = [
  { letter: 'B', en: 'Brackets', si: 'වරහන්', operation: 'brackets', rank: 1 },
  { letter: 'O', en: 'Orders', si: 'බල සහ වර්ගමූල', operation: 'orders', rank: 2 },
  { letter: 'D', en: 'Division', si: 'බෙදීම', operation: 'division', rank: 3 },
  { letter: 'M', en: 'Multiplication', si: 'ගුණ කිරීම', operation: 'multiplication', rank: 3 },
  { letter: 'A', en: 'Addition', si: 'එකතු කිරීම', operation: 'addition', rank: 4 },
  { letter: 'S', en: 'Subtraction', si: 'අඩු කිරීම', operation: 'subtraction', rank: 4 },
]

function OperationMark({ operation }: { operation: Operation }) {
  switch (operation) {
    case 'brackets':
      return <path d="M86 17c-10 0-10 12-10 19s0 19 10 19M98 17c10 0 10 12 10 19s0 19-10 19" />
    case 'orders':
      return <>
        <text x="81" y="51" fontSize="36">2</text>
        <text x="100" y="28" fontSize="19">3</text>
      </>
    case 'division':
      return <>
        <path d="M77 36h30" />
        <circle cx="92" cy="23" r="3" />
        <circle cx="92" cy="49" r="3" />
      </>
    case 'multiplication':
      return <path d="m80 24 24 24m0-24L80 48" />
    case 'addition':
      return <path d="M78 36h28M92 22v28" />
    case 'subtraction':
      return <path d="M78 36h28" />
  }
}

function StepGraphic({ letter, operation }: { letter: string; operation: Operation }) {
  return <svg className="bodmas-step-graphic" viewBox="0 0 120 72" aria-hidden="true" focusable="false">
    <circle className="bodmas-letter-disc" cx="31" cy="36" r="28" />
    <text className="bodmas-letter" x="31" y="48" textAnchor="middle">{letter}</text>
    <g className="bodmas-operation-mark" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
      <OperationMark operation={operation} />
    </g>
  </svg>
}

export function BodmasReference({ language }: { language: QuizLanguage }) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const showEnglish = language !== 'si'
  const showSinhala = language !== 'en'

  return <>
    <button
      className="bodmas-trigger"
      type="button"
      ref={triggerRef}
      onClick={() => dialogRef.current?.showModal()}
      aria-haspopup="dialog"
      aria-controls="bodmas-reference-dialog"
    >
      <svg viewBox="0 0 28 28" aria-hidden="true" focusable="false">
        <path d="M3 8h9M7.5 3.5v9M17 8h9M20 17h6M17 22h9" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
      <span>BODMAS</span>
    </button>

    <dialog
      className="bodmas-dialog"
      id="bodmas-reference-dialog"
      ref={dialogRef}
      aria-labelledby="bodmas-title"
      onClose={() => triggerRef.current?.focus()}
    >
      <div className="bodmas-dialog-header">
        <div>
          <span className="bodmas-eyebrow">{showEnglish ? 'Quick maths guide' : 'ගණිත මාර්ගෝපදේශය'}</span>
          <h2 id="bodmas-title">BODMAS</h2>
          <p>{showEnglish ? 'Order of operations' : 'ගණිත ක්‍රියා අනුපිළිවෙළ'}</p>
          {language === 'bilingual' && <p lang="si">ගණිත ක්‍රියා අනුපිළිවෙළ</p>}
        </div>
        <button className="bodmas-close" type="button" onClick={() => dialogRef.current?.close()} aria-label={showEnglish ? 'Close BODMAS guide' : 'BODMAS මාර්ගෝපදේශය වසන්න'}>
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M5 5l14 14M19 5 5 19" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      <ol className="bodmas-steps">
        {steps.map(step => <li className={`bodmas-step bodmas-step--${step.operation}`} key={step.letter}>
          <StepGraphic letter={step.letter} operation={step.operation} />
          <div className="bodmas-step-copy">
            <strong lang={showEnglish ? 'en' : 'si'}>{showEnglish ? step.en : step.si}</strong>
            {showSinhala && showEnglish && <span lang="si">{step.si}</span>}
            {!showEnglish && <span lang="en">{step.en}</span>}
          </div>
          <span className="bodmas-rank" aria-label={`${showEnglish ? 'Priority' : 'ප්‍රමුඛතාව'} ${step.rank}`}>{step.rank}</span>
        </li>)}
      </ol>

      <div className="bodmas-rule">
        {showEnglish && <p lang="en"><strong>Remember:</strong> D and M have equal priority. A and S have equal priority. Within each pair, work from left to right.</p>}
        {showSinhala && <p lang="si"><strong>මතක තබා ගන්න:</strong> බෙදීම සහ ගුණ කිරීම එකම ප්‍රමුඛතාවයේ ය. එකතු කිරීම සහ අඩු කිරීමත් එකම ප්‍රමුඛතාවයේ ය. එක් එක් යුගලයේ ක්‍රියා වමේ සිට දකුණට කරන්න.</p>}
      </div>
    </dialog>
  </>
}
