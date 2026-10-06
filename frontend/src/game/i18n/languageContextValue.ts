import { createContext } from 'react'
import type { Language } from './language'
import { UI_STRINGS } from './uiStrings'

export interface LanguageContextValue {
  language: Language
  strings: (typeof UI_STRINGS)[Language]
  toggleLanguage: () => void
}

export const LanguageContext = createContext<LanguageContextValue | null>(null)
