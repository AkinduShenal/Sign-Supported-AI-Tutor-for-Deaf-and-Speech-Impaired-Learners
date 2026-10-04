export type Language = 'en' | 'si'

export type Localized<T> = Record<Language, T>
