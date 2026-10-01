export interface SignManifestEntry {
  id: string
  label: string
  category: string
  priority: number
  required_for_research: boolean
  aliases: string[]
  clip: string
  animation_asset?: string
  animation_action?: string
  prototype_ready?: boolean
  animation_type?: 'educational_avatar_gesture'
  validation_status: 'needs_validation' | 'validated' | 'technical_only'
  notes: string
}
