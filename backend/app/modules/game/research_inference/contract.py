"""Frozen software contract. These identifiers do not assert proficiency validity."""

FEATURE_ORDER = (
    "first_attempt_accuracy", "game_success_rate", "wrong_attempt_count", "retry_count",
    "total_hint_count", "skipped_step_count", "game_active_time_sec", "game_hint_rate",
    "game_avg_attempts_per_task",
)
CLASS_ORDER = ("Advanced", "Beginner", "Intermediate")
CONTRACT = "legacy-nine-feature-observed-single-session-v1"
MODEL_VERSION = "game-ml-experimental-v1"  # Integration identifier, not a new training run.
MODEL_STATUS = "EXPERIMENTAL_NOT_PRODUCTION_APPROVED"
MODEL_SHA256 = "6083d2b4f73661c73e192238d3ecd926618d87be1dad3bdd33800f0d89712ff6"
MEMBER_HASHES = {
    "game_behaviour_model.joblib": MODEL_SHA256,
    "model_metadata.json": "f5313fd4e8db2f1c917145eaa8b784fcd4778ce662851671267e7b40a5d51102",
    "verification_report.json": "fbbfe6815781819c3fc4cc4fe2514718d1d08ea990d18a5ec3db89065edf1e49",
    "frozen_predictions.json": "67fb2003650afff5da024cfb9b6ab512bc77b58cf7836779838e8e7b18e41f84",
}
DEPENDENCIES = {"scikit-learn": "1.6.1", "numpy": "2.1.3", "pandas": "2.2.3",
                "scipy": "1.16.3", "joblib": "1.6.0"}
VALIDATED_PYTHON = "3.13.12"  # Audited patch; original Colab metadata retains 3.13.16.
KNOWN_EXCLUDED = frozenset({
    "750f7589-ab19-4f95-8772-d1f0af654e2f", "d16c1dbb-6f14-400f-be97-7f0fe2f535e9",
    "GAME-SES-2026-001", "GAME-SES-2026-002", "GAME-SES-2026-003",
})
