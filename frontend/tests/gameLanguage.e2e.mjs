/** Local-only Game primary-language regression. No API server or shared DB is used.
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
const output = path.join(root, 'artifacts', 'game-language-' + Date.now())
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
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false })
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
  await until(`!![...document.querySelectorAll('.app-navigation button')].find(b=>b.textContent==='Equation Game')`)
  await evaluate(`[...document.querySelectorAll('.app-navigation button')].find(b=>b.textContent==='Equation Game').click()`)
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
  assert.equal(Math.round(renderer.backingWidth / renderer.cssWidth), 1)
  assert.ok(renderer.textResolution > 1)

  const labels = await evaluate(`import('/src/game/phaser/gameText.ts').then(m=>({drag:m.GAME_TEXT.balanceEquation,hangman:m.GAME_TYPE_TEXT.hangman.name}))`)
  const report=[]
  async function language(value) {
    await evaluate(`document.querySelector('.game-language-toggle button[lang=${value}]').click()`)
    assert.equal(await evaluate(`document.querySelector('.game-language-toggle button[lang=${value}]').getAttribute('aria-pressed')`),'true')
  }
  async function heading(mode, value) {
    const pair=labels[mode]
    const p=value==='si'?pair.si:pair.en, q=value==='si'?pair.en:pair.si
    const geometry=await evaluate(`(()=>{const s=${scene},t=s.children.list.filter(o=>o.type==='Text'),a=t.find(o=>o.text===${JSON.stringify(p)}),b=t.find(o=>o.text===${JSON.stringify(q)}); return {primary:a?.style.fontSize,secondary:b?.style.fontSize,primaryY:a?.y,secondaryY:b?.y,primaryBottom:a?.getBounds().bottom,secondaryTop:b?.getBounds().top,compact:s.isCompactLayout};})()`)
    assert.ok(parseFloat(geometry.primary)>parseFloat(geometry.secondary))
    assert.ok(geometry.primaryY<geometry.secondaryY)
    assert.ok(geometry.primaryBottom<=geometry.secondaryTop)
    return geometry
  }
  async function stableState() {
    await until(`document.querySelector('.collection-gate')?.textContent.includes('Saved')`)
    return evaluate(`(()=>{const s=${scene};return {cycle:s.session.learningCycleId,student:s.session.studentId,mode:s.session.gameType,level:s.session.levelIndex,step:s.currentStepIndex,wrong:s.tracker.getSummary().totalWrongAttempts,hints:s.tracker.getSummary().totalHintsUsed,stars:s.session.stars,buffer:s.answerBuffer,grip:s.figure?.fingersLost,attempts:s.tracker.getCurrentLevelTotals()?.attemptsCount,choices:s.operationButtons?.map(b=>b.getData('choice').label),backendEvents:window.__gameApi.events.length,backendSessions:window.__gameApi.sessions.length};})()`)
  }
  async function switchWithoutReset(mode) {
    const before=await stableState()
    await evaluate(`window.__languageSession=${scene}.session`)
    await language('en')
    const en=await heading(mode,'en')
    assert.deepEqual(await stableState(),before)
    assert.equal(await evaluate(`${scene}.session===window.__languageSession`),true)
    await language('si')
    const si=await heading(mode,'si')
    assert.deepEqual(await stableState(),before)
    report.push({mode,si,en,statePreserved:true})
  }
  assert.equal(await evaluate(`document.querySelector('.game-language-toggle button[lang=si]').getAttribute('aria-pressed')`),'true')
  await tap(card('Drag & Drop'))
  await until(`${scene}.operationButtons?.length>0`)
  await heading('drag','si')
  await tap(wrongCard)
  await delay(700)
  await tap(`${scene}.hintButton`)
  await switchWithoutReset('drag')
  assert.ok((await evaluate(`${scene}.hintText.text`)).split('\n').at(-1).startsWith('Use') || (await evaluate(`${scene}.hintText.text`)).includes('\n'))
  await screenshot('drag-sinhala-default')
  for (let iteration=0;iteration<50;iteration++) {
    if (await evaluate(`${scene}.showSummary`)) break
    if (await evaluate(`${scene}.nextButton.input.enabled`)) { await tap(`${scene}.nextButton`); continue }
    if (await evaluate(`${scene}.hasAnsweredStepCorrectly`)) { await delay(300); continue }
    const prior=await state()
    await tap(correctCard)
    await until(`${scene}.showSummary || ${scene}.nextButton.input.enabled || ${scene}.currentStepIndex!==${prior.step} || ${scene}.session.levelIndex!==${prior.level} || ${scene}.session.stars.length===6`)
    if (await evaluate(`${scene}.session.stars.length===6`)) break
  }
  await until(`${scene}.showSummary && ${scene}.children.list.some(o=>o.type==='Container'&&o.list?.some(t=>t.text==='Choose Another Game'))`)
  const summaryStars=await evaluate(`${scene}.session.stars`)
  const summaryPair=await evaluate(`import('/src/game/phaser/gameText.ts').then(m=>m.GAME_TEXT.sessionComplete)`)
  const summaryBounds=await evaluate(`(()=>{const t=${scene}.children.list.filter(o=>o.type==='Text');const si=t.find(o=>o.text===${JSON.stringify(summaryPair.si)}),en=t.find(o=>o.text===${JSON.stringify(summaryPair.en)});return {siBottom:si.getBounds().bottom,enTop:en.getBounds().top};})()`)
  assert.ok(summaryBounds.siBottom<=summaryBounds.enTop)
  await screenshot('drag-summary-sinhala')
  await language('en'); await language('si')
  assert.deepEqual(await evaluate(`${scene}.session.stars`),summaryStars)
  await tap(findButton('Choose Another Game'))
  await until(`${scene}.sys.settings.key==='GameSelectionScene'`)
  await tap(card('Hangman'))
  await until(`${scene}.keyButtons?.length===12`)
  await heading('hangman','si')
  await enter('999'); await tap(`${scene}.submitButton`)
  await tap(`${scene}.hintButton`)
  await enter('12')
  await switchWithoutReset('hangman')
  assert.equal(await evaluate(`${scene}.answerBuffer`),'12')
  await screenshot('hangman-sinhala-default')

  await tap(`${scene}.keyButtons[11]`); await tap(`${scene}.keyButtons[11]`)
  for (let question=0;question<6;question++) {
    await enter(await evaluate(`${scene}.currentVariant.finalAnswer`))
    await tap(`${scene}.submitButton`)
    if (question===5) break
    await until(`${scene}.nextButton.input.enabled`)
    await tap(`${scene}.nextButton`)
  }
  await until(`${scene}.showSummary && ${scene}.children.list.some(o=>o.type==='Container'&&o.list?.some(t=>t.text==='Choose Another Game'))`)
  await language('en'); await language('si')
  await screenshot('hangman-summary-sinhala')
  await endCollection()
  for (const mode of ['drag','hangman']) {
    await send('Emulation.setDeviceMetricsOverride',{width:390,height:1100,deviceScaleFactor:1,mobile:true})
    await send('Page.reload')
    await until(`!![...document.querySelectorAll('.app-navigation button')].find(b=>b.textContent==='Equation Game')`)
    await evaluate(`[...document.querySelectorAll('.app-navigation button')].find(b=>b.textContent==='Equation Game').click()`)
    await setStudent()
    await tap(card(mode==='drag'?'Drag & Drop':'Hangman'))
    await until(`${scene}.session?.levels.length===6`)
    if(mode==='drag') await until(`${scene}.operationButtons?.length>0`)
    else await until(`${scene}.keyButtons?.length===12`)
    assert.equal((await heading(mode,'si')).compact,true)
    await switchWithoutReset(mode)
    await screenshot(mode+'-phone-sinhala')
    await endCollection()
  }
  assert.deepEqual(errors,[])
  await fs.writeFile(path.join(output,'verification.json'),JSON.stringify({status:'PASS',checks:['Sinhala default','both games and menu','live primary-language switch','same session and backend evidence','Drag & Drop retries/hints/choice order preserved','Hangman buffer and grip preserved','both full desktop summaries','compact phone headings'],report},null,2))
  console.log('PASS Game language defaults, switching and state preservation: '+output)
} finally {
  socket?.close()
  for(const child of children) child.kill('SIGTERM')
}
