/** Local-only smoke/visual checks, no shared DB writes or signed-in browser use.
 * Requires Chrome on macOS, Node 24+, installed frontend and backend dependencies.
 * Run: npm run test:e2e. Output: ignored frontend/artifacts/tutor-qa/.
 */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repository = path.dirname(frontend)
const artifacts = path.join(frontend, 'artifacts/tutor-qa')
const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'tutor-qa-'))
const children = []
let socket
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
function launch(command, args, cwd, env = {}) {
  const child = spawn(command, args, { cwd, env: { ...process.env, ...env }, stdio: 'ignore' })
  child.on('error', error => console.error(error.message))
  children.push(child)
  return child
}
async function ready(url, child) {
  for (let i = 0; i < 100; i++) {
    if (child.exitCode !== null) throw Error(`Test process exited before ${url} became ready. Ensure test ports are free.`)
    try { const response = await fetch(url); if (response.ok) return } catch { /* wait for startup */ }
    await delay(200)
  }
  throw Error(`Timed out starting ${url}`)
}
try {
  // Fail rather than accidentally control another service already using a test port.
  for (const port of [8126, 5176, 9226]) {
    try { await fetch(`http://127.0.0.1:${port}`); throw Error(`Port ${port} is already occupied`) }
    catch (error) { if (error.message.includes('occupied')) throw error }
  }
  const backend = launch(path.join(repository, 'backend/.venv/bin/uvicorn'), ['app.main:app', '--host', '127.0.0.1', '--port', '8126'], path.join(repository, 'backend'), { DATABASE_URL: 'sqlite+pysqlite:///:memory:' })
  const vite = launch(process.execPath, [path.join(frontend, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5176', '--strictPort'], frontend, { VITE_API_BASE_URL: 'http://127.0.0.1:8126/api/v1' })
  const chrome = launch(process.env.TUTOR_TEST_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=9226', `--user-data-dir=${profile}`, '--use-angle=swiftshader', '--enable-unsafe-swiftshader', 'about:blank'], frontend)
  await Promise.all([ready('http://127.0.0.1:8126/api/v1/health', backend), ready('http://127.0.0.1:5176', vite), ready('http://127.0.0.1:9226/json', chrome)])
  const targets = await (await fetch('http://127.0.0.1:9226/json')).json()
  socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl)
  await new Promise(resolve => socket.addEventListener('open', resolve, { once: true }))
  let id = 0
  const pending = new Map()
  const errors = []
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data)
    if (message.id) {
      const entry = pending.get(message.id)
      pending.delete(message.id)
      if (message.error) entry.reject(message.error)
      else entry.resolve(message.result)
    }
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text)
  })
  function send(method, params = {}) { return new Promise((resolve, reject) => { pending.set(++id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })) }) }
  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails))
    return result.result.value
  }
  async function until(expression) {
    for (let i = 0; i < 100; i++) { if (await evaluate(`Boolean(${expression})`)) return; await delay(200) }
    console.error(await evaluate(`JSON.stringify({time:document.querySelector('model-viewer')?.currentTime,duration:document.querySelector('model-viewer')?.duration,paused:document.querySelector('model-viewer')?.paused,active:document.querySelector('.sign-chip.is-active')?.innerText,animation:document.querySelector('model-viewer')?.animationName,events:window.auditEvents})`))
    throw Error(`Timeout: ${expression}`)
  }
  async function screenshot(name) {
    const image = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
    await fs.writeFile(path.join(artifacts, `${name}.png`), Buffer.from(image.data, 'base64'))
  }
  const click = text => evaluate(`[...document.querySelectorAll('button')].find(e=>e.textContent===${JSON.stringify(text)}).click()`)
  await fs.mkdir(artifacts, { recursive: true })
  await send('Page.enable'); await send('Runtime.enable')
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1050, deviceScaleFactor: 1, mobile: false })
  await send('Page.navigate', { url: 'http://127.0.0.1:5176/' })
  await until("document.querySelector('model-viewer')?.loaded")
  await until("document.body.innerText.includes('Validated clips only')")
  // Every current level's teaching text must have Sinhala wording; math tokens
  // still come from the same backend equation rather than a separate answer.
  const untranslated = await evaluate(`(async () => {
    const { sinhalaLessonText } = await import('/src/components/sinhalaLessonText.ts');
    const lessons = await Promise.all(['foundation','one_step','two_step','extended'].map(async level => {
      const response = await fetch('http://127.0.0.1:8126/api/v1/tutor/grade10/' + level);
      if (!response.ok) throw Error('Unable to load translation coverage level ' + level);
      return response.json();
    }));
    return lessons.flatMap(lesson => [lesson.simple_explanation.text,
      ...lesson.worked_examples.flatMap(example => example.steps.map(step => step.instruction)),
      ...lesson.practice_questions.flatMap(question => [question.prompt, question.hint.text,
        ...question.progressive_hints.map(hint => hint.text), question.feedback.correct, question.feedback.incorrect])
    ]).filter(text => !sinhalaLessonText(text));
  })()`)
  assert.deepEqual(untranslated, [])
  assert.equal(await evaluate("document.querySelector('.bilingual-instruction [lang=si]').textContent.includes('සමීකරණයක්')"), true)
  assert.equal(await evaluate("document.querySelector('.bilingual-question [lang=si]').textContent.includes('x + 5 = 12')"), true)
  assert.equal(await evaluate("document.querySelector('model-viewer').availableAnimations.length"), 22)
  assert.equal(await evaluate("document.querySelector('.sign-chip.is-active') === null"), true)
  assert.equal(await evaluate("document.querySelector('.tutor-setup').open"), false)
  assert.equal(await evaluate("document.querySelector('.reviewer-settings').open"), false)
  assert.equal(await evaluate("document.querySelector('.practice-evidence').open"), false)
  assert.equal(await evaluate("document.querySelector('.worked-example').tagName"), 'ARTICLE')
  assert.equal(await evaluate("document.querySelector('.avatar-options').open"), false)
  assert.equal(await evaluate("document.querySelector('.worked-example').getBoundingClientRect().top < 250 && document.querySelector('.worked-example').getBoundingClientRect().top < document.querySelector('.practice-card').getBoundingClientRect().top"), true)
  assert.equal(await evaluate("document.querySelector('.avatar-expression').textContent === document.querySelector('.adaptive-equation').textContent"), true)
  assert.equal(await evaluate("document.querySelector('[role=progressbar]').getAttribute('aria-valuenow')"), '1')
  await screenshot('strict-default')
  await evaluate("window.auditEvents=[]; for(const name of ['finished','loop','play','pause']) document.querySelector('model-viewer').addEventListener(name,()=>window.auditEvents.push([name,document.querySelector('model-viewer').animationName,document.querySelector('model-viewer').currentTime])); document.querySelector('model-viewer').scrollIntoView({block:'center'})")
  await click('Preview gestures')
  await until("document.querySelector('.sign-chip.is-active')")
  await click('Pause')
  const pausedTime = await evaluate("document.querySelector('model-viewer').currentTime")
  await delay(450)
  assert.equal(await evaluate("document.querySelector('model-viewer').currentTime"), pausedTime)
  await click('Resume')
  await until("document.querySelector('.sign-chip.is-active') === null && document.querySelector('model-viewer').animationName === 'IDLE'")
  await click('Next step'); await until("document.querySelector('.instruction').innerText.startsWith('Identify')")
  await click('Next step'); await until("document.querySelector('.instruction').innerText.startsWith('Subtract 3')")
  assert.equal(await evaluate("document.querySelector('.bilingual-instruction [lang=si]').textContent"), 'දෙපසින්ම 3 අඩු කරන්න.')
  await until("document.querySelector('.sign-chip.is-active')?.textContent.includes('SUBTRACTION')")
  await delay(950); await click('Pause'); await screenshot('prototype-subtraction')
  await evaluate(`(() => { const input=document.querySelector('#practice-answer'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'7.0'); input.dispatchEvent(new Event('input',{bubbles:true})); })()`)
  await evaluate("document.querySelector('.answer-form').requestSubmit()")
  await until("document.querySelector('.feedback.correct')")
  assert.equal(await evaluate("document.querySelector('.feedback [lang=si]') !== null"), true)
  await evaluate("document.querySelector('.reviewer-settings > summary').click(); document.querySelector('.practice-evidence > summary').click()")
  assert.equal(await evaluate("document.body.innerText.includes('1 / 2 correct on the first attempt')"), true)
  await evaluate("document.querySelector('.practice-evidence > summary').click(); document.querySelector('.reviewer-settings > summary').click(); window.scrollTo(0,0)")
  assert.equal(await evaluate("document.querySelector('[role=progressbar]').getAttribute('aria-valuenow')"), '3')
  await click('Next question →')
  await until("document.querySelector('.practice-prompt').textContent.includes('x + 2 = 8')")
  assert.equal(await evaluate("document.querySelector('.worked-example').tagName"), 'ARTICLE')
  assert.equal(await evaluate("document.querySelector('#practice-answer').value"), '')
  assert.equal(await evaluate("document.querySelector('.feedback') === null"), true)
  await click('Show hint')
  await until("document.querySelector('.question-hints .hint-panel')")
  assert.equal(await evaluate("document.querySelector('.avatar-caption').textContent === document.querySelector('.question-hints .hint-panel p').textContent"), true)
  await click('Next hint')
  await until("document.querySelector('.question-hints .hint-panel p').textContent.includes('Subtract 2')")
  assert.equal(await evaluate("document.querySelector('.question-hints [lang=si]').textContent"), 'දෙපසින්ම 2 අඩු කරන්න.')
  await click('Previous question')
  await until("document.querySelector('.practice-prompt').textContent.includes('x + 5 = 12')")
  assert.equal(await evaluate("document.querySelector('.question-hints .hint-panel') === null"), true)
  assert.equal(await evaluate("document.querySelector('.avatar-expression').textContent === document.querySelector('.practice-prompt').textContent"), true)
  // Hints survive question navigation, without leaking another question's hint.
  await click('Next question →')
  await until("document.querySelector('.avatar-caption').textContent.includes('Subtract 2')")
  await click('Next hint')
  await until("document.querySelector('.hint-button').disabled")
  await screenshot('student-desktop')
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true })
  await delay(300)
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true)
  assert.equal(await evaluate("document.querySelector('.worked-example').getBoundingClientRect().top < document.querySelector('.avatar-panel').getBoundingClientRect().top && document.querySelector('.avatar-panel').getBoundingClientRect().top < document.querySelector('.practice-card').getBoundingClientRect().top"), true)
  await evaluate("document.querySelector('model-viewer').scrollIntoView({block:'center'})")
  await delay(500)
  await screenshot('mobile-avatar')
  await evaluate('window.scrollTo(0,0)')
  await screenshot('mobile')
  await evaluate("document.querySelector('.tutor-setup > summary').click(); document.querySelector('.reviewer-settings > summary').click(); document.querySelector('.practice-evidence > summary').click()")
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true)
  await screenshot('mobile-settings')
  await evaluate("[...document.querySelectorAll('label')].find(e=>e.textContent.includes('Show avatar support')).querySelector('input').click()")
  await until("document.querySelector('.avatar-panel') === null")
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true)

  // Reduced-motion starts in a neutral, non-playing state, even after opt-in.
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] })
  await send('Page.reload', { ignoreCache: true })
  await until("document.querySelector('model-viewer')?.loaded")
  await until("document.querySelector('model-viewer')?.animationName === 'IDLE'")
  assert.equal(await evaluate("[...document.querySelectorAll('label')].find(e=>e.textContent.includes('Auto-play')).querySelector('input').checked"), false)
  await click('Preview gestures')
  await delay(300)
  assert.equal(await evaluate("document.querySelector('.sign-chip.is-active') === null"), true)
  await evaluate("document.querySelector('model-viewer').scrollIntoView({block:'center'})")
  await click('Replay')
  await until("document.querySelector('.sign-chip.is-active') !== null")
  await evaluate("document.querySelector('.reviewer-settings > summary').click(); [...document.querySelectorAll('label')].find(e=>e.textContent.includes('Preview unvalidated')).querySelector('input').click()")
  await until("document.querySelector('.sign-chip.is-active') === null && document.querySelector('model-viewer').animationName === 'IDLE'")
  await screenshot('reduced-motion')

  // A failed GLB request must not take down the mathematics lesson.
  await send('Network.enable')
  await send('Network.setCacheDisabled', { cacheDisabled: true })
  await send('Network.setBlockedURLs', { urls: ['*louise_signs_master.glb*'] })
  await send('Page.reload', { ignoreCache: true })
  await until("document.querySelector('.avatar-model-error')")
  assert.equal(await evaluate("document.querySelector('.practice-prompt').textContent.includes('x + 5 = 12')"), true)
  await screenshot('missing-model-fallback')
  await send('Network.setBlockedURLs', { urls: [] })
  await send('Page.reload', { ignoreCache: true })
  await until("document.querySelector('model-viewer')?.loaded")
  await until("document.querySelector('model-viewer')?.animationName === 'IDLE'")

  // Optional full motion audit; UI-only checks do not resample unchanged assets.
  if (!process.argv.includes('--ui-only')) {
  // Read-only visual audit: sample existing clips; never synthesize any motion.
  const reviewSrc = process.argv.includes('--review-avatar') ? '/models/louise_arm_review.glb' : process.env.TUTOR_AVATAR_REVIEW_SRC
  if (reviewSrc) {
    await evaluate(`document.querySelector('model-viewer').src=${JSON.stringify(reviewSrc)}`)
    await delay(200)
    await until("document.querySelector('model-viewer')?.loaded")
  }
  await evaluate("document.querySelector('model-viewer').pause()")
  const names = await evaluate("document.querySelector('model-viewer').availableAnimations")
  await send('Emulation.setDeviceMetricsOverride', { width: 420, height: 450, deviceScaleFactor: 1, mobile: false })
  await evaluate(`(() => { const v=document.querySelector('model-viewer'); v.animationCrossfadeDuration=0; v.style.cssText='position:fixed;inset:0;width:420px;height:450px;opacity:1;z-index:999;background:#eeeeff'; const h=document.createElement('h2');h.id='audit-label';h.style.cssText='position:fixed;top:0;left:10px;z-index:1000'; document.body.append(h); })()`)
  const poses = []
  for (const name of names) {
    await evaluate(`(async () => { const v=document.querySelector('model-viewer'); v.pause(); v.animationName=${JSON.stringify(name)}; await v.updateComplete; v.play({repetitions:1,pingpong:false}); v.pause(); v.currentTime=v.duration*.45; document.querySelector('#audit-label').textContent=${JSON.stringify(name)}; })()`)
    await delay(180)
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
    poses.push(shot.data)
  }
  const motionSheets = []
  // A midpoint alone misses transition flips. Sample complete clips from the
  // front and side, including returns to rest and finger-heavy number actions.
  for (const orbit of [0, 65]) {
    const frames = []
    await evaluate(`(() => {const v=document.querySelector('model-viewer');v.minCameraOrbit='-90deg 0deg 2.2m';v.maxCameraOrbit='90deg 180deg 3m';v.cameraOrbit='${orbit}deg 88deg 2.2m';v.jumpCameraToGoal()})()`)
    for (const name of ['EQUATION', 'SUBTRACTION', 'SUBSTITUTION', 'NUMBER_5']) {
      for (const fraction of [0, .2, .4, .6, .8, 1]) {
        await evaluate(`(async () => {const v=document.querySelector('model-viewer');v.pause();v.animationName=${JSON.stringify(name)};await v.updateComplete;v.play({repetitions:1,pingpong:false});v.pause();v.currentTime=v.duration*${fraction};document.querySelector('#audit-label').textContent=${JSON.stringify(name + ' · ' + Math.round(fraction*100) + '%')};})()`)
        await delay(100)
        frames.push((await send('Page.captureScreenshot', {format:'png',captureBeyondViewport:false})).data)
      }
    }
    motionSheets.push({name:`arm-transitions-${orbit}`,frames})
  }
  await send('Emulation.setDeviceMetricsOverride', { width: 1260, height: 2030, deviceScaleFactor: 1, mobile: false })
  await evaluate(`document.body.innerHTML=${JSON.stringify('<div style="display:grid;grid-template-columns:repeat(4,315px)">' + poses.map(data => '<img width="315" src="data:image/png;base64,' + data + '">').join('') + '</div>')}`)
  await delay(300)
  await screenshot('all-action-midpoints')
  for (const sheet of motionSheets) {
    await send('Emulation.setDeviceMetricsOverride', {width:1800,height:1320,deviceScaleFactor:1,mobile:false})
    await evaluate(`document.body.innerHTML=${JSON.stringify('<div style="display:grid;grid-template-columns:repeat(6,300px)">' + sheet.frames.map(data=>'<img width="300" src="data:image/png;base64,'+data+'">').join('')+'</div>')}`)
    await delay(200)
    await screenshot(sheet.name)
  }
  }
  assert.deepEqual(errors, [])
  console.log('PASS: always-visible worked-example-first layout, hints and navigation, strict fallback, 22 clips, explicit opt-in, pause/replay, step sequence, server grading, first-attempt evidence, mobile layout, reduced motion, missing model, no JS errors.')
} finally {
  socket?.close()
  for (const child of children) child.kill('SIGTERM')
  console.log(`Temporary isolated browser profile: ${profile}`)
}
