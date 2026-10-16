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
const correctOptionIds = bank.questions.map((item, index) => uuid(100 + index * 4 + item.options.findIndex(option => option[2])))

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
  for (let i = 0; i < 40; i++) {
    if (child.exitCode !== null) throw Error(`Test process exited before ${url} became ready`)
    try { const response = await fetch(url, { signal: AbortSignal.timeout(500) }); if (response.ok) return }
    catch { /* Wait for startup. */ }
    await delay(100)
  }
  throw Error(`Timed out starting ${url}`)
}

try {
  for (const port of [5187, 9237]) {
    try { await fetch(`http://127.0.0.1:${port}`); throw Error(`Port ${port} is already occupied`) }
    catch (error) { if (error.message.includes('occupied')) throw error }
  }
  const vite = launch(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5187', '--strictPort'], frontend)
  const chrome = launch(chromePath, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-allow-origins=*', '--remote-debugging-port=9237', `--user-data-dir=${profile}`, 'about:blank'], frontend)
  await Promise.all([ready('http://127.0.0.1:5187', vite), ready('http://127.0.0.1:9237/json', chrome)])

  let targets
  for (let attempt = 0; attempt < 20; attempt++) {
    try {
      targets = await (await fetch('http://127.0.0.1:9237/json', { signal: AbortSignal.timeout(1000) })).json()
      break
    } catch { await delay(100) }
  }
  if (!targets) throw Error('Chrome debugging endpoint could not be read')
  socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl)
  await new Promise(resolve => socket.addEventListener('open', resolve, { once: true }))
  let id = 0
  const pending = new Map()
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Page.javascriptDialogOpening') {
      void send('Page.handleJavaScriptDialog', { accept: true }).catch(() => {})
      return
    }
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
    throw Error(`Timed out waiting for ${expression}; page: ${JSON.stringify(await evaluate("({url: location.href, state: document.readyState, gate: document.querySelector('.quiz-collection-gate')?.textContent.slice(0, 250), body: document.body?.textContent.slice(0, 250)})"))}`)
  }
  async function click(selector) {
    assert.equal(await evaluate(`Boolean(document.querySelector(${JSON.stringify(selector)})?.click() ?? document.querySelector(${JSON.stringify(selector)}))`), true)
  }
  async function completeRemainingTries() {
    for (let attempt = 2; attempt <= 3; attempt++) {
      if (!await evaluate("document.querySelector('.quiz-feedback-continue')?.textContent.includes('Try again')")) return
      await click('.quiz-feedback-continue')
      await until("document.querySelector('.quiz-option input:not(:disabled)')")
      assert.equal(await evaluate("document.querySelectorAll('.quiz-option input:not(:disabled)').length"), 4)
      await click('.quiz-option input:not(:disabled)')
      await click('.quiz-submit')
      await until("Boolean(document.querySelector('.quiz-answer-feedback'))")
      assert.equal(await evaluate("Boolean(document.querySelector('.quiz-option.is-tried, .quiz-option-tried-label'))"), false)
      if (attempt < 3) {
        assert.equal(await evaluate("Boolean(document.querySelector('.quiz-correct-answer, .quiz-option.is-answer-key'))"), false)
      } else if (await evaluate("Boolean(document.querySelector('.quiz-answer-feedback.is-incorrect'))")) {
        assert.equal(await evaluate("Boolean(document.querySelector('.quiz-correct-answer, .quiz-option.is-answer-key'))"), true)
      }
    }
  }

  const mockSource = `(() => {
    const questions = ${JSON.stringify(questions)};
    const correctOptionIds = ${JSON.stringify(correctOptionIds)};
    const stored = JSON.parse(localStorage.getItem('__quizMockServer') || 'null');
    const calls = stored?.calls || { questions: 0, sessions: 0, responses: [], responseRequests: 0, completions: 0, analyses: 0, failNextResponse: false, loseNextConfirmation: false };
    window.__quizMock = calls;
    const originalFetch = window.fetch.bind(window);
    const session = stored?.session || { quiz_session_id: '', student_id: '', concept_id: 'linear_equations', learning_cycle_id: '${uuid(500)}', assessment_phase: 'pre_tutor', quiz_attempt_number: 1, display_language: 'bilingual', status: 'in_progress', started_at: new Date().toISOString(), completed_at: null };
    const persist = () => localStorage.setItem('__quizMockServer', JSON.stringify({ calls, session }));
    const reply = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
    window.fetch = async (input, init = {}) => {
      const url = typeof input === 'string' ? input : input.url;
      const path = new URL(url, location.href).pathname;
      if (!path.startsWith('/api/v1/quiz/')) return originalFetch(input, init);
      const method = init.method || 'GET';
      if (path.endsWith('/questions') && method === 'GET') {
        calls.questions++;
        if (localStorage.getItem('__quizHangQuestions') === '1') {
          return new Promise((_resolve, reject) => {
            init.signal?.addEventListener('abort', () => reject(init.signal.reason), { once: true });
          });
        }
        return reply(questions);
      }
      if (path.endsWith('/sessions') && method === 'POST') {
        calls.sessions++;
        const body = JSON.parse(init.body);
        session.quiz_session_id = 'QUIZ-' + body.client_session_id;
        session.student_id = body.student_id;
        session.learning_cycle_id = body.learning_cycle_id;
        session.display_language = body.display_language;
        persist();
        return reply(session, 201);
      }
      if (path.endsWith('/responses') && method === 'POST') {
        if (calls.failNextResponse) { calls.failNextResponse = false; persist(); return reply({ detail: 'Temporary network error' }, 503); }
        calls.responseRequests++;
        const body = JSON.parse(init.body);
        const prior = calls.responses.find(row => row.question_id === body.question_id);
        if (prior && JSON.stringify(prior) !== JSON.stringify(body)) return reply({ detail: 'Conflicting evidence' }, 409);
        if (!prior) calls.responses.push(body);
        persist();
        await new Promise(resolve => setTimeout(resolve, 60));
        if (calls.loseNextConfirmation) { calls.loseNextConfirmation = false; persist(); throw new Error('Confirmation lost'); }
        const correctOption = questions[body.question_order - 1].options.find(option => option.id === correctOptionIds[body.question_order - 1]);
        return reply({ response_id: '${uuid(600)}', quiz_session_id: session.quiz_session_id,
          question_id: body.question_id, question_order: body.question_order,
          selected_option_id: body.selected_option_id, response_time_sec: body.response_time_sec,
          confidence_level: body.confidence_level, answered_at: body.client_action_at,
          is_correct: body.selected_option_id === correctOption.id,
          correct_option: body.selected_option_id === correctOption.id ? null : correctOption,
          saved: true }, 201);
      }
      if (path.endsWith('/complete') && method === 'POST') { calls.completions++; session.status = 'completed'; session.completed_at = new Date().toISOString(); persist(); return reply(session); }
      if (path.endsWith('/analyze') && method === 'POST') {
        calls.analyses++;
        return reply({ quiz_session_id: session.quiz_session_id, questions_total: 10, questions_attempted: 10, correct_answers: 7, mastery_level: 'medium', weak_subconcept: calls.noWeak ? null : 'two_step_equations', recommended_focus: calls.noWeak ? 'Equation Meaning' : 'Two-step Equations', recommended_support_level: 'medium', confidence_insight: { kind: 'high_incorrect', high_confidence_incorrect_count: 2, low_confidence_correct_count: 0 }, misconception_code: 'inverse_operation', confidence_pattern: 'high_confidence_incorrect', diagnostic_evidence: { question_evidence: [{ question_order: 1, response_time_sec: 19.3 }] } });
      }
      if (path.includes('/sessions/') && method === 'GET') return reply({ ...session, responses_saved: calls.responses.length });
      return reply({ detail: 'Unexpected request' }, 404);
    };
  })()`

  await send('Page.enable')
  await send('Runtime.enable')
  await send('Page.addScriptToEvaluateOnNewDocument', { source: mockSource })
  await send('Page.navigate', { url: 'http://127.0.0.1:5187/' })
  await until("[...document.querySelectorAll('.app-navigation button')].some(button => button.textContent === 'Quiz Assessment')")
  await evaluate("[...document.querySelectorAll('.app-navigation button')].find(button => button.textContent === 'Quiz Assessment').click()")
  await until("document.querySelector('.quiz-collection-gate button[type=submit]:not(:disabled)')")
  await evaluate("(() => { const input = document.querySelector('#quiz-student-code'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'STU_001'); input.dispatchEvent(new Event('input', { bubbles: true })); })()")
  await click('.quiz-collection-gate button[type=submit]')
  await until("document.querySelector('[data-testid=quiz-active-student]')?.textContent === 'STU_001'")
  await until("document.querySelector('.quiz-intro button')?.textContent === 'Start assessment'")
  assert.equal(await evaluate('window.__quizMock.questions >= 1'), true)
  assert.equal(await evaluate("document.querySelector('.quiz-intro').textContent.includes('10 Questions · 4 Beginner · 4 Intermediate · 2 Advanced')"), true)
  await click('.quiz-intro button')
  await until("document.querySelector('.quiz-progress-label strong')?.textContent === 'Question 1 of 10'")
  assert.equal(await evaluate("document.querySelector('.quiz-level-heading').textContent.includes('Beginner Level')"), true)
  assert.equal(await evaluate('window.__quizMock.sessions'), 1)
  assert.equal(await evaluate("document.querySelectorAll('.quiz-option').length"), 4)
  assert.equal(await evaluate("document.querySelector('.quiz-question-prompt').textContent.includes('Solve x + 5 = 12.')"), true)
  await click('.bodmas-trigger')
  await until("document.querySelector('.bodmas-dialog')?.open")
  assert.equal(await evaluate("document.querySelectorAll('.bodmas-step-graphic').length"), 6)
  assert.equal(await evaluate("Boolean(document.querySelector('.bodmas-close svg'))"), true)
  assert.equal(await evaluate("(() => { const panel = document.querySelector('.bodmas-dialog').getBoundingClientRect(); return panel.right <= innerWidth && panel.right >= innerWidth - 40 && panel.width <= 540 && panel.height < innerHeight && panel.top < 40 })()"), true)
  await click('.bodmas-close')
  await until("!document.querySelector('.bodmas-dialog')?.open")
  await until("document.activeElement?.classList.contains('bodmas-trigger')")
  assert.equal(await evaluate("document.activeElement?.classList.contains('bodmas-trigger')"), true)
  assert.equal(await evaluate("document.querySelector('.quiz-question-prompt').textContent.includes('සමීකරණය විසඳන්න')"), true)
  assert.equal(await evaluate("/\\b(correct|wrong|misconception|pass|fail|hint|try again)\\b/i.test(document.querySelector('.quiz-page').textContent)"), false)
  assert.equal(await evaluate("document.querySelector('.quiz-submit').disabled"), true)

  await click('.quiz-option input')
  assert.equal(await evaluate("document.querySelector('.quiz-submit').disabled"), true)
  await click('.quiz-language button:nth-child(1)')
  assert.equal(await evaluate("document.querySelector('.quiz-question-prompt [lang=si]') === null"), true)
  await click('.quiz-language button:nth-child(2)')
  assert.equal(await evaluate("document.querySelector('.quiz-question-prompt [lang=en]') === null"), true)
  assert.equal(await evaluate("document.querySelector('.quiz-level-heading').textContent.includes('ආරම්භක මට්ටම')"), true)
  await click('.quiz-language button:nth-child(3)')
  assert.equal(await evaluate("document.querySelector('.quiz-question-prompt [lang=en]') !== null && document.querySelector('.quiz-question-prompt [lang=si]') !== null"), true)
  await click('.quiz-confidence input[value=medium]')
  assert.equal(await evaluate("document.querySelector('.quiz-submit').disabled"), false)
  await delay(50)
  await evaluate("document.querySelector('.quiz-submit').click(); document.querySelector('.quiz-submit').click()")
  await until("document.querySelector('.quiz-answer-feedback.is-correct')?.textContent.includes('Correct answer!')")
  assert.equal(await evaluate("document.querySelector('.quiz-answer-feedback-icon')?.textContent"), '✅')
  assert.equal(await evaluate('window.__quizMock.responses.length'), 1)
  assert.equal(await evaluate('window.__quizMock.responses[0].question_id'), questions[0].id)
  assert.equal(await evaluate("document.querySelector('.quiz-progress-label strong')?.textContent"), 'Question 1 of 10')
  assert.equal(await evaluate("document.querySelector('.quiz-option.is-correct input')?.checked"), true)
  assert.equal(await evaluate("document.querySelector('.quiz-option.is-correct input')?.disabled"), true)
  await click('.quiz-feedback-continue')
  await until("document.querySelector('.quiz-progress-label strong')?.textContent === 'Question 2 of 10'")
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
      await until("document.querySelector('.quiz-panel h2')?.textContent === 'Quiz evidence needs recovery'")
      assert.equal(await evaluate('window.__quizMock.responses.length'), 2)
      assert.equal(await evaluate("JSON.parse(localStorage.getItem('quiz.collection.pending.v1')).sessions[0].responses[2].body.question_id"), questions[2].id)
      await send('Page.reload', { ignoreCache: true })
      await until("document.querySelector('.quiz-panel h2')?.textContent !== 'Quiz evidence needs recovery' && [...document.querySelectorAll('.app-navigation button')].some(button => button.textContent === 'Quiz Assessment')")
      await evaluate("[...document.querySelectorAll('.app-navigation button')].find(button => button.textContent === 'Quiz Assessment').click()")
      await until("document.querySelector('.quiz-collection-gate button[type=submit]:not(:disabled)')")
      await evaluate("(() => { const input = document.querySelector('#quiz-student-code'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'STU_001'); input.dispatchEvent(new Event('input', { bubbles: true })); })()")
      await click('.quiz-collection-gate button[type=submit]')
      await until("document.querySelector('.quiz-answer-feedback.is-incorrect')?.textContent.includes('Incorrect. Try again.')")
      assert.equal(await evaluate("document.querySelector('.quiz-answer-feedback-icon')?.textContent"), '❌')
      assert.equal(await evaluate("Boolean(document.querySelector('.quiz-correct-answer, .quiz-option.is-answer-key'))"), false)
      assert.equal(await evaluate('window.__quizMock.sessions'), 1)
      assert.equal(await evaluate('window.__quizMock.responses.length'), 3)
      await completeRemainingTries()
      await click('.quiz-feedback-continue')
      await until("document.querySelector('.quiz-progress-label strong')?.textContent === 'Question 4 of 10'")
      continue
    }
    if (number === 4) await evaluate('window.__quizMock.loseNextConfirmation = true')
    await click('.quiz-submit')
    if (number === 4) {
      await until("document.querySelector('.quiz-panel h2')?.textContent === 'Quiz evidence needs recovery'")
      await click('.quiz-collection-gate button[type=button]')
      await until("document.querySelector('.quiz-answer-feedback.is-incorrect')?.textContent.includes('Incorrect. Try again.')")
      assert.equal(await evaluate("Boolean(document.querySelector('.quiz-correct-answer, .quiz-option.is-answer-key'))"), false)
      await completeRemainingTries()
      await click('.quiz-feedback-continue')
      await until("document.querySelector('#quiz-transition-title')?.textContent === 'Beginner Level Completed'")
      assert.equal(await evaluate("document.querySelector('.quiz-level-transition').textContent.includes('ආරම්භක මට්ටම සම්පූර්ණයි')"), true)
      await click('.quiz-language button:nth-child(2)')
      assert.equal(await evaluate("document.querySelector('#quiz-transition-title')?.textContent"), 'ආරම්භක මට්ටම සම්පූර්ණයි')
      await click('.quiz-language button:nth-child(3)')
      assert.equal(await evaluate('window.__quizMock.responses.length'), 4)
      await delay(1400)
      assert.equal(await evaluate('window.__quizMock.responses.length'), 4)
      await click('.quiz-level-transition button')
      await until("document.querySelector('.quiz-progress-label strong')?.textContent === 'Question 5 of 10'")
      assert.equal(await evaluate("document.querySelector('.quiz-level-heading').textContent.includes('Intermediate Level')"), true)
      continue
    }
    await until("Boolean(document.querySelector('.quiz-answer-feedback'))")
    assert.equal(await evaluate("document.querySelector('.quiz-progress-label strong')?.textContent"), `Question ${number} of 10`)
    assert.equal(await evaluate("document.querySelector('.quiz-answer-feedback').classList.contains('is-correct')"), correctOptionIds[number - 1] === questions[number - 1].options[0].id)
    if (correctOptionIds[number - 1] !== questions[number - 1].options[0].id) {
      assert.equal(await evaluate("Boolean(document.querySelector('.quiz-correct-answer, .quiz-option.is-answer-key'))"), false)
      await completeRemainingTries()
    }
    await click('.quiz-feedback-continue')
    if (number === 8) {
      await until("document.querySelector('#quiz-transition-title')?.textContent === 'Intermediate Level Completed'")
      assert.equal(await evaluate("document.querySelector('.quiz-level-transition').textContent.includes('අතරමැදි මට්ටම සම්පූර්ණයි')"), true)
      assert.equal(await evaluate('window.__quizMock.responses.length'), 8)
      await delay(1400)
      assert.equal(await evaluate('window.__quizMock.responses.length'), 8)
      await click('.quiz-level-transition button')
      await until("document.querySelector('.quiz-progress-label strong')?.textContent === 'Question 9 of 10'")
      assert.equal(await evaluate("document.querySelector('.quiz-level-heading').textContent.includes('Advanced Level')"), true)
      continue
    }
    if (number < 10) await until(`document.querySelector('.quiz-progress-label strong')?.textContent === 'Question ${number + 1} of 10'`)
  }
  await until("document.querySelector('#quiz-completed-title')?.textContent === 'Assessment Complete'")
  assert.equal(await evaluate("document.querySelector('.quiz-result-list')?.textContent.includes('7 / 10')"), true)
  assert.equal(await evaluate("document.querySelector('.quiz-result-list')?.textContent.includes('Developing Understanding')"), true)
  assert.equal(await evaluate("document.querySelector('.quiz-result-list')?.textContent.includes('Understanding Level')"), true)
  assert.equal(await evaluate("document.querySelector('.quiz-result-list')?.textContent.includes('Recommended Support')"), false)
  assert.equal(await evaluate("document.querySelector('.quiz-result-list')?.textContent.includes('Learning Level')"), false)
  assert.equal(await evaluate("document.querySelector('.quiz-confidence-insight h3')?.textContent"), 'Confidence Insight')
  assert.equal(await evaluate("document.querySelector('.quiz-confidence-insight')?.textContent.includes('2 incorrect answers')"), true)
  assert.equal(await evaluate("[...document.querySelectorAll('.quiz-result-list > div')].find(row => row.querySelector('dt')?.textContent.includes('Correct Answers'))?.querySelector('dd')?.textContent"), '7')
  assert.equal(await evaluate("[...document.querySelectorAll('.quiz-result-list > div')].find(row => row.querySelector('dt')?.textContent.includes('Incorrect Answers'))?.querySelector('dd')?.textContent"), '3')
  await click('.quiz-language button:nth-child(2)')
  assert.equal(await evaluate("document.querySelector('#quiz-completed-title')?.textContent"), 'ඇගයීම සම්පූර්ණයි')
  assert.equal(await evaluate("document.querySelector('.quiz-confidence-insight h3')?.textContent"), 'පිළිතුරු පිළිබඳ විශ්වාසයේ සාරාංශය')
  assert.equal(await evaluate("document.querySelector('.quiz-confidence-insight')?.textContent.includes('වැරදි පිළිතුරු 2කට')"), true)
  assert.equal(await evaluate("[...document.querySelectorAll('.quiz-result-list > div')].find(row => row.querySelector('dt')?.textContent.trim() === 'නිවැරදි පිළිතුරු')?.querySelector('dd')?.textContent"), '7')
  assert.equal(await evaluate("[...document.querySelectorAll('.quiz-result-list > div')].find(row => row.querySelector('dt')?.textContent.trim() === 'වැරදි පිළිතුරු')?.querySelector('dd')?.textContent"), '3')
  await click('.quiz-language button:nth-child(1)')
  assert.equal(await evaluate("document.querySelector('#quiz-completed-title')?.textContent"), 'Assessment Complete')
  await click('.quiz-language button:nth-child(3)')
  assert.equal(await evaluate("document.querySelectorAll('.quiz-confidence-insight p[lang=si]').length"), 2)
  assert.equal(await evaluate("[...document.querySelectorAll('.quiz-result-list > div')].find(row => row.querySelector('dt')?.textContent.includes('Correct Answers'))?.querySelector('dt small')?.textContent"), 'නිවැරදි පිළිතුරු')
  assert.equal(await evaluate("[...document.querySelectorAll('.quiz-result-list > div')].find(row => row.querySelector('dt')?.textContent.includes('Incorrect Answers'))?.querySelector('dt small')?.textContent"), 'වැරදි පිළිතුරු')
  const calls = JSON.parse(await evaluate('JSON.stringify(window.__quizMock)'))
  assert.equal(calls.sessions, 1)
  assert.equal(calls.responses.length, 10)
  assert.equal(calls.responseRequests, 11)
  assert.equal(calls.completions, 1)
  assert.equal(calls.analyses, 1)
  assert.deepEqual(calls.responses.map(answer => answer.question_order), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
  assert.equal(calls.responses.every(answer => Number.isFinite(answer.response_time_sec) && answer.response_time_sec >= 0), true)
  assert.equal(calls.responses[4].response_time_sec < 1.2, true)
  assert.equal(calls.responses[8].response_time_sec < 1.2, true)
  assert.equal(calls.responses.every(answer => answer.question_id && answer.selected_option_id && answer.confidence_level), true)
  assert.equal(await evaluate("document.querySelector('.quiz-page').textContent.includes('Question 1 of 10')"), false)
  assert.equal(await evaluate("document.querySelector('.quiz-page').textContent.includes('Solve x + 5 = 12')"), false)
  assert.equal(await evaluate("/\\b(misconception|inverse_operation|high_confidence_incorrect|diagnostic_evidence|19\\.3|pass|fail|hint)\\b/i.test(document.querySelector('.quiz-page').textContent)"), false)
  await evaluate("(() => { const server = JSON.parse(localStorage.getItem('__quizMockServer')); server.calls.noWeak = true; localStorage.setItem('__quizMockServer', JSON.stringify(server)); })()")
  await send('Page.reload', { ignoreCache: true })
  await until("document.querySelector('.quiz-page') === null && [...document.querySelectorAll('.app-navigation button')].some(button => button.textContent === 'Quiz Assessment')")
  await evaluate("[...document.querySelectorAll('.app-navigation button')].find(button => button.textContent === 'Quiz Assessment').click()")
  await until("document.querySelector('.quiz-collection-gate button[type=submit]:not(:disabled)')")
  await evaluate("(() => { const input = document.querySelector('#quiz-student-code'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'STU_001'); input.dispatchEvent(new Event('input', { bubbles: true })); })()")
  await click('.quiz-collection-gate button[type=submit]')
  await until("document.querySelector('#quiz-completed-title')?.textContent === 'Assessment Complete'")
  assert.equal(await evaluate("document.querySelector('.quiz-result-list').textContent.includes('No single weak area identified')"), true)
  assert.equal(await evaluate("document.querySelector('.quiz-result-list').textContent.includes('Continue practising all Linear Equation skills.')"), true)
  assert.equal(await evaluate("document.querySelector('.quiz-result-list').textContent.includes('Equation Meaning')"), false)
  await evaluate("(() => { localStorage.removeItem('quiz.collection.pending.v1'); localStorage.setItem('__quizHangQuestions', '1'); })()")
  await send('Page.reload', { ignoreCache: true })
  await until("[...document.querySelectorAll('.app-navigation button')].some(button => button.textContent === 'Quiz Assessment')")
  await evaluate("[...document.querySelectorAll('.app-navigation button')].find(button => button.textContent === 'Quiz Assessment').click()")
  await until("document.querySelector('.quiz-collection-gate button[type=submit]:not(:disabled)')")
  await evaluate("(() => { const input = document.querySelector('#quiz-student-code'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'STU_002'); input.dispatchEvent(new Event('input', { bubbles: true })); })()")
  await click('.quiz-collection-gate button[type=submit]')
  await until("document.querySelector('.quiz-panel[role=alert]')?.textContent.includes('Quiz request timed out')")
  assert.equal(await evaluate("document.querySelector('.quiz-panel[role=alert] button')?.textContent"), 'Reload questions')
  assert.equal(await evaluate('window.__quizMock.sessions'), 1)
  console.log('Quiz browser flow PASS: emoji feedback and immediate correct answer, three local tries, 4/4/2 levels, refresh recovery, 10 saved first responses, and one completion.')
} finally {
  socket?.close()
  for (const child of children) child.kill()
  if (profile.startsWith(os.tmpdir() + path.sep)) {
    await delay(200)
    await fs.rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 }).catch(() => {})
  }
}
