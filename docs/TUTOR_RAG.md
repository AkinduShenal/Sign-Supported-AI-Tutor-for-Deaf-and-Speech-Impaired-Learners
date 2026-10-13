# Tutor retrieval and optional generation

The worked-example interface now has **Ask about this step**, bilingual suggested
questions, cited English/Sinhala answers, source excerpts and optional avatar
support for the retrieved notes. Each lesson step also includes local retrieved
knowledge notes. The underlying equations, grading, strategy predictor and GLB
are unchanged by this layer.

## Knowledge source

`backend/app/modules/tutor/knowledge/linear_equations.json` contains ten bilingual
chunks derived from the current lesson implementation: equality, variables,
inverse operations, two-step order, negative signs, variables on both sides,
brackets, denominators and substitution. All are explicitly draft material
awaiting teacher review. No approval or curriculum-source attribution is invented.

The local BM25 index preserves Sinhala combining marks, uses English/Sinhala
search terms, and re-ranks genuine matches by level/strategy. It requires no
embedding API, vector database, package installation or schema migration. Restart
the backend after editing the corpus to rebuild the cached index.

Each chunk now includes authored `avatar_parts`: small paired English/Sinhala
ideas with explicit existing cue IDs. The excerpts and retrieval ranking stay
the same. Current worked-example context uses the same small parts as the
main lesson. Avatar support explains these source ideas; it does not claim to
translate arbitrary generated wording. See [explanation cues](../avatar-sign-package/docs/EXPLANATION_CUES.md).

## Modes and setup

Default: `RAG_ENABLED=true`, `RAG_GENERATION_ENABLED=false`.

Without generation, answers are **extractive lesson notes**, prefaced with
strategy guidance. This is retrieval plus an extractive fallback, not an LLM
generating a new explanation. The complete generation adapter is available once
configured in the existing repo-root `.env`:

```dotenv
RAG_ENABLED=true
RAG_GENERATION_ENABLED=true
OPENAI_API_KEY=your_api_key
RAG_MODEL=gpt-4.1-mini
RAG_TOP_K=3
RAG_TIMEOUT_SEC=15
```

Keep the key on the backend; do not put it in `VITE_*` settings. Restart the
backend after configuration changes. No existing `.env` credentials were changed.

The optional generator uses the [OpenAI Responses API with structured output](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).
It receives only the typed learner question, level/strategy and retrieved notes
plus the bank-checked current worked-example step. It does not receive student
IDs, quiz/game diagnostics or database records. Questions may themselves contain
personal information if a learner types it; enabling generation sends that text
to OpenAI. Requests set `store=false`, have a bounded timeout/output size, and
are made only when a learner explicitly asks a question.

## Contracts and fallbacks

- `POST /api/v1/tutor/rag/answer`: `question`, `concept_id`, `level`, `strategy`,
  optional bank-matching `example_problem`, and `step_index` (zero means intro).
- The response contains `supported`, `mode`, `knowledge_version`,
  `review_status`, bilingual `paragraphs` with `source_ids`, `sources`, and
  manifest-backed `avatar_segments`.
- `GET /api/v1/tutor/rag/status`: retrieval readiness and generation configuration
  status, never the API key.
- Missing/disabled corpus does not break the normal lesson. Unsupported queries
  return no fabricated sources or gestures. Generic “explain this step” questions
  use the validated bank context; arbitrary examples are rejected.
- Provider failure, malformed output or citations outside the retrieved set
  fall back to the local notes. Citation validation is not proof of mathematical
  correctness; generated wording and Sinhala still need teacher evaluation.
- RAG does not create new sign motion. Avatar support plays the retrieved notes'
  existing key-term gestures under the unchanged review/playback policy.
- Viewing Ask tutor help marks the current practice question as assisted for
  first-attempt independence evidence; raw questions are not added to exports.

The API-backed mode has not been exercised against a live provider because no
OpenAI key is configured. Tests cover bilingual retrieval, checked context,
unsupported queries, disabled/missing corpus, mocked generation, invalid
citations and provider failure. The tests and browser checks were not run,
following the user's earlier instruction to handle verification themselves.

For local verification, run `backend/.venv/bin/python -m pytest backend/tests/test_tutor_rag.py -q`
and the frontend build/lint checks. The RAG tests mock the provider and exercise
read-only endpoints; they do not send real questions to OpenAI or write student
records.
