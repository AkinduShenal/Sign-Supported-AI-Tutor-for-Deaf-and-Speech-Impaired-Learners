export type SignValidationStatus = 'pending' | 'validated'

export interface SignReference {
  sign_id: string
  label: string
  source_title: string
  source_page: number
  source_entry: number
  animation_asset: string | null
  animation_action: string | null
  prototype_ready: boolean
  validation_status: SignValidationStatus
}

export interface SignSupportedText {
  text: string
  sign_actions: string[]
}

export interface LessonStep {
  order: number
  instruction: string
  expression: string
  sign_actions: string[]
}

export interface WorkedExample {
  problem: string
  steps: LessonStep[]
  answer: string
}

export interface PracticeQuestion {
  question_id: string
  prompt: string
  hint: SignSupportedText
  expected_answer: string
  feedback: {
    correct: string
    incorrect: string
  }
}

export interface TutorLesson {
  concept_id: string
  title: string
  learning_objective: string
  simple_explanation: SignSupportedText
  sign_glossary: SignReference[]
  worked_examples: WorkedExample[]
  practice_questions: PracticeQuestion[]
}
