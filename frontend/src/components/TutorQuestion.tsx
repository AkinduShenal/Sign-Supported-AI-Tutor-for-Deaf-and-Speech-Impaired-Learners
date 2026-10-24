import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { askTutorQuestion } from '../api/tutor'
import type { LearningLevel, TeachingStrategy, TutorQuestionAnswer } from '../types/tutor'

interface Props {
  level: LearningLevel
  strategy: TeachingStrategy
  exampleProblem: string
  stepIndex: number
  onHelpUsed: () => void
  onAvatarSupport: (answer: TutorQuestionAnswer) => void
}

const SUGGESTIONS = [
  ['Why must we apply the same operation to both sides?', 'දෙපසටම එකම ගණිත ක්‍රියාව සිදු කරන්නේ ඇයි?'],
  ['Explain this step.', 'මේ පියවර පැහැදිලි කරන්න.'],
  ['How do I check the answer?', 'පිළිතුර පරීක්ෂා කරන්නේ කොහොමද?'],
]

export function TutorQuestion({ level, strategy, exampleProblem, stepIndex, onHelpUsed, onAvatarSupport }: Props) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<TutorQuestionAnswer>()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => { controller.current?.abort() }, [])

  async function ask(text: string) {
    if (!text.trim() || loading) return
    controller.current?.abort()
    const pending = new AbortController()
    controller.current = pending
    setQuestion(text)
    setLoading(true)
    setError('')
    setAnswer(undefined)
    try {
      const result = await askTutorQuestion(text.trim(), level, strategy, exampleProblem, stepIndex, pending.signal)
      if (pending.signal.aborted) return
      setAnswer(result)
      if (result.supported) {
        onHelpUsed()
        if (result.avatar_segments.length > 0) onAvatarSupport(result)
      }
    } catch (cause) {
      if (!pending.signal.aborted) setError(cause instanceof Error ? cause.message : 'Unable to answer. Try again.')
    } finally {
      if (!pending.signal.aborted) setLoading(false)
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    void ask(question)
  }

  return <section className="tutor-question" aria-labelledby="tutor-question-title">
    <h3 id="tutor-question-title">Ask about this step / <span lang="si">මේ පියවර ගැන අසන්න</span></h3>
    <div className="question-suggestions">{SUGGESTIONS.map(([en, si]) => <button key={en} type="button" className="secondary-button" disabled={loading} onClick={() => { void ask(en) }}><span>{en}</span><span lang="si">{si}</span></button>)}</div>
    <form onSubmit={submit}>
      <label htmlFor="tutor-question-input">Your question / <span lang="si">ඔබේ ප්‍රශ්නය</span></label>
      <textarea id="tutor-question-input" maxLength={1000} rows={3} value={question} disabled={loading} placeholder="Why do we subtract from both sides?" onChange={event => setQuestion(event.target.value)} />
      <button type="submit" className="primary-button" disabled={loading || !question.trim()}>{loading ? 'Preparing an explanation…' : 'Ask tutor / අසන්න'}</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {loading && <p role="status">Looking for relevant lesson notes…</p>}
    {answer && <div className="tutor-question-answer" aria-live="polite">
      <strong>{answer.mode === 'openai' ? 'Explanation based on lesson notes' : 'From the lesson notes'}</strong>
      {answer.paragraphs.map((paragraph, index) => <div className="answer-paragraph" key={index}><p lang="en">{paragraph.text_en}</p><p lang="si" className="sinhala-text">{paragraph.text_si}</p>
        {paragraph.source_ids.length > 0 && <small>Lesson notes: {paragraph.source_ids.map(id => answer.sources.findIndex(source => source.id === id) + 1).join(', ')}</small>}
      </div>)}
      {answer.supported && <>
        <details className="answer-sources"><summary>Lesson notes used / <span lang="si">භාවිත කළ පාඩම් සටහන්</span></summary><ol>{answer.sources.map(source => <li key={source.id}><strong>{source.title_en}</strong><p lang="si">{source.title_si}</p><p lang="en">{source.text_en}</p><p lang="si" className="sinhala-text">{source.text_si}</p></li>)}</ol></details>
        <p className="question-review-note">Draft lesson notes · teacher review pending.</p>
        {answer.avatar_segments.length > 0 && <button type="button" className="secondary-button" onClick={() => onAvatarSupport(answer)}>Avatar support / Avatar සහාය</button>}
      </>}
    </div>}
  </section>
}
