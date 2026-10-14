import { useContext } from 'react'
import { LanguageContext } from './languageContextValue'
import type { LanguageContextValue } from './languageContextValue'

export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}
