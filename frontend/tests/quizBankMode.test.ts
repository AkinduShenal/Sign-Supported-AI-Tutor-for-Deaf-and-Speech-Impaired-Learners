import assert from 'node:assert/strict'
import test from 'node:test'
import { isDynamicBankMode, newSessionBankMode } from '../src/quiz/bankMode.ts'

test('new Quiz sessions preserve the fixed bank until dynamic mode is explicitly enabled', () => {
  assert.equal(newSessionBankMode({}), 'fixed')
  assert.equal(newSessionBankMode({ VITE_QUIZ_DYNAMIC_DEV: 'true' }), 'dynamic_dev')
  assert.equal(newSessionBankMode({ VITE_QUIZ_BANK_MODE: 'fixed' }), 'fixed')
  assert.equal(newSessionBankMode({ VITE_QUIZ_BANK_MODE: 'dynamic' }), 'dynamic')
  assert.equal(newSessionBankMode({ VITE_QUIZ_BANK_MODE: 'unknown' }), 'fixed')
  assert.equal(newSessionBankMode({ VITE_QUIZ_BANK_MODE: 'dynamic', VITE_QUIZ_DYNAMIC_DEV: 'true' }), 'dynamic_dev')
})

test('both dynamic modes recover their saved question plan', () => {
  assert.equal(isDynamicBankMode('dynamic'), true)
  assert.equal(isDynamicBankMode('dynamic_dev'), true)
  assert.equal(isDynamicBankMode('fixed'), false)
  assert.equal(isDynamicBankMode(undefined), false)
})
