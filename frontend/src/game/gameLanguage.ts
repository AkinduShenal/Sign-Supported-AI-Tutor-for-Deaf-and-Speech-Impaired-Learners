export type GameLanguage = 'si' | 'en'
export type GameLanguageText = Record<GameLanguage, string>

// Shared by the two games and their selection screen. A fresh page defaults
// to Sinhala; changing the presentation never creates a new game session.
let language: GameLanguage = 'si'
const listeners = new Set<() => void>()

export function getGameLanguage(): GameLanguage { return language }

export function setGameLanguage(next: GameLanguage): void {
  if (next !== 'si' && next !== 'en') throw new Error('Unsupported game language')
  if (next === language) return
  language = next
  listeners.forEach(listener => listener())
}

export function subscribeGameLanguage(listener: () => void): () => void {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export function primaryGameText(text: GameLanguageText): string { return text[language] }
export function secondaryGameText(text: GameLanguageText): string { return text[language === 'si' ? 'en' : 'si'] }
export function formatGameLanguages(text: GameLanguageText, separator = '\n'): string {
  return `${primaryGameText(text)}${separator}${secondaryGameText(text)}`
}
