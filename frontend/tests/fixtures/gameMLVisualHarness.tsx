/** Only the isolated browser test rewrites its entry to this file. Not an app route. */
import { createRoot } from 'react-dom/client'
import { MLProficiencyCard } from '../../src/game/MLProficiencyCard'
import type { GameMLLevel, GameMLPredictionState } from '../../src/game/mlPrediction'
import { mockGameMLPrediction } from './gameMLPrediction.fixture'
import '../../src/index.css'

const params = new URLSearchParams(location.search)
const scenario = params.get('state') ?? 'default'
const showExperimentalLabel = params.get('label') !== 'false'
let state: GameMLPredictionState | undefined
if (['Beginner', 'Intermediate', 'Advanced'].includes(scenario)) {
  state = { status: 'ready', prediction: mockGameMLPrediction(scenario as GameMLLevel) }
} else if (scenario === 'loading' || scenario === 'unavailable' || scenario === 'error') {
  state = { status: scenario }
} else if (scenario === 'invalid') {
  state = { status: 'ready', prediction: { ...mockGameMLPrediction('Beginner'), probabilities: { Beginner: NaN, Intermediate: .2, Advanced: .3 } } }
}

createRoot(document.getElementById('root')!).render(
  <main data-ml-scenario={scenario} data-ml-label={String(showExperimentalLabel)} style={{ width: 'min(100% - 32px, 1000px)', margin: '32px auto' }}>
    <p style={{ color: '#843c34', fontWeight: 750 }}>Visual test only — mock data, not a student prediction.</p>
    <MLProficiencyCard state={state} showExperimentalLabel={showExperimentalLabel} />
  </main>,
)
