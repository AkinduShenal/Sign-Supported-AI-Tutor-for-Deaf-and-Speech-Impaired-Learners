export type QuizLanguage = 'en' | 'si' | 'bilingual'
export type ConfidenceLevel = 'low' | 'medium' | 'high'
export type DifficultyLevel = 'easy' | 'medium' | 'hard'

export interface QuizOption {
  id: string
  option_code: string
  option_text_en: string
  option_text_si: string
}

export interface QuizQuestion {
  id: string
  question_code: string
  concept_id: string
  subconcept_code: string
  question_type: 'multiple_choice'
  question_text_en: string
  question_text_si: string
  difficulty_level: DifficultyLevel
  options: QuizOption[]
}

export interface QuizSession {
  quiz_session_id: string
  student_id: string
  concept_id: string
  learning_cycle_id: string
  assessment_phase: 'pre_tutor'
  quiz_attempt_number: number
  display_language: QuizLanguage
  status: 'in_progress' | 'completed' | 'abandoned'
  started_at: string
  completed_at: string | null
}

export interface QuizSessionDetail extends QuizSession {
  responses_saved: number
}

export interface QuizAnswer {
  question_id: string
  selected_option_id: string
  response_time_sec: number
  confidence_level: ConfidenceLevel
  question_order: number
  client_action_at: string
}

export interface QuizAnswerSaved {
  response_id: string
  quiz_session_id: string
  question_id: string
  question_order: number
  selected_option_id: string
  response_time_sec: number
  confidence_level: ConfidenceLevel
  answered_at: string
  is_correct: boolean
  saved: true
}

export interface QuizDiagnosticResult {
  quiz_session_id: string
  questions_total: number
  questions_attempted: number
  correct_answers: number
  mastery_level: 'low' | 'medium' | 'high'
  weak_subconcept: string | null
  recommended_focus: string | null
  recommended_support_level: 'low' | 'medium' | 'high'
  confidence_insight: {
    kind: 'mixed' | 'high_incorrect' | 'low_correct' | 'neutral'
    high_confidence_incorrect_count: number
    low_confidence_correct_count: number
  }
}
