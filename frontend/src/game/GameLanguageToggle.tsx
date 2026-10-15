import { useSyncExternalStore } from 'react'
import { getGameLanguage, setGameLanguage, subscribeGameLanguage } from './gameLanguage'
import './GameLanguageToggle.css'

export function GameLanguageToggle() {
  const language = useSyncExternalStore(subscribeGameLanguage, getGameLanguage, () => 'si')
  return <div className="game-language-toggle" role="group" aria-label="Primary game language">
    <span>ප්‍රධාන භාෂාව / Primary language</span>
    <button type="button" lang="si" aria-pressed={language === 'si'} onClick={() => setGameLanguage('si')}>සිංහල</button>
    <button type="button" lang="en" aria-pressed={language === 'en'} onClick={() => setGameLanguage('en')}>English</button>
  </div>
}
