/** Local-only Game visual/input regression. No API server or shared DB is used.
 * Run from frontend/: node tests/gameUi.e2e.mjs
 * Chrome DevTools intercepts the served config to expose its game to this test
 * only. Production source has no audit globals or alternate gameplay paths.
 */
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const output = path.join(root, 'artifacts', 'game-ui-' + Date.now())
const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'game-ui-browser-'))
const chromePath = process.env.GAME_TEST_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const children = []
const errors = []
let socket
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
function launch(command, args, env = {}) {
  const child = spawn(command, args, { cwd: root, env: { ...process.env, ...env }, stdio: 'ignore', windowsHide: true })
  children.push(child)
  return child
}
async function ready(url, child) {
  for (let i = 0; i < 200; i++) {
    if (child.exitCode !== null) throw Error(`Test process exited: ${url}`)
    try { if ((await fetch(url, { signal: AbortSignal.timeout(500) })).ok) return } catch { /* local startup */ }
    await delay(100)
  }
  throw Error(`Timed out starting ${url}`)
}

try {
  await fs.mkdir(output, { recursive: true })
  for (const port of [5193, 9243]) {
    try { await fetch(`http://127.0.0.1:${port}`, { signal: AbortSignal.timeout(500) }); throw Error(`Port ${port} is occupied`) }
    catch (error) { if (error.message.includes('occupied')) throw error }
  }
  const vite = launch(process.execPath, [path.join(root, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5193', '--strictPort'], { VITE_API_BASE_URL: 'http://127.0.0.1:9/api/v1' })
  const chrome = launch(chromePath, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--remote-allow-origins=*', '--remote-debugging-port=9243', `--user-data-dir=${profile}`, 'about:blank'])
  console.log('Starting isolated Vite and Chrome.')
  await Promise.all([ready('http://127.0.0.1:5193', vite), ready('http://127.0.0.1:9243/json', chrome)])
  console.log('Local browser ready.')
  const targets = await (await fetch('http://127.0.0.1:9243/json')).json()
  socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl)
  await new Promise(resolve => socket.addEventListener('open', resolve, { once: true }))
  let id = 0
  const pending = new Map()
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const next = ++id
    pending.set(next, { resolve, reject })
    socket.send(JSON.stringify({ id: next, method, params }))
  })
  socket.addEventListener('message', async event => {
    const message = JSON.parse(event.data)
    if (message.method === 'Runtime.exceptionThrown') {
      const error = message.params.exceptionDetails.text + ': ' + (message.params.exceptionDetails.exception?.description || '')
      errors.push(error)
      console.error(error)
    }
    if (message.method === 'Page.javascriptDialogOpening') void send('Page.handleJavaScriptDialog', { accept: true })
    if (message.method === 'Fetch.requestPaused') {
      const requestId = message.params.requestId
      try {
        const body = await send('Fetch.getResponseBody', { requestId })
        const source = body.base64Encoded ? Buffer.from(body.body, 'base64').toString() : body.body
        const patched = source.replace('return {', 'return { callbacks: { postBoot: game => { window.__gameUiAudit = game; } },')
        assert.notEqual(source, patched, 'Test-only config interception failed')
        await send('Fetch.fulfillRequest', { requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/javascript' }], body: Buffer.from(patched).toString('base64') })
      } catch (error) { errors.push(String(error)); await send('Fetch.continueRequest', { requestId }) }
      return
    }
    if (!message.id) return
    const entry = pending.get(message.id)
    if (!entry) return
    pending.delete(message.id)
    if (message.error) entry.reject(Error(JSON.stringify(message.error)))
    else entry.resolve(message.result)
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
    const diagnostics = await evaluate(`({scene:(${scene})?.sys.settings.key,objects:(${scene})?.children.list.length,active:window.__gameUiAudit?.loop.running})`)
    throw Error(`Timed out: ${expression}; diagnostics=${JSON.stringify(diagnostics)}; errors=${JSON.stringify(errors)}`)
  }
  const scene = 'window.__gameUiAudit?.scene.getScenes(true)[0]'
  const mock = `(() => {
    window.__gameApi = { sessions: [], events: [], attempts: [], completions: 0, failUsage: false };
    const original = window.fetch.bind(window);
    const reply = (data, status=200) => new Response(JSON.stringify(data), {status, headers:{'Content-Type':'application/json'}});
    window.fetch = async (input, init={}) => {
      const url = new URL(typeof input === 'string' ? input : input.url, location.href);
      if (!url.pathname.includes('/api/')) return original(input, init);
      if (!url.pathname.includes('/game/')) return reply({}, 503);
      const body = init.body ? JSON.parse(init.body) : {};
      const calls = window.__gameApi;
      if (url.pathname.endsWith('/variant-usage')) return calls.failUsage ? reply({},503) : reply({usage_counts:{}});
      if (url.pathname.endsWith('/sessions')) { calls.sessions.push(body); return reply({...body,game_session_id:body.client_session_id,status:'in_progress',started_at:new Date().toISOString(),completed_at:null}); }
      if (url.pathname.endsWith('/events')) { calls.events.push(body); return reply({}); }
      if (url.pathname.endsWith('/task-attempts')) { calls.attempts.push(body); return reply({}); }
      if (url.pathname.endsWith('/complete')) { calls.completions++; return reply({game_session_id:url.pathname.split('/').at(-2),status:'completed'}); }
      return reply({}, 503); // Deliberately exercise the existing local summary fallback.
    };
  })()`
  await send('Runtime.enable')
  await send('Page.enable')
  await send('Page.bringToFront')
  await send('Page.addScriptToEvaluateOnNewDocument', { source: mock })
  await send('Fetch.enable', { patterns: [{ urlPattern: '*/src/game/phaser/GameConfig.ts*', requestStage: 'Response' }] })
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 2, mobile: false })
  await send('Page.navigate', { url: 'http://127.0.0.1:5193' })
  async function setStudent() {
    await until(`document.querySelector('#collection-student') && !document.querySelector('#collection-student').disabled`)
    await evaluate(`(() => {const e=document.querySelector('#collection-student');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(e,'STU_999');e.dispatchEvent(new Event('input',{bubbles:true}));})()`)
    await delay(80)
    await evaluate(`document.querySelector('.collection-gate button[type=submit]').click()`)
    await until(`${scene}?.sys.settings.key === 'GameSelectionScene'`)
  }
  async function endCollection() {
    await until(`document.querySelector('.collection-gate')?.textContent.includes('Saved')`)
    await evaluate(`document.querySelector('.collection-gate input[type=checkbox]').click()`)
    const close = `[...document.querySelectorAll('.collection-gate button')].find(b=>b.textContent==='End collection / switch learner')`
    await until(`!(${close}).disabled`)
    await evaluate(`(${close}).click()`)
    await until(`document.querySelector('#collection-student')`)
  }
  await setStudent()
  await until(`${scene}?.sys.settings.key === 'GameSelectionScene'`)
  await delay(450)

  async function screenshot(name) {
    // Renderer snapshots do not resize or scroll the DOM as CDP full-page
    // screenshots can. They also include controls below a phone's viewport.
    const data = await evaluate('new Promise(resolve => window.__gameUiAudit.renderer.snapshot(img => resolve(img.src)))')
    await fs.writeFile(path.join(output, name + '.png'), Buffer.from(data.split(',')[1], 'base64'))
  }
  async function point(expression) {
    await until(`${scene}?.cameras && (${expression})`)
    await evaluate(`(() => {
      const s=${scene}, o=${expression}, c=s.cameras.main;
      const m=o.getWorldTransformMatrix();
      const p=c.matrixCombined.transformPoint(m.tx,m.ty);
      const canvas=s.game.canvas, r=canvas.getBoundingClientRect();
      const y=r.top+p.y*r.height/canvas.height;
      window.scrollBy(0,y<80 ? y-80 : Math.max(0,y-window.innerHeight+90));
    })()`)
    await delay(180)
    await until(`${scene}?.cameras && (${expression})`)
    return evaluate(`(() => {
      const s=${scene},o=${expression},canvas=s.game.canvas;
      const m=o.getWorldTransformMatrix(),p=s.cameras.main.matrixCombined.transformPoint(m.tx,m.ty);
      s.game.scale.updateBounds();
      const b=canvas.getBoundingClientRect();
      return {x:b.left+p.x*b.width/canvas.width,y:b.top+p.y*b.height/canvas.height};
    })()`)
  }
  async function tap(expression, touch = false) {
    const p = await point(expression)
    if (touch) {
      await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [p] })
      await delay(80)
      await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
    } else {
      await send('Input.dispatchMouseEvent', { type: 'mouseMoved', ...p })
      await send('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...p })
      await send('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...p })
    }
    await delay(60)
  }
  const findButton = label => `${scene}.children.list.find(o=>o.type==='Container' && o.list?.some(t=>t.text===${JSON.stringify(label)} || t.text?.startsWith(${JSON.stringify(label + '\n')})))`
  const card = type => `${scene}.children.list.find(o=>o.type==='Container' && o.list?.some(t=>t.text===${JSON.stringify(type)}))`
  const state = () => evaluate(`(() => {const s=${scene};return {key:s.sys.settings.key,level:s.session?.levelIndex,step:s.currentStepIndex,stars:s.session?.stars,wrong:s.tracker?.getSummary().totalWrongAttempts,hints:s.tracker?.getSummary().totalHintsUsed,attempts:s.tracker?.getCurrentLevelTotals()?.attemptsCount,buffer:s.answerBuffer,grip:s.figure?.fingersLost,locked:s.locked};})()`)
  const correctCard = `${scene}.operationButtons.find(b=>b.getData('choice').isCorrect)`
  const wrongCard = `${scene}.operationButtons.find(b=>!b.getData('choice').isCorrect)`
  async function enter(value, touch=false) {
    for (const digit of value) await tap(findButton(digit), touch)
  }
  await screenshot('selection-desktop')
  const renderer = await evaluate(`(() => {const s=${scene},c=s.game.canvas,r=c.getBoundingClientRect(); return {dpr:devicePixelRatio,backingWidth:c.width,cssWidth:r.width,zoom:s.cameras.main.zoom,textResolution:s.children.list.find(o=>o.type==='Text').style.resolution};})()`)
  assert.equal(Math.round(renderer.backingWidth / renderer.cssWidth), 2)
  assert.ok(renderer.textResolution > 1)
  if (!process.env.GAME_UI_PHONE_ONLY) {
  await tap(card('Mystery Reveal'))
  assert.equal(await evaluate(`${scene}.sys.settings.key`), 'GameSelectionScene')
  await tap(card('Drag & Drop'))
  await until(`${scene}?.sys.settings.key==='EquationGameScene' && ${scene}.operationButtons?.length>0`)
  await screenshot('drag-drop-desktop')
  console.log('Desktop selection and Drag & Drop launch passed. Renderer:', renderer)

  const beforeHint = await state()
  await tap(`${scene}.hintButton`)
  assert.equal((await state()).hints, beforeHint.hints + 1)
  await tap(wrongCard)
  assert.equal((await state()).wrong, 1)
  await delay(900)

  // Preserve the pre-existing Phaser 4 missed-drag/tap quirk. The original
  // pointerdown resets the flag after Phaser fires dragstart, so a missed
  // drag can still be counted as a tap. Fixing mechanics is outside this pass.
  async function drag(expression, destination) {
    const from = await point(expression)
    const to = await point(destination)
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', ...from })
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', button: 'left', clickCount: 1, ...from })
    for (let i = 1; i <= 12; i++) {
      await send('Input.dispatchMouseEvent', { type: 'mouseMoved', buttons: 1, x: from.x + (to.x - from.x) * i / 12, y: from.y + (to.y - from.y) * i / 12 })
      await delay(20)
    }
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', button: 'left', clickCount: 1, ...to })
    await delay(80)
  }
  const attemptsBeforeMiss = (await state()).attempts
  await drag(wrongCard, `${scene}.equationText`)
  assert.equal((await state()).attempts, attemptsBeforeMiss + 1)
  assert.equal((await state()).wrong, 2)
  await delay(350)
  await drag(correctCard, `${scene}.dropZone`)
  await until(`${scene}.hasAnsweredStepCorrectly`)
  await until(`${scene}.nextButton.input.enabled`)
  assert.equal((await state()).stars[0], 1)
  await screenshot('drag-drop-feedback-desktop')
  // Complete all remaining steps through their real tap targets.
  for (let iteration = 0; iteration < 30; iteration++) {
    const s = await state()
    if (await evaluate(`${scene}.showSummary`)) break
    if (await evaluate(`${scene}.nextButton.input.enabled`)) {
      await tap(`${scene}.nextButton`)
      continue
    }
    if (await evaluate(`${scene}.hasAnsweredStepCorrectly`)) { await delay(2200); continue }
    await tap(correctCard)
    await until(`${scene}.currentStepIndex!==${s.step} || ${scene}.nextButton.input.enabled || ${scene}.showSummary || (${scene}.session.levelIndex===5 && ${scene}.session.stars[5]!==undefined)`)
  }
  await until(`${scene}.showSummary && ${scene}.children.list.some(o=>o.type==='Container'&&o.list?.some(t=>t.text==='Choose Another Game'))`)
  const dragEvidence = await evaluate(`({attempts:window.__gameApi.attempts,events:window.__gameApi.events.map(e=>({task:e.task_id,type:e.event_type})),tracker:(${scene}).tracker.getSummary()})`)
  await fs.writeFile(path.join(output, 'drag-evidence.json'), JSON.stringify(dragEvidence,null,2))
  assert.deepEqual(await evaluate('window.__gameApi.attempts.map(a=>a.difficulty_level)'), ['easy','easy','medium','medium','hard','hard'])
  assert.equal(await evaluate('window.__gameApi.attempts.length'), 6)
  assert.equal(await evaluate('window.__gameApi.completions'), 1)
  await tap(findButton('Show details ▾'))
  await tap(findButton('Hide details ▴'))
  await screenshot('drag-drop-summary-desktop')
  await tap(findButton('Choose Another Game'))
  await until(`${scene}?.sys.settings.key==='GameSelectionScene'`)
  console.log('Drag & Drop: hints, wrong feedback, missed drag, correct drag, tap, 6-task progression, stars, local summary and mocked persistence passed.')

  // Remaining regressions exercise the actual scene callbacks through pointer
  // input; the audit global is used only to inspect state and locate controls.
  await tap(card('Hangman'))
  await until(`${scene}?.sys.settings.key==='HangmanGameScene' && ${scene}.keyButtons?.length===12`)
  await screenshot('hangman-desktop')
  console.log('Desktop Hangman launch passed.')

  await tap(`${scene}.submitButton`)
  assert.equal((await state()).attempts, 0)
  await enter('12')
  await tap(findButton('⌫'))
  assert.equal((await state()).buffer, '1')
  await tap(findButton('⌫'))
  await tap(findButton('-'))
  await tap(`${scene}.submitButton`)
  assert.equal((await state()).attempts, 0)
  await tap(findButton('⌫'))
  await tap(`${scene}.hintButton`)
  assert.equal((await state()).hints, 1)
  assert.equal((await state()).grip, 0)
  await enter('999')
  await tap(`${scene}.submitButton`)
  assert.equal((await state()).grip, 1)
  assert.equal((await state()).buffer, '')
  assert.equal((await state()).wrong, 1)
  await screenshot('hangman-wrong-desktop')
  for (let n = 2; n <= 10; n++) {
    await enter('999')
    await tap(`${scene}.submitButton`)
    assert.equal((await state()).wrong, n)
    if (n < 10) assert.equal((await state()).grip, n)
  }
  await until(`${scene}.nextButton.input.enabled`)
  assert.equal((await state()).stars[0], 0)
  assert.equal(await evaluate(`${scene}.figure.fallProgress`), 1)
  await screenshot('hangman-failed-desktop')
  await tap(`${scene}.nextButton`)
  for (let q = 1; q < 6; q++) {
    assert.equal((await state()).level, q)
    const expected = await evaluate(`${scene}.currentVariant.finalAnswer`)
    await enter(expected)
    await tap(`${scene}.submitButton`)
    assert.equal((await state()).grip, 0)
    if (q === 1) {
      assert.equal(await evaluate(`${scene}.figure.celebrating`), true)
      await screenshot('hangman-correct-desktop')
    }
    if (q < 5) { await until(`${scene}.nextButton.input.enabled`); await tap(`${scene}.nextButton`) }
  }
  await until(`${scene}.showSummary && ${scene}.children.list.some(o=>o.type==='Container'&&o.list?.some(t=>t.text==='Choose Another Game'))`)
  assert.deepEqual((await state()).stars, [0,3,3,3,3,3])
  assert.equal(await evaluate('window.__gameApi.attempts.length'), 12)
  assert.equal(await evaluate('window.__gameApi.attempts[6].wrong_attempts'), 10)
  assert.equal(await evaluate('window.__gameApi.attempts[6].is_successful'), false)
  assert.equal(await evaluate('window.__gameApi.completions'), 2)
  await screenshot('hangman-summary-desktop')
  await tap(findButton('Choose Another Game'))
  await until(`${scene}?.sys.settings.key==='GameSelectionScene'`)
  console.log('Hangman: keypad/backspace/minus, empty submission, hints, ten slips/fall, correct grip preservation, stars, progression, summary and mocked persistence passed.')
  await endCollection()
  }

  const phoneMetrics = []
  for (const width of [390, 320]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 844, deviceScaleFactor: 3, mobile: true })
    await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 })
    await send('Page.reload')
    await delay(500)
    await setStudent()
    await until(`${scene}?.sys.settings.key==='GameSelectionScene'`)
    await delay(300)
    await screenshot(`selection-phone-${width}`)
    await tap(card('Mystery Reveal'), true)
    assert.equal(await evaluate(`${scene}.sys.settings.key`), 'GameSelectionScene')
    await tap(card('Drag & Drop'), true)
    await until(`${scene}?.sys.settings.key==='EquationGameScene' && ${scene}.operationButtons?.length>0`)
    const geometry = await evaluate(`(() => {const s=${scene},c=s.game.canvas,r=c.getBoundingClientRect(),b=s.operationButtons[0];return {width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth,ratio:c.width/r.width,tapHeight:b.input.hitArea.height*s.cameras.main.zoom*r.width/c.width};})()`)
    assert.equal(geometry.overflow, false)
    assert.ok(Math.abs(geometry.ratio-2)<.01, 'DPR 3 is capped at 2')
    assert.ok(geometry.tapHeight >= 44)
    await evaluate('window.scrollTo(0,0)')
    await delay(200)
    const background = await point(`${scene}.equationText`)
    const scrollBefore = await evaluate('scrollY')
    await send('Input.dispatchTouchEvent', {type:'touchStart',touchPoints:[background]})
    for (let move=1;move<=8;move++) {
      await send('Input.dispatchTouchEvent', {type:'touchMove',touchPoints:[{x:background.x,y:background.y-move*18}]})
      await delay(30)
    }
    await send('Input.dispatchTouchEvent', {type:'touchEnd',touchPoints:[]})
    await until(`scrollY>${scrollBefore+30}`)
    await delay(600)
    assert.equal((await state()).attempts, 0)
    await tap(`${scene}.hintButton`, true)
    assert.equal((await state()).hints, 1)
    await screenshot(`drag-drop-phone-${width}`)
    await tap(correctCard, true)
    await until(`${scene}.nextButton.input.enabled`)
    await tap(`${scene}.nextButton`, true)
    await until(`${scene}.session.levelIndex===1`)
    assert.equal((await state()).level, 1)
    const dragFrom = await point(correctCard), dragTo = await point(`${scene}.dropZone`)
    const dragScroll = await evaluate('scrollY')
    await send('Input.dispatchTouchEvent', {type:'touchStart',touchPoints:[dragFrom]})
    for (let move=1;move<=10;move++) {
      await send('Input.dispatchTouchEvent', {type:'touchMove',touchPoints:[{x:dragFrom.x+(dragTo.x-dragFrom.x)*move/10,y:dragFrom.y+(dragTo.y-dragFrom.y)*move/10}]})
      await delay(30)
    }
    await send('Input.dispatchTouchEvent', {type:'touchEnd',touchPoints:[]})
    await until(`${scene}.hasAnsweredStepCorrectly`)
    assert.equal(await evaluate('scrollY'), dragScroll)
    await tap(findButton('☰ Menu'), true)
    await until(`${scene}?.sys.settings.key==='GameSelectionScene'`)
    await endCollection()
    await setStudent()
    await tap(card('Hangman'), true)
    await until(`${scene}?.sys.settings.key==='HangmanGameScene' && ${scene}.keyButtons?.length===12`)
    const keyHeight = await evaluate(`(() => {const s=${scene};return s.keyButtons[0].input.hitArea.height*s.cameras.main.zoom*s.game.canvas.getBoundingClientRect().width/s.game.canvas.width;})()`)
    assert.ok(keyHeight >= 44)
    const ids = await evaluate(`${scene}.session.levels.map(v=>v.variantId)`)
    await screenshot(`hangman-phone-${width}`)
    await enter(await evaluate(`${scene}.currentVariant.finalAnswer`), true)
    await tap(`${scene}.submitButton`, true)
    await until(`${scene}.nextButton.input.enabled`)
    await tap(`${scene}.nextButton`, true)
    await until(`${scene}.session.levelIndex===1`)
    assert.equal((await state()).level, 1)
    await send('Emulation.setDeviceMetricsOverride', { width: 844, height: 390, deviceScaleFactor: 2, mobile: true })
    await until(`${scene}.isCompactLayout===false`)
    assert.deepEqual(await evaluate(`${scene}.session.levels.map(v=>v.variantId)`), ids)
    assert.equal((await state()).level, 1)
    await screenshot(`hangman-landscape-${width}`)
    await tap(findButton('☰ Menu'), true)
    await until(`${scene}?.sys.settings.key==='GameSelectionScene'`)
    await endCollection()
    phoneMetrics.push({...geometry,keyHeight})
    console.log('Phone '+width+': touch, 44px controls, no horizontal clipping, both games and orientation state preservation passed.')
  }
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] })
  await send('Page.reload')
  await delay(500)
  await setStudent()
  await until(`${scene}?.sys.settings.key==='GameSelectionScene'`)
  await evaluate('window.__gameApi.failUsage=true')
  await tap(card('Hangman'))
  await until(`${scene}?.sys.settings.key==='HangmanGameScene' && ${scene}.keyButtons?.length===12`)
  assert.equal(await evaluate(`${scene}.reducedMotion`), true)
  assert.equal(await evaluate(`${scene}.session.levels.length`), 6)
  await enter('999')
  await tap(`${scene}.submitButton`)
  assert.equal((await state()).grip, 1)
  for (let wrong=2;wrong<=10;wrong++) {
    await enter('999')
    await tap(`${scene}.submitButton`)
  }
  assert.equal(await evaluate(`${scene}.figure.fallProgress`), 1)
  assert.equal((await state()).stars[0], 0)
  await tap(findButton('☰ Menu'))
  await until(`${scene}?.sys.settings.key==='GameSelectionScene'`)
  await endCollection()
  assert.deepEqual(errors, [])
  await fs.writeFile(path.join(output, 'verification.json'), JSON.stringify({ renderer, phoneMetrics, errors, checks: ['desktop full sessions','drag and tap','Hangman failure and success','mocked API evidence','390/320px touch','landscape resize','reduced motion','offline usage fallback'] }, null, 2))
  console.log('PASS: local visual and input regressions. Screenshots: '+output)
} finally {
  socket?.close()
  for (const child of children) child.kill('SIGTERM')
}
