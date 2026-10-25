/** Memory-only demo capability/context. Never touches the shared learner store. */
export interface DevelopmentDemoContext {
  capability: string
  session_ids: string[]
  student_id: 'DEMO_TEAM'
  learning_cycle_id: string
  concept_id: 'linear_equations'
  assessment_phase: 'pre_tutor'
  classification: 'DEVELOPMENT_DEMO_NOT_RESEARCH'
}
let context: DevelopmentDemoContext | null = null
let remaining: string[] = []
export function getDevelopmentDemo(): DevelopmentDemoContext | null { return context }
export function setDevelopmentDemo(value: DevelopmentDemoContext | null): void {
  context = value
  remaining = value ? [...value.session_ids] : []
}
export function takeDevelopmentSessionId(): string {
  const id = remaining.shift()
  if (!context || !id) throw new Error('Start a fresh development demo before another session.')
  return id
}
export function demoHeaders(): Record<string, string> {
  return context ? { 'X-Game-Demo-Capability': context.capability } : {}
}
