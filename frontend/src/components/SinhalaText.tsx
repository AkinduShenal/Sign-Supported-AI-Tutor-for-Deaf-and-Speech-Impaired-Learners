import { sinhalaLessonText } from './sinhalaLessonText'

export function SinhalaText({ text, className = '' }: { text: string; className?: string }) {
  const translation = sinhalaLessonText(text)
  return translation ? <p lang="si" className={`sinhala-text ${className}`}>{translation}</p> : null
}
