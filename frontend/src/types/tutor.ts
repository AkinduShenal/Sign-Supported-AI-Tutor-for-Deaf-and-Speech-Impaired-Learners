export type SignValidationStatus = 'pending' | 'validated'

export interface SignReference {
  sign_id: string
  label: string
  source_title: string
  source_page: number | null
  source_entry: number | null
  animation_asset: string | null
  animation_action: string | null
  animation_type: string | null
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

export type LearningLevel = 'foundation' | 'one_step' | 'two_step' | 'extended'
export interface AdaptiveLesson extends TutorLesson {
  plan: {
    level: LearningLevel
    source: 'diagnostic' | 'preview'
    model_version: string
    content_version: string
    primary_strategy: string
    supporting_strategies: string[]
    rationale: string
    misconception_support: string
    preferred_mode: string
    sign_support_required: boolean
    content_review_status: string
    reassessment_note: string
  }
  practice_questions: (PracticeQuestion & { progressive_hints: SignSupportedText[] })[]
}
