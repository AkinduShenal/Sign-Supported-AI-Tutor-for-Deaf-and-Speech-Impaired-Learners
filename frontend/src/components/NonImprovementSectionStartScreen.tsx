import { useState } from 'react';
import { evaluateSubmission } from '../api/nonImprovementSectionTutor';
import type { EvaluationResponse, SubmissionRequest } from '../types/nonImprovementSection';
import './NonImprovementSection.css'; // Reusing styles

interface NonImprovementSectionStartScreenProps {
  onEvaluationComplete: (response: EvaluationResponse) => void;
}

export function NonImprovementSectionStartScreen({ onEvaluationComplete }: NonImprovementSectionStartScreenProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      // Dummy data representing an initial assessment where the student made mistakes
      const dummySubmission: SubmissionRequest = {
        user_id: "student_001",
        questions: [
          {
            question_id: "q_init_1",
            question: "2x + 3 = 11",
            correct_answer: "4",
            user_answer: "8",
            category: "two_step"
          },
          {
            question_id: "q_init_2",
            question: "x - 5 = -2",
            correct_answer: "3",
            user_answer: "-3",
            category: "negative_numbers"
          },
          {
            question_id: "q_init_3",
            question: "x + 4 = 10",
            correct_answer: "6",
            user_answer: "6",
            category: "single_variable"
          }
        ]
      };

      const response = await evaluateSubmission(dummySubmission);
      onEvaluationComplete(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }} translate="no">
      <div className="doodle-pattern" aria-hidden="true" />
      
      <main className="celebration" style={{ backgroundColor: 'white', padding: '40px', borderRadius: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.1)', textAlign: 'center', maxWidth: '400px', minHeight: 'auto' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '16px', color: '#333' }}>Re-Assessment</h1>
        <p style={{ marginBottom: '32px', color: '#666', fontSize: '1.1rem' }}>
          Welcome! Let's start by evaluating your current skills. Click the button below to submit your initial test and get a personalized lesson.
        </p>
        
        {error && (
          <div style={{ color: 'red', marginBottom: '16px', padding: '8px', backgroundColor: '#fee' }}>
            {error}
          </div>
        )}
        
        <button 
          className="next-button" 
          onClick={handleStart} 
          disabled={loading}
          style={{ width: '100%', padding: '16px', fontSize: '1.2rem', justifyContent: 'center', opacity: loading ? 0.7 : 1 }}
        >
          {loading ? "Analyzing..." : "Start Evaluation"}
        </button>
      </main>
    </div>
  );
}
