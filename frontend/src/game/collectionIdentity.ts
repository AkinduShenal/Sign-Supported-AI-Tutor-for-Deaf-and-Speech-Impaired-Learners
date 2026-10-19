// Researcher-assigned learner codes shared by Quiz, Game and Tutor.
export const STUDENT_CODE_PATTERN = /^STU_[0-9]{3,6}$/

export function validateStudentCode(value: string): string {
  const code = value.trim()
  if (!STUDENT_CODE_PATTERN.test(code)) {
    throw new Error('Use STU_ followed by 3–6 digits, for example STU_001.')
  }
  return code
}

let activeCode: string | null = null

export function setCollectionStudent(value: string | null): void {
  activeCode = value === null ? null : validateStudentCode(value)
}

export function requireCollectionStudent(): string {
  if (!activeCode) throw new Error('Enter the researcher-assigned student code before playing.')
  return activeCode
}
