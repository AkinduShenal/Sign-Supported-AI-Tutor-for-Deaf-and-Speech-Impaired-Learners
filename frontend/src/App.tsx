import { useState } from 'react'
import { AdaptiveTutor } from './components/AdaptiveTutor'
import { PhaserGame } from './game/phaser/PhaserGame'
import { QuizAssessment } from './quiz/QuizAssessment'
import './App.css'

type AppView = 'quiz' | 'game' | 'tutor' | 'remedial'

const gateways: Array<{ id: AppView; label: string }> = [
  { id: 'quiz', label: 'Quiz Assessment' },
  { id: 'game', label: 'Equation Game' },
  { id: 'tutor', label: 'AI Tutor' },
  { id: 'remedial', label: 'Remedial Support' },
]

interface PendingGatewayProps {
  title: string
  teamName: string
}

function PendingGateway({ title, teamName }: PendingGatewayProps) {
  return (
    <main className="component-gateway-page">
      <section className="component-placeholder" aria-labelledby="pending-gateway-title">
        <span className="component-placeholder-badge">Integration pending</span>
        <h1 id="pending-gateway-title">{title}</h1>
        <p>
          This gateway is ready for the {teamName} frontend. Its screen can be
          connected here after that component is merged into this branch.
        </p>
      </section>
    </main>
  )
}

function App() {
  const [view, setView] = useState<AppView>('tutor')

  return (
    <>
      <nav className="app-navigation" aria-label="Learning tools">
        <span className="app-navigation-title">Sign &amp; Learn</span>
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
      {view === 'remedial' && (
        <PendingGateway title="Remedial Support" teamName="Remedial Support" />
      )}
    </>
  )
}

export default App
