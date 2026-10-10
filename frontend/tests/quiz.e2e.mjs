/** Browser check for the Phase 2 quiz. API replies are mocked so no shared DB writes occur.
 * From frontend/: node tests/quiz.e2e.mjs
 */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repository = path.dirname(frontend)
const bank = JSON.parse(await fs.readFile(path.join(repository, 'backend/scripts/quiz_pre_prototype.json'), 'utf8'))
const uuid = n => `00000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const questions = bank.questions.map((item, index) => ({
  id: uuid(index + 1),
  question_code: item.code,
  concept_id: bank.concept_id,
  subconcept_code: item.subconcept,
  question_type: 'multiple_choice',
  question_text_en: item.text_en,
  question_text_si: item.text_si,
  difficulty_level: item.difficulty,
  options: item.options.map((option, optionIndex) => ({
    id: uuid(100 + index * 4 + optionIndex),
    option_code: option[0],
    option_text_en: option[1],
    option_text_si: option[1],
  })),
}))

const chromePath = process.env.QUIZ_TEST_CHROME || (process.platform === 'win32'
  ? 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  : '/usr/bin/google-chrome')
const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'quiz-phase2-e2e-'))
const children = []
let socket
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))

function launch(command, args, cwd, env = {}) {
  const child = spawn(command, args, { cwd, env: { ...process.env, ...env }, stdio: 'ignore' })
  children.push(child)
  return child
}

async function ready(url, child) {
  for (let i = 0; i < 200; i++) {
    if (child.exitCode !== null) throw Error(`Test process exited before ${url} became ready`)
    try { const response = await fetch(url); if (response.ok) return }
    catch { /* Wait for startup. */ }
    await delay(100)
  }
  throw Error(`Timed out starting ${url}`)
}

try {
  for (const port of [5177, 9227]) {
    try { await fetch(`http://127.0.0.1:${port}`); throw Error(`Port ${port} is already occupied`) }
    catch (error) { if (error.message.includes('occupied')) throw error }
  }
  const vite = launch(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5177', '--strictPort'], frontend)
  const chrome = launch(chromePath, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-allow-origins=*', '--remote-debugging-port=9227', `--user-data-dir=${profile}`, 'about:blank'], frontend)
  await Promise.all([ready('http://127.0.0.1:5177', vite), ready('http://127.0.0.1:9227/json', chrome)])

  const targets = await (await fetch('http://127.0.0.1:9227/json')).json()
  socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl)
  await new Promise(resolve => socket.addEventListener('open', resolve, { once: true }))
  let id = 0
  const pending = new Map()
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (!message.id) return
    const entry = pending.get(message.id)
    pending.delete(message.id)
    if (message.error) entry.reject(message.error)
    else entry.resolve(message.result)
  })
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    pending.set(++id, { resolve, reject })
    socket.send(JSON.stringify({ id, method, params }))
  })
  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails))
    return result.result.value
  }
  async function until(expression) {
    for (let i = 0; i < 200; i++) {
      if (await evaluate(`Boolean(${expression})`)) return
      await delay(100)
    }
    throw Error(`Timed out waiting for ${expression}`)
  }
  async function click(selector) {
    assert.equal(await evaluate(`Boolean(document.querySelector(${JSON.stringify(selector)})?.click() ?? document.querySelector(${JSON.stringify(selector)}))`), true)
  }

  const mockSource = `(() => {
    const questions = ${JSON.stringify(questions)};
    const calls = { questions: 0, sessions: 0, responses: [], completions: 0, failNextResponse: false, loseNextConfirmation: false };
    window.__quizMock = calls;
    const originalFetch = window.fetch.bind(window);
    const session = { quiz_session_id: 'QUIZ-e2e', concept_id: 'linear_equations', learning_cycle_id: '${uuid(500)}', assessment_phase: 'pre_tutor', quiz_attempt_number: 1, display_language: 'bilingual', status: 'in_progress', started_at: new Date().toISOString(), completed_at: null };
    const reply = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
    window.fetch = async (input, init = {}) => {
      const url = typeof input === 'string' ? input : input.url;
      const path = new URL(url, location.href).pathname;
      if (!path.startsWith('/api/v1/quiz/')) return originalFetch(input, init);
      const method = init.method || 'GET';
      if (path.endsWith('/questions') && method === 'GET') { calls.questions++; return reply(questions); }
      if (path.endsWith('/sessions') && method === 'POST') { calls.sessions++; return reply(session, 201); }
      if (path.endsWith('/responses') && method === 'POST') {
        if (calls.failNextResponse) { calls.failNextResponse = false; return reply({ detail: 'Temporary network error' }, 503); }
        calls.responses.push(JSON.parse(init.body));
        await new Promise(resolve => setTimeout(resolve, 60));
        if (calls.loseNextConfirmation) { calls.loseNextConfirmation = false; throw new Error('Confirmation lost'); }
        const last = calls.responses.at(-1);
        return reply({ response_id: '${uuid(600)}', quiz_session_id: session.quiz_session_id, question_id: last.question_id, question_order: last.question_order, saved: true }, 201);
      }
      if (path.endsWith('/complete') && method === 'POST') { calls.completions++; session.status = 'completed'; session.completed_at = new Date().toISOString(); return reply(session); }
      if (path.includes('/sessions/') && method === 'GET') return reply({ ...session, responses_saved: calls.responses.length });
      return reply({ detail: 'Unexpected request' }, 404);
    };
  })()`

  await send('Page.enable')
  await send('Runtime.enable')
  await send('Page.addScriptToEvaluateOnNewDocument', { source: mockSource })
  await send('Page.navigate', { url: 'http://127.0.0.1:5177/' })
  await until("[...document.querySelectorAll('.app-navigation button')].some(button => button.textContent === 'Quiz Assessment')")
  await evaluate("[...document.querySelectorAll('.app-navigation button')].find(button => button.textContent === 'Quiz Assessment').click()")
  await until("document.querySelector('.quiz-intro button')?.textContent === 'Start assessment'")
  assert.equal(await evaluate('window.__quizMock.questions >= 1'), true)
  assert.equal(await evaluate("document.querySelector('.quiz-intro').textContent.includes('10 questions')"), true)
  await click('.quiz-intro button')
  await until("document.querySelector('.quiz-progress-label strong')?.textContent === 'Question 1 of 10'")
  assert.equal(await evaluate('window.__quizMock.sessions'), 1)
  assert.equal(await evaluate("document.querySelectorAll('.quiz-option').length"), 4)
  assert.equal(await evaluate("document.querySelector('.quiz-question-prompt').textContent.includes('Solve x + 5 = 12.')"), true)
  assert.equal(await evaluate("document.querySelector('.quiz-question-prompt').textContent.includes('සමීකරණය විසඳන්න')"), true)
  assert.equal(await evaluate("/\\b(correct|wrong|misconception|pass|fail|hint|try again)\\b/i.test(document.querySelector('.quiz-page').textContent)"), false)
  assert.equal(await evaluate("document.querySelector('.quiz-submit').disabled"), true)

  await click('.quiz-option input')
  assert.equal(await evaluate("document.querySelector('.quiz-submit').disabled"), true)
  await click('.quiz-language button:nth-child(1)')
  assert.equal(await evaluate("document.querySelector('.quiz-question-prompt [lang=si]') === null"), true)
  await click('.quiz-language button:nth-child(2)')
  assert.equal(await evaluate("document.querySelector('.quiz-question-prompt [lang=en]') === null"), true)
  await click('.quiz-language button:nth-child(3)')
  assert.equal(await evaluate("document.querySelector('.quiz-question-prompt [lang=en]') !== null && document.querySelector('.quiz-question-prompt [lang=si]') !== null"), true)
  await click('.quiz-confidence input[value=medium]')
  assert.equal(await evaluate("document.querySelector('.quiz-submit').disabled"), false)
  await delay(50)
  await evaluate("document.querySelector('.quiz-submit').click(); document.querySelector('.quiz-submit').click()")
  await until("document.querySelector('.quiz-progress-label strong')?.textContent === 'Question 2 of 10'")
  assert.equal(await evaluate('window.__quizMock.responses.length'), 1)
  assert.equal(await evaluate('window.__quizMock.responses[0].question_id'), questions[0].id)
  assert.equal(await evaluate("document.querySelector('.quiz-question-prompt').textContent.includes('x + 5 = 12')"), false)
  assert.equal(await evaluate("/\\b(correct|wrong|misconception|pass|fail|hint|try again)\\b/i.test(document.querySelector('.quiz-page').textContent)"), false)
  assert.equal(await evaluate("document.querySelector('.quiz-submit').disabled"), true)
  await click('.quiz-confidence input[value=low]')
  assert.equal(await evaluate("document.querySelector('.quiz-submit').disabled"), true)

  for (let number = 2; number <= 10; number++) {
    if (number !== 2) await click('.quiz-confidence input[value=high]')
    await click('.quiz-option input')
    if (number === 3) {
      await evaluate('window.__quizMock.failNextResponse = true')
      await click('.quiz-submit')
      await until("document.querySelector('.quiz-error')?.textContent.includes('Temporary network error')")
      assert.equal(await evaluate("document.querySelector('.quiz-progress-label strong')?.textContent"), 'Question 3 of 10')
      assert.equal(await evaluate("document.querySelector('.quiz-option input:checked') !== null && document.querySelector('.quiz-confidence input:checked') !== null"), true)
      assert.equal(await evaluate('window.__quizMock.responses.length'), 2)
    }
    if (number === 4) await evaluate('window.__quizMock.loseNextConfirmation = true')
    await click('.quiz-submit')
    if (number < 10) await until(`document.querySelector('.quiz-progress-label strong')?.textContent === 'Question ${number + 1} of 10'`)
  }
  await until("document.querySelector('#quiz-completed-title')?.textContent === 'Assessment Completed'")
  await click('.quiz-language button:nth-child(2)')
  assert.equal(await evaluate("document.querySelector('#quiz-completed-title')?.textContent"), 'ඇගයීම අවසන්')
  await click('.quiz-language button:nth-child(1)')
  assert.equal(await evaluate("document.querySelector('#quiz-completed-title')?.textContent"), 'Assessment Completed')
  await click('.quiz-language button:nth-child(3)')
  const calls = JSON.parse(await evaluate('JSON.stringify(window.__quizMock)'))
  assert.equal(calls.responses.length, 10)
  assert.equal(calls.completions, 1)
  assert.deepEqual(calls.responses.map(answer => answer.question_order), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
  assert.equal(calls.responses.every(answer => Number.isFinite(answer.response_time_sec) && answer.response_time_sec >= 0), true)
  assert.equal(calls.responses.every(answer => answer.question_id && answer.selected_option_id && answer.confidence_level), true)
  assert.equal(await evaluate("/\\b(correct|wrong|misconception|pass|fail|hint|try again)\\b/i.test(document.querySelector('.quiz-page').textContent)"), false)
  console.log('Quiz browser flow PASS: 10 questions, 10 saved requests, one completion, bilingual display, validation, and no feedback.')
} finally {
  socket?.close()
  for (const child of children) child.kill()
  if (profile.startsWith(os.tmpdir() + path.sep)) {
    await delay(200)
    await fs.rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 }).catch(() => {})
  }
}
