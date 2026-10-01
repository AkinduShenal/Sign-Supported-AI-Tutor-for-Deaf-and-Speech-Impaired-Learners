export interface SignManifestEntry {
  id: string
  label: string
  category: string
  priority: number
  required_for_research: boolean
  aliases: string[]
  clip: string
  validation_status: 'needs_validation' | 'validated' | 'technical_only'
  notes: string
}
