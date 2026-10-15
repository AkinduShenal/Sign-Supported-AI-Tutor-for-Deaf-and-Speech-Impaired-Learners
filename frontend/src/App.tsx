import { useState } from 'react'
import { AdaptiveTutor } from './components/AdaptiveTutor'
import { PhaserGame } from './game/phaser/PhaserGame'
import { QuizAssessment } from './quiz/QuizAssessment'
import { NonImprovementSection } from './components/NonImprovementSection'
import { NonImprovementSectionStartScreen } from './components/NonImprovementSectionStartScreen'
import type { EvaluationResponse } from './types/nonImprovementSection'
import './App.css'

type AppView = 'quiz' | 'game' | 'tutor' | 'remedial'

const gateways: Array<{ id: AppView; label: string }> = [
  { id: 'quiz', label: 'Quiz Assessment' },
  { id: 'game', label: 'Equation Game' },
  { id: 'tutor', label: 'AI Tutor' },
  { id: 'remedial', label: 'Remedial Support' },
]


function RemedialGateway() {
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

function App() {
  const [view, setView] = useState<AppView>('tutor')

  return (
    <>
      <nav className="app-navigation" aria-label="Learning tools">
        <span className="app-navigation-title">
          <img className="app-navigation-logo" src="/connected-learning-emblem.png" alt="" width="48" height="48" />
          Sign &amp; Learn
        </span>
        <div className="app-navigation-actions">
          {gateways.map((gateway) => (
            <button
              key={gateway.id}
              type="button"
              className={view === gateway.id ? 'active' : ''}
              aria-pressed={view === gateway.id}
              onClick={() => setView(gateway.id)}
            >
              {gateway.label}
            </button>
          ))}
        </div>
      </nav>

      {view === 'quiz' && <QuizAssessment />}
      {view === 'game' && (
        <main className="game-page">
          <PhaserGame />
        </main>
      )}
      {view === 'tutor' && <AdaptiveTutor />}
      {view === 'remedial' && <RemedialGateway />}
    </>
  )
}

export default App
