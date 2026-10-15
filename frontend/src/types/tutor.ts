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
  reference_videos?: { title: string; url: string; language: string; source: string }[]
}

export interface ExplanationMotion {
  clip: string
  kind: string
  beats: { role: string; start: number; end: number; text: string; text_si: string }[]
  original_expression: string | null
  current_expression: string | null
  substituted_expression: string | null
  value: string | null
  language_status: string
}

export interface AvatarTeachingSegment {
  text: string
  text_si?: string | null
  expression?: string | null
  sign_actions: string[]
  expression_tokens?: { text: string; start: number; end: number; action_index: number | null }[]
  unsupported_tokens?: string[]
  support_kind?: 'key_terms' | 'expression' | 'meaning_demonstration'
  motion?: ExplanationMotion | null
}

export interface SignSupportedText {
  text: string
  sign_actions: string[]
  avatar_segments?: AvatarTeachingSegment[]
  knowledge_notes?: KnowledgeSource[]
}

export interface LessonStep {
  order: number
  instruction: string
  expression: string
  sign_actions: string[]
  avatar_segments?: AvatarTeachingSegment[]
  knowledge_notes?: KnowledgeSource[]
}

export interface WorkedExample {
  problem: string
  steps: LessonStep[]
  answer: string
  avatar_intro_segments?: AvatarTeachingSegment[]
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
export type TeachingStrategy = 'step_by_step' | 'worked_example_based' | 'conceptual_explanation' | 'progressive_hints' | 'advanced_challenge'

export interface KnowledgeSource {
  id: string
  title_en: string
  title_si: string
  text_en: string
  text_si: string
  source_ref: string
  review_status: string
  sign_actions: string[]
  avatar_parts?: AvatarTeachingSegment[]
  score: number
}

export interface TutorQuestionAnswer {
  supported: boolean
  mode: 'extractive' | 'openai' | 'fallback' | 'no_context' | 'disabled' | 'unavailable'
  knowledge_version: string
  review_status: string
  paragraphs: { text_en: string; text_si: string; source_ids: string[] }[]
  sources: KnowledgeSource[]
  avatar_segments: AvatarTeachingSegment[]
}
export interface AdaptiveLesson extends TutorLesson {
  plan: {
    level: LearningLevel
    source: 'diagnostic' | 'preview'
    model_version: string
    content_version: string
    primary_strategy: TeachingStrategy
    supporting_strategies: string[]
    rationale: string
    misconception_support: string
    preferred_mode: string
    sign_support_required: boolean
    avatar_playback_speed?: number
    content_review_status: string
    reassessment_note: string
  }
  practice_questions: (PracticeQuestion & { progressive_hints: SignSupportedText[]; worked_solution: WorkedExample })[]
}
