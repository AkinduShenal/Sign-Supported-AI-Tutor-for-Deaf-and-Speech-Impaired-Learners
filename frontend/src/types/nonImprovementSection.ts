export type EquationCategory = 
  | "single_variable"
  | "two_step"
  | "negative_numbers"
  | "fractions_basic"
  | "variables_both_sides"
  | "distributive";

export interface GeneratedQuestion {
  question_id: string;
  question: string;
  correct_answer: string;
  category: EquationCategory;
}

export interface QuestionAnswer {
  question_id: string;
  question: string;
  correct_answer: string;
  user_answer: string;
  category: EquationCategory;
}

export interface SubmissionRequest {
  user_id: string;
  questions: QuestionAnswer[];
}

export interface AnswerResult {
  question_id: string;
  question: string;
  correct_answer: string;
  user_answer: string;
  is_correct: boolean;
  category: EquationCategory;
  error_type: string | null;
  error_description: string | null;
}

export interface WeaknessArea {
  category: EquationCategory;
  error_count: number;
  total_questions: number;
  accuracy_percentage: number;
  common_error_types: string[];
  severity: "high" | "medium" | "low";
  is_issue: boolean;
}

export interface NextQuizPayload {
  targeted_categories: string[];
  questions: GeneratedQuestion[];
}

export interface TutorialStep {
  step_number: number;
  instruction: string;
  example: string;
}

export interface PracticeProblem {
  problem: string;
  answer: string;
}

export interface Tutorial {
  title: string;
  introduction: string;
  steps: TutorialStep[];
  practice_problems: PracticeProblem[];
  tips: string[];
  encouragement: string;
  category?: EquationCategory;
  severity?: string;
}

export interface EvaluationResponse {
  user_id: string;
  total_questions: number;
  correct_count: number;
  incorrect_count: number;
  overall_accuracy: number;
  is_perfect: boolean;
  results: AnswerResult[];
  focus_area: WeaknessArea | null;
  tutorial: Tutorial | null;
  next_quiz: NextQuizPayload | null;
  encouragement_message: string;
}
