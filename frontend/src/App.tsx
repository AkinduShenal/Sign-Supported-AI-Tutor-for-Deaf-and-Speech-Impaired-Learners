import { PhaserGame } from './game/phaser/PhaserGame'
import './App.css'

// Milestone 1 prototype: the earlier React/CSS balance-chip version
// (./game/GameActivity.tsx) is still in the repo, just not mounted here
// while we try the Phaser version.
function App() {
  return (
    <main id="center">
      <PhaserGame />
    </main>
  )
}

export default App
