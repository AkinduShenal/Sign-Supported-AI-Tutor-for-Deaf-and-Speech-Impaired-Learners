# Dynamic Quiz synthetic ML engineering demo

## Scope and provenance

`scripts/generate_quiz_dynamic_synthetic.py` creates **simulated learners**, not
research participants. Every CSV row has
`data_origin=SYNTHETIC_ENGINEERING_DEMO_ONLY` and a `SYN-` learner ID. The four
targets are latent synthetic profile bits assigned **before** answer behaviour
is generated. They are not inferred from option tags or teacher-confirmed
student labels. The generator reads only the checked-in 60-question draft bank,
builds a valid ten-question first-answer session in memory, and calls
`extract_dynamic_features` for its 62 predictors. It makes no database or
network connection, performs no model training, and changes no Quiz data.

The default seed is `20261022`. There are 2,400 sessions, 150 of each of the
16 possible M1–M4 binary profiles; every slot receives each of its six bank
variants 400 times. Question order is S01–S10, as in the live selection path.
The generator samples correctness, response time, confidence and an actual
available option for each item. Each row is accepted by the same extractor
that reads a completed development session. All 62 numeric features vary in
the generated file. The outputs are 70 CSV columns: 62 ordered features, four
binary targets and four provenance/version columns.

## Proposed taxonomy and limits of the simulation

The definitions below are from `research/quiz_m3/00_proposed_taxonomy.csv`,
version `m3a-taxonomy-v1-proposed`. Its teacher review status is **pending**.

| Target | Proposed meaning | Synthetic answer effect | Why an option tag is not the label |
| --- | --- | --- | --- |
| M1 | Inverse-operation misconception: repeatedly choosing a noninverse operation while isolating a term | More errors on relevant one-step and two-step slots; an `inverse_operation` distractor becomes more likely when offered | A selected distractor is one answer, not repeated working-step evidence. |
| M2 | Equation-balancing misconception: transforming only one side or treating equality as one-sided | More errors on two-step and both-sides slots; `concept_confusion` may become more likely | **No dedicated balancing tag exists** in this bank. `concept_confusion` is broad. |
| M3 | Negative-sign misconception: repeatedly mishandling a negative sign or signed term | More errors on signed/subtraction and selected harder slots; `sign_error` becomes more likely when offered | A sign-error distractor does not establish a stable teacher-observed misconception. |
| M4 | Coefficient/division misconception: repeatedly mishandling a coefficient or division while isolating x | More errors on multiplication, division and coefficient-related slots; `arithmetic_error` may become more likely when offered | `arithmetic_error` covers many slips and **is not equivalent to M4**. |

The all-zero target profile is a synthetic no-target case, not a verified M0
assessment. Several targets can be 1 simultaneously, so these data require a
multilabel approach (for example, four binary outputs). Four probabilities
need not sum to one. The numerical simulation weights are engineering
assumptions in the generator; they are not measured effects or approved label
mappings. Any validation score obtained from these rows measures only recovery
of the simulator's patterns and must not be presented as research accuracy.

## Reproduce and verify locally

From `backend/`:

```powershell
& .\.venv\Scripts\python.exe -m scripts.generate_quiz_dynamic_synthetic `
  --rows 2400 --seed 20261022 `
  --output-dir ../tmp/quiz_dynamic_ml_demo_new
& .\.venv\Scripts\python.exe -m pytest `
  tests/test_quiz_dynamic_synthetic.py `
  tests/test_quiz_dynamic_ml_features.py -q
```

Choose a new output directory on each run; the script refuses to overwrite
existing files and permits output only under this workspace's `tmp/` directory.
The current generated files are in `tmp/quiz_dynamic_ml_demo/`:

- `quiz_dynamic_synthetic_training_v1.csv`
- `quiz_dynamic_feature_contract_v1.json`

The JSON contains exactly `feature_names` in extractor order,
`feature_schema_version=quiz_dynamic_features_v1`, and
`bank_version=pp1_dynamic_v1_DRAFT`. It is a feature contract, not a trained
model manifest.

## Upload to Google Colab

1. Open `Dynamic_Quiz_62_Feature_Colab_PP1_Demo.ipynb` in Google Colab.
2. Use the left **Files** pane → **Upload** and select both files from
   `tmp/quiz_dynamic_ml_demo/`. Upload the CSV and JSON as separate files.
3. In a notebook cell, check the exact column and version match before fitting:

```python
import json
import pandas as pd

with open('/content/quiz_dynamic_feature_contract_v1.json') as f:
    contract = json.load(f)
df = pd.read_csv('/content/quiz_dynamic_synthetic_training_v1.csv')
targets = [f'target_M{i}' for i in range(1, 5)]
metadata = ['learner_id', 'data_origin', 'bank_version', 'feature_schema_version']
assert len(contract['feature_names']) == 62
assert df.columns.tolist() == contract['feature_names'] + targets + metadata
assert df['data_origin'].eq('SYNTHETIC_ENGINEERING_DEMO_ONLY').all()
assert df['bank_version'].eq(contract['bank_version']).all()
assert df['feature_schema_version'].eq(contract['feature_schema_version']).all()
assert df[targets].isin([0, 1]).all().all()
X = df[contract['feature_names']]
y = df[targets]
print(X.shape, y.shape)
```

4. Fit only the intended synthetic demo pipeline. Split by `learner_id` if
   you create repeated sessions for a learner later. Export the **fitted**
   preprocessing/model `.joblib` and a JSON manifest with model version,
   target order, bank version, feature schema version, exact feature names,
   SHA-256 checksum of the `.joblib`, and
   `training_origin=SYNTHETIC_ENGINEERING_DEMO_ONLY`.
5. Return both exported files for a separate compatibility review and Task C.
   Do not use the original 45-feature fixed-question model for inference here.

The attached `Dynamic_Quiz_62_Feature_Colab_PP1_Demo.ipynb` was inspected on
2026-10-22. Its upload contract, provenance/feature checks (cell 4), and grouped
split checks (cell 6) passed against the generated files. Its model fitting,
export and inference cells have not been run as part of file preparation.
