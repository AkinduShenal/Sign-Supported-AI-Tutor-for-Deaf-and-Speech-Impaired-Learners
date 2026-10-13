import { useState } from 'react'
import { NonImprovementSection } from './components/NonImprovementSection'
import { NonImprovementSectionStartScreen } from './components/NonImprovementSectionStartScreen'
import type { EvaluationResponse } from './types/nonImprovementSection'
import './App.css'

function App() {
  const [evaluationData, setEvaluationData] = useState<EvaluationResponse | null>(null);

  if (!evaluationData) {
    return <NonImprovementSectionStartScreen onEvaluationComplete={setEvaluationData} />;
  }

  if (evaluationData.is_perfect) {
    return (
      <div className="app-shell" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', backgroundColor: '#fff', color: '#333' }} translate="no">
        <div className="doodle-pattern" aria-hidden="true" />
        <main className="celebration" style={{ backgroundColor: 'white', padding: '40px', borderRadius: '24px', boxShadow: '0 4px 20px rgba(0,0,0,0.1)', textAlign: 'center', maxWidth: '500px', zIndex: 10, minHeight: 'auto' }}>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '20px', color: '#10b981' }}>Outstanding!</h1>
          <p style={{ fontSize: '1.2rem', marginBottom: '30px', color: '#444', lineHeight: 1.5 }}>
            {evaluationData.encouragement_message}
          </p>
          <button className="next-button" onClick={() => setEvaluationData(null)} style={{ padding: '16px 32px', width: '100%', justifyContent: 'center' }}>
            Back to Start
          </button>
        </main>
      </div>
    );
  }

  return (
    <NonImprovementSection 
      evaluationData={evaluationData}
      onUpdateEvaluation={setEvaluationData}
      onRestart={() => setEvaluationData(null)}
    />
  );
}

export default App
