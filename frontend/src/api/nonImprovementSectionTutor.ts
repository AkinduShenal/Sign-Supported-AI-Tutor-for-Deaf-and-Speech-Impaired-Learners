import type { SubmissionRequest, EvaluationResponse } from '../types/nonImprovementSection';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';
const RAW_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '');
const API_BASE_URL = RAW_API_BASE_URL.replace(/\/api\/v1$/, '');

export async function evaluateSubmission(submission: SubmissionRequest, signal?: AbortSignal): Promise<EvaluationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/evaluate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(submission),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Evaluation request failed (${response.status})`);
  }

  return response.json() as Promise<EvaluationResponse>;
}
