/** TEST FIXTURES ONLY. Invented visual examples; never student predictions. */
import type { GameMLLevel, GameMLPrediction } from '../../src/game/mlPrediction.ts'

export function mockGameMLPrediction(level: GameMLLevel): GameMLPrediction {
  const distributions = {
    Beginner: { Beginner: 0.73, Intermediate: 0.21, Advanced: 0.06 },
    Intermediate: { Beginner: 0.18, Intermediate: 0.645, Advanced: 0.175 },
    Advanced: { Beginner: 0.04, Intermediate: 0.16, Advanced: 0.8 },
  }
  return {
    status: 'experimental_prediction', predicted_level: level,
    probabilities: distributions[level],
    model_name: 'VISUAL TEST FIXTURE — NOT A STUDENT PREDICTION',
    model_version: 'game-ml-experimental-v1', model_status: 'EXPERIMENTAL_NOT_PRODUCTION_APPROVED',
    teacher_verified: false, feature_source: 'validated_saved_game_session',
    feature_contract: 'legacy-nine-feature-observed-single-session-v1', model_checksum: '0'.repeat(64),
    model_metadata: { test_fixture: true, not_student_data: true },
    runtime: { python: 'visual-test-only', dependencies: {} },
  }
}
