import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { Language } from './language'
import { UI_STRINGS } from './uiStrings'
import { LanguageContext } from './languageContextValue'
import type { LanguageContextValue } from './languageContextValue'

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>('en')

  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      strings: UI_STRINGS[language],
      toggleLanguage: () => setLanguage((current) => (current === 'en' ? 'si' : 'en')),
    }),
    [language],
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}
