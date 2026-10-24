# Teaching strategy model

These two files are the user's unchanged Colab exports, imported on 2026-10-16.
The backend loads the complete preprocessing and LogisticRegression pipeline,
including its fitted imputers, scaler and categorical encoder. It does not
retrain or reimplement those transformations.

- Version: `strategy-ml-v1`
- Target: `final_primary_strategy` (one of five primary strategies)
- Saved scikit-learn version: `1.6.1` (also pinned in backend requirements)
- Model SHA-256: `6f92fa60b2c1aa244387f0d4d89b5de56f6ab9bc8452200dae5225f55c9ef6b4`
- Metadata SHA-256: `e3f9c100152279d39287007d4f49f8932abaf6f18b2f8b0e5e1cdd0fcab7abbc`

The metadata's accuracy/CV metrics are supplied training results. Backend smoke
tests verify integration, not those metrics or teacher/learner effectiveness.
See [integration and verification](../../../../../docs/TUTOR_STRATEGY_MODEL.md).

Only replace these artifacts with trusted exports. Restart the backend after
updating both files and use a new model version. Missing files, incompatible
scikit-learn versions or conflicting feature/class metadata fail explicitly;
there is no automatic fallback to rules. This follows scikit-learn's
[persistence version guidance](https://scikit-learn.org/stable/model_persistence.html).
